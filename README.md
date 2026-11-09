# Myco Notes

*Linked, versioned, secret-free project notes for you and your AI agents.*

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
| `tools/notes-commit` | One command to commit with a described message: syntax checks, optional AI co-author trailer, optional sync of executed files, optional mirror push, optional milestone tag, and for teams `--branch`, `--push`, `--pr`. |
| `tools/hooks/pre-commit`, `tools/secret-scan` | Refuse commits whose added lines look like secrets (versioned; activated with `core.hooksPath`; the same rules run in CI). |
| `tools/notes-lint.py` | Finds missing references, duplicate heading numbers, stale "last updated" headers, passed follow-up dates, incomplete ledger rows, secrets, oversized notes and an `AGENTS.md` that is too big for the agents that cut it off. Records in `archive/` and `logs/` are not re-checked for dates and references. |
| `tools/build-notes-map.py` | Builds a static, searchable map: notes grouped by purpose, **who mentions whom**, backlinks, per-note git history, recent commits. Refuses to build if a note contains a secret. |
| `tools/mirror-push`, `tools/restore-drill` | A second copy of the repository, and proof that it can be restored. |
| `tools/bootstrap` | Creates a new notes repository from the template in one command, with everything in one `myco-notes/` folder and optional project data folders (`--data-dir`). |
| `tools/relocate` | Moves an older tree (notes/, tools/, docs/ at the root) into the single folder, or renames that folder: dry run first, keeps your folder names, rewrites the path references. |
| `tools/ci-check`, `tools/setup-clone`, `docs/TEAM.md`, `template/.github/` | Team use: a pull-request check (secret scan + lint), per-clone setup, CODEOWNERS and PR template, and the step-by-step guide for GitHub or GitHub Enterprise. |

At the repository root: `.claude-plugin/` (Claude Code plugin and marketplace manifests), `tests/` (`native.py`, `smoke.sh`), `examples/`, `LICENSE`, `NOTICE`.

## Install

### Claude Code (one command)
```
/plugin marketplace add LuzianMe/myco-notes
/plugin install myco-notes@myco-notes
```
Then ask Claude to "start a Myco Notes tree for my project", "update the notes", "audit the notes" or "commit the notes".

### OpenAI Codex
Codex reads skills from `~/.agents/skills` (all your projects) or `.agents/skills` inside a repository, and follows symlinks. Clone the kit once and link the skill folder:
```bash
git clone https://github.com/LuzianMe/myco-notes.git ~/.agents/myco-notes-kit
mkdir -p ~/.agents/skills
ln -s ~/.agents/myco-notes-kit/skills/myco-notes ~/.agents/skills/myco-notes
```
Restart Codex if the skill does not appear, then use the same requests as above. (Tried under Codex on Windows: the skill is discovered as "Myco Notes" and builds a tree. Please report anything that differs.)

### Other agents
Any agent that supports Agent Skills: copy or link `skills/myco-notes/` into its skills folder; the folder is self-contained. Any other agent: clone the repository and tell it to read `skills/myco-notes/SKILL.md` as a procedure; once a notes tree exists, point it at the tree's `AGENTS.md`.

### No agent
Use the tools directly (below). The method is plain Markdown plus git.

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

Trees made with 0.5.x or earlier (notes/, tools/, docs/ at the root) keep working unchanged; `relocate` converts one:

```bash
python3 <kit>/tools/relocate.py --root ~/projects/old-notes            # dry run: shows the moves and the path rewrites
python3 <kit>/tools/relocate.py --root ~/projects/old-notes --apply    # then review git diff, run the lint, commit
```

## Quick start (without an agent)

```bash
git clone https://github.com/LuzianMe/myco-notes.git
cd myco-notes/skills/myco-notes
tools/bootstrap ~/projects/my-project --name "My Project" --owner "Your Name" --tz "UTC" --data-dir files-input --data-dir files-output
cd ~/projects/my-project
# edit myco-notes/working-agreement.md and myco-notes/state.md, then:
myco-notes/tools/notes-commit "Describe the first real change and why"
python3 myco-notes/tools/notes-lint.py
python3 myco-notes/tools/build-notes-map.py && xdg-open myco-notes/map/index.html
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
