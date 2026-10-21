// اپ موبایل خلاصه اخبار - جایگزین ربات تلگرام.
// داده‌ها رو از data.json می‌خونه (که build_app_data.py هر ۱۵ دقیقه تو GitHub Actions می‌سازه)
// و با زدن هر دکمه، همون بخش رو نشون می‌ده. مسیریابی با hash (#key) انجام می‌شه تا دکمه‌ی
// «برگشت» خود گوشی (اندروید) هم درست کار کنه.

const $ = (id) => document.getElementById(id);
const menuEl = $("menu");
const sectionEl = $("section");
const titleEl = $("title");
const updatedEl = $("updated");
const backBtn = $("back");
const refreshBtn = $("refresh");

const APP_TITLE = "خلاصه اخبار";
const faNum = new Intl.NumberFormat("fa-IR");
let data = null;

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

function isLatin(s) {
  return /^[\s\W\d]*[A-Za-z]/.test(s);
}

async function load({ force = false } = {}) {
  refreshBtn.classList.add("spinning");
  try {
    const resp = await fetch("data.json", { cache: force ? "reload" : "no-cache" });
    if (!resp.ok) throw new Error(resp.status);
    data = await resp.json();
  } catch (e) {
    if (!data) {
      updatedEl.textContent = "اتصال برقرار نشد";
      menuEl.innerHTML = `<div class="error" style="grid-column:1/-1">الان نتونستم اخبار رو بگیرم. اینترنت رو چک کن و دوباره امتحان کن.</div>`;
      return;
    }
  } finally {
    refreshBtn.classList.remove("spinning");
  }
  render();
}

function sectionCount(s) {
  if (s.type === "rates") return s.rates.length ? `${faNum.format(s.rates.length)} قیمت` : "";
  return s.items.length ? `${faNum.format(s.items.length)} خبر` : "خبری نیست";
}

function renderMenu() {
  menuEl.innerHTML = data.sections.map((s) => {
    const [emoji, text] = splitLabel(s.label);
    const wide = s.key === "all" ? " wide" : "";
    return `<button class="menu-btn${wide}" data-key="${esc(s.key)}">
      <span class="emoji">${emoji}</span>
      <span class="label">${esc(text)}</span>
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
  renderMenu();

  const key = decodeURIComponent(location.hash.slice(1));
  const section = data.sections.find((s) => s.key === key);
  if (!section) {
    menuEl.hidden = false;
    sectionEl.hidden = true;
    backBtn.hidden = true;
    titleEl.textContent = APP_TITLE;
    return;
  }
  menuEl.hidden = true;
  sectionEl.hidden = false;
  backBtn.hidden = false;
  titleEl.textContent = section.label;
  sectionEl.innerHTML = section.type === "rates" ? renderRates(section.rates) : renderNews(section.items);
}

menuEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".menu-btn");
  if (!btn) return;
  location.hash = encodeURIComponent(btn.dataset.key);
  window.scrollTo(0, 0);
});
backBtn.addEventListener("click", () => {
  if (history.length > 1) history.back();
  else location.hash = "";
});
refreshBtn.addEventListener("click", () => load({ force: true }));
window.addEventListener("hashchange", () => { render(); window.scrollTo(0, 0); });
document.addEventListener("visibilitychange", () => {
  // وقتی دوباره اپ رو باز می‌کنی، اگه داده قدیمیه خودش تازه‌ش کنه
  if (document.visibilityState === "visible" && data &&
      Date.now() - new Date(data.generated_at).getTime() > 10 * 60000) load();
});

// --- راهنمای نصب روی صفحه اصلی گوشی ---
const installBox = $("install");
const installText = $("install-text");
const installBtn = $("install-btn");
const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
let dismissed = false;
try { dismissed = localStorage.getItem("installDismissed") === "1"; } catch (e) {}
let deferredPrompt = null;

if (!standalone && !dismissed) {
  if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
    installText.textContent = "برای نصب روی آیفون: تو سافاری دکمه‌ی اشتراک‌گذاری (مربع با فلش رو به بالا) رو بزن، بعد «Add to Home Screen».";
    installBox.hidden = false;
  }
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installText.textContent = "این اپ رو روی گوشیت نصب کن تا مثل یک برنامه‌ی معمولی از صفحه اصلی بازش کنی.";
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
  try { localStorage.setItem("installDismissed", "1"); } catch (e) {}
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

load();
