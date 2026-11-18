/* DAM Policy Explorer offline support. Caches only this app's own files; never anything from other sites.
   Pages: network first, so people see the latest version, with the cached copy when offline. Other files: cache first. */
var VERSION = 'dpe-__VERSION__';
var FILES = __FILES__;
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
