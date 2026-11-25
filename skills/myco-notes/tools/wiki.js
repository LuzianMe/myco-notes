/* The wiki layout's script (map_wiki.py): the tree and its filter, the search across the notes' text, the menu on a phone, the outline's
   current heading. No network: the data comes from nav.js (the tree) and search.js (loaded when someone searches). */
(function () {
  'use strict';
  var B = document.body, base = B.getAttribute('data-base') || '', cur = B.getAttribute('data-cur') || '';
  var NAV = window.MYCO_NAV || { groups: [] };
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function say(id, text) { var s = document.getElementById(id); if (s) s.textContent = text; }

  /* ---- the tree ---- */
  var side = document.getElementById('sidebar'), tree = document.getElementById('tree'), filt = document.getElementById('filter');
  function words(q) { return q.toLowerCase().split(/\s+/).filter(Boolean); }
  function buildTree(q) {
    var ts = words(q), total = 0;
    tree.textContent = '';
    NAV.groups.forEach(function (g) {
      var items = g.notes.filter(function (n) {
        if (!ts.length) return true;
        var s = (n.t + ' ' + n.n + ' ' + n.h).toLowerCase();
        return ts.every(function (t) { return s.indexOf(t) >= 0; });
      });
      if (!items.length) return;
      total += items.length;
      var d = el('details', 'tg'), ul = el('ul');
      d.open = ts.length > 0 || items.some(function (n) { return n.i === cur; });
      d.setAttribute('data-g', g.id);
      d.appendChild(el('summary', null, g.name + ' (' + items.length + ')'));
      items.forEach(function (n) {
        var li = el('li'), a = el('a', n.a ? 'att' : ''), t = el('span', 't', n.t);
        a.appendChild(t);
        a.href = base + 'p/' + n.i + '.html';
        a.title = n.n + (n.h ? ' - ' + n.h : '');
        if (n.i === cur) a.setAttribute('aria-current', 'page');
        if (n.a) { var sr = el('span', 'sr', ' (needs a look)'); a.appendChild(sr); }
        li.appendChild(a); ul.appendChild(li);
      });
      d.appendChild(ul); tree.appendChild(d);
    });
    if (!total) tree.appendChild(el('p', 'empty', 'No note matches.'));
    say('tree-status', ts.length ? total + (total === 1 ? ' note matches' : ' notes match') : '');
  }
  buildTree('');
  var here = tree.querySelector('[aria-current]');
  if (here && side) { side.scrollTop = Math.max(0, here.getBoundingClientRect().top - side.getBoundingClientRect().top + side.scrollTop - side.clientHeight / 3); }
  if (filt) {
    filt.addEventListener('input', function () { buildTree(filt.value); });
    filt.addEventListener('keydown', function (e) { if (e.key === 'Escape' && filt.value) { filt.value = ''; buildTree(''); e.stopPropagation(); } });
  }

  /* ---- the menu on a phone ---- */
  var menu = document.getElementById('menu'), scrim = document.getElementById('scrim');
  function setMenu(open) {
    B.classList.toggle('menu-open', open);
    if (menu) menu.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open && filt) filt.focus(); else if (!open && menu && document.activeElement && side && side.contains(document.activeElement)) menu.focus();
  }
  if (menu) menu.addEventListener('click', function () { setMenu(!B.classList.contains('menu-open')); });
  if (scrim) scrim.addEventListener('click', function () { setMenu(false); });
  if (window.matchMedia) { var mq = window.matchMedia('(min-width:861px)'); (mq.addEventListener ? mq.addEventListener('change', function () { setMenu(false); }) : mq.addListener(function () { setMenu(false); })); }

  /* ---- search across the text of the notes ---- */
  var box = document.getElementById('gsearch'), res = document.getElementById('results'), DB = null, waiting = null, active = -1, shown = [];
  function load(done) {
    if (DB) { done(); return; }
    if (waiting) { waiting.push(done); return; }
    waiting = [done];
    var s = document.createElement('script');
    s.src = base + 'assets/search.js';
    s.onload = function () {
      DB = (window.MYCO_SEARCH || []).map(function (r) { r.lt = r.t.toLowerCase(); r.lr = r.r.toLowerCase(); r.lh = (r.h || '').toLowerCase(); r.ls = (r.s || '').toLowerCase(); r.lx = r.x.toLowerCase(); return r; });
      var w = waiting; waiting = null; w.forEach(function (f) { f(); });
    };
    s.onerror = function () { waiting = null; showMessage('The search index could not be loaded.'); };
    document.head.appendChild(s);
  }
  function terms(q) { var out = []; q.replace(/"([^"]+)"|(\S+)/g, function (_, a, b) { out.push((a || b).toLowerCase()); return ''; }); return out; }
  function count(hay, t, cap) { var n = 0, i = -1; while (n < cap && (i = hay.indexOf(t, i + 1)) >= 0) n++; return n; }
  function score(r, ts) {
    var sc = 0;
    for (var k = 0; k < ts.length; k++) {
      var t = ts[k], inT = r.lt.indexOf(t) >= 0, inR = r.lr.indexOf(t) >= 0, inH = r.lh.indexOf(t) >= 0, inS = r.ls.indexOf(t) >= 0, n = count(r.lx, t, 12);
      if (!inT && !inR && !inH && !inS && !n) return 0;
      sc += (inT ? 30 : 0) + (inR ? 12 : 0) + (inS ? 10 : 0) + (inH ? 8 : 0) + n;
    }
    return sc;
  }
  function marked(parent, text, ts) {
    var low = text.toLowerCase(), pos = 0;
    while (pos < text.length) {
      var best = -1, len = 0;
      ts.forEach(function (t) { var i = low.indexOf(t, pos); if (i >= 0 && (best < 0 || i < best)) { best = i; len = t.length; } });
      if (best < 0) break;
      if (best > pos) parent.appendChild(document.createTextNode(text.slice(pos, best)));
      parent.appendChild(el('mark', null, text.slice(best, best + len)));
      pos = best + len;
    }
    if (pos < text.length) parent.appendChild(document.createTextNode(text.slice(pos)));
  }
  function snippet(r, ts) {
    var at = -1;
    for (var k = 0; k < ts.length && at < 0; k++) at = r.lx.indexOf(ts[k]);
    if (at < 0) return r.h || '';
    var from = Math.max(0, at - 60), to = Math.min(r.x.length, at + 120);
    return (from ? '... ' : '') + r.x.slice(from, to) + (to < r.x.length ? ' ...' : '');
  }
  function closeResults() { if (!res) return; res.hidden = true; res.textContent = ''; box.setAttribute('aria-expanded', 'false'); box.removeAttribute('aria-activedescendant'); active = -1; shown = []; }
  function showMessage(msg) { res.textContent = ''; res.appendChild(el('li', 'none', msg)); res.hidden = false; box.setAttribute('aria-expanded', 'true'); say('results-status', msg); }
  function setActive(i) {
    var items = res.querySelectorAll('li[role=option]');
    if (!items.length) return;
    active = (i + items.length) % items.length;
    items.forEach(function (li, k) { li.setAttribute('aria-selected', k === active ? 'true' : 'false'); });
    box.setAttribute('aria-activedescendant', items[active].id);
    items[active].scrollIntoView({ block: 'nearest' });
  }
  function run() {
    var q = box.value.trim();
    if (!q) { closeResults(); return; }
    showMessage('Searching...');
    load(function () {
      if (box.value.trim() !== q) return;
      var ts = terms(q), hits = [];
      DB.forEach(function (r) { var s = score(r, ts); if (s) hits.push([s, r]); });
      hits.sort(function (a, b) { return b[0] - a[0] || (a[1].t < b[1].t ? -1 : 1); });
      if (!hits.length) { showMessage('No note contains ' + q + '.'); return; }
      res.textContent = ''; shown = hits.slice(0, 12);
      shown.forEach(function (h, i) {
        var r = h[1], li = el('li'), a = el('a');
        li.id = 'r' + i; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
        a.href = base + 'p/' + r.i + '.html';
        a.appendChild(el('span', 'rt', r.t));
        a.appendChild(el('span', 'rg', r.g + ' - ' + r.r));
        var x = el('span', 'rx'); marked(x, snippet(r, ts), ts); a.appendChild(x);
        li.appendChild(a); res.appendChild(li);
      });
      res.hidden = false; box.setAttribute('aria-expanded', 'true'); active = -1;
      say('results-status', hits.length + (hits.length === 1 ? ' note' : ' notes') + (hits.length > 12 ? ', showing the first 12' : ''));
    });
  }
  if (box) {
    var timer = null;
    box.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 90); });
    box.addEventListener('focus', function () { load(function () {}); if (box.value.trim() && res.hidden) run(); });
    box.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); if (res.hidden) run(); else setActive(active + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(active - 1); }
      else if (e.key === 'Enter') { var a = res.querySelector('li[role=option][aria-selected=true] a') || res.querySelector('li[role=option] a'); if (a) { e.preventDefault(); location.href = a.href; } }
      else if (e.key === 'Escape') { if (!res.hidden) { closeResults(); e.stopPropagation(); } else if (box.value) box.value = ''; }
    });
    document.addEventListener('click', function (e) { if (!box.parentNode.contains(e.target)) closeResults(); });
  }
  document.addEventListener('keydown', function (e) {
    var t = e.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
    if (e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey && box) { e.preventDefault(); box.focus(); box.select(); }
    else if (e.key === 'Escape' && B.classList.contains('menu-open')) setMenu(false);
  });

  /* ---- the outline: mark the heading being read ---- */
  var links = [].slice.call(document.querySelectorAll('#outline .toc a')), heads = [];
  links.forEach(function (a) { var h = document.getElementById(decodeURIComponent((a.getAttribute('href') || '').slice(1))); if (h) heads.push([h, a]); });
  if (heads.length) {
    var ticking = false, on = null, out = document.getElementById('outline');
    function spy() {
      ticking = false;
      var pick = heads[0][1], line = 90;
      heads.forEach(function (p) { if (p[0].getBoundingClientRect().top <= line) pick = p[1]; });
      if (pick === on) return;
      if (on) { on.classList.remove('active'); on.removeAttribute('aria-current'); }
      pick.classList.add('active'); pick.setAttribute('aria-current', 'location'); on = pick;
      if (out && pick.getBoundingClientRect().bottom > out.clientHeight + out.getBoundingClientRect().top - 10) out.scrollTop += 60;
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(spy); } }, { passive: true });
    spy();
  }
})();
