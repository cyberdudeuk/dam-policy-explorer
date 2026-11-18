/* DAM Policy Explorer offline support. Caches only this app's own files; never anything from other sites.
   Pages: network first, so people see the latest version, with the cached copy when offline. Other files: cache first. */
var VERSION = 'dpe-1.1.0';
var FILES = ["about.html", "accessibility.html", "ask.html", "asset-test.html", "assets/app-icon.svg", "assets/barcode.svg", "assets/checker.js", "assets/explorer.css", "assets/explorer.js", "assets/hero.svg", "assets/icon-192.png", "assets/icon-512.png", "assets/icon-outline-32.png", "assets/page.js", "assets/process-ui.js", "assets/process.js", "assets/qr.svg", "assets/style.css", "capabilities.html", "embed.html", "explorer-data.json", "glossary.html", "index.html", "people.html", "policy.html", "questions.html", "resources.html", "return.html", "staticwebapp.config.json", "team.html", "templates/left-out-template.csv", "templates/question-log-template.csv", "templates/return-log-template.csv", "templates/return-template.csv", "manifest.webmanifest"];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) { return c.addAll(FILES); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k.indexOf('dpe-') === 0 && k !== VERSION; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  if (req.mode === 'navigate' || /\.html$/.test(url.pathname)) {
    e.respondWith(fetch(req).then(function (r) { var copy = r.clone(); caches.open(VERSION).then(function (c) { c.put(req, copy); }); return r; })
      .catch(function () { return caches.match(req, {ignoreSearch: true}).then(function (m) { return m || caches.match('index.html'); }); }));
    return;
  }
  e.respondWith(caches.match(req, {ignoreSearch: true}).then(function (m) { return m || fetch(req); }));
});
