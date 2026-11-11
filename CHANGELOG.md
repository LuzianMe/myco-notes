# Changelog

## 0.15.0
Quick notes and solo repositories (method 2.6, section 19): Myco Notes can sit behind an ordinary conversation, for example on a phone, and save what you say without ceremony.
- **Quick notes go to an inbox**: the new `tools/capture` saves a typed or dictated note as one dated entry at the end of `<notes>/inbox/YYYY-MM.md` (owner's words, title, optional tags and related note; time in `TIMEZONE`), and with `--commit` commits just that file. No questions, no checks, no other notes touched; sorting the inbox into the notes is a separate step. The skill has a matching quick-note mode, the starter tree an inbox README and an `AGENTS.md` section, the lint treats the inbox as a record, the map shows it as its own group, and `resume` counts unsorted notes.
- **Solo repositories**: `SOLO=1` in `.myco-notes.conf` lets an agent merge its own pull request once the server check passes. `notes-commit --pr --merge` (or `--pr` with `SOLO=1`) waits for the check, squash-merges (one commit per change on main) and deletes the branch, and refuses to merge when a check fails or never reports (exit 5). Teams keep `SOLO=0`.
- **The map, built on GitHub**: the starter tree's check workflow has a second job that, after each change lands on main, builds the notes map (index, pages, `graph.html`) and keeps it with the run as a private 30-day download (`notes-map` artifact), so the network can be seen without a local clone, for example on a phone. Existing trees: copy the job from `template/.github/workflows/notes-check.yml`.
- **Solo merges are robust in cloud sessions**: the merge step polls the checks for up to 15 minutes instead of waiting forever, and a GitHub CLI that cannot reach GitHub's API (as in Claude Code cloud sessions) is reported as such, not as a failed check; the agent then merges with its own GitHub tools.
- **New settings** in the starter conf: `TIMEZONE` (filled from `bootstrap --tz`) and `SOLO`.

## 0.14.0
Cloud and phone use, tested in Claude Code cloud sessions on a private test repository.
- **The hook switches itself on**: in a fresh clone where `core.hooksPath` is not set (a new teammate, an agent session in the cloud), `notes-commit` turns the secret-refusing hook on before committing and says so. Before, the first commits of a clone nobody had set up ran without it (the pull-request check still caught secrets).
- **A copy of the skill in the notes repository** (`.claude/skills/myco-notes` or `.agents/skills/myco-notes`) is supported: cloud sessions load it (they do not install plugins named in the repository's settings), the lint and the map leave it out instead of counting its docs as notes, and `relocate` refreshes it with the tools.
- **README: "From the cloud or a phone"**: what works in a cloud session, how to give it the skill, and what needs your own machine. Method section 18 covers agent sessions in the cloud.

## 0.13.5
- **Mycelium view, phone top bar**: the title no longer runs under the Find button. The room it leaves for the buttons is measured instead of fixed (it was sized for four buttons before Depth made five), and when a short title still does not fit beside them, the buttons get a row of their own above it.

## 0.13.4
- **Mycelium view, right-drag turns**: with depth on, dragging with the right mouse button turns the view, even when it starts on a note (no context menu over the network); Shift-drag, two fingers and the sideways trackpad swipe still work.
- **A hint on how to turn**: with depth on, a short line at the bottom says how to turn the view (with a mouse or trackpad: Shift-drag, right-drag or a sideways swipe; on a touch screen: two fingers) and that Fit faces the front. It fades after a few seconds, shows on at most three visits and never again once you have turned the view (remembered per browser). The Depth button's tooltip mentions right-drag too.

## 0.13.3
- **Mycelium view, calmer glow on small screens**: each note's glow is capped by the distance to its nearest neighbour on screen and grows fainter where it has to shrink, so a crowded view (a phone) no longer blurs into one haze; every note keeps a small halo, and a spread-out view looks as before. Notes at the back widen their glow less than in 0.13.0.

## 0.13.2
- **Mycelium view, turn all the way round**: left and right turning has no limit any more; tilting goes up to about 70 degrees either way and stops there, so the picture never flips upside down. The network turns about its own centre.
- **Fog follows the viewer**: notes fade with their distance from you instead of with their age, so the view stays right from any side (from the front it looks as before; from behind, the oldest notes are the near, bright ones).
- **Fit turns back**: Fit, a double-click and the Depth button turn the view back to the front by the shortest way round.
- **Fit measures the turned picture**, so a side view is neither cropped nor tiny; dragging a note follows the finger when the view is turned; small changes from the sway no longer make the fitted view breathe.

## 0.13.1
- **Mycelium view, turning with two fingers**: with depth on, two fingers moved together on a touch screen turn the view (left and right turn it, up and down tilt it); spreading them still zooms, in the same gesture, and one finger still pans. On a trackpad a sideways two-finger swipe turns it; a vertical swipe, a mouse wheel and a trackpad pinch still zoom, so nothing changes for mouse users. Shift-drag still works. With depth off, two fingers pan and zoom as before.

## 0.13.0
- **Mycelium view, depth**: notes float at different depths, recently changed ones in front and the ones untouched for longest at the back (smaller, fainter, without their shine; threads thin and fade with them). Depth is a rank among the notes in view, so it spreads evenly whatever the project's pace, and a replay pulls each commit's notes forward. The view looks from slightly above and sways gently (not with reduced motion); a pan tilts it, Shift-drag turns it. Clicking, labels and search work on the projected positions. The new Depth button returns the exact flat view; the choice is kept per browser, and `?depth=0` or `?depth=1` in the address sets it. Plain canvas, no libraries: the map is still one offline file.
- **README images** re-recorded with depth.

## 0.12.2
README and demo only; the skill and tools are unchanged apart from the version number.
- **A more colourful demo**: the demo tree's components are split into four groups (in the field, data path, greenhouses, for the growers), so the map uses ten colours instead of mostly one. The live demo is rebuilt with them.
- **README images re-recorded**: the replay clip and the four screenshots show the current mycelium view and the new groups.

## 0.12.1
Fixes from a second outside review (method 2.5: sections 8.2 and 8.4).
- **Links in a mirror are never followed**: a symbolic link or Windows junction found inside the mirror is removed and replaced, not entered, and a folder that resolves outside the mirror is refused; before, a junction placed in the mirror could make a sync delete and write files outside it. Tested with a junction on Windows and a symlink elsewhere.
- **Secret reports show no text from the line**: only file, line and rule. Before, a second credential on the same line was printed in full.
- **CI scans merge commits**: the lines a merge adds that none of its parents had (a conflict resolution) are scanned.
- **CI fails when its base cannot be found** (with a hint for shallow clones and force pushes) instead of quietly scanning only the last commit; a first push (zero base) scans the whole history.
- **A linked git worktree is not copied into a mirror**: its `.git` is only a pointer to history stored elsewhere; `mirror-push` refuses and points to `MIRROR_TARGET=git:URL`.
- **ssh targets get the ownership check** of local ones before rsync deletes anything (missing, empty, marked, or a mirror of the same repository), and keep their marker.
- **Content check**: `mirror-push --verify` or `MIRROR_VERIFY=hash` compares SHA-256 when sizes match, so a change that keeps size and time is not missed (rsync gets `--checksum`).
- **`notes-commit --only` checks only what it commits**: syntax checks and `SYNC_GLOBS` look at the selected paths; other staged files stay staged and unchecked.
- **`notes-commit -p` passes on the mirror result**: exit 4 means committed, but the mirror did not sync (failed, or skipped with `MIRROR_STRICT=1`).

## 0.12.0
Honest results and narrower actions, the second half of the outside review (method 2.4: sections 7, 8.4, 11.2, 11.5, 11.6, 12).
- **Approval rule**: "Ask before changing anything the owner has not asked for; an explicit request is approval for that change. Deleting and publishing always need a per-item yes." In the method, SKILL.md and the template's entry point and working agreement, so an agent no longer stops to re-ask for work it was just asked to do.
- **Restore drill gives two verdicts**: *history* (fsck, HEAD) and *working copy* (entry point, master record and tracker present; working files equal the last commit, ignoring file modes that archives drop). Either failing fails the drill, and the sync-log line names both.
- **Mirror scope and results**: `MIRROR_SCOPE=tracked` (new trees) copies `.git` and the tracked files only, never ignored or untracked files, and removes from the target what an earlier sync copied outside that scope; `all` keeps the whole working copy (the default when the setting is missing). The last line says `mirror: synced`, `skipped` or `failed`; a real failure (for example a rejected `git push --mirror`) now exits 1, while an unreachable target is still a quiet skip. `--strict` or `MIRROR_STRICT=1` makes a skip exit 3 and a failed post-push command exit 1, for scheduled jobs. ssh targets get `--dry-run` too.
- **Narrower commits**: `notes-commit --only PATH` (repeatable) commits just those paths and leaves other changes uncommitted; `notes-commit --dry-run` shows what would be committed, using a throw-away index.
- **Kit version and `doctor`**: `bootstrap` and `relocate` write `KIT_VERSION` into `.myco-notes.conf`, and the tools carry their version. The new read-only `tools/doctor` reports the tree's kit version, whether its tools are older than the kit you run it from (with the `relocate` command to refresh them), the hook, the layout, the launchers and missing settings (`NEW_FOLDERS`, `MIRROR_SCOPE`).
- Tests cover each change; the version now also lives in `tools/_myco.py` and moves with the others.

## 0.11.0
Safety fixes from an outside review (method 2.3: sections 8.2, 8.4, 11.1 and 18).
- **Mirror and map never delete what they do not own.** `mirror-push` refuses a local target that is the repository, inside it, or a folder that contains it, and writes only into an empty folder, a folder holding its `.myco-mirror` marker, or an earlier mirror of the same repository (which then gets the marker). `mirror-push --dry-run` lists what would be copied and removed. `build-notes-map.py` refuses an `--out` that is the repository or contains it, and empties only an empty folder, a folder with its `.myco-notes-map` marker or an earlier map.
- **CI scans every commit.** `ci-check` scans what each commit in the range adds, not only the net difference, so a secret added in one commit and removed in the next fails the check (it is still in the history).
- **A check that cannot run fails.** `notes-lint` exits 3 when it cannot run (for example an invalid expression in `.myco-notes-lint-ignore`, now reported with its entry number); `secret-scan` exits 3 the same way and the pre-commit hook then refuses the commit; `ci-check` fails unless the lint finished and printed its summary.
- **Secret reports hide the value**: file, line and rule, with the value shown as `[redacted, N chars]`, in the hook, CI, the lint and the map builder. One set of rules (`tools/secret_scan.py`) serves all four: names match in any case (`PASSWORD=`), and password/passphrase/psk values are flagged from 12 characters (placeholders such as `<password>`, `${PASS}` or `changeme` are not).
- **Unique note pages**: two notes whose paths give the same page name (`a/b.md` and `a-b.md`) both get a page; the later one gets a short hash of its path. Other page names do not change.
- The sync-log line now comes before the commit (SKILL.md, the method and the template), so it goes into the same commit. TEAM.md commands use `myco-notes/tools/`.
- Tests: the reviewer's cases are smoke tests; CI also runs both tests on Python 3.8, the oldest version the tools support.

## 0.10.9
- **Codex plugin**: Codex installs Myco Notes with `codex plugin marketplace add LuzianMe/myco-notes` and `codex plugin add myco-notes@myco-notes` (it reads the existing marketplace file). A new `.codex-plugin/plugin.json` gives Codex the display name, icon, description and starter prompts. The README's Codex section leads with this; linking the skill folder still works.
- Tests: the Codex manifest must match the plugin manifest's name and version, and its icon paths must exist.

## 0.10.8
- **Round icon**: the plugin icon (`.claude-plugin/icon.png`) now draws the mycelium on a dark disc with transparent corners instead of a dark square; a few notes and threads grow past the rim.

## 0.10.7
- **Plugin directory listing links**: `plugin.json` now sets `documentationUrl` (the method), `supportUrl` (GitHub issues) and `privacyPolicyUrl` (the README section "What it runs and what it sends": the plugin collects nothing and has no telemetry).
- The demo builder (`examples/demo/build_demo.py`) sets only its own git variables instead of copying the whole environment; the demo tree is unchanged.

## 0.10.6
- **Plugin directory validation**: the portal refused the repository ("Couldn't validate that repository") because its `.gitattributes` converted line endings (`text=auto eol=lf`, `*.cmd eol=crlf`), and the directory refuses attributes that rewrite file contents. The kit's `.gitattributes` is now `* -text` (store and check out every file exactly as committed): the `.cmd` launchers are committed with CRLF, everything else with LF, so they still work on every platform, also with `core.autocrlf=true`. The template's rules move to `template/gitattributes`, which `bootstrap` installs as the new tree's `.gitattributes`, so notes trees keep normalising line endings as before.
- Tests: `tests/smoke.sh` checks that no `.gitattributes` in the kit rewrites contents, that the launchers are stored with the right line endings, and that a new tree still gets its `.gitattributes`.

## 0.10.5
- **Ready for the plugin directory**: a listing icon (1024 px, a small mycelium in the view's colours, in the plugin manifest folder), `displayName` "Myco Notes" in `plugin.json`, and a README section "What it runs and what it sends" (local scripts and git only; network only for a mirror, push or pull request you configure; no telemetry). `claude plugin validate .` passes with no directory findings.
- Tests: the fake private-key header used to test the secret refusal is assembled at run time, so no file in the repository holds key-shaped text.

## 0.10.4
- **Mycelium view, collapsible boxes on a larger screen**: the search box has a − button that folds it to the title and counts (+ opens it again), and the detail panel has the phone's strip with Less and More, so both can give the network more room. The detail panel starts open on a larger screen and as a strip on a phone; a choice made with the buttons is remembered in the browser (localStorage, when allowed). The phone layout is unchanged.

## 0.10.3
- **Mycelium view, labels take turns**: names used to show only on the hubs (for ever) and, zoomed in, on every larger note. Now a few notes carry their name at a time (about the square root of the notes in view, more when zoomed in past the fitted view): one fades in about every second with a small rise, each stays about 7 s and fades out, and a note that was just named rests for 25 s. Hubs, well-mentioned and recently changed notes are picked more often; a name never lands on another one or under the search, timeline, tools or detail panel, and fades out if the camera moves it under one. With a note selected, only its neighbours take turns, faster, and the ones already named stay. Hover, selection and search matches are named at once. With reduced motion the names switch without fading, every 11 s.
- README stills retaken.

## 0.10.2
- **Mycelium view, phone panel**: on a phone, selecting a note opens a small strip at the bottom (the title on one line, links out and in, any warning, Open and More) instead of a panel that covered most of the screen. More (or a tap on the title) shows the full details and the lists; Less shrinks it again, and the choice is kept while the page is open. The desktop panel is unchanged.

## 0.10.1
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
