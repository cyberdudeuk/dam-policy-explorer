/* Draws the end-to-end process map across the full width of the screen, and links every shape to its workflow,
   its decision tree and its details. Everything here is also written out as text on the page, so nothing depends on it. */
(function () {
  'use strict';
  var d = document, P = window.DAMProcess, host = d.getElementById('pmap');
  if (!P) return;

  /* ---------- tabs: Overview, End-to-end map, Workflows, Decision trees ---------- */
  var tablist = d.querySelector('[data-tabs]');
  if (tablist) {
    var tabs = [].slice.call(tablist.querySelectorAll('[role=tab]'));
    tablist.hidden = false;
    function show(tab, focus) {
      tabs.forEach(function (t) { var on = t === tab; t.setAttribute('aria-selected', on ? 'true' : 'false'); t.tabIndex = on ? 0 : -1; d.getElementById(t.getAttribute('aria-controls')).hidden = !on; });
      if (focus) tab.focus();
      if (tab.getAttribute('aria-controls') === 'panel-map') draw(true);
      try { history.replaceState(null, '', '#' + tab.id); } catch (e) {}
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { show(t); });
      t.addEventListener('keydown', function (ev) {
        var k = ev.key, n = k === 'ArrowRight' ? i + 1 : k === 'ArrowLeft' ? i - 1 : k === 'Home' ? 0 : k === 'End' ? tabs.length - 1 : null;
        if (n === null) return; ev.preventDefault(); show(tabs[(n + tabs.length) % tabs.length], true);
      });
    });
    window.DAMShowTab = function (id, then) { var t = d.getElementById(id); if (t) show(t); if (then) setTimeout(then, 30); };
    var start = tabs.filter(function (t) { return location.hash === '#' + t.id; })[0] || tabs[0];
    setTimeout(function () { show(start); draw(true); }, 0);   // after the map's data below is ready; the map is drawn even while its tab is hidden, so it prints
    window.addEventListener('hashchange', function () { var t = tabs.filter(function (x) { return location.hash === '#' + x.id; })[0]; if (t) show(t); });
  }

  /* ---------- the map ---------- */
  var SEL = null, drawnFor = 0;
  var LANE = {}; P.lanes.forEach(function (l, i) { l.i = i; LANE[l.id] = l; });
  var NODE = {}; P.nodes.forEach(function (n) { NODE[n.id] = n; });
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function fillOf(n) {
    var k = LANE[n.lane].kind;
    return n.type === 'decision' ? 'f-decision' : n.type === 'error' ? 'f-error' : n.type === 'accept' ? 'f-accept' : n.type === 'register' ? 'f-register' :
      n.type === 'store' ? 'f-store' : n.type === 'output' || k === 'insight' ? 'f-insight' : k === 'auto' ? 'f-auto' : n.lane === 'L7' ? 'f-accept' : 'f-human';
  }
  var meter = null;   // measures real text widths, so labels wrap to fit their shapes in any font
  function fits(t, px, kind) {
    if (!meter) { meter = d.createElementNS('http://www.w3.org/2000/svg', 'svg'); meter.setAttribute('class', 'pm'); meter.setAttribute('aria-hidden', 'true'); meter.style.cssText = 'position:absolute;left:-9999px;top:0;width:10px;height:10px;visibility:hidden';
      meter.innerHTML = '<g class="node"><text class="lbl"></text></g><g class="lanehead"><text></text></g>'; d.body.appendChild(meter); }
    var el = meter.querySelector(kind === 'lanehead' ? '.lanehead text' : '.node text'); el.textContent = t; var len = el.getComputedTextLength(); return len ? len <= px : t.length * 7.2 <= px;
  }
  function wrapPx(t, px, kind) { var w = t.split(' '), lines = [w[0]], i; for (i = 1; i < w.length; i++) { var c = lines[lines.length - 1] + ' ' + w[i]; if (fits(c, px, kind)) lines[lines.length - 1] = c; else lines.push(w[i]); } return lines; }

  var TYPE = {step: 'Person', auto: 'Automated', sub: 'Automated workflow', decision: 'Decision', error: 'Needs a fix', accept: 'Accepted', store: 'Stored', register: 'Register', output: 'Measure'};
  var SHORT = {'Automated': 'Auto', 'Automated workflow': 'Workflow', 'Needs a fix': 'Fix', 'Stored': 'Store'};   // fits on the shape; the full word is in its name and details
  function typeOf(n) { return n.type === 'step' && LANE[n.lane].kind === 'auto' ? 'Automated' : n.type === 'step' && LANE[n.lane].kind === 'insight' ? 'Measure' : TYPE[n.type] || 'Step'; }
  function draw(force) {
    if (!host) return;
    if (!force && host.offsetParent === null && host.querySelector('svg')) return;
    var avail = host.clientWidth || (d.documentElement.clientWidth - 48);
    var W = Math.max(900, avail), HEAD = 100, ROW = 76, rows = 19, NH = 66, pad = 8, H = HEAD + rows * ROW + 16;
    var weight = function (l) { return l.id === 'L8' ? 1.9 : 1; }, total = P.lanes.reduce(function (a, l) { return a + weight(l); }, 0), lx0 = 0;
    P.lanes.forEach(function (l) { l.x = lx0; l.w = W * weight(l) / total; lx0 += l.w; });
    if (drawnFor === W && host.querySelector('svg')) { mark(); return; }
    drawnFor = W;
    var pos = {}, s = '';
    P.lanes.forEach(function (l) {
      var x = l.x, laneW = l.w;
      s += '<rect class="lane' + (l.i % 2 ? ' alt' : '') + '" x="' + x + '" y="0" width="' + laneW + '" height="' + H + '"/>';
      var hl = wrapPx(l.title, laneW - 22, 'lanehead').slice(0, 3);
      s += '<g class="lanehead"><rect x="' + (x + 4) + '" y="4" width="' + (laneW - 8) + '" height="' + (HEAD - 10) + '" rx="8"/>' +
        '<svg x="' + (x + laneW / 2 - 10) + '" y="12" width="20" height="20" class="ic" aria-hidden="true"><use href="#' + l.icon + '"/></svg>' +
        hl.map(function (t, k) { return '<text x="' + (x + laneW / 2) + '" y="' + (48 + k * 15) + '">' + esc(t) + '</text>'; }).join('') + '</g>';
    });
    P.nodes.forEach(function (n) {
      var l = LANE[n.lane], laneW = l.w, split = n.col !== undefined, w = split ? laneW / 2 - pad * 1.5 : laneW - pad * 2, x = l.x + pad + (split ? n.col * (laneW / 2 - pad / 2) : 0), y = HEAD + n.row * ROW + (ROW - NH) / 2;
      pos[n.id] = {x: x, y: y, w: w, h: NH, cx: x + w / 2, cy: y + NH / 2};
    });
    P.edges.forEach(function (e, k) {
      var a = pos[e[0]], b = pos[e[1]], path, lx, ly, back = e[0] === 'P09' && e[1] === 'P03';
      if (back) {                               // the correction loop goes round the outside, back to the mailbox
        var rx = a.x + a.w + 8, top = b.y + NH / 2;
        path = 'M' + (a.x + a.w) + ' ' + a.cy + ' C' + (rx + 40) + ' ' + a.cy + ' ' + (rx + 40) + ' ' + (a.cy - 40) + ' ' + (rx + 40) + ' ' + (a.cy - 60) + ' L' + (rx + 40) + ' ' + (top + 20) + ' C' + (rx + 40) + ' ' + top + ' ' + (b.x + b.w + 30) + ' ' + top + ' ' + (b.x + b.w) + ' ' + top;
        lx = rx + 46; ly = (a.cy + top) / 2;
      } else if (NODE[e[0]].lane === NODE[e[1]].lane && NODE[e[1]].row - NODE[e[0]].row > 1) {   // skip past steps in between, down the left edge
        var gx = a.x - 6;
        path = 'M' + a.x + ' ' + a.cy + ' C' + (gx - 14) + ' ' + a.cy + ' ' + (gx - 14) + ' ' + b.cy + ' ' + b.x + ' ' + b.cy;
        lx = gx - 10; ly = (a.cy + b.cy) / 2;
      } else if (b.y > a.y + 4) {
        var sx = a.cx, sy = a.y + NH, ex = b.cx, ey = b.y;
        path = 'M' + sx + ' ' + sy + ' C' + sx + ' ' + (sy + 22) + ' ' + ex + ' ' + (ey - 22) + ' ' + ex + ' ' + ey;
        lx = (sx + ex) / 2; ly = (sy + ey) / 2;
      } else {                                  // a step back up the page: side to side
        var right = b.cx > a.cx, sx2 = right ? a.x + a.w : a.x, ex2 = right ? b.x : b.x + b.w;
        path = 'M' + sx2 + ' ' + a.cy + ' C' + (sx2 + (right ? 40 : -40)) + ' ' + a.cy + ' ' + (ex2 + (right ? -40 : 40)) + ' ' + b.cy + ' ' + ex2 + ' ' + b.cy;
        lx = (sx2 + ex2) / 2; ly = (a.cy + b.cy) / 2;
      }
      var cls = 'edge' + (e[2] === 'No' && e[1] === 'P07' || e[2] === 'Yes' && (e[1] === 'P07' || e[1] === 'P09') || back ? ' exc' : ' main');
      s += '<path class="' + cls + '" data-from="' + e[0] + '" data-to="' + e[1] + '" d="' + path + '" marker-end="url(#arr)"/>';
      if (e[2]) s += '<g class="elabel" data-from="' + e[0] + '" data-to="' + e[1] + '"><rect x="' + (lx - (e[2].length * 3.6 + 8)) + '" y="' + (ly - 10) + '" width="' + (e[2].length * 7.2 + 16) + '" height="20" rx="10"/><text x="' + lx + '" y="' + (ly + 4) + '">' + esc(e[2]) + '</text></g>';
    });
    P.nodes.forEach(function (n) {
      var p = pos[n.id], lines = wrapPx(n.label, p.w - (n.type === 'decision' ? 30 : 12)), shape;
      shape = n.type === 'decision' ? '<path class="shape" d="M' + p.x + ' ' + p.cy + ' L' + (p.x + 14) + ' ' + p.y + ' L' + (p.x + p.w - 14) + ' ' + p.y + ' L' + (p.x + p.w) + ' ' + p.cy + ' L' + (p.x + p.w - 14) + ' ' + (p.y + NH) + ' L' + (p.x + 14) + ' ' + (p.y + NH) + 'Z"/>'
        : n.type === 'store' || n.type === 'register' ? '<rect class="shape" x="' + p.x + '" y="' + p.y + '" width="' + p.w + '" height="' + NH + '" rx="18"/>'
        : '<rect class="shape" x="' + p.x + '" y="' + p.y + '" width="' + p.w + '" height="' + NH + '" rx="7"/>' + (n.type === 'sub' ? '<path class="subbar" d="M' + (p.x + 5) + ' ' + p.y + 'v' + NH + 'M' + (p.x + p.w - 5) + ' ' + p.y + 'v' + NH + '"/>' : '');
      s += '<g class="node ' + fillOf(n) + ' t-' + n.type + '" tabindex="0" role="button" data-id="' + n.id + '" data-tip="' + esc(n.text) + '" data-tip-mouse>' +
        '<title>' + esc(n.id + ', ' + typeOf(n) + ': ' + n.label) + '</title>' + shape +
        lines.map(function (t, k) { return '<text class="lbl" x="' + p.cx + '" y="' + (p.cy + 8 + (k - (lines.length - 1) / 2) * 12.5) + '">' + esc(t) + '</text>'; }).join('') +
        '<text class="nid" x="' + (p.x + (n.type === 'decision' ? 16 : 9)) + '" y="' + (p.y + 12) + '">' + n.id + ' · ' + (SHORT[typeOf(n)] || typeOf(n)).toUpperCase() + '</text></g>';
    });
    host.innerHTML = '<svg class="pm" viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" role="group" aria-label="End-to-end process map: ' + P.nodes.length + ' steps in ' + P.lanes.length + ' lanes, read from top to bottom. A text version follows the map.">' +
      '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker></defs>' + s + '</svg>';
    mark();
  }
  function mark() {
    var svg = host && host.querySelector('svg'); if (!svg) return;
    [].forEach.call(svg.querySelectorAll('.node'), function (g) { g.classList.toggle('on', g.getAttribute('data-id') === SEL); g.setAttribute('aria-pressed', g.getAttribute('data-id') === SEL ? 'true' : 'false'); });
    [].forEach.call(svg.querySelectorAll('[data-from]'), function (p) { var hit = SEL && (p.getAttribute('data-from') === SEL || p.getAttribute('data-to') === SEL); p.classList.toggle('hot', !!hit); p.classList.toggle('dim', !!SEL && !hit); });
  }
  function detail(id) {
    var n = NODE[id], box = d.getElementById('pmap-detail'); if (!n || !box) return;
    SEL = id; mark();
    var into = P.edges.filter(function (e) { return e[1] === id; }), out = P.edges.filter(function (e) { return e[0] === id; });
    var dec = P.decisions.filter(function (x) { return x.id === id || (id === 'SP02' && x.id === 'R04') || (id === 'SP03' && x.id === 'R05'); })[0];
    var wf = P.workflows.filter(function (w) { return w.id === n.wf; })[0];
    function link(e, k) { var o = NODE[e[k]]; return '<li><button type="button" class="linkish" data-go="' + o.id + '">' + esc(o.label) + '</button>' + (e[2] ? ' <span class="pill">' + esc(e[2]) + '</span>' : '') + '</li>'; }
    var acts = '<div class="actions">' + (wf ? '<button type="button" data-wf="' + wf.id + '">Open the job: ' + esc(wf.title) + ' (' + wf.id + ')</button>' : '') +
      (dec ? '<button type="button" data-dec="' + dec.id + '">Open the decision</button>' : '') + '<button type="button" class="closer" data-close-detail>Close the details</button></div>';
    box.innerHTML = acts + '<p class="kicker">' + esc(n.id) + ' · ' + esc(typeOf(n)) + ' · ' + esc(LANE[n.lane].title) + '</p><h3>' + esc(n.label) + '</h3><p>' + esc(n.text) + '</p>' +
      '<dl class="mini"><dt>Who or what does it</dt><dd>' + esc(LANE[n.lane].who) + '</dd>' +
      (into.length ? '<dt>Comes from</dt><dd><ul>' + into.map(function (e) { return link(e, 0); }).join('') + '</ul></dd>' : '') +
      (out.length ? '<dt>Goes to</dt><dd><ul>' + out.map(function (e) { return link(e, 1); }).join('') + '</ul></dd>' : '') + '</dl>';
    box.hidden = false; var ph = d.getElementById('pmap-placeholder'); if (ph) ph.hidden = true;
  }
  function go(id, focusNode) { detail(id); if (focusNode) { var g = host.querySelector('[data-id="' + id + '"]'); if (g) { g.focus(); g.scrollIntoView({block: 'nearest', inline: 'nearest'}); } } }
  if (host) {
    host.addEventListener('click', function (ev) { var g = ev.target.closest('.node'); if (g) detail(g.getAttribute('data-id')); });
    host.addEventListener('keydown', function (ev) {
      var g = ev.target.closest('.node'); if (!g) return; var id = g.getAttribute('data-id');
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); detail(id); }
      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp' || ev.key === 'ArrowRight') {   // follow the arrows: down takes the first way out, right the second (a decision's other answer), up goes back
        ev.preventDefault(); var outs = P.edges.filter(function (x) { return x[0] === id; });
        var e = ev.key === 'ArrowDown' ? outs[0] : ev.key === 'ArrowRight' ? outs[1] : P.edges.filter(function (x) { return x[1] === id; })[0];
        if (e) go(e[ev.key === 'ArrowUp' ? 0 : 1], true);
      }
    });
    var resizeT; window.addEventListener('resize', function () { clearTimeout(resizeT); resizeT = setTimeout(function () { draw(true); }, 150); });
    window.addEventListener('beforeprint', function () { draw(true); });
  }
  d.addEventListener('click', function (ev) {
    if (ev.target.closest('[data-close-detail]')) { var bx = d.getElementById('pmap-detail'), was = SEL; bx.hidden = true; var ph0 = d.getElementById('pmap-placeholder'); if (ph0) ph0.hidden = false; SEL = null; mark(); var g0 = was && host.querySelector('[data-id="' + was + '"]'); if (g0) g0.focus(); return; }
    var b = ev.target.closest('[data-go]'); if (b && d.getElementById('pmap-detail').contains(b)) { go(b.getAttribute('data-go'), true); return; }
    var w = ev.target.closest('[data-wf]'); if (w) { var id = w.getAttribute('data-wf'); window.DAMShowTab('tab-workflows', function () { var c = d.getElementById('wf-' + id); if (c) { c.classList.add('flash'); c.scrollIntoView({block: 'start'}); c.querySelector('h3').focus(); setTimeout(function () { c.classList.remove('flash'); }, 1600); } }); return; }
    var t = ev.target.closest('[data-dec]'); if (t) { var did = t.getAttribute('data-dec'); window.DAMShowTab('tab-decisions', function () { var c = d.getElementById('dt-' + did); if (c) { c.classList.add('flash'); c.scrollIntoView({block: 'start'}); c.querySelector('h3').focus(); setTimeout(function () { c.classList.remove('flash'); }, 1600); } }); return; }
    var m = ev.target.closest('[data-map]'); if (m) { var nid = m.getAttribute('data-map'); window.DAMShowTab('tab-map', function () { draw(true); go(nid, true); }); }
  });
  window.DAMProcessUI = {draw: draw, select: detail};
})();
