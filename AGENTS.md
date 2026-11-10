# Myco Notes kit: contributor guide (for people and agents changing this repository)

This repository is a kit, not a notes tree. Do not confuse it with the notes trees it creates (those start from `skills/myco-notes/template/`).

## Layout
- `skills/myco-notes/` : the whole product, **self-contained** (a skill-only installer delivers just this folder). `SKILL.md`, `tools/`, `docs/METHODOLOGY.md`, `template/`. Nothing in it may refer to files outside the folder or to an environment variable.
- `.claude-plugin/` : Claude Code plugin and marketplace manifests (the plugin root is the repository root).
- `tests/smoke.sh` : the test. Run it before every commit; all checks must pass. `.github/workflows/test.yml` runs it on Linux and macOS for every push and pull request.
- `examples/` : sample entries for readers; `examples/demo/build_demo.py` builds the made-up demo tree behind the README screenshots and the live demo (`.github/workflows/demo.yml` publishes its map on GitHub Pages). Images for the README live in `.github/assets/`.

## Rules
1. **One copy of everything.** Do not duplicate tools or docs for a second agent; add installation instructions instead.
2. **Stay agent-neutral** in `SKILL.md`, `tools/` and `template/`. Agent-specific text belongs in the README or in the manifest folders.
3. **No secrets, no personal data** (hostnames, paths, addresses) in any file or commit; the tests use obviously fake values.
4. **Versions move together:** `.claude-plugin/plugin.json` `version` equals `metadata.version` in `SKILL.md` (the test checks it). Bump both, tag `vX.Y.Z` and make a GitHub release.
5. `SKILL.md` follows the Agent Skills specification (name equals the folder name, description at most 1024 characters, under 500 lines).
6. Tools are Python 3.8+ (standard library only) and git, with an extension-less `sh` launcher and a `.cmd` launcher for each. Keep them working on Linux, macOS and Windows (CI runs `tests/smoke.sh` on Linux and macOS and `tests/native.py` on all three). Do not add GNU-only shell commands or new dependencies.
8. **Never hard-code folder names** (`notes/`, `tools/`, `docs/`, `notes-map/`) in a tool: read them with `_myco.layout(root)`, which follows `.myco-notes.conf` (new trees: everything under `myco-notes/`; trees without `MYCO_DIR`: the older flat layout, which must keep working). Template files use the `{{NOTES_DIR}}`, `{{TOOLS_DIR}}`, `{{DOCS_DIR}}`, `{{MAP_DIR}}` placeholders. Tests cover both layouts and `relocate`.
7. Change the method in `docs/METHODOLOGY.md` first, then the tools and template that implement it (section 17 maps one to the other).
