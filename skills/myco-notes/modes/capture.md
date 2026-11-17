# Capture

*Part of the Myco Notes skill: read `SKILL.md` (the folder above) first for `<KIT>`, `<notes>`, `<tools>` and the guard rails, which always apply.*

**When:** A change was just made to the system or codebase, and the notes must follow.

1. Read `AGENTS.md`, `<notes>/working-agreement.md`, `<notes>/sync-tracker.md` (pending list and the "what to update when X changes" matrix).
2. **Verify the live system** (query it; do not rely on memory or on a script's own "ok").
3. **Read each file immediately before editing it**, then edit in place. Never regenerate a whole file.
4. Update the notes the matrix names (a note with a freshness header, method section 10.1: move `last_confirmed` and `review_after` only after you verified it live): master record (`state.md`: inventory/current state and a dated changelog entry), `runbook.md` (a "How do I ...?" entry and, for mistakes, a lesson), entity note, plan/backlog, verification guide. Entry formats are in `docs/METHODOLOGY.md` section 4: why, what changed with exact names/paths/ids/versions, backup and undo, how it was tested with numbers, mistakes and lessons, follow-ups. A new note starts with a header holding a one-line `summary:` (what it holds and when to read it, at most 200 characters, method 10.1); change a note's summary when its scope changes.
5. Copy every new or changed deployed file into `<notes>/scripts/` (bundles get a README).
6. Run `<tools>/notes-lint.py`; fix errors and relevant warnings.
7. Add ONE line at the top of the sync log in `sync-tracker.md` (before the commit, so it goes into the same commit), in the form `- **YYYY-MM-DD kind:** what was updated; what was NOT and why` with kind `change`, `note`, `answer`, `review`, `audit`, `import`, `merge`, `upgrade`, `setup` or `drill` (method 4; the lint checks the newest line), move the last-synced date of each ledger target really updated, and write anything not done under Pending (never mark a copy synced if it was not).
8. Commit: `<tools>/notes-commit "what changed and why"` (one logical change per commit; commit after every update big enough to matter, before ending the turn). **If it exits with code 3** it found a new folder or loose file in the repository root and committed nothing: show the owner its report, ask what to do with each item (`add`, `ignorelint`, `ignoreall` or `later`, explained in the report), never choose for them, then run it again with `--folder NAME=MODE` for each (see `NEW_FOLDERS` in `<KIT>/docs/REFERENCE.md`). When the working tree holds changes that are not part of this update, commit only yours with `--only PATH` (repeatable); `--dry-run` shows what would be committed.
9. Mirror/push and rebuild views if configured (`notes-commit -p`, `<tools>/build-notes-map.py`, which also writes the mycelium view `<map>/graph.html`: the notes as a network with a timeline that replays the git history; point the owner to it when they ask to see how the notes connect or grew).
10. Report in two layers: short steps while working; at the end a brief summary (what was done, how verified, what the owner must do).
