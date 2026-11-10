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
chk "marketplace source resolves to the plugin root" "[ -f $kit/.claude-plugin/plugin.json ] && [ -d $skill ]"
chk "skill version equals plugin version" "python3 - <<PY
import json,re
v=json.load(open('$kit/.claude-plugin/plugin.json'))['version']
t=open('$skill/SKILL.md').read().split('---')[1]
assert re.search(r'version:\s*\"?'+re.escape(v)+r'\"?\s*\$', t, re.M), 'SKILL.md metadata.version differs from plugin.json'
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
chk "mirror push"                       "myco-notes/tools/mirror-push | grep -q 'mirror: pushed'"
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

echo; echo "passed $pass, failed $fail"; [ "$fail" = 0 ]
