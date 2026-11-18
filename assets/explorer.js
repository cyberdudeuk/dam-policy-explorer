/* DAM Policy Explorer: what the pages do when JavaScript is available.
   Everything you can read works without it. Nothing is sent anywhere: the only storage is this browser's own. */
(function () {
  'use strict';
  var d = document, root = d.documentElement, body = d.body;
  var $ = function (s, r) { return (r || d).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || d).querySelectorAll(s)); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function announce(t) { var a = $('#announce'); if (a) { a.textContent = ''; setTimeout(function () { a.textContent = t; }, 50); } }

  // Storage that never throws: some browsers and Teams contexts block it, and the app must still work.
  var store = {
    get: function (k, dflt) { try { var v = localStorage.getItem('dpe.' + k); return v == null ? dflt : JSON.parse(v); } catch (e) { return dflt; } },
    set: function (k, v) { try { localStorage.setItem('dpe.' + k, JSON.stringify(v)); return true; } catch (e) { return false; } },
    del: function (k) { try { localStorage.removeItem('dpe.' + k); } catch (e) { /* nothing stored */ } }
  };
  var ALLOWED = {theme: ['auto', 'light', 'dark', 'contrast'], text: ['normal', 'large', 'xlarge']};   // allowlist: stored values are checked before use

  // ---- display settings, and the Teams theme ----
  function teamsTheme() {
    var m = /[?&]theme=(default|dark|contrast)\b/.exec(location.search);
    return m ? ({'default': 'light', dark: 'dark', contrast: 'contrast'})[m[1]] : null;
  }
  function prefs() {
    var p = store.get('prefs', {}) || {};
    return {theme: ALLOWED.theme.indexOf(p.theme) >= 0 ? p.theme : 'auto', text: ALLOWED.text.indexOf(p.text) >= 0 ? p.text : 'normal',
      spacing: p.spacing === true, motion: p.motion === true, underline: p.underline === true};
  }
  function apply(p) {
    var t = p.theme === 'auto' ? (teamsTheme() || 'auto') : p.theme;
    if (t === 'auto') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', t);
    root.setAttribute('data-text', p.text);
    root.toggleAttribute('data-spacing', p.spacing);
    root.toggleAttribute('data-reduce-motion', p.motion);
    root.toggleAttribute('data-underline', p.underline);
  }
  var P = prefs(); apply(P);
  var panel = $('#settings'), sbtn = $('.settings-btn');
  if (panel && sbtn) {
    sbtn.hidden = false;
    $$('input', panel).forEach(function (i) {
      if (i.type === 'radio') i.checked = P[i.name] === i.value; else i.checked = !!P[i.name];
      i.addEventListener('change', function () {
        P[i.name] = i.type === 'radio' ? i.value : i.checked; store.set('prefs', P); apply(P); announce('Display setting saved.');
      });
    });
    sbtn.addEventListener('click', function () { var open = panel.hidden; panel.hidden = !open; sbtn.setAttribute('aria-expanded', String(open)); if (open) $('input', panel).focus(); });
    $('[data-reset]', panel).addEventListener('click', function () {
      store.del('prefs'); P = prefs(); apply(P);
      $$('input', panel).forEach(function (i) { i.checked = i.type === 'radio' ? P[i.name] === i.value : false; });
      announce('Display settings reset to standard.');
    });
    if (location.hash === '#settings') { panel.hidden = false; sbtn.setAttribute('aria-expanded', 'true'); }
  }
  function motionOff() { return root.hasAttribute('data-reduce-motion') || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches); }

  // ---- main menu folds behind a button on narrow screens, so it never runs off the screen ----
  var nav = $('#site-nav'), mbtn = $('.menu-btn');
  if (nav && mbtn) {
    var mq = matchMedia('(max-width: 62rem)');   // folds before the menu would wrap onto a second row
    var sync = function () { var narrow = mq.matches; mbtn.hidden = !narrow; if (narrow) { nav.classList.add('folded'); mbtn.setAttribute('aria-expanded', 'false'); } else nav.classList.remove('folded', 'open'); };
    mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync); sync();
    mbtn.addEventListener('click', function () { var open = !nav.classList.contains('open'); nav.classList.toggle('open', open); mbtn.setAttribute('aria-expanded', String(open)); });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('open')) { nav.classList.remove('open'); mbtn.setAttribute('aria-expanded', 'false'); mbtn.focus(); } });
  }

  // ---- "On this page" becomes a retractable drawer, with a labelled switch; choice remembered ----
  var toc = $('[data-drawer]');
  if (toc) {
    var sw = d.createElement('button'); sw.type = 'button'; sw.className = 'drawer-switch'; sw.setAttribute('role', 'switch');
    sw.innerHTML = '<span class="track" aria-hidden="true"><span class="knob"></span></span><span>Page contents</span>';
    // D-12: on narrow screens the contents list pushed the page's main content down; it starts closed there unless the person opened it
    var saved = store.get('drawer', null), shown = saved === null ? !matchMedia('(max-width: 52rem)').matches : saved !== false;
    var setD = function (on) { toc.classList.toggle('closed', !on); sw.setAttribute('aria-checked', String(on)); d.body.classList.toggle('drawer-closed', !on); };
    setD(shown);
    sw.addEventListener('click', function () { shown = !shown; setD(shown); store.set('drawer', shown); });
    toc.parentNode.insertBefore(sw, toc);
    // flag sections that are new since this browser last visited
    var seen = store.get('seen.' + location.pathname.split('/').pop(), null), ver = body.getAttribute('data-version');
    if (seen && seen !== ver) $$('a', toc).forEach(function (a) { var h = d.getElementById(a.getAttribute('href').slice(1)); if (h && h.hasAttribute('data-new')) a.insertAdjacentHTML('beforeend', ' <span class="new">New</span>'); });
    store.set('seen.' + location.pathname.split('/').pop(), ver);
    // highlight where you are
    if ('IntersectionObserver' in window) {
      var links = {}; $$('a', toc).forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
      var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting && links[e.target.id]) { $$('a', toc).forEach(function (x) { x.removeAttribute('aria-current'); }); links[e.target.id].setAttribute('aria-current', 'location'); } }); }, {rootMargin: '0px 0px -70% 0px'});
      Object.keys(links).forEach(function (id) { var h = d.getElementById(id); if (h) io.observe(h); });
    }
  }

  // ---- glossary words show their meaning on hover and on focus; Escape hides it (WCAG 1.4.13) ----
  var tip = d.createElement('div'); tip.className = 'tooltip'; tip.id = 'term-tip'; tip.setAttribute('role', 'tooltip'); tip.hidden = true; body.appendChild(tip);
  var tipFor = null;
  function showTip(a) { return showAny(a);
    tip.textContent = a.getAttribute('data-def'); tip.hidden = false; tipFor = a; a.setAttribute('aria-describedby', 'term-tip');
    var r = a.getBoundingClientRect(), w = Math.min(320, innerWidth - 16);
    tip.style.maxWidth = w + 'px';
    var left = Math.max(8, Math.min(r.left + scrollX, scrollX + innerWidth - w - 8));
    tip.style.left = left + 'px'; tip.style.top = (r.bottom + scrollY + 6) + 'px';
  }
  function hideTip() { if (tipFor) tipFor.removeAttribute('aria-describedby'); tip.hidden = true; tipFor = null; }
  // Tooltips everywhere: glossary words, navigation, buttons, labels and badges. Each shows on hover and on keyboard focus,
  // and Escape hides it (WCAG 1.4.13). Native title attributes are moved into data-tip, so nothing shows twice.
  var NAVTIP = {'index.html': 'Start here: your path, your progress and routes by role', 'policy.html': 'What the policy asks, who it applies to and who does what',
    'return.html': 'The twelve steps of the return, with your progress saved', 'asset-test.html': 'Check whether a possible asset is in scope',
    'track.html': 'Track where your return has got to, and analyse what you sent', 'questions.html': 'Answers to the questions coordinators asked, with sources',
    'people.html': 'Roles, user stories and journeys', 'capabilities.html': 'The 32 capabilities behind the policy, with playbooks',
    'guide.html': 'How to use the explorer, tours, tutorials and how to set it up', 'resources.html': 'Guidance, templates and tools in one list',
    'ask.html': 'Ask a question in your own words', 'embed.html': 'Make the policy part of business as usual and change',
    'glossary.html': 'What the words mean', 'team.html': 'How GDS processes returns', 'about.html': 'Why it exists, how it was made, privacy and roadmap',
    'accessibility.html': 'Accessibility and inclusion statement'};
  $$('.xnav a').forEach(function (a) { var k = (a.getAttribute('href') || '').split('#')[0]; if (NAVTIP[k] && !a.hasAttribute('data-tip')) a.setAttribute('data-tip', NAVTIP[k]); });
  var AUTOTIP = [['.menu-btn', 'Show or hide the menu'], ['.settings-btn', 'Colours, text size, spacing and animation'], ['.hs-btn', 'Search the explorer'],
    ['.drawer-switch', 'Show or hide the list of sections on this page'], ['.mark', 'Mark this step as done or not done'], ['.copy', 'Copy a link you can paste into Teams or an email'],
    ['[data-download]', 'Download the assets you left out, in the template layout'], ['[data-clear]', 'Remove every asset from this list'], ['.cap-chip', 'Open this capability in the playbooks'],
    ['.journey a', 'Go to this stage of the journey'], ['.brand', 'Back to the home page'], ['.tour-start', 'A short guided tour of this page'], ['#tr-file', 'Choose the CSV copy of your return. It stays on your device']];
  // D-17: tooltips were assigned once, before the script created some controls; applyTips runs again at the end for anything added later
  function applyTips() {
    AUTOTIP.forEach(function (p) { $$(p[0]).forEach(function (el) { if (!el.hasAttribute('data-tip')) el.setAttribute('data-tip', p[1]); }); });
    $$('[title]').forEach(function (el) { if (el.tagName === 'svg' || el.closest('svg')) return; el.setAttribute('data-tip', el.getAttribute('title')); el.removeAttribute('title'); });
    $$('.prov, .lk').forEach(function (el) { if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '0'); });   // so keyboard users can reach the explanation
  }
  applyTips();
  function tipText(el) { return el.getAttribute('data-def') || el.getAttribute('data-tip'); }
  function showAny(el) { var t = tipText(el); if (!t) return; tip.textContent = t; tip.hidden = false; tipFor = el; el.setAttribute('aria-describedby', 'term-tip');
    var r = el.getBoundingClientRect(), w = Math.min(320, innerWidth - 16); tip.style.maxWidth = w + 'px';
    tip.style.left = Math.max(8, Math.min(r.left + scrollX, scrollX + innerWidth - w - 8)) + 'px';
    var below = r.bottom + scrollY + 6; tip.style.top = below + 'px';
    var th = tip.offsetHeight, up = r.bottom + th + 12 > innerHeight && r.top > th + 12; if (up) tip.style.top = (r.top + scrollY - th - 6) + 'px'; tip.classList.toggle('above', up); }
  d.addEventListener('mouseover', function (e) { var el = e.target.closest && e.target.closest('[data-def],[data-tip]'); if (el && el !== tipFor) showAny(el); });
  d.addEventListener('mouseout', function (e) { var el = e.target.closest && e.target.closest('[data-def],[data-tip]'); if (el && !el.contains(e.relatedTarget) && !tip.contains(e.relatedTarget) && d.activeElement !== el) hideTip(); });
  d.addEventListener('focusin', function (e) { var el = e.target.closest && e.target.closest('[data-def],[data-tip]'); if (el) showAny(el); else hideTip(); });
  d.addEventListener('focusout', function (e) { if (tipFor && e.target === tipFor) hideTip(); });
  tip.addEventListener('mouseleave', function () { if (!tipFor || d.activeElement !== tipFor) hideTip(); });
  d.addEventListener('keydown', function (e) { if (e.key === 'Escape') hideTip(); });

  // ---- stale-content warning: says so if the sources have not been re-checked recently ----
  var checked = body.getAttribute('data-checked'), staleDays = +body.getAttribute('data-stale-days') || 30;
  var age = Math.floor((Date.now() - Date.parse(checked + 'T00:00:00Z')) / 864e5);
  var staleEl = $('.stale');
  if (staleEl && age > staleDays) { staleEl.hidden = false; staleEl.textContent = 'The sources for this app were last checked ' + age + ' days ago. Check GOV.UK for anything recent.'; }

  // ---- counters and countdown ----
  $$('[data-count-to]').forEach(function (el) {
    var to = +el.getAttribute('data-count-to'); if (motionOff()) return;
    var t0 = null; el.textContent = '0';
    function step(t) { t0 = t0 || t; var k = Math.min(1, (t - t0) / 900); el.textContent = String(Math.round(to * (1 - Math.pow(1 - k, 3)))); if (k < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  });
  var cd = $('[data-countdown]'), ready = body.getAttribute('data-ready-by');
  if (cd && ready) {
    // D-13: count whole calendar days in UK time, not to the end of the target day
    var now = new Date(), today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    var left = Math.round((Date.parse(ready + 'T00:00:00Z') - today) / 864e5);
    if (left > 1) cd.innerHTML = '<b>' + left + ' days</b> until Friday 18 December 2026, when GDS asks you to be ready.';
    else if (left === 1) cd.innerHTML = '<b>Tomorrow</b>, Friday 18 December 2026, is the date GDS asks you to be ready by.';
    else if (left === 0) cd.innerHTML = '<b>Today</b>, Friday 18 December 2026, is the date GDS asks you to be ready by.';
    else cd.innerHTML = 'The date to be ready by, Friday 18 December 2026, has passed. The Baseline Return is due in January 2027.';
  }

  // ---- your return: mark steps done; progress saved on this device only ----
  var steps = $$('li.step[id^="step-"]');
  var done = store.get('steps', {}) || {};
  function total() { return 12; }
  function countDone() { var n = 0; for (var k in done) if (done[k] === true && /^step-(\d|1[0-2])$/.test(k)) n++; return n; }
  function ring(n, of) {
    var pc = Math.round(n / of * 100), C = 2 * Math.PI * 34, off = C * (1 - n / of);
    return '<svg class="ring" viewBox="0 0 80 80" aria-hidden="true" focusable="false"><circle cx="40" cy="40" r="34" class="ring-bg"/><circle cx="40" cy="40" r="34" class="ring-fg" stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + off.toFixed(1) + '"/><text x="40" y="45" text-anchor="middle">' + pc + '%</text></svg>';
  }
  if (steps.length) {
    var bar = d.createElement('div'); bar.className = 'progress-bar'; bar.setAttribute('role', 'status');
    var stepsSection = $('#steps') || steps[0].closest('section'); stepsSection.parentNode.insertBefore(bar, stepsSection);
    var paint = function () { var n = countDone(); bar.innerHTML = ring(n, total()) + '<p><b>' + n + ' of ' + total() + ' steps done.</b> Saved on this device only. <button type="button" class="linkish" data-steps-reset>Start again</button></p>'; };
    steps.forEach(function (li) {
      var id = li.id, b = d.createElement('button'); b.type = 'button'; b.className = 'mark';
      var set = function () { var on = done[id] === true; b.setAttribute('aria-pressed', String(on)); b.textContent = on ? 'Done' : 'Mark as done'; li.classList.toggle('is-done', on); };
      b.addEventListener('click', function () { done[id] = !(done[id] === true); store.set('steps', done); set(); paint(); announce('Step ' + id.slice(5) + (done[id] ? ' marked as done.' : ' marked as not done.')); });
      set(); (li.querySelector('.body') || li).appendChild(b);
    });
    paint();
    bar.addEventListener('click', function (e) { if (e.target.hasAttribute('data-steps-reset')) { done = {}; store.del('steps'); steps.forEach(function (li) { var b = $('.mark', li); li.classList.remove('is-done'); b.setAttribute('aria-pressed', 'false'); b.textContent = 'Mark as done'; }); paint(); announce('Progress cleared.'); } });
  }
  var ph = $('[data-progress-home]');
  if (ph) {
    var n = countDone();
    if (n > 0) {
      var next = 1; while (done['step-' + next] === true && next <= 12) next++;
      ph.innerHTML = '<div class="ring-wrap">' + ring(n, 12) + '<p><b>' + n + ' of 12 steps done.</b><br>' + (next <= 12 ? '<a href="return.html#step-' + next + '">Continue with step ' + next + '</a>' : 'All steps done. <a href="return.html#check">Check your list</a>') + '</p></div>';
    }
  }

  // ---- asset test ----
  var form = $('form.asset-test');
  /* decideAsset: turn the five answers into a result.
     Each rule follows the policy (OFFICIAL) or the four DAM Policy scope principles (GDS FAQs, November 2026).
     Returns {verdict: 'in' | 'in-later' | 'out' | 'flag', reasons: [...], failed: {official, purpose, shared, accountable, source}} */
  function decideAsset(a) {
    var r = [], failed = {}, unsure = [];
    if (a.official === 'no') { failed.official = true; r.push('It is SECRET or TOP SECRET. Only OFFICIAL data is in scope.'); }
    else if (a.official !== 'yes') unsure.push('whether it is OFFICIAL');
    var purposes = a.purpose.filter(function (x) { return x !== 'unsure'; });
    if (!purposes.length && a.purpose.indexOf('unsure') < 0) { failed.purpose = true; r.push('It serves none of the seven critical purposes.'); }
    else if (!purposes.length) unsure.push('which critical purposes it serves');
    if (a.shared === 'no') { failed.shared = true; r.push('It is only used inside your organisation, so it has no value across government through sharing.'); }
    else if (!a.shared || a.shared === 'unsure') unsure.push('how it is shared');
    if (a.accountable === 'asis') { failed.accountable = true; r.push('You use another organisation’s data as it is. The organisation accountable for it reports it.'); }
    else if (!a.accountable || a.accountable === 'unsure') unsure.push('who is accountable for it');
    if (a.source === 'derived') { failed.source = true; r.push('It is drawn from source data. Report the source data set instead, even if the source itself is never shared.'); }
    else if (!a.source || a.source === 'unsure') unsure.push('whether it is the source data');
    if (Object.keys(failed).length) return {verdict: 'out', reasons: r, failed: failed};
    // Owner's decision (18 Nov 2026): "not sure" means include it provisionally and flag it, so the baseline is not delayed (GDS FAQs: do not hold up the return)
    if (unsure.length) return {verdict: 'flag', reasons: ['Include it for now and flag it. Before you send the return, confirm ' + unsure.join(', ') + ' with the people who know the data, or ask your lead coordinator.'], purposes: purposes, failed: failed, unsure: unsure};
    if (a.shared === 'potential') return {verdict: 'in-later', reasons: ['It is in scope, but it is not shared yet. For the Baseline Return, start with assets already shared or published, and add this one if you have time.'], purposes: purposes, failed: failed};
    return {verdict: 'in', reasons: ['It is OFFICIAL, serves purpose ' + purposes.join(', ') + ', is ' + (a.shared === 'open' ? 'published as open data' : 'shared under a data sharing agreement') + ', you are accountable for it, and it is ' + (a.source === 'product' ? 'a product managed and owned in its own right' : 'the source data') + '.'], purposes: purposes, failed: failed};
  }
  window.DPE = {decideAsset: decideAsset};   // exposed for the build's tests
  if (form) {
    var tested = store.get('tested', []) || [];
    var HEAD = {in: 'Include it in your return', 'in-later': 'In scope: include it if you have time', out: 'Leave it out', flag: 'Include it provisionally, flagged'};
    var showTested = function () {
      var sec = $('.tested'); sec.hidden = !tested.length; if (!tested.length) return;
      $('[data-tested]').innerHTML = '<ul class="tested-list">' + tested.map(function (t) { return '<li class="v-' + esc(t.verdict) + '"><b>' + esc(t.name || 'Unnamed asset') + '</b>: ' + esc(HEAD[t.verdict] || '') + '</li>'; }).join('') + '</ul>';
    };
    showTested();
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = function (n) { var x = $('input[name="' + n + '"]:checked', form); return x ? x.value : ''; };
      var a = {official: v('official'), shared: v('shared'), accountable: v('accountable'), source: v('source'), purpose: $$('input[name="purpose"]:checked', form).map(function (x) { return x.value; })};
      var res = decideAsset(a), name = $('#asset-name').value.trim().slice(0, 120);
      var nextHtml = {in: '<p>Next: give it an owner and a steward (<a href="return.html#step-6">step 6</a>) and fill in its details (<a href="return.html#step-7">step 7</a>).</p>',
        'in-later': '<p>Next: note it for the October 2027 return, or add it now if you have time. <a href="questions.html#q-potential-value">How to judge potential value</a>.</p>',
        out: '<p>Next: add it to your list of assets left out, with the reason. You can download that list below.</p>',
        flag: '<p>Next: add it to your list with a note in its description saying what still needs confirming, then test it again once you know. <a href="questions.html#q-principles">The four principles explained</a>.</p>'}[res.verdict];
      $('[data-result]').innerHTML = '<div class="verdict v-' + res.verdict + '"><h3>' + esc((name ? name + ': ' : '') + HEAD[res.verdict]) + '</h3><ul>' + res.reasons.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' + nextHtml + '</div>';
      tested.push({name: name, verdict: res.verdict, a: a, failed: res.failed, reason: res.reasons.join(' '), date: new Date().toISOString().slice(0, 10)});
      store.set('tested', tested.slice(-200)); showTested();
      $('#result').focus();
    });
    $('[data-download]').addEventListener('click', function () {
      var yn = function (t, k) { return t.failed && t.failed[k] ? 'No' : 'Yes'; };
      var cell = function (x) { x = String(x == null ? '' : x); if (/^[=+\-@\t\r]/.test(x)) x = "'" + x; return /[",\r\n]/.test(x) ? '"' + x.replace(/"/g, '""') + '"' : x; };   // stops spreadsheet formula injection
      var rows = [['Unique identifier', 'Data asset name', 'OFFICIAL', 'Critical purpose', 'Shared', 'Accountable', 'Source asset', 'Reason', 'Decided by (role)', 'Date']];
      tested.filter(function (t) { return t.verdict === 'out'; }).forEach(function (t, i) { rows.push(['LO-' + String(i + 1).padStart(3, '0'), t.name, yn(t, 'official'), yn(t, 'purpose'), yn(t, 'shared'), yn(t, 'accountable'), yn(t, 'source'), t.reason, 'Coordinator', t.date]); });
      var blob = new Blob([rows.map(function (r) { return r.map(cell).join(','); }).join('\r\n') + '\r\n'], {type: 'text/csv'});
      var u = URL.createObjectURL(blob), l = d.createElement('a'); l.href = u; l.download = 'assets-left-out.csv'; d.body.appendChild(l); l.click(); l.remove(); setTimeout(function () { URL.revokeObjectURL(u); }, 1000);
      announce((rows.length - 1) + ' assets left out downloaded.');
      window.__dpeCsv = rows.map(function (r) { return r.map(cell).join(','); }).join('\r\n');
    });
    var cc = d.createElement('button'); cc.type = 'button'; cc.className = 'btn secondary'; cc.textContent = 'Copy the list as CSV';
    cc.addEventListener('click', function () {
      $('[data-download]').click();
      var t = window.__dpeCsv || '';
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(function () { announce('List copied. Paste it into Excel.'); cc.textContent = 'Copied'; setTimeout(function () { cc.textContent = 'Copy the list as CSV'; }, 2500); }, function () { announce('Copy was blocked by this browser.'); });
    });
    $('[data-download]').parentNode.insertBefore(cc, $('[data-clear]'));
    $('[data-clear]').addEventListener('click', function () { tested = []; store.del('tested'); showTested(); announce('List cleared.'); });
  }

  // ---- filters: questions and resources ----
  function filterer(opts) {
    var items = $$(opts.items); if (!items.length) return;
    var input = opts.search ? $(opts.search) : null;
    var run = function () {
      var q = input ? input.value.trim().toLowerCase() : '', vals = {}, shown = 0;
      opts.groups.forEach(function (g) { var x = $('input[name="' + g.name + '"]:checked'); vals[g.name] = x ? x.value : ''; });
      items.forEach(function (it) {
        var ok = !q || it.textContent.toLowerCase().indexOf(q) >= 0;
        opts.groups.forEach(function (g) { var want = vals[g.name]; if (want && (' ' + it.getAttribute(g.attr) + ' ').indexOf(' ' + want + ' ') < 0 && it.getAttribute(g.attr) !== want) ok = false; });
        it.hidden = !ok; if (ok) shown++;
        if (ok && q && it.querySelector('details')) it.querySelector('details').open = true;
      });
      if (opts.headings) $$(opts.headings).forEach(function (h) { var n = h.nextElementSibling, any = false; while (n && !n.matches(opts.headings)) { if (!n.hidden) any = true; n = n.nextElementSibling; } h.hidden = !any; });
      var c = $(opts.count); if (c) c.textContent = shown + ' ' + (shown === 1 ? opts.noun : opts.noun.replace(/y$/, 'ie') + 's') + (shown ? '' : '. Try fewer words, or another topic.');
    };
    if (input) input.addEventListener('input', run);
    opts.groups.forEach(function (g) { $$('input[name="' + g.name + '"]').forEach(function (r) { r.addEventListener('change', run); }); });
  }
  filterer({items: '.qa-list .qa', search: '#qa-search', groups: [{name: 'topic', attr: 'data-topic'}], count: '#qa-count', noun: 'question', headings: '.qa-list .topic-h'});
  filterer({items: '.caps .cap', groups: [{name: 'who', attr: 'data-who'}, {name: 'link', attr: 'data-link'}], count: '#cap-count', noun: 'capability'});
  filterer({items: '.res-list .res', groups: [{name: 'rtype', attr: 'data-type'}, {name: 'raud', attr: 'data-aud'}], count: '#res-count', noun: 'resource'});

  // ---- forms that only work in the browser never submit to a server ----
  var rf = $('#reply-form'); if (rf) rf.addEventListener('submit', function (e) { e.preventDefault(); });

  // ---- Ask: finds the closest answers in the explorer's own content. Runs in the browser; not generative AI. ----
  var SYN = {alb: 'arm length body bodies', albs: 'arm length body bodies', cda: 'critical data asset', cdas: 'critical data assets', dqap: 'data quality action plan',
    iao: 'information asset owner', iar: 'information asset register', cdo: 'chief data officer', api: 'apis data service', apis: 'api data service',
    esda: 'essential shared data asset', ndl: 'national data library', mem: 'metadata exchange model', deadline: 'due date when return', due: 'when date deadline',
    secret: 'classified official', classified: 'secret official', names: 'name owner steward', owner: 'ownership owners', coordinator: 'coordinator coordinators', tool: 'product catalogue tool'};
  var STOP = ' a an the of to in on for and or is are do does we our us i my it be can what how who when which with should must about this that there their they you your if as at by from not';
  function toks(s) { return String(s).toLowerCase().replace(/[’']/g, '').split(/[^a-z0-9_]+/).filter(function (w) { return w && w.length > 1 && STOP.indexOf(' ' + w + ' ') < 0 && (' ' + STOP + ' ').indexOf(' ' + w + ' ') < 0; }); }
  function stem(w) { return w.replace(/(ing|ies|es|s|ed)$/, function (m) { return m === 'ies' ? 'y' : ''; }); }
  function scoreItem(qt, it) {
    var t = toks(it.t).map(stem), x = toks(it.x).map(stem), sc = 0;
    qt.forEach(function (w) { if (t.indexOf(w) >= 0) sc += 3; if (x.indexOf(w) >= 0) sc += 1; });
    if (it.k === 'Answer') sc *= 1.25;
    return sc;
  }
  var askBox = $('[data-ask]');
  if (askBox) {
    var q0 = new URLSearchParams(location.search).get('q') || '';
    var qi = $('#ask-q'); if (qi) qi.value = q0.slice(0, 200);
    var hq = $('#hq'); if (hq && q0) hq.value = q0.slice(0, 200);
    var runAsk = function (q0) { fetch('explorer-data.json').then(function (r) { return r.json(); }).then(function (data) {
      var raw = toks(q0), qt = [];
      raw.forEach(function (w) { qt.push(stem(w)); if (SYN[w]) toks(SYN[w]).forEach(function (s) { qt.push(stem(s)); }); });
      var res = data.index.map(function (it) { return {it: it, s: scoreItem(qt, it)}; }).filter(function (r) { return r.s >= 3; }).sort(function (a, b) { return b.s - a.s; }).slice(0, 6);
      if (!res.length) { askBox.innerHTML = '<p>No close match for “' + esc(q0) + '”. Try other words, browse <a href="questions.html">all questions and answers</a>, or <a href="' + esc(body.getAttribute('data-contact')) + '" target="_blank" rel="noopener noreferrer">ask us through the contact form<span class="vh"> (opens in a new tab)</span></a>.</p>'; announce('No close match.'); return; }
      askBox.innerHTML = '<p>' + res.length + ' best match' + (res.length === 1 ? '' : 'es') + ' for “' + esc(q0) + '”. The first is usually the answer.</p><ol class="ask-results">' + res.map(function (r, i) {
        var it = r.it, ext = /^https?:/.test(it.u);
        var badgeHtml = it.p ? ' <span class="prov prov-' + esc(it.p) + '">' + esc(data.prov[it.p] || '') + '</span>' : '';
        var snip = it.x.length > 320 ? it.x.slice(0, 317).replace(/\s+\S*$/, '') + '…' : it.x;
        return '<li class="' + (i === 0 ? 'best' : '') + '"><p class="small muted">' + esc(it.k) + badgeHtml + '</p><h3><a href="' + esc(it.u) + '"' + (ext ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' + esc(it.t) + (ext ? '<span class="vh"> (opens in a new tab)</span>' : '') + '</a></h3><p>' + esc(snip) + '</p></li>';
      }).join('') + '</ol>';
      applyTips(); announce(res.length + ' answers found.');
    }).catch(function () { askBox.innerHTML = '<p>Search is not available right now. Browse <a href="questions.html">all questions and answers</a>.</p>'; }); };
    if (q0) runAsk(q0);
    var af = $('form.askform');
    if (af) af.addEventListener('submit', function (e) { e.preventDefault(); var q = qi.value.trim().slice(0, 200); if (q) runAsk(q); });
    $$('.starters a').forEach(function (a) { a.addEventListener('click', function (e) { e.preventDefault(); var q = a.textContent; qi.value = q; runAsk(q); }); });
  }

  // ---- Track and analyse: stage tracker and analysis of the return the person sent. All in this browser. ----
  var trk = $('form.tracker');
  if (trk) {
    var T = store.get('track', {}) || {};
    var STAGES = $$('input[name=stage]', trk).map(function (i) { return i.value; });
    var paintT = function () {
      var idx = STAGES.indexOf(T.stage);
      $$('.trk-stages li', trk).forEach(function (li, i) { li.classList.toggle('done', idx >= 0 && i < idx); li.classList.toggle('now', i === idx); });
      $('[data-tr-saved]').textContent = T.stage ? 'Saved on this device: ' + $('.trk-stages li.now b', trk).textContent + (T.ref ? ', reference ' + T.ref : '') + (T.date ? ', sent ' + T.date : '') + '.' : '';
    };
    $('#tr-ref').value = typeof T.ref === 'string' ? T.ref.slice(0, 40) : '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(T.date || '')) $('#tr-date').value = T.date;
    $$('input[name=stage]', trk).forEach(function (r) { r.checked = r.value === T.stage; r.addEventListener('change', function () { T.stage = r.value; store.set('track', T); paintT(); }); });
    $('#tr-ref').addEventListener('change', function () { T.ref = this.value.trim().slice(0, 40); store.set('track', T); paintT(); });
    $('#tr-date').addEventListener('change', function () { T.date = this.value; store.set('track', T); paintT(); });
    trk.addEventListener('submit', function (e) { e.preventDefault(); });
    paintT();
  }
  var trFile = $('#tr-file'), trOut = $('[data-tr-analytics]');
  function bars(title, counts, total) {
    var keys = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
    if (!keys.length) return '';
    return '<figure class="chart"><figcaption>' + esc(title) + '</figcaption><ul class="bars">' + keys.map(function (k) {
      var pc = total ? Math.round(counts[k] / total * 100) : 0;
      return '<li><span class="bl">' + esc(k || 'Blank') + '</span><span class="chartbar"><span class="fill" data-pc="' + pc + '"></span></span><span class="bv">' + counts[k] + '</span></li>';
    }).join('') + '</ul></figure>';
  }
  function analyse(text, name) {
    var api = window.DAMChecker; if (!api) return;
    var res = api.check(text), rows = api.parseCSV(text), head = rows[0] || [], col = {};
    head.forEach(function (h, i) { var k = api.key(h); api.FIELDS.forEach(function (f) { if (api.key(f[1]) === k && !(f[0] in col)) col[f[0]] = i; }); });
    var recs = rows.slice(1).filter(function (r) { return r.some(function (x) { return String(x).trim(); }); });
    var n = recs.length, get = function (r, L) { return L in col ? String(r[col[L]] || '').trim() : ''; };
    var tally = function (L, split) { var o = {}; recs.forEach(function (r) { var v = get(r, L); (split ? v.split(/[,;]\s*/) : [v]).forEach(function (x) { x = x.trim(); if (split && !x) return; o[x] = (o[x] || 0) + 1; }); }); return o; };
    var yes = function (L) { return recs.filter(function (r) { return /^y(es)?$/i.test(get(r, L)); }).length; };
    var pct = function (x) { return n ? Math.round(x / n * 100) + '%' : '0%'; };
    var c = res.counts;
    var h = '<p class="small">' + esc(name) + ': ' + n + ' asset' + (n === 1 ? '' : 's') + '. Read in your browser only.</p>';
    h += '<ul class="stats"><li><span class="num">' + n + '</span><span class="lbl">assets in your return</span></li><li><span class="num">' + c.ready + '</span><span class="lbl">ready</span></li><li><span class="num">' + c.gap + '</span><span class="lbl">with policy gaps only</span></li><li><span class="num">' + c.fix + '</span><span class="lbl">with something to fix</span></li></ul>';
    h += '<ul class="stats"><li><span class="num">' + pct(yes('G')) + '</span><span class="lbl">have a data owner assigned</span></li><li><span class="num">' + pct(yes('H')) + '</span><span class="lbl">have a data steward assigned</span></li><li><span class="num">' + pct(tally('R')['In catalogue'] || 0) + '</span><span class="lbl">are in a data catalogue</span></li><li><span class="num">' + pct(yes('N')) + '</span><span class="lbl">contain personal data</span></li></ul>';
    h += '<div class="duo">' + bars('Critical purposes served (an asset can serve several)', tally('J', true), n) + bars('In a data catalogue?', tally('R'), n) + bars('Data quality plan status', tally('T'), n) + bars('Primary sharing status', tally('K'), n) + '</div>';
    if (n) h += '<div class="tbl-scroll" tabindex="0" role="region" aria-label="Your assets, scrollable table"><table class="tbl small"><caption class="vh">Your assets and how ready each one is</caption><thead><tr><th scope="col">Identifier</th><th scope="col">Asset</th><th scope="col">Ready?</th><th scope="col">What to look at</th></tr></thead><tbody>' + res.rows.map(function (r) {
      var lab = {ready: 'Ready', gap: 'Policy gaps', ask: 'Questions', fix: 'Fix'}[r.state];
      return '<tr><td>' + esc(r.identifier) + '</td><td>' + esc(r.title) + '</td><td><span class="pill ' + (r.state === 'ready' ? 'yes' : r.state === 'fix' ? 'no' : 'maybe') + '">' + lab + '</span></td><td>' + esc(r.issues.slice(0, 2).map(function (x) { return x.text; }).join(' ')) + '</td></tr>';
    }).join('') + '</tbody></table></div>';
    trOut.innerHTML = h;
    $$('.fill[data-pc]', trOut).forEach(function (f) { f.style.width = Math.max(2, +f.getAttribute('data-pc')) + '%'; });   // CSSOM, allowed by the security policy
    announce('Your return has ' + n + ' assets: ' + c.ready + ' ready.');
  }
  if (trFile && trOut) trFile.addEventListener('change', function () {
    var f = trFile.files && trFile.files[0]; if (!f) return;
    if (f.size > 5 * 1024 * 1024) { trOut.innerHTML = '<p>That file is larger than 5 MB. Save only the return sheet as CSV.</p>'; return; }
    var rd = new FileReader(); rd.onload = function () { analyse(String(rd.result), f.name); }; rd.readAsText(f);
  });
  window.DPE.analyse = analyse;

  // ---- guided tours and tutorials ----
  // A modal dialog that points at one part of the page at a time. Keyboard: Tab stays inside, Escape closes, focus returns.
  var TOURS = {
    home: [['.hsearch', 'Ask anything', 'Type a question here on any page. The explorer finds the best answers, with their sources.'],
           ['#site-nav', 'Move between sections', 'The menu takes you to each part of the explorer. On narrow screens it folds behind the Menu button.'],
           ['.settings-btn', 'Make it work for you', 'Change colours, including high contrast, text size, spacing and animation. Saved on this device.'],
           ['.journey', 'Your path through the policy', 'Six stages, from understanding the policy to keeping your list current. Choose any stage.'],
           ['[data-countdown]', 'Key date', 'How long until GDS asks you to be ready.'],
           ['[data-progress-home]', 'Your progress', 'Mark steps done on Your return and your progress shows here.'],
           ['.xcards', 'Start from your role', 'Each card takes you to the route that fits what you do.'],
           ['.nextbest', 'What to do next', 'Every page ends with the next step and related pages.']],
    asset: [['#q-official', 'Five questions', 'Answer one question at a time. Not sure? Choose Not sure: the asset is included provisionally and flagged.'],
            ['.asset-test button[type=submit]', 'Get your result', 'You see whether it goes in your return, why, and what to do next.'],
            ['#result', 'Your result', 'Each asset you test is added to a list you can download or copy, in the template layout.']],
    check: [['#return-check', 'Check before you send', 'Open the CSV copy of your workbook. It is read in your browser and never uploaded.'],
            ['#steps', 'Twelve steps', 'Open any step, and mark it done when you finish. Your progress is kept on this device.']],
    track: [['form.tracker', 'Where your return has got to', 'Record your reference, the date you sent it and the current stage.'],
            ['#tr-file', 'What you sent', 'Open the CSV of the workbook you sent to see how ready each asset is, with charts.'],
            ['#government', 'Across government', 'The measures GDS will report once returns arrive.']],
    answers: [['#qa-search', 'Search the answers', 'Type a few words. Matching answers open as you type.'],
              ['.chips', 'Filter by topic', 'Narrow the list to one topic.'],
              ['.legend', 'How far to rely on an answer', 'Each answer carries a label: Policy, GDS position, Suggested practice, Programme plan or Open. Point at a label for its meaning.'],
              ['#asked', 'Built from your questions', 'Every need raised in the forums, and where it is answered.']]
  };
  var PAGE_TOUR = {'index.html': 'home', '': 'home', 'asset-test.html': 'asset', 'return.html': 'check', 'track.html': 'track', 'questions.html': 'answers'};
  var here = location.pathname.split('/').pop();
  function runTour(name) {
    var steps = (TOURS[name] || []).filter(function (s) { var el = $(s[0]); return el && el.getClientRects().length; });
    if (!steps.length) return;
    var back = d.activeElement, i = 0;
    var dim = d.createElement('div'); dim.className = 'tour-dim';
    var box = d.createElement('div'); box.className = 'tour'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-labelledby', 'tour-h');
    body.appendChild(dim); body.appendChild(box);
    var ring = d.createElement('div'); ring.className = 'tour-ring'; body.appendChild(ring);
    function close() { box.remove(); dim.remove(); ring.remove(); d.removeEventListener('keydown', key, true); store.set('toured.' + name, true); if (back && back.focus) back.focus(); announce('Tour closed.'); }
    function key(e) {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      if (e.key === 'Tab') { var f = $$('button', box); if (e.shiftKey && d.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); } else if (!e.shiftKey && d.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); } }
    }
    d.addEventListener('keydown', key, true);
    function show() {
      var s = steps[i], el = $(s[0]);
      el.scrollIntoView({block: 'center', behavior: motionOff() ? 'auto' : 'smooth'});
      setTimeout(function () {
        var r = el.getBoundingClientRect();
        ring.style.left = (r.left + scrollX - 6) + 'px'; ring.style.top = (r.top + scrollY - 6) + 'px'; ring.style.width = (r.width + 12) + 'px'; ring.style.height = (Math.min(r.height, innerHeight * 0.6) + 12) + 'px';
      }, motionOff() ? 0 : 350);
      box.innerHTML = '<p class="tour-n">Step ' + (i + 1) + ' of ' + steps.length + '</p><h2 id="tour-h">' + esc(s[1]) + '</h2><p>' + esc(s[2]) + '</p><p class="tour-btns">' +
        (i ? '<button type="button" class="btn secondary" data-t="back">Back</button> ' : '') +
        (i < steps.length - 1 ? '<button type="button" class="btn" data-t="next">Next</button> ' : '<button type="button" class="btn" data-t="done">Finish</button> ') +
        '<button type="button" class="linkish" data-t="close">Close the tour</button></p>';
      $('h2', box).setAttribute('tabindex', '-1'); $('h2', box).focus();
    }
    box.addEventListener('click', function (e) { var t = e.target.getAttribute && e.target.getAttribute('data-t'); if (t === 'next') { i++; show(); } else if (t === 'back') { i--; show(); } else if (t === 'done' || t === 'close') close(); });
    dim.addEventListener('click', close);
    show();
  }
  window.DPE.runTour = runTour;
  var tn = PAGE_TOUR[here];
  if (tn) {
    var tb = d.createElement('button'); tb.type = 'button'; tb.className = 'tour-start linkish'; tb.innerHTML = 'Take a short tour of this page';
    tb.addEventListener('click', function () { runTour(tn); });
    var h1 = $('main h1'); if (h1) h1.insertAdjacentElement('afterend', tb);
    tb.setAttribute('data-tip', 'A short guided tour of this page');
  }
  $$('[data-tutorial]').forEach(function (b) { b.addEventListener('click', function () { location.href = b.getAttribute('data-page') + '#tour-' + b.getAttribute('data-tutorial'); }); });
  var tm = /^#tour-([a-z]+)$/.exec(location.hash);
  if (tm && TOURS[tm[1]]) setTimeout(function () { runTour(tm[1]); }, 300);
  else if (tn && !store.get('toured.' + tn, false) && !store.get('tours-off', false) && tn === 'home') {
    var offer = d.createElement('div'); offer.className = 'tour-offer'; offer.setAttribute('role', 'region'); offer.setAttribute('aria-label', 'Tour');
    offer.innerHTML = '<p><b>New here?</b> Take a one-minute tour of the explorer.</p><p><button type="button" class="btn" data-o="go">Start the tour</button> <button type="button" class="linkish" data-o="no">No thanks</button></p>';
    var mainEl = $('#main'); mainEl.insertBefore(offer, mainEl.firstChild);
    offer.addEventListener('click', function (e) { var o = e.target.getAttribute && e.target.getAttribute('data-o'); if (o === 'go') { offer.remove(); runTour('home'); } if (o === 'no') { offer.remove(); store.set('tours-off', true); } });
  }

  // ---- copy a link to an answer, to paste into Teams or an email ----
  $$('.qa').forEach(function (art) {
    var bodyEl = $('.body', art); if (!bodyEl) return;
    var cb = d.createElement('button'); cb.type = 'button'; cb.className = 'linkish copy'; cb.textContent = 'Copy a link to this answer';
    cb.addEventListener('click', function () {
      var url = location.href.split('#')[0] + '#' + art.id;
      var done = function () { cb.textContent = 'Link copied'; announce('Link copied.'); setTimeout(function () { cb.textContent = 'Copy a link to this answer'; }, 2500); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () { cb.textContent = url; });
      else cb.textContent = url;
    });
    bodyEl.appendChild(cb);
  });

  // ---- links to a question open it ----
  function reveal() { var id = decodeURIComponent(location.hash.slice(1)); if (!id) return; var el = d.getElementById(id); if (!el) return; var own = el.querySelector(':scope > details'); if (own) own.open = true; var p = el.closest('details'); while (p) { p.open = true; p = p.parentElement.closest('details'); } }
  window.addEventListener('hashchange', reveal); reveal();

  // ---- bar charts take their width from data, without inline styles (the security policy forbids them) ----
  // widths are classes w0..w100 in steps of 10, set at build time

  // ---- self-check: the app checks itself every time it opens, and reports on the About page ----
  function selfCheck() {
    var results = [];
    var add = function (name, ok, detail) { results.push({name: name, ok: ok, detail: detail}); };
    var ids = {}; $$('[id]').forEach(function (e) { ids[e.id] = (ids[e.id] || 0) + 1; });
    var dup = Object.keys(ids).filter(function (k) { return ids[k] > 1; });
    add('Every identifier on this page is unique', !dup.length, dup.join(', '));
    var broken = $$('a[href^="#"]').filter(function (a) { var h = a.getAttribute('href').slice(1); return h && h !== 'main' && !d.getElementById(h); }).map(function (a) { return a.getAttribute('href'); });
    add('Every link within this page goes somewhere', !broken.length, broken.join(', '));
    var noalt = $$('img:not([alt])').length; add('Every image has a text alternative (or is marked decorative)', !noalt, noalt + ' missing');
    var ext = $$('a[href^="http"]').filter(function (a) { return a.target !== '_blank' || !/noopener/.test(a.rel); }).length;
    add('Links that leave the app open safely in a new tab', !ext, ext + ' do not');
    var terms = $$('a.term').filter(function (a) { return !a.getAttribute('data-def'); }).length; add('Every glossary word has a definition', !terms, terms + ' missing');
    add('Sources checked within the last ' + staleDays + ' days', age <= staleDays, 'last checked ' + age + ' days ago');
    var st = store.set('probe', 1); store.del('probe'); add('This browser can save your progress', st, st ? '' : 'progress and settings will not be kept');
    return results;
  }
  var sc = $('[data-selfcheck]');
  if (sc) {
    var res = selfCheck(), bad = res.filter(function (r) { return !r.ok; });
    sc.innerHTML = '<p><b>' + (res.length - bad.length) + ' of ' + res.length + ' checks passed on this page.</b></p><ul class="checks">' + res.map(function (r) {
      return '<li class="' + (r.ok ? 'pass' : 'fail') + '"><span class="vh">' + (r.ok ? 'Passed: ' : 'Failed: ') + '</span>' + esc(r.name) + (r.ok || !r.detail ? '' : ' (' + esc(r.detail) + ')') + '</li>';
    }).join('') + '</ul>';
  }
  window.DPE.selfCheck = selfCheck;
  applyTips();   // after every control the script creates
  window.DPE.applyTips = applyTips;

  // ---- works offline and can be installed, where the browser and host allow it ----
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    try { navigator.serviceWorker.register('sw.js').catch(function () { /* host does not allow it: the app still works online */ }); } catch (e) { /* ignore */ }
  }
})();
