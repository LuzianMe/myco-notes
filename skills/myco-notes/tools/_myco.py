"""Shared helpers for the Myco Notes tools. Standard library only; the same code runs on Linux, macOS and Windows."""
import os
import re
import subprocess
import sys

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


def _rel(p):
    """A repository-relative folder name written with forward slashes and no leading or trailing slash."""
    return (p or "").strip().replace("\\", "/").strip("/")


def layout(root, conf=None):
    """Folder layout from .myco-notes.conf, as repository-relative paths with forward slashes.

    No MYCO_DIR (trees made before 0.6.0): notes/, tools/, docs/ and notes-map/ at the repository root.
    MYCO_DIR=myco-notes: that one folder holds the notes themselves plus tools/, docs/ and map/.
    NOTES_DIR, TOOLS_DIR, DOCS_DIR and MAP_DIR each override one folder; DATA_DIRS lists project folders that are not notes;
    HISTORY_DIRS (inside the notes folder) holds records that are not re-checked for dates and references.
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
        "data": [d for d in (_rel(x) for x in conf.get("DATA_DIRS", "").split()) if d],
        "history": [d for d in (_rel(x) for x in conf.get("HISTORY_DIRS", "archive logs").split()) if d],
    }


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
