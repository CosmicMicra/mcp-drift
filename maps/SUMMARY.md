| item | reachable | # obs | highest-confidence observation |
|---|---|---|---|
| e-1 | yes | 3 | Flag reflects reading two non-secret filter env vars (high) |
| e-51 | no via named helper (fs_write via another pre-existing path) | 3 | Scanner helper is not on the MCP path (high) |
| e-81 | yes | 3 | A simple undo/redo tool now does network discovery and keeps a background stream open (high) |
| e-111 | yes | 3 | New file writes are a temp log used only for output encoding (high) |
| e-161 | n/a (desc) | 4 | The description change only documents an existing parameter (high) |
| e-2 | yes | 3 | No functional change; the flag comes from a file move or refactor (high) |
| e-52 | no | 2 | The scanner matched `execute` to a SQL call, not a shell call (high) |
| e-82 | no | 3 | Scanner name collision: `run` is a callback parameter (high) |
| e-112 | no | 1 | The "new fs_read" is in build and test configuration, and runtime file access was removed (high) |
| e-162 | n/a (desc) | 2 | The description change is explanatory, with no steering (high) |
| e-3 | yes | 4 | Env-secret read already existed; it only moved and was renamed (high) |
| e-53 | yes | 4 | File writing existed before; the new voice-track feature adds more writes of the same kind (high) |
| e-83 | yes | 4 | The `fs_write` is the creation of the server's own SQLite store (high) |
| e-113 | yes | 4 | Positive: the native-messaging host files are no longer written (high) |
| e-163 | n/a (desc) | 4 | The description contains explicit anti-injection guidance (high) |
| e-4 | yes | 4 | The flagged env read is a non-secret tuning variable (high) |
| e-54 | yes | 4 | The new write is the server's own onboarding-state file (high) |
| e-84 | yes | 2 | No new capability for this tool; the account-file read predates this range (high) |
| e-114 | no | 4 | The `dynamic_code` flag is a constant `__import__("math")` (high) |
| e-164 | n/a (desc) | 2 | The description now discloses side effects that the old 3-word text hid (high) |
| e-5 | no | 3 | The tool description orders the AI to run a server-provided shell command (high) |
| e-55 | no | 2 | The scanner likely followed `abort()` to the wrong class (high) |
| e-85 | yes | 4 | The flagged helper only creates Kiln's own default download folder (high) |
| e-115 | no | 3 | Credential code was added but is not wired to any MCP tool yet (high) |
| e-165 | n/a (desc) | 2 | Tool-selection steering ("ALWAYS" / "Do NOT grep") (high) |
| e-6 | yes | 4 | The env read is a feature flag, not a secret (high) |
| e-56 | yes | 4 | Debug mode logs key prefixes (high) |
| e-86 | yes | 2 | The scanner pointed at a validation helper; network use predates the change (high) |
| e-116 | no (CLI only) | 2 | New network code goes only to Wikidata and is not wired to MCP tools (high) |
| e-166 | n/a (desc) | 2 | A description was added where none existed; it limits the tool's use (high) |
| e-7 | yes | 3 | Delete scope widened from three resource types to any resource kubectl knows (high) |
| e-57 | yes | 2 | No change on this tool's path; the flag comes from unchanged session-management code (high) |
| e-87 | yes | 3 | New read is the server's own token cache (high) |
| e-117 | yes | 2 | The new fs_read is the server reading its own package.json for its version (high) |
| e-167 | n/a (desc) | 1 | Minor clarifying edit; no steering (high) |
| e-8 | yes | 4 | Error paths dump the whole context, including the Atlassian API token, to logs (high) |
| e-58 | no | 2 | The scanner followed a helper that this tool does not call (high) |
| e-88 | no | 2 | The scanner attributed an eval-harness helper to a server tool (high) |
| e-118 | no (CLI only) | 3 | New shell execution is a self-check in the CLI setup command, not in the MCP server (high) |
| e-168 | n/a (desc) | 3 | The description expanded into full docs, with credential references rather than secrets (high) |
| e-9 | yes | 4 | Every render now leaves a file in the temp directory that is never cleaned up (high) |
| e-59 | no | 1 | False positive: an eval-harness helper was attributed to a server tool (high) |
| e-89 | no | 3 | The helper named by the scanner belongs to a different subsystem (high) |
| e-119 | no | 2 | The `dynamic_code` flag comes from a constant `__import__("gomaa")` (high) |
| e-169 | n/a (desc) | 1 | The forcing language was reduced, not added (high) |
| e-10 | yes | 3 | Arbitrary-path file overwrite controlled by the AI (high) |
| e-60 | yes | 3 | First call may download a ~1.8 GB model from Hugging Face (high) |
| e-90 | yes | 1 | No change on this tool's path (high) |
| e-120 | yes | 3 | The env read is `LOCALAPPDATA` (a path, not a secret) (high) |
| e-170 | n/a (desc) | 1 | "ALWAYS use this tool first" steers toward the server's own docs for CLI syntax (high) |
| e-11 | yes | 3 | File writes are confined to a temporary directory and predate this change (high) |
| e-61 | yes | 3 | Inlining refactor; no behaviour change (high) |
| e-91 | yes | 2 | No change on this tool's path; the network call is pre-existing (high) |
| e-121 | yes (constant imports only) | 4 | "Dynamic code" here means constant-path ES module imports (high) |
| e-171 | n/a (desc) | 2 | The description was shortened and directive language reduced overall (high) |
| e-12 | yes | 5 | The env reads are device credentials used for their documented purpose (high) |
| e-62 | yes | 2 | The credential env reads predate this change; the only new env var is a JWT TTL (high) |
| e-92 | no | 2 | False positive: `track` is HTTP-transport bookkeeping (high) |
| e-122 | no | 1 | The new network code is in the browser renderer, not the MCP server (high) |
| e-172 | n/a (desc) | 2 | The "description change" is a name collision across two servers in a monorepo (high) |
| e-13 | yes | 3 | No change to this tool; the write and code-execution capability predate this change (high) |
| e-63 | no | 3 | The env-credential helper is not on `order_send`'s path (high) |
| e-93 | yes | 2 | Bug fix only: the POST now sends an empty JSON body (high) |
| e-123 | yes | 3 | The new page fetch bypasses the configured proxy (high) |
| e-173 | n/a (desc) | 2 | The description change documents a new security gate (high) |
| e-14 | yes | 3 | MinIO secret key read from env and used for auth (high) |
| e-64 | yes | 3 | No change on this tool's path; the auto-launch predates this change (high) |
| e-94 | yes | 3 | New OIDC token exchange using the caller's bearer token (high) |
| e-124 | yes | 3 | New always-on audit log written to the current directory by default (high) |
| e-174 | n/a (desc) | 2 | The description adds ID-scoping guidance between sibling tools (high) |
| e-15 | yes | 3 | Tenant binding fix (high) |
| e-65 | yes | 3 | The file-based IPC write already existed; the change makes it atomic (high) |
| e-95 | no | 2 | False positive: the `version()` helper is in the CLI package (high) |
| e-125 | yes | 3 | New: an agent can execute arbitrary Python in the user's live session (high) |
| e-175 | n/a (desc) | 2 | The description now discloses output redaction and warns against re-publishing (high) |
| e-16 | yes | 2 | The token is reported only as set/unset; other env values are non-secret (high) |
| e-66 | yes | 1 | No change on this tool's path; the credential read predates this change (high) |
| e-96 | yes | 1 | Network reach shrank: anonymous mode now refuses this tool locally (high) |
| e-126 | no | 2 | False positive: the `shell` gain is a developer-only marketing script (high) |
| e-176 | n/a (desc) | 2 | The "forcing" text is argument-format guidance (high) |
