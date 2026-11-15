# The daily run is a local Desktop scheduled task that hands JSON over through an inbox

The daily run needs the investor's Depot in `~/.financial-support/` (ADR 0004), so it runs as a local scheduled task in the Claude desktop app, not as a cloud routine, which would need the Depot in a repo. The investor accepts that the run only starts while the Mac is awake and the app is open. The phone notification comes from the Claude app's "Scheduled tasks" notification.

Nobody is there to approve prompts, and Claude Code blocks shell commands that contain `{"`, so JSON can't be passed on the command line or in a heredoc. Instead the agent writes each JSON to `<data dir>/inbox/` and passes it with `--input`. The script deletes the file after a successful save. Writing is allowed only in the inbox. The Depot, the Theses and the Investor Profile are read-only for the run.
