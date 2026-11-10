#!/usr/bin/env python3
"""mirror-push: keep a second copy of the notes repository on another machine or disk.

Target comes from MIRROR_TARGET in .myco-notes.conf:
  /path/or/C:\\path     a local directory: the whole working copy including .git is copied and the copy is made equal
                        (files that no longer exist are removed there)
  git:URL               a git remote (any URL git understands, including a bare repository on another disk or server):
                        `git push --mirror` (history and tracked files only; needs no rsync, works the same on Windows)
  user@host:/path       another machine over ssh with rsync (needs ssh and rsync installed)
History safety comes from an independent snapshot job that backs up the mirror. Skips quietly (exit 0) when the target is
unreachable or not configured, so a timer never nags. Run it from a timer (for example every 6 hours) and after notes-commit -p.

  mirror-push --dry-run    for a local directory: list what would be copied and removed, change nothing

A local directory target must not be the repository, a folder inside it or a folder that contains it. Because the copy is
made equal (files only in the target are removed), the tool writes only into an empty folder, a folder holding its marker
file .myco-mirror, or an earlier mirror of the same repository (it then adds the marker).
"""
import os
import re
import shutil
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402


def _rm(path):
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)  # read-only files (.git objects on Windows)
    except OSError:
        pass
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))
    else:
        os.remove(path)


MARKER = ".myco-mirror"


def sync_dir(src, dst, plan=None, top=True):
    """Make dst equal to src (like rsync -a --delete): copy new or changed files, remove what no longer exists.
    With `plan` (a list) nothing changes: each action is appended as ("remove"|"copy", path) instead."""
    if plan is None:
        os.makedirs(dst, exist_ok=True)
    src_names = set(os.listdir(src))
    dst_names = os.listdir(dst) if os.path.isdir(dst) else []
    for name in dst_names:
        if name not in src_names and not (top and name == MARKER):
            if plan is None:
                _rm(os.path.join(dst, name))
            else:
                plan.append(("remove", os.path.join(dst, name)))
    for name in sorted(src_names):
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if plan is not None:
            if os.path.isdir(s) and not os.path.islink(s):
                if os.path.lexists(d) and not os.path.isdir(d):
                    plan.append(("remove", d))
                sync_dir(s, d, plan, False)
            elif not (os.path.isfile(d) and os.stat(d).st_size == os.stat(s).st_size
                      and int(os.stat(d).st_mtime) == int(os.stat(s).st_mtime)):
                plan.append(("copy", d))
            continue
        if os.path.islink(s):
            if os.path.lexists(d):
                _rm(d)
            try:
                os.symlink(os.readlink(s), d)
            except (OSError, NotImplementedError):
                pass
        elif os.path.isdir(s):
            if os.path.lexists(d) and not os.path.isdir(d):
                _rm(d)
            sync_dir(s, d, None, False)
        else:
            if os.path.isdir(d) and not os.path.islink(d):
                _rm(d)
            ss = os.stat(s)
            if os.path.exists(d):
                ds = os.stat(d)
                if ds.st_size == ss.st_size and int(ds.st_mtime) == int(ss.st_mtime):
                    continue
                if not os.access(d, os.W_OK):
                    os.chmod(d, stat.S_IWRITE | stat.S_IREAD)
            shutil.copy2(s, d)


def same_repository(root, target):
    """True when target is a git working copy that shares its first commit with root (an earlier mirror of it)."""
    if not os.path.isdir(os.path.join(target, ".git")):
        return False
    a = _myco.git("-C", root, "rev-list", "--max-parents=0", "HEAD").stdout.split()
    b = _myco.git("-C", target, "rev-list", "--max-parents=0", "HEAD").stdout.split()
    return bool(a) and bool(set(a) & set(b))


def check_local_target(root, target):
    """None when the local target is safe to make equal to root, else the reason it is refused."""
    rel = _myco.overlap(root, target)
    if rel == "same":
        return "the target is the repository itself"
    if rel == "inside":
        return "the target is inside the repository (it would copy itself)"
    if rel == "contains":
        return "the target contains the repository (making it equal would delete everything else in it)"
    if not _myco.owned_or_empty(target, MARKER, lambda t: same_repository(root, t)):
        return (f"{target} is not empty and is not a mirror of this repository; point MIRROR_TARGET at an empty folder, or put an "
                f"empty file named {MARKER} in it if every file there may be replaced or removed")
    return None


def dir_size(path):
    total = 0
    for dp, _dn, fn in os.walk(path):
        for f in fn:
            try:
                total += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return total


def main():
    _myco.utf8_console()
    root = _myco.toplevel(HERE)
    if not root:
        print("mirror: not inside a git repository", file=sys.stderr)
        return 1
    os.chdir(root)
    dry = "--dry-run" in sys.argv[1:]
    conf = _myco.load_conf(root)
    target = os.path.expanduser(os.path.expandvars(conf.get("MIRROR_TARGET", "")))
    post = [c for c in conf.get("POST_PUSH_CMDS", "").splitlines() if c.strip()]
    if not target:
        print("mirror: MIRROR_TARGET not set in .myco-notes.conf, skipped")
        return 0

    if target.startswith("git:"):
        url = target[4:]
        r = subprocess.run(["git", "push", "--mirror", "-q", url], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            print(f"mirror: git push --mirror to {url} failed, skipped ({r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'no detail'})")
            return 0
    elif re.match(r"^[A-Za-z]:[\\/]", target) or ":" not in target:
        why = check_local_target(root, target)
        if why:
            print(f"mirror: failed, refused: {why}", file=sys.stderr)
            return 1
        if dry:
            plan = []
            sync_dir(root, target, plan)
            for act, path in plan:
                print(f"  would {act}: {path}")
            print(f"mirror: dry run, {sum(a == 'copy' for a, _ in plan)} to copy, {sum(a == 'remove' for a, _ in plan)} to remove; nothing changed")
            return 0
        sync_dir(root, target)
        open(os.path.join(target, MARKER), "a").close()
    else:  # user@host:/path
        host = target.split(":", 1)[0]
        if not shutil.which("rsync") or not shutil.which("ssh"):
            print("mirror: a remote host target needs rsync and ssh; install them or use MIRROR_TARGET=git:URL", file=sys.stderr)
            return 1
        ok = subprocess.run(["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", host, "true"], capture_output=True).returncode == 0
        if not ok:
            print(f"mirror: {host} not reachable, skipped")
            return 0
        subprocess.run(["rsync", "-a", "--delete", "-e", "ssh -o BatchMode=yes", root.rstrip("/") + "/", target.rstrip("/") + "/"], check=True)

    for c in post:
        try:
            r = _myco.run_shell(c, root, timeout=120)
            print("\n".join((r.stdout + r.stderr).strip().splitlines()[-2:]))
        except Exception as e:  # a failing publish never breaks the push
            print(f"mirror: post-push command failed ({e})")
    try:
        with open(os.path.join(root, ".git", "last-mirror-push"), "w") as fh:
            fh.write(str(int(time.time())) + "\n")
    except OSError:
        pass
    print(f"mirror: pushed {_myco.human_size(dir_size(root))} to {conf.get('MIRROR_TARGET')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
