#!/usr/bin/env python3
"""index: every note of a Myco Notes tree with its one-line summary (Python standard library only).

The note index of method 3.2 and 10.1: read it first to find the note for a question instead of opening files one by one. Each line is
the note's path and the `summary` from its header; a note without one shows its first sentence, marked "(first line)". Records in the
history folders (logs, archive, inbox, imported, HISTORY_DIRS) are listed after the notes, as a count per folder unless --all is given.
It reads; it never writes. It is generated, so it is never out of date and never committed.

Usage:  tools/index [--root DIR] [--all] [--missing] [--review-scope [--full]]
        --all           list every record in the history folders too
        --missing       only the notes outside the history folders that have no summary (for an upgrade, method 21.4)
        --review-scope  what the next review should read (method 21.5): the notes changed since the last commit of the newest review
                        file, the one that applied its fixes (uncommitted edits included), plus the notes named in the changed lines
                        and the notes that point to a changed note (unless more than 5 do: a hub such as the master record); or every note when a full review is due (no
                        earlier review, or the last full one older than REVIEW_FULL_DAYS, default 30). --full asks for a full one.
                        'Also check' names the entry point (AGENTS.md) when the kit was updated or it changed since the last
                        review, and in every full review.
Exit:   0 (also when summaries are missing; the lint reports those)
"""
import argparse, datetime, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402

SKIP_NAMES = {".git", "site", "notes-map", "node_modules", "__pycache__", ".obsidian", ".trash", ".github"}
ENTRY = {"AGENTS.md", "CLAUDE.md"}


def note_files(root, lay):
    """Repository-relative paths of the Markdown notes: everything the lint reads, without the kit's tools and docs, the map,
    the data folders, agent skill copies and the root entry files."""
    skip = {lay["map"], lay["tools"], lay["docs"], *lay["data"], *_myco.AGENT_SKILL_DIRS, "template"}
    out = []
    for dp, dn, fn in os.walk(root):
        reldir = os.path.relpath(dp, root).replace(os.sep, "/")
        dn[:] = sorted(d for d in dn if d not in SKIP_NAMES and (d if reldir == "." else reldir + "/" + d) not in skip)
        for f in sorted(fn):
            if f.endswith(".md") and not (reldir == "." and f in ENTRY):
                out.append(f if reldir == "." else reldir + "/" + f)
    return out


def collect(root, lay):
    """[(rel, summary, from_header, is_history)] for every note."""
    hist = tuple(lay["notes"] + "/" + h + "/" for h in lay["history"])
    rows = []
    for rel in note_files(root, lay):
        text = open(os.path.join(root, *rel.split("/")), encoding="utf-8", errors="replace").read()
        s, own = _myco.note_summary(text)
        rows.append((rel, s, own, rel.startswith(hist)))
    return rows


def review_files(root, lay):
    """[(ct, sha, rel, is_full)] for committed review files (method 21.2), oldest first by the commit that added them; sha is the LAST
    commit that touched the file (the one that applied its fixes), so the next review starts after them; is_full: scope 'full' or absent."""
    d = os.path.join(root, *lay["notes"].split("/"), "plans")
    out = []
    if not os.path.isdir(d):
        return out
    for f in os.listdir(d):
        if not _myco.REVIEW_FILE.match(f):
            continue
        rel = lay["notes"] + "/plans/" + f
        r = _myco.git("-C", root, "log", "--diff-filter=A", "--format=%ct %H", "-1", "--", rel)
        if r.returncode != 0 or not r.stdout.strip():
            continue                                  # not committed yet: a review being written
        ct = r.stdout.split()[0]
        last = _myco.git("-C", root, "log", "--format=%H", "-1", "--", rel)
        sha = last.stdout.strip() or r.stdout.split()[1]
        fm, _ = _myco.frontmatter(open(os.path.join(d, f), encoding="utf-8", errors="replace").read())
        scope = fm.get("scope", ("",))[0].strip().lower()
        out.append((int(ct), sha, rel, scope in ("", "full") or scope.startswith("full")))
    return sorted(out)


HUB_LINKERS = 5   # a changed note that more notes than this point to is a hub: its linkers are not added to the scope


class Linker:
    """Finds the notes a piece of text names: backticked file names and wiki/relative links (method 9)."""
    def __init__(self, notes):
        self.by_base, self.paths = {}, set(notes)
        for n in notes:
            self.by_base.setdefault(os.path.basename(n), []).append(n)
        self.index = _myco.LinkIndex(notes, self.paths)

    def targets(self, text, rel):
        tgt = set()
        for tok in re.findall(r"`([^`\n]+\.md)`", text):
            tgt.update(self.by_base.get(os.path.basename(tok.strip()), []))
        for kind, target, _ in _myco.links(text):
            found = self.index.resolve(kind, target, rel)
            if found in self.paths:
                tgt.add(found)
        tgt.discard(rel)
        return tgt


def changed_lines(root, base, rel, untracked):
    """The added and removed lines of one note since `base`, uncommitted edits included; the whole file when it is new."""
    if rel in untracked:
        return open(os.path.join(root, *rel.split("/")), encoding="utf-8", errors="replace").read()
    r = _myco.git("-C", root, "-c", "core.quotepath=off", "diff", "-U0", base, "--", rel)
    return "\n".join(l[1:] for l in r.stdout.split("\n") if l[:1] in "+-" and not l.startswith(("+++", "---")))


def review_scope(root, lay, conf, want_full=False, today=None):
    """(scope, reason, base sha or None, changed notes, linked notes, all notes) for the next review (method 21.5)."""
    rows = collect(root, lay)
    notes = sorted(r[0] for r in rows if not r[3] and not (r[0].startswith(lay["notes"] + "/plans/") and _myco.REVIEW_FILE.match(os.path.basename(r[0]))))
    try:
        full_days = int(conf.get("REVIEW_FULL_DAYS") or 30)
    except ValueError:
        full_days = 30
    revs = review_files(root, lay)
    today = today or datetime.date.today()
    fulls = [r for r in revs if r[3]]
    if want_full:
        return "full", "asked for a full review", None, [], [], notes
    if not revs:
        return "full", "no earlier review file", None, [], [], notes
    if not fulls:
        return "full", "no earlier full review", None, [], [], notes
    age = (today - datetime.date.fromtimestamp(fulls[-1][0])).days
    if age > full_days:
        return "full", f"the last full review ({fulls[-1][2]}) is {age} days old (REVIEW_FULL_DAYS={full_days})", None, [], [], notes
    base = revs[-1][1]
    changed = set()
    r = _myco.git("-C", root, "-c", "core.quotepath=off", "diff", "--name-only", "-z", base, "HEAD")
    changed.update(p for p in r.stdout.split("\0") if p)
    r = _myco.git("-C", root, "-c", "core.quotepath=off", "status", "--porcelain", "-z", "--untracked-files=all")
    for entry in r.stdout.split("\0"):
        if len(entry) > 3:
            changed.add(entry[3:])
    ch = sorted(n for n in notes if n in changed)
    untracked = set(p for p in _myco.git("-C", root, "-c", "core.quotepath=off", "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0") if p)
    lk = Linker(notes)
    linked = set()
    for n in ch:                                   # notes named in the lines that changed
        linked.update(lk.targets(changed_lines(root, base, n, untracked), n))
    linkers = {n: set() for n in ch}               # notes that point to a changed note, unless it is a hub
    for n in notes:
        text = open(os.path.join(root, *n.split("/")), encoding="utf-8", errors="replace").read()
        for tgt in lk.targets(text, n) & set(ch):
            linkers[tgt].add(n)
    for n, who in linkers.items():
        if len(who) <= HUB_LINKERS:
            linked.update(who)
    linked = sorted(linked - set(ch))
    return "changed", f"since {revs[-1][2]} (commit {base[:7]}); last full review {age} day(s) ago, full every {full_days}", base, ch, linked, notes


def entry_checks(root, lay, conf, scope, base):
    """Things outside the notes a review must also look at (method 21.4, 21.5): the entry point when the kit was updated since the
    last review, when the entry point itself changed, and in every full review."""
    out = []
    now = conf.get("KIT_VERSION", "").strip().strip("\"'")
    if base:
        r = _myco.git("-C", root, "show", base + ":.myco-notes.conf")
        m = re.search(r"^KIT_VERSION=[\"']?([^\"'\s]*)", r.stdout, re.M) if r.returncode == 0 else None
        was = m.group(1) if m else ""
        if now and was != now:
            out.append(f"the kit was updated since the last review ({was or 'unknown'} to {now}): compare `AGENTS.md` with the kit's "
                       "`template/AGENTS.md` and propose the missing lines as `upgrade` fixes (method 21.4)")
        ch = _myco.git("-C", root, "diff", "--name-only", base, "HEAD", "--", "AGENTS.md", "CLAUDE.md").stdout.split()
        ch += [l[3:] for l in _myco.git("-C", root, "status", "--porcelain", "--", "AGENTS.md", "CLAUDE.md").stdout.split("\n") if len(l) > 3]
        if ch:
            out.append(f"the entry point changed since the last review ({', '.join(sorted(set(ch)))}): read the changed lines")
    if base:                                       # a source fetched again with changed content (method 22.4)
        try:
            import notes_ingest
            srcs = dict(notes_ingest.read_sources(root, lay))
            added = _myco.git("-C", root, "-c", "core.quotepath=off", "diff", "--name-only", "--diff-filter=A", base, "HEAD", "--",
                              lay["notes"] + "/sources/").stdout.split("\n")
            added += [l[3:] for l in _myco.git("-C", root, "-c", "core.quotepath=off", "status", "--porcelain", "--untracked-files=all",
                                                 "--", lay["notes"] + "/sources/").stdout.split("\n") if l.startswith("??")]
            for p in sorted({x.strip() for x in added if x.strip()}):
                f = os.path.basename(p)
                old = srcs.get(f, {}).get("supersedes", "").strip()
                if old:
                    who = notes_ingest.citing(root, lay, [old])[old]
                    out.append(f"source `{f}` replaces `{old}` (the content changed): compare "
                               + (", ".join(f"`{w}`" for w in who) if who else "the notes that relied on it (none cite it by name)")
                               + " with the new copy (method 22.4)")
                elif f in srcs:
                    out.append(f"new source `{f}` since the last review: if it has not been taken in yet, read it and propose (method 22.3)")
        except Exception:
            pass
    if scope == "full" and not any("template/AGENTS.md" in o for o in out):
        out.append("a full review also compares `AGENTS.md` with the kit's `template/AGENTS.md` (missing lines become `upgrade` fixes, method 21.4)")
    return out


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--all", action="store_true", help="list every record in the history folders too")
    ap.add_argument("--missing", action="store_true", help="only notes without a summary")
    ap.add_argument("--review-scope", action="store_true", help="what the next review should read (method 21.5)")
    ap.add_argument("--full", action="store_true", help="with --review-scope: a full review")
    a = ap.parse_args()
    root = _myco.toplevel(a.root) or os.path.abspath(a.root)
    conf = _myco.load_conf(root)
    lay = _myco.layout(root, conf)
    if a.review_scope:
        scope, reason, base, ch, linked, notes = review_scope(root, lay, conf, a.full)
        revs = review_files(root, lay)
        extra = entry_checks(root, lay, conf, scope, revs[-1][1] if revs else None)
        if scope == "full":
            print(f"# Review scope: full ({reason})")
            print(f"Read all {len(notes)} notes (`index` lists them with their summaries). Header line for the review file: `scope: full`.")
            print("\n## Also check\n" + "".join(f"- {e}\n" for e in extra), end="")
            return 0
        print(f"# Review scope: changed ({reason})")
        if extra:
            print("\n## Also check\n" + "".join(f"- {e}\n" for e in extra))
        if not ch and not extra:
            print("Nothing changed in the notes since the last review: no review needed (say so in one line; write no review file).")
            return 0
        if not ch:
            print("No note changed since the last review: check only the items above. Header line for the review file: "
                  f"`scope: changed since {base[:7]}`. Finding nothing still means a short review file with 'open: none', committed,"
                  " so the next review starts after it (method 21.5).")
            return 0
        print(f"Read {len(ch)} changed and {len(linked)} linked note(s) of {len(notes)}. Header line for the review file: `scope: changed since {base[:7]}`."
              " Finding nothing still means a short review file with 'open: none', committed, so the next review starts after it (method 21.5).")
        print("\n## Changed")
        for n in ch:
            print(f"- `{n}`")
        if linked:
            print("\n## Linked to or from them")
            for n in linked:
                print(f"- `{n}`")
        return 0
    rows = collect(root, lay)
    notes = [r for r in rows if not r[3]]
    missing = [r for r in notes if not r[2]]
    if a.missing:
        print(f"# Notes without a summary: {len(missing)} of {len(notes)}")
        for rel, s, _, _ in missing:
            print(f"- `{rel}`" + (f" (first line: {s})" if s else ""))
        return 0
    project = os.path.basename(root)
    print(f"# {project}: note index ({len(notes)} notes, {len(missing)} without a summary)")
    print(f"Generated from the notes; `summary` lines come from each note's header (method 10.1). Open the note before acting on it.")
    groups = {}
    for r in notes:
        folder = os.path.dirname(r[0]) or "."
        groups.setdefault(folder, []).append(r)
    for folder in sorted(groups, key=lambda f: (f != lay["notes"], f)):
        print(f"\n## {folder if folder != '.' else '(repository root)'}/")
        for rel, s, own, _ in groups[folder]:
            print(f"- `{rel}`: " + (s if own else (f"(first line) {s}" if s else "(no summary)")))
    hist = [r for r in rows if r[3]]
    if hist:
        print("\n## Records (history folders: what was true when written)")
        counts = {}
        for r in hist:
            top = "/".join(r[0].split("/")[:len(lay["notes"].split("/")) + 1])
            counts.setdefault(top, []).append(r)
        for top in sorted(counts):
            if a.all:
                for rel, s, own, _ in counts[top]:
                    print(f"- `{rel}`: " + (s if own else (f"(first line) {s}" if s else "(no summary)")))
            else:
                print(f"- `{top}/`: {len(counts[top])} file(s) (`--all` lists them)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
