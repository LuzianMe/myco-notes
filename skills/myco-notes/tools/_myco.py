"""Shared helpers for the Myco Notes tools. Standard library only; the same code runs on Linux, macOS and Windows."""
import os
import re
import subprocess
import sys

VERSION = "0.17.3"   # the kit version these tools come from; moves with plugin.json and SKILL.md (tests check it)
AGENT_SKILL_DIRS = (".claude/skills", ".agents/skills")   # a copy of the skill kept in a notes repository for agents (a cloud session loads it from there): not notes, so the lint and the map leave it out

IS_WINDOWS = os.name == "nt"


def utf8_console():
    """Make printing safe on consoles that are not UTF-8 (Windows)."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def git(*args, cwd=None, input=None):
    """Run git, capture UTF-8 output. Returns the CompletedProcess (never raises on a non-zero exit)."""
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", input=input)


def toplevel(start):
    """Root of the git repository that contains `start`, or None."""
    r = git("-C", start, "rev-parse", "--show-toplevel")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _real(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def overlap(a, b):
    """How folder b relates to folder a: 'same', 'inside' (b is inside a), 'contains' (b contains a) or None.
    Compares resolved paths (symbolic links, case on Windows), so two spellings of one folder are the same folder."""
    ra, rb = _real(a), _real(b)
    if ra == rb:
        return "same"
    try:
        common = os.path.commonpath([ra, rb])
    except ValueError:  # different drives on Windows
        return None
    if common == ra:
        return "inside"
    if common == rb:
        return "contains"
    return None


def owned_or_empty(path, marker, looks_like=None):
    """True when `path` does not exist, is an empty folder, holds our `marker` file, or (for folders made before markers
    existed) passes `looks_like(path)`. Tools that empty or overwrite a folder call this first."""
    if not os.path.exists(path):
        return True
    if not os.path.isdir(path):
        return False
    if not os.listdir(path) or os.path.isfile(os.path.join(path, marker)):
        return True
    return bool(looks_like and looks_like(path))


def load_conf(root):
    """Read .myco-notes.conf (shell-style KEY=value, quoted values may span lines). No shell is executed."""
    p = os.path.join(root, ".myco-notes.conf")
    conf = {}
    if not os.path.isfile(p):
        return conf
    with open(p, encoding="utf-8") as fh:
        text = fh.read()
    pat = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)=", re.M)
    n, pos = len(text), 0
    while True:
        m = pat.search(text, pos)
        if not m:
            break
        j = m.end()
        if j < n and text[j] in "\"'":
            q, k, buf = text[j], j + 1, []
            while k < n and text[k] != q:
                if q == '"' and text[k] == "\\" and k + 1 < n and text[k + 1] in '"\\$`':
                    buf.append(text[k + 1])
                    k += 2
                    continue
                buf.append(text[k])
                k += 1
            val, pos = "".join(buf), k + 1
        else:
            e = text.find("\n", j)
            e = n if e < 0 else e
            val, pos = re.split(r"\s+#", text[j:e])[0].strip(), e
        conf[m.group(1)] = val
    return conf


def frontmatter(text):
    """Optional header at the top of a note (method 10.1): a '---' line, 'key: value' lines, a closing '---' line. No YAML library.

    Returns ({key: (value, line_number)}, number of lines the header occupies); ({}, 0) when the note has none. Keys are lower-cased
    and use underscores; a trailing '# comment' and surrounding quotes are dropped; anything that is not 'key: value' is ignored.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fm = {}
    for i in range(1, min(len(lines), 60)):
        raw = lines[i].rstrip("\r")
        if raw.strip() in ("---", "..."):
            return fm, i + 1
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", raw)
        if m:
            key = m.group(1).lower().replace("-", "_")
            val = m.group(2) if key == "summary" else re.sub(r"\s+#.*$", "", m.group(2))   # a summary may contain " #"
            fm[key] = (val.strip().strip("\"'"), i + 1)
    return {}, 0


SUMMARY_MAX = 200   # characters (method 10.1)
LOG_KINDS = ("change", "note", "answer", "review", "audit", "import", "merge", "upgrade", "setup", "drill")   # sync-log line kinds (method 4)
LOG_LINE = re.compile(r"^- \*\*\d{4}-\d{2}-\d{2} (" + "|".join(LOG_KINDS) + r")( \([^)]*\))?:\*\*\s+\S")


REVIEW_FILE = re.compile(r"^review-.*\.md$")   # <notes>/plans/review-YYYY-MM-DD.md (method 21.2)


def review_proposals(text):
    """(numbers of all proposals, numbers still waiting) of a review file: '## N. title' headings, each with a 'Status:' line;
    a status starting with 'proposed' (also 'proposed (revised ...)') is waiting."""
    num, allp, waiting = None, [], []
    for line in text.split("\n"):
        hm = re.match(r"^#{2,3}\s+(\d+)[.)]?\s", line)
        if hm:
            num = hm.group(1)
        elif num and re.match(r"^\s*\**Status:?\**:?\s*\S", line, re.I):
            allp.append(num)
            if re.match(r"^\s*\**Status:?\**:?\s*proposed", line, re.I):
                waiting.append(num)
            num = None
    return allp, waiting


def parse_open(value):
    """The numbers in a review file's 'open:' header ('none', '' or '-' is no number); None when it cannot be read."""
    v = value.strip().lower()
    if v in ("none", "-", ""):
        return []
    parts = [p.strip() for p in v.split(",") if p.strip()]
    return parts if all(p.isdigit() for p in parts) else None


def first_sentence(text, fm_end=0):
    """The first sentence of the first plain paragraph after the title (no heading, table, list, quote or code), for a note
    without a summary. Markdown emphasis and link syntax are dropped; at most SUMMARY_MAX characters."""
    in_code = False
    for line in text.split("\n")[fm_end:]:
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s or s.startswith(("#", "|", ">", "-", "*", "<", "---")) or re.match(r"^\d+[.)]\s", s):
            continue
        s = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]|\[([^\]]+)\]\([^)]*\)|[`*_]", lambda m: m.group(2) or m.group(1) or m.group(3) or "", s)
        m = re.match(r"(.+?[.!?])(\s|$)", s)
        s = m.group(1) if m else s
        return s if len(s) <= SUMMARY_MAX else s[:SUMMARY_MAX - 3].rstrip() + "..."
    return ""


def note_summary(text):
    """(summary, from_header) of a note: the `summary` key of its header (method 10.1), else its first sentence (from_header False)."""
    fm, end = frontmatter(text)
    s = fm.get("summary", ("", 0))[0].strip()
    return (s, True) if s else (first_sentence(text, end), False)


def _rel(p):
    """A repository-relative folder name written with forward slashes and no leading or trailing slash."""
    return (p or "").strip().replace("\\", "/").strip("/")


def layout(root, conf=None):
    """Folder layout from .myco-notes.conf, as repository-relative paths with forward slashes.

    No MYCO_DIR (trees made before 0.6.0): notes/, tools/, docs/ and notes-map/ at the repository root.
    MYCO_DIR=myco-notes: that one folder holds the notes themselves plus tools/, docs/ and map/.
    NOTES_DIR, TOOLS_DIR, DOCS_DIR and MAP_DIR each override one folder; DATA_DIRS lists project folders that are not notes;
    HISTORY_DIRS (inside the notes folder) holds records that are not re-checked for dates and references.
    STATE_FILE is the master record's file name inside the notes folder (default state.md; a project may call it homelab.md).
    """
    conf = load_conf(root) if conf is None else conf
    my = _rel(conf.get("MYCO_DIR"))

    def pick(key, legacy, nested):
        return _rel(conf.get(key)) or (nested if my else legacy)

    return {
        "myco": my,
        "notes": pick("NOTES_DIR", "notes", my),
        "tools": pick("TOOLS_DIR", "tools", my + "/tools"),
        "docs": pick("DOCS_DIR", "docs", my + "/docs"),
        "map": pick("MAP_DIR", "notes-map", my + "/map"),
        "state": _rel(conf.get("STATE_FILE")) or "state.md",
        "data": [d for d in (_rel(x) for x in conf.get("DATA_DIRS", "").split()) if d],
        "history": list(dict.fromkeys([d for d in (_rel(x) for x in conf.get("HISTORY_DIRS", "archive logs").split()) if d] + ["inbox", "imported"])),   # the inbox (19.1) and imported originals (20) are always records
    }


def record_kit_version(root):
    """Write KIT_VERSION=<these tools' version> into the tree's .myco-notes.conf (bootstrap and relocate call it)."""
    cp = os.path.join(root, ".myco-notes.conf")
    if not os.path.isfile(cp):
        return
    with open(cp, encoding="utf-8", newline="") as fh:
        text = fh.read()
    with open(cp, "w", encoding="utf-8", newline="") as fh:
        fh.write(set_conf_key(text, "KIT_VERSION", VERSION))


def set_conf_key(text, key, value):
    """Return the conf text with KEY set to value: the first uncommented KEY= line is replaced, otherwise the line is appended."""
    new = f'{key}="{value}"' if (" " in value) else f"{key}={value}"
    pat = re.compile(rf"^[ \t]*{re.escape(key)}=.*$", re.M)
    if pat.search(text):
        return pat.sub(lambda _m: new, text, count=1)
    return text + ("" if text.endswith("\n") or not text else "\n") + new + "\n"


def run_shell(cmd, cwd, timeout=None):
    """Run a command line from the configuration: bash on Linux and macOS, the platform shell (cmd.exe) on Windows."""
    args = cmd if IS_WINDOWS else ["bash", "-c", cmd]
    return subprocess.run(args, cwd=cwd, shell=IS_WINDOWS, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def human_size(nbytes):
    for unit in ("B", "K", "M", "G", "T"):
        if nbytes < 1024 or unit == "T":
            return f"{nbytes:.0f}{unit}" if unit == "B" else f"{nbytes:.1f}{unit}"
        nbytes /= 1024


WIKI_LINK = re.compile(r"!?\[\[([^\]\n|#]*)(?:#[^\]\n|]*)?(?:\|[^\]\n]*)?\]\]")
MD_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")


def links(text):
    """Links in a note other than file-name mentions (method 9): wiki links ([[Name]], [[Name|text]], [[Name#heading]], ![[embed]])
    and Markdown links to relative paths ([text](../a/b.md), ![](img.png)). Fenced code blocks and inline code are skipped.
    Yields (kind, target, line number): kind 'wiki' (target is a note name or path without .md, or a file name) or 'path' (a relative
    path with %-escapes decoded and any #anchor removed). Web, mail and other scheme links and pure #anchors are left out."""
    from urllib.parse import unquote
    in_code = False
    for i, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            continue
        if in_code:
            continue
        line = re.sub(r"`[^`\n]*`", "", line)
        for m in WIKI_LINK.finditer(line):
            t = m.group(1).strip()
            if t:
                yield "wiki", t, i
        for m in MD_LINK.finditer(line):
            t = m.group(1).strip()
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", t) or t.startswith(("#", "//")):
                continue
            t = unquote(t.split("#", 1)[0].split("?", 1)[0])
            if t:
                yield "path", t, i


class LinkIndex:
    """Resolves links (see links()) to repository paths. md_files and all_paths are repository-relative with forward slashes."""

    def __init__(self, md_files, all_paths=()):
        self.paths = set(all_paths) | set(md_files)
        self.by_stem, self.by_name = {}, {}
        for f in md_files:
            self.by_stem.setdefault(f[:-3].rsplit("/", 1)[-1].lower(), []).append(f)
            self.by_stem.setdefault(f[:-3].lower(), []).append(f)
        for f in self.paths:
            self.by_name.setdefault(f.rsplit("/", 1)[-1].lower(), []).append(f)

    def resolve(self, kind, target, from_rel):
        """The repository path a link points to, or None when nothing matches. A wiki name shared by several notes picks the one
        nearest to the linking note (same folder first)."""
        if kind == "path":
            if target.startswith("/"):
                cand = [target.lstrip("/")]
            else:
                cand = [os.path.normpath(os.path.join(os.path.dirname(from_rel), target)).replace(os.sep, "/"), target]
            for c in cand:
                if c in self.paths:
                    return c
                if not os.path.splitext(c)[1] and c + ".md" in self.paths:
                    return c + ".md"
            return None
        t = target.replace("\\", "/").strip("/")
        low = t.lower()
        hits = self.by_stem.get(low[:-3] if low.endswith(".md") else low) or self.by_name.get(low.rsplit("/", 1)[-1] if "/" not in low else low) or []
        if not hits and "/" in low:
            hits = [f for f in self.paths if f.lower().endswith("/" + low) or f.lower().endswith("/" + low + ".md")]
        if not hits:
            return None
        here = os.path.dirname(from_rel)
        return sorted(set(hits), key=lambda f: (os.path.dirname(f) != here, not f.startswith(here + "/") if here else 0, f.count("/"), f))[0]
