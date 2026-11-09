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


def sync_dir(src, dst):
    """Make dst equal to src (like rsync -a --delete): copy new or changed files, remove what no longer exists."""
    os.makedirs(dst, exist_ok=True)
    src_names = set(os.listdir(src))
    for name in os.listdir(dst):
        if name not in src_names:
            _rm(os.path.join(dst, name))
    for name in src_names:
        s, d = os.path.join(src, name), os.path.join(dst, name)
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
            sync_dir(s, d)
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
        sync_dir(root, target)
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
