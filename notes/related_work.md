# Related work and positioning (checked 2 Nov 2026 via alphaXiv full text)

## Closest work and how we differ

| Paper | What it does | Time dimension? | Gap we fill |
|---|---|---|---|
| DCIChecker, arXiv 2606.04769 (Fudan, Jun 2026) | Description-code inconsistency in 2,214 Python MCP servers, 19,200 tools; 9.93% of tools / 35% of servers inconsistent; static + LLM (Direct-Reverse-Arbitration) | **Single snapshot.** Names "stale documentation or feature drift" as a cause but never measures it | We measure *when* inconsistencies appear: post-release capability gains with unchanged descriptions |
| MCPDiFF, arXiv 2602.03580 (Feb 2026) | Static check of declared vs implemented behavior, 10,240 servers | Single snapshot | Same as above |
| MCP-FSD, arXiv 2610.22301 (Oct 2026) | Filesystem capability laundering; 21,097 servers, 16.4% of triaged have FS capability despite non-FS category; dynamic 3-case validation; 13 advisories, 2 CVEs | Single snapshot | Ours is longitudinal; their per-tool least-privilege boundary could be checked per version |
| Unicode TAG-block / approval-view fidelity, arXiv 2607.05744 (Jul 2026) | 8 techniques against real MCP client/server; **0/8 force re-approval**, incl. T3 rug-pull | Synthetic rug pull; states "true prevalence of any of the eight techniques in the wild is not something this measurement design can estimate" | We estimate in-the-wild prevalence of post-approval definition/behavior change |
| TrustShiftProbe, arXiv 2608.23763 (Aug 2026) | Temporally staged *runtime* defection (benign then malicious after N calls); 360 synthetic tasks; SHIELD defense; 69.5% → 42.7% ASR | Runtime, synthetic servers | We study *release-level* changes in real servers' code and metadata. They cite postmark-mcp (15 clean versions, then exfiltration) as motivation; we quantify how common capability changes after release are |
| MCPZoo / Rethinking MCP Security, arXiv 2607.11086 (Jul 2026) | 64,611 servers, 37,288 runnable; scanners flag 96.89% risky, <50% true positives | Snapshot | Scanner unreliability motivates validated, diff-focused signals |
| ETDI, arXiv 2506.01333 | OAuth-enhanced tool definitions vs. rug pull / tool squatting | Defense proposal | Our data quantifies how often signed-definition re-approval would trigger |
| Skill Constellations, arXiv 2610.11169 (Oct 2026) | Dated copy network of agent skills (2.19M adoptions); copies gain command execution via adopted versions; 20.9% of copies follow source edits | Longitudinal, **skills only** | We do the longitudinal security analysis for **MCP servers** |
| Agent Skill Evolution, arXiv 2610.04832 (Oct 2026) | Revisions of 3,159 SKILL.md files and effect on agents | Longitudinal, skills, effectiveness not security | MCP servers, security |
| AgentBound, arXiv 2510.21236 | Android-style permission manifests for MCP servers, AgentManifestGen | Snapshot | Manifests are approved once; we show how often they would go stale |
| Parasites in the Toolchain, IEEE S&P 2026 | Large-scale analysis of attacks on the MCP ecosystem | — | Shows S&P accepts MCP ecosystem measurement |

## One-sentence positioning
Prior MCP security measurement treats each server as a fixed artifact and each approval as permanent;
we provide the first longitudinal measurement of how MCP servers' capabilities and tool descriptions change
after release, i.e. after users and clients have already approved them.

## Motivating incidents
- postmark-mcp (Sep 2025): clean across 15 versions, then an update BCC'd all mail to the attacker (Koi Security).
- CVE-2025-54136 "MCPoison" (Cursor): approved MCP config re-used after mutation.
- Unit 42 / ClawHub: skill passed audit until mid-May 2026 then changed (skills, not MCP).

## Still to read before submission
- MCP-SafetyBench rug-pull scenario (arXiv 2512.15163)
- Guo et al. MCP ecosystem measurement (arXiv 2509.25292) - dataset reused by DCIChecker
- "Parasites in the Toolchain" (S&P 2026) - check for any versioning analysis
- Secure tool manifest and signing (arXiv 2601.23132)
