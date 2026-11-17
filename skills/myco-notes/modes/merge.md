# Merge a handoff

*Part of the Myco Notes skill: read `SKILL.md` (the folder above) first for `<KIT>`, `<notes>`, `<tools>` and the guard rails, which always apply.*

**When:** Another session or person left a handoff in the plans folder.

Read the handoff in `<notes>/plans/`, check `git status` and last-modified times for concurrent edits, merge each fact into its canonical file in small atomic edits (re-read before each write), then update the handoff's merge-status block. In a shared repository (several people or agents, a hosting service), work on a branch and open a pull request instead of committing to main: `<tools>/notes-commit --branch NAME --pr "message"`; CI (`<tools>/ci-check`) scans for secrets and lints; a human merges. Set-up and conflict handling: `<KIT>/docs/TEAM.md`.
