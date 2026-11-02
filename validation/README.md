# How to label (about 3-4 hours total)

## drift_events.csv (~200 rows)
Open `compare_url`, search the diff for the capability (e.g. `subprocess`, `exec`, `writeFile`, `process.env`).
`via` says where the extractor found it: `self` = the tool's own handler, otherwise a helper function name.

Label column, one of:
- **extraction_error**: the capability was not really added to this tool (wrong function matched, code moved
  between files, the tool was renamed, a refactor only).
- **benign**: really added, but routine and not security-relevant (e.g. reading a config env var for a port,
  writing a log/cache file, a helper that shells out to `xdotool` for cursor position).
- **security_relevant**: really added and a user who approved the old version would plausibly want to know
  (new shell/exec of user input, writes outside a sandbox, reads of credentials/tokens, new upload/exfil endpoint,
  for descriptions: hidden or instruction-like text that steers the agent toward other tools or data).
- **unsure**

For `suspicious_desc` rows, judge the new description text: most "always call X first" text is ordinary
agent-steering (label benign); label security_relevant only if it pushes toward data/tools outside the tool's purpose
or hides content.

## extractor_tools.csv (60 rows)
Open `file_url`. Is it a real MCP tool definition (y/n)? Is the description what the client would see (y/n)?
Any obvious capability the handler has that `caps` misses? Write it in `missed caps`.

Do the first 20 rows of each file, then message me; I'll check agreement with my own labels before you do the rest.
