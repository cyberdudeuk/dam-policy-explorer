// Refresh the Government Data portal pages from the published DAM Policy Explorer.
//
// Run it in the browser console while on any page of the portal site, signed in as a site owner, after each
// release of the explorer or the playbooks snapshot. It needs no credentials of its own: it uses your session.
// It only ever writes two pages, by file name, and only the text web part it created; anything else on the page
// (for example the Power Apps web part on the explorer page) is left as it is.
//
// What it does, for each page: fetch the body the build published (out/portal/*.html), check it carries only
// headings, paragraphs, lists, links and emphasis, put it in the page's first text web part, save and publish.
(async () => {
  const SITE = '/sites/developingourdirectorate';
  const SRC = 'https://cyberdudeuk.github.io/dam-policy-explorer/portal/';
  const PAGES = [
    { file: 'DAM-Policy-Explorer.aspx', title: 'DAM Policy Explorer', body: 'explorer.html' },
    { file: 'DAM-capability-playbooks.aspx', title: 'DAM capability playbooks', body: 'playbooks.html' },
  ];
  const ALLOWED = new Set(['h2', 'p', 'ul', 'li', 'a', 'em']);
  const J = { Accept: 'application/json;odata=nometadata', 'Content-Type': 'application/json;odata=nometadata' };
  const digest = (await (await fetch(SITE + '/_api/contextinfo', { method: 'POST', headers: J })).json()).FormDigestValue;
  const H = { ...J, 'X-RequestDigest': digest };
  const api = async (path, body) => {
    const r = await fetch(SITE + '/_api/sitepages/' + path, { method: body === undefined ? 'GET' : 'POST', headers: H, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!r.ok) throw new Error(path + ': HTTP ' + r.status + ' ' + (await r.text()).slice(0, 300));
    return r.status === 204 ? null : r.json().catch(() => null);
  };
  const safe = (html) => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    for (const el of doc.body.querySelectorAll('*')) {
      if (!ALLOWED.has(el.tagName.toLowerCase())) throw new Error('unexpected tag ' + el.tagName);
      for (const at of el.attributes) if (!(el.tagName === 'A' && at.name === 'href')) throw new Error('unexpected attribute ' + at.name);
      if (el.tagName === 'A' && !/^(https:\/\/|[A-Za-z0-9-]+\.aspx$)/.test(el.getAttribute('href'))) throw new Error('unexpected link ' + el.getAttribute('href'));
    }
    return html;
  };
  const report = [];
  for (const p of PAGES) {
    const html = safe(await (await fetch(SRC + p.body, { cache: 'no-store' })).text());
    const found = (await api("pages?$select=Id,FileName&$filter=FileName eq '" + p.file + "'")).value;
    let id = found.length ? found[0].Id : null, canvas = [];
    if (id) {
      await api('pages(' + id + ')/checkoutpage', {});
      canvas = JSON.parse((await api('pages(' + id + ')?$select=CanvasContent1')).CanvasContent1 || '[]');
    } else {
      id = (await api('pages', { Title: p.title, PageLayoutType: 'Article' })).Id;
    }
    const text = canvas.find((c) => c.controlType === 4);
    if (text) text.innerHTML = html;
    else canvas.unshift({ controlType: 4, id: crypto.randomUUID(), position: { zoneIndex: 1, sectionIndex: 1, sectionFactor: 12, layoutIndex: 1, controlIndex: 1 }, innerHTML: html });
    if (!canvas.some((c) => c.controlType === 0)) canvas.push({ controlType: 0, pageSettingsSlice: { isDefaultDescription: true, isDefaultThumbnail: true } });
    await api('pages(' + id + ')/savepage', { Title: p.title, CanvasContent1: JSON.stringify(canvas) });
    await api('pages(' + id + ')/publish', {});
    report.push(p.file + ': updated and published (page ' + id + ', ' + html.length + ' characters)');
  }
  console.log(report.join('\n'));
  return report.join('\n');
})();
