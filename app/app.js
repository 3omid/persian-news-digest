// اپ خلاصه اخبار - جایگزین ربات تلگرام. همین یک کد روی وب (PWA)، اپ اندروید و اپ ویندوز اجرا می‌شه.
// داده‌ها از data.json میان (build_app_data.py هر ۱۵ دقیقه تو GitHub Actions می‌سازدش).
// سرعت: آخرین داده‌ی گرفته‌شده تو گوشی ذخیره می‌شه و اپ بلافاصله با همون باز می‌شه، بعد تو
// پس‌زمینه نسخه‌ی تازه رو می‌گیره - یعنی هیچ‌وقت منتظر اینترنت نمی‌مونی.
// مسیریابی با hash (#key) تا دکمه‌ی «برگشت» گوشی هم درست کار کنه.

const $ = (id) => document.getElementById(id);
const menuEl = $("menu");
const sectionEl = $("section");
const heroEl = $("hero");
const titleEl = $("title");
const updatedEl = $("updated");
const backBtn = $("back");
const refreshBtn = $("refresh");

const APP_TITLE = "خلاصه اخبار";
// نسخه‌ی اپ - با desktop/package.json یکی نگهش دار (نسخه‌ی اندروید/ویندوز از اون‌جا میاد)
const APP_VERSION = "1.0.0";
const homeEl = $("home");
const NEW_MINUTES = 60;
const CACHE_KEY = "newsData";
const faNum = new Intl.NumberFormat("fa-IR");
const inNativeApp = /Electron|NewsDigestAndroid/.test(navigator.userAgent);
let data = null;

const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function splitLabel(label) {
  // «💰 اخبار اقتصادی» → ["💰", "اخبار اقتصادی"]
  const i = label.indexOf(" ");
  return i > 0 ? [label.slice(0, i), label.slice(i + 1)] : ["", label];
}

function timeAgo(iso) {
  if (!iso) return "";
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "همین الان";
  if (mins < 60) return `${faNum.format(mins)} دقیقه پیش`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${faNum.format(hours)} ساعت پیش`;
  return `${faNum.format(Math.round(hours / 24))} روز پیش`;
}

const isLatin = (s) => /^[\s\W\d]*[A-Za-z]/.test(s);
const isNew = (it) => it.published && Date.now() - new Date(it.published).getTime() < NEW_MINUTES * 60000;

// رنگ هر دکمه از تم: ۷ رنگ کاشی‌های اپ شیفت، و «همه اخبار» رنگ کارت «شیفت من».
function tileVar(s, i) {
  return s.key === "all" ? "my" : `t${i % 7}`;
}

// داده‌ی زنده از سرور Cloudflare (functions/api/data.js، حداکثر چند دقیقه قدیمی). اگه در دسترس
// نبود، data.json که GitHub Actions می‌سازه (کندتر به‌روز می‌شه، ولی همیشه هست).
const LIVE_API = location.hostname.endsWith(".pages.dev") ? "api/data" : "https://persian-news-digest.pages.dev/api/data";

async function fetchText(url, opts = {}, timeoutMs = 8000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { ...opts, signal: ctrl.signal });
    if (!resp.ok) throw new Error(resp.status);
    return await resp.text();
  } finally {
    clearTimeout(timer);
  }
}

async function fetchData(force) {
  try {
    // بار اول بعد از خالی شدن کش، سرور چند ثانیه منبع‌ها رو می‌گیره؛ بعدش فوریه
    const text = await fetchText(LIVE_API, {}, 12000);
    if (JSON.parse(text).sections) return text;
  } catch (e) { /* میریم سراغ data.json */ }
  return fetchText("data.json", { cache: force ? "reload" : "no-cache" });
}

// تیتر خبرهایی که همین الان رسیدن (تو داده‌ی قبلی نبودن) - چند ثانیه رنگی نشون داده می‌شن
const justIn = new Set();
const titlesOf = (sections) => new Set((sections || []).flatMap((s) => (s.items || []).map((it) => it.title)));
function markJustIn(oldSections, newSections) {
  if (!oldSections) return;
  const old = titlesOf(oldSections);
  for (const t of titlesOf(newSections)) if (!old.has(t)) justIn.add(t);
  setTimeout(() => justIn.clear(), 15000);
}

let loading = 0;
function busy(on) {
  loading += on ? 1 : -1;
  refreshBtn.classList.toggle("spinning", loading > 0);
}

async function load({ force = false } = {}) {
  busy(true);
  try {
    const text = await fetchData(force);
    const fresh = JSON.parse(text);
    markJustIn(data?.sections, fresh.sections);
    data = fresh;
    store.set(CACHE_KEY, text);
    render();
  } catch (e) {
    if (!data) {
      updatedEl.textContent = "اتصال برقرار نشد";
      menuEl.innerHTML = `<div class="error">الان نتونستم اخبار رو بگیرم. اینترنت رو چک کن و دکمه‌ی 🔄 رو بزن.</div>`;
    } else {
      updatedEl.textContent = `آفلاین · آخرین به‌روزرسانی: ${timeAgo(data.generated_at)}`;
    }
  } finally {
    busy(false);
  }
}

// وقتی یک دکمه زده می‌شه: اول خبرهای ذخیره‌شده فوری، بعد همون بخش زنده از سرور
async function refreshSection(key) {
  if (!data || !key || key === "weather" || !data.sections.some((s) => s.key === key)) return;
  busy(true);
  try {
    const fresh = JSON.parse(await fetchText(`${LIVE_API}?section=${encodeURIComponent(key)}`, {}, 10000));
    const sec = fresh.sections?.[0];
    if (!sec || sec.key !== key) return;
    const idx = data.sections.findIndex((s) => s.key === key);
    markJustIn([data.sections[idx]], [sec]);
    data.sections[idx] = sec;
    if (fresh.prices) data.prices = fresh.prices;
    data.generated_at = fresh.generated_at;
    store.set(CACHE_KEY, JSON.stringify(data));
    if (decodeURIComponent(location.hash.slice(1)) === key) render();
  } catch (e) {
    /* بدون اینترنت یا سرور: همون خبرهای ذخیره‌شده می‌مونه */
  } finally {
    busy(false);
  }
}

function sectionCount(s) {
  if (s.type === "rates") return s.rates.length ? `${faNum.format(s.rates.length)} قیمت` : "";
  return s.items.length ? `${faNum.format(s.items.length)} خبر` : "خبری نیست";
}

function sectionPeek(s) {
  if (s.type === "rates") {
    const usd = s.rates.find((r) => r.unit === "تومان");
    return usd ? `${usd.label}: ${faNum.format(usd.value)}` : "";
  }
  return s.items[0]?.title || "";
}

function renderMenu() {
  menuEl.innerHTML = data.sections.map((s, i) => {
    const [emoji, text] = splitLabel(s.label);
    const v = tileVar(s, i);
    const wide = s.key === "all" ? " wide" : "";
    const fresh = s.type === "news" ? s.items.filter(isNew).length : 0;
    const peek = s.key === "all" ? "" : `<span class="peek"${isLatin(sectionPeek(s)) ? ' dir="ltr"' : ""}>${esc(sectionPeek(s))}</span>`;
    return `<button class="tile${wide}" data-key="${esc(s.key)}" style="background: var(--${v}-g)">
      ${fresh ? `<span class="new-count">${faNum.format(fresh)} تازه</span>` : ""}
      <span class="emoji">${emoji}</span>
      <span class="label">${esc(text)}</span>
      ${peek}
      <span class="count">${sectionCount(s)}</span>
    </button>`;
  }).join("");
}

function renderNews(items) {
  if (!items.length) return `<div class="empty">فعلاً خبر جدیدی تو این دسته پیدا نشد.</div>`;
  return `<ul class="news">${items.map((it) => `
    <li${justIn.has(it.title) ? ' class="just-in"' : ""}><a href="${esc(it.link)}" target="_blank" rel="noopener">
      <p class="title"${isLatin(it.title) ? ' dir="ltr"' : ""}>${esc(it.title)}</p>
      <div class="meta">
        ${isNew(it) ? `<span class="badge-new">تازه</span>` : ""}
        ${it.category ? `<span class="chip">${esc(it.category)}</span>` : ""}
        <span>${esc(it.source)}</span>
        ${it.published ? `<span>${timeAgo(it.published)}</span>` : ""}
      </div>
    </a></li>`).join("")}</ul>`;
}

function renderRates(rates) {
  if (!rates.length) return `<div class="empty">فعلاً قیمت‌ها در دسترس نیست.</div>`;
  const top = data.prices?.length
    ? `${Home.renderPrices(data.prices, { big: true })}<h3 class="sub-title">همه‌ی قیمت‌ها</h3>` : "";
  return `${top}<div class="rates">${rates.map((r) => `
    <div class="rate-row">
      <span>${esc(r.label)}</span>
      <span class="value">${faNum.format(r.value)}<span class="unit">${esc(r.unit)}</span></span>
    </div>`).join("")}</div>`;
}

function showPage(title, html, gradient, accent) {
  homeEl.hidden = true;
  sectionEl.hidden = false;
  backBtn.hidden = false;
  titleEl.textContent = title;
  heroEl.style.background = gradient;
  sectionEl.style.setProperty("--sec", accent);
  sectionEl.innerHTML = html;
}

function render() {
  const key = decodeURIComponent(location.hash.slice(1));
  // صفحه‌ی آب‌وهوا به data.json وابسته نیست
  if (key === "weather") {
    showPage("🌦 آب‌وهوا", Home.renderWeatherPage(), "var(--clock-g)", "var(--accent)");
    return;
  }
  if (!data) return;
  updatedEl.textContent = `به‌روزرسانی: ${timeAgo(data.generated_at)}`;
  updatedEl.title = data.generated_at_label || "";

  const idx = data.sections.findIndex((s) => s.key === key);
  const section = data.sections[idx];
  if (!section) {
    renderMenu();
    $("px-list").innerHTML = Home.renderPrices(data.prices) || `<p class="note">قیمت‌ها در دسترس نیست</p>`;
    $("news-updated").textContent = timeAgo(data.generated_at);
    homeEl.hidden = false;
    sectionEl.hidden = true;
    backBtn.hidden = true;
    titleEl.textContent = APP_TITLE;
    heroEl.style.background = "";
    return;
  }
  // تو هر بخش، بنر بالا و خط کنار خبرها رنگ همون دکمه رو می‌گیرن
  const v = tileVar(section, idx);
  showPage(section.label, section.type === "rates" ? renderRates(section.rates) : renderNews(section.items),
    `var(--${v}-g)`, `var(--${v})`);
}

menuEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".tile");
  if (!btn) return;
  location.hash = encodeURIComponent(btn.dataset.key);
});
backBtn.addEventListener("click", () => {
  if (history.length > 1) history.back();
  else location.hash = "";
});
refreshBtn.addEventListener("click", () => {
  load({ force: true });
  Home.mountWeather($("wx-row"), true).then(() => { if (location.hash === "#weather") render(); });
});
window.addEventListener("hashchange", () => {
  render();
  window.scrollTo(0, 0);
  refreshSection(decodeURIComponent(location.hash.slice(1)));
});
// تا وقتی اپ بازه، هر ۲ دقیقه خودش خبرهای تازه رو می‌گیره
setInterval(() => {
  if (document.visibilityState !== "visible") return;
  const key = decodeURIComponent(location.hash.slice(1));
  if (key && key !== "weather") refreshSection(key);
  else load();
}, 2 * 60 * 1000);
document.addEventListener("visibilitychange", () => {
  // وقتی دوباره اپ رو باز می‌کنی، داده رو بی‌صدا تازه کن
  if (document.visibilityState === "visible") { load(); Home.mountWeather($("wx-row")); }
});

// --- انتخاب تم (مثل اپ شیفت) ---
const picker = $("picker");
let pickStart = null;
function showPickerState() {
  const i = THEMES.findIndex((t) => t.id === Theme.style);
  const nameEl = $("pk-name");
  nameEl.innerHTML = `<bdi>${esc(THEMES[Math.max(0, i)].name)}</bdi>`;
  nameEl.style.animation = "none"; void nameEl.offsetWidth; nameEl.style.animation = "";
  $("pk-count").textContent = `${i + 1} / ${THEMES.length}`;
  picker.querySelectorAll(".seg button").forEach((b) => b.classList.toggle("on", b.dataset.mode === Theme.mode));
}
function stepTheme(d) {
  const i = THEMES.findIndex((t) => t.id === Theme.style);
  Theme.setStyle(THEMES[(i + d + THEMES.length) % THEMES.length].id, false);
  showPickerState();
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const s = document.createElement("div");
    s.className = "sweep" + (d > 0 ? " back" : "");
    s.addEventListener("animationend", () => s.remove());
    document.body.appendChild(s);
  }
}
function openPicker() {
  pickStart = { style: Theme.style, mode: Theme.mode };
  picker.hidden = false;
  document.body.classList.add("picking");
  showPickerState();
}
function closePicker(keep) {
  if (keep) Theme.save();
  else { Theme.setStyle(pickStart.style, false); Theme.setMode(pickStart.mode, false); }
  picker.hidden = true;
  document.body.classList.remove("picking");
}
$("theme-btn").addEventListener("click", () => (picker.hidden ? openPicker() : closePicker(true)));
$("pk-next").addEventListener("click", () => stepTheme(1));
$("pk-prev").addEventListener("click", () => stepTheme(-1));
$("pk-apply").addEventListener("click", () => closePicker(true));
$("pk-cancel").addEventListener("click", () => closePicker(false));
picker.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
  Theme.setMode(b.dataset.mode, false);
  showPickerState();
}));
// کشیدن صفحه به چپ/راست = تم بعدی/قبلی (فقط وقتی نوار تم بازه؛ کشیدن عمودی همون اسکرول می‌مونه)
let touchFrom = null;
document.addEventListener("touchstart", (e) => {
  touchFrom = !picker.hidden && e.touches.length === 1 ? [e.touches[0].clientX, e.touches[0].clientY] : null;
}, { passive: true });
document.addEventListener("touchend", (e) => {
  if (!touchFrom) return;
  const dx = e.changedTouches[0].clientX - touchFrom[0], dy = e.changedTouches[0].clientY - touchFrom[1];
  touchFrom = null;
  if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) stepTheme(dx > 0 ? 1 : -1);
}, { passive: true });
document.addEventListener("keydown", (e) => {
  if (picker.hidden) return;
  if (e.key === "ArrowLeft") stepTheme(1);
  else if (e.key === "ArrowRight") stepTheme(-1);
  else if (e.key === "Escape") closePicker(false);
  else if (e.key === "Enter") closePicker(true);
});

// --- راهنمای نصب (فقط تو مرورگر؛ تو اپ اندروید/ویندوز لازم نیست) ---
const installBox = $("install");
const installText = $("install-text");
const installBtn = $("install-btn");
const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone || inNativeApp;
const dismissed = store.get("installDismissed") === "1";
let deferredPrompt = null;
if (inNativeApp) $("downloads").hidden = true;
// گزارش ساعتی فقط روی GitHub Pages ساخته می‌شه
if (location.hostname.endsWith(".pages.dev")) $("report-link").href = "https://3omid.github.io/persian-news-digest/report.html";

if (!standalone && !dismissed) {
  if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
    installText.textContent = "برای نصب روی آیفون: تو سافاری دکمه‌ی اشتراک‌گذاری (مربع با فلش رو به بالا) رو بزن، بعد «Add to Home Screen».";
    installBox.hidden = false;
  }
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installText.textContent = "این اپ رو روی دستگاهت نصب کن تا مثل یک برنامه‌ی معمولی بازش کنی.";
    installBtn.hidden = false;
    installBox.hidden = false;
  });
}
installBtn.addEventListener("click", async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  installBox.hidden = true;
});
$("install-close").addEventListener("click", () => {
  installBox.hidden = true;
  store.set("installDismissed", "1");
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

// شروع: اول فوری با داده‌ی ذخیره‌شده، بعد نسخه‌ی تازه از اینترنت
try { data = JSON.parse(store.get(CACHE_KEY)); } catch (e) { data = null; }
$("version").textContent = `نسخه ${APP_VERSION.replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d])}`;
Home.mountClocks($("clocks"));
Home.mountWeather($("wx-row")).then(() => { if (location.hash === "#weather") render(); });
render();
load();
