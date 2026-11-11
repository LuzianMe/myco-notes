#!/usr/bin/env python3
"""capture: save a quick note as one dated entry in this month's inbox (method section 19.1), and optionally commit it.

  tools/capture "the note, in the owner's words"
  tools/capture --title "Valve B fixed" --tag greenhouse --related irrigation-valve.md "Cleaned it and replaced the seal."
  tools/capture --commit "note"          also commit just this inbox file with notes-commit ("Inbox: <title>")
  tools/capture --commit --pr "note"     ... and push it and open a pull request (with SOLO=1 in the conf: merged once the check passes)
  echo "note" | tools/capture -          read the note from standard input (long or multi-line notes)

The entry goes at the end of <notes>/inbox/YYYY-MM.md (the file is created with a heading when the month starts):

  ## YYYY-MM-DD HH:MM <title>
  <the note>
  Tags: a, b · Related: `note.md`

Options:
  --title TEXT     short title (default: the first words of the note)
  --tag WORD       repeatable; written as a Tags line
  --related NOTE   repeatable; an existing note this one belongs with (a warning if no file of that name exists)
  --when "YYYY-MM-DD HH:MM"   the time the owner meant (default: now)
  --commit, --pr, --merge, --human   passed on to notes-commit (with --only for the inbox file)
Time zone: TIMEZONE in .myco-notes.conf (an IANA name such as Europe/Zurich), else this machine's local time; the zone or UTC
offset is written after the time. Nothing is asked and nothing else is changed: sorting the inbox into the notes is a separate step.
Exit: 0 saved (and committed if asked), 1 not saved or the commit failed, 2 usage; with --commit, notes-commit's own exit code.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402


def now_in(tzname):
    if tzname:
        try:
            from zoneinfo import ZoneInfo  # Python 3.9+
            t = datetime.datetime.now(ZoneInfo(tzname))
            return t, t.strftime("%Y-%m-%d %H:%M ") + tzname
        except Exception:   # unknown name, or Python 3.8: fall back to local time with its offset
            pass
    t = datetime.datetime.now().astimezone()
    off = t.strftime("%z")
    return t, t.strftime("%Y-%m-%d %H:%M ") + ("UTC" if off == "+0000" else off[:3] + ":" + off[3:])


def default_title(text, words=8):
    first = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]
    w = first.split()
    t = " ".join(w[:words]).rstrip(".,;:!?")
    return t + ("..." if len(w) > words else "")


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(prog="capture", add_help=False)
    ap.add_argument("--title", default="")
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--related", action="append", default=[])
    ap.add_argument("--when", default="")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--pr", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--human", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    ap.add_argument("text", nargs="*")
    a = ap.parse_args()
    if a.help:
        print(__doc__)
        return 0
    text = " ".join(a.text).strip()
    if text == "-":
        text = sys.stdin.read().strip()
    if not text:
        print('usage: capture [--title T] [--tag W] [--related NOTE] [--when "YYYY-MM-DD HH:MM"] [--commit [--pr [--merge]]] "note" (or - for stdin)', file=sys.stderr)
        return 2
    root = _myco.toplevel(os.environ.get("NOTES_ROOT") or os.getcwd()) or _myco.toplevel(HERE)
    if not root:
        print("capture: not inside a git repository", file=sys.stderr)
        return 1
    conf = _myco.load_conf(root)
    lay = _myco.layout(root, conf)
    tz = conf.get("TIMEZONE", "").strip()
    if a.when:
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?", a.when.strip())
        if not m:
            print('capture: --when takes "YYYY-MM-DD HH:MM" or "YYYY-MM-DD"', file=sys.stderr)
            return 2
        y, mo, d, hh, mm = m.groups()
        stamp = f"{y}-{mo}-{d}" + (f" {hh}:{mm}" + (" " + tz if tz else "") if hh else "")
        month = f"{y}-{mo}"
    else:
        t, stamp = now_in(tz)
        month = t.strftime("%Y-%m")
    title = re.sub(r"\s+", " ", a.title).strip() or default_title(text)
    body = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    body = re.sub(r"(?m)^(#+\s)", r"\\\1", body)   # a line starting with '#' would become a heading: escape it
    extra = []
    if a.tag:
        extra.append("Tags: " + ", ".join(t.strip().lstrip("#") for t in a.tag if t.strip()))
    if a.related:
        names = []
        for r in a.related:
            r = os.path.basename(r.strip().strip("`"))
            if not r.endswith(".md"):
                r += ".md"
            names.append(f"`{r}`")
            if not any(r in fn for _, _, fns in os.walk(os.path.join(root, *lay["notes"].split("/"))) for fn in fns if fn == r):
                print(f"capture: warning: no note named {r} found; written anyway")
        extra.append("Related: " + ", ".join(names))
    entry = f"## {stamp} {title}\n{body}\n" + (" · ".join(extra) + "\n" if extra else "")

    rel = f"{lay['notes']}/inbox/{month}.md"
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.isfile(path):
        with open(path, encoding="utf-8", newline="") as fh:
            old = fh.read()
        sep = "" if old.endswith("\n\n") else ("\n" if old.endswith("\n") else "\n\n")
    else:
        old, sep = f"# Inbox {month}\nQuick notes as they were captured (method section 19.1), oldest first; sorted into the notes later.\n", "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(old + sep + entry)
    print(f"saved to {rel}: {title}")
    if not (a.commit or a.pr or a.merge):
        return 0
    cmd = [sys.executable, "-B", os.path.join(HERE, "notes_commit.py"), "--only", rel]
    cmd += ["--human"] if a.human else []
    cmd += ["--pr"] if a.pr else []
    cmd += ["--merge"] if a.merge else []
    return subprocess.run(cmd + [f"Inbox: {title}"], cwd=root).returncode


if __name__ == "__main__":
    sys.exit(main())
