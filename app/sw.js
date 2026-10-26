// Service worker: فایل‌های اپ رو کش می‌کنه تا بدون اینترنت هم اپ باز بشه.
// همه‌چیز (به‌خصوص data.json) همیشه اول از شبکه گرفته می‌شه تا خبر و نسخه‌ی اپ همیشه تازه
// باشن، و فقط اگه اینترنت نبود از کش. (خودِ اپ هم آخرین خبرها رو جدا ذخیره می‌کنه تا فوری باز بشه.)
const CACHE = "news-app-v7";
const SHELL = [
  "./",
  "index.html",
  "app.css",
  "app.js",
  "theme.js",
  "home.js",
  "themes.js",
  "manifest.webmanifest",
  "icons/icon-192.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // آیکون‌ها عوض نمی‌شن - مستقیم از کش
  if (url.pathname.endsWith(".png")) {
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
    return;
  }

  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        if (resp.ok) {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return resp;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
