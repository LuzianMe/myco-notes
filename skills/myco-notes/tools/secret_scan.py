#!/usr/bin/env python3
"""secret_scan: read a unified diff on stdin and report ADDED lines that look like secrets. Used by hooks/pre-commit
(staged changes) and by ci_check (a pull request range), so the local hook and CI apply the same rules.

    git diff --cached -U0 | tools/secret-scan
    git diff -U0 origin/main...HEAD | tools/secret-scan

Flags: private-key blocks, cloud/API token prefixes, and names such as password/passphrase/secret/token/api_key followed by
':' or '=' and a long literal value (20+ characters). Prompts like printf "...%s" and references like "!secret name" do not
match. Pattern-based: an unusual format can pass, so treat this as a safety net, not a guarantee.
Allow list: regular expressions (one per line) in the file named by SECRET_ALLOW_FILE (default .myco-notes-secret-allow).
Exit: 0 nothing found, 1 hits (printed to stdout, first 80 characters of each line).
"""
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _myco  # noqa: E402

PATTERNS = [
    r"BEGIN [A-Z ]*PRIVATE KEY",
    r"AKIA[0-9A-Z]{16}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{30,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"sk-[A-Za-z0-9]{32,}",
    r"(password|passwd|passphrase|secret|token|api[_-]?key|psk)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9+/_=-]{20,}",
]


def scan(diff_text, allow_regexes=()):
    added = [l for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++ ")]
    hits = []
    for p in PATTERNS:
        rx = re.compile(p)
        for i, line in enumerate(added, 1):
            if rx.search(line):
                hits.append(f"{i}:{line}")
    allow = [re.compile(a) for a in allow_regexes]
    return [h for h in hits if not any(a.search(h) for a in allow)]


def main():
    _myco.utf8_console()
    root = _myco.toplevel(os.getcwd()) or os.getcwd()
    conf = _myco.load_conf(root)
    allow_file = os.path.join(root, conf.get("SECRET_ALLOW_FILE") or ".myco-notes-secret-allow")
    allow = []
    if os.path.isfile(allow_file):
        with open(allow_file, encoding="utf-8") as fh:
            allow = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    diff_text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    hits = scan(diff_text, allow)
    for h in hits:
        print(h[:80])
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
