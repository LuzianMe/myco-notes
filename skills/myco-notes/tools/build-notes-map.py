#!/usr/bin/env python3
"""build-notes-map: generate a navigable static view of the notes (index, one page per note, backlinks, git history).

  tools/build-notes-map.py [--root DIR] [--out DIR] [--layout classic|wiki]        default out: the map folder of .myco-notes.conf (myco-notes/map, or notes-map in older repositories; gitignored, rebuilt on demand)
  tools/build-notes-map.py --public [--labels FILE] [--title TEXT] --out DIR
                            only DIR/graph.html, a public mycelium view to embed on a website: no note name, title, path, size or commit
                            subject, only the labels of FILE ({"note-name": "Label shown"}, keyed by the file name without .md); every
                            other note is an unlabelled dot. It opens in embed mode. Other files in DIR are left alone.

What it produces (the classic layout; --layout wiki, or "layout": "wiki" in .myco-notes-map.json, makes the wiki layout of map_wiki.py from the
same data: group tree, breadcrumbs, outline, "what links here", recently changed, search across the text; it also writes recent.html and assets/)
  index.html        notes grouped by purpose, live search, the 15 latest commits
  p/<slug>.html     each note rendered, with table of contents, 'mentions' and 'mentioned by' chips and its recent git history
  raw/<slug>.md     the original files
  graph.html        the mycelium view: notes as a living network (mentions, groups, freshness, follow-ups gone stale, missing references) with a
                    timeline that replays the git history; one self-contained file, opens by double-click; only titles, paths and commit subjects
Relations are file-name mentions: a note that writes `runbook.md` in backticks (or plain text) mentions that note; wiki links
([[Note name]], [[Note name|text]]) and Markdown links to relative paths ([text](../a/note.md)) count too.
It refuses to build if any note contains a secret-looking string (publication gate; the rules of tools/secret_scan.py, value hidden).
The output folder is emptied and rebuilt, so --out must not be the repository or a folder that contains it, and must be empty,
missing, or a map this tool built (it leaves a .myco-notes-map marker there).
Two notes whose paths give the same page name (a/b.md and a-b.md) keep apart: the later one gets a short hash of its path.
Optional config: .myco-notes-map.json  {"title": "...", "groups": [{"id","name","blurb","prefixes":["myco-notes/plans/"]}], "hints": {"myco-notes/state.md": "one line"},
        "layout": "wiki", "theme": {"light": {"accent": "#7a3e00"}, "dark": {"accent": "#ffb454"}, "font": "Georgia, serif", "mono": "monospace", "radius": "4px"}}
        (theme: the wiki layout's own colours for its Light and Dark themes, a font, a code font and a corner radius; see tools/map_themes.py project_theme)
        (a hint replaces the note's own one-line `summary` from its header, method 10.1; without either, the first paragraph is shown)
Folders: the notes folder, docs folder and map folder come from .myco-notes.conf (see tools/_myco.py layout); DATA_DIRS (project data that is not notes) are left out.
Needs only the Python standard library; if the 'markdown' package is installed pages are rendered nicely, otherwise as preformatted text.
"""
import argparse, datetime, html, json, os, re, shutil, subprocess, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402
import notes_graph  # noqa: E402
import secret_scan  # noqa: E402
import hashlib  # noqa: E402
import map_themes  # noqa: E402
import map_wiki  # noqa: E402

SKIP_DIRS = {".git", "site", "notes-map", "node_modules", "__pycache__", ".obsidian", ".trash"}
MARKER = ".myco-notes-map"   # marks a folder this tool made, so it may empty and rebuild it
MAP_FILES = {"index.html", "graph.html", "p", "raw", "recent.html", "assets", MARKER}
LAYOUTS = ("classic", "wiki")


def default_groups(lay):
    n = lay["notes"] + "/"
    start = ["AGENTS.md", "CLAUDE.md", "README.md"] + [n + f for f in ("working-agreement.md", "sync-tracker.md", lay["state"], "runbook.md")]
    return [
        ("start", "Start here", "Read in this order: entry point, working agreement, tracker, master record, runbook.", start),
        ("plans", "Plans, backlog and decisions", "What is parked, planned, waiting or decided.", [n + "plans/"]),
        ("inbox", "Inbox", "Quick notes as they were captured, one file per month, waiting to be sorted into the notes.", [n + "inbox/"]),
        ("logs", "Effort logs and incidents", "Chronological records of large efforts and incidents.", [n + "logs/"]),
        ("verify", "Verification", "Health check and test procedures.", [n + "verification/"]),
        ("artifacts", "Deployed artifacts", "Repository copies of what runs elsewhere (READMEs of bundles).", [n + "scripts/"]),
        ("archive", "Archive", "Old detail kept for history.", [n + "archive/"]),
        ("imported", "Imported, as found", "Notes taken over from an older collection, unchanged (method section 20); the import log says what became of each.", [n + "imported/"]),
        ("sources", "Sources", "Outside documents as they were retrieved: manuals, release notes, articles (method section 22); notes cite them.", [n + "sources/"]),
        ("docs", "Method", "How the notes are kept.", [lay["docs"] + "/"]),
        ("other", "Other notes", "Everything else (entity notes and new files appear here automatically).", []),
    ]


def area_groups(groups, info, lay):
    """The project's own groups (method 9): a note the method's groups left in "other" goes to its `area` header's group, or to the group of
    the subfolder of the notes folder it sits in. They come right after "Start here", so they get the first colours. Changes info in place."""
    notes = lay["notes"] + "/"
    found = {}                                     # group id -> (name, blurb, count)
    for rel, d in info.items():
        if d["group"] != "other":
            continue
        area = (d["fm"].get("area") or "").strip().strip("\"'")
        if area:
            gid = "area-" + re.sub(r"[^a-z0-9]+", "-", area.lower()).strip("-")
            name, blurb = area, f"Notes about {area} (their area header)."
        elif rel.startswith(notes) and "/" in rel[len(notes):]:
            sub = rel[len(notes):].split("/", 1)[0]
            role = next((g for g in default_groups(lay) if notes + sub + "/" in g[3]), None)
            if role:                               # a method folder a custom map configuration does not list keeps the method's group
                gid, name, blurb = role[0], role[1], role[2]
            else:
                gid, name, blurb = "dir-" + re.sub(r"[^a-z0-9]+", "-", sub.lower()).strip("-"), sub + "/", f"Notes in {notes}{sub}/."
        else:
            continue
        d["group"] = gid
        cur = found.get(gid)
        found[gid] = (cur[0] if cur else name, blurb, (cur[2] if cur else 0) + 1)
    if not found:
        return groups
    roles = {g[0] for g in default_groups(lay)}
    extra = [(gid, name, blurb, []) for gid, (name, blurb, _) in sorted(found.items(), key=lambda kv: (-kv[1][2], kv[1][0].lower())) if gid not in roles]
    late = [(gid, name, blurb, []) for gid, (name, blurb, _) in found.items() if gid in roles and gid not in {g[0] for g in groups}]
    at = next((i + 1 for i, g in enumerate(groups) if g[0] == "start"), 0)
    return groups[:at] + extra + groups[at:-1] + late + groups[-1:] if groups and groups[-1][0] == "other" else groups[:at] + extra + groups[at:] + late


CSS = map_themes.page_css() + """
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 var(--font)}a{color:var(--accent)}
.top{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:4px 14px}.top>p,.top>h1{margin:0 0 6px;min-width:0}
.theme-pick{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);margin:0 0 6px auto;white-space:nowrap}
.theme-pick select{font:inherit;font-size:13px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--fg)}
.theme-pick select:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.wrap{max-width:1100px;margin:0 auto;padding:18px 16px 50px}h1{font-size:24px;margin:0 0 6px}.sub{color:var(--muted);margin:0 0 14px}
input{font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--fg);width:100%;max-width:360px}
.grp{background:var(--panel);border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:6px 14px}.grp h2{font-size:16px;margin:8px 0 2px}.grp p{margin:0 0 6px;color:var(--muted);font-size:13px}
.note{display:block;padding:7px 0;border-top:1px solid var(--line);text-decoration:none;color:var(--fg)}.note small{display:block;color:var(--muted)}.note b{color:var(--accent)}
article{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 24px 24px}article code{background:var(--code);padding:1px 5px;border-radius:4px}
article pre{background:var(--code);padding:12px;overflow:auto;border-radius:6px}article table{display:block;overflow-x:auto;border-collapse:collapse}article th,article td{border:1px solid var(--line);padding:5px 9px}
.rel{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:10px 0;font-size:13px;background:var(--bg)}.chip{display:inline-block;margin:2px 4px 2px 0;padding:1px 9px;border-radius:99px;border:1px solid var(--line);text-decoration:none;background:var(--panel)}
.recent{color:var(--muted);font-size:13px}.recent code{font:12px ui-monospace,monospace}"""
HEAD = map_themes.head_script()   # applies the stored theme before the first paint
PICK = map_themes.picker()        # the theme picker, the same on every page


def group_items(groups, info):
    """[(id, name, blurb, [notes in the order shown])] for the groups that have notes: the method's order inside a group with prefixes, else by path."""
    out = []
    for gid, gname, blurb, prefixes in groups:
        items = [d for d in info.values() if d["group"] == gid]
        if prefixes and gid != "other":
            order = {p: i for i, p in enumerate(prefixes)}
            items.sort(key=lambda d: (order.get(d["rel"], 99), d["rel"]))
        else:
            items.sort(key=lambda d: d["rel"])
        if items:
            out.append((gid, gname, blurb, items))
    return out


def sh(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout
    except Exception:
        return ""


def slug(rel):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", rel[:-3]).strip("-")


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--layout", choices=LAYOUTS, default=None, help="classic (default) or wiki: the same notes laid out like a wiki site (see above); \"layout\" in .myco-notes-map.json sets it for the project")
    ap.add_argument("--public", action="store_true", help="write only <out>/graph.html, a public graph for a website (see above)")
    ap.add_argument("--labels", default=None, help="with --public: the approved labels, a JSON object {\"note-name\": \"Label shown\"}")
    ap.add_argument("--title", default=None, help="with --public: a title for the page (default: none)")
    a = ap.parse_args()
    if (a.labels is not None or a.title is not None) and not a.public:
        ap.error("--labels and --title go with --public")
    if a.public and not a.out:
        ap.error("--public needs --out DIR (the folder that gets graph.html)")
    labels = {}
    if a.public and a.labels:
        try:
            labels = notes_graph.read_labels(a.labels)
        except (OSError, ValueError) as e:
            sys.exit(f"REFUSING to build: {e}")
        for k, v in labels.items():
            if secret_scan.find(v) or secret_scan.find(k):
                sys.exit(f"REFUSING to build: a label in {a.labels} looks like it contains a secret (value not shown)")
    root = sh(["git", "rev-parse", "--show-toplevel"], a.root).strip() or os.path.abspath(a.root)
    lay = _myco.layout(root)
    out = os.path.abspath(a.out) if a.out else os.path.join(root, *lay["map"].split("/"))
    rel_out = _myco.overlap(root, out)
    if a.public:
        if rel_out == "same" or os.path.isfile(out):
            sys.exit(f"REFUSING to build: --out {out} must be a folder other than the repository's own root")
    elif rel_out in ("same", "contains"):
        sys.exit(f"REFUSING to build: --out {out} is the repository or contains it, and the output folder is emptied before each build")
    elif not _myco.owned_or_empty(out, MARKER, lambda d: set(os.listdir(d)) <= MAP_FILES and "index.html" in os.listdir(d)):
        sys.exit(f"REFUSING to build: {out} holds files this tool did not make, and the output folder is emptied before each build; "
                 "choose an empty or new folder")
    skip_rel = {lay["map"], *lay["data"]}
    cfg = {}
    cp = os.path.join(root, ".myco-notes-map.json")
    if os.path.exists(cp):
        cfg = json.load(open(cp, encoding="utf-8"))
    title = cfg.get("title") or (os.path.basename(root) + " notes")
    layout = a.layout or cfg.get("layout") or "classic"
    if layout not in LAYOUTS:
        sys.exit(f'REFUSING to build: "layout" in .myco-notes-map.json must be "classic" or "wiki" (got {layout!r})')
    try:
        project = map_themes.project_theme(cfg.get("theme"))
    except ValueError as e:
        sys.exit(f"REFUSING to build: .myco-notes-map.json: {e}")
    if project and layout != "wiki" and not a.public:
        print('note: "theme" in .myco-notes-map.json applies to the wiki layout only (--layout wiki)', file=sys.stderr)
    hints = cfg.get("hints", {})
    groups = [(g["id"], g["name"], g.get("blurb", ""), g.get("prefixes", [])) for g in cfg["groups"]] if "groups" in cfg else default_groups(lay)
    try:
        import markdown as md_lib
    except Exception:
        md_lib = None

    files = []
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS and os.path.relpath(os.path.join(dp, d), root).replace(os.sep, "/") not in skip_rel
                     and os.path.relpath(os.path.join(dp, d), root).replace(os.sep, "/") not in _myco.AGENT_SKILL_DIRS
                       and not os.path.relpath(os.path.join(dp, d), root).replace(os.sep, "/").startswith("template"))
        for f in sorted(fn):
            if f.endswith(".md"):
                files.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    info = {}
    for rel in files:
        text = open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
        for ln, line in enumerate(text.split("\n"), 1):
            hit = secret_scan.find(line)
            if hit:
                sys.exit(f"REFUSING to build: {rel}:{ln} looks like it contains a secret ({hit[0]}; value not shown)")
        fm, fm_end = _myco.frontmatter(text)      # optional freshness header (method 10.1): shown as a line, not rendered as text
        shown = "\n".join(text.split("\n")[fm_end:]) if fm_end else text
        h1 = re.search(r"^#\s+(.+)$", shown, re.M)
        ttl = re.sub(r"[`*_]", "", h1.group(1)).strip() if h1 else os.path.basename(rel)
        body = shown[h1.end():] if h1 else shown
        para = next((l.strip() for l in body.split("\n") if l.strip() and not l.lstrip().startswith(("#", "|", "```", ">", "-", "*"))), "")
        para = re.sub(r"[`*_]|\[([^\]]+)\]\([^)]*\)", lambda mm: mm.group(1) or "", para)
        group = "other"
        for gid, _, _, prefixes in groups:
            if any(rel == p or (p.endswith("/") and rel.startswith(p)) for p in prefixes):
                group = gid
                break
        info[rel] = dict(id=slug(rel), rel=rel, name=os.path.basename(rel), title=ttl, group=group, text=text, shown=shown, fm={k: v[0] for k, v in fm.items()}, out={}, inn={},
                         hint=hints.get(rel) or (fm["summary"][0] if fm.get("summary", ("",))[0] else "") or (para[:170] + ("..." if len(para) > 170 else "")),
                         mtime=os.path.getmtime(os.path.join(root, rel)), size=len(text.encode("utf-8")))
    groups = area_groups(groups, info, lay)
    taken = {}
    for rel in sorted(info):                       # a/b.md and a-b.md give the same page name: the later one gets a path hash
        pid = info[rel]["id"]
        if pid in taken:
            pid = f"{pid}-{hashlib.sha1(rel.encode('utf-8')).hexdigest()[:6]}"
            info[rel]["id"] = pid
        if pid in taken:
            sys.exit(f"REFUSING to build: {rel} and {taken[pid]} would write the same page {pid}.html")
        taken[pid] = rel
    by_name = {}
    for rel, d in info.items():
        by_name.setdefault(d["name"], []).append(rel)
    linkable = {n: v[0] for n, v in by_name.items() if len(v) == 1 and n != "README.md"}
    name_re = None
    if linkable:
        name_re = re.compile(r"(?<![\w./-])(" + "|".join(re.escape(n) for n in sorted(linkable, key=len, reverse=True)) + r")(?![\w-])")
        for rel, d in info.items():
            for mm in name_re.finditer(d["text"]):
                tgt = linkable[mm.group(1)]
                if tgt != rel:
                    info[tgt]["inn"][d["id"]] = info[tgt]["inn"].get(d["id"], 0) + 1
                    d["out"][info[tgt]["id"]] = d["out"].get(info[tgt]["id"], 0) + 1
    link_index = _myco.LinkIndex(list(info))     # wiki links and relative Markdown links count as mentions too (method 9)
    for rel, d in info.items():
        for tgt in {link_index.resolve(k, t, rel) for k, t, _ in _myco.links(d["text"])}:
            if tgt and tgt != rel and tgt in info and info[tgt]["id"] not in d["out"]:
                info[tgt]["inn"][d["id"]] = info[tgt]["inn"].get(d["id"], 0) + 1
                d["out"][info[tgt]["id"]] = 1
    byid = {d["id"]: d for d in info.values()}
    if a.public:
        os.makedirs(out, exist_ok=True)
        gn, ge, gc = notes_graph.build(root, lay, info, groups, out, a.title or "", sh, datetime.date.today().isoformat(), "", public=labels)
        stems = {d["name"][:-3] for d in info.values() if d["name"].endswith(".md")}
        used = sorted(k for k in labels if k in stems)
        print(f"public graph: {gn} notes ({sum(1 for d in info.values() if d['name'][:-3] in labels)} labelled), {ge} links, {gc} commits -> {os.path.join(out, 'graph.html')}")
        unknown = sorted(set(labels) - set(used))
        if unknown:
            print(f"labels that match no note (not used): {', '.join(unknown)}", file=sys.stderr)
        return

    def log_rows(extra):
        rows = [l.split("\t", 2) for l in sh(["git", "log", *extra], root).splitlines()]
        return [r for r in rows if len(r) == 3]

    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(os.path.join(out, "p")); os.makedirs(os.path.join(out, "raw"))
    open(os.path.join(out, MARKER), "w").write("Built by build-notes-map.py; this folder is emptied and rebuilt on each build.\n")
    built = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.date.today().isoformat()
    if layout == "wiki":                           # the same notes, relations and groups, laid out by map_wiki.py
        for w in map_themes.contrast_warnings(project):
            print("warning: " + w, file=sys.stderr)
        stale = _myco.load_conf(root).get("STALE_DAYS", "365")
        map_wiki.build(types.SimpleNamespace(
            root=root, lay=lay, out=out, title=title, info=info, byid=byid, sections=group_items(groups, info), linkable=linkable, name_re=name_re,
            link_index=link_index, md_lib=md_lib, project=project, log_rows=log_rows, sh=sh, built=built, today=today,
            stale_days=float(stale) if re.fullmatch(r"\d+(\.\d+)?", stale or "") else 365.0))
        gn, ge, gc = notes_graph.build(root, lay, info, groups, out, title, sh, today, built)
        print(f"notes map (wiki layout): {len(info)} notes, {sum(len(d['out']) for d in info.values())} relations -> {out}/index.html; graph: {gn} nodes, {ge} links, {gc} commits -> {out}/graph.html")
        return
    for rel, d in info.items():
        if md_lib:
            m = md_lib.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"])
            body = m.convert(d["shown"]); toc = m.toc
            body = re.sub(r"<code>([^<]+)</code>", lambda mm: (f'<a href="{byid[info[linkable[mm.group(1)]]["id"]]["id"]}.html"><code>{mm.group(1)}</code></a>'
                          if mm.group(1) in linkable and linkable[mm.group(1)] != rel else mm.group(0)), body)
        else:
            body, toc = "<pre>" + html.escape(d["shown"]) + "</pre>", ""
        chips = lambda mp, cls: "".join(f'<a class="chip" href="{i}.html">{html.escape(byid[i]["name"])} <small>{n}</small></a>' for i, n in sorted(mp.items(), key=lambda kv: -kv[1]))
        relh = ""
        fr = [(k, d["fm"][k]) for k in ("last_confirmed", "review_after", "valid_from", "valid_until", "supersedes", "superseded_by") if d["fm"].get(k)]
        if fr: relh += "<div><b>Freshness</b> " + " &middot; ".join(html.escape(k.replace("_", " ")) + " " + html.escape(v) for k, v in fr) + "</div>"
        if d["out"]: relh += "<div><b>Mentions</b> " + chips(d["out"], "o") + "</div>"
        if d["inn"]: relh += "<div><b>Mentioned by</b> " + chips(d["inn"], "i") + "</div>"
        hist = log_rows(["--follow", "-n", "12", "--format=%h\t%as\t%s", "--", rel])
        histh = ("<details class='rel'><summary><b>History</b> (%d recent changes)</summary><ul>%s</ul></details>" % (len(hist), "".join(f"<li><code>{h}</code> {dt} &middot; {html.escape(s)}</li>" for h, dt, s in hist))) if hist else ""
        age = datetime.date.fromtimestamp(d["mtime"]).isoformat()
        page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(d["title"])}</title><style>{CSS}</style>{HEAD}</head><body><div class="wrap">'
                f'<div class="top"><p><a href="../index.html">&larr; {html.escape(title)}</a> &middot; <code>{html.escape(rel)}</code> &middot; {d["size"]//1024 or 1} KB &middot; edited {age} &middot; <a href="../raw/{d["id"]}.md">raw</a></p>{PICK}</div>'
                f'<p class="sub">{html.escape(d["hint"])}</p>{"<div class=rel>"+relh+"</div>" if relh else ""}{histh}<details class="rel"><summary><b>On this page</b></summary>{toc}</details><article>{body}</article></div></body></html>')
        open(os.path.join(out, "p", d["id"] + ".html"), "w", encoding="utf-8").write(page)
        shutil.copy(os.path.join(root, rel), os.path.join(out, "raw", d["id"] + ".md"))

    recent = log_rows(["-n", "15", "--format=%h\t%as\t%s"])
    sections = []
    for gid, gname, blurb, items in group_items(groups, info):
        rows = "".join(f'<a class="note" href="p/{d["id"]}.html" data-s="{html.escape((d["rel"]+" "+d["title"]+" "+d["hint"]).lower())}"><b>{html.escape(d["name"])}</b> &middot; {html.escape(d["title"])}<small>{html.escape(d["rel"])} &mdash; {html.escape(d["hint"])}</small></a>' for d in items)
        sections.append(f'<section class="grp"><h2>{html.escape(gname)} ({len(items)})</h2><p>{html.escape(blurb)}</p>{rows}</section>')
    rec = ("<div class='recent'><h2>Recent changes</h2><ul>%s</ul></div>" % "".join(f"<li><code>{h}</code> {dt} &middot; {html.escape(s)}</li>" for h, dt, s in recent)) if recent else ""
    index = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style>{HEAD}</head><body><div class="wrap">'
             f'<div class="top"><h1>{html.escape(title)}</h1>{PICK}</div><p class="sub">{len(info)} notes. Built {built}. Search filters the list; open a note to see what it mentions, what mentions it and how it changed. <a href="graph.html">Open the mycelium view</a> (graph and timeline).</p>'
             f'<p><input id="q" type="search" placeholder="Search names, titles, hints..." aria-label="Search notes"></p>{"".join(sections)}{rec}</div>'
             "<script>const q=document.getElementById('q');q.addEventListener('input',()=>{const t=q.value.toLowerCase();document.querySelectorAll('.note').forEach(n=>{n.style.display=n.dataset.s.includes(t)?'':'none'});document.querySelectorAll('.grp').forEach(g=>{g.style.display=[...g.querySelectorAll('.note')].some(n=>n.style.display!=='none')?'':'none'})})</script></body></html>")
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(index)
    gn, ge, gc = notes_graph.build(root, lay, info, groups, out, title, sh, today, built)
    print(f"notes map: {len(info)} notes, {sum(len(d['out']) for d in info.values())} relations -> {out}/index.html; graph: {gn} nodes, {ge} links, {gc} commits -> {out}/graph.html")


if __name__ == "__main__":
    main()
