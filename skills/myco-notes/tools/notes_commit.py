#!/usr/bin/env python3
"""notes-commit: commit everything changed in the notes repository with a described message.

  tools/notes-commit "what changed and why"            commit only
  tools/notes-commit -p "message"                      also mirror afterwards (tools/mirror-push)
  tools/notes-commit --human "message"                 no AI co-author trailer
  tools/notes-commit --tag audit-2026-11-03 "message"  also create a milestone tag
  tools/notes-commit --branch my-change "message"      commit on that branch (created from the current one if new)
  tools/notes-commit --push "message"                  also git push the current branch to origin (sets the upstream)
  tools/notes-commit --pr "message"                    --push, then open a pull request with the GitHub CLI (gh pr create --fill)

Behaviour (configured in .myco-notes.conf at the repository root):
  - stages everything (respecting .gitignore); says "nothing to commit" and exits 0 when clean
  - syntax-checks changed shell and python files before committing (CHECK_SH / CHECK_PY)
  - the pre-commit hook (<tools folder>/hooks/pre-commit) refuses commits that add secret-looking lines
  - adds AGENT_TRAILER unless --human
  - after the commit, if a changed file matches SYNC_GLOBS, runs SYNC_CMD so the live copy equals the committed copy
  - team use: --branch / --push / --pr give each change its own branch and pull request (see docs/TEAM.md)
"""
import argparse
import fnmatch
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402


def fail(msg, code=1):
    print(f"notes-commit: {msg}", file=sys.stderr)
    sys.exit(code)


def shell_syntax_ok(path):
    """bash -n on Linux and macOS; skipped on Windows, where `bash` may be an unrelated launcher."""
    if _myco.IS_WINDOWS or not shutil.which("bash"):
        return True
    return subprocess.run(["bash", "-n", path]).returncode == 0


def is_shell_script(path, hooks_prefix="tools/hooks/"):
    if path.endswith(".sh") or path.startswith(hooks_prefix):
        return True
    try:
        with open(path, "rb") as fh:
            first = fh.readline(200)
    except OSError:
        return False
    return first.startswith(b"#!") and (b"sh" in first)


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(prog="notes-commit", add_help=False)
    ap.add_argument("-p", action="store_true")
    ap.add_argument("--human", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--branch", default="")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--pr", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    ap.add_argument("message", nargs="*")
    a = ap.parse_args()
    if a.help:
        print(__doc__)
        return 0
    msg = " ".join(a.message).strip()
    if not msg:
        print('usage: notes-commit [-p] [--human] [--tag NAME] [--branch NAME] [--push|--pr] "message"', file=sys.stderr)
        return 2

    root = _myco.toplevel(os.environ.get("NOTES_ROOT") or os.getcwd()) or _myco.toplevel(HERE)
    if not root:
        fail("not inside a git repository", 2)
    os.chdir(root)
    conf = _myco.load_conf(root)
    check_sh, check_py = conf.get("CHECK_SH", "1") == "1", conf.get("CHECK_PY", "1") == "1"
    trailer, sync_globs, sync_cmd = conf.get("AGENT_TRAILER", ""), conf.get("SYNC_GLOBS", "").split(), conf.get("SYNC_CMD", "")
    hooks_prefix = _myco.layout(root, conf)["tools"] + "/hooks/"

    if a.branch:
        cur = _myco.git("symbolic-ref", "-q", "--short", "HEAD").stdout.strip()
        if cur != a.branch:
            exists = _myco.git("show-ref", "-q", "--verify", f"refs/heads/{a.branch}").returncode == 0
            r = _myco.git("switch", "-q", *([] if exists else ["-c"]), a.branch)
            if r.returncode:
                fail(f"cannot switch to branch {a.branch}: {r.stderr.strip()}")
            print(f"notes-commit: on branch {a.branch}")

    _myco.git("add", "-A")
    if _myco.git("diff", "--cached", "--quiet").returncode == 0:
        print("notes-commit: nothing to commit")
        return 0

    changed = [f for f in _myco.git("-c", "core.quotepath=off", "diff", "--cached", "--name-only", "--diff-filter=AM", "-z").stdout.split("\0") if f]
    for f in changed:
        if f.endswith(".py") and check_py:
            try:
                with open(f, "rb") as fh:
                    compile(fh.read(), f, "exec")
            except (SyntaxError, ValueError) as e:
                fail(f"syntax error in {f} ({e}), not committing")
        elif check_sh and os.path.isfile(f) and is_shell_script(f, hooks_prefix):
            if not shell_syntax_ok(f):
                fail(f"syntax error in {f}, not committing")

    full = msg + (f"\n\n{trailer}" if trailer and not a.human else "")
    rc = subprocess.run(["git", "commit", "-q", "-m", full]).returncode  # hook output goes straight to the terminal
    if rc:
        return rc
    print(_myco.git("log", "--oneline", "-1").stdout.strip())
    print("\n".join(_myco.git("show", "--stat", "--format=", "HEAD").stdout.rstrip("\n").splitlines()[-6:]))
    if a.tag:
        if _myco.git("tag", a.tag).returncode == 0:
            print(f"tagged {a.tag}")

    if sync_globs and sync_cmd and any(fnmatch.fnmatchcase(f, g) for g in sync_globs for f in changed):
        r = _myco.run_shell(sync_cmd, root)
        if r.returncode:
            print("WARNING: committed, but SYNC_CMD failed; the live copy may differ from the committed copy", file=sys.stderr)

    if a.p:
        if subprocess.run([sys.executable, os.path.join(HERE, "mirror_push.py")]).returncode:
            print("WARNING: committed, but the mirror push failed", file=sys.stderr)

    if a.push or a.pr:
        cur = _myco.git("symbolic-ref", "-q", "--short", "HEAD").stdout.strip()
        if not cur:
            print("WARNING: detached HEAD, not pushing", file=sys.stderr)
            return 0
        if _myco.git("remote", "get-url", "origin").returncode != 0:
            print("WARNING: no remote named origin; nothing pushed", file=sys.stderr)
            return 0
        if subprocess.run(["git", "push", "-q", "-u", "origin", cur]).returncode == 0:
            print(f"pushed {cur} to origin")
        else:
            print("WARNING: committed, but git push failed", file=sys.stderr)
        if a.pr:
            if shutil.which("gh"):
                if subprocess.run(["gh", "pr", "create", "--fill"]).returncode:
                    print("WARNING: pull request not created (does one exist already?)", file=sys.stderr)
            else:
                print(f"gh (GitHub CLI) not installed: open a pull request for branch {cur} in your hosting service")
    return 0


if __name__ == "__main__":
    sys.exit(main())
