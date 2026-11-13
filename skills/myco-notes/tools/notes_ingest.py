#!/usr/bin/env python3
"""ingest: keep an outside document (manual, release notes, forum answer, article) as a source in the notes (method section 22).

  tools/ingest --url URL --title "Relay board manual" --summary "one line" [--kind manual] < page.md
  tools/ingest --original manual.pdf --title T --summary S --file manual-text.md     a local file (keep the PDF in a data folder)
  tools/ingest --list                                                                  every source, when retrieved, which notes cite it
  ... --commit [--human]                                                               commit just the new source file

The text comes from --file or standard input; this tool fetches nothing (the agent or the owner gets the document). It writes
<notes>/sources/YYYY-MM-DD-<title>.md with a header (summary, source_url or original, retrieved, kind, sha256, supersedes) and the
text as given. Sources are records: never edited after saving. The same URL saved again: unchanged content writes nothing; changed
content writes a new file that supersedes the old one, and `index --review-scope` then lists the notes citing the old copy.
Notes cite a source in their header (`sources: <file>`) and next to the fact ("per `<file>`").
Options: --kind manual|release-notes|forum|article|benchmark|datasheet|other (default other); --date YYYY-MM-DD (default today).
Exit: 0 saved or unchanged, 1 error, 2 usage, 4 refused: the text has a secret-looking string (lines named, values not shown);
with --commit, notes-commit's own exit code.
"""
import argparse, datetime, hashlib, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402
import secret_scan  # noqa: E402

KINDS = ("manual", "release-notes", "forum", "article", "benchmark", "datasheet", "other")


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:60].rstrip("-") or "source")


def sources_dir(root, lay):
    return os.path.join(root, *lay["notes"].split("/"), "sources")


def read_sources(root, lay):
    """[(file name, header dict)] of the saved sources, oldest first."""
    d = sources_dir(root, lay)
    out = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".md") and f.lower() != "readme.md":
                fm, _ = _myco.frontmatter(open(os.path.join(d, f), encoding="utf-8", errors="replace").read())
                out.append((f, {k: v[0] for k, v in fm.items()}))
    return out


def citing(root, lay, names):
    """{source file name: [notes that cite it]} for notes outside the history folders (header `sources` or the name in the text)."""
    import notes_index
    found = {n: [] for n in names}
    for rel, _, _, is_hist in notes_index.collect(root, lay):
        if is_hist:
            continue
        text = open(os.path.join(root, *rel.split("/")), encoding="utf-8", errors="replace").read()
        fm, _ = _myco.frontmatter(text)
        listed = {os.path.basename(x.strip().strip("`")) for x in fm.get("sources", ("",))[0].split(",") if x.strip()}
        for n in names:
            if n in listed or n in text:
                found[n].append(rel)
    return found


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(prog="ingest", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="")
    ap.add_argument("--original", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--summary", default="")
    ap.add_argument("--kind", default="other", choices=KINDS)
    ap.add_argument("--file", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--human", action="store_true")
    ap.add_argument("--root", default="")
    a = ap.parse_args()
    root = _myco.toplevel(a.root or os.environ.get("NOTES_ROOT") or os.getcwd()) or _myco.toplevel(HERE)
    if not root:
        print("ingest: not inside a git repository", file=sys.stderr)
        return 1
    conf = _myco.load_conf(root)
    lay = _myco.layout(root, conf)
    srcs = read_sources(root, lay)

    if a.list:
        if not srcs:
            print("ingest: no sources yet")
            return 0
        superseded = {s.strip() for _, h in srcs for s in h.get("supersedes", "").split(",") if s.strip()}
        cites = citing(root, lay, [f for f, _ in srcs])
        print(f"# Sources ({len(srcs)})")
        for f, h in srcs:
            where = h.get("source_url") or ("original: " + h.get("original", "")) if (h.get("source_url") or h.get("original")) else "where: not recorded"
            state = " (superseded)" if f in superseded else ""
            who = ", ".join(f"`{c}`" for c in cites[f]) or "no note cites it yet"
            print(f"- `{f}`{state}: {h.get('kind', 'other')}, retrieved {h.get('retrieved', '?')}; {where}\n  cited by: {who}")
        return 0

    if not a.title or not a.summary or bool(a.url) == bool(a.original):
        print("usage: ingest (--url URL | --original FILE) --title T --summary S [--kind K] [--file PATH] [--date YYYY-MM-DD] [--commit]  (text on stdin without --file)", file=sys.stderr)
        return 2
    if len(a.summary) > _myco.SUMMARY_MAX:
        print(f"ingest: --summary is {len(a.summary)} characters; keep it to {_myco.SUMMARY_MAX}", file=sys.stderr)
        return 2
    try:
        text = open(a.file, encoding="utf-8", errors="replace").read() if a.file else sys.stdin.read()
    except OSError as e:
        print(f"ingest: cannot read {a.file}: {e}", file=sys.stderr)
        return 1
    text = "\n".join(l.rstrip() for l in text.replace("\r\n", "\n").split("\n")).strip("\n")
    if not text.strip():
        print("ingest: no text given (use --file or standard input)", file=sys.stderr)
        return 2
    hits = [i for i, l in enumerate(text.split("\n"), 1) if secret_scan.find(l)]
    if hits:
        print(f"ingest: REFUSED: the text has secret-looking strings on line(s) {', '.join(map(str, hits[:10]))} (values not shown); remove them and run again", file=sys.stderr)
        return 4
    day = a.date or datetime.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        print("ingest: --date takes YYYY-MM-DD", file=sys.stderr)
        return 2
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    key, val = ("source_url", a.url.strip()) if a.url else ("original", os.path.basename(a.original.strip()))
    same = [(f, h) for f, h in srcs if h.get(key) == val]
    supersedes = ""
    if same:
        last_f, last_h = same[-1]
        if last_h.get("sha256") == digest:
            print(f"ingest: unchanged: `{last_f}` already holds this content; nothing written")
            return 0
        supersedes = last_f
    d = sources_dir(root, lay)
    os.makedirs(d, exist_ok=True)
    name = f"{day}-{slug(a.title)}.md"
    n = 2
    while os.path.exists(os.path.join(d, name)):
        name, n = f"{day}-{slug(a.title)}-{n}.md", n + 1
    head = [f"summary: {a.summary.strip()}", f"{key}: {val}", f"retrieved: {day}", f"kind: {a.kind}", f"sha256: {digest}"]
    if supersedes:
        head.append(f"supersedes: {supersedes}")
    origin = a.url.strip() if a.url else f"the local file {val}"
    body = (f"---\n" + "\n".join(head) + "\n---\n# " + re.sub(r"\s+", " ", a.title).strip() + "\n\n"
            + f"Retrieved {day} from {origin}. Kept as found (method section 22): not edited after saving"
            + (f"; replaces `{supersedes}`, whose content differs" if supersedes else "") + ".\n\n" + text + "\n")
    with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    rel = f"{lay['notes']}/sources/{name}"
    print(f"saved to {rel}" + (f" (supersedes {supersedes}; content changed)" if supersedes else ""))
    if supersedes:
        cites = citing(root, lay, [supersedes])[supersedes]
        if cites:
            print("notes citing the earlier copy (the next review compares them): " + ", ".join(f"`{c}`" for c in cites))
    if not a.commit:
        return 0
    cmd = [sys.executable, "-B", os.path.join(HERE, "notes_commit.py"), "--only", rel] + (["--human"] if a.human else [])
    return subprocess.run(cmd + [f"Source: {a.title.strip()}"], cwd=root).returncode


if __name__ == "__main__":
    sys.exit(main())
