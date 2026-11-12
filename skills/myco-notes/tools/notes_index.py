#!/usr/bin/env python3
"""index: every note of a Myco Notes tree with its one-line summary (Python standard library only).

The note index of method 3.2 and 10.1: read it first to find the note for a question instead of opening files one by one. Each line is
the note's path and the `summary` from its header; a note without one shows its first sentence, marked "(first line)". Records in the
history folders (logs, archive, inbox, imported, HISTORY_DIRS) are listed after the notes, as a count per folder unless --all is given.
It reads; it never writes. It is generated, so it is never out of date and never committed.

Usage:  tools/index [--root DIR] [--all] [--missing]
        --all      list every record in the history folders too
        --missing  only the notes outside the history folders that have no summary (for an upgrade, method 21.4)
Exit:   0 (also when summaries are missing; the lint reports those)
"""
import argparse, os, sys

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


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--all", action="store_true", help="list every record in the history folders too")
    ap.add_argument("--missing", action="store_true", help="only notes without a summary")
    a = ap.parse_args()
    root = _myco.toplevel(a.root) or os.path.abspath(a.root)
    lay = _myco.layout(root)
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
