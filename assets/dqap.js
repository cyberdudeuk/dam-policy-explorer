/* DAM Policy Explorer: data quality action plans (dqap.html).
   Reads a filled-in GOV.UK DQAP template, or a plan built on the page, checks it against the steps of the GOV.UK
   implementation guide, scores a self-assessment for an equivalent process, and writes the plan as W3C DQV linked
   to the asset's DCAT record. Everything stays on this device: files are read in the browser and nothing is sent.
   The .xlsx reader is written here (no third-party code): a zip directory walk, the browser's own deflate, and an
   XML parser that never runs anything it reads. */
(function () {
  'use strict';
  var d = document;
  var $ = function (s, r) { return (r || d).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || d).querySelectorAll(s)); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function say(t) { var a = $('#announce'); if (a) { a.textContent = ''; setTimeout(function () { a.textContent = t; }, 50); } }
  var form = $('.dq-build');
  if (!form) return;
  var KEY = 'dpe.dqap', EQKEY = 'dpe.dqap-eq', MAXFILE = 5 * 1024 * 1024, MAXPART = 50 * 1024 * 1024;
  var store = {
    get: function (k) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage full or blocked: the page still works */ } },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) { /* nothing stored */ } }
  };
  var DATA = null;
  var ROWS = {
    items: [['item', 'Data item'], ['purpose', 'What it is used for'], ['crit', 'How critical (1 low to 4 high)', 'number']],
    issues: [['ref', 'Reference'], ['desc', 'Description']],
    rules: [['id', 'Rule ID'], ['rule', 'Rule'], ['dim', 'Dimension', 'dim'], ['metric', 'Metric'], ['target', 'Target (%)', 'number']],
    results: [['id', 'Rule ID'], ['date', 'Date measured', 'date'], ['value', 'Result (%)', 'number']],
    causes: [['issue', 'Issue'], ['priority', 'Priority', 'prio'], ['root', 'Root cause']],
    actions: [['issue', 'Issue'], ['action', 'Action'], ['owner', 'Owner (role)'], ['due', 'Target date', 'date']]
  };
  function empty() { return {source: 'built', details: {title: '', iri: '', scope: '', lead: '', report: '', freq: '', review: ''}, items: [], issues: [], rules: [], results: [], causes: [], actions: [], cover: {}, examples: 0}; }
  var plan = store.get(KEY) || empty();

  // ---------- numbers: the template stores 1 and 0.6, people type 100 and 60 ----------
  function frac(v) {
    if (v == null || v === '') return null;
    var s = String(v).trim(), pct = /%$/.test(s), n = parseFloat(s.replace(/[%\s,]/g, ''));
    if (isNaN(n)) return null;
    return pct || n > 1 ? n / 100 : n;
  }
  function pct(n) { return n == null ? '' : (Math.round(n * 1000) / 10) + '%'; }
  function ruleKey(r) { return String(r.id || r.rule || '').trim().toLowerCase(); }

  // ---------- the checks ----------
  function latest(rid) {
    var rs = plan.results.filter(function (x) { return String(x.id).trim().toLowerCase() === rid && frac(x.value) != null; });
    rs.sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });
    return {n: rs.length, dates: rs.map(function (x) { return x.date; }).filter(function (x, i, a) { return x && a.indexOf(x) === i; }).length, last: rs.length ? frac(rs[rs.length - 1].value) : null};
  }
  function below() {
    return plan.rules.filter(function (r) { var l = latest(ruleKey(r)), t = frac(r.target); return l.last != null && t != null && l.last < t; });
  }
  var TESTS = {
    details: function () { var t = plan.details; return t.title && t.scope ? ['met'] : t.title ? ['partly', 'The scope is missing.'] : ['missing']; },
    items: function () {
      var n = plan.items.length, w = plan.items.filter(function (x) { return x.purpose; }).length;
      return !n ? ['missing'] : w === n ? ['met', n + ' critical data item' + (n === 1 ? '' : 's') + '.'] : ['partly', (n - w) + ' of ' + n + ' items have no purpose.'];
    },
    issues: function () { return plan.issues.length || plan.causes.length ? ['met'] : ['partly', 'No issues are recorded. If you know of none, say so in the log.']; },
    rules: function () {
      var n = plan.rules.length, bad = plan.rules.filter(function (r) { return !(r.dim && r.metric && frac(r.target) != null); });
      return !n ? ['missing'] : !bad.length ? ['met', n + ' rule' + (n === 1 ? '' : 's') + '.'] : ['partly', bad.length + ' of ' + n + ' rules lack a dimension, a metric or a target: ' + bad.map(function (r) { return r.id || r.rule; }).slice(0, 5).join(', ') + '.'];
    },
    results: function () {
      var n = plan.rules.length; if (!n) return ['missing', 'Set rules first.'];
      var done = plan.rules.filter(function (r) { return latest(ruleKey(r)).n; }).length;
      return !done ? ['missing'] : done === n ? ['met'] : ['partly', (n - done) + ' of ' + n + ' rules have no result yet.'];
    },
    priority: function () {
      if (!plan.results.length) return ['missing', 'Measure first: priorities come from results.'];
      var b = below(); if (!b.length) return ['met', 'Every measured rule meets its target.'];
      var p = plan.causes.filter(function (c) { return /^(high|medium|low|critical)$/i.test(String(c.priority).trim()); }).length;
      return !p ? ['missing', b.length + ' rule' + (b.length === 1 ? ' is' : 's are') + ' below target, with no prioritised issue.'] : p < b.length ? ['partly', b.length + ' rules are below target; ' + p + ' prioritised issue' + (p === 1 ? '' : 's') + '.'] : ['met'];
    },
    actions: function () {
      if (!plan.results.length && !plan.causes.length) return ['missing', 'Measure first.'];
      if (!plan.causes.length && !below().length) return ['met', 'Nothing below target to act on yet.'];
      var root = plan.causes.filter(function (c) { return c.root; }).length, own = plan.actions.filter(function (a) { return a.action && a.owner && a.due; }).length;
      if (!root && !own) return ['missing'];
      var gaps = []; if (root < plan.causes.length) gaps.push((plan.causes.length - root) + ' issue' + (plan.causes.length - root === 1 ? ' has' : 's have') + ' no root cause');
      if (!plan.actions.length) gaps.push('no actions are recorded'); else if (own < plan.actions.length) gaps.push((plan.actions.length - own) + ' action' + (plan.actions.length - own === 1 ? ' has' : 's have') + ' no owner or date');
      return gaps.length ? ['partly', gaps.join('; ') + '.'] : ['met'];
    },
    reported: function () { var c = plan.cover[6]; return plan.details.report || c ? ['met'] : ['missing']; },
    monitor: function () {
      var f = plan.details.freq, r = plan.details.review, again = plan.rules.some(function (x) { return latest(ruleKey(x)).dates > 1; });
      if (f && r) return ['met', again ? 'Results are recorded over time.' : 'Record each new measurement as you make it.'];
      return f || r ? ['partly', (f ? 'The next review date' : 'The measurement frequency') + ' is missing.'] : ['missing'];
    },
    examples: function () { return plan.examples ? ['missing', plan.examples + ' example row' + (plan.examples === 1 ? '' : 's') + ' from the template ' + (plan.examples === 1 ? 'is' : 'are') + ' still there.'] : ['met']; }
  };
  var LABEL = {met: 'In place', partly: 'Partly', missing: 'Missing'};
  function check() {
    if (!DATA) return;
    var res = DATA.checks.map(function (c) { var r = TESTS[c.test](); return {c: c, st: r[0], note: r[1] || ''}; });
    var met = res.filter(function (r) { return r.st === 'met'; }).length, steps = res.filter(function (r) { return r.c.step; });
    var stepsMet = steps.every(function (r) { return r.st === 'met'; });
    var head = '<p class="lead-s"><b>' + met + ' of ' + res.length + ' in place.</b> ' +
      (stepsMet ? 'The plan covers all seven steps of the guide.' : 'Some steps are missing or only partly done: see below.') + '</p>' +
      '<p class="small">' + (plan.source === 'file' ? 'Read from ' + esc(plan.file) + (plan.known ? ', the GOV.UK template.' : '. It does not look like the GOV.UK template, so some parts may not have been found.') : 'Built on this page.') +
      ' In your return, report a plan that covers every step as in place; where work has started but is not finished, use the In Development option.</p>';
    var list = '<ol class="dq-checks">' + res.map(function (r) {
      var src = r.c.src.map(function (s) { return '<a href="' + esc(s.u) + '">' + esc(s.t) + '</a>'; }).join('; ');
      return '<li class="dq-' + r.st + '"><span class="pill ' + {met: 'yes', partly: 'maybe', missing: 'no'}[r.st] + '">' + LABEL[r.st] + '</span> <b>' + (r.c.step ? 'Step ' + r.c.step + ': ' : '') + esc(r.c.title) + '.</b> ' +
        esc(r.note) + (r.st === 'met' ? '' : ' <span class="dq-fix">' + esc(r.c.fix) + '</span>') + (src ? '<br><span class="src">' + src + '</span>' : '') + '</li>';
    }).join('') + '</ol>';
    var tbl = '';
    if (plan.rules.length) {
      tbl = '<div class="table-wrap" role="region" aria-labelledby="dq-tcap" tabindex="0"><table><caption id="dq-tcap">Rules against their targets (latest result)</caption><thead><tr><th scope="col">Rule</th><th scope="col">Dimension</th><th scope="col">Target</th><th scope="col">Latest</th><th scope="col">Status</th></tr></thead><tbody>' +
        plan.rules.map(function (r) {
          var l = latest(ruleKey(r)), t = frac(r.target), ok = l.last != null && t != null ? l.last >= t : null;
          return '<tr><th scope="row">' + esc((r.id ? r.id + '. ' : '') + (r.rule || '')) + '</th><td>' + esc(dimLabel(r.dim)) + '</td><td>' + pct(t) + '</td><td>' + pct(l.last) + '</td><td>' +
            (ok == null ? 'Not measured' : ok ? 'Meets target' : 'Below target') + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    }
    $('[data-dq-out]').innerHTML = head + list + tbl;
    var sec = $('#dq-result'); sec.hidden = false; sec.focus();
    say(met + ' of ' + res.length + ' checks in place.');
  }
  function dimLabel(id) { var x = DATA && DATA.dims.filter(function (m) { return m.id === id; })[0]; return x ? x.label : (id || ''); }
  function dimId(v) {
    var s = String(v || '').trim().toLowerCase(); if (!s) return '';
    var x = DATA.dims.filter(function (m) { return m.id === s || m.label.toLowerCase() === s; })[0];
    return x ? x.id : s;
  }

  // ---------- the builder ----------
  var uid = 0;
  function field(list, i, f, val) {
    var id = 'dq-' + list + '-' + i + '-' + f[0] + '-' + (uid++), lab = '<label for="' + id + '">' + esc(f[1]) + '</label>', a = ' id="' + id + '" data-f="' + f[0] + '"';
    if (f[2] === 'dim') {   // D-36: options come from the data file, escaped, never from text read back out of the page
      return lab + '<select' + a + '><option value="">Choose</option>' + DATA.dims.map(function (m) { return '<option value="' + esc(m.id) + '"' + (m.id === val ? ' selected' : '') + '>' + esc(m.label) + '</option>'; }).join('') + '</select>';
    }
    if (f[2] === 'prio') return lab + '<select' + a + '><option value="">Choose</option>' + ['High', 'Medium', 'Low'].map(function (p) { return '<option' + (p === val ? ' selected' : '') + '>' + p + '</option>'; }).join('') + '</select>';
    return lab + '<input' + a + ' type="' + (f[2] === 'date' ? 'date' : 'text') + '"' + (f[2] === 'number' ? ' inputmode="decimal"' : '') + ' maxlength="300" autocomplete="off" value="' + esc(val) + '">';
  }
  function render(list) {
    var box = $('[data-rows="' + list + '"]');
    box.innerHTML = plan[list].map(function (row, i) {
      return '<div class="dq-row" data-i="' + i + '">' + ROWS[list].map(function (f) { return '<div class="field">' + field(list, i, f, row[f[0]] == null ? '' : row[f[0]]) + '</div>'; }).join('') +
        '<p><button type="button" class="btn secondary small" data-del>Remove</button></p></div>';
    }).join('');
  }
  function renderAll() {
    Object.keys(ROWS).forEach(render);
    $$('[name]', form).forEach(function (el) { if (el.name in plan.details) el.value = plan.details[el.name] || ''; });
  }
  function save() { store.set(KEY, plan); }
  function edited(e) {
    var el = e.target, row = el.closest('.dq-row');
    if (row) { var list = row.parentNode.getAttribute('data-rows'); plan[list][+row.getAttribute('data-i')][el.getAttribute('data-f')] = el.value; }
    else if (el.name in plan.details) plan.details[el.name] = el.value;
    if (plan.source === 'file') plan.source = 'edited';
    save();
  }
  form.addEventListener('input', edited);
  form.addEventListener('change', edited);   // selects and date pickers in older browsers only fire change
  form.addEventListener('click', function (e) {
    var add = e.target.closest('[data-add]'), del = e.target.closest('[data-del]');
    if (add) {
      var list = add.getAttribute('data-add'), o = {}; ROWS[list].forEach(function (f) { o[f[0]] = ''; });
      if (list === 'rules') o.id = String(plan.rules.length + 1);
      plan[list].push(o); render(list); save();
      var rows = $$('.dq-row', $('[data-rows="' + list + '"]')); var f = $('input,select', rows[rows.length - 1]); if (f) f.focus();
    }
    if (del) { var r = del.closest('.dq-row'), l = r.parentNode.getAttribute('data-rows'); plan[l].splice(+r.getAttribute('data-i'), 1); render(l); save(); say('Removed.'); }
  });
  $('[data-check]').addEventListener('click', check);
  $('[data-clear-plan]').addEventListener('click', function () {
    plan = empty(); store.del(KEY); renderAll(); $('#dq-result').hidden = true; say('Plan cleared from this device.');
  });

  // ---------- reading the GOV.UK template (.xlsx) on the device ----------
  async function unzip(buf) {
    var u8 = new Uint8Array(buf), dv = new DataView(buf), dec = new TextDecoder();
    if (u8[0] === 0xD0 && u8[1] === 0xCF) throw new Error('protected');
    if (!(u8[0] === 0x50 && u8[1] === 0x4B)) throw new Error('notxlsx');
    var eocd = -1;
    for (var i = u8.length - 22; i >= Math.max(0, u8.length - 65557); i--) { if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; } }
    if (eocd < 0) throw new Error('notxlsx');
    var n = dv.getUint16(eocd + 10, true), off = dv.getUint32(eocd + 16, true), files = {};
    for (var k = 0; k < n; k++) {
      if (off + 46 > u8.length || dv.getUint32(off, true) !== 0x02014b50) throw new Error('notxlsx');
      var nl = dv.getUint16(off + 28, true), el = dv.getUint16(off + 30, true), cl = dv.getUint16(off + 32, true);
      files[dec.decode(u8.subarray(off + 46, off + 46 + nl))] = {m: dv.getUint16(off + 10, true), c: dv.getUint32(off + 20, true), u: dv.getUint32(off + 24, true), h: dv.getUint32(off + 42, true)};
      off += 46 + nl + el + cl;
    }
    return async function (name) {
      var f = files[name]; if (!f) return null;
      if (f.u > MAXPART) throw new Error('toolarge');
      var s = f.h + 30 + dv.getUint16(f.h + 26, true) + dv.getUint16(f.h + 28, true), data = u8.subarray(s, s + f.c);
      if (f.m === 0) return dec.decode(data);
      if (f.m !== 8 || typeof DecompressionStream === 'undefined') throw new Error('unsupported');
      var out = await new Response(new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer();
      return dec.decode(out);
    };
  }
  function xml(t) { var x = new DOMParser().parseFromString(t, 'application/xml'); if (x.getElementsByTagName('parsererror').length) throw new Error('notxlsx'); return x; }
  function kids(x, tag) { return [].slice.call(x.getElementsByTagName(tag)); }
  function col(ref) { var m = /^([A-Z]+)/.exec(ref || ''), n = 0; if (!m) return -1; for (var i = 0; i < m[1].length; i++) n = n * 26 + m[1].charCodeAt(i) - 64; return n - 1; }
  function excelDate(n) { var t = Date.UTC(1899, 11, 30) + Math.round(n) * 864e5; return new Date(t).toISOString().slice(0, 10); }
  async function readWorkbook(buf) {
    var get = await unzip(buf), wb = await get('xl/workbook.xml'), rels = await get('xl/_rels/workbook.xml.rels');
    if (!wb || !rels) throw new Error('notxlsx');
    var ss = await get('xl/sharedStrings.xml'), strings = ss ? kids(xml(ss), 'si').map(function (si) { return kids(si, 't').map(function (t) { return t.textContent; }).join(''); }) : [];
    var target = {}; kids(xml(rels), 'Relationship').forEach(function (r) { target[r.getAttribute('Id')] = r.getAttribute('Target'); });
    var sheets = {};
    for (var s of kids(xml(wb), 'sheet')) {
      var t = target[s.getAttribute('r:id')] || target[s.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships', 'id')];
      if (!t) continue;
      var path = t.charAt(0) === '/' ? t.slice(1) : 'xl/' + t.replace(/^\.\//, ''), body = await get(path);
      if (!body) continue;
      sheets[s.getAttribute('name').trim()] = kids(xml(body), 'row').map(function (row) {
        var out = [];
        kids(row, 'c').forEach(function (c) {
          var tt = c.getAttribute('t'), v = c.getElementsByTagName('v')[0], val = '';
          if (tt === 's' && v) val = strings[+v.textContent] || '';
          else if (tt === 'inlineStr') val = kids(c, 't').map(function (x) { return x.textContent; }).join('');
          else if (v) val = tt === 'str' || tt === 'b' || tt === 'e' ? v.textContent : Number(v.textContent);
          var i = col(c.getAttribute('r')); out[i < 0 ? out.length : i] = val;
        });
        return out;
      });
    }
    return sheets;
  }
  function norm(v) { return String(v == null ? '' : v).replace(/\s+/g, ' ').trim(); }
  function fromWorkbook(sheets, name) {
    var T = DATA.template, p = empty(); p.source = 'file'; p.file = name;
    p.known = T.sheets.filter(function (s) { return sheets[s]; }).length >= 6;
    var det = sheets.Details || [];
    det.forEach(function (r) {
      var lab = norm(r[0]), val = norm(r.slice(1).filter(function (x) { return norm(x) !== ''; })[0]);
      var key = {'Data set title:': 'title', 'Scope/Description:': 'scope', 'Technical lead:': 'lead', 'Measurement frequency:': 'freq', 'Next review date:': 'review'}[lab];
      if (key && val) p.details[key] = key === 'review' && /^\d+(\.\d+)?$/.test(val) ? excelDate(+val) : val;
    });
    function table(sheet) {
      var t = T.tables[sheet], rows = sheets[sheet]; if (!rows) return [];
      var h = rows.findIndex(function (r) { return r && norm(r[0]) === t.first; }); if (h < 0) return [];
      var head = rows[h].map(norm), out = [];
      rows.slice(h + 1).forEach(function (r) {
        if (!r) return; var cells = r.map(norm).filter(function (x) { return x; }); if (!cells.length) return;
        if (cells[0] === 'Examples below' || t.guide.some(function (g) { return cells[0].slice(0, 60) === g; })) return;
        if (t.examples.indexOf(cells[0].slice(0, 60) + (cells.length > 1 ? ' | ' + cells[1].slice(0, 60) : '')) >= 0) { p.examples++; return; }
        var o = {}; head.forEach(function (k, i) { if (k) o[k.toLowerCase()] = r[i]; }); o._row = r; out.push(o);
      });
      out.head = head; return out;
    }
    var pick = function (o, k) { for (var key in o) if (key.indexOf(k) === 0) return norm(o[key]); return ''; };
    p.items = table('Data Criticality Matrix').map(function (o) { return {item: pick(o, 'data item') || pick(o, 'reference'), purpose: pick(o, 'purpose'), crit: pick(o, 'business criticality')}; });
    p.issues = table('Data Issues Log').map(function (o) { return {ref: pick(o, 'data issue reference'), desc: pick(o, 'description')}; });
    // the template stores 98% as 0.98; the form asks for a percentage, so show 98
    var asPct = function (v) { var n = frac(v); return n == null ? norm(v) : String(Math.round(n * 1e4) / 100); };
    p.rules = table('Rules').map(function (o) { return {id: pick(o, 'id'), rule: pick(o, 'rule'), dim: dimId(pick(o, 'data quality dimension')), metric: pick(o, 'metric'), method: pick(o, 'method'), target: asPct(pick(o, 'target'))}; });
    var res = table('Results');
    if (res.length) {
      var head = res.head;
      res.forEach(function (o) {
        head.forEach(function (h, i) {
          if (i < 4 || !h) return; var v = o._row[i]; if (v === '' || v == null) return;
          var date = /^\d+(\.\d+)?$/.test(h) ? excelDate(+h) : h;
          p.results.push({id: pick(o, 'id'), date: date, value: asPct(v)});
        });
        if (!p.rules.some(function (r) { return ruleKey(r) === pick(o, 'id').toLowerCase(); }) && pick(o, 'rule')) p.rules.push({id: pick(o, 'id'), rule: pick(o, 'rule'), metric: pick(o, 'metric'), target: asPct(pick(o, 'target')), dim: ''});
      });
    }
    p.causes = table('Causes').map(function (o) { return {issue: pick(o, 'data quality issue'), priority: pick(o, 'priority'), root: pick(o, 'root cause')}; });
    p.actions = table('Actions').map(function (o) {
      var due = o._row[3]; return {issue: pick(o, 'data quality issue'), action: pick(o, 'action to rectify'), owner: pick(o, 'action owner'), due: typeof due === 'number' ? excelDate(due) : norm(due)};
    });
    (sheets['Cover page'] || []).forEach(function (r) { var st = norm(r[0]); if (/^[1-7]$/.test(st) && /^(y|yes|done|complete|completed|x|✓|✔|true)$/i.test(norm(r[2]))) p.cover[st] = true; });
    return p;
  }
  var MSG = {protected: 'This file is protected, for example by a sensitivity label or a password, so it cannot be read here. Save an unprotected copy and open that.',
    notxlsx: 'This does not look like an Excel workbook (.xlsx). Open the GOV.UK template you filled in.', toolarge: 'This file is too large to read here.',
    unsupported: 'This browser cannot open compressed workbooks. Try a recent version of Edge, Chrome, Firefox or Safari.'};
  $('#dq-file').addEventListener('change', async function (e) {
    var f = e.target.files && e.target.files[0]; if (!f) return;
    var out = $('[data-dq-out]'), sec = $('#dq-result');
    try {
      if (f.size > MAXFILE) throw new Error('toolarge');
      plan = fromWorkbook(await readWorkbook(await f.arrayBuffer()), f.name.slice(0, 120));
      save(); renderAll(); check();
    } catch (err) {
      out.innerHTML = '<p class="warn-box">' + esc(MSG[err.message] || 'This file could not be read. ' + MSG.notxlsx) + '</p>'; sec.hidden = false; sec.focus(); say('The file could not be read.');
    }
    e.target.value = '';
  });

  // ---------- DQV export, linked to the DCAT record ----------
  function slug(t) { return String(t || 'data-set').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'data-set'; }
  function dqv() {
    var t = plan.details.title || 'Untitled data set', iri = /^https:\/\/[^\s<>"]+$/.test(plan.details.iri) ? plan.details.iri : 'https://example.invalid/dataset/' + slug(t);
    var at = function (s) { return iri + (iri.indexOf('#') >= 0 ? '-' : '#') + 'dq-' + slug(s); };
    var lit = function (v, ty) { return {'@value': String(v), '@type': ty}; }, ref = function (x) { return {'@id': x}; };
    var g = [], ds = {'@id': iri, '@type': 'dcat:Dataset', 'dcterms:title': t, 'dqv:hasQualityMeasurement': [], 'dqv:hasQualityAnnotation': []};
    var lead = plan.details.lead ? {'@type': 'prov:Agent', 'rdfs:label': plan.details.lead} : null;
    var duties = [];
    plan.rules.forEach(function (r, i) {
      var m = at('rule-' + (r.id || i + 1)), node = {'@id': m, '@type': 'dqv:Metric', 'skos:prefLabel': r.rule || ('Rule ' + (r.id || i + 1)), 'dqv:expectedDataType': ref('xsd:decimal')};
      if (r.metric) node['skos:definition'] = r.metric;
      if (r.method) node['dcterms:description'] = r.method;
      if (DATA.dims.some(function (x) { return x.id === r.dim; })) node['dqv:inDimension'] = ref('dq:' + r.dim);
      g.push(node);
      var tg = frac(r.target);
      if (tg != null) duties.push({'@type': 'odrl:Duty', 'odrl:target': ref(iri), 'odrl:constraint': {'@type': 'odrl:Constraint', 'prov:wasDerivedFrom': ref(m), 'odrl:leftOperand': ref('odrl:percentage'), 'odrl:operator': ref('odrl:gteq'), 'odrl:rightOperand': lit(Math.round(tg * 1e4) / 100, 'xsd:decimal')}});
      plan.results.filter(function (x) { return String(x.id).trim().toLowerCase() === ruleKey(r) && frac(x.value) != null; }).forEach(function (x, j) {
        var mm = {'@id': at('result-' + (r.id || i + 1) + '-' + (x.date || j)), '@type': 'dqv:QualityMeasurement', 'dqv:computedOn': ref(iri), 'dqv:isMeasurementOf': ref(m), 'dqv:value': lit(Math.round(frac(x.value) * 1e4) / 100, 'xsd:decimal')};
        if (/^\d{4}-\d{2}-\d{2}$/.test(x.date)) mm['dcterms:date'] = lit(x.date, 'xsd:date');
        if (lead) mm['prov:wasAttributedTo'] = lead;
        g.push(mm); ds['dqv:hasQualityMeasurement'].push(ref(mm['@id']));
      });
    });
    g.push({'@id': at('plan'), '@type': ['dqv:QualityPolicy', 'odrl:Set'], 'dcterms:title': 'Data quality action plan: ' + t,
      'dcterms:conformsTo': ref(DATA.guide), 'odrl:obligation': duties});
    plan.causes.forEach(function (c, i) {
      var acts = plan.actions.filter(function (a) { return norm(a.issue) && norm(a.issue) === norm(c.issue); }).map(function (a) { return a.action + (a.owner ? ' (owner: ' + a.owner + (a.due ? ', by ' + a.due : '') + ')' : ''); });
      var body = [c.issue, c.priority ? 'Priority: ' + c.priority : '', c.root ? 'Root cause: ' + c.root : '', acts.length ? 'Actions: ' + acts.join('; ') : ''].filter(Boolean).join('. ');
      var a = {'@id': at('issue-' + (i + 1)), '@type': 'dqv:QualityAnnotation', 'oa:motivatedBy': ref('dqv:qualityAssessment'), 'oa:hasTarget': ref(iri),
        'oa:hasBody': {'@type': 'oa:TextualBody', 'rdf:value': body, 'dcterms:format': 'text/plain', 'dcterms:language': 'en'}};
      g.push(a); ds['dqv:hasQualityAnnotation'].push(ref(a['@id']));
    });
    g.unshift(ds);
    return {'@context': {dcat: 'http://www.w3.org/ns/dcat#', dcterms: 'http://purl.org/dc/terms/', dqv: 'http://www.w3.org/ns/dqv#', odrl: 'http://www.w3.org/ns/odrl/2/', oa: 'http://www.w3.org/ns/oa#',
      prov: 'http://www.w3.org/ns/prov#', skos: 'http://www.w3.org/2004/02/skos/core#', rdf: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#', rdfs: 'http://www.w3.org/2000/01/rdf-schema#',
      xsd: 'http://www.w3.org/2001/XMLSchema#', dq: DATA.ns}, '@graph': g};
  }
  $('[data-dqv]').addEventListener('click', function () {
    var blob = new Blob([JSON.stringify(dqv(), null, 1)], {type: 'application/ld+json'}), a = d.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'dqap-' + slug(plan.details.title) + '.jsonld'; d.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    say(/^https:\/\//.test(plan.details.iri) ? 'Downloaded.' : 'Downloaded. Add the catalogue identifier to link it to the right record.');
  });
  $('[data-print]').addEventListener('click', function () { window.print(); });

  // ---------- self-assessment for an equivalent process ----------
  var eqf = $('.dq-equiv'), eq = store.get(EQKEY) || {};
  $$('input', eqf).forEach(function (i) { var v = eq[i.name]; if (i.type === 'radio') i.checked = v === i.value; else if (v) i.value = v; });
  eqf.addEventListener('input', function (e) { var i = e.target; eq[i.name] = i.value; store.set(EQKEY, eq); });
  $('[data-equiv]').addEventListener('click', function () {
    var steps = DATA.equiv, ans = steps.map(function (s) { return {s: s, v: eq['eq' + s.step] || '', e: eq['eqe' + s.step] || ''}; });
    var yes = ans.filter(function (a) { return a.v === 'yes'; }), none = ans.filter(function (a) { return !a.v; });
    var out = '';
    if (none.length === steps.length) out = '<p>Answer the questions for each step first.</p>';
    else {
      var gaps = ans.filter(function (a) { return a.v !== 'yes'; });
      out = yes.length === steps.length ?
        '<p class="lead-s"><b>Your process covers all seven steps.</b> It can count as an equivalent to a DQAP. Keep the evidence where your organisation holds its records; the return asks only for a reference.</p>' :
        '<p class="lead-s"><b>Your process covers ' + yes.length + ' of 7 steps.</b> To count as an equivalent it needs all seven. If work has started on the rest, use the In Development option in your return.</p>' +
        '<ul>' + gaps.map(function (a) { return '<li><b>Step ' + a.s.step + ': ' + esc(a.s.title) + '</b> (' + (a.v === 'partly' ? 'partly' : a.v === 'no' ? 'not covered' : 'not answered') + '). It needs: ' + esc(a.s.covers.join('; ').toLowerCase()) + '. <a href="' + esc(a.s.u) + '">What the guide says (GOV.UK)</a></li>'; }).join('') + '</ul>';
      var ev = ans.filter(function (a) { return a.e; });
      if (ev.length) out += '<p class="small">Evidence you noted: ' + ev.map(function (a) { return 'step ' + a.s.step + ', ' + esc(a.e); }).join('; ') + '.</p>';
    }
    $('[data-eq-out]').innerHTML = out; var s = $('#eq-result'); s.hidden = false; s.focus(); say('Result shown.');
  });

  fetch('dqap-data.json').then(function (r) { return r.json(); }).then(function (j) {
    DATA = j; renderAll();
    if (plan.rules.length || plan.items.length || plan.details.title) say('Your saved plan is loaded.');
  }).catch(function () { $('#dq-file').disabled = true; });
})();
