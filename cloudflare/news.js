// داده‌ی اپ (همون ساختار data.json که build_app_data.py می‌سازه)، این‌بار زنده روی Cloudflare:
// آخرین خبرهای هر دکمه + قیمت‌های صفحه اصلی + جدول طلا و ارز. functions/api/data.js هر چند
// دقیقه یک‌بار این رو صدا می‌زنه و نتیجه رو کش می‌کنه.
// منابع از cloudflare/app_config.js میان (ساخته‌شده از config.py با export_app_config.py).

import CONFIG from "./app_config.js";

const ITEMS_PER_CATEGORY = 12;
const ITEMS_PER_SOURCE = 6;
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

async function get(url, as = "text", timeoutMs = 8000) {
  const resp = await fetch(url, { headers: UA, signal: AbortSignal.timeout(timeoutMs), cf: { cacheTtl: 120 } });
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

// تیترهای Google News آخرشون « - اسم سایت» دارن؛ اسم سایت میره تو منبع
function cleanGoogleNews(it) {
  if (it.link.includes("news.google.com")) {
    const i = it.title.lastIndexOf(" - ");
    if (i > 0 && it.title.length - i < 60) return { ...it, title: it.title.slice(0, i).trim(), source: it.title.slice(i + 3).trim() };
  }
  return it;
}

async function fetchAllNews() {
  const unique = new Map();
  for (const list of Object.values(CONFIG.sources)) for (const s of list) unique.set(s.url, s);
  const fetched = new Map();
  await Promise.all([...unique.keys()].map(async (url) => {
    try {
      fetched.set(url, parseFeed(await get(url)));
    } catch {
      fetched.set(url, []);
    }
  }));

  const news = {};
  for (const [cat, list] of Object.entries(CONFIG.sources)) {
    const seen = new Set();
    const items = [];
    for (const src of list) {
      for (const it of fetched.get(src.url) || []) {
        if (seen.has(it.title)) continue;
        seen.add(it.title);
        items.push(cleanGoogleNews({ ...it, source: src.name.replace("تلگرام: ", "") }));
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
  // برای عیب‌یابی: زمان فید لحظه‌ای و آخرین روز تاریخچه (اپ ازشون استفاده نمی‌کنه)
  const debug = {
    ticker_ts: ticker.price_dollar_rl?.ts || null, ticker_dp: ticker.price_dollar_rl?.dp ?? null,
    ticker_p: ticker.price_dollar_rl?.p || null, usd_hist_last: usdHist.slice(-2), cad_last: cadHist.slice(-1),
  };
  return { prices, rates, debug };
}

// ---------- کل داده ----------
export async function buildData() {
  const [news, { prices, rates, debug }] = await Promise.all([fetchAllNews(), buildPrices()]);
  const sections = CONFIG.menu.map(({ label, key }) => {
    if (key === "gold_currency") return { key, label, type: "rates", rates };
    if (key === "all") {
      return { key, label, type: "news", items: unique(Object.entries(news).map(([cat, items]) => items.map((it) => ({ ...it, category: cat }))), 1) };
    }
    if (key === "سیاسی") {
      return { key, label, type: "news", items: unique(["سیاسی داخلی", "سیاسی خارجی"].map((cat) => (news[cat] || []).map((it) => ({ ...it, category: cat })))) };
    }
    return { key, label, type: "news", items: news[key] || [] };
  });
  return { generated_at: new Date().toISOString(), source: "live", api_version: 2, prices, sections, debug };
}
