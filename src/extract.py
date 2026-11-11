"""Extract MCP tool definitions and capability signals from source files.

Parsing uses tree-sitter (Python, TypeScript/JavaScript). For each tool we
record its name, its description (literal strings resolved, including
implicit concatenation, template literals without substitutions and
same-file string constants), and capability signals found in its handler
plus helper functions it calls (depth <= 2, resolved repo-wide by name).

Supported registration styles
  Python: @<x>.tool(...) decorators (FastMCP / official SDK high-level API)
          Tool(name=..., description=...) objects (official low-level API)
  TS/JS:  <x>.tool("name", "desc"?, ...)  (official SDK, older API)
          <x>.registerTool("name", {description, ...}, handler)
          {name: "...", description: "..."} literals in files that handle
          ListToolsRequestSchema (official low-level API)
"""
import hashlib
import re
from dataclasses import dataclass, field, asdict

import tree_sitter_python as tspy
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser

PY = Parser(Language(tspy.language()))
TS = Parser(Language(tsts.language_typescript()))
TSX = Parser(Language(tsts.language_tsx()))

# ---------------------------------------------------------------- capabilities
CAPS = {
    "network": [
        r"\brequests\.(get|post|put|patch|delete|head|request|Session)\b",
        r"\bhttpx\.", r"\baiohttp\.", r"\burllib\.request\b", r"\burlopen\(",
        r"\bsocket\.(socket|create_connection)\(", r"(?<![\w.])fetch\(", r"\baxios\b",
        r"\bhttps?\.(request|get)\(", r"\bnew WebSocket\(", r"\bnode-fetch\b",
        r"\bundici\b", r"\bsmtplib\b", r"\bnodemailer\b", r"\bparamiko\b", r"\bky\(",
    ],
    "shell": [
        r"\bsubprocess\.", r"\bos\.system\(", r"\bos\.popen\(", r"\bos\.exec\w*\(",
        r"\bchild_process\b", r"\bexecSync\(", r"\bexecFile(Sync)?\(",
        r"(?<![\w.])spawn(Sync)?\(", r"\bexeca\b", r"\bshelljs\b", r"\bpty\.spawn",
        r"\bcreate_subprocess_(exec|shell)\b",
    ],
    "fs_write": [
        r"open\([^)]*['\"][wax]\+?b?['\"]", r"\.write_(text|bytes)\(",
        r"\b(writeFile|appendFile|unlink|rmdir|copyFile|mkdir)(Sync)?\(",
        r"\bfs\.(promises\.)?(rm|rename)(Sync)?\(",
        r"\bshutil\.(rmtree|move|copy\w*)\(", r"\bos\.(remove|unlink|rename|replace|makedirs|mkdir|rmdir)\(",
        r"\.(unlink|touch)\(\)",
    ],
    "fs_read": [
        r"(?<![\w.])open\(", r"\.read_(text|bytes)\(",
        r"\b(readFile|readdir|createReadStream)(Sync)?\(",
        r"\bos\.(listdir|walk|scandir)\(", r"\bglob\.(i?glob)\(",
    ],
    "env_secrets": [
        r"\bos\.environ\b", r"\bos\.getenv\(", r"\bprocess\.env\b", r"\bkeyring\.",
        r"\.ssh/", r"\.aws/credentials", r"\bid_rsa\b", r"\.npmrc\b", r"\.netrc\b",
    ],
    "dynamic_code": [
        r"(?<![\w.])eval\(", r"(?<![\w.])exec\(", r"\bimportlib\.import_module\((?!\s*['\"])",
        r"\bnew Function\(", r"\bvm\.runIn\w+\(", r"\b__import__\((?!\s*['\"])", r"\bpickle\.loads?\(",
    ],
}
CAP_RE = {k: re.compile("|".join(v)) for k, v in CAPS.items()}
URL_RE = re.compile(r"https?://([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
IGNORE_DOMAINS = ("example.com", "example.org", "localhost", "127.0.0.1", "schemas.openxmlformats.org",
                  "www.w3.org", "json-schema.org", "github.com", "modelcontextprotocol.io")


# String literals and comments. Short strings (e.g. file modes like "w") are kept so that
# open(path, "w") is still recognised; long strings (scripts, help text, prompts) are blanked.
_STR_OR_COMMENT = re.compile(
    r'''("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|`(?:\\.|[^`\\])*`|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|/\*[\s\S]*?\*/|//[^\n]*|\#[^\n]*)''')
# Sensitive credential paths only ever appear inside strings, so they are matched on the raw text.
_SENSITIVE_PATH = re.compile(r"\.ssh/|\.aws/credentials|\bid_rsa\b|\.npmrc\b|\.netrc\b")


def _strip_code(text):
    def repl(m):
        t = m.group(0)
        if t.startswith(("//", "/*", "#")):
            return " "
        return t if len(t) <= 12 else t[0] + t[0]
    return _STR_OR_COMMENT.sub(repl, text)


def capabilities(text):
    code = _strip_code(text)
    caps = {k for k, rx in CAP_RE.items() if rx.search(code)}
    if _SENSITIVE_PATH.search(text):
        caps.add("env_secrets")
    return sorted(caps)


def domains(text):
    return sorted({d.lower() for d in URL_RE.findall(text) if not d.lower().endswith(IGNORE_DOMAINS)})


def _h(text):
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:12]


@dataclass
class Tool:
    name: str
    description: str
    file: str
    lang: str
    desc_dynamic: bool = False
    caps: list = field(default_factory=list)
    domains: list = field(default_factory=list)
    body_hash: str = ""
    callees: list = field(default_factory=list)  # helper names, resolved repo-wide later
    direct_caps: list = field(default_factory=list)  # caps in the tool's own handler body
    caps_via: dict = field(default_factory=dict)  # cap -> "self" or first helper that adds it

    def to_dict(self):
        return asdict(self)


def _txt(node, src):
    return src[node.start_byte:node.end_byte].decode("utf-8", "ignore")


def _walk(node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(")


# ================================================================== Python
def _py_str(node, src, consts):
    """Evaluate a Python string expression to text, or None if dynamic."""
    if node is None:
        return None
    t = node.type
    if t == "string":
        if any(c.type == "interpolation" for c in node.children):
            return None
        return "".join(_txt(c, src) for c in node.children if c.type == "string_content")
    if t == "concatenated_string":
        parts = [_py_str(c, src, consts) for c in node.children if c.type == "string"]
        return None if None in parts else "".join(parts)
    if t == "parenthesized_expression":
        inner = [c for c in node.children if c.type not in ("(", ")", "comment")]
        return _py_str(inner[0], src, consts) if len(inner) == 1 else None
    if t == "binary_operator" and len(node.children) == 3 and _txt(node.children[1], src) == "+":
        a, b = _py_str(node.children[0], src, consts), _py_str(node.children[2], src, consts)
        return None if a is None or b is None else a + b
    if t == "identifier":
        return consts.get(_txt(node, src))
    return None


def _py_consts(root, src):
    consts = {}
    for n in root.children:
        if n.type == "expression_statement" and n.children and n.children[0].type == "assignment":
            a = n.children[0]
            left, right = a.child_by_field_name("left"), a.child_by_field_name("right")
            if left is not None and left.type == "identifier" and right is not None:
                v = _py_str(right, src, consts)
                if v is not None:
                    consts[_txt(left, src)] = v
    return consts


def _py_docstring(fn, src):
    body = fn.child_by_field_name("body")
    if body is None or not body.children:
        return ""
    first = body.children[0]
    if first.type == "expression_statement" and first.children and first.children[0].type == "string":
        return _py_str(first.children[0], src, {}) or ""
    return ""


def _kwargs(call, src):
    out, pos = {}, []
    args = call.child_by_field_name("arguments")
    if args is None:
        return out, pos
    for a in args.children:
        if a.type == "keyword_argument":
            out[_txt(a.child_by_field_name("name"), src)] = a.child_by_field_name("value")
        elif a.type not in ("(", ")", ",", "comment"):
            pos.append(a)
    return out, pos


def py_functions(root, src):
    funcs = {}
    for n in _walk(root):
        if n.type == "function_definition":
            nm = n.child_by_field_name("name")
            if nm is not None:
                funcs.setdefault(_txt(nm, src), _txt(n, src))
    return funcs


def extract_python(path, text):
    if ".tool" not in text and ".add_tool" not in text and "Tool(" not in text and "inputSchema" not in text and "input_schema" not in text:
        return [], {}
    src = text.encode("utf-8", "ignore")
    root = PY.parse(src).root_node
    consts = _py_consts(root, src)
    funcs = py_functions(root, src)
    fnodes = {}
    for n in _walk(root):
        if n.type == "function_definition" and n.child_by_field_name("name") is not None:
            fnodes.setdefault(_txt(n.child_by_field_name("name"), src), n)
    tools = []
    for n in _walk(root):
        if n.type == "decorated_definition":
            fn = n.child_by_field_name("definition")
            if fn is None or fn.type != "function_definition":
                continue
            for d in n.children:
                if d.type != "decorator":
                    continue
                expr = d.children[-1]
                call = expr if expr.type == "call" else None
                target = call.child_by_field_name("function") if call else expr
                if target is None or not _txt(target, src).endswith(".tool"):
                    continue
                kw, pos = _kwargs(call, src) if call else ({}, [])
                fname = _txt(fn.child_by_field_name("name"), src)
                name = _py_str(kw.get("name"), src, consts) or (_py_str(pos[0], src, consts) if pos else None) or fname
                if "description" in kw:
                    desc = _py_str(kw["description"], src, consts)
                    dyn = desc is None
                    desc = desc or ""
                else:
                    desc, dyn = _py_docstring(fn, src), False
                body = _txt(fn, src)
                tools.append(Tool(name, desc.strip(), path, "py", dyn, body_hash=_h(body),
                                  callees=_body_info(body)))
                tools[-1]._body = body
        elif n.type == "call" and (n.child_by_field_name("function") is not None
                                   and _txt(n.child_by_field_name("function"), src).endswith(".add_tool")):
            # FastMCP imperative form: server.add_tool(fn | wrapper(fn), name=?, description=?)
            kw, pos = _kwargs(n, src)
            if not pos:
                continue
            a = pos[0]
            while a.type == "call":
                _, inner = _kwargs(a, src)
                if not inner:
                    break
                a = inner[0]
            if a.type not in ("identifier", "attribute"):
                continue
            fname = _txt(a, src).split(".")[-1]
            name = _py_str(kw.get("name"), src, consts) or fname
            fnode = fnodes.get(fname)
            if "description" in kw:
                desc = _py_str(kw["description"], src, consts)
                dyn, desc = desc is None, desc or ""
            else:
                desc, dyn = (_py_docstring(fnode, src) if fnode is not None else ""), False
            body = funcs.get(fname, "")
            tools.append(Tool(name, desc.strip(), path, "py", dyn, body_hash=_h(body), callees=_body_info(body)))
            tools[-1]._body = body
        elif n.type == "call":
            f = n.child_by_field_name("function")
            if f is None or _txt(f, src).split(".")[-1] != "Tool":
                continue
            kw, _ = _kwargs(n, src)
            name = _py_str(kw.get("name"), src, consts)
            if not name:
                continue
            desc = _py_str(kw.get("description"), src, consts)
            body = funcs.get(name, "")
            if not body:
                m = re.search(r"(name|tool_name)\s*==\s*['\"]" + re.escape(name) + r"['\"](.*?)(?=\n\s*(el)?if\s|\Z)", text, re.S)
                body = m.group(2) if m else ""
            tools.append(Tool(name, (desc or "").strip(), path, "py", desc is None and "description" in kw,
                              body_hash=_h(body), callees=_body_info(body)))
            tools[-1]._body = body
    have = {t.name for t in tools}
    for n in _walk(root):
        if n.type != "dictionary":
            continue
        kv = {}
        for p in n.children:
            if p.type == "pair":
                k = _py_str(p.child_by_field_name("key"), src, consts)
                if k:
                    kv[k] = p.child_by_field_name("value")
        if "name" in kv and "description" in kv and ("inputSchema" in kv or "input_schema" in kv or "parameters" in kv):
            name = _py_str(kv["name"], src, consts)
            if not name or name in have:
                continue
            desc = _py_str(kv["description"], src, consts)
            body = funcs.get(name, "") or funcs.get("_" + name, "") or funcs.get("handle_" + name, "")
            t = Tool(name, (desc or "").strip(), path, "py", desc is None, body_hash=_h(body), callees=_body_info(body))
            t._body = body
            tools.append(t)
            have.add(name)
    for t in tools:
        if not hasattr(t, "_body"):
            t._body = ""
    return tools, funcs


def _body_info(body):
    return sorted(set(CALL_RE.findall(body)))


# ================================================================== TypeScript / JavaScript
def _ts_str(node, src, consts):
    if node is None:
        return None
    t = node.type
    if t == "string":
        return "".join(_txt(c, src) for c in node.children if c.type in ("string_fragment", "escape_sequence"))
    if t == "template_string":
        if any(c.type == "template_substitution" for c in node.children):
            return None
        return _txt(node, src)[1:-1]
    if t == "binary_expression" and len(node.children) == 3 and _txt(node.children[1], src) == "+":
        a, b = _ts_str(node.children[0], src, consts), _ts_str(node.children[2], src, consts)
        return None if a is None or b is None else a + b
    if t == "parenthesized_expression":
        inner = [c for c in node.children if c.type not in ("(", ")")]
        return _ts_str(inner[0], src, consts) if len(inner) == 1 else None
    if t == "identifier":
        return consts.get(_txt(node, src))
    if t in ("as_expression", "satisfies_expression"):
        return _ts_str(node.children[0], src, consts)
    return None


def _ts_consts(root, src):
    consts = {}
    for n in _walk(root):
        if n.type == "variable_declarator":
            nm, val = n.child_by_field_name("name"), n.child_by_field_name("value")
            if nm is not None and nm.type == "identifier" and val is not None:
                v = _ts_str(val, src, consts)
                if v is not None:
                    consts.setdefault(_txt(nm, src), v)
    return consts


def _obj_prop(obj, key, src):
    if obj is None or obj.type != "object":
        return None
    for p in obj.children:
        if p.type == "pair":
            k = p.child_by_field_name("key")
            if k is not None and _txt(k, src).strip("'\"") == key:
                return p.child_by_field_name("value")
    return None


TOOL_KEYS = ("inputSchema", "input_schema", "schema", "parameters", "handler", "execute", "annotations")


def ts_functions(root, src):
    funcs = {}
    for n in _walk(root):
        if n.type in ("function_declaration", "method_definition"):
            nm = n.child_by_field_name("name")
            if nm is not None:
                funcs.setdefault(_txt(nm, src), _txt(n, src))
        elif n.type == "variable_declarator":
            nm, val = n.child_by_field_name("name"), n.child_by_field_name("value")
            if nm is not None and val is not None and val.type in ("arrow_function", "function_expression", "function"):
                funcs.setdefault(_txt(nm, src), _txt(val, src))
    return funcs


def extract_ts(path, text):
    if "tool" not in text.lower():
        return [], {}
    src = text.encode("utf-8", "ignore")
    root = (TSX if path.endswith((".tsx", ".jsx")) else TS).parse(src).root_node
    consts = _ts_consts(root, src)
    funcs = ts_functions(root, src)
    tools = []
    for n in _walk(root):
        if n.type != "call_expression":
            continue
        f = n.child_by_field_name("function")
        if f is None or f.type != "member_expression":
            continue
        prop = f.child_by_field_name("property")
        meth = _txt(prop, src) if prop is not None else ""
        if meth not in ("tool", "registerTool"):
            continue
        args = [a for a in n.child_by_field_name("arguments").children if a.type not in ("(", ")", ",", "comment")]
        if not args:
            continue
        name = _ts_str(args[0], src, consts)
        if not name:
            continue
        desc, dyn = "", False
        if meth == "tool" and len(args) >= 3:
            d = _ts_str(args[1], src, consts)
            if d is not None:
                desc = d
            elif args[1].type not in ("object",):
                dyn = True
            if args[1].type == "object":  # tool(name, schema, ...) or tool(name, {description})
                dv = _obj_prop(args[1], "description", src)
                if dv is not None:
                    desc = _ts_str(dv, src, consts) or ""
                    dyn = _ts_str(dv, src, consts) is None
        elif meth == "registerTool" and len(args) >= 2:
            dv = _obj_prop(args[1], "description", src)
            if dv is not None:
                d = _ts_str(dv, src, consts)
                desc, dyn = (d or ""), d is None
        body = _txt(n, src)
        t = Tool(name, desc.strip(), path, "ts", dyn, body_hash=_h(body), callees=_body_info(body))
        t._body = body
        tools.append(t)
    have = {t.name for t in tools}
    if True:
        for n in _walk(root):
            if n.type != "object":
                continue
            nv, dv = _obj_prop(n, "name", src), _obj_prop(n, "description", src)
            if nv is None or dv is None or not any(_obj_prop(n, k, src) is not None for k in TOOL_KEYS):
                continue
            if _ts_str(nv, src, consts) in have:
                continue
            name = _ts_str(nv, src, consts)
            if not name:
                continue
            d = _ts_str(dv, src, consts)
            m = re.search(r"case\s+['\"`]" + re.escape(name) + r"['\"`]\s*:(.*?)(?=\bcase\s+['\"`]|default\s*:|\Z)", text, re.S)
            body = m.group(1) if m else funcs.get(name, "")
            if not body:
                for k in ("handler", "execute", "run", "callback"):
                    hv = _obj_prop(n, k, src)
                    if hv is not None:
                        body = _txt(hv, src)
                        break
            t = Tool(name, (d or "").strip(), path, "ts", d is None, body_hash=_h(body), callees=_body_info(body))
            t._body = body
            tools.append(t)
    return tools, funcs


# ================================================================== repo-level
PY_EXT = (".py",)
TS_EXT = (".ts", ".mts", ".cts", ".js", ".mjs", ".cjs", ".tsx", ".jsx")
SKIP_PARTS = {"node_modules", "test", "tests", "__tests__", "spec", "examples", "example",
              "dist", "build", "out", ".venv", "venv", "vendor", "docs", "scripts", "benchmarks",
              "fixtures", "__pycache__", "site-packages", "coverage", "e2e", "bench", "eval", "evals",
              "__mocks__", "mocks"}
BUILD_FILES = {"setup.py", "conftest.py", "noxfile.py", "fabfile.py", "gulpfile.js", "gruntfile.js",
               "jest.config.js", "webpack.config.js", "rollup.config.js", "tsup.config.ts", "vite.config.ts",
               "vitest.config.ts", "eslint.config.js", "babel.config.js", ".eslintrc.js", "prettier.config.js"}


def relevant(path):
    p = path.lower()
    parts = set(p.split("/")[:-1])
    if parts & SKIP_PARTS:
        return False
    base = p.split("/")[-1]
    if p.endswith((".d.ts", ".min.js", ".test.ts", ".spec.ts", ".test.js", ".spec.js", "_test.py")) \
            or base.startswith("test_") or base in BUILD_FILES or re.search(r"\.config\.[cm]?[jt]s$", base):
        return False
    return p.endswith(PY_EXT + TS_EXT)


# A call we follow: a bare call f(...) or self./this./cls. method call. Calls on other objects
# (client.execute(...), db.run(...)) are not followed: their target is unknown statically.
RESOLVE_RE = re.compile(r"(?:(?<![\w.$])|(?<=\bself\.)|(?<=\bthis\.)|(?<=\bcls\.))([A-Za-z_$][\w$]*)\s*\(")
# Names too generic to resolve by name alone.
GENERIC_NAMES = {"run", "execute", "exec", "call", "handle", "handler", "main", "init", "start", "stop", "close",
                 "open", "read", "write", "send", "get", "set", "update", "create", "delete", "remove", "list",
                 "load", "save", "parse", "process", "request", "fetch", "invoke", "apply", "next", "resolve",
                 "reject", "emit", "log", "error", "warn", "info", "debug", "abort", "cancel", "wait", "connect",
                 "query", "search", "build", "render", "format", "validate", "check", "track", "version", "help"}


def _pick_definition(defs, tool_file):
    """Resolve a helper name to one definition: unique name, else the one in the tool's own file,
    else the single one in the tool's package (longest shared directory prefix). Ambiguous -> None."""
    if not defs:
        return None
    if len(defs) == 1:
        return defs[0][1]
    same = [b for f, b in defs if f == tool_file]
    if len(same) == 1:
        return same[0]
    tparts = tool_file.split("/")[:-1]
    def shared(f):
        n = 0
        for a, b in zip(f.split("/")[:-1], tparts):
            if a != b:
                break
            n += 1
        return n
    best = max(shared(f) for f, _ in defs)
    cands = [b for f, b in defs if shared(f) == best]
    return cands[0] if best > 0 and len(cands) == 1 else None


def analyze_tree(files):
    """files: dict path -> text. Returns (tools, server_caps, server_domains)."""
    all_tools, all_funcs, server_text, def_count, defs_by_name = [], {}, [], {}, {}
    for path, text in files.items():
        if len(text) > 400_000:
            continue
        try:
            if path.endswith(PY_EXT):
                tools, funcs = extract_python(path, text)
            elif path.endswith(TS_EXT):
                tools, funcs = extract_ts(path, text)
            else:
                continue
        except Exception:
            continue
        all_tools += tools
        for k, v in funcs.items():
            all_funcs.setdefault(k, v)
            def_count[k] = def_count.get(k, 0) + 1
            defs_by_name.setdefault(k, []).append((path, v))
        server_text.append(text)
    for t in all_tools:
        parts, seen, frontier = [("self", t._body)], set(), [t._body]
        for _ in range(4):
            nxt = []
            for b in frontier:
                for c in RESOLVE_RE.findall(_strip_code(b)):   # calls in code only, not in strings/comments
                    if c in seen or len(seen) >= 150 or c in GENERIC_NAMES:
                        continue
                    body = _pick_definition(defs_by_name.get(c, []), t.file)
                    if body is None:
                        continue
                    seen.add(c)
                    parts.append((c, body))
                    nxt.append(body)
            frontier = nxt
        full = "\n".join(b for _, b in parts)
        t.caps, t.domains = capabilities(full), domains(full)
        t.direct_caps = capabilities(t._body)
        t.caps_via = {}
        for who, b in parts:  # BFS order: nearest source first
            for c in capabilities(b):
                t.caps_via.setdefault(c, who)
        t.callees = []
        del t._body
    blob = "\n".join(server_text)
    return all_tools, capabilities(blob), domains(blob)
