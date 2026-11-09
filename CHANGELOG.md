# Changelog

## 0.6.0
- **One folder for everything.** New trees keep the notes, `tools/`, `docs/` and the generated `map/` inside one folder, `myco-notes/`; only the files agents, git and the host look for at the root (`AGENTS.md`, `CLAUDE.md`, `.github/`, `.gitignore`, `.gitattributes`, `.myco-notes.conf`) stay outside it. The root is left for the project's own folders. Configurable with `MYCO_DIR` (and `NOTES_DIR`, `TOOLS_DIR`, `DOCS_DIR`, `MAP_DIR` per folder). `bootstrap --layout flat` and trees without `MYCO_DIR` keep the older layout.
- **`tools/relocate`** moves an older tree into the single folder, or renames the folder: dry run by default, keeps the folder names a tree uses (for example a docs folder called `myco-docs`), rewrites the path references that name real paths, updates the conf, `.gitignore` and `core.hooksPath`, and refreshes the project's tools and docs from the kit.
- **Project data folders** (`DATA_DIRS`, `bootstrap --data-dir`): inputs, outputs and attachments that are not notes are gitignored and skipped by the lint and the map; notes may still reference files in them.
- **Lint:** `archive/` and `logs/` (`HISTORY_DIRS`) are records and are no longer re-checked for passed follow-up dates, missing references, size or orphans (secrets still are); new size check (`MAX_NOTE_KB`, default 100) and a warning when `AGENTS.md` nears the 32 KiB that Codex and some agents load (`ENTRY_WARN_KB`, default 24); references into the generated map folder are not flagged.
- **Windows fix:** the lint resolved references written relative to a note's own folder (for example `plans/backlog.md` in `state.md`) with backslashes, so on Windows every such reference was reported as missing (0.5.0 and earlier). Found by the CI run on Windows.
- The tools and launchers no longer leave `__pycache__` folders in a project.
- Tests: `tests/native.py` 60 checks, `tests/smoke.sh` 44; both cover the single-folder layout, the flat layout, `relocate`, the new lint checks and data folders.
- Verified outside the test suite: the Claude Code plugin installs on Windows, and Codex finds the skill (author's Windows machine).

## 0.5.0
Renamed from Living Notes to Myco Notes. Earlier releases (0.1.0 to 0.4.0) keep the old name.
