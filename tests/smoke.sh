#!/bin/bash
# Smoke test: bootstrap a tree in a temporary folder and exercise the tools. Exit 0 = all passed.
set -u
kit="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
repo="$kit"   # the repository root (kit is later pointed at a skill-only copy)
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0
ok()   { echo "  PASS $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL $1"; fail=$((fail+1)); }
chk()  { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }
export GIT_AUTHOR_NAME=Test GIT_AUTHOR_EMAIL=t@example.com GIT_COMMITTER_NAME=Test GIT_COMMITTER_EMAIL=t@example.com

skill="$kit/skills/myco-notes"

echo "plugin manifests"
chk "plugin.json is valid JSON"         "python3 -c \"import json;json.load(open('$kit/.claude-plugin/plugin.json'))\""
chk "marketplace.json is valid JSON"    "python3 -c \"import json;json.load(open('$kit/.claude-plugin/marketplace.json'))\""
chk "plugin and marketplace names match" "python3 - <<PY
import json
a=json.load(open('$kit/.claude-plugin/plugin.json'));b=json.load(open('$kit/.claude-plugin/marketplace.json'))
assert a['name']==b['plugins'][0]['name'] and 'version' in a and b['plugins'][0]['source'] in ('./', '.')
PY"
chk "Codex manifest matches the plugin manifest" "python3 - <<PY
import json,os
a=json.load(open('$kit/.claude-plugin/plugin.json'));c=json.load(open('$kit/.codex-plugin/plugin.json'))
assert c['name']==a['name'] and c['version']==a['version'], 'name or version differs'
assert c['skills']=='./skills/' and c['interface']['displayName']
for k in ('composerIcon','logo'):
    assert os.path.isfile(os.path.join('$kit', c['interface'][k])), k
PY"
chk "marketplace source resolves to the plugin root" "[ -f $kit/.claude-plugin/plugin.json ] && [ -d $skill ]"
chk "skill version equals plugin version" "python3 - <<PY
import json,re
v=json.load(open('$kit/.claude-plugin/plugin.json'))['version']
t=open('$skill/SKILL.md').read().split('---')[1]
assert re.search(r'version:\s*\"?'+re.escape(v)+r'\"?\s*\$', t, re.M), 'SKILL.md metadata.version differs from plugin.json'
assert re.search(r'^VERSION = \"'+re.escape(v)+r'\"', open('$skill/tools/_myco.py').read(), re.M), '_myco.VERSION differs from plugin.json'
PY"

echo "agent skill (Agent Skills specification)"
chk "frontmatter follows the specification" "python3 - <<PY
import re,os
t=open('$skill/SKILL.md').read(); fm=t.split('---')[1]
get=lambda k: (re.search(r'^'+k+r':\s*(.+)\$', fm, re.M) or [None,None])[1]
name=get('name'); desc=get('description'); comp=get('compatibility')
assert name==os.path.basename('$skill'), 'name must equal the folder name'
assert re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', name) and len(name)<=64
assert desc and len(desc)<=1024, 'description missing or over 1024 characters'
assert comp is None or len(comp)<=500
assert t.count(chr(10))<500, 'SKILL.md should stay under 500 lines'
PY"
chk "SKILL.md needs no CLAUDE_PLUGIN_ROOT" "! grep -q 'CLAUDE_PLUGIN_ROOT' $skill/SKILL.md"
chk "every path SKILL.md names exists in the skill folder" "python3 - <<PY
import re,os
t=open('$skill/SKILL.md').read()
for m in set(re.findall(r'<KIT>/((?:tools|docs|template)[A-Za-z0-9_./-]*)', t)):
    p=os.path.join('$skill', m.rstrip('/.,)'))
    assert os.path.exists(p), 'missing '+m
PY"

# From here on the kit is a COPY of the skill folder alone: proves the skill is self-contained (what a skill-only installer delivers).
cp -a "$skill" "$tmp/skill-only"; kit="$tmp/skill-only"

echo "bootstrap (from the copied skill folder only)"
"$kit/tools/bootstrap" "$tmp/proj" --name "Demo" --owner "Tester" --tz "UTC" >/dev/null 2>&1
cd "$tmp/proj" || exit 1
chk "baseline commit exists"            "git log --oneline | grep -q Baseline"
chk "placeholders filled"               "! grep -rq '{{' AGENTS.md myco-notes/working-agreement.md myco-notes/state.md .myco-notes.conf"
chk "hooks path is versioned"           "[ \"\$(git config core.hooksPath)\" = myco-notes/tools/hooks ]"
chk "bootstrap not copied into tree" "[ ! -e myco-notes/tools/bootstrap ]"

echo "notes-commit"
echo "- **$(date +%F) (test change):** added a thing, tested, undo: revert." >> myco-notes/state.md
chk "commit with message"               "myco-notes/tools/notes-commit 'Record the test change and why' | grep -q 'Record the test change'"
chk "clean tree says nothing to commit" "myco-notes/tools/notes-commit 'again' | grep -q 'nothing to commit'"
printf '#!/bin/bash\nif then\n' > myco-notes/scripts/broken.sh
chk "syntax error blocks the commit"    "! myco-notes/tools/notes-commit 'broken script'"
rm myco-notes/scripts/broken.sh

echo "pre-commit hook"
printf 'api_key = AbCdEfGhIjKlMnOpQrStUvWx12\n' > myco-notes/secret-test.md
chk "secret is refused"                 "! myco-notes/tools/notes-commit 'add a secret'"
git reset -q; rm -f myco-notes/secret-test.md
printf -- '-----BEGIN RSA %s-----\nabc\n' 'PRIVATE KEY' > myco-notes/key-test.md   # assembled at run time: no key-shaped text in this file
chk "private key block is refused"      "! myco-notes/tools/notes-commit 'add a key'"
git reset -q; rm -f myco-notes/key-test.md
chk "tree is clean again"               "[ -z \"\$(git status --porcelain)\" ]"

echo "new folders in the root"
mkdir runbooks files_input; echo "# r" > runbooks/a.md; echo x > files_input/a.pdf
head0="$(git rev-parse HEAD)"
chk "ask: a new root folder stops the commit with exit 3" "myco-notes/tools/notes-commit 'new folders'; [ \$? = 3 ] && [ \"\$(git rev-parse HEAD)\" = $head0 ]"
chk "the report names the folders and the choices" "myco-notes/tools/notes-commit 'new folders' | grep -q 'runbooks/' && myco-notes/tools/notes-commit 'new folders' | grep -q 'ignorelint'"
chk "answers commit: add, ignoreall" "myco-notes/tools/notes-commit --folder runbooks=add --folder files_input=ignoreall 'Decide the new folders' >/dev/null && git ls-files | grep -q runbooks/a.md && ! git ls-files | grep -q files_input && git check-ignore -q files_input && grep -q 'files_input' .myco-notes.conf"
rm -rf runbooks files_input; git rm -rq runbooks; git commit -qam "remove the folder test items"
sed -i 's/^DATA_DIRS=.*/DATA_DIRS=""/' .myco-notes.conf; sed -i '/^\/files_input\/$/d' .gitignore; git commit -qam "reset the folder test"
chk "tree is clean again after the folder test" "[ -z \"\$(git status --porcelain)\" ]"

echo "lint"
myco-notes/tools/notes-lint.py >/tmp/lint.$$ 2>&1; rc=$?
chk "lint runs on a fresh tree (exit 0 or 1)" "[ $rc -le 1 ]"
printf '\n## 3. One\n## 3. Two\nSee `missing-note.md`. Pending, review-by 2020-01-01.\n' >> myco-notes/runbook.md
myco-notes/tools/notes-lint.py >/tmp/lint.$$ 2>&1; rc=$?
chk "lint finds duplicate heading"      "grep -q 'duplicate heading number 3' /tmp/lint.$$"
chk "lint finds missing reference"      "grep -q 'missing note' /tmp/lint.$$"
chk "lint finds passed follow-up date"  "grep -q 'has passed' /tmp/lint.$$"
git checkout -q -- myco-notes/runbook.md
rm -f /tmp/lint.$$

echo "freshness header, resume, asof"
printf -- '---\nreview_after: 2020-03-01\n---\n# Fresh smoke\n' > myco-notes/plans/fresh-smoke.md
myco-notes/tools/notes-lint.py >/tmp/lint.$$ 2>&1
chk "lint reports a passed review_after in a header" "grep -q 'review date 2020-03-01 has passed' /tmp/lint.$$"
rm -f /tmp/lint.$$
chk "resume prints a briefing with a footer" "myco-notes/tools/resume | grep -q 'budget 6000 characters'"
chk "resume lists the note past its review date" "myco-notes/tools/resume | grep -q 'fresh-smoke.md'"
chk "asof shows the notes at HEAD"      "myco-notes/tools/asof HEAD state.md | grep -q 'master record'"
chk "asof rejects a date before the history" "! myco-notes/tools/asof 2001-01-01"
rm -f myco-notes/plans/fresh-smoke.md

echo "map"
chk "map builds"                        "python3 myco-notes/tools/build-notes-map.py && [ -f myco-notes/map/index.html ]"
chk "page has history"                  "grep -q 'History' myco-notes/map/p/myco-notes-state.html"
chk "map is gitignored"                 "git check-ignore -q myco-notes/map"
chk "map also builds the mycelium view and links it" "[ -f myco-notes/map/graph.html ] && grep -q graph.html myco-notes/map/index.html && grep -q 'id=\"data\"' myco-notes/map/graph.html"
printf 'token = ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n' > myco-notes/leak.md
chk "map refuses a secret"              "! python3 myco-notes/tools/build-notes-map.py"
rm -f myco-notes/leak.md

echo "mirror and restore drill"
sed "s|^MIRROR_TARGET=.*|MIRROR_TARGET=\"$tmp/mirror\"|" .myco-notes.conf > .myco-notes.conf.new && mv .myco-notes.conf.new .myco-notes.conf
git add -A; git commit -q -m "Configure mirror"
chk "mirror push"                       "myco-notes/tools/mirror-push | grep -q 'mirror: synced'"
chk "mirror contains .git"              "[ -d $tmp/mirror/.git ]"
chk "restore drill passes"              "myco-notes/tools/restore-drill $tmp/mirror | grep -q 'fsck: OK'"

echo "team setup (branches, CI check, per-clone setup)"
chk "team files exist in the bootstrapped tree" "[ -f .github/workflows/notes-check.yml ] && [ -f .github/CODEOWNERS ] && [ -f .github/pull_request_template.md ] && [ -f myco-notes/docs/TEAM.md ]"
chk "workflow runs myco-notes/tools/ci-check"      "grep -q 'myco-notes/tools/ci-check' .github/workflows/notes-check.yml"
git clone -q "$tmp/proj" "$tmp/clone"
chk "hooks path is not cloned"          "[ -z \"\$(git -C $tmp/clone config core.hooksPath)\" ]"
chk "setup-clone activates the hook in a fresh clone" "(cd $tmp/clone && myco-notes/tools/setup-clone >/dev/null 2>&1 && [ \"\$(git config core.hooksPath)\" = myco-notes/tools/hooks ])"
base="$(git rev-parse HEAD)"
echo "- team test line" >> myco-notes/plans/backlog.md
chk "notes-commit --branch creates the branch" "myco-notes/tools/notes-commit --branch feat-a 'Team test change and why' >/dev/null && [ \"\$(git symbolic-ref --short HEAD)\" = feat-a ]"
chk "ci-check passes on a clean change"  "myco-notes/tools/ci-check $base"
printf 'api_key = AbCdEfGhIjKlMnOpQrStUvWx12\n' > myco-notes/leak2.md
git switch -q -c feat-leak; git add -A; git commit -q --no-verify -m "bypass the hook"
chk "ci-check catches a secret committed with --no-verify" "! myco-notes/tools/ci-check $base"
git switch -q main
git init -q --bare "$tmp/remote.git"; git remote add origin "$tmp/remote.git"
echo "- push test line" >> myco-notes/plans/backlog.md
chk "notes-commit --push publishes the branch" "myco-notes/tools/notes-commit --branch feat-b --push 'Push test and why' >/dev/null 2>&1 && git ls-remote --heads origin feat-b | grep -q feat-b"
chk "--pr is documented in the usage"   "myco-notes/tools/notes-commit --help | grep -q -- '--pr'"

chk "no __pycache__ left in the project by the tools" "[ -z \"\$(find . -name __pycache__ -not -path './.git/*')\" ]"

echo "safety: destructive outputs, history scan, crashes, redaction, page names"
chk "map refuses --out at the repository root" "! python3 myco-notes/tools/build-notes-map.py --out . && [ -f myco-notes/state.md ]"
chk "map refuses --out on a folder it did not make" "! python3 myco-notes/tools/build-notes-map.py --out myco-notes && [ -f myco-notes/state.md ]"
chk "map marks its own folder"          "python3 myco-notes/tools/build-notes-map.py && [ -f myco-notes/map/.myco-notes-map ]"
setmirror() { sed "s|^MIRROR_TARGET=.*|MIRROR_TARGET=\"$1\"|" .myco-notes.conf > .myco-notes.conf.new && mv .myco-notes.conf.new .myco-notes.conf; }
setmirror "$tmp/proj";            chk "mirror refuses the repository itself"   "! myco-notes/tools/mirror-push"
setmirror "$tmp/proj/myco-notes/m"; chk "mirror refuses a folder inside the repository" "! myco-notes/tools/mirror-push && [ ! -e myco-notes/m ]"
setmirror "$tmp";                 chk "mirror refuses a folder that contains the repository" "! myco-notes/tools/mirror-push"
mkdir -p "$tmp/other"; echo keep > "$tmp/other/precious.txt"
setmirror "$tmp/other";           chk "mirror refuses a non-empty folder that is not its mirror" "! myco-notes/tools/mirror-push && [ -f $tmp/other/precious.txt ]"
setmirror "$tmp/mirror2";         chk "mirror dry run changes nothing" "myco-notes/tools/mirror-push --dry-run | grep -q 'nothing changed' && [ ! -e $tmp/mirror2 ]"
chk "mirror into a new folder leaves its marker" "myco-notes/tools/mirror-push | grep -q 'mirror: synced' && [ -f $tmp/mirror2/.myco-mirror ]"
setmirror "$tmp/mirror"; git checkout -q -- .myco-notes.conf 2>/dev/null
mkdir -p myco-notes/pg && echo "# Nested" > myco-notes/pg/x.md && echo "# Flat" > myco-notes/pg-x.md
chk "two notes with the same page name both get a page" "python3 myco-notes/tools/build-notes-map.py && [ \$(ls myco-notes/map/p | grep -c '^myco-notes-pg-x') = 2 ]"
rm -rf myco-notes/pg myco-notes/pg-x.md
upper="PASS""WORD"
printf '%s=Hunter2Hunter2x\n' "$upper" > myco-notes/upper.md
chk "an upper-case password line is refused, no line text shown" "out=\$(git add -A && git commit -q -m upper 2>&1); [ \$? -ne 0 ] && echo \"\$out\" | grep -q 'value not shown' && ! echo \"\$out\" | grep -q Hunter2"
git reset -q; rm -f myco-notes/upper.md
base2="$(git rev-parse HEAD)"; git switch -q -c feat-history
printf 'token = %s\n' "QQQQQQQQQQABCDEFGHIJKL1234" > myco-notes/gone.md; git add -A; git commit -q --no-verify -m "add"
git rm -q myco-notes/gone.md; git commit -q -m "remove"
chk "ci-check finds a secret added and removed again" "out=\$(myco-notes/tools/ci-check $base2); [ \$? -ne 0 ] && echo \"\$out\" | grep -q 'gone.md:1' && ! echo \"\$out\" | grep -q QQQQ"
git switch -q main; git branch -q -D feat-history
git switch -q -c feat-crash; echo '[unclosed' > .myco-notes-lint-ignore; git add -A; git commit -q -m "bad ignore"
chk "lint exits 3 on an invalid ignore expression" "myco-notes/tools/notes-lint.py --quiet; [ \$? = 3 ]"
chk "ci-check fails when the lint cannot run" "! myco-notes/tools/ci-check $base2"
git switch -q main; git branch -q -D feat-crash

echo "0.12: restore verdicts, mirror scope and results, narrower commits, kit version, doctor"
chk "new trees record the kit version"  "grep -q '^KIT_VERSION=[0-9]' .myco-notes.conf && grep -q '^MIRROR_SCOPE=tracked' .myco-notes.conf"
chk "doctor reports a healthy tree"     "myco-notes/tools/doctor | grep -q 'doctor: healthy'"
git clone -q "$tmp/proj" "$tmp/drill"; rm -f "$tmp/drill/AGENTS.md"; echo changed > "$tmp/drill/myco-notes/state.md"
chk "restore drill fails an incomplete working copy" "out=\$(myco-notes/tools/restore-drill $tmp/drill); [ \$? -ne 0 ] && echo \"\$out\" | grep -q 'verdict history:      OK' && echo \"\$out\" | grep -q 'working copy: INCOMPLETE'"
echo "local only" > ignored-local.env; printf 'ignored-local.env\n' >> .git/info/exclude
setmirror "$tmp/mirror3"
chk "tracked mirror leaves ignored files out" "myco-notes/tools/mirror-push | grep -q 'mirror: synced' && [ -f $tmp/mirror3/AGENTS.md ] && [ -d $tmp/mirror3/.git ] && [ ! -e $tmp/mirror3/ignored-local.env ]"
rm -f ignored-local.env
setmirror "git:$tmp/nowhere.git"
chk "unreachable git mirror is skipped (exit 0)" "myco-notes/tools/mirror-push | grep -q 'mirror: skipped'"
chk "--strict makes a skip exit 3"      "myco-notes/tools/mirror-push --strict; [ \$? = 3 ]"
git checkout -q -- .myco-notes.conf
echo "- only one" >> myco-notes/plans/backlog.md; echo "- not this" >> myco-notes/runbook.md
chk "notes-commit --dry-run changes nothing" "myco-notes/tools/notes-commit --dry-run 'x' | grep -q 'would commit 2' && [ -z \"\$(git diff --cached --name-only)\" ]"
chk "notes-commit --only commits just that path" "myco-notes/tools/notes-commit --only myco-notes/plans/backlog.md 'Only the backlog' >/dev/null && git show --name-only --format= HEAD | grep -qx myco-notes/plans/backlog.md && ! git show --name-only --format= HEAD | grep -q runbook && git diff --name-only | grep -q runbook"
git checkout -q -- myco-notes/runbook.md

echo "0.12.1: links in the mirror, line text, merges, missing base, worktrees, scoped checks, -p result, content check, ssh"
setmirror "$tmp/mir4"; myco-notes/tools/mirror-push >/dev/null
mkdir -p "$tmp/outside4"; echo sentinel > "$tmp/outside4/keep.txt"
rm -rf "$tmp/mir4/myco-notes/plans"; ln -s "$tmp/outside4" "$tmp/mir4/myco-notes/plans"
rm -f "$tmp/mir4/AGENTS.md"; ln -s "$tmp/outside4/keep.txt" "$tmp/mir4/AGENTS.md"
chk "a link inside the mirror is replaced, never followed" "myco-notes/tools/mirror-push | grep -q 'mirror: synced' && [ -f $tmp/outside4/keep.txt ] && [ \"\$(cat $tmp/outside4/keep.txt)\" = sentinel ] && [ \$(ls $tmp/outside4 | wc -l) = 1 ] && [ ! -L $tmp/mir4/myco-notes/plans ] && [ ! -L $tmp/mir4/AGENTS.md ]"
f="$tmp/mir4/myco-notes/state.md"; t=$(python3 -c "import os,sys;print(int(os.stat(sys.argv[1]).st_mtime))" "$f")
python3 - "$f" "$t" <<'PY'
import os,sys
p,t=sys.argv[1],int(sys.argv[2]); b=bytearray(open(p,'rb').read()); b[0]=ord('X') if b[0]!=ord('X') else ord('Y'); open(p,'wb').write(b); os.utime(p,(t,t))
PY
chk "--verify repairs a same-size, same-time change" "myco-notes/tools/mirror-push >/dev/null; ! cmp -s myco-notes/state.md $f && myco-notes/tools/mirror-push --verify >/dev/null && cmp -s myco-notes/state.md $f"
two="token = $(printf 'Q%.0s' 1 2 3 4 5 6 7 8 9 10)ABCDEFGHIJKL1234 api_key = $(printf 'W%.0s' 1 2 3 4 5 6 7 8 9 10)ABCDEFGHIJKL5678"
printf '%s\n' "$two" > myco-notes/two.md
chk "two secrets on one line: neither is shown" "out=\$(git add -A && git commit -q -m two 2>&1); [ \$? -ne 0 ] && echo \"\$out\" | grep -q 'two.md:1' && ! echo \"\$out\" | grep -q -e QQQQ -e WWWW"
git reset -q; rm -f myco-notes/two.md
base3="$(git rev-parse HEAD)"
git switch -q -c side3; echo "side line" >> myco-notes/runbook.md; git commit -qam side
git switch -q -c feat-merge "$base3"; echo "main line" >> myco-notes/runbook.md; git commit -qam main
git merge -q side3 >/dev/null 2>&1
printf 'resolved\ntoken = %sABCDEFGHIJKL1234\n' "$(printf 'M%.0s' 1 2 3 4 5 6 7 8 9 10)" > myco-notes/runbook.md
git add -A; git commit -q --no-verify -m "merge with a secret in the resolution"
git rm -q -f myco-notes/runbook.md 2>/dev/null; git checkout -q "$base3" -- myco-notes/runbook.md; git commit -q -m "drop the secret"
chk "ci-check finds a secret added by a merge resolution" "out=\$(myco-notes/tools/ci-check $base3); [ \$? -ne 0 ] && echo \"\$out\" | grep -q 'runbook.md' && ! echo \"\$out\" | grep -q MMMM"
chk "ci-check fails when the base cannot be found" "out=\$(myco-notes/tools/ci-check 0123456789abcdef0123456789abcdef01234567); [ \$? -ne 0 ] && echo \"\$out\" | grep -q 'not found'"
chk "a first push (zero base) scans the whole history" "! myco-notes/tools/ci-check 0000000000000000000000000000000000000000"
git switch -q main; git branch -q -D side3 feat-merge
git worktree add -q "$tmp/wt" -b wt-branch >/dev/null 2>&1
chk "a linked worktree is not copied into a mirror" "(cd $tmp/wt && sed -i.bak 's|^MIRROR_TARGET=.*|MIRROR_TARGET=\"$tmp/wtmir\"|' .myco-notes.conf && rm -f .myco-notes.conf.bak && out=\$(myco-notes/tools/mirror-push 2>&1); [ \$? = 1 ] && echo \"\$out\" | grep -q 'worktree') && [ ! -e $tmp/wtmir ]"
git worktree remove --force "$tmp/wt"; git branch -q -D wt-branch
printf 'def broken(:\n' > broken_unrelated.py; git add broken_unrelated.py
echo "- scoped" >> myco-notes/plans/backlog.md
chk "--only ignores an unrelated staged file with a syntax error" "myco-notes/tools/notes-commit --only myco-notes/plans/backlog.md 'Scoped commit' >/dev/null && git show --name-only --format= HEAD | grep -qx myco-notes/plans/backlog.md && git diff --cached --name-only | grep -qx broken_unrelated.py"
git rm -q --cached broken_unrelated.py; rm -f broken_unrelated.py
setmirror "git:$tmp/nowhere.git"; echo "- p test" >> myco-notes/plans/backlog.md
chk "notes-commit -p exits 4 when a strict mirror is skipped" "MS=1; sed -i.bak 's|^MIRROR_STRICT=.*|MIRROR_STRICT=1|' .myco-notes.conf; rm -f .myco-notes.conf.bak; myco-notes/tools/notes-commit -p --only myco-notes/plans/backlog.md 'P test' >/dev/null 2>&1; [ \$? = 4 ]"
git checkout -q -- .myco-notes.conf
if command -v rsync >/dev/null 2>&1; then
  mkdir -p "$tmp/fakebin"; printf '#!/bin/sh\nwhile [ $# -gt 0 ]; do case "$1" in -o|-l|-p) shift 2;; -*) shift;; *) break;; esac; done\nshift\nexec sh -c "$*"\n' > "$tmp/fakebin/ssh"; chmod +x "$tmp/fakebin/ssh"
  mkdir -p "$tmp/rforeign"; echo x > "$tmp/rforeign/x"
  setmirror "fakehost:$tmp/rforeign"
  chk "an ssh target that is not its mirror is refused before rsync" "out=\$(PATH=$tmp/fakebin:\$PATH myco-notes/tools/mirror-push 2>&1); [ \$? = 1 ] && echo \"\$out\" | grep -q 'not a mirror' && [ -f $tmp/rforeign/x ]"
  setmirror "fakehost:$tmp/rmir"
  chk "an ssh target that is new gets synced and marked" "PATH=$tmp/fakebin:\$PATH myco-notes/tools/mirror-push | grep -q 'mirror: synced' && [ -f $tmp/rmir/.myco-mirror ] && [ -d $tmp/rmir/.git ]"
  git checkout -q -- .myco-notes.conf
fi

echo "flat layout and relocate (older trees keep working; relocate moves them)"
"$kit/tools/bootstrap" "$tmp/flat" --name "Old" --tz "UTC" --layout flat >/dev/null 2>&1
chk "flat tree has notes/ tools/ docs/ at the root" "[ -d $tmp/flat/notes ] && [ -d $tmp/flat/tools ] && [ -d $tmp/flat/docs ] && [ \"\$(git -C $tmp/flat config core.hooksPath)\" = tools/hooks ]"
chk "flat lint and map work"             "(cd $tmp/flat && tools/notes-lint.py >/dev/null; [ \$? -le 1 ] && python3 tools/build-notes-map.py && [ -f notes-map/index.html ])"
rm -rf "$tmp/flat/notes-map"
chk "relocate dry run changes nothing"   "\"$kit/tools/relocate\" --root $tmp/flat | grep -q 'dry run' && [ -d $tmp/flat/notes ]"
chk "relocate --apply moves the tree"    "\"$kit/tools/relocate\" --root $tmp/flat --apply >/dev/null && [ -f $tmp/flat/myco-notes/state.md ] && [ ! -e $tmp/flat/notes ] && [ \"\$(git -C $tmp/flat config core.hooksPath)\" = myco-notes/tools/hooks ]"
chk "moved tree: lint clean and commit works" "(cd $tmp/flat && myco-notes/tools/notes-lint.py --quiet | grep -q ' 0 warnings' && myco-notes/tools/notes-commit 'Moved to the single folder layout' | grep -q 'Moved to')"

echo "demo tree (README screenshots and the live demo)"
chk "build_demo makes the tree, its map and the mycelium view" "python3 $repo/examples/demo/build_demo.py $tmp/demo | grep -q 'graph: 30 nodes' && [ -f $tmp/demo/myco-notes/map/graph.html ] && [ \"\$(git -C $tmp/demo rev-list --count HEAD)\" -ge 20 ]"
chk "the demo tree is lint-clean apart from its two staged warnings" "(cd $tmp/demo && myco-notes/tools/notes-lint.py --quiet | grep -q ' 0 errors, 2 warnings')"

chk "no .gitattributes in the kit rewrites file contents (the plugin directory refuses it)" "! git -C $repo ls-files -z '*.gitattributes' '.gitattributes' | xargs -0 -I{} grep -h -v '^#' $repo/{} | grep -q -E 'eol=|filter|export-|(^| )text( |=|$)'"
chk ".cmd launchers are stored with CRLF and shell launchers with LF" "git -C $repo ls-files --eol -- skills/myco-notes/tools | awk '/\\.cmd\$/{if(\$1!=\"i/crlf\")bad=1;next} \$1==\"i/crlf\"{bad=1} END{exit bad}'"
chk "bootstrap gives a new tree the normalising .gitattributes" "grep -q 'eol=lf' myco-notes/../.gitattributes 2>/dev/null || grep -q 'eol=lf' $tmp/demo/.gitattributes"

echo; echo "passed $pass, failed $fail"; [ "$fail" = 0 ]
