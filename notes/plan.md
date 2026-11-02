# Plan to IEEE S&P 2027 cycle 2

Deadlines (verify on https://sp2027.ieee-security.org/cfpapers.html):
- Abstract registration: Nov 10, 2026, 23:59 AoE
- Full paper: Nov 17, 2026, 23:59 AoE

## Working title
Trusted Once, Changed Later: A Longitudinal Study of Post-Approval Drift in MCP Servers

## Research questions
- RQ1 Prevalence: how often do MCP servers gain capabilities (shell, dynamic code, file writes,
  secrets/env access, network, new external domains) after their first tool-bearing release?
- RQ2 Disclosure: how often is that gain silent, i.e. tool descriptions, tool list and README are unchanged?
- RQ3 Description mutation: how often do approved tools' descriptions change, and how often does the change add
  instruction-like or hidden content (the rug-pull surface)?
- RQ4 Detection (if time): can a diff-only detector flag security-relevant undisclosed changes?

## Status
- [x] Literature check (notes/related_work.md)
- [x] Crawl: 4,812 repos tagged mcp-server / model-context-protocol / mcp-servers with >= 20 stars
- [x] Extractor (tree-sitter; Python + TS/JS; decorators, registerTool, tool(), Tool(), object/dict literals)
- [ ] History extraction over 3,508 Python/TS/JS repos (running)
- [ ] Extractor recall/precision check on a hand-labelled sample (YOU)
- [ ] Manual validation of ~200 drift events (YOU)
- [ ] Figures + paper

## Known limitations (write these into the paper)
- Static, regex-based capability signals; capabilities inside third-party libraries are invisible.
- Tool-level capabilities use a name-resolved call graph (depth 4); server-level signals are the robust unit.
- Version = release tag when >= 3 tags, else up to 12 time-spaced commits; HEAD always included.
- Only default-branch, first-parent history; npm/PyPI published artifacts may differ from git.
- Large monorepos (> 600 source files at HEAD) excluded: not dedicated MCP servers.
