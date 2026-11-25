#!/usr/bin/env python3
"""wiki: tests of the wiki layout of the notes map (build-notes-map.py --layout wiki), on invented notes. Standard library only.

    python3 tests/wiki.py

Covers: the classic map is unchanged by default; every file the wiki writes and every link inside it; the header of a note (summary, freshness,
last edit, raw link, follow-ups and missing references); links here, mentions, previous and next, history, recently changed; wiki links,
relative links and file-name mentions as real links; the search data; the project's theme (and refusing a bad one); the secret gate; data
folders, flat layout, the output-folder rules, slug collisions, --public; and the plain-text fallback without the markdown package.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

sys.dont_write_bytecode = True
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(REPO, "skills", "myco-notes", "tools", "build-notes-map.py")
passed = failed = 0
os.environ.update(GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="t@example.com")


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def run(cmd, cwd, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git(cwd, *a, date=None):
    return run(["git", *a], cwd, {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date} if date else None)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def build(root, out, *args, env=None):
    return run([sys.executable, BUILD, "--root", root, "--out", out, *args], root, env)


def page_of(out, name):
    return read(os.path.join(out, "p", name + ".html"))


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("a", "link") and a.get("href"):
            self.hrefs.append(a["href"])
        if tag == "script" and a.get("src"):
            self.hrefs.append(a["src"])
        if a.get("id"):
            self.ids.add(a["id"])


def fixture(root):
    """An invented orchard's notes, with every kind of link and header the wiki layout has to show."""
    write(os.path.join(root, ".myco-notes.conf"), "MYCO_DIR=myco-notes\nDATA_DIRS=scripts\n")
    write(os.path.join(root, "AGENTS.md"), "# Orchard notes: start here\n\nRead `working-agreement.md` first, then [[harvest-plan]].\n")
    write(os.path.join(root, "myco-notes", "working-agreement.md"), "---\nsummary: How we work in the orchard: approvals, safety, things never to do\n---\n# Working agreement\n\nAsk before pruning the old trees.\n")
    write(os.path.join(root, "myco-notes", "state.md"),
          "---\nsummary: Master record of the orchard: rows, trees, the press, open items\nlast_confirmed: 2019-12-01\nreview_after: 2020-01-01\nsuperseded_by: harvest-plan.md\n---\n"
          "# Orchard: master record\n\nThe press is described in [[cider-press|the cider press]] and the dates in [[harvest-plan#Dates]].\n"
          "A relative link: [the plan](plans/harvest-plan.md#dates) and one to a script [run it](../scripts/run.sh).\n"
          "Plain mention of runbook.md in the text, and `runbook.md` in code. Missing: `ghost-note.md`.\n\n"
          "Follow-up after 2020-02-01 to check the nets.\n\n## Rows\n\nA table:\n\n| row | trees |\n|---|---|\n| A | 12 |\n\n"
          "```\n[[not-a-link]] and runbook.md stay as written\n```\n\n## Quirks\n\nThe unique word is quincunx.\n")
    write(os.path.join(root, "myco-notes", "runbook.md"), "---\nsummary: How to do the yearly jobs, with the commands\n---\n# Runbook\n\nSee state.md for the rows.\n")
    write(os.path.join(root, "myco-notes", "plans", "harvest-plan.md"), "---\nsummary: The harvest plan and its dates\n---\n# Harvest plan\n\n## Dates\n\nPick in October. See state.md.\n")
    write(os.path.join(root, "myco-notes", "plans", "pruning-plan.md"), "---\nsummary: When to prune\n---\n# Pruning plan\n\nAfter the harvest-plan.md.\n")
    write(os.path.join(root, "myco-notes", "entities", "cider-press.md"), "---\nsummary: The cider press: where it is and how it is cleaned\narea: Equipment\n---\n# Cider press\n\nUsed after the harvest, see runbook.md.\n")
    write(os.path.join(root, "myco-notes", "archive", "old-orchard.md"), "# Old orchard\n\nBefore 2019. Follow-up after 2019-05-01.\n")
    write(os.path.join(root, "scripts", "readme.md"), "# Script notes\n\nSecret data folder note, not part of the map.\n")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "Start the orchard notes", date="2026-01-10T10:00:00")
    write(os.path.join(root, "myco-notes", "runbook.md"), read(os.path.join(root, "myco-notes", "runbook.md")) + "\nPressing: two days after picking.\n")
    git(root, "commit", "-qam", "Runbook: pressing", date="2026-02-20T10:00:00")


def main():
    if importlib.util.find_spec("markdown") is None:
        print("SKIP: the markdown package is not installed (pip install markdown); the wiki test renders notes with it and without it")
        return 0
    tmp = tempfile.mkdtemp(prefix="myco-wiki-")
    try:
        root = os.path.join(tmp, "orchard")
        os.makedirs(root)
        fixture(root)
        print("classic stays the default")
        rc, out = build(root, os.path.join(tmp, "classic"))
        check("classic builds", rc == 0 and os.path.isfile(os.path.join(tmp, "classic", "index.html")), out)
        check("classic has no wiki files", not os.path.exists(os.path.join(tmp, "classic", "assets")) and not os.path.exists(os.path.join(tmp, "classic", "recent.html")))
        check("classic pages keep their own look (chips, History block)", 'class="chip"' in page_of(os.path.join(tmp, "classic"), "myco-notes-state") and "<details class='rel'>" in page_of(os.path.join(tmp, "classic"), "myco-notes-state"))

        print("wiki layout")
        w = os.path.join(tmp, "wiki")
        rc, out = build(root, w, "--layout", "wiki")
        check("wiki builds", rc == 0 and "wiki layout" in out, out)
        files = {f for dp, _, fn in os.walk(w) for f in fn}
        check("it writes index, recent, assets, graph and one page and one raw copy per note",
              all(os.path.isfile(os.path.join(w, f)) for f in ("index.html", "recent.html", "graph.html", ".myco-notes-map", "assets/wiki.css", "assets/wiki.js", "assets/nav.js", "assets/search.js"))
              and len(os.listdir(os.path.join(w, "p"))) == 8 and len(os.listdir(os.path.join(w, "raw"))) == 8, str(sorted(files)))
        bad = []
        for dp, _, fn in os.walk(w):
            for f in fn:
                if not f.endswith(".html") or f == "graph.html":
                    continue
                path = os.path.join(dp, f)
                lp = Links()
                lp.feed(read(path))
                for h in lp.hrefs:
                    if re.match(r"^[a-z]+:", h) or h.startswith("//"):
                        bad.append(f"{f}: external {h}")
                        continue
                    target, _, frag = h.partition("#")
                    tp = os.path.normpath(os.path.join(dp, target)) if target else path
                    if not os.path.isfile(tp):
                        bad.append(f"{f}: {h} -> missing file")
                    elif frag and tp.endswith(".html"):
                        ids = Links()
                        ids.feed(read(tp))
                        if frag not in ids.ids:
                            bad.append(f"{f}: {h} -> no anchor")
        check("every link and script in every page points at a file (and an anchor) that exists, and none leaves the folder", not bad, "\n       ".join(bad[:8]))

        st = page_of(w, "myco-notes-state")
        check("a note has breadcrumbs with its group, its title as the heading and its summary", 'aria-label="Breadcrumb"' in st and "Start here" in st and "<h1>Orchard: master record</h1>" in st and "Master record of the orchard" in st)
        check("freshness: status, header fields and a passed review date", "Review due since 2020-01-01" in st and "Superseded" in st and "review after 2020-01-01" in st and "last confirmed 2019-12-01" in st and "last_confirmed" not in st.split("<article")[0])
        check("a superseding note named in the header is a link", 'superseded by <a href="myco-notes-plans-harvest-plan.html">' in st)
        check("last edited comes from git, the raw file is linked", "Last edited 2026-01-10" in st and 'href="../raw/myco-notes-state.md"' in st)
        check("a follow-up date that has passed and a missing reference are marked", "1 follow-up date passed" in st and "Missing references:" in st and "<code>ghost-note.md</code>" in st)
        check("the note's own title is not repeated in the article", st.count("Orchard: master record</h1>") == 1 and "<h1>" not in st.split("<article")[1].split("</article>")[0] and "<h1 " not in st.split("<article")[1].split("</article>")[0])
        check("a table sits in a keyboard-reachable scroll region", 'class="tablewrap" tabindex="0"' in st)
        check("history lists the commits of the note", "Start the orchard notes" in st and 'id="history"' in st)
        rb = page_of(w, "myco-notes-runbook")
        check("history of a note follows its commits (newest first)", rb.index("Runbook: pressing") < rb.index("Start the orchard notes"))
        check("what links here lists each linking note with its title and summary, and the count", 'id="linkshere"' in rb and "Orchard: master record" in rb.split('id="linkshere"')[1] and "Master record of the orchard" in rb.split('id="linkshere"')[1])
        check("mentions lists the notes this one mentions", "Mentions" in st and "Harvest plan" in st.split('id="mentions"')[1] and "The harvest plan and its dates" in st.split('id="mentions"')[1])
        hp = page_of(w, "myco-notes-plans-harvest-plan")
        check("previous and next stay inside the group", 'aria-label="Previous and next in Plans, backlog and decisions"' in hp and "Pruning plan" in hp.split('class="pn"')[1])
        check("the outline lists the headings and links to the footer sections", 'id="outline"' in st and 'href="#rows"' in st and 'href="#linkshere"' in st)
        check("the phone gets an inline outline instead", 'class="otoc-inline"' in st)

        print("links")
        check("[[Name|text]] becomes a link with the text", re.search(r'<a class="wikilink" href="myco-notes-entities-cider-press.html">the cider press</a>', st) is not None, st[st.index("<article"):][:900])
        check("[[Name#Heading]] links to the heading", 'href="myco-notes-plans-harvest-plan.html#dates"' in st)
        check("a relative Markdown link to a note becomes its page, anchor kept", st.count('href="myco-notes-plans-harvest-plan.html#dates"') >= 2)
        check("a link to something that is not a note is shown as text, not as a dead link", 'class="nolink"' in st and 'href="../scripts/run.sh"' not in st)
        check("a file name written in the text becomes a link (the mention the map counts)", 'class="mention" href="myco-notes-runbook.html">runbook.md</a>' in st)
        body = st.split("<article")[1].split("</article>")[0]
        check("a file name alone in a code span is linked", "<code><a class=\"mention\" href=\"myco-notes-runbook.html\">runbook.md</a></code>" in body)
        check("a fenced code block is left as written", "[[not-a-link]] and runbook.md stay as written" in body)
        check("a note is not linked to itself", 'href="myco-notes-state.html"' not in body)
        check("notes outside the map are not linked and data folders are left out", not os.path.exists(os.path.join(w, "p", "scripts-readme.html")))

        print("search, tree, recent, home")
        sj = read(os.path.join(w, "assets", "search.js"))
        data = json.loads(sj[sj.index("=") + 1:].rstrip().rstrip(";"))
        entry = next(e for e in data if e["r"].endswith("state.md"))
        check("the search data holds the text of every note, plain", len(data) == 8 and "quincunx" in entry["x"] and "```" not in entry["x"] and "Rows" in entry["s"] and entry["g"] == "Start here", str(entry)[:300])
        check("pages do not load the search data up front", "search.js" not in st and "search.js" in read(os.path.join(w, "assets", "wiki.js")))
        nav = read(os.path.join(w, "assets", "nav.js"))
        check("the tree data lists every group with its notes, and marks a note that needs a look", '"Start here"' in nav and '"Equipment"' in nav and '"a":1' in nav and nav.count('"i":"') == 8, nav[:300])
        rec = read(os.path.join(w, "recent.html"))
        check("recently changed lists commits by day with the notes they touched", "2026-02-20" in rec and "Runbook: pressing" in rec and 'href="p/myco-notes-runbook.html"' in rec and "2026-01-10" in rec)
        home = read(os.path.join(w, "index.html"))
        check("the home page keeps the groups, blurbs, hints, filter, latest commits and the mycelium link",
              'id="g-start"' in home and "Read in this order" in home and "The harvest plan and its dates" in home and 'id="q"' in home and "Recent changes" in home and "Runbook: pressing" in home and 'href="graph.html"' in home)
        check("the home page marks a note that needs a look", 'class="flag"' in home)
        check("every page has the skip link, landmarks, the theme picker and the early theme script", all(
            'class="skip"' in p and "<main" in p and 'aria-label="Breadcrumb"' in p.split("<main")[1][:200] + 'aria-label="Breadcrumb"' and '<select id="theme-pick">' in p and "localStorage.getItem('myco-theme')" in p.split("</head>")[0]
            for p in (st, rb, hp)))
        check("the mycelium view is still written and links to the note pages", os.path.isfile(os.path.join(w, "graph.html")) and 'href="p/' in read(os.path.join(w, "graph.html")))

        print("theme")
        write(os.path.join(root, ".myco-notes-map.json"), json.dumps({"layout": "wiki", "title": "Orchard", "theme": {"light": {"accent": "#7A3E00", "bg": "#fff"}, "dark": {"accent": "#ffb454"}, "font": "Georgia, serif", "mono": "Menlo, monospace", "radius": "4px"}}))
        t = os.path.join(tmp, "themed")
        rc, out = build(root, t)
        css = read(os.path.join(t, "assets", "wiki.css"))
        check('"layout": "wiki" in the config is enough', rc == 0 and os.path.isfile(os.path.join(t, "assets", "wiki.css")) and "Orchard" in read(os.path.join(t, "index.html")), out)
        check("the project's colours replace Light and Dark (and so Auto), the other themes stay", ":root{color-scheme:light;--bg:#ffffff;" in css and "--accent:#7a3e00" in css.split(":root[data-theme=\"light\"]")[1].split("}")[0]
              and "--accent:#ffb454" in css.split(":root[data-theme=\"dark\"]")[1].split("}")[0] and "--accent:#a6ec6c" in css and "--accent:#ffb454" in css.split("prefers-color-scheme:dark")[1].split("}")[0])
        check("its font, code font and radius are variables", "--font:Georgia, serif" in css and "--mono:Menlo, monospace" in css and "--radius:4px" in css.rsplit(":root{", 1)[1])
        check("the derived colours follow the project's accent", "--soft:" in css and re.search(r'data-theme="light"\]\{[^}]*--soft:#[0-9a-f]{6}', css) is not None)
        rc, out = build(root, os.path.join(tmp, "cl2"), "--layout", "classic")
        check("--layout classic overrides the config, and says the theme is not used", rc == 0 and not os.path.exists(os.path.join(tmp, "cl2", "assets")) and "applies to the wiki layout only" in out, out)
        for label, theme in (("an unknown key", {"colour": {}}), ("a colour that is not #rrggbb", {"light": {"accent": "red"}}), ("a colour name that does not exist", {"light": {"sparkle": "#fff"}}),
                             ("a font that could break out of the style", {"font": "x;}body{display:none"}), ("a radius without a unit", {"radius": "4"})):
            write(os.path.join(root, ".myco-notes-map.json"), json.dumps({"theme": theme}))
            rc, out = build(root, os.path.join(tmp, "bad"), "--layout", "wiki")
            check(f"it refuses {label}", rc != 0 and "REFUSING" in out and not os.path.exists(os.path.join(tmp, "bad", "index.html")), out)
        write(os.path.join(root, ".myco-notes-map.json"), json.dumps({"theme": {"light": {"accent": "#cccccc"}}}))
        rc, out = build(root, os.path.join(tmp, "low"), "--layout", "wiki")
        check("it builds but warns when the project's colours are hard to read", rc == 0 and "warning: theme light: accent #cccccc" in out, out)
        write(os.path.join(root, ".myco-notes-map.json"), json.dumps({"layout": "tiles"}))
        rc, out = build(root, os.path.join(tmp, "bad2"))
        check("it refuses a layout it does not know", rc != 0 and "REFUSING" in out and "classic" in out, out)
        os.remove(os.path.join(root, ".myco-notes-map.json"))

        print("the build's rules, in the wiki layout")
        rc, out = build(root, root, "--layout", "wiki")
        check("--out at the repository is refused", rc != 0 and "REFUSING" in out)
        write(os.path.join(tmp, "foreign", "keep.txt"), "mine\n")
        rc, out = build(root, os.path.join(tmp, "foreign"), "--layout", "wiki")
        check("a folder with files it did not make is refused and left alone", rc != 0 and os.path.isfile(os.path.join(tmp, "foreign", "keep.txt")), out)
        rc1, _ = build(root, w, "--layout", "classic")
        check("the same folder can be rebuilt in the other layout, and nothing of the wiki stays", rc1 == 0 and not os.path.exists(os.path.join(w, "assets")) and not os.path.exists(os.path.join(w, "recent.html")))
        rc2, _ = build(root, w, "--layout", "wiki")
        check("and back", rc2 == 0 and os.path.isfile(os.path.join(w, "assets", "wiki.css")))
        pub = os.path.join(tmp, "pub")
        write(os.path.join(tmp, "labels.json"), json.dumps({"state": "The record"}))
        rc, out = build(root, pub, "--public", "--labels", os.path.join(tmp, "labels.json"), "--layout", "wiki")
        pg = read(os.path.join(pub, "graph.html")) if os.path.isfile(os.path.join(pub, "graph.html")) else ""
        check("--public still writes only the labelled graph, whatever the layout", rc == 0 and sorted(os.listdir(pub)) == ["graph.html"] and "The record" in pg and "cider" not in pg.lower() and "quincunx" not in pg, out)
        write(os.path.join(root, "myco-notes", "state.md"), read(os.path.join(root, "myco-notes", "state.md")) + "\napi_key = AbCdEfGhIjKlMnOpQrStUvWx12\n")
        rc, out = build(root, os.path.join(tmp, "secret"), "--layout", "wiki")
        check("the secret scan still stops the build, value hidden", rc != 0 and "REFUSING" in out and "AbCdEfGh" not in out and not os.path.exists(os.path.join(tmp, "secret", "index.html")), out)
        git(root, "checkout", "-q", "--", "myco-notes/state.md")

        print("slugs, flat layout")
        write(os.path.join(root, "myco-notes", "pg", "x.md"), "# Page x\n\nOne.\n")
        write(os.path.join(root, "myco-notes", "pg-x.md"), "# Page x again\n\nTwo.\n")
        rc, out = build(root, os.path.join(tmp, "slug"), "--layout", "wiki")
        pages = os.listdir(os.path.join(tmp, "slug", "p"))
        check("two notes with the same page name both get a page", rc == 0 and len([p for p in pages if p.startswith("myco-notes-pg-x")]) == 2, out + str(pages))
        flat = os.path.join(tmp, "flat")
        write(os.path.join(flat, "notes", "a.md"), "---\nsummary: Note a\n---\n# Note a\n\nSee b.md and [[b]].\n")
        write(os.path.join(flat, "notes", "b.md"), "---\nsummary: Note b\n---\n# Note b\n\nSee a.md.\n")
        git(flat, "init", "-q", "-b", "main")
        git(flat, "add", "-A")
        git(flat, "commit", "-qm", "flat")
        rc, out = run([sys.executable, BUILD, "--layout", "wiki"], flat)
        check("a flat repository (no MYCO_DIR) builds into notes-map", rc == 0 and os.path.isfile(os.path.join(flat, "notes-map", "p", "notes-a.html")) and 'href="notes-b.html"' in read(os.path.join(flat, "notes-map", "p", "notes-a.html")), out)

        print("0.44.0: reviews have their own group, in the folder reviews/ and (older repositories) in plans/")
        write(os.path.join(root, "myco-notes", "reviews", "review-2026-01-01.md"), "---\nsummary: First review of the orchard notes\nscope: full\nopen: none\n---\n# Review 2026-01-01\n\nNothing to propose; read state.md.\n")
        rc, out = build(root, os.path.join(tmp, "rev"), "--layout", "wiki")
        nav = read(os.path.join(tmp, "rev", "assets", "nav.js"))
        check("the tree has a Reviews group holding the review file", rc == 0 and "Reviews of the notes" in nav and "review-2026-01-01" in nav
              and nav.index("Reviews of the notes") < nav.index("review-2026-01-01"), out)
        git(root, "checkout", "-q", "--", ".")
        os.remove(os.path.join(root, "myco-notes", "reviews", "review-2026-01-01.md"))

        print("0.44.1: long headings")
        write(os.path.join(root, "myco-notes", "longhead.md"), "---\nsummary: A note with a long heading\n---\n# Long heading note\n\n"
              "# 1. Current state (each row carries its own check date; the last full re-check is in the review file)\n\nText.\n\n## Short one\n\nMore.\n\n"
              "## A heading with `code` (and a parenthesis that is short)\n\nX.\n\n## Averyveryveryverylongheadingwithoutanyparenthesisatall that goes on and on and on and on\n\nY.\n")
        rc, out = build(root, os.path.join(tmp, "lh"), "--layout", "wiki")
        lh = page_of(os.path.join(tmp, "lh"), "myco-notes-longhead")
        check("a long heading with a parenthesis: the start is the heading, the rest a quieter line, the anchor unchanged",
              rc == 0 and '<span class="hmain">1. Current state</span> <span class="hsub">(each row' in lh and 'id="1-current-state-each-row-carries' in lh, out)
        check("a short heading, and a heading whose tag comes before the parenthesis, are left as they are", '<h2 id="short-one">Short one<a' in lh and 'class="hmain"><code>' not in lh, out)
        check("the outline shows the start of a long heading with the whole as its tooltip", re.search(r'<a href="#1-current-state[^"]*" title="1\. Current state \(each row[^"]*">1\. Current state</a>', lh) is not None, out)
        os.remove(os.path.join(root, "myco-notes", "longhead.md"))

        print("raw HTML in a note's text")
        write(os.path.join(root, "myco-notes", "rawhtml.md"), "---\nsummary: A note whose text names tags\n---\n# Raw tags\n\n"
              "- Saved: <title>\n- Edit the <textarea> field\n- <script>alert(1)</script>\n- <!-- never closed\n- A forged <a class=\"wikilink\" href=\"javascript:alert(1)\">link</a> and a real [[runbook]] link\n- `<title>` in a code span, <https://example.com/x> a link and &amp; an entity\n\n"
              "<div>a block of text</div>\n\n| a | b |\n|---|---|\n| <textarea> | x |\n\n## Heading with <style>\n\n```\n<title> fenced\n```\n")
        for layout in ("wiki", "classic"):
            o = os.path.join(tmp, "raw-" + layout)
            rc, out = build(root, o, "--layout", layout)
            pg = page_of(o, "myco-notes-rawhtml")
            art = pg[pg.index("<article"):pg.index("</article>")]
            check(f"{layout}: it builds and warns about nothing", rc == 0 and "warning" not in out, out)
            check(f"{layout}: the page keeps one title and no element opened by the text",
                  pg.count("<title>") == 1 and not re.search(r"<(textarea|style|xmp|iframe|plaintext)\b|<div>|<!--", art) and "<script>alert" not in pg, art[:600])
            check(f"{layout}: the text is shown as text", all(t in art for t in ("Saved: &lt;title&gt;", "&lt;textarea&gt; field", "&lt;script&gt;alert(1)&lt;/script&gt;", "&lt;!-- never closed", "&lt;div&gt;a block of text&lt;/div&gt;")), art[:600])
            check(f"{layout}: code spans, fenced blocks, autolinks and entities still work",
                  "<code>&lt;title&gt;</code>" in art and "<code>&lt;title&gt; fenced" in art and '<a href="https://example.com/x">' in art and "&amp; an entity" in art, art[:900])
            if layout == "wiki":
                check("wiki: a link a note forges by hand is text, the real [[wiki link]] beside it is a link",
                      '<a class="wikilink" href="javascript:' not in pg and "link&lt;/a&gt; and a real" in art and "forged &lt;a class=" in art and '<a class="wikilink" href="myco-notes-runbook.html">runbook</a>' in art and "data-myco" not in pg, art[:500])
                check("wiki: both script tags of the page are still there, and the structure parses",
                      pg.count('<script src="../assets/nav.js"></script><script src="../assets/wiki.js"></script>') == 1 and 'id="tree"' in pg and 'id="outline"' in pg
                      and 'id="rawhtml"' not in pg, pg[-300:])
                tags = []
                class Tags(HTMLParser):
                    def handle_starttag(self, tag, attrs):
                        tags.append(tag)
                Tags().feed(pg)
                check("wiki: the page has exactly the shell's script elements (no script came from the text)", tags.count("script") == 4 and tags.count("title") == 1, str(tags.count("script")))
        sys.path.insert(0, os.path.join(REPO, "skills", "myco-notes", "tools"))
        import map_wiki
        good = page_of(os.path.join(tmp, "raw-wiki"), "myco-notes-rawhtml")
        check("the page check accepts a good page", map_wiki.page_problems(good) == [])
        broken = good.replace('<article class="doc">', '<article class="doc"><title>').replace('<script src="../assets/nav.js"></script><script src="../assets/wiki.js"></script>', "")
        check("the page check names a page that lost its scripts and carries a raw-text tag", len(map_wiki.page_problems(broken)) == 3, str(map_wiki.page_problems(broken)))
        os.remove(os.path.join(root, "myco-notes", "rawhtml.md"))

        print("without the markdown package")
        shim = os.path.join(tmp, "shim")
        write(os.path.join(shim, "markdown.py"), 'raise ImportError("not installed (test)")\n')
        shutil.rmtree(os.path.join(root, "myco-notes", "pg"))
        os.remove(os.path.join(root, "myco-notes", "pg-x.md"))
        pl = os.path.join(tmp, "plain")
        rc, out = build(root, pl, "--layout", "wiki", env={"PYTHONPATH": shim})
        ps = page_of(pl, "myco-notes-state") if rc == 0 else ""
        check("it builds and shows the text as preformatted text", rc == 0 and '<pre class="plain" tabindex="0">' in ps and "Pick in October" not in ps and "quincunx" in ps, out)
        check("the plain text still links wiki links, relative links and file names", 'href="myco-notes-entities-cider-press.html"' in ps and 'href="myco-notes-plans-harvest-plan.html' in ps and 'href="myco-notes-runbook.html"' in ps and "&lt;" not in ps.replace("&lt;a", ""), ps[ps.index("<pre"):][:900])
        check("the header, links here, history and the tree are there without it", "Review due since 2020-01-01" in ps and 'id="linkshere"' in ps and 'id="history"' in ps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"wiki: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
