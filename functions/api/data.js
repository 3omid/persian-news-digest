// GET /api/data            → همه‌ی داده‌ی اپ (خبرها + قیمت‌ها)، وقتی اپ باز می‌شه
// GET /api/data?section=…  → فقط یک بخش (وقتی یک دکمه زده می‌شه)، سریع‌تر
// همیشه تازه: جواب فقط FRESH_MS نگه داشته می‌شه (تا اگه چند نفر هم‌زمان باز کنن، سایت‌های خبری
// اذیت نشن) و بعدش همون لحظه دوباره ساخته می‌شه. خودِ هر منبع خبری هم حداکثر یک دقیقه تو لبه‌ی
// Cloudflare کش می‌شه (cloudflare/news.js)، پس خبر تازه حداکثر حدود یک دقیقه بعد تو اپه.
// اگه ساختن به هر دلیلی خطا بده، آخرین نسخه‌ی موجود برمی‌گرده.
// همه‌ی نسخه‌ها (سایت GitHub Pages، اپ اندروید، اپ ویندوز) از همین آدرس می‌خونن (CORS باز).
import { buildData, SECTION_KEYS } from "../../cloudflare/news.js";

const FRESH_MS = 30 * 1000;
const CACHE_BASE = "https://news-digest.internal/api/data/v3";
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS" };

export const onRequestOptions = () => new Response(null, { status: 204, headers: CORS });

function respond(body, age, status = 200) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-cache", "X-Data-Age": String(age), ...CORS },
  });
}

export async function onRequestGet({ request, waitUntil }) {
  const section = new URL(request.url).searchParams.get("section");
  if (section && !SECTION_KEYS.includes(section)) return respond(JSON.stringify({ error: "unknown section" }), 0, 400);

  const cache = caches.default;
  const key = section ? `${CACHE_BASE}?section=${encodeURIComponent(section)}` : CACHE_BASE;
  const hit = await cache.match(key);
  const age = hit ? Date.now() - Number(hit.headers.get("X-Built-At") || 0) : Infinity;
  if (hit && age < FRESH_MS) return respond(await hit.text(), Math.round(age / 1000));

  try {
    const body = JSON.stringify(await buildData(section || undefined, waitUntil));
    await cache.put(key, new Response(body, {
      headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=86400", "X-Built-At": String(Date.now()) },
    }));
    return respond(body, 0);
  } catch (e) {
    if (hit) return respond(await hit.text(), Math.round(age / 1000));
    return respond(JSON.stringify({ error: String(e?.message || e) }), 0, 502);
  }
}
