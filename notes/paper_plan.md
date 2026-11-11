# Paper plan: "Your MCP Server Changed and Didn't Tell You: Measuring Post-Approval Drift"

IEEE S&P 2027 cycle 2, submission #2511. Final PDF due Wed Nov 18, 4:59 AM PST (upload a draft by Mon Nov 16).
Format: IEEE compsoc (`\documentclass[conference,compsoc]{IEEEtran}`), US Letter, 13 pages + 5 pages refs/appendix, anonymous.

## 1. Direction (one paragraph every section serves)
MCP tools are approved once, from their name and description, but servers keep changing afterwards.
Measured over 35,725 sampled versions of 2,571 servers, descriptions change often, code-level capabilities
change silently, most changes are benign, and the rare risky ones are buried in routine churn.
Re-approving on every update overwhelms users; re-approving on description changes misses silent capability
gains. Approval must follow what the code can do (and where data goes), not what the description says.

## 2. Structure (13 pages)
| # | Section | Pages | Content | Key element |
|---|---|---|---|---|
| 1 | Introduction | 1.5 | Problem (approve-once), real incident (postmark-mcp), gap (all prior work = snapshots), our study, numbered findings, contributions list | Fig. 1 |
| 2 | Background & threat model | 1 | MCP tools/descriptions/approval; what clients show; three drift scenarios: benign evolution, compromised maintainer, malicious maintainer; what is in/out of scope (agent misalignment out) | |
| 3 | Methodology | 2 | Crawl & filtering funnel; version selection; tool extraction (tree-sitter); capability detection (6 classes, provenance self/helper); diffing; disclosure check; validation design (sampling strata, blind human labels, code maps); limitations up front | Fig. 2, Table 1 |
| 4 | RQ1 Prevalence | 1.5 | How many servers/versions change: descriptions, tools added, capabilities gained (by class), new domains/deps; per-version and per-year rates; time to first silent high-risk gain | Fig. 3, Fig. 5 |
| 5 | RQ2 Visibility | 1.5 | Silent vs vague vs specific disclosure per capability; README/changelog; MCP annotations vs reality (readOnlyHint etc.) | Fig. 4 |
| 6 | RQ3 Validation & risk | 1.5 | Human labels: extraction error / benign / security-relevant per stratum; scanner precision; map accuracy vs human; what security-relevant changes look like | Table 2 |
| 7 | Case studies | 1 | ctx_upgrade (agent-mediated execution), swarmvault query_graph (description contradicts code), sidecar (output imitates `<system-reminder>`); hidden Unicode virtually absent | Table 3 |
| 8 | RQ4 Re-approval policies | 1.5 | Simulate 5-6 client policies on real histories: prompts/server/year vs share of security-relevant changes caught | Fig. 6 (key figure) |
| 9 | Discussion | 1 | Recommendations for clients, MCP spec, developers, registries; capability + data-destination labels (the "same power, new use" problem, e.g. postmark-mcp); limitations; future work | |
| 10 | Related work | 0.5 | MCP security measurement; MCP attacks; agent skills ecosystem; software supply chain; permission systems & warning fatigue | Table 4 (optional) |
| A | Appendix | ≤5 incl. refs | Ethics, GenAI use, open science/artifact, extra tables, labeling guide | |

## 3. Figures and tables
| ID | What | Type | Data source |
|---|---|---|---|
| Fig. 1 | Motivating timeline: a tool approved at v1, silently gains capability at vN, user never re-asked (use a real anonymised-pattern example) | Diagram (TikZ / draw.io) | case study |
| Fig. 2 | Pipeline: crawl → versions → extract → detect → diff → validate → simulate | Diagram | method |
| Table 1 | Dataset funnel 4,812 → 3,508 → 2,571; versions; median versions/server; tools | Table | repo_summary.csv |
| Fig. 3 | Share of servers with each change type, split by capability class | Horizontal bar | events.jsonl |
| Fig. 4 | Disclosure of capability gains (silent / vague / specific) per capability | 100% stacked bar | events + disclosure analysis |
| Fig. 5 | Time from first tool-bearing release to first silent high-risk gain (CDF) | CDF line | events + snapshot times |
| Table 2 | Validation: labels per stratum, scanner precision, human-vs-map agreement (kappa) | Table | labels_v2 + maps |
| Table 3 | Case studies: server type, change, why it matters, disclosure status | Table | notes |
| Fig. 6 | Policy trade-off: prompts/server/year (x, log) vs % security-relevant changes caught (y), one point per policy | Scatter | simulation + labels |
| Table 4 | Related work comparison: data size, languages, time dimension, validation | Table | related_work.md |

Figure rules: vector PDF; single column = 3.5 in wide, double = 7.16 in; font ≥ 7 pt matching the paper;
colour-blind-safe palette, also distinguishable in greyscale; every axis labelled with units; denominators in captions;
every figure produced by one script (`src/figures.py`) from committed data so results are reproducible.

## 4. Tools
- Writing: Overleaf (IEEE "Demo Template for Computer Society Conferences"), shared link for the author.
- Plots: Python matplotlib (+ pandas), saved as PDF; `src/figures.py`.
- Diagrams: TikZ in LaTeX, or draw.io exported to PDF.
- References: BibTeX; take entries from DBLP / arXiv / ACM DL, not typed by hand.
- Artifact: anonymised repository (Anonymous GitHub) linked in the paper.

## 5. References still needed (verify each before citing)
MCP: MCP specification (tools, annotations); DCIChecker (2606.04769); MCPDiFF (2602.03580); MCP-FSD (2610.22301);
MCPZoo / Rethinking MCP Security (2607.11086); Unicode TAG / approval-view fidelity (2607.05744); TrustShiftProbe
(2608.23763); ETDI (2506.01333); AgentBound (2510.21236); Guo et al. MCP ecosystem (2509.25292); MCP-SafetyBench
(2512.15163); secure tool manifests (2601.23132); "Parasites in the Toolchain" (S&P 2026).
Skills: Skill Constellations (2610.11169); Agent Skill Evolution (2610.04832).
Incidents: postmark-mcp (Koi Security, Sep 2025); Invariant Labs tool poisoning / rug pull (2025); Cursor MCPoison advisory.
Supply chain: Zimmermann et al., npm ecosystem (USENIX Sec 2019); Ladisa et al., SoK OSS supply chain attacks (S&P 2023);
Ohm et al., Backstabber's Knife Collection (DIMVA 2020).
Permissions & fatigue: Felt et al., Android permissions (SOUPS 2012); Akhawe & Felt, Alice in Warningland (USENIX Sec 2013);
a study of permission changes across app/extension updates (to find).
Agents/LLM: Greshake et al., indirect prompt injection (2023); OWASP Top 10 for LLM Applications (excessive agency).
Method/ethics: Paxson, sound Internet measurement (IMC 2004); Menlo Report; Cohen's kappa.

## 6. Language and style
- Plain, precise, confident but measured. "We find", "we measure", "our results suggest". No hype words
  ("alarming", "devastating", "catastrophic"), no "novel" more than once.
- Every number has its denominator: "1,687 of 2,571 servers (65.6%)".
- Define each term once and never vary it: *post-approval drift*, *capability*, *silent gain*, *disclosure*,
  *security-relevant*. Add a short terminology box in Section 3.
- Separate what the code shows from what happens at runtime: "the code establishes a path by which…;
  we did not observe…".
- Do not attribute intent to maintainers; most changes are benign.
- Each results section opens with the question and closes with a one-sentence boxed **Finding N**.
- Present tense for findings ("servers change"), past tense for what we did ("we cloned").
- Anonymity: no names, no Rapticore, no GitHub username; cite own work in third person; artifact via Anonymous GitHub.

## 6b. Sound human and sharp (assume a strict, well-prompted AI reviewer)
What makes text read as machine-written, and what we do instead:
| Avoid | Do instead |
|---|---|
| "plays a crucial role", "in today's rapidly evolving landscape", "it is worth noting", "delve", "leverage", "robust", "seamless", "comprehensive", "pivotal", "underscore" | Say the thing. "Agents now send email and run shell commands on users' behalf." |
| Every paragraph = claim + three bullet points + summary | Prose with one point per paragraph; bullets only for genuine lists |
| Lists of exactly three adjectives or examples | As many as the evidence has |
| "Not only X, but also Y"; "X, not Y"; em-dash asides; colon reveals | Two plain sentences |
| Claims without numbers ("many servers", "significant") | "1,687 of 2,571 servers (65.6%)" |
| Hedging everything / overclaiming everything | Hedge exactly where the evidence is weak, and say why |
| Generic examples ("e.g., a malicious tool") | Real ones from our data (ctx_upgrade, query_graph, sidecar) with file-level detail |
| Summaries that repeat the section | End with one boxed Finding that adds the "so what" |
| Perfect symmetry and smooth transitions everywhere | Vary sentence length; short sentences for key results |

What a strict reviewer model also checks, so we make it easy to verify:
- every abstract claim has a section, number, and figure behind it;
- the method is reproducible from the text alone (thresholds, sample sizes, versions, dates);
- limitations are specific (what we cannot see and how it biases the numbers), not generic;
- related work is cited precisely and fairly, with the exact difference stated;
- no claim stronger than the data (static analysis shows a path exists, not that it ran).

Process: Claude drafts each section; Soniya rewrites it in her own words and cuts anything she
cannot explain or defend aloud. Final read-aloud pass before submission.

## 7. Writing order
1. Methodology (stable now) → 2. Results RQ1–RQ4 as numbers freeze → 3. Case studies → 4. Discussion →
5. Introduction (written last, from the findings) → 6. Related work → 7. Appendix → 8. Proofread against the abstract
(every abstract claim must be supported in the paper).
