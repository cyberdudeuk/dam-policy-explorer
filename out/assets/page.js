/* What the pages do when JavaScript is available. Everything you can read works without it. */
(function () {
  'use strict';
  var d = document;
  function $(s, r) { return (r || d).querySelector(s); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }

  // Printing shows every hidden section, then puts them back.
  var closed = [];
  window.addEventListener('beforeprint', function () { closed = [].slice.call(d.querySelectorAll('details:not([open])')); closed.forEach(function (x) { x.open = true; }); });
  window.addEventListener('afterprint', function () { closed.forEach(function (x) { x.open = false; }); closed = []; });

  // Opening a link to something inside a closed section opens the section.
  function reveal() { var id = decodeURIComponent(location.hash.slice(1)); if (!id) return; var el = d.getElementById(id); if (!el) return; var own = el.querySelector(':scope > details'); if (own) own.open = true; var p = el.closest('details'); while (p) { p.open = true; p = p.parentElement.closest('details'); } }
  window.addEventListener('hashchange', reveal); reveal();

  var KIND = {fix: 'Must fix', ask: 'We will ask', gap: 'Policy gap', tip: 'Tip'};
  var EXAMPLE = [   // invented rows in the version 3 layout. "(list value)" stands for an answer chosen from the workbook's own list, which we do not have
    'Unique identifier,Data asset name,Description,Owning department / publisher,ALB / agency,Source / provenance,Data owner assigned?,Data steward assigned?,Stewardship model,Critical purpose number(s),Primary sharing status,Legal gateway / regulatory basis,Security classification / marking,Contains personal data?,Source-asset access rights,Primary licence / usage basis,Asset version / update status,Metadata recorded in catalogue?,Catalogue / metadata reference,DQ assurance / action plan status,Quality evidence reference,Discoverability / interoperability status,Geospatial standard applied,Previous ESDA return reference',
    'EX-0001,Fishing vessel licences (invented),"An invented example: every fishing vessel licence, with its class and dates.",Example Department,Example Agency,Collected from licence applications,Yes,Yes,Central,"1, 2",(list value),Example Act 2020 section 4,OFFICIAL-SENSITIVE,Yes,(list value),(list value),Version 3 (monthly),In catalogue,CAT-123,(list value),QE-9,(list value),UPRN,',
    'EX-0002,Fishing vessel licences (invented copy),An invented example: a near copy of the row above with two policy gaps.,Example Department,Example Agency,,No,Yes,,1,(list value),,OFFICIAL,No,(list value),(list value),,Not in catalogue,,(list value),,,Not applicable,',
    'EX-0003,QVKA vehicle keeper extract (invented),An invented example with mistakes to fix.,Example Department,,,Yes,Maybe,,"1, 9",Out of scope,,SECRET,No,(list value),,,In catalogue,,(list value),,,"UPRN, Not applicable",',
    'ex-0001,Harbour fees ledger (invented),An invented example: an identifier used twice and an address that should not be there (fees@example.invalid).,Example Department,,,Yes,Yes,,4,(list value),,OFFICIAL,No,(list value),(list value),,Planned,,(list value),,(list value),Not applicable,'
  ].join('\r\n');

  function readFile(input) {
    return new Promise(function (ok) {
      var f = input && input.files && input.files[0]; if (!f) return ok(null);
      var r = new FileReader(); r.onload = function () { ok({name: f.name, text: String(r.result)}); }; r.onerror = function () { ok(null); }; r.readAsText(f);
    });
  }

  function show(box, res, name) {
    var c = res.counts, h = '';
    var head = {ready: ['Ready to send', 'Every row meets the checks.'],
      'ready-with-gaps': ['You can send it', 'Policy gaps are accepted: they show us where to help. Anything marked "We will ask" will come back to you as a question.'],
      'not-ready': ['Not ready to send yet', 'Fix everything marked "Must fix", save the file again and check it again.']}[res.verdict];
    h += '<div class="verdict ' + res.verdict + '"><h3>' + head[0] + '</h3><p>' + head[1] + '</p><p class="small">' + esc(name) + ': ' +
      plural(c.records, 'row', 'rows') + ' checked: ' + c.ready + ' ready, ' + c.gap + ' with policy gaps only, ' + c.ask + ' with questions only, ' + c.fix + ' with something to fix. ' + plural(c.questions, 'question', 'questions') + ' we will ask.' + (c.excluded ? ' ' + plural(c.excluded, 'asset', 'assets') + ' left out.' : '') + '</p></div>';
    if (res.file.length) h += '<h3>About the file as a whole</h3><ul class="issues">' + res.file.map(function (x) { return '<li><span class="kind ' + x.kind + '">' + KIND[x.kind] + '</span>' + esc(x.text) + '</li>'; }).join('') + '</ul>';
    var rows = res.rows.filter(function (r) { return r.issues.length; });
    if (rows.length) {
      h += '<h3>Row by row</h3>';
      rows.forEach(function (r) {
        h += '<h4 class="small">Row ' + r.line + (r.title ? ': ' + esc(r.title) : '') + '</h4><ul class="issues">' + r.issues.map(function (x) { return '<li><span class="kind ' + x.kind + '">' + KIND[x.kind] + '</span>' + esc(x.text) + '</li>'; }).join('') + '</ul>';
      });
    }
    if (res.exclusions.length) h += '<h3>Assets you left out</h3><ul class="issues">' + res.exclusions.map(function (x) { return '<li><span class="kind ' + x.kind + '">' + KIND[x.kind] + '</span>Row ' + x.line + (x.title ? ' (' + esc(x.title) + ')' : '') + ': ' + esc(x.text) + '</li>'; }).join('') + '</ul>';
    box.innerHTML = h;
    var v = box.querySelector('.verdict'); if (v) { v.setAttribute('tabindex', '-1'); v.focus(); }
  }

  // The file check: the same on both pages.
  [].forEach.call(d.querySelectorAll('[data-checker]'), function (root) {
    var file = $('[data-return]', root), excl = $('[data-exclusions]', root), out = $('[data-result]', root), example = $('[data-example]', root), run = $('[data-run]', root);
    root.hidden = false; var nojs = d.getElementById(root.getAttribute('data-checker') + '-nojs'); if (nojs) nojs.hidden = true;
    var last = null;
    function go() {
      Promise.all([readFile(file), readFile(excl)]).then(function (f) {
        if (!file.files || !file.files[0]) { out.innerHTML = '<p role="alert">Choose the return file first, using the “Choose file” button above.</p>'; file.focus(); return; }
        if (!f[0]) { out.innerHTML = '<p role="alert">The file could not be opened. Check it is a CSV file and try again. If it still will not open, <a href="' + (d.body.getAttribute('data-contact') || '#') + '">use our contact form</a> and we will help.</p>'; file.focus(); return; }
        last = {res: DAMChecker.check(f[0].text, f[1] && f[1].text), name: f[0].name}; show(out, last.res, last.name); root.dispatchEvent(new CustomEvent('checked', {detail: last}));
      });
    }
    run.addEventListener('click', go);
    example.addEventListener('click', function () { last = {res: DAMChecker.check(EXAMPLE), name: 'Example file (invented)'}; show(out, last.res, last.name); root.dispatchEvent(new CustomEvent('checked', {detail: last})); });
  });

  // Team page: write a query email from the check.
  var q = d.getElementById('team-check');
  if (q) {
    var btn = $('[data-query]'), qout = $('[data-query-out]'), copy = $('[data-query-copy]'), LAST = null;
    q.addEventListener('checked', function (ev) { LAST = ev.detail; btn.disabled = false; });
    btn.addEventListener('click', function () {
      if (!LAST) return; var r = LAST.res, fix = [], fill = [], gaps = [];
      function put(x, where) { (x.kind === 'fix' ? fix : x.kind === 'ask' ? fill : x.kind === 'gap' ? gaps : []).push('- ' + where + x.text); }
      r.file.forEach(function (x) { put(x, ''); });
      r.rows.forEach(function (row) { row.issues.forEach(function (x) { put(x, 'Row ' + row.line + (row.identifier ? ' (' + row.identifier + ')' : '') + ': '); }); });
      r.exclusions.forEach(function (x) { put(x, 'Left out, row ' + x.line + (x.title ? ' (' + x.title + ')' : '') + ': '); });
      function list(a) { return a.slice(0, 40).join('\n') + (a.length > 40 ? '\n- and ' + (a.length - 40) + ' more of the same kinds' : ''); }
      var body = fix.length ? 'Before we can accept it, please change these and send the file again:\n\n' + list(fix) + (fill.length ? '\n\nWhile you are doing that, please also answer these:\n\n' + list(fill) : '')
        : fill.length ? 'We have accepted it. Please answer these when you can, all in one reply:\n\n' + list(fill) : 'Everything we check is in order. We have accepted your return.';
      if (gaps.length) body += '\n\nWe have recorded these policy gaps. They are not mistakes, and you do not need to change your return. They show us where to offer support:\n\n' + list(gaps);
      qout.textContent = 'Subject: Your data asset return' + (fix.length ? ': some changes needed' : ' has been accepted') + '\n\nThank you for your return (' + LAST.name + ').\n\n' + body +
        (fix.length || fill.length ? '\n\nYou can check your file yourself before you send it, in the "Is my list ready to send?" section of the "Make a return" page.' : '') +
        '\n\nThank you,\nGDS team';
      qout.hidden = false; copy.hidden = false; qout.focus();
    });
    copy.addEventListener('click', function () { copyText(qout, copy); });
  }

  // Team page: the reply builder follows the answer standard.
  var rf = d.getElementById('reply-form');
  if (rf) {
    var rout = $('[data-reply-out]'), rcopy = $('[data-reply-copy]');
    function build() {
      var g = function (n) { return (rf.elements[n].value || '').trim(); }, st = rf.elements.sure, sure = st.options[st.selectedIndex].text;
      rout.textContent = (g('answer') || '[The answer, in one or two sentences]') + '\n\n' +
        'Where this comes from: ' + (g('source') || '[the document and the part of it, for example: Identifying and recording critical data assets, section 3]') + '.\n' +
        'How sure we are: ' + (st.value ? sure : '[choose how sure you are]') + '.' +
        (g('other') ? '\n\nThere is another way to read this: ' + g('other') : '') +
        (g('record') ? '\n\nPlease note in your return: ' + g('record') : '') +
        '\n\nWe will add this answer to our published answers, so others with the same question can find it.\n\nGDS team';
      var warn = $('[data-reply-warn]'), need = !!(st.value && st.value !== 'published' && st.value !== 'agreed');
      if (warn.hasAttribute('data-shown') !== need) { warn.textContent = need ? 'This is not published guidance or an agreed decision. Ask another team member to check it before you send it.' : ''; if (need) warn.setAttribute('data-shown', ''); else warn.removeAttribute('data-shown'); }
    }
    rf.addEventListener('input', build); rf.addEventListener('change', build); build();
    rcopy.addEventListener('click', function () { copyText(rout, rcopy); });
  }

  function copyText(el, b) {
    var t = el.textContent, label = b.textContent;
    var say = d.getElementById('announce');
    function done(msg) { b.textContent = msg; if (say) { say.textContent = ''; setTimeout(function () { say.textContent = msg; }, 50); } setTimeout(function () { b.textContent = label; }, 2500); }
    function select() { var r = d.createRange(); r.selectNodeContents(el); var s = getSelection(); s.removeAllRanges(); s.addRange(r); done('Text selected: press Ctrl+C (or Cmd+C) to copy'); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(function () { done('Copied'); }, select); else select();
  }
})();

/* ---------- tooltips: on hover and keyboard focus, dismissed with Escape, and you can move onto them (WCAG 1.4.13) ---------- */
(function () {
  'use strict';
  var d = document, tip = d.createElement('div'), owner = null, hideT = null, pinned = false;
  tip.id = 'tip'; tip.setAttribute('role', 'tooltip'); tip.className = 'tooltip'; tip.hidden = true; d.body.appendChild(tip);
  function place(el) {
    var r = el.getBoundingClientRect(), t = tip.getBoundingClientRect(), x = r.left + r.width / 2 - t.width / 2, y = r.top - t.height - 10, below = false;
    if (y < 8) { y = r.bottom + 10; below = true; }
    x = Math.max(8, Math.min(x, d.documentElement.clientWidth - t.width - 8));
    tip.style.left = (x + window.scrollX) + 'px'; tip.style.top = (y + window.scrollY) + 'px'; tip.classList.toggle('below', below);
  }
  function show(el) {
    clearTimeout(hideT); if (owner && owner !== el) owner.removeAttribute('aria-describedby');
    owner = el; tip.textContent = el.getAttribute('data-tip'); tip.hidden = false; el.setAttribute('aria-describedby', 'tip'); place(el);
  }
  function hide(now) { var f = function () { tip.hidden = true; pinned = false; if (owner) { owner.removeAttribute('aria-describedby'); owner.removeAttribute('aria-expanded'); } owner = null; }; clearTimeout(hideT); if (now) f(); else hideT = setTimeout(f, 250); }
  d.addEventListener('mouseover', function (ev) { var el = ev.target.closest && ev.target.closest('[data-tip]'); if (el) show(el); else if (ev.target === tip || tip.contains(ev.target)) clearTimeout(hideT); });
  d.addEventListener('mouseout', function (ev) { var el = ev.target.closest && ev.target.closest('[data-tip]'); if ((el || ev.target === tip) && !pinned) hide(); });
  d.addEventListener('focusin', function (ev) { var el = ev.target.closest && ev.target.closest('[data-tip]:not([data-tip-mouse])'); if (el) show(el); else if (!pinned) hide(true); });
  d.addEventListener('focusout', function (ev) { if (ev.target.closest && ev.target.closest('[data-tip]') && !pinned) hide(); });
  d.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && !tip.hidden) { hide(true); } });
  d.addEventListener('click', function (ev) {                         // terms are buttons: a tap pins the explanation open (touch screens have no hover)
    var t = ev.target.closest && ev.target.closest('button.term');
    if (t) { if (pinned && owner === t) hide(true); else { show(t); pinned = true; t.setAttribute('aria-expanded', 'true'); } return; }
    if (pinned && !tip.contains(ev.target)) hide(true);
  });
  window.addEventListener('scroll', function () { if (owner && !tip.hidden) place(owner); }, {passive: true});
})();

/* ---------- the drawer: in-page navigation only, built from the page's own headings, with icons, counts and "new" flags ---------- */
(function () {
  'use strict';
  var d = document, heads = [].slice.call(d.querySelectorAll('main h2[id]'));
  if (heads.length < 3) return;
  var nav = d.createElement('nav'), btn = d.createElement('button');
  nav.className = 'drawer'; nav.id = 'drawer'; nav.setAttribute('aria-label', 'On this page'); nav.hidden = true;
  nav.innerHTML = '<div class="drawer-head"><p class="drawer-title">On this page</p><button type="button" class="drawer-close" data-drawer-close><svg class="ic" aria-hidden="true"><use href="#i-close"/></svg>Close</button></div><ol>' +
    heads.map(function (h) {
      var icon = h.getAttribute('data-icon') || 'i-list', n = h.getAttribute('data-count'), isNew = h.hasAttribute('data-new');
      return '<li><a href="#' + h.id + '"><svg class="ic" aria-hidden="true"><use href="#' + icon + '"/></svg><span>' + h.textContent.trim() + '</span>' +
        (isNew ? '<span class="flag">New</span>' : '') + (n ? '<span class="count" aria-label="' + n + ' items">' + n + '</span>' : '') + '</a></li>';
    }).join('') + '</ol>';
  btn.type = 'button'; btn.className = 'drawer-toggle'; btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'drawer');
  btn.innerHTML = '<span class="slide" aria-hidden="true"><span class="knob"></span></span><svg class="ic" aria-hidden="true"><use href="#i-menu"/></svg><span>On this page</span>';
  d.body.appendChild(nav); d.body.appendChild(btn);
  var wide = window.matchMedia('(min-width: 82rem)');
  function set(open, focus) {
    nav.hidden = !open; btn.setAttribute('aria-expanded', open ? 'true' : 'false'); d.body.classList.toggle('drawer-open', open && wide.matches);
    try { localStorage.setItem('dam-drawer', open ? '1' : '0'); } catch (e) {}
    if (open && focus) nav.querySelector('a').focus(); else if (!open && focus) btn.focus();
  }
  btn.addEventListener('click', function () { set(nav.hidden, true); });
  nav.addEventListener('click', function (ev) { if (ev.target.closest('[data-drawer-close]')) set(false, true); else if (ev.target.closest('a') && !wide.matches) set(false); });
  nav.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') set(false, true); });
  wide.addEventListener('change', function () { d.body.classList.toggle('drawer-open', !nav.hidden && wide.matches); });
  // which section you are in
  var links = [].slice.call(nav.querySelectorAll('a[href^="#"]'));
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) links.forEach(function (a) { if (a.getAttribute('href') === '#' + e.target.id) { links.forEach(function (x) { x.removeAttribute('aria-current'); }); a.setAttribute('aria-current', 'location'); } }); }); }, {rootMargin: '0px 0px -70% 0px'});
    heads.forEach(function (h) { io.observe(h); });
  }
  var saved = null; try { saved = localStorage.getItem('dam-drawer'); } catch (e) {}
  if (saved === '1' && wide.matches) set(true);
})();

/* copy the Mermaid source */
(function () { var b = document.querySelector('[data-mmd-copy]'), pre = document.querySelector('[data-mmd]'); if (!b || !pre) return;
  b.addEventListener('click', function () { var t = pre.textContent, say = document.getElementById('announce');
    function done(m) { b.textContent = m; if (say) { say.textContent = ''; setTimeout(function () { say.textContent = m; }, 50); } setTimeout(function () { b.textContent = 'Copy the Mermaid'; }, 2500); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(function () { done('Copied'); }, function () { done('Could not copy: select the text and copy it'); }); else done('Select the text and copy it'); }); })();

/* the 24 details: show only those that must be filled in, and so on */
(function () {
  var box = document.querySelector('[data-fields]'); if (!box) return;
  var bar = box.querySelector('.filter'), status = box.querySelector('[data-filter-status]'); bar.hidden = false;
  bar.addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-filter]'); if (!b) return; var k = b.getAttribute('data-filter'), n = 0;
    [].forEach.call(bar.querySelectorAll('button'), function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
    [].forEach.call(box.querySelectorAll('li[data-ob]'), function (li) { var on = !k || li.getAttribute('data-ob') === k; li.hidden = !on; if (on) n++; });
    [].forEach.call(box.querySelectorAll('.fgroup'), function (g) { g.hidden = !g.querySelector('li[data-ob]:not([hidden])'); });
    status.textContent = 'Showing ' + n + ' of 24 details.';
  });
})();
