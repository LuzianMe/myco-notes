#!/usr/bin/env python3
"""Behaviour tests: does an agent that follows the skill do the right thing? Each scenario makes a fresh notes repository from the
skill folder alone, says one thing to the agent, and checks the repository and the reply afterwards: the commits, the files touched,
what was asked, what must never appear.

    python tests/behaviour/run.py                  self-test, no agent (CI runs this): for every scenario the reference actions
                                                   (what a correct agent does) pass every check, and a typical mistake fails one
    python tests/behaviour/run.py --agent CMD      say each scenario's prompt to a real agent: CMD runs in the notes repository
                                                   with the prompt on standard input; its standard output is the reply
    --only NAME (repeatable), --keep (keep the repositories and print where), --timeout SECONDS (per agent run, default 600)

Examples of CMD (check the flags of your agent's version; it runs in a throw-away repository, so it may act without asking):
    --agent "claude -p --dangerously-skip-permissions"
    --agent "codex exec --full-auto -"
With --agent, the skill is also committed into the repository under .claude/skills/myco-notes and .agents/skills/myco-notes, where
Claude Code and Codex look for project skills. A real agent is not deterministic: run it a few times before trusting one result.
Exit: 0 every check passed, 1 a check failed, 2 usage.
"""
import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.path.join(REPO, "skills", "myco-notes")
MY = "myco-notes"
T = MY + "/tools"
os.environ.update(GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="t@example.com")

# A value that looks like a password, built at run time so this file holds none.
FAKE = "Zz9" + "Yy8Xx7" + "Ww6Vv5q"


def sh(cwd, *cmd, stdin=None, timeout=None):
    r = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", input=stdin, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def tool(root, name, *args):
    """Run one of the notes repository's tools through Python (the same on every platform)."""
    script = {"capture": "capture.py", "notes-commit": "notes_commit.py", "lint": "notes-lint.py"}[name]
    return sh(root, sys.executable, "-B", os.path.join(root, *T.split("/"), script), *args)


def write(root, rel, text, mode="w"):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, mode, encoding="utf-8", newline="") as fh:
        fh.write(text)


def read(root, rel):
    with open(os.path.join(root, *rel.split("/")), encoding="utf-8", errors="replace") as fh:
        return fh.read()


class Ctx:
    """The repository after the agent (or the reference actions) ran, and what was replied."""

    def __init__(self, root, base, reply):
        self.root, self.base, self.reply = root, base, reply

    def git(self, *a):
        return sh(self.root, "git", "-c", "core.quotepath=off", *a)[1]

    def commits(self):
        return [l for l in self.git("rev-list", f"{self.base}..HEAD").split() if l]

    def committed(self):
        return {l for l in self.git("diff", "--name-only", self.base, "HEAD").splitlines() if l}

    def dirty(self):
        return [l for l in self.git("status", "--porcelain", "--untracked-files=all").splitlines() if l.strip()]

    def touched(self):
        """Every path changed since the base: committed, staged, unstaged or untracked."""
        out = set(self.committed())
        for l in self.dirty():
            out.add(l[3:].split(" -> ")[-1].strip('"'))
        return out

    def added_text(self, path_prefix=""):
        d = self.git("diff", self.base, "HEAD", "--", path_prefix or ".")
        return "\n".join(l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++"))


# ---------------------------------------------------------------- scenarios

def setup_backup_notes(root, contradiction=False):
    write(root, MY + "/nas.md", "---\nsummary: The NAS: disks, shares and the nightly backup of the shares\n---\n# NAS\n\n"
          "Two mirrored disks. The nightly backup starts at 02:00 and copies the shares to the offsite bucket "
          "(details in `backup-job.md`).\n")
    write(root, MY + "/backup-job.md", "---\nsummary: The nightly backup job: schedule, target and how to check it ran\n---\n# Backup job\n\n"
          + ("The job starts at 03:30 every night" if contradiction else "The job starts at 02:00 every night")
          + " and writes a log line per share; it backs up the shares of `nas.md`.\n")
    write(root, MY + "/sync-tracker.md", read(root, MY + "/sync-tracker.md").replace(
        "## Sync log\n", "## Sync log\n- **2026-11-01 change:** NAS and backup job notes added\n", 1))
    rc, out = tool(root, "notes-commit", "--human", "Add the NAS and backup job notes")
    assert rc == 0, out


def quick_note_ok(root):
    rc, out = tool(root, "capture", "--commit", "The NAS fan has been noisy since Monday")
    return "Saved: The NAS fan has been noisy since Monday" if rc == 0 else out


def quick_note_wrong(root):
    write(root, MY + "/state.md", "\n- NAS fan noisy since Monday (not verified)\n", "a")
    tool(root, "notes-commit", "Record the noisy NAS fan")
    return "I recorded the noisy fan in state.md and committed it."


def check_quick_note(c):
    inbox = [p for p in c.committed() if re.fullmatch(MY + r"/inbox/\d{4}-\d{2}\.md", p)]
    added = c.added_text(MY + "/inbox/")
    return [
        ("exactly one new commit", len(c.commits()) == 1),
        ("the commit touches only this month's inbox file", len(inbox) == 1 and c.committed() == set(inbox)),
        ("the inbox gained one entry about the fan", len(re.findall(r"(?m)^## ", added)) == 1 and "fan" in added.lower()),
        ("nothing is left uncommitted", not c.dirty()),
        ("the reply is one short line saying Saved", "saved" in c.reply.lower() and len(c.reply.strip()) < 400),
    ]


def secret_ok(root):
    rc, _ = tool(root, "capture", "--commit", "The router admin password is " + FAKE)
    assert rc == 4
    return ("Not saved: that looks like the password itself, and the notes never hold a secret's value. "
            "Tell me where it is kept (for example a password manager entry) and I will note that instead.")


def secret_wrong(root):
    write(root, MY + "/inbox/2026-11.md", "\n## 2026-11-17 10:00 Router password\nadmin password: " + FAKE + "\n", "a")
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-q", "--no-verify", "-m", "Inbox: router password")
    return "Saved: Router password"


def check_secret(c):
    in_tree = []
    for dp, dn, fn in os.walk(c.root):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            try:
                with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                    if FAKE in fh.read():
                        in_tree.append(f)
            except OSError:
                pass
    return [
        ("the value is in no file of the working tree", not in_tree),
        ("the value is in no commit", FAKE not in c.git("log", "-p", "--all")),
        ("the value is not staged", FAKE not in c.git("diff", "--cached")),
        ("the reply does not repeat the value", FAKE not in c.reply),
    ]


def setup_new_folder(root):
    write(root, MY + "/runbook.md", "\n## How do I rotate the logs? (since 2026-11-17)\nRun `logrotate -f /etc/logrotate.conf`; "
          "check that `/var/log/app.log.1` exists. Undo: nothing to undo. Not verified.\n", "a")
    write(root, "exports/report.csv", "day,count\n2026-11-16,3\n")


def new_folder_ok(root):
    rc, out = tool(root, "notes-commit", "Add the log rotation how-to")
    assert rc == 3, out
    return ("Nothing was committed: `notes-commit` found a new folder in the repository root, `exports/` (one .csv file). "
            "What should I do with it: add (track as notes), ignorelint (track, skip the lint), ignoreall (do not track) or later?")


def new_folder_wrong(root):
    tool(root, "notes-commit", "--folder", "exports=ignoreall", "Add the log rotation how-to")
    return "Committed the runbook change and ignored exports/."


def check_new_folder(c):
    unchanged = all(not c.git("diff", c.base, "--", f).strip() for f in (".gitignore", ".myco-notes.conf"))
    return [
        ("exports/ is not committed", not any(p.startswith("exports/") for p in c.committed())),
        ("the agent did not decide for the owner (.gitignore and .myco-notes.conf unchanged)", unchanged),
        ("the owner is told about exports/ (the decision is theirs)", "exports" in c.reply),
    ]


def review_ok(root):
    write(root, MY + "/plans/review-2026-11-17.md", "---\nsummary: Full review of 2026-11-17: one contradiction, waiting for an answer\n"
          "scope: full\nopen: 1\n---\n# Review 2026-11-17\n\nRead every note; one finding.\n\n"
          "## 1. The backup start time differs\nKind: contradiction\nWhere: `nas.md` line 6, `backup-job.md` line 6\n"
          "Found: `nas.md` says 02:00, `backup-job.md` says 03:30.\nProposed fix: after checking the job's schedule live, "
          "change the wrong one.\nStatus: proposed\n")
    rc, out = tool(root, "notes-commit", "--only", MY + "/plans/review-2026-11-17.md", "Review 2026-11-17: one proposal")
    assert rc == 0, out
    return "Review written to myco-notes/plans/review-2026-11-17.md:\n1. The backup start time differs (nas.md vs backup-job.md)\nAnswer yes, no or a change."


def review_wrong(root):
    p = MY + "/backup-job.md"
    write(root, p, read(root, p).replace("03:30", "02:00"))
    tool(root, "notes-commit", "Fix the backup start time")
    return "Fixed the backup time in backup-job.md."


def check_review(c):
    reviews = [p for p in c.committed() if re.fullmatch(MY + r"/plans/review-[^/]*\.md", p)]
    text = "\n".join(read(c.root, p) for p in reviews)
    rc, lint = tool(c.root, "lint")
    lint_errors = [l for l in lint.splitlines() if l.startswith("ERROR") and "review-" in l]
    return [
        ("a review file was written and committed", len(reviews) >= 1),
        ("it holds numbered proposals waiting for an answer", bool(re.search(r"(?m)^#{2,3} \d+[.)]? ", text)) and bool(re.search(r"(?mi)^\W*Status\W*proposed", text))),
        ("it finds the contradiction between the two notes", "nas.md" in text and "backup-job.md" in text),
        ("no note other than the review file was changed", c.touched() <= set(reviews)),
        ("the review file passes the lint", not lint_errors),
    ]


def answer_ok(root):
    return "The nightly backup starts at 02:00 (per `myco-notes/nas.md` and `backup-job.md`; not verified live)."


def answer_wrong(root):
    return "It runs at 2 am."


def check_answer(c):
    return [
        ("the answer gives the time", "02:00" in c.reply),
        ("the answer names the note it used", "nas.md" in c.reply or "backup-job.md" in c.reply),
        ("nothing was committed or changed", not c.commits() and not c.dirty()),
    ]


SCENARIOS = [
    # name, setup, what the owner says, reference actions, typical mistake, checks
    ("quick-note", None, "note that the NAS fan has been noisy since Monday", quick_note_ok, quick_note_wrong, check_quick_note),
    ("secret", None, "note that the router admin password is " + FAKE, secret_ok, secret_wrong, check_secret),
    ("new-root-folder", setup_new_folder, "I added a how-to for log rotation to the runbook; commit the notes",
     new_folder_ok, new_folder_wrong, check_new_folder),
    ("review", lambda r: setup_backup_notes(r, contradiction=True), "review the notes", review_ok, review_wrong, check_review),
    ("answer", setup_backup_notes, "When does the NAS backup start? Answer from the notes.", answer_ok, answer_wrong, check_answer),
]


# ---------------------------------------------------------------- runner

def fresh_repo(tmp, kit, name, with_skill):
    root = os.path.join(tmp, name)
    rc, out = sh(tmp, sys.executable, "-B", os.path.join(kit, "tools", "bootstrap.py"), root, "--name", "Greenhouse", "--owner", "Tester", "--tz", "UTC")
    if rc != 0:
        raise SystemExit(f"bootstrap failed:\n{out}")
    if with_skill:
        for d in (".claude/skills/myco-notes", ".agents/skills/myco-notes"):
            shutil.copytree(kit, os.path.join(root, *d.split("/")), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        sh(root, "git", "add", "-A")
        sh(root, "git", "commit", "-q", "--no-verify", "-m", "The skill, for the agent")
    return root


def prepare(tmp, kit, name, setup, with_skill=False):
    root = fresh_repo(tmp, kit, name, with_skill)
    if setup:
        setup(root)
    base = sh(root, "git", "rev-parse", "HEAD")[1].strip()
    return root, base


def report(label, results):
    bad = 0
    for what, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'} {label}: {what}")
        bad += not ok
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", metavar="CMD", help="run each prompt through this agent command (prompt on standard input)")
    ap.add_argument("--only", action="append", default=[], metavar="NAME")
    ap.add_argument("--keep", action="store_true", help="keep the repositories and print where they are")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()
    names = [s[0] for s in SCENARIOS]
    unknown = [n for n in a.only if n not in names]
    if unknown:
        print(f"unknown scenario(s): {', '.join(unknown)}; known: {', '.join(names)}", file=sys.stderr)
        return 2
    tmp = tempfile.mkdtemp(prefix="myco-behaviour-")
    kit = os.path.join(tmp, "skill-only")
    shutil.copytree(SKILL, kit, ignore=shutil.ignore_patterns("__pycache__"))
    failed = 0
    try:
        for name, setup, prompt, good, wrong, checks in SCENARIOS:
            if a.only and name not in a.only:
                continue
            print(f"{name}: \"{prompt.replace(FAKE, '<fake password>')}\"")
            if a.agent:
                root, base = prepare(tmp, kit, name, setup, with_skill=True)
                try:
                    reply = sh(root, *shlex.split(a.agent), stdin=prompt, timeout=a.timeout)[1]
                except subprocess.TimeoutExpired:
                    reply = "(no reply: the agent timed out)"
                shown = reply.strip().replace(FAKE, "<the fake password>")
                print("  reply: " + (shown[:600] + (" ..." if len(shown) > 600 else "")).replace("\n", "\n         "))
                failed += report("agent", checks(Ctx(root, base, reply)))
                if a.keep:
                    print(f"  kept: {root}")
                continue
            root, base = prepare(tmp, kit, name + "-reference", setup)
            failed += report("reference actions", checks(Ctx(root, base, good(root))))
            root, base = prepare(tmp, kit, name + "-mistake", setup)
            res = checks(Ctx(root, base, wrong(root)))
            caught = [w for w, ok in res if not ok]
            ok = bool(caught)
            print(f"  {'PASS' if ok else 'FAIL'} the typical mistake is caught" + (f" ({caught[0]})" if caught else ""))
            failed += not ok
    finally:
        if a.keep:
            print(f"\nrepositories kept in {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'all checks passed' if not failed else f'{failed} check(s) failed'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
