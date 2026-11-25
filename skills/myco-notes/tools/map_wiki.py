"""map_wiki: the wiki layout of the notes map (build-notes-map.py --layout wiki, or "layout": "wiki" in .myco-notes-map.json).

The same notes, relations, groups, freshness and history as the classic map, laid out like a wiki site: a tree of the groups on the left, breadcrumbs
and a header (summary, freshness, last edit) on every note, the article in the middle with a sticky outline on the right, "What links here" and
"Mentions" as lists with each note's title and summary, previous and next within the group, a "Recently changed" page from git, and a search
across the text of the notes. Links between notes (wiki links, relative Markdown links, file-name mentions) are real links.

File names stay those of the classic map (index.html, p/<slug>.html, raw/<slug>.md, graph.html), so the mycelium view still links to every note.
New: recent.html and assets/ (wiki.css with every theme's variables and the project's own, wiki.js, nav.js: the tree, search.js: the text of the
notes, loaded only when someone searches). Standard library only; works from a double-click (no fetch, no network).
"""
import datetime
import html
import json
import os
import re
import secrets
import shutil
import sys
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
import _myco  # noqa: E402
import map_themes  # noqa: E402
import notes_graph  # noqa: E402

esc = html.escape
SEARCH_CHARS = 100000          # most text of one note that goes into the search index
RECENT_COMMITS = 100           # most commits on the "Recently changed" page
MORE_AFTER = 15                # a list of links longer than this folds the rest away
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
TAG = re.compile(r"(<[^>]*>)")
A_HREF = re.compile(r'<a href="([^"]*)"([^>]*)>(.*?)</a>', re.S)
RAW_TEXT = re.compile(r"<(?:script|style|title|textarea|xmp|noscript|iframe|plaintext|noembed|noframes|template|svg|math)\b|<!--", re.I)
MD_TEXT_LINK = re.compile(r"\[([^\]\n]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FRESH_KEYS = ("last_confirmed", "review_after", "valid_from", "valid_until", "supersedes", "superseded_by")


def dash(s):
    return re.sub(r"[^\w\s-]", "", s.strip().lower()).replace(" ", "-")      # the heading anchor the Markdown toc makes (close enough for [[Note#heading]])


def date_of(t):
    return datetime.date.fromtimestamp(t).isoformat()


# ---------- links ----------
class Linker:
    """Turns what the kit understands as a link between notes into real links, for one note at a time."""

    def __init__(self, c):
        self.c, self.n = c, 0
        self.mark = f' data-myco="{secrets.token_hex(8)}"'      # only the tags written below carry it: the Markdown step lets those through and escapes any other raw HTML

    def trusted(self, tag):
        return self.mark in tag

    def page(self, tgt, frag=""):
        return self.c.info[tgt]["id"] + ".html" + frag

    def dead(self, text, why, mark=""):
        return f'<span class="nolink"{mark} title="{esc(why)}">{text}</span{mark}>'

    def wiki(self, rel, src):
        """[[Note]], [[Note|text]], [[Note#heading]] and ![[Note]] in Markdown source (code is left alone) become HTML links."""
        c = self.c

        def repl(m):
            target, heading, text = (m.group(2) or "").strip(), (m.group(3) or "").strip(), (m.group(4) or "").strip()
            label = esc(text or (target + ("#" + heading if heading else "") if target else heading))
            if not target:
                return f'<a class="wikilink"{self.mark} href="#{esc(dash(heading))}">{label}</a{self.mark}>' if heading else m.group(0)
            tgt = c.link_index.resolve("wiki", target, rel)
            if tgt in c.info:
                return f'<a class="wikilink"{self.mark} href="{self.page(tgt, "#" + dash(heading) if heading else "")}">{label}</a{self.mark}>'
            return self.dead(label, f"No note called {target} in this map", self.mark)

        out, in_code = [], False
        for line in src.split("\n"):
            if line.lstrip().startswith(("```", "~~~")):
                in_code = not in_code
            if in_code or "[[" not in line:
                out.append(line)
                continue
            out.append("".join(p if p.startswith("`") else _myco.WIKI_PARTS.sub(repl, p) for p in re.split(r"(`[^`\n]*`)", line)))
        return "\n".join(out)

    def relative(self, rel, htm):
        """The links Markdown wrote, to a relative path: a note becomes its page; anything else the map does not hold is shown as text."""
        c = self.c

        def repl(m):
            href = html.unescape(m.group(1))
            if SCHEME.match(href) or href.startswith(("#", "//")):
                return m.group(0)
            path, _, frag = href.partition("#")
            path = unquote(path.split("?")[0])
            if not path:
                return m.group(0)
            tgt = c.link_index.resolve("path", path, rel)
            if tgt in c.info:
                return f'<a href="{esc(self.page(tgt, "#" + frag if frag else ""))}"{m.group(2)}>{m.group(3)}</a>'
            return self.dead(m.group(3), f"{path} is not a note in this map")
        return A_HREF.sub(repl, htm)

    def mentions(self, rel, htm):
        """A file name of another note written in the text (the mentions the map counts) becomes a link, so does `name.md` alone in a code span.
        Links, code blocks and headings are left alone."""
        c = self.c
        if not c.name_re:
            return htm
        skip = {"a": 0, "pre": 0, "code": 0, "h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0}
        out = []
        for piece in TAG.split(htm):
            if piece.startswith("<"):
                m = re.match(r"<(/?)([A-Za-z0-9]+)", piece)
                if m and m.group(2).lower() in skip and not piece.endswith("/>"):
                    skip[m.group(2).lower()] += -1 if m.group(1) else 1
                out.append(piece)
                continue
            if skip["a"] or skip["pre"] or any(skip[h] for h in ("h1", "h2", "h3", "h4", "h5", "h6")):
                out.append(piece)
            elif skip["code"]:
                tgt = c.linkable.get(piece)
                out.append(f'<a class="mention" href="{self.page(tgt)}">{piece}</a>' if tgt and tgt != rel else piece)
            else:
                out.append(c.name_re.sub(lambda m: self.link_name(rel, m.group(1)), piece))
        return "".join(out)

    def link_name(self, rel, name):
        tgt = self.c.linkable.get(name)
        return f'<a class="mention" href="{self.page(tgt)}">{name}</a>' if tgt and tgt != rel else name

    def plain(self, rel, text):
        """The plain-text fallback (no markdown package): the same three kinds of link inside the escaped text."""
        c, held = self.c, []

        def keep(s):
            held.append(s)
            return f"\x00{len(held) - 1}\x00"

        def wiki(m):
            tgt = c.link_index.resolve("wiki", (m.group(2) or "").strip(), rel) if (m.group(2) or "").strip() else None
            return keep(f'<a class="wikilink" href="{self.page(tgt)}">{m.group(0)}</a>') if tgt in c.info else m.group(0)

        def md(m):
            href = html.unescape(m.group(2))
            if SCHEME.match(href) or href.startswith(("#", "//")):
                return m.group(0)
            tgt = c.link_index.resolve("path", unquote(href.partition("#")[0].split("?")[0]), rel) if href.partition("#")[0] else None
            return keep(f'<a href="{self.page(tgt)}">{m.group(0)}</a>') if tgt in c.info else m.group(0)
        text = _myco.WIKI_PARTS.sub(wiki, esc(text, quote=False))
        text = MD_TEXT_LINK.sub(md, text)
        if c.name_re:
            text = c.name_re.sub(lambda m: keep(self.link_name(rel, m.group(1))), text)
        return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], text)


HEAD_SPLIT = 60          # a heading longer than this (visible characters) with a " (" after a short start shows the start as the heading and the rest below it


def _plain_len(html):
    return len(re.sub(r"<[^>]*>", "", html))


def _split_at(html):
    """(main, rest) when the heading's HTML has a ' (' after at least 8 characters of plain start and no tag before it, else None."""
    i = html.find(" (")
    if i < 8 or "<" in html[:i] or _plain_len(html) <= HEAD_SPLIT:
        return None
    return html[:i], html[i + 1:]


def split_heading(html):
    """A long heading such as '1. Current state (each row carries its own check date; ...)': the start is the heading, the parenthesis a quieter line
    under it (the anchor and the text are unchanged, so every link to the section still works)."""
    s = _split_at(html)
    return html if not s else f'<span class="hmain">{s[0]}</span> <span class="hsub">{s[1]}</span>'


def short_link(href, html):
    """An outline entry: the heading's start only, the whole heading as the tooltip, when it is long."""
    if _plain_len(html) <= HEAD_SPLIT:
        return f'<a href="{href}">{html}</a>'
    s = _split_at(html)
    full = re.sub(r"<[^>]*>", "", html).replace('"', "&quot;")
    return f'<a href="{href}" title="{full}">{s[0] if s else html}</a>'


def render(c, d, linker):
    """(article HTML, outline HTML) of one note."""
    rel, src = d["rel"], d["shown"]
    first = re.match(r"\s*#\s+[^\n]*\n?", src)
    if first:                                            # the title is the page's own heading
        src = src[first.end():]
    if c.md_lib:
        m = c.md_lib.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists", _myco.markdown_no_raw_html(linker.trusted)],
                              extension_configs={"toc": {"permalink": "#", "permalink_title": "Link to this section", "toc_depth": "1-3"}})
        body = m.convert(linker.wiki(rel, src)).replace(linker.mark, "")
        body = linker.mentions(rel, linker.relative(rel, body))
        body = re.sub(r"<pre>", '<pre tabindex="0">', body)
        body = re.sub(r"<table>", '<div class="tablewrap" tabindex="0" role="region" aria-label="Table"><table>', body).replace("</table>", "</table></div>")
        toc = m.toc if re.search(r"<li>", m.toc or "") else ""
        body = re.sub(r'(<h([1-4]) id="[^"]*">)(.*?)(<a class="headerlink")', lambda x: x.group(1) + split_heading(x.group(3)) + x.group(4), body)
        toc = re.sub(r'<a href="(#[^"]*)">(.*?)</a>', lambda x: short_link(x.group(1), x.group(2)), toc)
    else:
        body, toc = '<pre class="plain" tabindex="0">' + linker.plain(rel, src) + "</pre>", ""
    return body, toc


def page_problems(page):
    """What is wrong with a note page that was just written, as short sentences (empty when it is fine). A tag that reaches the article from a note's text
    (the renderer turns raw HTML off, so this should never happen) can open a raw-text element that swallows the rest of the page, the scripts included,
    and nothing shows an error: the tree and the outline are just empty."""
    out = []
    if page.count("<title>") != 1:
        out.append(f"{page.count('<title>')} <title> elements instead of 1")
    if len(re.findall(r'<script src="[^"]*assets/(?:nav|wiki)\.js"></script>', page)) != 2:
        out.append("not both <script src> tags (assets/nav.js, assets/wiki.js)")
    art = re.search(r'<article class="doc">(.*?)</article>', page, re.S)
    if art and RAW_TEXT.search(art.group(1)):
        out.append("a raw-text or comment tag inside the article")
    return out


# ---------- the notes' own status ----------
def freshness(c, d):
    """([(status label, warn?)], fields line HTML) from the header (method 10.1), or None when the note has no header."""
    fm = d["fm"]
    if not any(fm.get(k) for k in FRESH_KEYS):
        return None
    today, stale = c.today, c.stale_days
    vu, ra, lc = fm.get("valid_until", ""), fm.get("review_after", ""), fm.get("last_confirmed", "")
    iso = lambda s: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s or ""))
    st = []
    if iso(vu) and vu < today:
        st.append((f"Expired {vu}", True))
    if fm.get("superseded_by"):
        st.append(("Superseded", True))
    if iso(ra) and ra < today:
        st.append((f"Review due since {ra}", True))
    elif iso(ra):
        st.append(("Up to date", False))
    elif iso(lc) and (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(lc)).days > stale:
        st.append((f"Not confirmed since {lc}", True))
    elif iso(lc):
        st.append((f"Confirmed {lc}", False))
    parts = []
    for k in FRESH_KEYS:
        v = fm.get(k)
        if not v:
            continue
        shown = esc(v)
        if k in ("supersedes", "superseded_by"):
            tgt = c.link_index.resolve("wiki", v.split(",")[0].strip(), d["rel"])
            if tgt in c.info:
                shown = f'<a href="{c.info[tgt]["id"]}.html">{esc(v)}</a>'
        parts.append(f"{esc(k.replace('_', ' '))} {shown}")
    return st, " &middot; ".join(parts)


def code(d):
    """The file name after a title, unless the title is the file name already."""
    return "" if d["title"] == d["name"] else f' <code>{esc(d["name"])}</code>'


def row(c, i, n, base, group_of=None):
    """One note as a list row: title, count of mentions, one-line summary."""
    d = c.byid[i]
    count = f'<span class="n" title="{n} mention{"s" if n != 1 else ""}">&times;{n}</span>' if n > 1 else ""
    return (f'<li><a href="{base}{d["id"]}.html">{count}<b>{esc(d["title"])}</b>{code(d)}'
            f'<span class="sum">{esc(d["hint"])}</span></a></li>')


def rows(c, mp, base=""):
    items = sorted(mp.items(), key=lambda kv: (-kv[1], c.byid[kv[0]]["title"].lower()))
    li = [row(c, i, n, base) for i, n in items]
    if len(li) <= MORE_AFTER:
        return '<ul class="rows">' + "".join(li) + "</ul>"
    return ('<ul class="rows">' + "".join(li[:MORE_AFTER]) + "</ul>"
            f'<details class="more"><summary>Show {len(li) - MORE_AFTER} more</summary><ul class="rows">' + "".join(li[MORE_AFTER:]) + "</ul></details>")


# ---------- pages ----------
def shell(c, *, title, base, cur, main, outline="", crumbs=""):
    brand = esc(c.title)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><link rel="stylesheet" href="{base}assets/wiki.css">{c.head}</head>'
            f'<body data-base="{base}" data-cur="{esc(cur)}"><a class="skip" href="#main">Skip to the note</a>'
            f'<header class="top"><button id="menu" type="button" aria-expanded="false" aria-controls="sidebar">Menu</button>'
            f'<a class="brand" href="{base}index.html" title="{brand}">{brand}</a>'
            f'<form class="search" role="search" onsubmit="return false"><input id="gsearch" type="search" placeholder="Search all notes   ( / )" autocomplete="off" '
            f'role="combobox" aria-expanded="false" aria-controls="results" aria-autocomplete="list" aria-label="Search the text of all notes">'
            f'<ul id="results" class="results" role="listbox" aria-label="Search results" hidden></ul><p id="results-status" class="sr" role="status"></p></form>'
            f'<nav class="tools" aria-label="Map"><a href="{base}recent.html">Recently changed</a><a href="{base}graph.html">Mycelium view</a></nav>{c.pick}</header>'
            f'<div class="scrim" id="scrim"></div>'
            f'<div class="shell"><nav id="sidebar" aria-label="All notes"><ul class="quick"><li><a href="{base}index.html"{" aria-current=page" if cur == "_home" else ""}>Home</a></li>'
            f'<li><a href="{base}recent.html"{" aria-current=page" if cur == "_recent" else ""}>Recently changed</a></li><li><a href="{base}graph.html">Mycelium view</a></li></ul>'
            f'<div class="sbhead"><input id="filter" type="search" placeholder="Filter the tree" aria-label="Filter the list of notes by name, title or summary" autocomplete="off"></div>'
            f'<p id="tree-status" class="sr" role="status"></p><div id="tree"><noscript><p class="empty">The tree needs JavaScript. <a href="{base}index.html">All notes are listed on the home page.</a></p></noscript></div></nav>'
            f'<main id="main">{crumbs}{main}</main>'
            f'<aside id="outline" aria-label="On this page">{outline}</aside></div>'
            f'<script src="{base}assets/nav.js"></script><script src="{base}assets/wiki.js"></script></body></html>')


def crumbs(c, base, group, last=None):
    g = f'<li><a href="{base}index.html#g-{esc(group[0])}">{esc(group[1])}</a></li>' if group else ""
    tail = f'<li aria-current="page">{esc(last)}</li>' if last else ""
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="{base}index.html">{esc(c.title)}</a></li>{g}{tail}</ol></nav>'


def note_page(c, d, linker, ctx):
    rel, base = d["rel"], "../"
    group = ctx["group_of"][d["id"]]
    body, toc = render(c, d, linker)
    fr = freshness(c, d)
    hist = c.log_rows(["--follow", "-n", "12", "--format=%h\t%as\t%s", "--", rel])
    edited = f"Last edited {hist[0][1]}" if hist else f"Edited {date_of(d['mtime'])} (not committed yet)"
    due, miss = ctx["attention"][d["id"]]
    badges = []
    for label, warn in (fr[0] if fr else []):
        badges.append(f'<li><span class="badge {"warn" if warn else "ok"}"><span aria-hidden="true">{"!" if warn else "&check;"}</span> {esc(label)}</span></li>')
    if due:
        badges.append(f'<li><span class="badge warn" title="A date such as &quot;after 2026-01-31&quot; on a line not marked DONE has passed (the lint checks the same)">'
                      f'<span aria-hidden="true">!</span> {due} follow-up date{"s" if due != 1 else ""} passed</span></li>')
    badges.append(f"<li>{esc(edited)}</li>")
    badges.append(f'<li><a href="{base}raw/{d["id"]}.md">Raw file</a></li>')
    badges.append(f'<li><code>{esc(rel)}</code> &middot; {d["size"] // 1024 or 1} KB</li>')
    alerts = ""
    if fr and fr[1]:
        alerts += f'<p class="fresh">{fr[1]}</p>'
    if miss:
        alerts += ('<p class="alert"><b>Missing references:</b> ' + ", ".join(f"<code>{esc(m)}</code>" if not m.startswith("+") else esc(m) for m in miss) +
                   " &mdash; no note has that name (the lint reports the same).</p>")
    pn = ""
    seq = ctx["seq"][group[0]]
    at = seq.index(d["id"])
    prev, nxt = (seq[at - 1] if at else None), (seq[at + 1] if at + 1 < len(seq) else None)
    if prev or nxt:
        card = lambda i, side, lab: (f'<a class="{side}" href="{c.byid[i]["id"]}.html"><small>{lab}</small><b>{esc(c.byid[i]["title"])}</b></a>' if i else "<span></span>")
        pn = f'<nav class="pn" aria-label="Previous and next in {esc(group[1])}">{card(prev, "prev", "&larr; Previous in " + esc(group[1]))}{card(nxt, "next", "Next in " + esc(group[1]) + " &rarr;")}</nav>'
    more = ""
    more += f'<section id="linkshere" class="rel"><h2>What links here <span class="count">{len(d["inn"])}</span></h2>' + \
            (rows(c, d["inn"]) if d["inn"] else '<p class="none">No other note mentions this one.</p>') + "</section>"
    more += f'<section id="mentions" class="rel"><h2>Mentions <span class="count">{len(d["out"])}</span></h2>' + \
            (rows(c, d["out"]) if d["out"] else '<p class="none">This note does not mention another note.</p>') + "</section>"
    if hist:
        more += ('<section id="history" class="rel"><h2>History <span class="count">%d</span></h2><table class="hist"><thead><tr><th scope="col">Date</th><th scope="col">Commit</th><th scope="col">Change</th></tr></thead><tbody>%s</tbody></table></section>'
                 % (len(hist), "".join(f"<tr><td>{dt}</td><td><code>{h}</code></td><td>{esc(s)}</td></tr>" for h, dt, s in hist)))
    foot = ('<ul class="more-links"><li><a href="#linkshere">What links here (%d)</a></li><li><a href="#mentions">Mentions (%d)</a></li>%s</ul>'
            % (len(d["inn"]), len(d["out"]), '<li><a href="#history">History</a></li>' if hist else ""))
    inline = f'<details class="otoc-inline"><summary>On this page</summary>{toc}{foot}</details>'
    main = (f'<header class="nhead"><h1>{esc(d["title"])}</h1><p class="lead">{esc(d["hint"])}</p><ul class="meta">{"".join(badges)}</ul>{alerts}</header>'
            f'{inline}<article class="doc">{body}</article>{pn}{more}')
    outline = "<h2>On this page</h2>" + toc + foot
    return shell(c, title=f'{d["title"]} - {c.title}', base=base, cur=d["id"], main=main, outline=outline, crumbs=crumbs(c, base, group, d["title"]))


def home_page(c, ctx):
    secs = []
    for gid, gname, blurb, items in c.sections:
        rws = "".join(
            f'<a class="note" href="p/{d["id"]}.html" data-s="{esc((d["rel"] + " " + d["title"] + " " + d["hint"]).lower())}">'
            f'<b>{esc(d["title"])}</b>{code(d)}{ctx["mark"](d)}<small>{esc(d["rel"])} &mdash; {esc(d["hint"])}</small></a>' for d in items)
        secs.append(f'<section class="grp" id="g-{esc(gid)}"><h2>{esc(gname)} <span class="count">{len(items)}</span></h2><p>{esc(blurb)}</p>{rws}</section>')
    recent = c.log_rows(["-n", "15", "--format=%h\t%as\t%s"])
    rec = ('<section class="recent" id="recent"><h2>Recent changes</h2><ul>%s</ul><p><a href="recent.html">Everything that changed lately, note by note &rarr;</a></p></section>'
           % "".join(f"<li><code>{h}</code> {dt} &middot; {esc(s)}</li>" for h, dt, s in recent)) if recent else \
          '<p><a href="recent.html">Recently changed notes &rarr;</a></p>'
    main = (f'<header class="nhead"><h1>{esc(c.title)}</h1><p class="lead">{len(c.info)} notes in {len(c.sections)} groups. Built {esc(c.built)}. '
            'Open a note to see what it mentions, what mentions it and how it changed. <a href="graph.html">Open the mycelium view</a> (graph and timeline).</p></header>'
            '<p><input id="q" class="listfilter" type="search" placeholder="Filter this list by name, title or summary..." aria-label="Filter the list of notes"></p>'
            f'{"".join(secs)}{rec}'
            "<script>var q=document.getElementById('q');q.addEventListener('input',function(){var t=q.value.toLowerCase();document.querySelectorAll('.note').forEach(function(n){n.style.display=n.dataset.s.includes(t)?'':'none'});"
            "document.querySelectorAll('.grp').forEach(function(g){g.style.display=[].some.call(g.querySelectorAll('.note'),function(n){return n.style.display!=='none'})?'':'none'})})</script>")
    return shell(c, title=c.title, base="", cur="_home", main=main, outline="", crumbs="")


def recent_page(c, commits):
    shown = [x for x in reversed(commits) if x["n"]][:RECENT_COMMITS]
    days, last = [], None
    for x in shown:
        day = date_of(x["t"])
        if day != last:
            days.append([day, []])
            last = day
        ids = [c.info[p]["id"] for p in x["n"] if p in c.info]
        links = ", ".join(f'<a href="p/{i}.html">{esc(c.byid[i]["title"])}</a>' for i in ids[:6]) + (f" and {len(ids) - 6} more" if len(ids) > 6 else "")
        days[-1][1].append(f'<li><span class="what">{esc(x["s"])}</span><span class="which"><code>{x["h"]}</code> {links}</span></li>')
    body = "".join(f"<section class=\"day\"><h2>{day}</h2><ul class=\"log\">{''.join(items)}</ul></section>" for day, items in days) or "<p class=\"none\">No commit has touched a note yet.</p>"
    main = (f'<header class="nhead"><h1>Recently changed</h1><p class="lead">The latest commits that touched a note, newest first, with the notes they changed '
            f'({len(shown)} shown, from git history).</p></header>{body}')
    return shell(c, title=f"Recently changed - {c.title}", base="", cur="_recent", main=main, crumbs=crumbs(c, "", None, "Recently changed"))


# ---------- search and navigation data ----------
def plain_text(text):
    t = re.sub(r"```[^\n]*", " ", text)
    t = re.sub(r"!?\[([^\]\n]*)\]\([^)\n]*\)", r"\1", t)
    t = re.sub(r"\[\[([^\]\n|#]*)(?:#[^\]\n|]*)?(?:\|([^\]\n]*))?\]\]", lambda m: m.group(2) or m.group(1), t)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"[`*|>]+", " ", t)
    t = re.sub(r"(?<!\w)_+|_+(?!\w)", " ", t)           # emphasis marks, not the underscores inside names
    return re.sub(r"\s+", " ", t).strip()[:SEARCH_CHARS]


def js_data(name, value):
    blob = json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/").replace("<!--", "<\\!--")
    return f"window.{name}={blob};\n"


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def build(c):
    """Write the wiki into c.out. c holds: root, lay, out, title, info, byid, sections [(gid, name, blurb, [notes])], linkable, name_re, link_index,
    md_lib, project (the checked theme setting), log_rows, sh, built, today, stale_days."""
    info = c.info
    names = {d["name"] for d in info.values()}
    commits = notes_graph.commit_history(c.root, set(info), c.sh)
    att = {d["id"]: notes_graph.attention(c.root, c.lay, rel, d["text"], names, c.today) for rel, d in info.items()}
    group_of, seq = {}, {}
    for gid, gname, _, items in c.sections:
        seq[gid] = [d["id"] for d in items]
        for d in items:
            group_of[d["id"]] = (gid, gname)
    c.hist = notes_graph.prefixes(c.lay)[1]
    c.head = map_themes.head_script()
    c.pick = map_themes.picker()

    def flagged(d):
        fr = freshness(c, d)
        due, miss = att[d["id"]]
        return bool((fr and any(w for _, w in fr[0]) and not d["rel"].startswith(c.hist)) or due or miss)
    mark = lambda d: ' <span class="flag" title="Needs a look: a date has passed or a reference is missing (open the note)">needs a look</span>' if flagged(d) else ""
    ctx = {"group_of": group_of, "seq": seq, "attention": att, "mark": mark}

    assets = os.path.join(c.out, "assets")
    os.makedirs(assets)
    with open(os.path.join(HERE, "wiki-template.css"), encoding="utf-8") as fh:
        css = map_themes.wiki_css(c.project) + "\n" + fh.read() + "\n" + map_themes.project_vars(c.project) + "\n"
    write(os.path.join(assets, "wiki.css"), css)
    shutil.copy(os.path.join(HERE, "wiki.js"), os.path.join(assets, "wiki.js"))
    nav = {"groups": []}
    for gid, gname, _, items in c.sections:
        dupes = {}
        for d in items:
            dupes[d["title"]] = dupes.get(d["title"], 0) + 1
        nav["groups"].append({"id": gid, "name": gname, "notes": [
            {"i": d["id"], "t": d["title"] if dupes[d["title"]] == 1 else f'{d["title"]} ({os.path.dirname(d["rel"]) or "root"})', "n": d["name"], "h": d["hint"][:140], "a": 1 if flagged(d) else 0}
            for d in items]})
    write(os.path.join(assets, "nav.js"), js_data("MYCO_NAV", nav))
    idx = []
    for rel, d in sorted(info.items()):
        idx.append({"i": d["id"], "t": d["title"], "r": rel, "g": group_of[d["id"]][1], "h": d["hint"],
                    "s": " | ".join(re.findall(r"^#{1,6}\s+(.+)$", d["shown"], re.M))[:600], "x": plain_text(d["shown"])})
    write(os.path.join(assets, "search.js"), js_data("MYCO_SEARCH", idx))

    linker = Linker(c)
    for rel, d in info.items():
        page = note_page(c, d, linker, ctx)
        write(os.path.join(c.out, "p", d["id"] + ".html"), page)
        for why in page_problems(page):
            print(f"warning: {rel}: the page is broken ({why}); the tree and the outline may not load", file=sys.stderr)
        shutil.copy(os.path.join(c.root, rel), os.path.join(c.out, "raw", d["id"] + ".md"))
    write(os.path.join(c.out, "index.html"), home_page(c, ctx))
    write(os.path.join(c.out, "recent.html"), recent_page(c, commits))
