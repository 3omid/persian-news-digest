// GET /api/data: داده‌ی زنده‌ی اپ (خبرها + قیمت‌ها) روی Cloudflare Pages.
// برای سرعت: جواب تو کش Cloudflare نگه داشته می‌شه. اگه کمتر از FRESH_MS ازش گذشته باشه همون
// فوری برمی‌گرده؛ اگه قدیمی‌تر باشه، باز هم فوری همون برمی‌گرده و نسخه‌ی تازه پشت صحنه ساخته
// می‌شه (stale-while-revalidate)، پس کاربر هیچ‌وقت منتظر سایت‌های خبری نمی‌مونه.
// همه‌ی نسخه‌ها (سایت GitHub Pages، اپ اندروید، اپ ویندوز) از همین آدرس می‌خونن (CORS باز).
import { buildData } from "../../cloudflare/news.js";

const FRESH_MS = 5 * 60 * 1000;
const CACHE_KEY = "https://news-digest.internal/api/data/v1";
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS" };

export const onRequestOptions = () => new Response(null, { status: 204, headers: CORS });

function respond(body, extra = {}) {
  return new Response(body, {
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=60", ...CORS, ...extra },
  });
}

async function rebuild(cache) {
  const body = JSON.stringify(await buildData());
  // یک روز تو کش می‌مونه، ولی بعد از FRESH_MS پشت صحنه تازه می‌شه
  await cache.put(CACHE_KEY, new Response(body, {
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=86400", "X-Built-At": String(Date.now()) },
  }));
  return body;
}

export async function onRequestGet({ waitUntil }) {
  const cache = caches.default;
  const hit = await cache.match(CACHE_KEY);
  if (hit) {
    const age = Date.now() - Number(hit.headers.get("X-Built-At") || 0);
    if (age > FRESH_MS) waitUntil(rebuild(cache).catch(() => {}));
    return respond(await hit.text(), { "X-Data-Age": String(Math.round(age / 1000)) });
  }
  try {
    return respond(await rebuild(cache), { "X-Data-Age": "0" });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e?.message || e) }), { status: 502, headers: { "Content-Type": "application/json", ...CORS } });
  }
}
