// داده‌ی اپ (همون ساختار data.json که build_app_data.py می‌سازه)، این‌بار زنده روی Cloudflare:
// آخرین خبرهای هر دکمه + قیمت‌های صفحه اصلی + جدول طلا و ارز. functions/api/data.js هر چند
// دقیقه یک‌بار این رو صدا می‌زنه و نتیجه رو کش می‌کنه.
// منابع از cloudflare/app_config.js میان (ساخته‌شده از config.py با export_app_config.py).

import CONFIG from "./app_config.js";

const ITEMS_PER_CATEGORY = 12;
const ITEMS_PER_SOURCE = 6;
// تو هر بخش از هر منبع حداکثر این‌قدر خبر، تا یک منبع کل لیست رو پر نکنه
const MAX_PER_SOURCE_IN_SECTION = 3;
const SPARK_DAYS = 30;
const UA = { "User-Agent": "Mozilla/5.0 (compatible; NewsDigest/1.0)" };

const TGJU_TICKER = ["https://call4.tgju.org/ajax.json", "https://call3.tgju.org/ajax.json", "https://call2.tgju.org/ajax.json"];
const TGJU_HISTORY = (slug) => `https://api.tgju.org/v1/market/indicator/summary-table-data/${slug}?length=${SPARK_DAYS + 10}&start=0`;
const BOC_USDCAD = `https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=${SPARK_DAYS + 15}`;

// قیمت‌های صفحه اصلی (مثل DASHBOARD_PRICES در build_app_data.py)
const DASHBOARD_PRICES = [
  { key: "usd", label: "دلار آمریکا", slug: "price_dollar_rl" },
  { key: "cad", label: "دلار کانادا", slug: null },
  { key: "sekee", label: "سکه تمام (امامی)", slug: "sekee" },
  { key: "nim", label: "نیم سکه", slug: "nim" },
  { key: "geram18", label: "طلای ۱۸ عیار (گرم)", slug: "geram18" },
];

// هر منبع حداکثر FEED_TTL ثانیه تو لبه‌ی Cloudflare کش می‌شه (خبر تازه حداکثر یک دقیقه دیرتر)؛
// منبعی که جواب نده بعد از چند ثانیه کنار گذاشته می‌شه تا بقیه منتظر نمونن.
const FEED_TTL = 60;
async function get(url, as = "text", timeoutMs = 6000) {
  const resp = await fetch(url, { headers: UA, signal: AbortSignal.timeout(timeoutMs), cf: { cacheTtl: FEED_TTL, cacheEverything: true } });
  if (!resp.ok) throw new Error(`${resp.status} ${url}`);
  return as === "json" ? resp.json() : resp.text();
}

// ---------- RSS / Atom (بدون کتابخونه: فقط چند تا عبارت باقاعده، و فقط چند آیتم اول) ----------
const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decode(s) {
  return s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/<[^>]+>/g, "")
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&([a-z]+);/gi, (m, n) => ENTITIES[n.toLowerCase()] ?? m)
    .replace(/[‪-‮]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
const tag = (block, name) => {
  const m = block.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)</${name}>`, "i"));
  return m ? decode(m[1]) : "";
};

export function parseFeed(xml) {
  const items = [];
  const re = /<(item|entry)[\s>][\s\S]*?<\/\1>/gi;
  let m;
  while ((m = re.exec(xml)) && items.length < ITEMS_PER_SOURCE) {
    const b = m[0];
    const title = tag(b, "title");
    if (!title) continue;
    let link = tag(b, "link");
    if (!link) link = (b.match(/<link[^>]*href="([^"]+)"/i) || [])[1] || "";
    const when = tag(b, "pubDate") || tag(b, "published") || tag(b, "updated") || tag(b, "dc:date");
    const t = when ? Date.parse(when) : NaN;
    items.push({ title, link: decode(link), published: Number.isNaN(t) ? null : new Date(t).toISOString() });
  }
  return items;
}

// سایت‌های آمار/شرط‌بندی که Google News قاطی خبرها میاره و خبر نیستن
const NOT_NEWS = /odds|sofascore|transfermarkt|flashscore|forza football|fotmob|besoccer|livescore|\bTOD\b/i;

// تیترهای Google News آخرشون « - اسم سایت» دارن؛ اسم سایت میره تو منبع
function cleanGoogleNews(it) {
  if (it.link.includes("news.google.com")) {
    const i = it.title.lastIndexOf(" - ");
    if (i > 0 && it.title.length - i < 60) return { ...it, title: it.title.slice(0, i).trim(), source: it.title.slice(i + 3).trim() };
  }
  return it;
}

// منبعی که تا SOFT_MS جواب نده، این‌بار بدون اون جواب می‌دیم (مثلا ایرنا از سرورهای خارج از
// ایران اصلا جواب نمی‌ده). خودِ درخواستش پشت صحنه (waitUntil) ادامه پیدا می‌کنه و اگه برسه، تو
// کش لبه می‌مونه و دفعه‌ی بعد فوریه - این‌طوری یک منبع کند کل اپ رو کند نمی‌کنه.
const SOFT_MS = 2500;
// منبعی که اخیرا کند بوده: تا SLOW_MEMORY_MS دیگه منتظرش نمی‌مونیم (فقط پشت صحنه امتحانش می‌کنیم)
const SLOW_MEMORY_MS = 10 * 60 * 1000;
const slowUntil = new Map();

// categories: فقط این دسته‌ها (برای وقتی یک دکمه زده می‌شه)؛ خالی = همه
async function fetchAllNews(categories, waitUntil) {
  const wanted = Object.entries(CONFIG.sources).filter(([cat]) => !categories || categories.includes(cat));
  const unique = new Map();
  for (const [, list] of wanted) for (const s of list) unique.set(s.url, s);
  const fetched = new Map();
  await Promise.all([...unique.keys()].map(async (url) => {
    const full = get(url).then(parseFeed).catch(() => []);
    const wait = (slowUntil.get(url) || 0) > Date.now() ? 0 : SOFT_MS;
    let timer;
    const late = new Promise((r) => { timer = setTimeout(() => r(null), wait); });
    const items = await Promise.race([full, late]);
    clearTimeout(timer);
    if (items === null) {
      slowUntil.set(url, Date.now() + SLOW_MEMORY_MS);
      if (waitUntil) waitUntil(full);
    } else if (items.length) {
      slowUntil.delete(url);
    }
    fetched.set(url, items || []);
  }));

  const news = {};
  for (const [cat, list] of wanted) {
    const seen = new Set();
    const items = [];
    for (const src of list) {
      // از هر منبع فقط چند خبر آخرش (فیدها خودشون از جدید به قدیم مرتب‌ان)
      const own = (fetched.get(src.url) || [])
        .filter((it) => !seen.has(it.title))
        .sort((a, b) => (b.published || "").localeCompare(a.published || ""))
        .slice(0, MAX_PER_SOURCE_IN_SECTION);
      for (const it of own) {
        seen.add(it.title);
        const clean = cleanGoogleNews({ ...it, source: src.name.replace("تلگرام: ", "") });
        if (!NOT_NEWS.test(clean.source) && !/live score|best odds|h2h/i.test(clean.title)) items.push(clean);
      }
    }
    // خبرهای بدون تاریخ میرن ته لیست
    items.sort((a, b) => (b.published || "").localeCompare(a.published || ""));
    news[cat] = items.slice(0, ITEMS_PER_CATEGORY);
  }
  return news;
}

function unique(groups, perGroup = 0) {
  const seen = new Set(), out = [];
  for (const items of groups) {
    let taken = 0;
    for (const it of items) {
      if (seen.has(it.title)) continue;
      seen.add(it.title);
      out.push(it);
      if (perGroup && ++taken >= perGroup) break;
    }
  }
  return out;
}

// ---------- قیمت‌ها (tgju + بانک مرکزی کانادا) ----------
const num = (s) => Number(String(s).replace(/,/g, "").trim());

async function tgjuTicker() {
  for (const url of TGJU_TICKER) {
    try {
      const cur = (await get(url, "json"))?.current;
      if (cur && typeof cur === "object") return cur;
    } catch { /* سرور بعدی */ }
  }
  return {};
}

// تاریخچه‌ی روزانه به تومان: [[YYYY-MM-DD, تومان], ...] از قدیم به جدید
async function tgjuHistory(slug) {
  try {
    const rows = (await get(TGJU_HISTORY(slug), "json"))?.data || [];
    return rows
      .map((r) => [String(r[6]).split("/").map((x) => x.padStart(2, "0")).join("-"), num(r[3]) / 10])
      .filter(([d, v]) => d.length === 10 && v > 0)
      .sort((a, b) => a[0].localeCompare(b[0]));
  } catch {
    return [];
  }
}

async function usdCadHistory() {
  try {
    const obs = (await get(BOC_USDCAD, "json"))?.observations || [];
    // با recent=… جدیدترین روز اول میاد؛ از قدیم به جدید مرتب می‌شه
    return obs.map((o) => [o.d, Number(o.FXUSDCAD?.v)]).filter(([, v]) => v > 0).sort((a, b) => a[0].localeCompare(b[0]));
  } catch {
    return [];
  }
}

// قیمت لحظه‌ای فقط وقتی به آخرین قیمت جدول تاریخچه نزدیکه (±۳۰٪)، وگرنه احتمال خطا (مثل _prefer_live)
function preferLive(live, fallback) {
  if (!live) return fallback;
  if (!fallback) return live;
  const r = live / fallback;
  return r >= 0.7 && r <= 1.3 ? live : fallback;
}

const pct = (now, prev) => (now && prev ? Math.round(((now - prev) / prev) * 10000) / 100 : null);

function cadSeries(usdHist, cadHist) {
  // دلار کانادا به تومان = دلار/تومان ÷ USD/CAD (آخرین نرخ بانک کانادا تا همون روز)
  const out = [];
  let j = -1;
  for (const [d, usd] of usdHist) {
    while (j + 1 < cadHist.length && cadHist[j + 1][0] <= d) j++;
    if (j >= 0) out.push([d, usd / cadHist[j][1]]);
  }
  return out;
}

async function buildPrices() {
  const [ticker, usdHist, cadHist, ...goldHists] = await Promise.all([
    tgjuTicker(), tgjuHistory("price_dollar_rl"), usdCadHistory(),
    ...DASHBOARD_PRICES.filter((p) => p.slug && p.key !== "usd").map((p) => tgjuHistory(p.slug)),
  ]);
  const hist = { usd: usdHist, cad: cadSeries(usdHist, cadHist) };
  DASHBOARD_PRICES.filter((p) => p.slug && p.key !== "usd").forEach((p, i) => { hist[p.key] = goldHists[i]; });

  const live = (slug) => {
    const e = ticker[slug];
    const p = e ? num(e.p) / 10 : 0;
    return { price: p > 0 ? p : null, change: e && e.dp !== "" && Math.abs(Number(e.dp)) <= 30 ? Number(e.dp) : null };
  };
  const lastOf = (h) => (h.length ? h[h.length - 1][1] : null);

  const usdNow = preferLive(live("price_dollar_rl").price, lastOf(usdHist));
  const usdCad = lastOf(cadHist);
  const today = new Date().toISOString().slice(0, 10);

  const prices = [];
  for (const p of DASHBOARD_PRICES) {
    const now = p.key === "usd" ? usdNow
      : p.key === "cad" ? (usdNow && usdCad ? usdNow / usdCad : null)
      : preferLive(live(p.slug).price, lastOf(hist[p.key]));
    if (!now) continue;
    const past = hist[p.key].filter(([d]) => d < today).map(([, v]) => v).slice(-SPARK_DAYS);
    // بعد از نیمه‌شب تهران، tgju تغییر روز جدید رو صفر می‌کنه؛ اون موقع با بسته‌ی روز قبل مقایسه می‌شه
    let change = p.slug ? live(p.slug).change : null;
    if (!change) change = pct(now, past[past.length - 1]);
    prices.push({ key: p.key, label: p.label, value: Math.round(now), unit: "تومان", change, spark: [...past.map(Math.round), Math.round(now)] });
  }

  // جدول کامل «طلا و ارز» (مثل _rates_snapshot)
  const rates = [];
  if (usdCad) rates.push({ label: "۱ دلار آمریکا", value: Math.round(usdCad * 10000) / 10000, unit: "دلار کانادا" });
  if (usdNow) rates.push({ label: "دلار بازار آزاد ایران", value: Math.round(usdNow), unit: "تومان" });
  for (const g of CONFIG.goldIndicators) {
    const v = live(g.slug).price;
    if (v) rates.push({ label: g.label, value: Math.round(v), unit: "تومان" });
  }
  const g18 = live("geram18").price;
  if (g18) rates.push({ label: "طلای دست دوم (تقریبی)", value: Math.round(g18 * 0.99), unit: "تومان" });
  return { prices, rates };
}

// ---------- کل داده ----------
export const SECTION_KEYS = CONFIG.menu.map((m) => m.key);

// دسته‌های خبری‌ای که یک دکمه لازم داره. «همه اخبار» فقط دسته‌هایی که خودشون دکمه دارن
// (مهاجرت کانادا و بازی و گجت فقط تو گزارش ساعتی‌ان) - تا تعداد درخواست‌ها زیر سقف رایگان
// Cloudflare (۵۰ درخواست بیرونی برای هر جواب) بمونه.
function categoriesFor(key) {
  if (key === "gold_currency") return [];
  if (key === "all") return [...new Set(SECTION_KEYS.filter((k) => k !== "all").flatMap(categoriesFor))];
  if (key === "سیاسی") return ["سیاسی داخلی", "سیاسی خارجی"];
  return CONFIG.sources[key] ? [key] : [];
}

// ---------- ترجمه‌ی تیترهای غیرفارسی به فارسی (Google Translate رایگان) ----------
const hasPersian = (t) => /[\u0600-\u06FF]/.test(t);
const translated = new Map(); // تیتر → ترجمه (تو حافظه‌ی سرور، تا یک تیتر دوباره ترجمه نشه)

// اول آدرسی که افزونه‌ی ترجمه‌ی Chrome استفاده می‌کنه (از سرورهای Cloudflare جواب می‌ده و چند تیتر
// رو با یک درخواست ترجمه می‌کنه)؛ اگه نشد، آدرس معمولی Google Translate (که Cloudflare رو گاهی می‌بنده).
async function translateBatch(titles) {
  try {
    const qs = titles.map((t) => `q=${encodeURIComponent(t)}`).join("&");
    const resp = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl=fa&${qs}`, {
      headers: UA, signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) throw new Error(`translate ${resp.status}`);
    let out = await resp.json();
    if (titles.length === 1 && typeof out[0] === "string") out = [out];
    if (!Array.isArray(out) || out.length !== titles.length) throw new Error("translate: count mismatch");
    titles.forEach((t, i) => {
      const fa = Array.isArray(out[i]) ? out[i][0] : out[i];
      if (typeof fa === "string" && fa.trim()) translated.set(t, fa.trim());
    });
    return;
  } catch { /* راه دوم */ }
  const body = new URLSearchParams({ q: titles.join("\n") });
  const resp = await fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=fa&dt=t", {
    method: "POST", body, headers: { ...UA, "Content-Type": "application/x-www-form-urlencoded" }, signal: AbortSignal.timeout(5000),
  });
  if (!resp.ok) throw new Error(`translate ${resp.status}`);
  const lines = (await resp.json())[0].map((seg) => seg[0]).join("").split("\n");
  if (lines.length !== titles.length) throw new Error("translate: line count mismatch");
  titles.forEach((t, i) => { if (lines[i].trim()) translated.set(t, lines[i].trim()); });
}

async function translateTitles(sections) {
  const todo = [...new Set(sections.flatMap((s) => (s.items || []).map((it) => it.title)))]
    .filter((t) => !hasPersian(t) && !translated.has(t));
  // دسته‌های حداکثر ~۳۵۰۰ حرفی، هم‌زمان
  const batches = [];
  let cur = [], len = 0;
  for (const t of todo) {
    if (len + t.length > 1500 && cur.length) { batches.push(cur); cur = []; len = 0; }
    cur.push(t.replace(/\n/g, " ")); len += t.length + 1;
  }
  if (cur.length) batches.push(cur);
  await Promise.all(batches.slice(0, 5).map((b) => translateBatch(b).catch(() => {})));
  if (translated.size > 3000) translated.clear();
  for (const s of sections) {
    for (const it of s.items || []) {
      const fa = translated.get(it.title);
      if (fa) { it.title_orig = it.title; it.title = fa; }
    }
  }
}

function makeSection({ label, key }, news, rates) {
  if (key === "gold_currency") return { key, label, type: "rates", rates };
  if (key === "all") {
    return { key, label, type: "news", items: unique(Object.entries(news).map(([cat, items]) => items.map((it) => ({ ...it, category: cat }))), 1) };
  }
  if (key === "سیاسی") {
    return { key, label, type: "news", items: unique(["سیاسی داخلی", "سیاسی خارجی"].map((cat) => (news[cat] || []).map((it) => ({ ...it, category: cat })))) };
  }
  return { key, label, type: "news", items: news[key] || [] };
}

// section: کلید یک دکمه → فقط داده‌ی همون بخش (سریع‌تر)؛ خالی → همه‌چیز
export async function buildData(section, waitUntil) {
  const menu = section ? CONFIG.menu.filter((m) => m.key === section) : CONFIG.menu;
  const cats = section ? categoriesFor(section) : categoriesFor("all");
  const needPrices = !section || section === "gold_currency";
  const [news, priceData] = await Promise.all([
    cats.length ? fetchAllNews(cats, waitUntil) : {},
    needPrices ? buildPrices() : null,
  ]);
  const sections = menu.map((m) => makeSection(m, news, priceData?.rates || []));
  await translateTitles(sections);
  const out = { generated_at: new Date().toISOString(), source: "live", api_version: 5, sections };
  if (priceData) out.prices = priceData.prices;
  return out;
}
