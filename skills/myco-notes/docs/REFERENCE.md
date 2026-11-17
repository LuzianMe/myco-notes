# Myco Notes reference: the tools, the layout and new folders

A quick reference to the kit's reference implementation. The method is in `METHODOLOGY.md`, the format of the notes in `FORMAT.md`, working as a team in `TEAM.md`.

Paths below assume the default single-folder layout (`myco-notes/...`). In a notes repository made before 0.6.0 the tools are at `tools/...`; use the folders named in `.myco-notes.conf`.

## 1. The tools

They live in each notes repository's `myco-notes/tools/`. Each has a launcher without extension (Linux, macOS, Git Bash) and a `.cmd` launcher (cmd, PowerShell); `--help` shows its options.

| Tool | What it does |
|---|---|
| `notes-commit "message"` | Stage, check and commit with a described message; `--only PATH`, `--dry-run`, `-p` (push the mirror), `--tag`, and for teams `--branch`, `--push`, `--pr`. Stops (exit 3) when a new folder appears in the root and asks what to do with it (section 3). |
| `capture "note"` | A quick note into this month's inbox; `--commit`, `--pr`. |
| `resume` | The start-of-session briefing, within a character budget. |
| `index` | Every note with its one-line summary; `--missing`, `--review-scope`. |
| `ingest` | Keep an outside document as a source; `--list` shows the sources and who cites them. |
| `notes-lint.py` | References, headings, dates, freshness header, summaries, sync-log format, ledger, sizes, secrets. |
| `asof DATE [NOTE]` | What the notes said on a date; `--since`, `--grep`, `--history NOTE`. |
| `build-notes-map.py` | The searchable map with backlinks and history, and `graph.html` (the mycelium view). |
| `mirror-push`, `restore-drill` | A second copy, and proof that it can be restored. |
| `doctor` | Read-only health check: kit version, hook, layout, settings. |
| `bootstrap` | A new notes repository (`--data-dir`, `--new-folders`), or take over a folder (`--import`, `--adopt`). Run from the kit. |
| `relocate` | Move an older notes repository into the single folder, or refresh a notes repository's tools and docs from a newer kit. Run from the kit. |
| `secret-scan`, `hooks/pre-commit`, `ci-check`, `setup-clone` | The secret rules, the commit hook (secret scan of the added lines), the pull-request check (secret scan and lint), per-clone set-up. |

## 2. Layout of a notes repository

```
my-project/
  AGENTS.md  CLAUDE.md  .github/  .gitignore  .gitattributes  .myco-notes.conf     (agents, git and the host look for these at the root)
  myco-notes/        the notes (state.md, runbook.md, one note per component, plans/, logs/, inbox/, sources/, ...)
                     plus tools/, docs/ and map/ (generated, gitignored)
  files-input/ ...   your own folders (--data-dir: not notes, gitignored, skipped by the lint and the map)
```

Repositories from 0.5.x or earlier (`notes/`, `tools/`, `docs/` at the root) keep working; `relocate --root <repository>` run from the kit shows the move, `--apply` does it.

## 3. New folders in the root

`notes-commit` never adds a new root folder silently. By default (`NEW_FOLDERS=ask`) it stops and the owner is asked:

| Answer | Tracked | Lint and map | For |
|---|---|---|---|
| `add` | yes | read as notes | knowledge, mostly Markdown |
| `ignorelint` | yes | skipped | reference files you want history for |
| `ignoreall` | no | skipped | inputs, outputs, downloads, large or sensitive files |
| `later` | not this time | not this time | undecided |

Set `NEW_FOLDERS` in `.myco-notes.conf` to apply one answer every time.
