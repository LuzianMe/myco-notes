---
summary: The kit's tools, the folder layout, new folders and the configuration; read to find a tool, a flag or a setting
area: Kit documents
---
# Myco Notes reference: the tools, the layout, new folders and the configuration

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
| `search WORDS` | The notes that hold the words, ranked, with summaries and matching lines; `"a phrase"`, `--notes-only`. |
| `ingest` | Keep an outside document as a source; `--list` shows the sources and who cites them. |
| `notes-lint.py` | References, headings, dates, freshness header, summaries, sync-log format, ledger, sizes, secrets. |
| `asof DATE [NOTE]` | What the notes said on a date; `--since`, `--grep`, `--history NOTE`. |
| `build-notes-map.py` | The searchable map with backlinks and history, and `graph.html` (the mycelium view); `--public` writes a public graph for a website (section 6); `--layout wiki` lays the map out like a wiki site (section 7). |
| `mirror-push`, `restore-drill` | A second copy, and proof that it can be restored. |
| `doctor` | Read-only health check: kit version, hook, layout, settings. |
| `bootstrap` | A new notes repository (`--data-dir`, `--new-folders`), or take over a folder (`--import`, `--adopt`). Run from the kit. |
| `relocate` | Move an older notes repository into the single folder, or refresh a notes repository's tools and docs from a newer kit; `--move-reviews` moves review files kept in `plans/` into `reviews/` (format 1.2). Run from the kit. |
| `secret-scan`, `hooks/pre-commit`, `ci-check`, `setup-clone` | The secret rules, the commit hook (secret scan of the added lines), the pull-request check (secret scan and lint), per-clone set-up. |

## 2. Layout of a notes repository

```
my-project/
  AGENTS.md  CLAUDE.md  .github/  .gitignore  .gitattributes  .myco-notes.conf     (agents, git and the host look for these at the root)
  myco-notes/        the notes (state.md, runbook.md, one note per component, plans/, reviews/, logs/, inbox/, sources/, ...)
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

## 4. Files a notes repository has (created by `bootstrap`)

`AGENTS.md`/`CLAUDE.md`; `<notes>/working-agreement.md`; `<notes>/state.md`; `<notes>/runbook.md`; `<notes>/sync-tracker.md`; `<notes>/plans/backlog.md`; `<notes>/logs/`; `<notes>/scripts/`; `<notes>/verification/verification.md`; `<notes>/archive/`; `.myco-notes.conf`; `<tools>/`; `<docs>/` (`<notes>` is `myco-notes` by default, so these are `myco-notes/state.md` and so on).

## 5. Configuration

`.myco-notes.conf` (shell syntax): the layout (`MYCO_DIR`, `NOTES_DIR`, `TOOLS_DIR`, `DOCS_DIR`, `MAP_DIR`, `DATA_DIRS`, `HISTORY_DIRS`, `STATE_FILE` for a master record not called `state.md`), the lint limits (`MAX_NOTE_KB`, `ENTRY_WARN_KB`, `STALE_DAYS` for the freshness header, `RESUME_BUDGET` for `resume`, `REVIEW_FULL_DAYS` for how often a review reads every note), `AGENT_TRAILER` (co-author line for commits made by an agent), `SYNC_GLOBS`/`SYNC_CMD` (keep the live copy of executed files equal to the committed copy), `TIMEZONE` (IANA name for the times `capture` writes), `SOLO` (1 = one owner: an agent merges its own pull request after the check passes, method 19.2), `NEW_FOLDERS` (`ask` default, `add`, `ignorelint`, `ignoreall`: what `notes-commit` does with a new root folder or loose file; `notes-commit --folder NAME=MODE` answers for one item, `NAME=*` for all, `later` leaves it out of this commit), `CHECK_SH`/`CHECK_PY`, `MIRROR_TARGET`, `POST_PUSH_CMDS`, `SECRET_ALLOW_FILE`. Optional `.myco-notes-map.json` (groups, hints, title, and for the wiki layout `layout` and `theme`, section 7) and `.myco-notes-lint-ignore` (regexes of findings to drop).

## 6. The mycelium view on a website

`graph.html` is one self-contained file: no server, no network requests, no libraries. Two things make it safe and easy to show on another site.

### 6.1 A public graph: `build-notes-map.py --public`

```bash
python3 myco-notes/tools/build-notes-map.py --public --labels labels.json --title "My homelab" --out ../my-site/graph
```

It writes only `<out>/graph.html` (the folder is created if needed; other files in it are left alone). The file keeps only what drawing and the replay need: a number for each note, its group number, hub and history flags, link counts, the commit it was born in and last changed in, the links, and per commit its time and the notes it touched and added. It drops note names, titles, paths, file names, sizes, follow-ups, missing references, commit subjects, group names and the project title. `--title` is the only title it carries (default: none). The page always opens in embed mode (6.2).

`--labels` is the approved list, one JSON object keyed by the note's file name without `.md`: a note in the list is drawn with that label, every other note is an unlabelled dot whose name appears nowhere in the file. Notes that share a file name in different folders all get the label. A label that matches no note is reported and left out.

```json
{"frigate": "Cameras", "home-assistant": "Home Assistant", "router": "Network"}
```

The build refuses, as the full map does, when a note or a label looks like it contains a secret. A public graph is a copy of the notes: record it in the derived-copy ledger (method 9, item 5) and rebuild it when the notes change.

### 6.2 Embed mode and its options

| URL option | Effect |
|---|---|
| `?embed=1` | Only the network and its labels: no panels, tool bar, replay panel, Find, hint or note panel, and no links out. The page and canvas are transparent (`color-scheme: normal`), so the host page shows through, and the network fades out towards the edges of the frame; the theme keeps its node, thread and label colours. Lighter drawing than the full view (threads as plain lines without their glow, about 30 frames a second while it turns by itself, at most 1.5 device pixels per pixel). Labels show only on a frame of at least 360x240, at the fitted size or closer, and where the notes are not crowded together. A public graph is always in embed mode. |
| `?theme=<id>` | The theme, as in the full view: `light`, `dark`, `mycelium`, `fruit`, `matrix`, `amber`, `contrast`, `deepsea`, `paper` (or `auto`). Embed mode never uses a choice stored in the browser. |
| `?interactive=0` | No pointer, wheel or touch handling at all (no selecting either): a preview that only turns by itself, so the host page keeps its own scrolling and swiping. |
| `?replay=1` | Start with the replay of the history instead of the finished graph. |
| `?depth=0` | The flat view instead of the ball. |

Interaction in embed mode (unless `interactive=0`): drag with the mouse or one finger to turn the network about its upright axis (the tilt stays at the gentle view from slightly above); scroll, a trackpad pinch or two fingers zoom about the middle of the network, which stays centred, from half the fitted size up to four times it; a double-click fits it again. A click or tap on a note (one that does not move) selects it, as in the full view: the note and its neighbours stay lit, the rest dims, and their labels show where they have one; a click or tap on empty space, on the selected note again, or Escape clears it. Only the highlight: no note panel, nothing beyond what the page already holds. Left alone it turns slowly by itself; with `prefers-reduced-motion` it does not, and a selection holds it still until it is cleared.

Drawing pauses while the page is hidden (`visibilitychange`) and while the host page asks for it.

### 6.3 Options of the full view

| URL option | Effect |
|---|---|
| `?spin=1` | The network turns by itself when left alone, for this visit. Off by default: the **Spin** button in the tool bar turns it on (and off), and the choice is kept in the browser. An embedded graph always turns by itself; the screensaver turns it while it is on. A drag still turns the network by hand either way. |
| `?perf=1` | A small panel with the frame rate, how long a frame's own work takes and where it goes (simulation, threads, notes), the pixel density, the settings that decide the cost, the graphics card, how much of the screen the thread layer paints and a 2D canvas test (a few ms: hardware canvas; tens: the browser draws it on the processor). **Copy numbers** puts them in the clipboard as one line, to compare two ways of drawing on the same machine. |
| `?gl=0` | Switch the GPU drawing off. By default (since 0.46.0), where the browser has WebGL 2, the graphics card draws the quiet threads, and in the themes whose notes are plain discs the notes and the selected note's threads too: the threads' paths go into a texture once and are turned, widened, faded with the depth and given their glow and buds by a shader in every frame, so nothing is rebuilt while the view moves; Mycelium, Deep sea, Light, Dark and High contrast. The names, spikes and ripples stay on the 2D canvas, and in Fruit and Paper (drawn notes) the notes do. Matrix and Amber terminal, an embed, and a browser without WebGL 2 use the 2D drawing (`?perf=1` says which is in use). |

On a slow machine the 2D drawing steps down by itself, one step at a time and never back: a screen with 2 device pixels per pixel drops to 1.5, then the threads are redrawn less often while the view turns, then they become plain lines.

**Messages** (`window.postMessage`). The page accepts these only from its parent window (`event.source === window.parent`) and ignores anything else:

| From the host page | Effect |
|---|---|
| `{type: "myco-theme", theme: "<id>"}` | Switch the theme live, without a reload (`"auto"` follows the system). |
| `{type: "myco-pause"}` | Stop drawing (for a slide that is not showing). |
| `{type: "myco-resume"}` | Draw again. |

| To the host page | When |
|---|---|
| `{type: "myco-ready"}` | Once, when the first frame is drawn (an iframe that starts hidden, with no size, sends it once it is shown). |
| `{type: "myco-select", selected: true/false, label: "..."}` | When the selection changes; `label` is the note's label (in a public graph: the approved label), or `null` for a note without one and when the selection is cleared (`selected: false`). |
| `{type: "myco-error", message: "..."}` | Once, if something fails; `message` is the browser's error text. |

```html
<iframe id="notes" src="graph/graph.html?theme=deepsea" title="My notes as a network"
        style="width:100%;height:480px;border:0" loading="lazy"></iframe>
<script>
  const f = document.getElementById("notes");
  addEventListener("message", e => {
    if (e.source === f.contentWindow && e.data && e.data.type === "myco-ready") console.log("graph ready");
  });
  // a slide that goes out of view: f.contentWindow.postMessage({type: "myco-pause"}, "*")
  // and back: {type: "myco-resume"}; a theme switch: {type: "myco-theme", theme: "amber"}
</script>
```

If the host page sets its own `color-scheme` (for example `dark`), give the iframe `style="color-scheme: normal"`: browsers paint an opaque background behind an iframe whose colour scheme differs from its page's.

## 7. The wiki layout of the map

`build-notes-map.py` makes the classic map by default. `--layout wiki` (or `"layout": "wiki"` in `.myco-notes-map.json`; the option wins over the file) lays out the same notes, relations, groups, freshness and history like a wiki site. `graph.html`, `raw/`, the page names (`index.html`, `p/<name>.html`) and the rules about the output folder, the secret check, `DATA_DIRS` and `--public` are the same; the layout only changes how the pages look and adds `recent.html` and an `assets/` folder (open `index.html` from the folder; nothing is fetched from the network).

- **Every note page:** a left tree of the groups (the current note marked, a filter box; on a phone it opens as a menu), breadcrumbs, a header with the one-line summary, the freshness status (`Review due since...`, `Confirmed...`, `Superseded`, `Expired`) and the header's dates, the last edit from git, the raw file, the follow-up dates that have passed and the missing references; the article with a sticky "On this page" outline on the right (on a narrow screen a collapsed one above the article); then "What links here" and "Mentions" (each linked note with its title, summary and how often it is mentioned), the note's history, and previous and next within its group. A note that needs a look (a passed follow-up date, a missing reference, a review or a validity date that has passed) has a mark in the tree and on the front page.
- **Long notes (0.44.1):** a long heading shows its start with the parenthesis below it; very long paragraphs, list items and table cells are clipped with Show more; in a note over 40 KB the top-level sections over 12 KB are folded; on a phone a table of three or more columns is one card per row. All of it is added by `wiki.js` (without the script, and when printing, everything shows in full).
- **Links:** wiki links (`[[Note]]`, `[[Note|text]]`, `[[Note#Heading]]`), relative Markdown links and file names written in the text or alone in a code span become links; one that points to something that is not a note is shown as plain text with a dotted line. Without the `markdown` package a page is shown as preformatted text with the same links (and no outline).
- **Search:** the box in the top bar searches the text of every note (key `/`, arrows and Enter, Escape). The text is in `assets/search.js`, loaded only when someone searches. The text of every note is in `raw/` already, so this shows nothing the folder did not hold; the secret check ran first.
- **Recently changed:** `recent.html` lists the latest commits that touched a note by day, with the notes they changed.
- **Theme:** the reader's picker (Auto, Light, Dark and the others) works as before. A project can set its own look in `.myco-notes-map.json` without touching the kit:

```json
{
  "layout": "wiki",
  "theme": {
    "light": {"accent": "#7a3e00", "bg": "#fbf7f0"},
    "dark":  {"accent": "#ffb454"},
    "font": "Georgia, serif",
    "mono": "ui-monospace, Menlo, monospace",
    "radius": "4px"
  }
}
```

`light` and `dark` change the colours of the Light and Dark themes (so Auto too; the other themes of the picker stay the kit's own): `bg`, `panel`, `fg`, `muted`, `line`, `accent`, `code`, each as `#rgb` or `#rrggbb`. `font`, `mono` (code) and `radius` are optional; everything else in the layout is a CSS variable (`assets/wiki.css`) derived from these. The build refuses a value that is not what it says, and warns (it still builds) when a colour pair of Light or Dark is under the 4.5:1 contrast for text.
