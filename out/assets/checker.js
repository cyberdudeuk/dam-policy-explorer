/* The return file check, for the Baseline Return version 3 (24 fields). One set of rules, used by organisations before they
   send a return (return.html) and by The GDS team when a return arrives (team.html), so both sides
   always apply the same checks. It runs only in the browser: nothing you choose is uploaded or sent anywhere.
   Source of every rule: the V3 template's headers, Data Dictionary, User Guide and value lists, as recorded in
   docs/sources.md. Where the template's own value list is not available to us (K, O, P, T, V), the check only asks that
   the field is filled in; it does not guess the list. */
(function (root) {
  'use strict';

  // The 24 fields, in the workbook's order (columns A to X).
  var FIELDS = [
    ['A', 'Unique identifier', 'm', {max: 100}],
    ['B', 'Data asset name', 'm', {max: 200}],
    ['C', 'Description', 'm', {min: 20, max: 2000}],
    ['D', 'Owning department / publisher', 'm', {max: 200}],
    ['E', 'ALB / agency', 'a', {max: 200}],
    ['F', 'Source / provenance', 'a', {max: 1000}],
    ['G', 'Data owner assigned?', 'm', {yesno: 1}],
    ['H', 'Data steward assigned?', 'm', {yesno: 1}],
    ['I', 'Stewardship model', 'o', {list: ['Central', 'Federated', 'Distributed', 'Shared service', 'Other']}],
    ['J', 'Critical purpose number(s)', 'm', {}],
    ['K', 'Primary sharing status', 'r', {}],
    ['L', 'Legal gateway / regulatory basis', 'a', {max: 500}],
    ['M', 'Security classification / marking', 'm', {}],
    ['N', 'Contains personal data?', 'm', {yesno: 1}],
    ['O', 'Source-asset access rights', 'm', {}],
    ['P', 'Primary licence / usage basis', 'm', {}],
    ['Q', 'Asset version / update status', 'r', {max: 100}],
    ['R', 'Metadata recorded in catalogue?', 'm', {list: ['In catalogue', 'Planned', 'Not in catalogue']}],
    ['S', 'Catalogue / metadata reference', 'a', {max: 250}],
    ['T', 'DQ assurance / action plan status', 'm', {}],
    ['U', 'Quality evidence reference', 'o', {max: 250}],
    ['V', 'Discoverability / interoperability status', 'r', {}],
    ['W', 'Geospatial standard applied', 'a', {}],
    ['X', 'Previous ESDA return reference', 'o', {max: 100}]
  ];
  var OBLIGATION = {m: 'Mandatory', a: 'Mandatory if applicable', r: 'Recommended', o: 'Optional'};
  var GEO = ['UPRN', 'USRN', 'GEMINI', 'Other', 'Not applicable'];
  // Our suggested list of assets left out. It is not part of the workbook or the guidance, so its rule only raises questions.
  // Columns follow the scope gate (OFFICIAL) and the four DAM Policy scope principles (DAM Policy FAQs, November 2026).
  var EXCLUSION_COLUMNS = ['Unique identifier', 'Data asset name', 'OFFICIAL', 'Critical purpose', 'Shared', 'Accountable', 'Source asset', 'Reason', 'Decided by (role)', 'Date'];
  var EXCLUSION_OPTIONAL = [5, 6];   // Accountable and Source asset were added on 18 November 2026; older lists without them are still accepted
  var EXCLUSION_OLD = {identifier: 0, title: 1, scopeofficial: 2, scopeboundary: 4, scopepurpose: 3, test1official: 2, test2sharedwithgovernment: 4, test3servesapurpose: 3, reason: 7, decidedby: 8, date: 9};   // headings used before 18 November 2026

  // Four kinds of result. "fix" stops the return being accepted. "ask" means we will ask you about it.
  // "gap" is an honest policy gap: it is accepted and shows us where to help. "tip" is advice only.
  var CHECKS = {
    V1: ['fix', 'The file has all 24 columns of the version 3 template'],
    V2: ['fix', 'The 13 mandatory fields are filled in'],
    V3: ['fix', 'Text fits the length the template allows'],
    V4: ['fix', 'Yes or No questions say Yes or No'],
    V5: ['fix', 'The security marking is OFFICIAL or OFFICIAL-SENSITIVE (SECRET and TOP SECRET data does not go in)'],
    V6: ['fix', 'Critical purposes are numbers from 1 to 7, separated by commas, each used once'],
    V7: ['fix', 'Answers chosen from a list use one of the list’s values'],
    V8: ['fix', 'An asset recorded “In catalogue” gives its catalogue reference'],
    V9: ['fix', 'Geospatial standards come from the list, each used once, and “Not applicable” stands alone'],
    V10: ['fix', 'No asset is marked “Out of scope”'],
    V11: ['fix', 'There are no email addresses: the return does not record people’s names or contact details'],
    V12: ['ask', 'Each identifier is used once, unless the row is an approved version or licence variant'],
    V17: ['fix', 'The template’s worked example has been deleted'],
    V13: ['gap', 'Policy gaps are shown: no data owner, no data steward, not in a catalogue, or a quality gap'],
    V14: ['tip', 'Recommended fields are filled in: sharing status, version and discoverability'],
    V15: ['tip', 'Names spell out abbreviations, and no two assets have almost the same name'],
    V16: ['ask', 'Every asset you left out says which test it failed and why (our suggested list, not part of the workbook)']
  };

  var STOPWORDS = {the: 1, of: 1, and: 1, data: 1, dataset: 1, database: 1, register: 1, records: 1, record: 1, system: 1, uk: 1, national: 1};
  var NOT_ABBREVIATIONS = {OFFICIAL: 1, SENSITIVE: 1, SECRET: 1, TOP: 1, UK: 1, ID: 1};
  var EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+/;

  function key(h) { return String(h || '').replace(/\[[^\]]*\]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ''); }   // "Data owner assigned? [Mandatory]" -> "dataownerassigned"
  var BYKEY = {}; FIELDS.forEach(function (f) { BYKEY[key(f[1])] = f[0]; });

  function parseCSV(text) {
    var t = String(text || '').replace(/^\uFEFF/, ''), rows = [], row = [], field = '', quoted = false;
    for (var i = 0; i < t.length; i++) {
      var c = t[i];
      if (quoted) { if (c === '"') { if (t[i + 1] === '"') { field += '"'; i++; } else quoted = false; } else field += c; }
      else if (c === '"') quoted = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && t[i + 1] === '\n') i++; row.push(field); rows.push(row); row = []; field = ''; }
      else field += c;
    }
    if (field !== '' || row.length) { row.push(field); rows.push(row); }
    rows.forEach(function (r, k) { r.line = k + 1; });              // the row number a spreadsheet shows, kept when blank rows are dropped
    var out = rows.filter(function (r) { return r.some(function (x) { return String(x).trim() !== ''; }); });
    if (quoted) out.unclosed = rows.length;                          // a quote mark was opened and never closed: later rows were swallowed
    return out;
  }
  function words(t) { var o = {}; String(t || '').toLowerCase().split(/[^a-z0-9]+/).forEach(function (w) { if (w.length > 1 && !STOPWORDS[w]) o[w] = 1; }); return o; }
  function likeness(a, b) { var ka = Object.keys(a), kb = Object.keys(b); if (!ka.length || !kb.length) return 0; var n = ka.filter(function (k) { return b[k]; }).length; return n / (ka.length + kb.length - n); }
  function same(a, b) { return String(a || '').trim().toLowerCase() === String(b || '').trim().toLowerCase(); }
  function inList(v, list) { for (var i = 0; i < list.length; i++) if (same(v, list[i])) return list[i]; return null; }
  function yes(v) { return same(v, 'yes'); }
  function no(v) { return same(v, 'no'); }
  function marking(v) { return String(v || '').trim().toUpperCase().replace(/[\s_]+/g, '-'); }   // "Official sensitive" means OFFICIAL-SENSITIVE
  function name(L) { var f = FIELDS.filter(function (x) { return x[0] === L; })[0]; return L + ' (' + f[1] + ')'; }

  function check(returnText, exclusionsText) {
    var result = {file: [], rows: [], exclusions: [], counts: {records: 0, ready: 0, gap: 0, ask: 0, fix: 0, excluded: 0, questions: 0}};
    function fileIssue(id, text, kind) { result.file.push({check: id, kind: kind || CHECKS[id][0], text: text}); }
    var R = parseCSV(returnText);
    if (!R.length) { fileIssue('V1', 'The file is empty.'); return finish(result); }
    if (R.slice(0, 10).every(function (r) { return r.length === 1; }) && R.slice(0, 10).some(function (r) { return /;/.test(r[0]); })) { fileIssue('V1', 'This file uses semicolons between columns. In your spreadsheet program, save it again choosing "CSV UTF-8 (comma delimited)".'); return finish(result); }
    if (R.unclosed) { fileIssue('V1', 'A quote mark opened on or before row ' + R.unclosed + ' is never closed, so rows after it may have been joined together. Check that row in your spreadsheet and save the file again.'); }
    if (/\uFFFD/.test(returnText)) fileIssue('V1', 'Some letters could not be read, so names with accents may look wrong. Save the file again choosing "CSV UTF-8 (comma delimited)".', 'tip');
    // The workbook has title rows above its headings, so look for the heading row in the first ten rows.
    var hi = -1; for (var k = 0; k < Math.min(10, R.length); k++) if (R[k].some(function (h) { return BYKEY[key(h)] === 'A'; })) { hi = k; break; }
    if (hi < 0) { fileIssue('V1', 'The file does not have the version 3 headings, so it cannot be checked. Start from the version 3 template and keep its heading row as it is.'); return finish(result); }
    var at = {}; R[hi].forEach(function (h, i) { var L = BYKEY[key(h)]; if (L && !(L in at)) at[L] = i; });
    var missing = FIELDS.filter(function (f) { return !(f[0] in at); }).map(function (f) { return name(f[0]); });
    if (missing.length) fileIssue('V1', 'These columns are missing: ' + missing.join('; ') + '. Start from the version 3 template and keep its heading row as it is.');
    var extra = R[hi].filter(function (h) { return String(h).trim() && !BYKEY[key(h)]; });
    if (extra.length) fileIssue('V1', 'These columns are not in the template and will be ignored: ' + extra.join(', ') + '.', 'tip');

    var seen = {}, recs = R.slice(hi + 1).map(function (r) { var a = {}; FIELDS.forEach(function (f) { var i = at[f[0]]; a[f[0]] = i == null ? '' : String(r[i] == null ? '' : r[i]).trim(); }); a.line = r.line; return a; });
    recs.forEach(function (a) {
      var out = [];
      function add(id, text, kind) { out.push({check: id, kind: kind || CHECKS[id][0], text: text}); }
      FIELDS.forEach(function (f) {
        var L = f[0], v = a[L], rule = f[3];
        if (!v) { if (f[2] === 'm' && (L in at)) add('V2', name(L) + ' is empty. It must be filled in.'); return; }
        if (rule.max && v.length > rule.max) add('V3', name(L) + ' is ' + v.length + ' characters long. The most it can be is ' + rule.max + '.');
        if (rule.min && v.length < rule.min) add('V3', name(L) + ' is ' + v.length + ' characters long. It needs at least ' + rule.min + ', so it explains what the data is.');
        if (rule.yesno && !yes(v) && !no(v)) add('V4', name(L) + ' must say Yes or No. It says "' + v + '".');
        if (rule.list && !inList(v, rule.list)) add('V7', name(L) + ' must be one of: ' + rule.list.join(', ') + '. It says "' + v + '".');
        if (L !== 'A' && /delete (this row )?before|worked example/i.test(v) || L === 'A' && /^example\b/i.test(v)) add('V17', 'This row looks like the template’s worked example (' + name(L) + ' says "' + v.slice(0, 60) + '"). Delete it before you send the return, so it is not added to the register.');
        if (EMAIL.test(v)) add('V11', name(L) + ' contains an email address. The return does not record people’s names or contact details. Take it out.');
      });
      var m = marking(a.M);
      if (a.M && /SECRET/.test(m) && !/OFFICIAL/.test(m)) add('V5', 'This is marked ' + a.M + '. SECRET and TOP SECRET data does not go in the return. Take this row out.');
      else if (a.M && ['OFFICIAL', 'OFFICIAL-SENSITIVE'].indexOf(m) < 0) add('V5', 'The security marking must be OFFICIAL or OFFICIAL-SENSITIVE. It says "' + a.M + '".');
      else if (a.M && a.M !== m) add('V5', 'Write the security marking exactly as ' + m + ', as the workbook’s list does. It says "' + a.M + '".', 'tip');
      if (a.J) {
        var parts = a.J.split(',').map(function (x) { return x.trim(); }), bad = parts.filter(function (x) { return !/^[1-7]$/.test(x); });
        var twice = parts.filter(function (x, i) { return parts.indexOf(x) !== i; });
        if (bad.length) add('V6', 'Critical purposes must be numbers from 1 to 7, separated by commas, for example "1, 4". It says "' + a.J + '".');
        else if (twice.length) add('V6', 'Critical purpose ' + twice[0] + ' is listed more than once. List each purpose once.');
      }
      if (same(a.R, 'In catalogue') && !a.S) add('V8', 'This asset is recorded as "In catalogue", so ' + name('S') + ' must give the catalogue reference.');
      if (a.W) {
        var g = a.W.split(',').map(function (x) { return x.trim(); }), off = g.filter(function (x) { return !inList(x, GEO); });
        var dup = g.filter(function (x, i) { return g.map(function (y) { return y.toLowerCase(); }).indexOf(x.toLowerCase()) !== i; });
        if (off.length) add('V9', name('W') + ' must come from: ' + GEO.join(', ') + '. "' + off[0] + '" is not on the list.');
        else if (dup.length) add('V9', name('W') + ' lists "' + dup[0] + '" more than once.');
        else if (g.length > 1 && g.some(function (x) { return same(x, 'Not applicable'); })) add('V9', name('W') + ' says "Not applicable" together with a standard. Use "Not applicable" on its own.');
      }
      if (same(a.K, 'Out of scope')) add('V10', 'This asset is marked "Out of scope", so it does not go in the return. Take it out, and add it to your list of assets left out with the reason.');
      var idk = a.A.toLowerCase();
      if (idk) { if (seen[idk]) add('V12', 'Identifier ' + a.A + ' is also used on row ' + seen[idk] + '. That is only allowed for an approved version or licence variant. We will ask you to confirm.'); else seen[idk] = a.line; }
      if (no(a.G)) add('V13', 'No data owner is assigned yet. We will accept the return and record this as a policy gap.');
      if (no(a.H)) add('V13', 'No data steward is assigned yet. We will accept the return and record this as a policy gap.');
      if (same(a.R, 'Not in catalogue')) add('V13', 'The asset is not in a data catalogue yet. We will accept the return and record this as a policy gap.');
      if (/^gap\b/i.test(a.T)) add('V13', 'There is a gap in data quality assurance. We will accept the return, but the asset is not counted as ready until a quality plan is in place.');
      ['K', 'Q', 'V'].forEach(function (L) { if (!a[L]) add('V14', name(L) + ' is empty. It is recommended, and it helps us understand the asset.'); });
      var abbr = ((a.B || '').match(/\b[A-Z]{2,}\b/g) || []).filter(function (w) { return !NOT_ABBREVIATIONS[w]; });
      if (abbr.length) add('V15', 'Spell out ' + abbr.slice(0, 3).join(', ') + ' in the asset name, so anyone can understand it.');
      a.issues = out;
    });
    for (var i = 0; i < recs.length; i++) for (var j = i + 1; j < recs.length; j++) {
      if (recs[i].B && recs[j].B && recs[i].A !== recs[j].A && likeness(words(recs[i].B), words(recs[j].B)) >= 0.8)
        recs[j].issues.push({check: 'V15', kind: 'tip', text: 'The name is almost the same as row ' + recs[i].line + ' ("' + recs[i].B + '"). Check they are different assets.'});
    }
    recs.forEach(function (a) {
      var state = ['fix', 'ask', 'gap'].filter(function (s) { return a.issues.some(function (x) { return x.kind === s; }); })[0] || 'ready';
      result.counts[state]++; result.counts.records++; result.counts.questions += a.issues.filter(function (x) { return x.kind === 'ask'; }).length;
      result.rows.push({line: a.line, identifier: a.A, title: a.B, state: state, issues: a.issues});
    });
    if (exclusionsText) {
      var E = parseCSV(exclusionsText), col = {};
      (E[0] || []).forEach(function (h, i) { var k = key(h), n = EXCLUSION_COLUMNS.map(key).indexOf(k); if (n < 0 && k in EXCLUSION_OLD) n = EXCLUSION_OLD[k]; if (n >= 0 && !(n in col)) col[n] = i; });
      var em = EXCLUSION_COLUMNS.filter(function (c, n) { return !(n in col) && EXCLUSION_OPTIONAL.indexOf(n) < 0; });
      if (em.length) fileIssue('V16', 'The list of assets you left out is missing these columns: ' + em.join(', ') + '.');
      else E.slice(1).forEach(function (r) {
        var get = function (n) { return String(r[col[n]] || '').trim(); }; result.counts.excluded++;
        var tests = [2, 3, 4, 5, 6].filter(function (n) { return n in col; }).map(get);
        var why = !get(7) ? 'Say why it was left out.' : !tests.some(no) ? (tests.every(yes) ? 'Every scope test says "yes", so it should be in the return, not left out.' : 'Say which test it failed by writing "no" against that test.') : '';
        if (why) result.exclusions.push({line: r.line, identifier: get(0), title: get(1), check: 'V16', kind: 'ask', text: why});
        if (r.some(function (x) { return EMAIL.test(x); })) result.exclusions.push({line: r.line, identifier: get(0), title: get(1), check: 'V11', kind: 'fix', text: 'This row contains an email address. Use a role, such as "data owner", not a person’s name or address.'});
      });
    }
    return finish(result);
  }
  function finish(r) {
    if (!r.counts.records && !r.file.some(function (x) { return x.kind === 'fix'; })) r.file.push({check: 'V1', kind: 'fix', text: 'There are no assets in this file. Add one row for each asset under the heading row.'});
    var blocked = r.file.some(function (x) { return x.kind === 'fix'; }) || r.counts.fix > 0 || r.exclusions.some(function (x) { return x.kind === 'fix'; });
    r.verdict = blocked ? 'not-ready' : (r.counts.ask || r.counts.gap || r.exclusions.length) ? 'ready-with-gaps' : 'ready';
    return r;
  }
  function template(kind) { return (kind === 'exclusions' ? EXCLUSION_COLUMNS : FIELDS.map(function (f) { return f[1]; })).map(function (h) { return /[",]/.test(h) ? '"' + h.replace(/"/g, '""') + '"' : h; }).join(',') + '\r\n'; }

  var api = {check: check, parseCSV: parseCSV, template: template, key: key, FIELDS: FIELDS, OBLIGATION: OBLIGATION, GEO: GEO, EXCLUSION_COLUMNS: EXCLUSION_COLUMNS, CHECKS: CHECKS};
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.DAMChecker = api;
})(this);
