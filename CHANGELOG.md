# Changelog

## Unreleased
- **Mycelium view, pinch to zoom**: on a touch screen two fingers now zoom around their midpoint, and moving them together pans (the canvas turns off the browser's own gestures, and until now it followed only one finger, so pinching did nothing). Lifting the fingers selects nothing. The mouse wheel is unchanged.
- **Mycelium view, bud colours**: the bud at the end of a thread has the colour of the note the thread comes from (its group, or the wilt colour), a shade darker on the dark theme and lighter on the light one.
- **Live demo**: `examples/demo/build_demo.py` builds a made-up "Greenhouse Sensors" tree (about 20 dated commits, a wilting note and a missing reference on purpose); `.github/workflows/demo.yml` publishes its map and mycelium view on GitHub Pages from `main`.
- **README**: new opening (the problem in one line, a replay clip of the mycelium view, the live demo link, the install command, five feature bullets, badges); the screenshots now come from the demo tree.
- Tests: `tests/smoke.sh` builds the demo tree and lints it.

## 0.10.0
- **Mycelium view, direction**: the threads now show who mentions whom, in the view's own vocabulary instead of arrowheads. A hypha leaves the note that writes the mention broad and thins toward the note it names, ending in a small swollen tip (a bud) on its rim; two notes that mention each other share an even thread with a bud at both ends. On a lit thread the sap flows from the mentioning note to the mentioned one, and during a replay a new thread grows from its source instead of fading in. The detail panel lists "Mentions" and "Mentioned by" separately (it had one mixed list).
- **Method**: section 9 says the relation map's edges have a direction and a view should show it. Version 2.2 of the document.
- **README**: screenshots of the mycelium view (dark with a selected note, a close-up of the threads, light theme, mid-replay), taken from a made-up demo tree.
- Tests: `tests/native.py` checks that an edge keeps its direction and that the page draws it.

## 0.9.0
- **`tools/resume`**: a start-of-session briefing capped at a character budget (default 6000, `--budget`, `RESUME_BUDGET`). It prints the repository state, the sync tracker's pending list, the master record's headline facts and open items, notes past a review or follow-up date, the newest handoff and the last commits. Items are whole or left out, never cut, and the footer counts what was left out. `SKILL.md` uses it in the resume mode and the audit mode.
- **Optional freshness header** on any note (`---` block: `last_confirmed`, `review_after`, `valid_from`, `valid_until`, `supersedes`, `superseded_by`, ISO dates, no YAML library). `notes-lint.py` reports a passed `review_after`, a `valid_until` that has passed outside the history folders, an old `last_confirmed` without a `review_after` (`STALE_DAYS`, default 365), reversed or malformed dates, and missing `supersedes`/`superseded_by` targets. The map shows the header as a "Freshness" line instead of rendering it, and the mycelium view wilts a note past its review date. Method: section 10.1.
- **`tools/asof`**: what the notes said on a date or revision, a note as it was, `--grep`, `--since` (what changed after it), `--history NOTE` (follows renames). Read only. Method: section 7.1.
- **Method**: new section 1.1 "When this is not a fit" (also in the README); sections 7.1, 10.1, 11.2 and the tool table (section 17) cover the new tools. Version 2.1 of the document.
- **Mycelium view, replay**: the nodes no longer shake. A replay step now only nudges the layout (it used to re-heat the physics on every commit, so the nodes never settled), new notes sprout outward from a neighbour at the length of a thread instead of 20 px inside the cluster, the camera ignores small changes of the bounding box and moves slower, and the size pulse of recent notes is off while replaying. Measured on a 74-note, 81-commit tree at phone size: mean movement per node per frame 1.0 px to 0.21 px, direction reversals 43% to 3% of frames, camera zoom reversals 84 to 5.
- **Mycelium view, bug fix**: a hub note fading in could get a ring with a negative radius; the canvas call threw, the animation loop stopped and the replay froze. The radius is now clamped.
- **Mycelium view, phone layout**: the header is title and counts with the Map, Fit and Theme buttons on the same row and a Find button that opens the search and the legend; the replay bar is one row of controls (play, slider, speed) and one line with the date and commit message (tap it to expand); on a tall screen the picture is stretched vertically (positions only; picking and panning account for it) so the network fills the height; a note nobody mentions is pulled in a little harder so it does not drift out of the picture; the detail panel sits above the smaller bar.
- Tests: `tests/native.py` covers the header lint, `resume` (content, budget) and `asof` (every mode), and the map and graph treatment of the header.

## 0.8.3
- **`STATE_FILE` in `.myco-notes.conf`.** A project whose master record is not called `state.md` (the homelab calls it `homelab.md`) can name it; the map's "Start here" group and `_myco.layout()` use that name. The default stays `state.md`, so nothing changes for existing trees. The working agreement and the tracker keep their standard names for now.
- Tests: `tests/native.py` checks the default and the override.

## 0.8.2
- **Mycelium view: no more mushrooms.** The entry notes (`AGENTS.md`, `CLAUDE.md`, working agreement, tracker, state, runbook) were drawn as cartoon mushrooms, but every Myco Notes tree has the same ones, so highlighting them said nothing about the project. Every note is now a glowing orb.
- **Hubs come from the project's own data.** The few most-mentioned notes (at least two mentions, at most six) are drawn larger with two soft rings and always carry a label. The entry and method notes (the map's "Start here" and "Method" groups) and the history folders are never hubs, however often they are mentioned, because every tree has them.
- **The timeline moved to the left column**, under the search and legend panel, so it no longer takes room from the diagram on a desktop screen; the network is centered in the free space to its right. On a phone it stays a bar at the bottom.
- Tests: `tests/native.py` 105 checks (hubs follow mentions and not names, the timeline sits in the left column, no mushrooms in the page).

## 0.8.1
- **`relocate` now updates a project that already uses the single folder.** Until now it said "nothing to do" for such a tree, so a project kept the tools it was created with. Run from a newer kit (`python <kit>/tools/relocate.py --root PROJECT`) it lists the new and changed files in the project's tools and docs (a Windows checkout's CRLF line endings do not count as a change), and `--apply` copies them (never `bootstrap`, the notes, `.myco-notes.conf` or `AGENTS.md`), refreshes the hooks path and shows the lint before and after. It then prints what else to check: set `NEW_FOLDERS` if the conf lacks it, and add the exit-code-3 rule to `AGENTS.md` if it is missing. Run from the project's own tools folder it says there is no newer kit.
- `SKILL.md` documents the update flow. Tests: `tests/native.py` 102 checks (refresh dry run, CRLF, apply, protected files, second run, the refreshed tools build the graph).

## 0.8.0
- **The mycelium view.** `build-notes-map.py` now also writes `graph.html` in the map folder (`myco-notes/map/graph.html`): the notes drawn as a living network in one self-contained page (no server, no network, no libraries; double-click to open). Notes are nodes, the file-name mentions between them are hyphae, the entry notes are mushrooms, groups are colonies, `archive/` and `logs/` are dimmed compost at the edge. Recently changed notes glow, notes with passed follow-up dates wilt, references to notes that do not exist end in a `?` stub, unmentioned notes drift alone.
- **Timeline replay** of the git history (renames followed): the network grows commit by commit, a slider jumps anywhere, `graph.html#replay` starts it automatically. Hover, click for details and a link to the note's map page, search, group filter, zoom and pan, light and dark theme, reduced-motion respected, a plain list of all notes for keyboard and screen-reader use.
- Only titles, paths, counts and commit subjects are written into the page, never note text; the map's secret gate still applies. The index of the map links to the view.
- New files in `tools/`: `notes_graph.py` (data) and `graph-template.html` (page); both are copied into projects with the other tools and refreshed by `relocate`.
- Tests: `tests/native.py` 93 checks (graph data, rename-following history, no note text in the page, no network references, JavaScript syntax when node is available), `tests/smoke.sh` checks that the view is built and linked. The script's physics and interactions were also run headless with node on the real homelab notes (44 notes, 110 commits) and a 400-note synthetic tree: replay completes, no NaN positions, about 2 ms per frame of computation.

## 0.7.0
- **New folders and files in the root are no longer committed silently.** `notes-commit` finds new root folders and loose files that nothing in the configuration covers, and by default (`NEW_FOLDERS=ask`) commits nothing, prints a report (file count, size, file types, a suggestion) and exits with code 3, so the agent can ask the owner. The owner answers per item with `notes-commit --folder NAME=MODE` (`NAME=*` for all): `add` (track it, lint it as notes), `ignorelint` (track it, skip the lint and the map: recorded in `DATA_DIRS`), `ignoreall` (do not track, do not lint: `DATA_DIRS` and `.gitignore`) or `later` (leave it out of this commit, ask again next time). The decision is written to `.myco-notes.conf`, `.gitignore` or `.myco-notes-lint-ignore` for you and committed with the change.
- **`NEW_FOLDERS` in `.myco-notes.conf`** sets a default: `ask` (the default), or `add`, `ignorelint`, `ignoreall` to apply one answer without a question (it is still recorded). `bootstrap --new-folders` sets it.
- **First-time setup asks.** `SKILL.md` tells the agent to ask the owner which default they want (and which folders are project data) before running `bootstrap`, and to ask once for an existing tree whose conf has no `NEW_FOLDERS` line.
- Not asked about: folders inside the notes folder, `DATA_DIRS`, the generated map, `.github`, `.agents`, `.codex`, `.claude`, and the entry files (`AGENTS.md`, `CLAUDE.md`, `README.md`, `LICENSE*`, `.myco-notes*`, `.gitignore`, `.gitattributes`). Anything git already tracks, or `.gitignore` already covers, is never asked about.
- Behaviour change for existing trees: after updating the tools, a root folder that is untracked today is asked about once (answer `add` for the old behaviour, or set `NEW_FOLDERS=add`).
- Only `notes-commit` is gated; a plain `git add -A` is not.
- Tests: `tests/native.py` 84 checks, `tests/smoke.sh` with the new-folder checks added; both cover ask, each answer, `later`, the wildcard, every `NEW_FOLDERS` value and the flat layout.

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
