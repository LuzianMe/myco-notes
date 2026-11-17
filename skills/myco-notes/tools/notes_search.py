#!/usr/bin/env python3
"""search: find the notes that answer a question, ranked (Python standard library only).

For a notes repository that has grown past what `index` shows at a glance. Every word of the query is looked for in each note's
summary, title, file name, headings and text; a word matches the start of a word in the note ("backup" finds "backups"), and a
"quoted phrase" must appear as written (any case). Matches in the summary, title and file name count most, then headings, then
the text; rare words count more than common ones; a note that many other notes name ranks a little higher (method 9). Notes that
hold every word come first; when no note holds them all, notes holding some of them are listed. Records (logs, archive, inbox,
imported, sources, HISTORY_DIRS) count half and are marked, because they say what was true when written; --notes-only leaves them out.
Each result shows the note's summary and its first matching lines with line numbers; a line that looks like a secret is never shown.
It reads; it never writes. Open the note before acting on it.

Usage:  tools/search [--root DIR] [--limit N] [--notes-only] [--lines N] QUERY...
Exit:   0 found, 1 nothing found, 2 usage
"""
import argparse, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402
import notes_index  # noqa: E402
import secret_scan  # noqa: E402

WORD = re.compile(r"\w+", re.U)
WEIGHTS = {"summary": 6.0, "title": 5.0, "path": 4.0, "heading": 3.0}
RECORD_FACTOR = 0.5


def parse_query(words):
    """(terms, phrases): lower-case words to match at a word start, and lower-case "quoted phrases" to match as written."""
    q = " ".join(words)
    phrases = [p.strip().lower() for p in re.findall(r'"([^"]+)"', q) if p.strip()]
    rest = re.sub(r'"[^"]*"', " ", q)
    terms = list(dict.fromkeys(w.lower() for w in WORD.findall(rest)))
    return terms, phrases


class Doc:
    def __init__(self, rel, text, is_record):
        self.rel, self.is_record = rel, is_record
        fm, end = _myco.frontmatter(text)
        self.summary, _ = _myco.note_summary(text)
        self.lines = text.split("\n")
        body = self.lines[end:]
        self.title = next((l.lstrip("#").strip() for l in body if l.startswith("# ")), "")
        self.headings = " ".join(l.lstrip("#").strip() for l in body if re.match(r"^#{2,6}\s", l))
        self.fields = {"summary": self.summary.lower(), "title": self.title.lower(),
                       "path": re.sub(r"[/_.-]", " ", rel.lower()), "heading": self.headings.lower()}
        self.text = "\n".join(body).lower()
        self.tokens = {}
        for f, s in list(self.fields.items()) + [("text", self.text)]:
            self.tokens[f] = WORD.findall(s)

    def count(self, field, term=None, phrase=None):
        if phrase is not None:
            return (self.fields.get(field) if field != "text" else self.text).count(phrase)
        return sum(1 for t in self.tokens[field] if t.startswith(term))

    def has(self, term=None, phrase=None):
        return any(self.count(f, term, phrase) for f in ("summary", "title", "path", "heading", "text"))


def score(doc, keys, idf):
    s = 0.0
    for k in keys:
        term, phrase = (None, k[1]) if k[0] == "phrase" else (k[1], None)
        part = sum(w * min(doc.count(f, term, phrase), 3) for f, w in WEIGHTS.items())
        n = doc.count("text", term, phrase)
        part += 1 + math.log(n) if n else 0.0
        s += part * idf[k]
    return s


def matching_lines(doc, keys, limit):
    """(line number, text) of the first lines that hold a query word, secret-looking lines left out."""
    out = []
    pats = [re.compile(r"(?<!\w)" + re.escape(k[1]), re.I) if k[0] == "term" else re.compile(re.escape(k[1]), re.I) for k in keys]
    in_fm = doc.lines[:1] == ["---"]
    for i, line in enumerate(doc.lines, 1):
        if in_fm:
            in_fm = not (i > 1 and line.strip() in ("---", "..."))
            continue
        if line.startswith("# ") or not line.strip() or not any(p.search(line) for p in pats):
            continue
        if secret_scan.find(line):
            out.append((i, "(line hidden: it looks like a secret)"))
        else:
            s = line.strip()
            out.append((i, s if len(s) <= 160 else s[:157].rstrip() + "..."))
        if len(out) >= limit:
            break
    return out


def search(root, lay, words, notes_only=False):
    """[(score, Doc, matched every key)] best first, for the query words."""
    terms, phrases = parse_query(words)
    keys = [("term", t) for t in terms] + [("phrase", p) for p in phrases]
    if not keys:
        return [], keys
    docs = []
    for rel, _s, _own, is_hist in notes_index.collect(root, lay):
        if notes_only and is_hist:
            continue
        with open(os.path.join(root, *rel.split("/")), encoding="utf-8", errors="replace") as fh:
            docs.append(Doc(rel, fh.read(), is_hist))
    if not docs:
        return [], keys
    n = len(docs)
    idf = {}
    for k in keys:
        df = sum(1 for d in docs if (d.has(phrase=k[1]) if k[0] == "phrase" else d.has(term=k[1])))
        idf[k] = math.log(1 + (n - df + 0.5) / (df + 0.5))
    linker = notes_index.Linker([d.rel for d in docs])
    inbound = {}
    for d in docs:
        for tgt in linker.targets("\n".join(d.lines), d.rel):
            inbound[tgt] = inbound.get(tgt, 0) + 1
    res = []
    for d in docs:
        held = [k for k in keys if (d.has(phrase=k[1]) if k[0] == "phrase" else d.has(term=k[1]))]
        if not held:
            continue
        s = score(d, held, idf) * (1 + 0.1 * math.log(1 + inbound.get(d.rel, 0)))
        if d.is_record:
            s *= RECORD_FACTOR
        res.append((s, d, len(held) == len(keys)))
    complete = [r for r in res if r[2]]
    res = complete or res
    res.sort(key=lambda r: (-r[0], r[1].rel))
    return res, keys


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--limit", type=int, default=10, help="at most this many notes (default 10)")
    ap.add_argument("--lines", type=int, default=2, help="matching lines shown per note (default 2, 0 for none)")
    ap.add_argument("--notes-only", action="store_true", help="leave out records (logs, archive, inbox, imported, sources)")
    ap.add_argument("query", nargs="+")
    a = ap.parse_args()
    root = _myco.toplevel(a.root) or os.path.abspath(a.root)
    lay = _myco.layout(root)
    res, keys = search(root, lay, a.query, a.notes_only)
    if not keys:
        print("search: the query has no words to look for", file=sys.stderr)
        return 2
    shown = " ".join([k[1] for k in keys if k[0] == "term"] + [f'"{k[1]}"' for k in keys if k[0] == "phrase"])
    if not res:
        print(f"# search: no note mentions {shown}")
        print("Try fewer or shorter words, `index` for the list of notes, or `asof WHEN --grep TEXT` for older text.")
        return 1
    partial = not res[0][2]
    print(f"# search: {shown} ({len(res)} note(s){', none holds every word: best partial matches' if partial else ''})")
    for s, d, _all in res[:max(a.limit, 1)]:
        print(f"\n- `{d.rel}`" + (" (record)" if d.is_record else "") + f" [{s:.1f}]: " + (d.summary or "(no summary)"))
        for ln, text in matching_lines(d, keys, a.lines) if a.lines > 0 else []:
            print(f"    {ln}: {text}")
    if len(res) > a.limit:
        print(f"\n... and {len(res) - a.limit} more (--limit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
