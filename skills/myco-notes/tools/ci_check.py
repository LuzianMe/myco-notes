#!/usr/bin/env python3
"""ci-check: the checks a pull request must pass (run by .github/workflows/notes-check.yml, runnable locally).

  tools/ci-check [BASE]      BASE = commit or ref to compare with (default origin/main); empty or all zeros = last commit only

  1. secret scan of every line the range adds (same rules as the local hook, which a contributor can bypass)
  2. tools/notes-lint.py: errors (exit 2) fail the check; warnings fail only when CI_LINT_STRICT=1 in .myco-notes.conf
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402
import secret_scan  # noqa: E402

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def main():
    _myco.utf8_console()
    root = _myco.toplevel(HERE)
    if not root:
        print("ci-check: not inside a git repository", file=sys.stderr)
        return 1
    os.chdir(root)
    conf = _myco.load_conf(root)
    strict = conf.get("CI_LINT_STRICT", "0") == "1"

    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    if base.strip("0") == "":
        base = ""
    if base and _myco.git("rev-parse", "-q", "--verify", f"{base}^{{commit}}").returncode != 0:
        print(f"ci-check: base '{base}' not found (shallow clone?); scanning the last commit only", file=sys.stderr)
        base = ""
    if base:
        rng = [f"{base}...HEAD"]
    else:
        parent = _myco.git("rev-parse", "-q", "--verify", "HEAD~1")
        rng = [parent.stdout.strip() if parent.returncode == 0 else EMPTY_TREE, "HEAD"]

    rc = 0
    print(f"== secret scan ({' '.join(rng)})")
    diff = _myco.git("diff", "-U0", "--no-color", *rng).stdout
    allow_file = os.path.join(root, conf.get("SECRET_ALLOW_FILE") or ".myco-notes-secret-allow")
    allow = []
    if os.path.isfile(allow_file):
        with open(allow_file, encoding="utf-8") as fh:
            allow = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    hits = secret_scan.scan(diff, allow)
    if hits:
        print("FAIL: possible secrets in added lines (first 80 characters shown):")
        for h in hits:
            print(h[:80])
        rc = 1
    else:
        print("ok: no secret-looking added lines")

    print("== notes-lint")
    sys.stdout.flush()
    lrc = subprocess.run([sys.executable, os.path.join(HERE, "notes-lint.py"), "--root", root]).returncode
    if lrc == 2:
        print("FAIL: lint errors")
        rc = 1
    elif lrc == 1 and strict:
        print("FAIL: lint warnings (CI_LINT_STRICT=1)")
        rc = 1
    elif lrc == 1:
        print("warnings only: not failing (set CI_LINT_STRICT=1 to fail on warnings)")

    print("ci-check: passed" if rc == 0 else "ci-check: FAILED")
    return rc


if __name__ == "__main__":
    sys.exit(main())
