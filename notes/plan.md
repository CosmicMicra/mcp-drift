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
- [x] History extraction over 3,508 Python/TS/JS repos (v2 extractor; 2,571 analyzable, 35,725 versions)
- [ ] Extractor recall/precision check on a hand-labelled sample (YOU)
- [ ] Manual validation of ~200 drift events (YOU)
- [ ] Figures + paper

## Known limitations (write these into the paper)
- Static, regex-based capability signals; capabilities inside third-party libraries are invisible.
- Tool-level capabilities use a name-resolved call graph (depth 4); server-level signals are the robust unit.
- Version = release tag when >= 3 tags, else up to 12 time-spaced commits; HEAD always included.
- Only default-branch, first-parent history; npm/PyPI published artifacts may differ from git.
- Large monorepos (> 600 source files at HEAD) excluded: not dedicated MCP servers.

## First full results (v2 extractor, UNVALIDATED; 2,571 servers, 35,725 versions)
- Silent high-risk tool capability gain: 15.6% of servers (any path); 2.1% in the tool's own handler.
- Silent server-level high-risk gain (no tool/description/README change): 3.6%.
- Tool description changed after first release: 65.6% of servers.
- "Suspicious" description changes: 8.1% of servers, but manual read of all 14 concealment/zero-width hits: all benign
  agent-steering. No evidence so far of malicious description rug pulls. Keyword markers cannot separate steering from injection.
- TODO for paper: per-repo rates grow with number of versions; also report per-step and per-year rates.

## Scope decision (Nov 7): measurement + policy simulation; attack-planting experiment = future work

## Preliminary policy simulation (1,667 servers with >= 3 months history; per server per year; UNVALIDATED)
- Re-prompt on any sampled update: median 15.7/yr (lower bound: we sample at most 40 tags / 12 commits)
- On description change or new tool: median 4.1/yr; 86% of servers would prompt at least once
- On description change only: median 2.4/yr; 73%
- On any capability gain: median 1.4/yr; 63%
- On high-risk capability gain: median 0.7/yr; 53%
- On high-risk gain in a tool's own code: mean 0.1/yr; 6%
- 700 steps with silent high-risk gains (description unchanged): a description-change rule misses all of them by construction
- Claude's 20 labels: 5 extraction errors, 14 benign, 1 unsure, 0 security-relevant (validation/claude_labels_first20.json)

## Agent-mediated execution (Nov 7)
Description scan (src/agent_exec.py, all versions): 40 matching repo/tool pairs in 26 repos; manual classification:
- AI told to run something in its own shell: 5 clear repos (context-mode ctx_upgrade/ctx_doctor "You MUST run the
  returned command using your shell tool"; sidecar "ALWAYS run `sleep 25` in your shell" (added v0.4.2);
  ui-beats "Run the returned command in the project root" (npm install); memi "Run npm install ...") + 2 borderline
  (gdharness, added v1.3.8; gemini-cloud-assist routes gcloud to the agent's shell tool)
- ask the human: 4; tool executes itself: 7; "use this tool instead of the terminal": 3 repos; false matches: 6
=> in descriptions this is rare (~0.2-0.3% of 2,571 servers). Next: scan tool OUTPUT strings in code (src/agent_exec_code.py, HEAD only).
Output-string scan (src/agent_exec_code.py, latest code of 2,563 servers): raw matches in 378 repos, but a random
sample of 45 was almost entirely human-directed (CLI help, error messages, web UI, comments). Filtering for
AI-addressed cues left 88 repos; reading all of them:
- clear AI-directed execution in tool output: jrenaldi79/sidecar ("<system-reminder>IMPORTANT: ... you MUST run
  `sleep 25` in your shell first" - output imitates the client's system-reminder tag), INSANE0777/Awwwards-mcp
  ("... then run npm install && npm run build yourself"); context-mode historically (v1.0.58 output).
- opposite convention (developers routing commands to the human on purpose): surendranb google-analytics-mcp and
  google-search-console-mcp ("Inform the user to run '{cmd}' ... Do NOT attempt to run this command yourself"),
  cheap-ag ("never approve yourself"), FlowState, perp-cli, marm-memory, artokun, ScientificFigureLibrary
  ("Run it yourself in a terminal").
- the rest: human-facing setup text.
=> Agent-mediated execution is RARE (a handful of servers). Paper: short case-study subsection, incl. the
   system-reminder imitation and the lack of any convention. Stop exploring here.

## Case study candidate (found by Soniya while labelling e-51; verified by Claude in code, Nov 8)
swarmclawai/swarmvault v0.1.20 adds MCP tool query_graph, description: "Traverse the local graph from search seeds
without calling a model provider." Handler -> queryGraphVault -> ensureCompiledGraph: if the search DB or graph file
is missing it calls compileVault(), which gets getProviderForTask("compileProvider") and analyses sources lacking
analyses. With a remote provider configured, a "no provider" lookup can send document text to that provider.
Not observed live; code path only. Description-code mismatch in a newly added tool (DCI-style), not post-approval drift.

## Extractor v3 results (Nov 11; final population, pinned versions)
Population fixed to the registered 2,571 servers / 35,725 sampled versions (PIN_DIR re-extraction of the same
commits; 7 repos deleted after collection keep their first-run extraction, see data/deleted_repos.txt).
4 servers have no comparable tools under v3: their only "tools" were eval/bench fixtures -> 2,567 servers yield events.
| Measure (share of servers) | v2 | v3 |
|---|---|---|
| any tool capability gain | 25.9% | 19.5% |
| silent tool capability gain | 19.8% | 13.9% |
| silent high-risk tool gain | 15.6% | 11.0% |
| silent high-risk gain in tool's own handler | 2.1% | 2.1% |
| tool description changed | 65.6% | 65.7% |
| silent server-level high-risk gain | 3.6% | 3.5% |
| dynamic_code gain events | 845 | 37 |
Policy simulation (median prompts/server/year): every update 15.7; desc or new tool 4.1; any description 2.4;
any capability 1.2; high-risk capability 0.6. Per-tool description rule surfaces 0% of silent high-risk gains;
server-wide description rule surfaces 54% by coincidence. Coverage axis still circular -> replace with human labels.
