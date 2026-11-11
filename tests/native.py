#!/usr/bin/env python3
"""Cross-platform test (Linux, macOS, Windows) that needs no bash: copies ONLY the skill folder to a temporary place, then
bootstraps a notes tree from that copy and exercises the real launchers (the .cmd files on Windows). Exit 0 = all passed."""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True   # the test imports _myco from the project under test; that must not leave a __pycache__ there

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "myco-notes")
WIN = os.name == "nt"
MY = "myco-notes"
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


def run(cmd, cwd, stdin=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", input=stdin)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git(cwd, *a):
    return run(["git", *a], cwd)


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8", newline="") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def pycache_dirs(root):
    return [dp for dp, dn, _fn in os.walk(root) if "__pycache__" in dn and ".git" not in dp.split(os.sep)]


def _data_dirs(conf_text):
    """The names listed in DATA_DIRS of a conf file's text."""
    for line in conf_text.splitlines():
        if line.startswith("DATA_DIRS="):
            return line.split("=", 1)[1].strip().strip('"').split()
    return []


def main():
    tmp = tempfile.mkdtemp(prefix="myco-native-")
    try:
        kit = os.path.join(tmp, "skill-only")
        shutil.copytree(SKILL, kit, ignore=shutil.ignore_patterns("__pycache__"))

        def L(root, name, tools="tools"):  # the launcher a user would type
            p = os.path.join(root, *tools.split("/"), name)
            return [p + ".cmd"] if WIN else [p]

        T = MY + "/tools"
        proj = os.path.join(tmp, "proj")
        print("bootstrap (from the copied skill folder only; default single-folder layout)")
        rc, out = run(L(kit, "bootstrap") + [proj, "--name", "Demo", "--owner", "Tester", "--tz", "UTC", "--data-dir", "files-input", "--data-dir", "files-output"], tmp)
        check("bootstrap runs", rc == 0, out)
        check("baseline commit exists", "Baseline" in git(proj, "log", "--oneline")[1])
        check("placeholders filled", all("{{" not in read(os.path.join(proj, f)) for f in ("AGENTS.md", ".myco-notes.conf", ".gitignore", ".github/CODEOWNERS", ".github/pull_request_template.md"))
              and "{{TOOLS_DIR}}" not in read(os.path.join(proj, ".github", "workflows", "notes-check.yml")))
        check("hooks path is versioned", git(proj, "config", "core.hooksPath")[1].strip() == T + "/hooks")
        check("bootstrap launcher not copied", not os.path.exists(os.path.join(proj, MY, "tools", "bootstrap.py")))
        check("team files present", all(os.path.exists(os.path.join(proj, p)) for p in (".github/workflows/notes-check.yml", MY + "/docs/TEAM.md", ".gitattributes")))
        check("one folder holds notes, tools and docs", all(os.path.isdir(os.path.join(proj, MY, d)) for d in ("plans", "tools", "docs")) and not os.path.exists(os.path.join(proj, "notes")) and not os.path.exists(os.path.join(proj, "tools")))
        check("root keeps only entry files, the folder and project data", sorted(x for x in os.listdir(proj) if x != ".git") == sorted([".gitattributes", ".github", ".gitignore", ".myco-notes.conf", "AGENTS.md", "CLAUDE.md", MY, "files-input", "files-output"]))
        check("conf records the layout", all(f"{k}=" in read(os.path.join(proj, ".myco-notes.conf")) for k in ("MYCO_DIR", "NOTES_DIR", "TOOLS_DIR", "DOCS_DIR", "MAP_DIR")) and "MYCO_DIR=myco-notes" in read(os.path.join(proj, ".myco-notes.conf")))
        check("AGENTS.md names the new paths", MY + "/working-agreement.md" in read(os.path.join(proj, "AGENTS.md")) and T + "/notes-commit" in read(os.path.join(proj, "AGENTS.md")))
        check("data folders are gitignored", git(proj, "check-ignore", "-q", "files-input")[0] == 0 and git(proj, "check-ignore", "-q", "files-output")[0] == 0)

        NC = L(proj, "notes-commit", T)
        print("notes-commit")
        write(os.path.join(proj, MY, "state.md"), "\n- native test change\n", "a")
        rc, out = run(L(proj, "notes-commit", T) + ["Record the native test change and why"], proj)
        check("commit with message", rc == 0 and "Record the native test change" in out, out)
        rc, out = run(L(proj, "notes-commit", T) + ["again"], proj)
        check("clean tree says nothing to commit", "nothing to commit" in out, out)
        bad = os.path.join(proj, MY, "scripts", "broken.py")
        write(bad, "def (:\n")
        rc, out = run(L(proj, "notes-commit", T) + ["broken script"], proj)
        check("syntax error blocks the commit", rc != 0, out)
        os.remove(bad)
        git(proj, "reset", "-q")

        print("pre-commit hook (run by git through its own sh)")
        leak = os.path.join(proj, MY, "secret-test.md")
        write(leak, "api_key = AbCdEfGhIjKlMnOpQrStUvWx12\n")
        rc, out = run(L(proj, "notes-commit", T) + ["add a secret"], proj)
        check("secret is refused", rc != 0 and "possible secret" in out, out)
        os.remove(leak)
        git(proj, "reset", "-q")
        key = os.path.join(proj, MY, "key-test.md")
        write(key, "-----BEGIN RSA " + "PRIVATE KEY-----\nabc\n")   # built at run time, so this file holds no key-shaped text
        rc, out = run(L(proj, "notes-commit", T) + ["add a key"], proj)
        check("private key block is refused", rc != 0, out)
        os.remove(key)
        git(proj, "reset", "-q")
        check("tree is clean again", git(proj, "status", "--porcelain")[1].strip() == "")

        print("lint and map")
        lint = [sys.executable, os.path.join(proj, MY, "tools", "notes-lint.py")]
        rc, out = run(lint, proj)
        check("lint runs", rc in (0, 1) and "notes-lint:" in out, out)
        rc, out = run([sys.executable, os.path.join(proj, MY, "tools", "build-notes-map.py")], proj)
        check("map builds inside the one folder", rc == 0 and os.path.exists(os.path.join(proj, MY, "map", "index.html")), out)
        sys.path.insert(0, os.path.join(proj, MY, "tools"))
        import _myco as _m
        check("STATE_FILE defaults to state.md", _m.layout(proj)["state"] == "state.md")
        check("STATE_FILE can name the master record", _m.layout(proj, {"MYCO_DIR": "myco-notes", "STATE_FILE": "homelab.md"})["state"] == "homelab.md")
        sys.path.pop(0)
        check("map is gitignored", git(proj, "check-ignore", "-q", MY + "/map")[0] == 0)
        check("map is not read as notes by the lint", "map/" not in run(lint, proj)[1])

        print("mycelium view (graph.html)")
        import json, re as _re
        def graph_data(root_dir, map_dir):
            h = read(os.path.join(root_dir, *map_dir.split("/"), "graph.html"))
            return h, json.loads(_re.search(r'<script id="data" type="application/json">(.*?)</script>', h, _re.S).group(1).replace("<\\/", "</"))
        write(os.path.join(proj, MY, "plans", "graph-test.md"), "# Graph Test Note\nSee `state.md`. The unique phrase is zebra-unique-phrase-8812 and `no-such-note.md` is missing.\n")
        write(os.path.join(proj, MY, "plans", "graph-hub.md"), "# Hub\nThe centre of the test.\n")
        for x in ("a", "b", "c"):
            write(os.path.join(proj, MY, "plans", f"graph-{x}.md"), f"# Spoke {x}\nSee `graph-hub.md`.\n")
        rc, out = run(NC + ["Add a note for the graph test"], proj)
        git(proj, "mv", MY + "/plans/graph-test.md", MY + "/plans/graph-renamed.md")
        write(os.path.join(proj, MY, "plans", "graph-renamed.md"), "\nMore text.\n", "a")
        rc, out = run(NC + ["Rename and touch the graph test note"], proj)
        rc, out = run([sys.executable, os.path.join(proj, MY, "tools", "build-notes-map.py")], proj)
        check("the map build also writes graph.html", rc == 0 and "graph:" in out and os.path.exists(os.path.join(proj, MY, "map", "graph.html")), out)
        h, g = graph_data(proj, MY + "/map")
        nodes = {n["rel"]: n for n in g["nodes"]}
        gn = nodes.get(MY + "/plans/graph-renamed.md")
        check("every note is a node, with title and path only", gn is not None and gn["title"] == "Graph Test Note" and len(g["nodes"]) >= 8, str(sorted(nodes)))
        check("the text of a note is not written into the page", "zebra-unique-phrase-8812" not in h and "More text" not in h)
        check("a mention becomes a link", any({g["nodes"][e[0]]["rel"], g["nodes"][e[1]]["rel"]} == {MY + "/plans/graph-renamed.md", MY + "/state.md"} for e in g["edges"]), str(g["edges"][:5]))
        def weight(src, dst):   # an edge is [a, b, weight a->b, weight b->a]
            for e in g["edges"]:
                ra, rb = g["nodes"][e[0]]["rel"], g["nodes"][e[1]]["rel"]
                if (ra, rb) == (src, dst):
                    return e[2]
                if (rb, ra) == (src, dst):
                    return e[3]
            return None
        check("a link keeps its direction (who mentions whom)", (weight(MY + "/plans/graph-renamed.md", MY + "/state.md") or 0) > 0 and weight(MY + "/state.md", MY + "/plans/graph-renamed.md") == 0 and (weight(MY + "/plans/graph-a.md", MY + "/plans/graph-hub.md") or 0) > 0,
              str(g["edges"][:8]))
        check("the threads are drawn with a direction", "e.dir" in h and "Mentioned by" in h)
        check("on a phone the detail panel opens as a strip with More", "panelFull" in h and '#panel.min' in h and '"More"' in h)
        check("labels take turns (rotation, fades, neighbourhood of a selection)", "updateLabels" in h and "slotCount" in h and "LDWELL" in h and "n.hub||n.i===hov" not in h)
        check("the search box folds and the panel shrinks on a larger screen too, remembered", 'id="fold"' in h and "#head.fold" in h and "togglePanel" in h and "myco-graph-" in h)
        check("depth: recent notes in front, a Depth button for the flat view, picking on projected places", 'id="depth"' in h and "depthTargets" in h and "function proj(" in h and "n.px-px" in h and 'pref("depth"' in h and "turnTo(pinch.ry" in h and "ev.deltaX" in h and "turnHome()" in h and "n.fz=" in h and "Math.max(-.8" not in h)
        check("two fingers pinch to zoom, and a bud has its source's colour", "pinch" in h and "pointercancel" in h and "budRGB(e.dir>0?e.a:e.b)" in h)
        check("a missing reference is shown", gn is not None and gn.get("miss") == ["no-such-note.md"], str(gn))
        check("the history is replayed across a rename", gn is not None and gn["b"] < gn["l"] and len(g["commits"]) >= 3 and g["commits"][gn["b"]]["s"].startswith("Add a note for the graph test"), str((gn, [c["s"] for c in g["commits"]])))
        hubs = {n["rel"] for n in g["nodes"] if n["hub"]}
        live = sorted((n for n in g["nodes"] if not n["hist"] and n["in"] >= 2 and g["groups"][n["g"]]["id"] not in ("start", "docs")), key=lambda n: (-n["in"], -n["kb"], n["rel"]))
        check("hubs are the most-mentioned project notes", MY + "/plans/graph-hub.md" in hubs and hubs == {n["rel"] for n in live[:min(6, max(2, len(g["nodes"]) // 8))]} and not any(n["in"] < 2 for n in g["nodes"] if n["hub"]), str(sorted(hubs)))
        check("the entry and method notes are never hubs, however often they are mentioned", not any(n["hub"] and g["groups"][n["g"]]["id"] in ("start", "docs") for n in g["nodes"]) and any(n["in"] >= 2 and g["groups"][n["g"]]["id"] == "start" for n in g["nodes"]), str([(n["rel"], n["in"]) for n in g["nodes"] if n["in"] >= 2]))
        check("the timeline sits in the left column under the search panel, no mushrooms drawn", h.index('id="left"') < h.index('id="head"') < h.index('id="time"') < h.index('id="panel"') and "mushroom" not in h.lower())
        check("the page needs no network", not _re.search(r'(src|href)="https?:', h) and h.count("</script>") == 2 and "%%" not in h)
        node = shutil.which("node")
        if node:
            code = _re.search(r"<script>\n\(function.*?</script>", h, _re.S).group(0)[len("<script>\n"):-len("</script>")]
            write(os.path.join(tmp, "graph-check.js"), code)
            check("the script is valid JavaScript", run([node, "--check", os.path.join(tmp, "graph-check.js")], tmp)[0] == 0)
        git(proj, "rm", "-q", MY + "/plans/graph-renamed.md", *[MY + f"/plans/graph-{x}.md" for x in ("hub", "a", "b", "c")])
        run(NC + ["Remove the graph test note"], proj)
        shutil.rmtree(os.path.join(proj, MY, "map"), ignore_errors=True)
        check("the map folder is still gitignored and the tree clean", git(proj, "status", "--porcelain")[1].strip() == "", git(proj, "status", "--porcelain")[1])

        print("freshness header, resume, asof")
        import datetime as _dt
        today = _dt.date.today().isoformat()
        git(proj, "tag", "before-fresh")
        write(os.path.join(proj, MY, "plans", "fresh-old.md"), "---\nlast_confirmed: 2020-01-05\nreview_after: 2020-03-01   # re-check\nsupersedes: fresh-new.md, no-such-note.md\n---\n# Fresh old\nBody `state.md`.\n")
        write(os.path.join(proj, MY, "plans", "fresh-new.md"), "---\nlast_confirmed: 2099-01-01\nvalid_from: 2030-01-01\nvalid_until: 2020-02-01\n---\n# Fresh new\n")
        write(os.path.join(proj, MY, "plans", "fresh-bad.md"), "---\nlast_confirmed: 01/02/2020\n---\n# Fresh bad\n")
        write(os.path.join(proj, MY, "plans", "fresh-stale.md"), "---\nlast_confirmed: 2020-01-01\n---\n# Fresh stale\n")
        write(os.path.join(proj, MY, "plans", "fresh-ok.md"), f"---\nlast_confirmed: {today}\nreview_after: 2099-01-01\n---\n# Fresh ok\n")
        write(os.path.join(proj, MY, "plans", "session-2026-01-01-test.md"), "# Session test\nMerge status: pending, nothing merged yet\n")
        tr = os.path.join(proj, MY, "sync-tracker.md")
        write(tr, read(tr).replace("1. _(item; owner; waiting on)_", "1. Renew the demo certificate; owner: Tester; waiting on the vendor"))
        stf = os.path.join(proj, MY, "state.md")
        write(stf, read(stf).replace("- _(five to ten lines", "- Demo system runs on one host\n- _(five to ten lines", 1))
        rc, out = run(lint, proj)
        check("lint: a passed review_after is reported", "fresh-old.md:3 review date 2020-03-01 has passed" in out, out)
        check("lint: a header supersedes target that does not exist is reported, an existing one is not", "points to a missing note `no-such-note.md`" in out and "`fresh-new.md`" not in out, out)
        check("lint: future last_confirmed, reversed validity and a passed valid_until are reported", "last_confirmed 2099-01-01 is in the future" in out and "valid_from 2030-01-01 is after valid_until 2020-02-01" in out and "valid_until 2020-02-01 has passed" in out, out)
        check("lint: a malformed date is reported", "fresh-bad.md:2 header last_confirmed '01/02/2020' is not a date" in out, out)
        check("lint: an old last_confirmed without review_after is stale", "fresh-stale.md:2 last confirmed 2020-01-01" in out, out)
        check("lint: a current header raises nothing", not any("fresh-ok.md" in l and l.startswith(("WARN", "ERROR")) for l in out.splitlines()), out)
        rc, out = run(NC + ["Add freshness test notes and a handoff"], proj)
        check("the notes with headers commit", rc == 0, out)
        rc, out = run(L(proj, "resume", T), proj)
        check("resume: project, pending item, headline fact and the handoff", rc == 0 and "# Demo: resume," in out and "Renew the demo certificate" in out and "Demo system runs on one host" in out and "session-2026-01-01-test.md" in out and "Merge status: pending" in out, out)
        check("resume: notes past a review date are listed, current ones are not", "fresh-old.md`: review after 2020-03-01" in out and "fresh-ok.md" not in out, out)
        check("resume: the footer reports the budget and nothing left out", "budget 6000 characters; left out: 0 item(s)" in out, out)
        rc, out = run(L(proj, "resume", T) + ["--budget", "600"], proj)
        check("resume: a small budget is kept and the footer says what was left out", rc == 0 and len(out) <= 600 and "left out: 0" not in out and "## Repository" in out, f"{len(out)} chars\n{out}")
        rc, out = run(L(proj, "asof", T) + ["before-fresh", "state.md"], proj)
        check("asof: a note as it was at a tag", rc == 0 and "# Demo: master record" in out and "Demo system runs on one host" not in out, out)
        rc, out = run(L(proj, "asof", T) + ["HEAD", "plans/fresh-old.md"], proj)
        check("asof: a path inside the notes folder resolves", rc == 0 and "# Fresh old" in out, out)
        rc, out = run(L(proj, "asof", T) + ["before-fresh", "fresh-old.md"], proj)
        check("asof: a note that did not exist yet is reported", rc == 1 and "did not exist then" in out, out)
        rc, out = run(L(proj, "asof", T) + ["before-fresh", "--grep", "demo system"], proj)
        check("asof: --grep finds nothing before the change", rc == 1, out)
        rc, out = run(L(proj, "asof", T) + ["HEAD", "--grep", "demo system"], proj)
        check("asof: --grep finds it after the change, with file and line", rc == 0 and MY + "/state.md:" in out and "Demo system runs on one host" in out, out)
        rc, out = run(L(proj, "asof", T) + ["before-fresh", "--since"], proj)
        check("asof: --since lists what was added and changed", rc == 0 and "A  " + MY + "/plans/fresh-old.md" in out and "M  " + MY + "/state.md" in out and "Add freshness test notes" in out, out)
        rc, out = run(L(proj, "asof", T) + [today], proj)
        check("asof: a date gives the commit and the notes that existed", rc == 0 and "notes existed then" in out and MY + "/state.md" in out, out)
        rc, out = run(L(proj, "asof", T) + ["2001-01-01"], proj)
        check("asof: a date before the history says so", rc == 1 and "nothing was committed" in out, out)
        rc, out = run(L(proj, "asof", T) + ["--history", "fresh-old.md"], proj)
        check("asof: --history lists the commits of a note", rc == 0 and "Add freshness test notes" in out, out)
        rc, out = run([sys.executable, os.path.join(proj, MY, "tools", "build-notes-map.py")], proj)
        h, g = graph_data(proj, MY + "/map")
        fo = {n["rel"]: n for n in g["nodes"]}.get(MY + "/plans/fresh-old.md")
        fk = {n["rel"]: n for n in g["nodes"]}.get(MY + "/plans/fresh-ok.md")
        check("graph: a note past its review date wilts, a current one does not", fo is not None and fo.get("due", 0) >= 1 and fk is not None and fk.get("due", 0) == 0, str((fo, fk)))
        page = read(os.path.join(proj, MY, "map", "p", fo["id"] + ".html")) if fo else ""
        check("map page: the header is shown as a freshness line, not as text", "review after 2020-03-01" in page and "last_confirmed" not in page and "<h2" not in page.split("Fresh old")[0], page[:400])
        git(proj, "reset", "-q", "--hard", "before-fresh")
        git(proj, "tag", "-d", "before-fresh")
        shutil.rmtree(os.path.join(proj, MY, "map"), ignore_errors=True)
        check("the tree is clean again", git(proj, "status", "--porcelain")[1].strip() == "", git(proj, "status", "--porcelain")[1])

        print("lint: data folders, history folders, size")
        write(os.path.join(proj, "files-input", "case.md"), "See `missing-case.md`. Follow-up after 2020-01-01.\napi_key = AbCdEfGhIjKlMnOpQrStUvWx12\n")
        write(os.path.join(proj, "files-input", "export.csv"), "a,b\n")
        write(os.path.join(proj, MY, "plans", "backlog.md"), "\nInput is `files-input/export.csv`.\n", "a")
        rc, out = run(lint, proj)
        check("data folders are not read as notes", "case.md" not in out and rc in (0, 1), out)
        check("a note may reference a file in a data folder", "export.csv" not in out, out)
        write(os.path.join(proj, MY, "archive", "old.md"), "# Old\nSee `gone-note.md`. Waiting, review-by 2020-01-01.\n")
        write(os.path.join(proj, MY, "logs", "effort.md"), "# Effort\nSee `gone-note.md`. Waiting, review-by 2020-01-01.\n")
        write(os.path.join(proj, MY, "live.md"), "# Live\nSee `gone-note.md`. Waiting, review-by 2020-01-01.\n")
        rc, out = run(lint, proj)
        check("archive and logs are not checked for references or dates", "archive/old.md" not in out and "logs/effort.md" not in out, out)
        check("the same text in a live note is flagged", "live.md:2 reference to missing note" in out and "live.md:2 follow-up date" in out, out)
        write(os.path.join(proj, MY, "archive", "leak.md"), "token = ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n")
        rc, out = run(lint, proj)
        check("secrets are still found in the archive", rc == 2 and "archive/leak.md" in out, out)
        os.remove(os.path.join(proj, MY, "archive", "leak.md"))
        write(os.path.join(proj, MY, "big.md"), "# Big\n" + ("line of text that makes a note large\n" * 4000))
        rc, out = run(lint, proj)
        check("a note over the size limit is flagged", "big.md:1" in out and "is large" in out, out)
        write(os.path.join(proj, "AGENTS.md"), "\n" + ("x" * 79 + "\n") * 330, "a")
        rc, out = run(lint, proj)
        check("AGENTS.md near the 32 KiB limit warns", "AGENTS.md:1" in out and "close to the 32 KiB" in out, out)
        write(os.path.join(proj, "AGENTS.md"), ("x" * 79 + "\n") * 120, "a")
        rc, out = run(lint, proj)
        check("AGENTS.md over 32 KiB warns that it is cut off", "over the 32 KiB" in out, out)
        for f in ("archive/old.md", "logs/effort.md", "live.md", "big.md"):
            os.remove(os.path.join(proj, MY, *f.split("/")))
        git(proj, "checkout", "-q", "--", "AGENTS.md", MY + "/plans/backlog.md")
        shutil.rmtree(os.path.join(proj, "files-input"))
        os.makedirs(os.path.join(proj, "files-input"))
        check("tree is clean after the lint scenarios", git(proj, "status", "--porcelain")[1].strip() == "")
        check("no __pycache__ was left by the tools or the launchers", not pycache_dirs(proj), str(pycache_dirs(proj)))

        print("new folders and loose files in the root (NEW_FOLDERS)")
        NC = L(proj, "notes-commit", T)
        conf_p = os.path.join(proj, ".myco-notes.conf")
        head0 = git(proj, "rev-parse", "HEAD")[1].strip()
        check("bootstrap writes NEW_FOLDERS=ask by default", "\nNEW_FOLDERS=ask\n" in read(conf_p))
        write(os.path.join(proj, "runbooks", "a.md"), "# Runbook\n")
        write(os.path.join(proj, "exports", "data.csv"), "a,b\n")
        write(os.path.join(proj, "loose-export.xlsx"), "x")
        write(os.path.join(proj, MY, "state.md"), "\n- a change next to new folders\n", "a")
        rc, out = run(NC + ["Change next to new folders"], proj)
        check("ask: stops with exit 3 and a report", rc == 3 and "runbooks/" in out and "exports/" in out and "loose-export.xlsx" in out and "ignoreall" in out and "suggestion:" in out, out)
        check("ask: nothing was committed or staged", git(proj, "rev-parse", "HEAD")[1].strip() == head0 and git(proj, "diff", "--cached", "--quiet")[0] == 0)
        check("ask: files already covered (data folders, the notes folder) are not listed", "files-input" not in out and MY + "/" not in out.split("Choices:")[0])
        rc, out = run(NC + ["--folder", "nosuch=add", "x"], proj)
        check("a name that is not new is refused", rc == 2 and "nosuch" in out, out)
        rc, out = run(NC + ["--folder", "runbooks=maybe", "x"], proj)
        check("a bad choice is refused", rc == 2 and "must be one of" in out, out)
        rc, out = run(NC + ["--folder", "runbooks=add", "x"], proj)
        check("a partial answer still stops", rc == 3 and "exports/" in out and "runbooks/" not in out.split("Choices:")[0], out)
        write(os.path.join(proj, "loose-note.md"), "# Loose\nSee `gone-note.md`.\n")
        rc, out = run(NC + ["--folder", "runbooks=add", "--folder", "exports=ignoreall", "--folder", "loose-export.xlsx=ignorelint", "--folder", "loose-note.md=ignorelint", "Decide the new items"], proj)
        tracked = git(proj, "ls-files")[1].split("\n")
        check("answers are applied and committed", rc == 0 and "Decide the new items" in out, out)
        check("add: tracked", "runbooks/a.md" in tracked)
        check("ignoreall: not tracked, in DATA_DIRS and .gitignore", not any(t.startswith("exports/") for t in tracked) and "exports" in _data_dirs(read(conf_p)) and git(proj, "check-ignore", "-q", "exports")[0] == 0)
        check("ignorelint on a loose file: tracked", "loose-export.xlsx" in tracked and "loose-note.md" in tracked)
        check("the change was committed together with the decision", MY + "/state.md" in git(proj, "show", "--stat", "--format=", "HEAD")[1].replace("\\", "/"))
        out = run(lint, proj)[1]
        check("ignorelint on a loose Markdown file: the lint skips it", "loose-note.md" not in out, out)
        check("add: the lint reads the new notes folder", "runbooks/a.md" in out or "notes-lint:" in out)
        write(os.path.join(proj, "later-dir", "x.md"), "# Later\nSee `gone-note.md`.\n")
        rc, out = run(NC + ["--folder", "later-dir=later", "Later test"], proj)
        check("later: nothing to commit, folder untracked, conf untouched", rc == 0 and "asked again" in out and not any(t.startswith("later-dir/") for t in git(proj, "ls-files")[1].split("\n")) and "later-dir" not in read(conf_p), out)
        rc, out = run(NC + ["Later test again"], proj)
        check("later: asked again next time", rc == 3 and "later-dir/" in out, out)
        rc, out = run(NC + ["--folder", "*=ignorelint", "Wildcard answer"], proj)
        check("NAME=* answers for everything and lint skips the folder", rc == 0 and "later-dir/x.md" in git(proj, "ls-files")[1] and "later-dir" in _data_dirs(read(conf_p)) and "later-dir" not in run(lint, proj)[1], out)
        c0 = read(conf_p)
        for mode in ("add", "ignorelint", "ignoreall"):
            write(conf_p, c0.replace("NEW_FOLDERS=ask", "NEW_FOLDERS=" + mode))
            write(os.path.join(proj, "auto-" + mode, "f.md"), "# f\n")
            rc, out = run(NC + [f"Automatic {mode}"], proj)
            t = git(proj, "ls-files", "auto-" + mode)[1].strip()
            data = "auto-" + mode in _data_dirs(read(conf_p))
            ig = git(proj, "check-ignore", "-q", "auto-" + mode)[0] == 0
            want = {"add": (True, False, False), "ignorelint": (True, True, False), "ignoreall": (False, True, True)}[mode]
            check(f"NEW_FOLDERS={mode}: no question, tracked/data/ignored = {want}", rc == 0 and "exit 3" not in out and (bool(t), data, ig) == want, out)
            write(conf_p, c0)
            git(proj, "commit", "-qam", "restore conf") if git(proj, "status", "--porcelain", ".myco-notes.conf")[1].strip() else None
        write(conf_p, c0.replace("NEW_FOLDERS=ask", "NEW_FOLDERS=sometimes"))
        write(os.path.join(proj, "bad-mode", "f.md"), "# f\n")
        rc, out = run(NC + ["Bad mode"], proj)
        check("an unknown NEW_FOLDERS value is refused", rc == 2 and "NEW_FOLDERS" in out, out)
        write(conf_p, c0)
        shutil.rmtree(os.path.join(proj, "bad-mode"))
        git(proj, "add", "-A")
        git(proj, "commit", "-qm", "settle the new-folder test")
        check("tree is clean after the new-folder scenarios", git(proj, "status", "--porcelain")[1].strip() == "", git(proj, "status", "--porcelain")[1])
        for d in ("runbooks", "exports", "later-dir", "auto-add", "auto-ignorelint", "auto-ignoreall"):
            shutil.rmtree(os.path.join(proj, d), ignore_errors=True)
        for f in ("loose-export.xlsx", "loose-note.md"):
            if os.path.exists(os.path.join(proj, f)):
                git(proj, "rm", "-q", "-f", f)
        for d in ("runbooks", "later-dir", "auto-add", "auto-ignorelint"):
            git(proj, "rm", "-r", "-q", "-f", "--ignore-unmatch", d)
        git(proj, "commit", "-qm", "remove the new-folder test items")
        write(conf_p, "\n".join(l for l in read(conf_p).split("\n") if not l.startswith("DATA_DIRS=")) + '\nDATA_DIRS="files-input files-output"\n')
        git(proj, "commit", "-qam", "reset data folders") if git(proj, "status", "--porcelain")[1].strip() else None

        print("mirror and restore drill")
        mirror = os.path.join(tmp, "mirror")
        conf = os.path.join(proj, ".myco-notes.conf")
        text = read(conf)
        text = "".join(f'MIRROR_TARGET="{mirror}"\n' if l.startswith("MIRROR_TARGET=") else l for l in text.splitlines(True))
        write(conf, text)
        run(L(proj, "notes-commit", T) + ["Configure mirror"], proj)
        rc, out = run(L(proj, "mirror-push", T), proj)
        check("mirror push to a local directory", rc == 0 and "mirror: synced" in out and os.path.isdir(os.path.join(mirror, ".git")), out)
        outside = os.path.join(tmp, "outside")
        os.makedirs(outside)
        write(os.path.join(outside, "keep.txt"), "sentinel\n")
        plans = os.path.join(mirror, MY, "plans")
        shutil.rmtree(plans)
        if WIN:   # a junction needs no special rights on Windows; the reviewer's case
            made = subprocess.run(["cmd", "/c", "mklink", "/J", plans, outside], capture_output=True).returncode == 0
        else:
            os.symlink(outside, plans)
            made = True
        rc, out = run(L(proj, "mirror-push", T) + ["--strict"], proj)
        check("a link or junction inside the mirror is replaced, never followed",
              made and rc == 0 and os.listdir(outside) == ["keep.txt"] and read(os.path.join(outside, "keep.txt")) == "sentinel\n"
              and os.path.isdir(plans) and not os.path.islink(plans), out)
        rc, out = run(L(proj, "restore-drill", T) + [mirror], proj)
        check("restore drill passes", rc == 0 and "fsck: OK" in out and "tracker present" in out, out)
        arch = os.path.join(tmp, "backup.zip")
        with zipfile.ZipFile(arch, "w") as z:
            for dp, _dn, fn in os.walk(mirror):
                for f in fn:
                    full = os.path.join(dp, f)
                    z.write(full, os.path.relpath(full, mirror))
        rc, out = run(L(proj, "restore-drill", T) + [arch], proj)
        check("restore drill from a zip archive", rc == 0 and "fsck: OK" in out, out)
        bare = os.path.join(tmp, "mirror.git")
        git(tmp, "init", "-q", "--bare", bare)
        text = "".join(f'MIRROR_TARGET="git:{bare}"\n' if l.startswith("MIRROR_TARGET=") else l for l in text.splitlines(True))
        write(conf, text)
        git(proj, "commit", "-qam", "git mirror target")
        rc, out = run(L(proj, "mirror-push", T), proj)
        check("mirror push to a git remote (git:URL)", rc == 0 and "main" in git(bare, "branch", "--list")[1], out)

        print("team setup")
        clone = os.path.join(tmp, "clone")
        git(tmp, "clone", "-q", proj, clone)
        check("hooks path is not cloned", git(clone, "config", "core.hooksPath")[1].strip() == "")
        rc, out = run(L(clone, "setup-clone", T), clone)
        check("setup-clone activates the hook in a fresh clone", rc == 0 and git(clone, "config", "core.hooksPath")[1].strip() == T + "/hooks", out)
        base = git(proj, "rev-parse", "HEAD")[1].strip()
        write(os.path.join(proj, MY, "plans", "backlog.md"), "- team test line\n", "a")
        rc, out = run(L(proj, "notes-commit", T) + ["--branch", "feat-a", "Team test change and why"], proj)
        check("notes-commit --branch creates the branch", rc == 0 and git(proj, "symbolic-ref", "--short", "HEAD")[1].strip() == "feat-a", out)
        rc, out = run(L(proj, "ci-check", T) + [base], proj)
        check("ci-check passes on a clean change", rc == 0 and "ci-check: passed" in out, out)
        write(os.path.join(proj, MY, "leak2.md"), "api_key = AbCdEfGhIjKlMnOpQrStUvWx12\n")
        git(proj, "switch", "-q", "-c", "feat-leak")
        git(proj, "add", "-A")
        git(proj, "commit", "-q", "--no-verify", "-m", "bypass the hook")
        rc, out = run(L(proj, "ci-check", T) + [base], proj)
        check("ci-check catches a secret committed with --no-verify", rc != 0 and "FAIL" in out, out)
        git(proj, "switch", "-q", "main")
        remote = os.path.join(tmp, "remote.git")
        git(tmp, "init", "-q", "--bare", remote)
        git(proj, "remote", "add", "origin", remote)
        write(os.path.join(proj, MY, "plans", "backlog.md"), "- push test line\n", "a")
        rc, out = run(L(proj, "notes-commit", T) + ["--branch", "feat-b", "--push", "Push test and why"], proj)
        check("notes-commit --push publishes the branch", "feat-b" in git(tmp, "ls-remote", "--heads", remote)[1], out)

        print("direct python call")
        rc, out = run([sys.executable, os.path.join(proj, MY, "tools", "notes_commit.py"), "--help"], proj)
        check("python <tools>/notes_commit.py --help", rc == 0 and "--branch" in out, out)

        print("flat layout still works (older trees, --layout flat)")
        flat = os.path.join(tmp, "flat")
        rc, out = run(L(kit, "bootstrap") + [flat, "--name", "Old", "--tz", "UTC", "--layout", "flat", "--new-folders", "add"], tmp)
        check("flat bootstrap runs", rc == 0 and all(os.path.isdir(os.path.join(flat, d)) for d in ("notes", "tools", "docs")), out)
        check("flat hooks path is tools/hooks", git(flat, "config", "core.hooksPath")[1].strip() == "tools/hooks")
        write(os.path.join(flat, "notes", "state.md"), "\n- flat change\n", "a")
        rc, out = run(L(flat, "notes-commit") + ["Flat layout change and why"], flat)
        check("flat notes-commit works", rc == 0 and "Flat layout change" in out, out)
        check("bootstrap --new-folders writes the conf", "\nNEW_FOLDERS=add\n" in read(os.path.join(flat, ".myco-notes.conf")))
        write(os.path.join(flat, "reference", "list.txt"), "x\n")
        check("flat: NEW_FOLDERS=add commits a new root folder without asking", run(L(flat, "notes-commit") + ["Add a reference folder"], flat)[0] == 0 and "reference/list.txt" in git(flat, "ls-files")[1].replace("\\", "/"))
        rc, out = run([sys.executable, os.path.join(flat, "tools", "build-notes-map.py")], flat)
        check("flat map goes to notes-map", rc == 0 and os.path.exists(os.path.join(flat, "notes-map", "index.html")), out)
        shutil.rmtree(os.path.join(flat, "notes-map"))
        check("flat tree: no __pycache__", not pycache_dirs(flat), str(pycache_dirs(flat)))

        print("relocate: flat tree -> single folder (run from the kit, as an agent or user would)")
        write(os.path.join(flat, "notes", "state.md"), "\nSee `notes/plans/backlog.md` and `tools/notes-lint.py`. Release notes/changes stay.\n", "a")
        git(flat, "commit", "-qam", "reference paths")
        rc, out = run(L(kit, "relocate") + ["--root", flat], tmp)
        check("dry run changes nothing", rc == 0 and "dry run" in out and git(flat, "status", "--porcelain")[1].strip() == "" and os.path.isdir(os.path.join(flat, "notes")), out)
        write(os.path.join(flat, "dirty.md"), "x\n")
        git(flat, "add", "dirty.md")
        rc, out = run(L(kit, "relocate") + ["--root", flat, "--apply"], tmp)
        check("apply refuses a tree with uncommitted changes", rc != 0 and "uncommitted" in out and os.path.isdir(os.path.join(flat, "notes")), out)
        git(flat, "commit", "-qm", "dirty")
        rc, out = run(L(kit, "relocate") + ["--root", flat, "--apply"], tmp)
        check("apply moves the folders", rc == 0 and not os.path.exists(os.path.join(flat, "notes")) and not os.path.exists(os.path.join(flat, "tools")) and not os.path.exists(os.path.join(flat, "docs")) and os.path.isfile(os.path.join(flat, MY, "state.md")) and os.path.isfile(os.path.join(flat, MY, "tools", "notes_commit.py")), out)
        c = read(os.path.join(flat, ".myco-notes.conf"))
        check("conf and hooks path follow", "MYCO_DIR=myco-notes" in c and "TOOLS_DIR=myco-notes/tools" in c and git(flat, "config", "core.hooksPath")[1].strip() == T + "/hooks", c)
        st = read(os.path.join(flat, MY, "state.md"))
        check("path references are rewritten, prose is left alone", "`myco-notes/plans/backlog.md`" in st and "`myco-notes/tools/notes-lint.py`" in st and "Release notes/changes stay" in st, st[-300:])
        check("workflow and .gitignore follow", T + "/ci-check" in read(os.path.join(flat, ".github", "workflows", "notes-check.yml")) and MY + "/map/" in read(os.path.join(flat, ".gitignore")))
        write(os.path.join(flat, MY, "state.md"), "\n- after relocate\n", "a")
        rc, out = run(L(flat, "notes-commit", T) + ["Moved to the single folder layout"], flat)
        check("the moved tree commits with its own tools", rc == 0 and "Moved to the single folder layout" in out, out)
        rc, out = run([sys.executable, os.path.join(flat, MY, "tools", "notes-lint.py"), "--quiet"], flat)
        check("lint is clean after the move", rc == 0 and "0 warnings" in out, out)
        rc, out = run(L(kit, "relocate") + ["--root", flat, "--apply"], tmp)
        check("a second run says there is nothing to do", rc == 0 and "already uses" in out, out)

        print("relocate: rename the folder, and a tree with custom folder names")
        rc, out = run(L(kit, "relocate") + ["--root", flat, "--myco-dir", "project-notes", "--apply"], tmp)
        check("rename moves the whole folder", rc == 0 and os.path.isfile(os.path.join(flat, "project-notes", "state.md")) and not os.path.exists(os.path.join(flat, MY)), out)
        check("rename updates conf, hooks path and references", "MYCO_DIR=project-notes" in read(os.path.join(flat, ".myco-notes.conf")) and git(flat, "config", "core.hooksPath")[1].strip() == "project-notes/tools/hooks" and "project-notes/tools/ci-check" in read(os.path.join(flat, ".github", "workflows", "notes-check.yml")))
        custom = os.path.join(tmp, "custom")
        run(L(kit, "bootstrap") + [custom, "--name", "Custom", "--tz", "UTC", "--layout", "flat"], tmp)
        git(custom, "mv", "docs", "myco-docs")
        write(os.path.join(custom, "notes", "knowledge-base", "kb.md"), "# KB\n")
        c = read(os.path.join(custom, ".myco-notes.conf")).replace("DOCS_DIR=docs", "DOCS_DIR=myco-docs")
        write(os.path.join(custom, ".myco-notes.conf"), c)
        git(custom, "add", "-A")
        git(custom, "commit", "-qm", "custom names")
        rc, out = run(L(kit, "relocate") + ["--root", custom, "--apply"], tmp)
        check("a custom docs folder name and extra notes folders are kept", rc == 0 and os.path.isfile(os.path.join(custom, MY, "myco-docs", "METHODOLOGY.md")) and os.path.isfile(os.path.join(custom, MY, "knowledge-base", "kb.md")) and "DOCS_DIR=myco-notes/myco-docs" in read(os.path.join(custom, ".myco-notes.conf")), out)
        print("relocate: a tree that already has the layout gets its tools and docs refreshed from the kit")
        ref = os.path.join(tmp, "refresh")
        run(L(kit, "bootstrap") + [ref, "--name", "Refresh", "--tz", "UTC"], tmp)
        os.remove(os.path.join(ref, MY, "tools", "notes_graph.py"))
        os.remove(os.path.join(ref, MY, "tools", "graph-template.html"))
        write(os.path.join(ref, MY, "tools", "notes_commit.py"), "# an older copy\n", "a")
        write(os.path.join(ref, MY, "docs", "TEAM.md"), "an older team guide\n")
        crlf = os.path.join(ref, MY, "tools", "_myco.py")
        write(crlf, read(crlf).replace("\n", "\r\n"))
        c = read(os.path.join(ref, ".myco-notes.conf"))
        write(os.path.join(ref, ".myco-notes.conf"), "".join(l for l in c.splitlines(True) if not l.startswith("NEW_FOLDERS")))
        write(os.path.join(ref, "AGENTS.md"), "".join(l for l in read(os.path.join(ref, "AGENTS.md")).splitlines(True) if "exit code 3" not in l))
        git(ref, "add", "-A")
        git(ref, "commit", "-qm", "older tools")
        rc, out = run(L(kit, "relocate") + ["--root", ref], tmp)
        check("dry run lists the new and changed files and changes nothing", rc == 0 and "dry run" in out and "+ myco-notes/tools/notes_graph.py" in out and "~ myco-notes/tools/notes_commit.py" in out and "~ myco-notes/docs/TEAM.md" in out and git(ref, "status", "--porcelain")[1].strip() == "", out)
        check("a CRLF checkout of an unchanged file is not reported as changed", "_myco.py" not in out, out)
        check("it tells what else to check (NEW_FOLDERS, the AGENTS.md rule)", "NEW_FOLDERS is not set" in out and "exit code 3" in out, out)
        write(os.path.join(ref, "dirty.md"), "x\n")
        git(ref, "add", "dirty.md")
        rc, out = run(L(kit, "relocate") + ["--root", ref, "--apply"], tmp)
        check("apply refuses a tree with uncommitted changes", rc != 0 and "uncommitted" in out, out)
        git(ref, "commit", "-qm", "dirty")
        rc, out = run(L(kit, "relocate") + ["--root", ref, "--apply"], tmp)
        check("apply copies the files", rc == 0 and os.path.isfile(os.path.join(ref, MY, "tools", "notes_graph.py")) and os.path.isfile(os.path.join(ref, MY, "tools", "graph-template.html")) and "an older copy" not in read(os.path.join(ref, MY, "tools", "notes_commit.py")) and "older team guide" not in read(os.path.join(ref, MY, "docs", "TEAM.md")), out)
        check("it leaves the conf, AGENTS.md, bootstrap and the notes alone", "NEW_FOLDERS" not in read(os.path.join(ref, ".myco-notes.conf")) and not os.path.exists(os.path.join(ref, MY, "tools", "bootstrap.py")) and "exit code 3" not in read(os.path.join(ref, "AGENTS.md")))
        rc, out = run(L(kit, "relocate") + ["--root", ref], tmp)
        check("a second run finds nothing to refresh", rc == 0 and "nothing to refresh" in out, out)
        rc, out = run([sys.executable, os.path.join(ref, MY, "tools", "relocate.py"), "--root", ref], ref)
        check("from the project's own tools it says there is no newer kit", rc == 0 and "no newer kit" in out, out)
        rc, out = run([sys.executable, os.path.join(ref, MY, "tools", "build-notes-map.py")], ref)
        check("the refreshed tools build the map with the graph", rc == 0 and os.path.isfile(os.path.join(ref, MY, "map", "graph.html")), out)
        rc, out = run(L(kit, "relocate") + ["--root", tmp], tmp)
        check("it refuses a folder that is not a notes project", rc != 0 and ".myco-notes.conf" in out, out)
    finally:
        def _force(func, path, _exc):
            os.chmod(path, 0o700)
            func(path)
        shutil.rmtree(tmp, onerror=_force)
    print(f"\npassed {passed}, failed {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
