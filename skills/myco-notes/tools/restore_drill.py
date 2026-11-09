#!/usr/bin/env python3
"""restore-drill: prove the notes can be restored. Give it a directory that was restored from the mirror or from a snapshot
(or a .tar, .tar.gz or .zip of it). It runs git fsck, shows the last commits, checks the entry point and the tracker, compares
the newest commit with the live repository, and prints one line ready to paste into the sync log.

  tools/restore-drill /path/to/restored-copy
  tools/restore-drill /path/to/backup.tar.gz
"""
import datetime
import os
import sys
import tarfile
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402


def extract(archive, dest):
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)  # zipfile already refuses absolute paths and ..
    else:
        with tarfile.open(archive) as t:
            try:
                t.extractall(dest, filter="data")  # Python 3.12+ and recent patch releases: refuses unsafe members
            except TypeError:
                base = os.path.realpath(dest)
                for m in t.getmembers():
                    if not os.path.realpath(os.path.join(dest, m.name)).startswith(base + os.sep) or m.issym() or m.islnk():
                        raise SystemExit(f"FAIL: unsafe path in archive: {m.name}")
                t.extractall(dest)


def find_repo(src, depth=3):
    src = os.path.abspath(src)
    for dp, dn, _fn in os.walk(src):
        if dp[len(src):].count(os.sep) >= depth:
            dn[:] = []
        if ".git" in dn:
            return dp
    return None


def main():
    _myco.utf8_console()
    if len(sys.argv) < 2:
        print("usage: restore-drill <restored dir | archive>", file=sys.stderr)
        return 2
    arg = sys.argv[1]
    live = _myco.toplevel(HERE)
    tmp = None
    src = arg
    if os.path.isfile(arg):
        tmp = tempfile.TemporaryDirectory()
        extract(arg, tmp.name)
        src = tmp.name
    repo = find_repo(src)
    if not repo:
        print(f"FAIL: no .git found under {src}")
        return 1
    rc = 0
    print(f"restored repository: {repo}")
    r = _myco.git("-C", repo, "fsck", "--no-progress")
    for line in (r.stdout + r.stderr).splitlines():
        if not line.startswith("dangling"):
            print(f"  fsck: {line}")
    if r.returncode == 0:
        print("  fsck: OK")
    else:
        print("  fsck: PROBLEMS")
        rc = 1
    print("  last commits:")
    for line in _myco.git("-C", repo, "log", "--oneline", "-5").stdout.splitlines():
        print(f"    {line}")
    for f in ("AGENTS.md", "CLAUDE.md"):
        if os.path.isfile(os.path.join(repo, f)):
            print(f"  entry point present: {f}")
    notes_dir = _myco.layout(repo)["notes"]
    if os.path.isfile(os.path.join(repo, *notes_dir.split("/"), "sync-tracker.md")):
        print("  tracker present")
    else:
        print("  tracker MISSING")
        rc = 1
    a = _myco.git("-C", repo, "rev-parse", "HEAD").stdout.strip()
    b = _myco.git("-C", live, "rev-parse", "HEAD").stdout.strip() if live else ""
    if a == b:
        print(f"  restored HEAD equals live HEAD ({a})")
    else:
        print(f"  restored HEAD differs from live HEAD (restored {a[:8]}, live {b[:8]}): fine for an old snapshot, check the date")
    now = datetime.datetime.now()
    res = "OK" if rc == 0 else "PROBLEMS"
    print()
    print(f"Sync-log line: - **{now:%Y-%m-%d} ({now:%H:%M}):** restore drill from {os.path.basename(arg.rstrip('/' + os.sep))}: fsck and log {res}; HEAD {a[:8]}.")
    if tmp:
        tmp.cleanup()
    return rc


if __name__ == "__main__":
    sys.exit(main())
