#!/usr/bin/env python3
"""bootstrap: create a new notes repository from the Myco Notes template.

  tools/bootstrap <target-dir> --name "Project name" [--owner "Name"] [--tz "MST (UTC-7)"] [--no-commit]
                  [--myco-dir myco-notes] [--layout nested|flat] [--data-dir files-input --data-dir files-output ...]
                  [--new-folders ask|add|ignorelint|ignoreall]

Layout (default nested): one folder, myco-notes/, holds the notes, tools/, docs/ and map/; only the files agents and git look for at the
root (AGENTS.md, CLAUDE.md, .github/, .gitignore, .gitattributes, .myco-notes.conf) stay outside it, so the root stays free for the
project's own folders. --layout flat gives the older arrangement (notes/, tools/, docs/ and notes-map/ at the root).
--data-dir (repeatable) names a project folder that is not notes (inputs, outputs, attachments): it is created, gitignored, listed in
the conf as DATA_DIRS and left out of the lint and the map.

--new-folders sets what notes-commit does with a new folder or loose file in the root (NEW_FOLDERS in the conf): ask (default; it stops and the
agent asks the owner), add (track it and lint it as notes), ignorelint (track it, skip the lint and the map), ignoreall (do not track, do not lint).
An agent setting up a notes repository for a person asks them which one they want first.

Copies template/ into <target-dir>, fills the {{PLACEHOLDERS}}, copies tools/ and docs/*.md, makes git use the versioned hooks
(core.hooksPath = <tools folder>/hooks), and makes the baseline commit. The target must be empty or not exist.

Existing notes (method section 20):
  bootstrap <new-dir> --name "Notes" --import <folder>     a new notes repository; the folder is copied as found into <notes>/imported/<folder name>/
                                                            (the folder itself is not touched; app settings such as .obsidian/ are left out)
  bootstrap <folder> --name "Notes" --adopt [--backup-to DIR | --no-backup]
                                                            the folder becomes the repository, its notes stay where they are. First a zip
                                                            of the whole folder is written next to it (or into DIR), and a folder that
                                                            is already a git repository (with a clean working tree) gets the tag
                                                            before-myco-notes. The rules of an existing AGENTS.md keep working: its
                                                            text follows the new entry point under "Your project rules" (a CLAUDE.md
                                                            with rules of its own keeps them after @AGENTS.md). Other files the
                                                            template would overwrite are kept as <name>.pre-myco<ext>; .gitignore and
                                                            .gitattributes are extended.
Both scan the collection for secrets first: a file with a secret-looking string is not committed (listed, value hidden).
Both write the import log <notes>/logs/import-<name>.md: the choice, the backup, an inventory and one row per note to work through.
Exit: 0 done, 1 refused (nothing changed), 2 usage, 4 done but files with secrets were left uncommitted (listed).
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402
import secret_scan  # noqa: E402

NOT_COPIED = {"bootstrap", "bootstrap.cmd", "bootstrap.py", "__pycache__"}
TEXT_EXT = (".md", ".yml", ".yaml")
TEXT_NAMES = {".myco-notes.conf", ".gitignore", "CODEOWNERS"}
NOT_NOTES = {".git", ".obsidian", ".trash", ".logseq", ".foam", ".vscode", ".idea", "node_modules", "__pycache__", ".DS_Store", "Thumbs.db", "desktop.ini"}
APPENDED = {".gitignore", ".gitattributes"}   # adopt: extended, never replaced
ENTRY = ("AGENTS.md", "CLAUDE.md")             # adopt: the owner's rules stay in effect next to the new entry point (method 20.2)
OWNER_RULES = ("## Your project rules (kept from before Myco Notes)\n\n"
               "These rules were in this folder's `AGENTS.md` before Myco Notes was added, and they still apply alongside the ones above. "
               "Where the two disagree, ask the owner; do not pick one silently. Tidying them up (moving facts into the notes, "
               "shortening what repeats) is part of the first pass (method 20.4) and needs the owner's yes.\n\n")
CLAUDE_RULES = ("## Rules for agents that read CLAUDE.md (kept from before Myco Notes)\n\n"
                "These rules were in this folder's `CLAUDE.md` before Myco Notes was added, and they still apply "
                "alongside `AGENTS.md` (method 20.2).\n\n")


def pointer_only(text, name):
    """Whether an entry file holds nothing but a pointer to the other one (@AGENTS.md, or a symlink's target text)."""
    return text.strip() in ("@" + name, name)


def merge_entry(target, old):
    """Put the owner's earlier AGENTS.md text after the new entry point, and a CLAUDE.md's own rules after @AGENTS.md. Returns what was kept where."""
    agents, claude = old.get("AGENTS.md"), old.get("CLAUDE.md")
    if agents is not None and (pointer_only(agents, "CLAUDE.md") or not agents.strip()):
        agents = None
    if claude is not None and (pointer_only(claude, "AGENTS.md") or not claude.strip() or (agents is not None and claude.strip() == agents.strip())):
        claude = None
    done = []
    for name, text, head, lead in (("AGENTS.md", agents, OWNER_RULES, None), ("CLAUDE.md", claude, CLAUDE_RULES, "@AGENTS.md\n")):
        if text is None:
            continue
        p = os.path.join(target, name)
        with open(p, encoding="utf-8", newline="") as fh:
            new = fh.read() if lead is None else lead
        body = text if text.endswith("\n") else text + "\n"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(new.rstrip("\n") + "\n\n" + head + body)
        done.append(name)
    return done


def check_adopt(target, lay, a):
    """--adopt: refuse anything that could lose or mix up the owner's files. Returns whether the folder is already a git repository, or an exit code."""
    if not os.path.isdir(target) or not os.listdir(target):
        print(f"bootstrap: --adopt needs an existing folder with notes in it; {target} is missing or empty (leave out --adopt for a new notes repository)", file=sys.stderr)
        return 1
    if os.path.exists(os.path.join(target, ".myco-notes.conf")):
        print("bootstrap: this folder is a Myco Notes repository already; to update its tools run relocate.py --root from the kit", file=sys.stderr)
        return 1
    for d in ([lay["myco"]] if lay["myco"] else [lay["notes"], lay["tools"], lay["docs"]]):
        if os.path.exists(os.path.join(target, *d.split("/"))):
            print(f"bootstrap: the folder already has {d}/; choose another name for the Myco Notes folder with --myco-dir", file=sys.stderr)
            return 1
    top = _myco.toplevel(target)
    if top and _myco.overlap(top, target) != "same":
        print(f"bootstrap: {target} is inside another git repository ({top}); adopt that repository's root folder, or copy the notes with --import", file=sys.stderr)
        return 1
    if top and _myco.git("-C", target, "status", "--porcelain").stdout.strip():
        print("bootstrap: the folder's git repository has uncommitted changes; commit or stash them first, so the take-over starts from a known state", file=sys.stderr)
        return 1
    return bool(top)


def make_backup(target, to):
    """A zip of the whole folder (with its .git, if any) outside it; verified by reading it back. Returns its path, or None."""
    dest_dir = os.path.abspath(to) if to else os.path.dirname(target)
    if _myco.overlap(target, dest_dir) in ("same", "inside"):
        print("bootstrap: the backup must go outside the folder being adopted (--backup-to)", file=sys.stderr)
        return None
    os.makedirs(dest_dir, exist_ok=True)
    base = os.path.basename(target.rstrip(os.sep)) or "notes"
    path = os.path.join(dest_dir, f"{base}-before-myco-notes-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.zip")
    count = 0
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for dp, dn, fn in os.walk(target):
                dn.sort()
                for f in sorted(fn):
                    full = os.path.join(dp, f)
                    if os.path.isfile(full):
                        z.write(full, base + "/" + os.path.relpath(full, target).replace(os.sep, "/"))
                        count += 1
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None or len(z.namelist()) != count:
                raise OSError("the archive does not read back complete")
    except OSError as e:
        print(f"bootstrap: backup failed ({e}); nothing was changed", file=sys.stderr)
        return None
    print(f"bootstrap: backup written: {path} ({_myco.human_size(os.path.getsize(path))}, {count} files)")
    return path


def collect(root):
    """The owner's files under root (relative, forward slashes), without version-control data and notes-app settings or caches."""
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in NOT_NOTES)
        for f in sorted(fn):
            if f not in NOT_NOTES:
                out.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    return out


def scan(root, rels):
    """Secret-looking strings in text files: [(rel, line, kind)]; values are never returned."""
    hits = []
    for rel in rels:
        p = os.path.join(root, *rel.split("/"))
        try:
            if os.path.getsize(p) > 5 * 1024 * 1024:
                continue
            with open(p, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        if b"\0" in raw[:8192]:
            continue
        for i, line in enumerate(raw.decode("utf-8", errors="replace").split("\n"), 1):
            hit = secret_scan.find(line)
            if hit:
                hits.append((rel, i, hit[0]))
    return hits


def write_import_log(target, lay, project, mode, files, hits, backup, kept, had_git, source=None, name=None, merged=()):
    """The import log (method 20.3): the choice, the backup, an inventory and one row per note. Returns its path in the repository."""
    name = name or re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(target)).strip("-.") or "notes"
    rel_log = f"{lay['notes']}/logs/import-{name}.md"
    md = [f for f in files if f.lower().endswith(".md")]
    other = [f for f in files if not f.lower().endswith(".md")]
    size = lambda f: os.path.getsize(os.path.join(target, *f.split("/")))
    index = _myco.LinkIndex(md, files)
    held = {h[0] for h in hits}
    rows, keys, styles, broken = [], {}, {"wiki": 0, "path": 0}, 0
    for f in md:
        with open(os.path.join(target, *f.split("/")), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        fm, end = _myco.frontmatter(text)
        for k in fm:
            keys[k] = keys.get(k, 0) + 1
        h = re.search(r"^#\s+(.+)$", "\n".join(text.split("\n")[end:]), re.M)
        title = re.sub(r"[|`]", "", h.group(1)).strip()[:70] if h else "(no heading)"
        n_links = 0
        for kind, tgt, _ln in _myco.links(text):
            styles[kind] += 1
            n_links += 1
            if index.resolve(kind, tgt, f) is None:
                broken += 1
        rows.append(f"| `{f}` | {title} | {max(1, round(size(f) / 1024))} | {n_links} | {'held: secret' if f in held else 'pending'} |")
    today = datetime.date.today().isoformat()
    where = (f"A new notes repository; the notes were copied as found from the folder `{os.path.basename(source)}` into `{lay['notes']}/imported/{name}/`. The original folder was not changed."
             if source else "In place: the notes stay at their paths in this folder; the Myco Notes files were added around them.")
    if backup:
        where += f" Backup of the folder as it was: `{os.path.basename(backup)}` ({'next to this folder' if os.path.dirname(backup) == os.path.dirname(target) else 'in the backup folder chosen'})."
    elif not source:
        where += " No backup archive was made (--no-backup)."
    if had_git:
        where += " The last commit before the take-over is tagged `before-myco-notes`."
    lines = [
        f"# Import log: {project}",
        "",
        f"Effort log (method section 20). Started {today}. Later entry wins; the import is finished when no row below is `pending`.",
        "",
        "## Choice",
        f"- **Where:** {where}",
        "- **How far:** _(ask the owner: keep the structure, or reorganise into the method's roles; method 20.1)_",
        "",
        "## Inventory (as found)",
        f"- {len(md)} notes, {len(other)} other files ({_myco.human_size(sum(size(f) for f in other)) if other else '0B'}).",
        f"- Links: {styles['wiki']} wiki links, {styles['path']} relative links, {broken} pointing nowhere (the lint lists them).",
        "- Header keys: " + (", ".join(f"{k} ({v})" for k, v in sorted(keys.items(), key=lambda kv: -kv[1])[:12]) or "none") + ".",
        f"- Secrets: {len(hits)} secret-looking string(s) in {len(held)} file(s); those files are not committed (marked `held`)." if hits else "- Secrets: none found.",
    ]
    if merged:
        lines.append("- Entry files: the rules of your earlier " + " and ".join(f"`{m}`" for m in merged) + " still apply; they follow the new "
                     "entry point in the same file. Propose how to tidy them up in the first pass (method 20.2, 20.4).")
    if kept:
        lines.append("- Kept under a new name (merge into the working agreement): " + ", ".join(f"`{o}` (was {n})" for o, n in kept) + ".")
    if other:
        exts = {}
        for f in other:
            e = os.path.splitext(f)[1].lower() or "(none)"
            exts[e] = exts.get(e, 0) + 1
        lines.append("- Other files by type: " + ", ".join(f"{e} {c}" for e, c in sorted(exts.items(), key=lambda kv: -kv[1])[:10]) + ".")
    lines += ["", "## Decisions and open questions", "_(duplicates, contradictions, what was left out and why; newest first)_", "",
              "## Notes", "Status: `pending`, `kept`, `merged into x.md`, `became x.md`, `left out: reason`, `held: secret`.", "",
              "| Note | Title | KB | Links | Status |", "|---|---|---|---|---|", *rows, ""]
    path = os.path.join(target, *rel_log.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    return rel_log


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(prog="bootstrap", add_help=True)
    ap.add_argument("target")
    ap.add_argument("--name", required=True)
    ap.add_argument("--owner", default=None)
    ap.add_argument("--tz", default="UTC")
    ap.add_argument("--no-commit", action="store_true")
    ap.add_argument("--layout", choices=("nested", "flat"), default="nested")
    ap.add_argument("--myco-dir", default="myco-notes")
    ap.add_argument("--data-dir", action="append", default=[])
    ap.add_argument("--new-folders", choices=("ask", "add", "ignorelint", "ignoreall"), default="ask")
    ap.add_argument("--import", dest="source", default=None, metavar="FOLDER")
    ap.add_argument("--adopt", action="store_true")
    ap.add_argument("--backup-to", default=None)
    ap.add_argument("--no-backup", action="store_true")
    a = ap.parse_args()
    if a.source and a.adopt:
        print("bootstrap: use either --import FOLDER (a new notes repository with a copy) or --adopt (the folder itself), not both", file=sys.stderr)
        return 2
    if (a.backup_to or a.no_backup) and not a.adopt:
        print("bootstrap: --backup-to and --no-backup go with --adopt", file=sys.stderr)
        return 2
    owner = a.owner or _myco.git("config", "user.name").stdout.strip() or "owner"

    my = _myco._rel(a.myco_dir) if a.layout == "nested" else ""
    if a.layout == "nested" and (not my or my.startswith(".")):
        print("bootstrap: --myco-dir must be a plain folder name", file=sys.stderr)
        return 2
    data = [d for d in (_myco._rel(x) for x in a.data_dir) if d]
    lay =_myco.layout("", {"MYCO_DIR": my} if my else {})   # same defaults every tool derives later

    def at(rel):
        return os.path.join(target, *rel.split("/"))

    target = os.path.abspath(a.target)
    had_git, backup, kept = False, None, []
    if a.adopt:
        r = check_adopt(target, lay, a)
        if type(r) is int:   # an exit code (a bool means: refused or not, already a git repository)
            return r
        had_git = r
    else:
        if os.path.exists(target) and os.listdir(target):
            print(f"bootstrap: {target} exists and is not empty" + ("" if a.source else " (to take over the notes in it, add --adopt; method section 20)"), file=sys.stderr)
            return 1
        if a.source:
            src = os.path.abspath(a.source)
            if not os.path.isdir(src) or not os.listdir(src):
                print(f"bootstrap: --import {a.source}: not a folder, or empty", file=sys.stderr)
                return 1
            if _myco.overlap(src, target):
                print("bootstrap: the new notes repository and the imported folder must not contain each other", file=sys.stderr)
                return 1
    if a.adopt and not a.no_backup:
        backup = make_backup(target, a.backup_to)
        if not backup:
            return 1
    if a.adopt and had_git and _myco.git("-C", target, "rev-parse", "-q", "--verify", "HEAD").returncode == 0:
        if _myco.git("-C", target, "tag", "before-myco-notes").returncode == 0:
            print("bootstrap: tagged the last commit before the take-over: before-myco-notes")
    collection = sorted(collect(target)) if a.adopt else []   # the owner's files, before anything is added
    os.makedirs(target, exist_ok=True)
    hits = scan(target, collection)
    held, rc = sorted({h[0] for h in hits}), 0
    if not had_git:
        if _myco.git("-C", target, "init", "-q", "-b", "main").returncode != 0:  # git older than 2.28
            _myco.git("-C", target, "init", "-q")
            _myco.git("-C", target, "symbolic-ref", "HEAD", "refs/heads/main")

    def commit(msg, paths=None):
        if a.no_commit:
            return
        if paths is None:
            _myco.git("-C", target, "add", "-A")
        for i in range(0, len(paths or []), 200):   # in chunks (command-line length); paths the owner's .gitignore excludes stay out
            _myco.git("-C", target, "-c", "advice.addIgnoredFile=false", "add", "-A", "--", *paths[i:i + 200])
        for i in range(0, len(held), 200):
            _myco.git("-C", target, "rm", "-q", "--cached", "--ignore-unmatch", "--", *held[i:i + 200])
        if not _myco.git("-C", target, "diff", "--cached", "--quiet").returncode:
            return
        r = subprocess.run(["git", "-C", target, "commit", "-q", "-m", msg], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            print(f"bootstrap: commit failed ({(r.stderr or r.stdout).strip()}); set git user.name and user.email, then commit", file=sys.stderr)
        else:
            print(_myco.git("-C", target, "log", "--oneline", "-1").stdout.strip())

    if a.adopt and not had_git:   # the owner's notes exactly as found, before anything is added (secrets held back)
        commit("Before Myco Notes: the notes as found", collection)

    entry_old = {}   # adopt: the owner's AGENTS.md / CLAUDE.md text (read before either is replaced: one may link to the other)
    for name in ENTRY if a.adopt else ():
        p = os.path.join(target, name)
        if os.path.lexists(p) and name not in held:
            try:
                with open(p, encoding="utf-8", newline="") as fh:
                    entry_old[name] = fh.read()
            except (OSError, UnicodeDecodeError):
                pass   # unreadable or a dangling link: kept under a new name below, like any other file
    written = []   # files this run writes from the template (placeholders are filled only in these, never in the owner's notes)

    def put(src, dest):
        name = os.path.basename(dest)
        if name in entry_old and os.path.dirname(dest) == target and os.path.lexists(dest):
            os.remove(dest)   # its text is in entry_old and comes back after the new entry point; a symlink becomes a plain file
        if os.path.lexists(dest):
            if name in APPENDED:
                with open(src, encoding="utf-8", newline="") as fh:
                    extra = fh.read()
                with open(dest, encoding="utf-8", newline="") as fh:
                    old_text = fh.read()
                with open(dest, "a", encoding="utf-8", newline="") as fh:
                    fh.write(("" if old_text.endswith("\n") or not old_text else "\n") + "\n# Added by Myco Notes\n" + extra)
                written.append(dest)
                return
            stem, ext = os.path.splitext(dest)
            keep = stem + ".pre-myco" + ext
            n = 2
            while os.path.exists(keep):
                keep, n = f"{stem}.pre-myco{n}{ext}", n + 1
            os.replace(dest, keep)
            rel_dest, rel_keep = (os.path.relpath(x, target).replace(os.sep, "/") for x in (dest, keep))
            if rel_dest in held:   # a held file keeps being held under its new name; the template's file takes the old name
                held[held.index(rel_dest)] = rel_keep
            kept.append((os.path.relpath(keep, target).replace(os.sep, "/"), os.path.relpath(dest, target).replace(os.sep, "/")))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        written.append(dest)

    def put_tree(src, dest, skip=()):
        for dp, dn, fn in os.walk(src):
            dn[:] = [d for d in dn if d not in skip]
            for f in fn:
                if f in skip:
                    continue
                put(os.path.join(dp, f), os.path.join(dest, os.path.relpath(os.path.join(dp, f), src)))

    tpl = os.path.join(KIT, "template")
    for item in sorted(os.listdir(tpl)):
        src = os.path.join(tpl, item)
        if item == "notes":   # the template's notes folder lands in the notes folder of the chosen layout
            put_tree(src, at(lay["notes"]))
        elif os.path.isdir(src):
            put_tree(src, os.path.join(target, item))
        else:   # template/gitattributes becomes the repository's .gitattributes (in the kit it must not apply to the kit's own files)
            put(src, os.path.join(target, "." + item if item == "gitattributes" else item))
    put_tree(HERE, at(lay["tools"]), skip=NOT_COPIED)
    docs = os.path.join(KIT, "docs")
    os.makedirs(at(lay["docs"]), exist_ok=True)
    if os.path.isdir(docs):
        for f in os.listdir(docs):
            if f.endswith(".md"):
                put(os.path.join(docs, f), os.path.join(at(lay["docs"]), f))

    subs = (("{{PROJECT_NAME}}", a.name), ("{{OWNER}}", owner), ("{{TIMEZONE}}", a.tz), ("{{DATE}}", datetime.date.today().isoformat()),
            ("{{MYCO_DIR}}", lay["myco"]), ("{{NOTES_DIR}}", lay["notes"]), ("{{TOOLS_DIR}}", lay["tools"]), ("{{DOCS_DIR}}", lay["docs"]),
            ("{{MAP_DIR}}", lay["map"]), ("{{DATA_DIRS}}", " ".join(data)), ("{{NEW_FOLDERS}}", a.new_folders), ("{{KIT_VERSION}}", _myco.VERSION), ("{{FORMAT_VERSION}}", _myco.FORMAT_VERSION))
    tools_abs = os.path.normcase(at(lay["tools"]))
    for p in written:
        f = os.path.basename(p)
        if (f.endswith(TEXT_EXT) or f in TEXT_NAMES) and not os.path.normcase(p).startswith(tools_abs + os.sep):
            with open(p, encoding="utf-8", newline="") as fh:
                s = fh.read()
            for k, v in subs:
                s = s.replace(k, v)
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(s)

    if data:
        for d in data:
            os.makedirs(at(d), exist_ok=True)
        with open(os.path.join(target, ".gitignore"), "a", encoding="utf-8", newline="") as fh:
            fh.write("\n# Project data (inputs, outputs, attachments): not notes, not versioned. Delete a line to version that folder.\n")
            fh.write("".join(f"{d}/\n" for d in data))
        with open(os.path.join(target, "AGENTS.md"), "a", encoding="utf-8", newline="") as fh:
            fh.write("- Project data folders (inputs and outputs, not notes; ignored by git): " + ", ".join(f"`{d}/`" for d in data) + ".\n")

    merged = merge_entry(target, entry_old) if entry_old else []

    if a.adopt:
        present = [d for d in (".obsidian", ".trash", ".logseq") if os.path.isdir(at(d))]
        if present:
            with open(os.path.join(target, ".gitignore"), "a", encoding="utf-8", newline="") as fh:
                fh.write("\n# Settings and caches of the notes app used before (method 20.2): not notes\n" + "".join(f"{d}/\n" for d in present))

    if not _myco.IS_WINDOWS:
        for d in (lay["tools"], lay["tools"] + "/hooks"):
            full = at(d)
            for f in os.listdir(full):
                p = os.path.join(full, f)
                if os.path.isfile(p):
                    os.chmod(p, os.stat(p).st_mode | 0o111)

    _myco.git("-C", target, "config", "core.hooksPath", lay["tools"] + "/hooks")
    print(f"bootstrap: {'took over' if a.adopt else 'created'} {target}")
    for name in merged:
        print(f"bootstrap: the rules of your {name} still apply: they follow the new entry point in {name} (tidy them up in the first pass, method 20.4)")
    for old_name, new_name in kept:
        print(f"bootstrap: kept your {new_name} as {old_name} (merge what it says into the working agreement)")

    if a.adopt:
        log = write_import_log(target, lay, a.name, "in place", collection, hits, backup, kept, had_git, merged=merged)
        commit("Baseline: Myco Notes added around the existing notes (method section 20)")
    elif a.source:
        commit("Baseline: notes repository created from the Myco Notes template")
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(os.path.abspath(a.source))).strip("-.") or "notes"
        base = lay["notes"] + "/imported/" + name
        copied = []
        for rel in collect(os.path.abspath(a.source)):
            dest = at(base + "/" + rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(os.path.join(os.path.abspath(a.source), *rel.split("/")), dest)
            copied.append(base + "/" + rel)
        hits = scan(target, copied)
        held = sorted({h[0] for h in hits})
        log = write_import_log(target, lay, a.name, "new folder", copied, hits, None, kept, False, source=os.path.abspath(a.source), name=name)
        commit(f"Import: the notes from {os.path.basename(os.path.abspath(a.source))} as found (method section 20)")
    else:
        commit("Baseline: notes repository created from the Myco Notes template")
    sys.stdout.flush()
    if held:
        rc = 4
        print(f"bootstrap: {len(held)} file(s) look like they contain a secret and were NOT committed (values hidden):", file=sys.stderr)
        for f, ln, kind in sorted(hits)[:40]:
            print(f"  {f}:{ln} ({kind})", file=sys.stderr)
        print("  Remove each value (or move it where secrets live), then commit them with notes-commit.", file=sys.stderr)
    n, t, d_ = lay["notes"], lay["tools"], lay["docs"]
    if a.adopt or a.source:
        print(f"""
Next: the first pass (method section 20.4), guided by the import log {log}.
  1. Read the collection; write {n}/{lay['state']} (what it is about, main subjects, open questions) and {n}/working-agreement.md.
  2. Connect notes that belong together; reorganise only if the owner chose to, in batches of about 20 files, one commit each,
     updating each row of the import log ({t}/notes-commit "Import: ...").
  3. python3 {t}/notes-lint.py and python3 {t}/build-notes-map.py to see the network.
  Never delete originals during the import.""")
        return rc
    print(f"""
Next steps:
  1. Edit {n}/working-agreement.md and {n}/state.md (headline facts, components).
  2. Set MIRROR_TARGET in .myco-notes.conf and run {t}/mirror-push (then a timer every few hours).
  3. Set up an independent encrypted snapshot of the mirror and run {t}/restore-drill once.
  4. python3 {t}/build-notes-map.py   (navigable map with backlinks and history)
  5. Commit after every meaningful update:  {t}/notes-commit "what changed and why"
     (New folders and files in the root: NEW_FOLDERS={a.new_folders} in .myco-notes.conf; with 'ask' notes-commit stops and lists them.)
  6. Sharing with a team (GitHub or GitHub Enterprise): see {d_}/TEAM.md; teammates run {t}/setup-clone after cloning.
  (On Windows in cmd or PowerShell write {t.replace('/', chr(92))}\\notes-commit; in Git Bash, WSL, macOS and Linux write {t}/notes-commit.)""")
    return rc


if __name__ == "__main__":
    sys.exit(main())
