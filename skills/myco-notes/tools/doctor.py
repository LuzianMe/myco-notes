#!/usr/bin/env python3
"""doctor: read-only health check of a Myco Notes repository. It changes nothing.

  tools/doctor [--root DIR] [--home DIR]

Run it from the repository's own tools to check the repository, or from a newer kit (python3 <KIT>/tools/doctor.py --root PROJECT) to
also see whether the repository's tools are older than that kit.

Checks
  version   KIT_VERSION in .myco-notes.conf, the version of the repository's tools, and (from a kit) the kit's version
  layout    the notes, tools and docs folders named in .myco-notes.conf exist; the master record, tracker and entry point exist
  hook      git uses the versioned hook (core.hooksPath) and the hook file is there
  tools     every tool has its sh and .cmd launcher
  settings  settings newer kits expect (NEW_FOLDERS, MIRROR_SCOPE, KIT_VERSION) and the generated map being gitignored
  skills    this skill installed more than once for the same agent (a standalone copy next to a plugin, or two standalone copies,
            in a hidden folder of your home folder or of the repository): the agent may load it twice, or an old copy
Exit: 0 healthy, 1 something to fix (each line says what), 2 not a Myco Notes repository.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import _myco  # noqa: E402

TOOLS = ("asof", "ci-check", "doctor", "mirror-push", "notes-commit", "relocate", "restore-drill", "resume",
         "secret-scan", "setup-clone")


def tools_version(tools_dir):
    try:
        with open(os.path.join(tools_dir, "_myco.py"), encoding="utf-8") as fh:
            m = re.search(r'^VERSION = "([^"]+)"', fh.read(), re.M)
        return m.group(1) if m else None   # tools older than 0.12.0 do not carry a version
    except OSError:
        return None


def is_this_skill(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(2000)
    except OSError:
        return False
    return re.search(r"^name:\s*[\"']?myco-notes[\"']?\s*$", head, re.M) is not None


def skill_copies(base):
    """Installed copies of this skill in base's hidden folders: {folder: [(kind, path)]}, kind 'standalone' (<folder>/skills/<x>/)
    or 'plugin' (anywhere under <folder>/plugins/, where plugin managers keep their copies)."""
    found = {}
    try:
        tops = sorted(d for d in os.listdir(base) if d.startswith(".") and d != ".git" and os.path.isdir(os.path.join(base, d)))
    except OSError:
        return found
    for d in tops:
        skills = os.path.join(base, d, "skills")
        for x in (sorted(os.listdir(skills)) if os.path.isdir(skills) else []):
            if is_this_skill(os.path.join(skills, x, "SKILL.md")):
                found.setdefault(d, []).append(("standalone", os.path.join(skills, x)))
        plugins = os.path.join(base, d, "plugins")
        depth0 = plugins.rstrip(os.sep).count(os.sep)
        for dp, dn, fn in os.walk(plugins):
            if dp.count(os.sep) - depth0 >= 7:
                dn[:] = []
            dn[:] = [n for n in dn if n not in (".git", "node_modules")]
            if "SKILL.md" in fn and os.path.basename(os.path.dirname(dp)) == "skills" and is_this_skill(os.path.join(dp, "SKILL.md")):
                found.setdefault(d, []).append(("plugin", dp))
    return found


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3])


def main():
    _myco.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--home", default=None, help="the home folder to look for installed copies of the skill in (default: yours)")
    a = ap.parse_args()
    root = _myco.toplevel(os.path.abspath(a.root))
    if not root or not os.path.isfile(os.path.join(root, ".myco-notes.conf")):
        print(f"doctor: {os.path.abspath(a.root)} is not a Myco Notes repository (no .myco-notes.conf at a git repository root)")
        return 2
    conf = _myco.load_conf(root)
    lay = _myco.layout(root, conf)
    problems = 0

    def ok(text):
        print(f"  ok    {text}")

    def fix(text):
        nonlocal problems
        problems += 1
        print(f"  FIX   {text}")

    print(f"doctor: {root}")
    tools_dir = os.path.join(root, *lay["tools"].split("/"))
    recorded = conf.get("KIT_VERSION", "").strip()
    have = tools_version(tools_dir)
    from_kit = _myco.overlap(tools_dir, HERE) != "same"
    print(f"  repository tools: {have or 'older than 0.12.0 (no version inside)'}; recorded KIT_VERSION: {recorded or 'not set'}"
          + (f"; this kit: {_myco.VERSION}" if from_kit else ""))
    if not recorded:
        fix("KIT_VERSION is not set in .myco-notes.conf: refresh the tools with relocate from the current kit (it records it)")
    elif have and recorded != have:
        fix(f"KIT_VERSION says {recorded} but the tools are {have}: the tools were copied by hand; refresh them with relocate")
    if from_kit and vkey(have) < vkey(_myco.VERSION):
        fix(f"the repository's tools ({have or 'before 0.12.0'}) are older than this kit ({_myco.VERSION}): "
            f"python3 {os.path.join(HERE, 'relocate.py')} --root {root}  (dry run first, then --apply)")
    elif not from_kit or have:
        ok("tools version")

    for what, rel in (("notes folder", lay["notes"]), ("tools folder", lay["tools"]), ("docs folder", lay["docs"])):
        (ok if os.path.isdir(os.path.join(root, *rel.split("/"))) else fix)(f"{what} {rel}/" + ("" if os.path.isdir(os.path.join(root, *rel.split("/"))) else " is missing"))
    for what, rel in (("entry point", "AGENTS.md"), ("master record", lay["notes"] + "/" + lay["state"]),
                      ("tracker", lay["notes"] + "/sync-tracker.md")):
        present = os.path.isfile(os.path.join(root, *rel.split("/")))
        (ok if present else fix)(f"{what} {rel}" + ("" if present else " is missing"))

    hp = _myco.git("-C", root, "config", "core.hooksPath").stdout.strip()
    want = lay["tools"] + "/hooks"
    if hp != want:
        fix(f"git does not use the versioned hook (core.hooksPath is {hp or 'not set'}, expected {want}): run {lay['tools']}/setup-clone")
    elif not os.path.isfile(os.path.join(root, *want.split("/"), "pre-commit")):
        fix(f"{want}/pre-commit is missing: refresh the tools with relocate")
    else:
        ok("secret-refusing hook active")

    missing = []
    for t in TOOLS:
        for name in (t, t + ".cmd"):
            if not os.path.isfile(os.path.join(tools_dir, name)) and not (t == "doctor" and have is None):
                missing.append(name)
    if missing:
        fix(f"launchers missing in {lay['tools']}/: {', '.join(missing)}")
    else:
        ok("launchers present")

    for key, why in (("NEW_FOLDERS", "what notes-commit does with a new root folder (ask, add, ignorelint, ignoreall)"),
                     ("MIRROR_SCOPE", "what a mirror copies (tracked recommended: never ignored or untracked files)")):
        if key in conf:
            ok(f"{key}={conf[key]}")
        else:
            fix(f"{key} is not set in .myco-notes.conf: {why}")
    if _myco.git("-C", root, "check-ignore", "-q", lay["map"] + "/x").returncode == 0:
        ok(f"generated map {lay['map']}/ is gitignored")
    else:
        fix(f"the generated map {lay['map']}/ is not in .gitignore")
    if not os.path.isfile(os.path.join(root, ".gitattributes")):
        fix(".gitattributes is missing (line endings may differ between Windows and other systems)")

    home = os.path.abspath(a.home or os.path.expanduser("~"))
    copies = {}
    for base in ([home] + ([root] if _myco.overlap(root, home) != "same" else [])):
        for d, items in skill_copies(base).items():
            copies.setdefault(d, []).extend(items)
    shown = lambda p: "~" + p[len(home):] if p.startswith(home + os.sep) else p
    for d, items in sorted(copies.items()):
        standalone = [p for k, p in items if k == "standalone"]
        plugin = [p for k, p in items if k == "plugin"]
        if len(standalone) + (1 if plugin else 0) > 1:
            fix(f"this skill is installed more than once for the agent folder {d}: " + ", ".join(shown(p) for p in standalone)
                + (f" and a plugin ({len(plugin)} cached cop{'y' if len(plugin) == 1 else 'ies'})" if plugin else "")
                + ". The agent may load it twice, or an old copy. Keep one (the plugin, if you installed it) and move the others aside, outside the skills folder.")
    if copies and all(len([1 for k, _ in v if k == "standalone"]) + (1 if any(k == "plugin" for k, _ in v) else 0) <= 1 for v in copies.values()):
        ok("the skill is installed once per agent folder")

    print(f"doctor: {'healthy' if not problems else str(problems) + ' thing(s) to fix'} (nothing was changed)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
