# Myco Notes

*Linked, versioned, secret-free project notes for you and your AI agents.*

[![test](https://github.com/LuzianMe/myco-notes/actions/workflows/test.yml/badge.svg)](https://github.com/LuzianMe/myco-notes/actions/workflows/test.yml) [![live demo](https://img.shields.io/badge/live%20demo-mycelium%20view-3fbfa8)](https://luzianme.github.io/myco-notes/graph.html) [![license](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Your AI agent forgets everything between sessions. Your notes should not.** Myco Notes keeps a project's knowledge in plain Markdown and git, and keeps it **true**: every change is written down with its evidence, every note says which notes it depends on, nothing secret gets committed, and nothing is deleted, only superseded.

![The notes of a demo project growing commit by commit in the mycelium view: notes appear as glowing nodes and threads grow between the notes that mention each other](.github/assets/mycelium-replay.gif)

*A made-up project's notes growing commit by commit. **[Open the live demo](https://luzianme.github.io/myco-notes/graph.html)** to click around it, or browse [its notes map](https://luzianme.github.io/myco-notes/).*

**Install in Claude Code** (other agents: [Install](#install)):
```
/plugin marketplace add LuzianMe/myco-notes
/plugin install myco-notes@myco-notes
```
Then ask: *"start a Myco Notes tree for my project"*.

- **Capture, not chores:** after each change the agent updates the right notes (master record, runbook, entity notes) and commits them with a described message.
- **Stays accurate:** a lint finds broken references, passed follow-up and review dates, stale headers and oversized notes; `resume` briefs the next session in a fixed budget; `asof` shows what the notes said on any date.
- **Safe by default:** a commit hook and CI refuse anything that looks like a secret; notes say where a secret lives, never its value.
- **See how it connects:** a static map with backlinks, and the mycelium view above, which replays the git history and shows wilting (overdue) notes and missing references.
- **Plain files:** Markdown, git and Python 3.8+ standard library. Linux, macOS and Windows. Works with any agent, or none.

## Where it comes from

A method, a starter tree and a small set of tools for keeping a project's knowledge **accurate, secure, versioned and connected**, for engineers who run large or long projects (infrastructure, platforms, data and ML systems, research, hardware) alone, in teams, or together with AI coding agents.

It started as the operational memory of a long-running, AI-operated engineering project, where the notes had to work for an operator that forgets everything between sessions. If the notes are good enough for that operator, they are good enough for a new teammate, an auditor, or you next year.

Agent-neutral: the skill follows the open [Agent Skills](https://agentskills.io/specification) format, so Claude Code, OpenAI Codex and other agents that read `SKILL.md` and `AGENTS.md` can use it. Everything it needs is inside one folder, `skills/myco-notes/`.

## Why "Myco"
Mycelium is the underground network of threads (hyphae) that connects the trees of a forest, carries what one needs to another, and breaks down what has died. The notes work the same way: every note is a thread, the references between them are the network, and nothing is lost: old statements are superseded and kept. The vocabulary is used lightly:

| In nature | Here |
|---|---|
| Spawn (the starter culture) | the `template/` and `tools/bootstrap` |
| Substrate (what it grows in) | your notes repository |
| Hyphae (the threads) | the notes and the references between them (backlinks, "who mentions whom") |
| Fruiting body (the visible part) | the generated notes map |
| Decomposition | superseding and archiving stale statements |

## What you get (all paths inside `skills/myco-notes/`)

| Part | What it is |
|---|---|
| `SKILL.md` | The skill: five working modes (capture, audit, bootstrap, merge, restore/review) plus resume/hand-off, guard rails and an execution-environment check. |
| `docs/METHODOLOGY.md` | The full method: principles, file roles, entry formats, how to capture information, when to update, relations between files and datasets, git versioning, security, freshness, procedures, working with AI agents, anti-patterns. |
| `template/` | A ready starter tree: entry point (`AGENTS.md` / `CLAUDE.md`), working agreement, master record, runbook with a lessons list, sync tracker (derived-copy ledger, dependency matrix, pending list, sync log), backlog, verification guide, artifact and archive folders, `.gitignore`, config. |
| `tools/notes-commit` | One command to commit with a described message: syntax checks, optional AI co-author trailer, optional sync of executed files, optional mirror push, optional milestone tag, `--only PATH` to commit just those paths, `--dry-run` to preview, and for teams `--branch`, `--push`, `--pr`. |
| `tools/hooks/pre-commit`, `tools/secret-scan` | Refuse commits whose added lines look like secrets (versioned; activated with `core.hooksPath`; the same rules run in CI). |
| `tools/notes-lint.py` | Finds missing references, duplicate heading numbers, stale "last updated" headers, passed follow-up dates, incomplete ledger rows, secrets, oversized notes and an `AGENTS.md` that is too big for the agents that cut it off. It also reads an optional freshness header (`last_confirmed`, `review_after`, `valid_from`, `valid_until`, `supersedes`, `superseded_by`) and reports passed review dates, old confirmations and missing targets. Records in `archive/` and `logs/` are not re-checked for dates and references. |
| `tools/resume` | A start-of-session briefing capped at a character budget (default 6000): repository state, pending list, headline facts and open items, notes past a review date, the newest handoff, the last commits. Items are whole or left out, and the footer says how many. |
| `tools/asof` | Read-only time travel over the git history: `asof 2026-09-01` (the notes as they were), `asof 2026-09-01 NOTE`, `--grep TEXT`, `--since` (what changed after that date), `--history NOTE`. |
| `tools/build-notes-map.py` | Builds a static, searchable map: notes grouped by purpose, **who mentions whom**, backlinks, per-note git history, recent commits, and the **mycelium view** (`graph.html`): the notes as a living network with a timeline that replays the git history. Refuses to build if a note contains a secret. |
| `tools/mirror-push`, `tools/restore-drill` | A second copy of the repository (by default only what git tracks; refuses targets that overlap the tree; `--dry-run`, `--strict`), and proof that it can be restored, with separate verdicts for the history and the working copy. |
| `tools/doctor` | Read-only health check: kit version (and whether the tools are older than the kit you run it from), hook, layout, missing settings. |
| `tools/bootstrap` | Creates a new notes repository from the template in one command, with everything in one `myco-notes/` folder and optional project data folders (`--data-dir`). |
| `tools/relocate` | Moves an older tree (notes/, tools/, docs/ at the root) into the single folder, or renames that folder: dry run first, keeps your folder names, rewrites the path references. |
| `tools/ci-check`, `tools/setup-clone`, `docs/TEAM.md`, `template/.github/` | Team use: a pull-request check (secret scan + lint), per-clone setup, CODEOWNERS and PR template, and the step-by-step guide for GitHub or GitHub Enterprise. |

At the repository root: `.claude-plugin/` (Claude Code plugin and marketplace manifests, also read by Codex), `.codex-plugin/` (Codex plugin manifest), `tests/` (`native.py`, `smoke.sh`), `examples/`, `LICENSE`, `NOTICE`.

## Install

### Claude Code (one command)
```
/plugin marketplace add LuzianMe/myco-notes
/plugin install myco-notes@myco-notes
```
Then ask Claude to "start a Myco Notes tree for my project", "update the notes", "audit the notes" or "commit the notes".

### OpenAI Codex (one command)
```bash
codex plugin marketplace add LuzianMe/myco-notes
codex plugin add myco-notes@myco-notes
```
Then use the same requests as above. `codex plugin marketplace upgrade` followed by the same `add` picks up a new release.

Without the plugin system, link the skill folder instead: Codex reads skills from `~/.agents/skills` (all your projects) or `.agents/skills` inside a repository, and follows symlinks.
```bash
git clone https://github.com/LuzianMe/myco-notes.git ~/.agents/myco-notes-kit
mkdir -p ~/.agents/skills
ln -s ~/.agents/myco-notes-kit/skills/myco-notes ~/.agents/skills/myco-notes
```
Restart Codex if the skill does not appear.

### Other agents
Any agent that supports Agent Skills: copy or link `skills/myco-notes/` into its skills folder; the folder is self-contained. Any other agent: clone the repository and tell it to read `skills/myco-notes/SKILL.md` as a procedure; once a notes tree exists, point it at the tree's `AGENTS.md`.

### No agent
Use the tools directly (below). The method is plain Markdown plus git.

## What it runs and what it sends
Everything runs on your machine, inside the notes repository you point it at. Nothing is sent anywhere unless you configure it.
- **The skill** tells the agent to edit Markdown files in the notes tree and to run the kit's own Python scripts (`notes-commit`, `notes-lint.py`, `build-notes-map.py`, `resume`, `asof` and the others in `tools/`) and `git`. No package is downloaded or installed; the scripts use the Python standard library only.
- **Writes** go to the notes repository: its files, its git history, and `core.hooksPath` in its git config (so the secret-refusing pre-commit hook runs). `bootstrap` creates a new tree in the folder you name.
- **Network:** none by default, and no telemetry. Only when you set it up: `mirror-push` copies the repository to the `MIRROR_TARGET` you configure (a local folder, `git push --mirror` to a git URL, or rsync over ssh); `notes-commit --push` / `--pr` runs `git push` to your `origin` and, with `--pr`, `gh pr create` if the GitHub CLI is installed; `POST_PUSH_CMDS` and `SYNC_CMD` run commands you write yourself in `.myco-notes.conf`.
- **The map and the mycelium view** are static HTML files with no scripts or fonts from the network; they contain note titles, paths, counts and commit subjects (the map pages also the note text), and are written only to the gitignored map folder.
- **Secrets:** the notes say where a secret lives, never its value; the pre-commit hook, the map builder and the CI check refuse text that looks like a credential.
- **Commit trailer:** commits made by an agent get the `AGENT_TRAILER` line from `.myco-notes.conf` (empty it, or use `notes-commit --human`, to leave it out).

## When it is not a fit
Myco Notes is the operational memory of one project or system, edited by a few people and agents, in one git repository, over months or years. It is the wrong tool for: memory about a person or a stream of small facts (a typed one-fact-per-file store fits better); many writers updating at once (writes here are plain edits protected by git, the hook and the lint, not transactions); ranked retrieval or graph queries over thousands of records (add a search index, or a real store); facts that a tool must check for meaning (the freshness header and `asof` check dates and history, not whether two sentences contradict); and a tree nobody will keep current in the same session as the change. The full list is in `skills/myco-notes/docs/METHODOLOGY.md` section 1.1.

## Sharing with a team
Put the notes tree in a private repository on GitHub, GitHub Enterprise or any git host. A bootstrapped tree already contains a pull-request check (`.github/workflows/notes-check.yml`), a CODEOWNERS file and a PR template. Teammates run `myco-notes/tools/setup-clone` once after cloning and change notes with `myco-notes/tools/notes-commit --branch NAME --pr "message"`. Set-up, branch protection and conflict handling: `skills/myco-notes/docs/TEAM.md`.

## Platform support
Linux, macOS and Windows (native, Git for Windows, or WSL). The tools are Python 3.8+ (standard library only) plus git; each has a launcher for every shell. In Git Bash, WSL, macOS and Linux write `myco-notes/tools/notes-commit ...`; in cmd or PowerShell write `myco-notes\tools\notes-commit ...` (a `.cmd` launcher) or `python tools\notes_commit.py ...`. Remote mirrors over ssh need rsync and ssh; a `git:URL` mirror target needs neither. The kit's tests run on all three systems in GitHub Actions.

## Layout

Everything the method adds lives in one folder, so the project's root stays yours:

```
my-project/
  AGENTS.md  CLAUDE.md  .github/  .gitignore  .gitattributes  .myco-notes.conf     (agents, git and the host look for these at the root)
  myco-notes/        the notes, plus tools/, docs/ and map/ (generated, gitignored)
  files-input/ ...   your own folders (--data-dir: not notes, gitignored, skipped by the lint and the map)
```

**New folders in the root.** `notes-commit` does not silently add a folder or file that appears in the root. By default (`NEW_FOLDERS=ask`) it stops, commits nothing, lists what is new and exits with code 3; your agent asks you and runs it again with your answer:

| Answer | Tracked | Lint and map | For |
|---|---|---|---|
| `add` | yes | read as notes | knowledge, mostly Markdown |
| `ignorelint` | yes | skipped | small reference files you want history for |
| `ignoreall` | no | skipped | inputs, outputs, downloads, large or sensitive files |
| `later` | not this time | not this time | undecided, asked again next time |

Set `NEW_FOLDERS=add`, `ignorelint` or `ignoreall` in `.myco-notes.conf` (or `bootstrap --new-folders`) to apply one answer every time without being asked. The first-time setup asks you which you want.

Trees made with 0.5.x or earlier (notes/, tools/, docs/ at the root) keep working unchanged; `relocate` converts one (and, on a tree that already has the single folder, refreshes its tools and docs from a newer kit):

```bash
python3 <kit>/tools/relocate.py --root ~/projects/old-notes            # dry run: shows the moves and the path rewrites
python3 <kit>/tools/relocate.py --root ~/projects/old-notes --apply    # then review git diff, run the lint, commit
```

## The mycelium view

`build-notes-map.py` also writes `myco-notes/map/graph.html`: one self-contained page (no server, no network, no libraries) that opens by double-click and draws the notes as a mycelium.

![The mycelium view of a demo notes tree in the dark theme, with one note selected: its threads light up and the panel lists what it mentions and what mentions it](.github/assets/graph-dark.webp)

| Threads grow from the note that writes the mention and end in a bud on the note it names | Light theme; a wilting note (dashed ring) and a missing reference (`?`) | Halfway through the replay of the git history |
|---|---|---|
| ![Close-up of tapered threads ending in small buds on the rim of the notes](.github/assets/graph-hyphae.webp) | ![The same tree in the light theme](.github/assets/graph-light.webp) | ![The network after 12 of 23 commits](.github/assets/graph-replay.webp) |

*Screenshots of a made-up demo tree ("Greenhouse Sensors"), built by `examples/demo/build_demo.py`; the same tree is the [live demo](https://luzianme.github.io/myco-notes/graph.html), rebuilt from `main` on every change to the kit.*

- **Notes are nodes, mentions are hyphae**: the threads are the same file-name mentions the map uses for backlinks. Notes with many backlinks are bigger, and the few most-mentioned notes of the project are its hubs (two soft rings, chosen by mentions; the entry and method notes every tree has are never hubs); each group of notes is a color and clusters into a colony; history folders (`archive/`, `logs/`) sit dimmed at the edge.
- **Threads have a direction**: a hypha grows out of the note that writes the mention, broad at its base, and thins toward the note it names, where it ends in a small bud on the rim, in the colour of the note it came from (a shade darker on the dark theme, lighter on the light one), so you can tell where a thread starts without following it. Two notes that mention each other share an even thread with a bud at both ends. While a thread is lit, sap flows the same way, and during a replay a new thread grows along its length instead of fading in.
- **Names take turns**: a few notes carry their name at a time and hand it on, one fading in about every second and each staying about 7 seconds, so over a minute you see most of the network named without clutter. Well-mentioned, hub and recently changed notes come up more often, names never overlap each other or the panels, and zooming in brings more of them. With a note selected, only its neighbours take turns (all of them, when they fit). The hovered and selected note and search matches are always named.
- **Depth**: the notes float at different depths. Recently changed notes sit in front, big and bright; the notes untouched for longest sink to the back, smaller and fainter. During a replay each commit pulls its notes forward while the rest recede. The view looks from slightly above and sways gently (not with reduced motion), a pan tilts it a little, and you turn it with two fingers moved together on a touch screen (one finger pans, spreading two zooms), a sideways two-finger swipe on a trackpad, or Shift-drag. Depth is a ranking among the notes in view, so it spreads evenly whatever the project's pace. The Depth button returns the flat view (remembered per browser; `graph.html?depth=0` or `?depth=1` also works).
- **Health you can see**: recently changed notes glow; notes with passed follow-up dates wilt (amber, dashed ring); a reference to a note that does not exist ends in a dashed stub with a `?`; a note nobody mentions drifts alone like a spore.
- **Timeline replay**: press Replay (or Space) and the network grows commit by commit from the first commit to now; renames are followed, new and changed notes let out a ring. Drag the slider to jump anywhere in the history. `graph.html#replay` starts the replay on its own, handy for recording a clip.
- **Explore**: hover to light up a note's threads, click for its details (mentions and mentioned by, each with its own list of notes, last change, follow-ups, missing references) and a link to its map page, search with Enter to fly to a match, click a group in the legend to hide it, wheel or pinch with two fingers to zoom, drag to pan, double-click or Fit to see everything, Theme for light and dark (it follows the system by default). On a larger screen the − button folds the search box down to the title and counts, and Less shrinks the detail panel to a strip (More opens it again); the browser remembers both.
- **On a phone** the header shrinks to the title, the counts and four buttons (Find opens the search and the legend), the replay bar is one row of controls and one line of text (tap the line to read the whole commit message), the network is stretched to fill the height, a selected note opens a small strip (title, links in and out, Open, More) instead of a panel over half the screen, and during a replay the nodes move slowly and settle instead of shaking.
- A note past its `review_after` or `valid_until` date wilts, like one with a passed follow-up date.
- Only titles, paths, counts and commit subjects go into the page, never the text of a note; the map's secret gate still applies. A note list in the page keeps it usable with a keyboard or a screen reader, and `prefers-reduced-motion` turns the animation off.

## Quick start (without an agent)

```bash
git clone https://github.com/LuzianMe/myco-notes.git
cd myco-notes/skills/myco-notes
tools/bootstrap ~/projects/my-project --name "My Project" --owner "Your Name" --tz "UTC" --data-dir files-input --data-dir files-output
cd ~/projects/my-project
# edit myco-notes/working-agreement.md and myco-notes/state.md, then:
myco-notes/tools/notes-commit "Describe the first real change and why"
python3 myco-notes/tools/notes-lint.py
python3 myco-notes/tools/build-notes-map.py && xdg-open myco-notes/map/index.html   # and myco-notes/map/graph.html for the mycelium view
```

The notes map is nicer with `pip install markdown` but works without it.

## Using it with an AI agent

Put the notes repository where the agent works and point it at `AGENTS.md` (Claude Code reads `CLAUDE.md`, which contains `@AGENTS.md`; Codex reads `AGENTS.md` directly). The entry point lists the read order and the rules that must never be missed. The skill finds its own `tools/`, `docs/` and `template/` next to `SKILL.md`, so no environment variable or install path is needed.

## The ideas in six lines

1. One source of truth; current state and history are separate; everything is dated in one time zone.
2. Evidence, not conclusions: exact commands, ids, numbers, the undo, the lesson.
3. Relations are explicit: canonical home per fact, references by file name, a dependency matrix, a ledger of derived copies.
4. Git is the history (no `.bak` files); small, described, frequent commits.
5. No secrets in the tree, enforced by a hook, a publication gate and a periodic scan; copies are checksummed, mirrored, snapshotted and restore-drilled.
6. Honest status words: "not verified", "NOT synced", "pending". Never mark something done that is not.

## Tests

```bash
python3 tests/native.py     # Linux, macOS, Windows: no bash needed, runs the real launchers
bash tests/smoke.sh         # Linux and macOS: the same ground plus manifest and specification checks
```
Both run automatically for every push (GitHub Actions: `native.py` on Linux, macOS and Windows, `smoke.sh` on Linux and macOS). They check the plugin manifests and the skill file against the Agent Skills specification, then copy **only** the skill folder to a temporary place and, from that copy, bootstrap a tree and exercise commit, hook, lint, map, mirror, restore drill and the team workflow (branch, push, CI check, per-clone setup). The team workflow has also been run live against GitHub (pull request that passes, pull request with a planted fake secret that fails).

## Contributing

See `AGENTS.md` for the repository layout and the rules for changing the kit.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
