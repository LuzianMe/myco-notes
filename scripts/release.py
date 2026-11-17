#!/usr/bin/env python3
"""release: move the kit's version everywhere it is written, and check a release before it is made (kit repository only).

The version lives in four places that must agree (AGENTS.md rule 4): .claude-plugin/plugin.json, .codex-plugin/plugin.json,
metadata.version in skills/myco-notes/SKILL.md and VERSION in skills/myco-notes/tools/_myco.py. CHANGELOG.md needs a section
"## X.Y.Z" for the release.

    python3 scripts/release.py 0.41.0          set all four to 0.41.0 (write the CHANGELOG section first or after; --check tells)
    python3 scripts/release.py --check         the four agree and CHANGELOG.md has their section; prints the version
    python3 scripts/release.py --notes [X.Y.Z] print the CHANGELOG section of the current (or given) version: the release notes

The GitHub Actions workflow .github/workflows/release.yml runs --check on every push to main; when the version has no tag yet it
tags the commit vX.Y.Z and makes the GitHub release from --notes. So a release is: bump, write the CHANGELOG section, merge.
Exit: 0 fine, 1 a check failed, 2 usage.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")
SKILL = "skills/myco-notes/SKILL.md"
MYCO = "skills/myco-notes/tools/_myco.py"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def path(rel):
    return os.path.join(ROOT, *rel.split("/"))


def read(rel):
    with open(path(rel), encoding="utf-8", newline="") as fh:
        return fh.read()


def write(rel, text):
    with open(path(rel), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


SKILL_RX = re.compile(r'(?m)^(  version: )"?([^"\n]*)"?$')
MYCO_RX = re.compile(r'(?m)^(VERSION = )"([^"]*)"')


def versions():
    """{file: version} for the four places."""
    out = {p: json.loads(read(p)).get("version", "") for p in PLUGINS}
    fm = read(SKILL).split("---")[1]
    m = SKILL_RX.search(fm)
    out[SKILL] = m.group(2) if m else ""
    m = MYCO_RX.search(read(MYCO))
    out[MYCO] = m.group(2) if m else ""
    return out


def changelog_section(version):
    """The text of CHANGELOG.md under '## version' up to the next '## ', or None."""
    text = read("CHANGELOG.md")
    m = re.search(r"(?m)^## " + re.escape(version) + r"\s*$", text)
    if not m:
        return None
    rest = text[m.end():]
    n = re.search(r"(?m)^## ", rest)
    return (rest[:n.start()] if n else rest).strip("\n")


def set_version(new):
    for p in PLUGINS:
        text = read(p)
        text, k = re.subn(r'("version"\s*:\s*)"[^"]*"', lambda m: m.group(1) + f'"{new}"', text, count=1)
        assert k == 1, p
        write(p, text)
    text = read(SKILL)
    head, sep, rest = text.partition("\n---\n")
    head, k = SKILL_RX.subn(lambda m: m.group(1) + f'"{new}"', head, count=1)
    assert k == 1, SKILL
    write(SKILL, head + sep + rest)
    text, k = MYCO_RX.subn(lambda m: m.group(1) + f'"{new}"', read(MYCO), count=1)
    assert k == 1, MYCO
    write(MYCO, text)


def check():
    v = versions()
    problems = []
    if len(set(v.values())) != 1:
        problems.append("the versions differ: " + ", ".join(f"{p} {x or '(none)'}" for p, x in v.items()))
    ver = v[PLUGINS[0]]
    if not SEMVER.match(ver or ""):
        problems.append(f"{PLUGINS[0]}: {ver!r} is not X.Y.Z")
    elif changelog_section(ver) is None:
        problems.append(f"CHANGELOG.md has no '## {ver}' section")
    elif not changelog_section(ver).strip():
        problems.append(f"CHANGELOG.md: the '## {ver}' section is empty")
    return ver, problems


def main():
    args = sys.argv[1:]
    if args == ["--check"]:
        ver, problems = check()
        for p in problems:
            print("release: " + p, file=sys.stderr)
        if not problems:
            print(ver)
        return 1 if problems else 0
    if args and args[0] == "--notes" and len(args) <= 2:
        ver = args[1] if len(args) == 2 else versions()[PLUGINS[0]]
        sec = changelog_section(ver)
        if sec is None:
            print(f"release: CHANGELOG.md has no '## {ver}' section", file=sys.stderr)
            return 1
        print(sec)
        return 0
    if len(args) == 1 and SEMVER.match(args[0]):
        old = versions()
        set_version(args[0])
        print(f"version {', '.join(sorted(set(old.values())))} -> {args[0]} in {', '.join(list(PLUGINS) + [SKILL, MYCO])}")
        if changelog_section(args[0]) is None:
            print(f"next: add a '## {args[0]}' section at the top of CHANGELOG.md, run the tests, commit and merge")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
