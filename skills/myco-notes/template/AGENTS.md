# {{PROJECT_NAME}}: start here (entry point for humans and AI agents)

This repository holds the **notes** of {{PROJECT_NAME}}: the single source of truth for its current state, procedures, decisions and lessons. Read this file first, in any session, from any starting folder.

> Claude Code reads `CLAUDE.md`; Codex and many other agents read `AGENTS.md`. Keep this file as the real content and make `CLAUDE.md` contain only the line `@AGENTS.md` (or a symlink). If your agent looks for another filename, make that file a one-line pointer to this one (the exact syntax depends on the agent). Keep this file small: some agents cap the instructions they load (Codex: 32 KiB in total).

## Read order (about five files)
1. `{{NOTES_DIR}}/working-agreement.md` : how to work here (approvals, safety rules, things never to do).
2. `{{NOTES_DIR}}/sync-tracker.md` : what is pending, what is stale, which copies are behind, the "what to update when X changes" matrix.
3. `{{NOTES_DIR}}/state.md` : the master record (headline facts, open items).
4. `{{NOTES_DIR}}/runbook.md` : the how-to for the task at hand, and the lessons list.
5. The entity note or newest handoff for what you will touch (`{{NOTES_DIR}}/*.md`, `{{NOTES_DIR}}/plans/`).

## The five rules that must never be missed
1. **Verify the live system before writing a fact; read a file just before you edit it** (never rewrite a file from memory).
2. **Update the notes in the same session as the change**, using the matrix in the tracker, then commit: `{{TOOLS_DIR}}/notes-commit "what changed and why"`. Commit after every update that is big enough to matter.
3. **No secrets in this repository, ever.** Write where a secret lives, never its value. The commit hook will refuse obvious cases; do not rely on it.
4. **Ask before changing anything the owner has not asked for; an explicit request is approval for that change. Deleting and publishing always need a per-item yes.** Say how to undo it, and keep a backup or a commit to return to.
5. **Be honest in the notes**: date everything ({{TIMEZONE}}), mark what is not verified, and never mark a copy "synced" that was not. Put what is still pending in the tracker.

## Quick notes (a thought to keep, typed or dictated)
When the owner just wants something remembered ("note that…", "remember…", a voice memo), do not run the full update: save it as one entry in this month's inbox with `{{TOOLS_DIR}}/capture --commit "the note"` (add `--title`, `--tag`, `--related NOTE` when obvious), reply in one line ("Saved: <title>"), ask nothing. Sorting the inbox into the notes is a separate step, when asked. Format: `{{NOTES_DIR}}/inbox/README.md`.
Working through pull requests (a cloud session, a branch per change; experimental, method section 19): push and open the pull request; if `SOLO=1` in `.myco-notes.conf`, squash-merge it yourself once its check passes, then continue from the updated main branch; if the check fails, say why and stop. Reply "Saved" without waiting for a slow check; if `notes-commit` exits 5 because the GitHub CLI cannot reach GitHub, use your own GitHub tools. With `SOLO=0` a human merges.

## Questions and reviews
- **A question about the project:** run `{{TOOLS_DIR}}/index` (every note with its one-line summary) and open the notes it points to. If the answer took several notes, a live check or research, offer in one line to keep it as a note (and where); save it only on a yes.
- **"Review the notes":** write the findings with ready-to-apply fixes to `{{NOTES_DIR}}/plans/review-<date>.md` and change no note yet; the owner answers per number (yes, no, or a change). Apply only the accepted fixes exactly as shown; a changed fix is shown again before it is applied; declined ones are recorded and not proposed again (method section 21).
- Every note starts with a header line `summary:` (one line, what it holds and when to read it). Sync-log lines read `- **YYYY-MM-DD kind:** what` (kind: change, note, answer, review, audit, import, merge, upgrade, setup, drill).

## Tools
- `{{TOOLS_DIR}}/notes-commit "message"` : stage, check, commit (add `-p` to push the mirror; `--only PATH` commits only those paths, `--dry-run` shows what would go in).
- If `notes-commit` stops with exit code 3 and lists new folders or files in the root, it committed nothing: ask the owner what to do with each (add as notes, track but skip the lint, ignore completely, or later) and run it again with `--folder NAME=MODE`; never choose for them. `NEW_FOLDERS` in `.myco-notes.conf` sets a default.
- `{{TOOLS_DIR}}/capture "note"` : a quick note into this month's inbox (`--commit` commits it; `--pr` also pushes and opens a pull request, merged after the check when `SOLO=1`).
- `{{TOOLS_DIR}}/resume` : bounded start-of-session briefing (repository state, review proposals waiting for an answer, pending, headline facts, notes past a review date, newest handoff, last commits). Run it first.
- `{{TOOLS_DIR}}/index` : every note with its one-line summary (`--missing`: notes without one). Read it to find the right note.
- `{{TOOLS_DIR}}/asof WHEN [NOTE]` : what the notes said on a date (`--since` what changed after it, `--grep TEXT` search, `--history NOTE`). Read only.
- `{{TOOLS_DIR}}/notes-lint.py` : reference, heading, freshness, ledger, summary, sync-log and secret checks.
- `{{TOOLS_DIR}}/build-notes-map.py` : generate the navigable map with backlinks and history, plus `graph.html`, the notes as a network with a timeline replay.
- `{{TOOLS_DIR}}/mirror-push`, `{{TOOLS_DIR}}/restore-drill` : second copy and proof it can be restored.
- `{{TOOLS_DIR}}/doctor` : read-only health check (kit version, hook, layout, settings).
- Shared repository: run `{{TOOLS_DIR}}/setup-clone` once after cloning; change notes on a branch (`{{TOOLS_DIR}}/notes-commit --branch NAME --pr "message"`); CI (`{{TOOLS_DIR}}/ci-check`) must pass; see `{{DOCS_DIR}}/TEAM.md`.
- Method: `{{DOCS_DIR}}/METHODOLOGY.md` (if present) or the Myco Notes method it was copied from.

## Project facts an agent needs immediately
- Time zone for all dates: {{TIMEZONE}}.
- Notes root: `{{NOTES_DIR}}/`. Deployed files are mirrored in `{{NOTES_DIR}}/scripts/`. Tools: `{{TOOLS_DIR}}/`; method and team guide: `{{DOCS_DIR}}/`; generated map (not versioned): `{{MAP_DIR}}/`.
- Owner / contact for decisions: {{OWNER}}.
