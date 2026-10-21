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

// رنگ هر دکمه از تم: ۷ رنگ کاشی‌های اپ شیفت، و «همه اخبار» رنگ کارت «شیفت من».
function tileVar(s, i) {
  return s.key === "all" ? "my" : `t${i % 7}`;
}

async function load({ force = false } = {}) {
  refreshBtn.classList.add("spinning");
  try {
    const resp = await fetch("data.json", { cache: force ? "reload" : "no-cache" });
    if (!resp.ok) throw new Error(resp.status);
    const text = await resp.text();
    data = JSON.parse(text);
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
    refreshBtn.classList.remove("spinning");
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
    const peek = s.key === "all" ? "" : `<span class="peek"${isLatin(sectionPeek(s)) ? ' dir="ltr"' : ""}>${esc(sectionPeek(s))}</span>`;
    return `<button class="tile${wide}" data-key="${esc(s.key)}" style="background: var(--${v}-g)">
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
    <li><a href="${esc(it.link)}" target="_blank" rel="noopener">
      <p class="title"${isLatin(it.title) ? ' dir="ltr"' : ""}>${esc(it.title)}</p>
      <div class="meta">
        ${it.category ? `<span class="chip">${esc(it.category)}</span>` : ""}
        <span>${esc(it.source)}</span>
        ${it.published ? `<span>${timeAgo(it.published)}</span>` : ""}
      </div>
    </a></li>`).join("")}</ul>`;
}

function renderRates(rates) {
  if (!rates.length) return `<div class="empty">فعلاً قیمت‌ها در دسترس نیست.</div>`;
  return `<div class="rates">${rates.map((r) => `
    <div class="rate-row">
      <span>${esc(r.label)}</span>
      <span class="value">${faNum.format(r.value)}<span class="unit">${esc(r.unit)}</span></span>
    </div>`).join("")}</div>`;
}

function render() {
  if (!data) return;
  updatedEl.textContent = `به‌روزرسانی: ${timeAgo(data.generated_at)}`;
  updatedEl.title = data.generated_at_label || "";

  const key = decodeURIComponent(location.hash.slice(1));
  const idx = data.sections.findIndex((s) => s.key === key);
  const section = data.sections[idx];
  if (!section) {
    renderMenu();
    menuEl.hidden = false;
    sectionEl.hidden = true;
    backBtn.hidden = true;
    titleEl.textContent = APP_TITLE;
    heroEl.style.background = "";
    return;
  }
  // تو هر بخش، بنر بالا و خط کنار خبرها رنگ همون دکمه رو می‌گیرن
  const v = tileVar(section, idx);
  heroEl.style.background = `var(--${v}-g)`;
  sectionEl.style.setProperty("--sec", `var(--${v})`);
  menuEl.hidden = true;
  sectionEl.hidden = false;
  backBtn.hidden = false;
  titleEl.textContent = section.label;
  sectionEl.innerHTML = section.type === "rates" ? renderRates(section.rates) : renderNews(section.items);
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
refreshBtn.addEventListener("click", () => load({ force: true }));
window.addEventListener("hashchange", () => { render(); window.scrollTo(0, 0); });
document.addEventListener("visibilitychange", () => {
  // وقتی دوباره اپ رو باز می‌کنی، داده رو بی‌صدا تازه کن
  if (document.visibilityState === "visible") load();
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
render();
load();
