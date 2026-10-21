// ویجت‌های صفحه اصلی: ساعت تهران و تورنتو، آب‌وهوای مشهد/تورنتو/آرورا، و قیمت طلا و ارز.
// ساعت عقربه‌ای و ایموجی آب‌وهوا از اپ شیفت کپی شده (src/ui/clock.jsx و features/weather).
// آب‌وهوا مستقیم از Open-Meteo گرفته می‌شه (رایگان، بدون کلید) و ۲۰ دقیقه تو دستگاه می‌مونه.

const Home = (() => {
  const fa = new Intl.NumberFormat("fa-IR");
  const fa1 = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 });
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const escH = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- ساعت‌ها ----------
  const CLOCKS = [
    { name: "تهران", tz: "Asia/Tehran", cal: "persian" },
    { name: "تورنتو", tz: "America/Toronto", cal: "gregory" },
  ];

  // اختلاف هر منطقه‌ی زمانی با UTC (دقیقه) - دقیقه‌ای یک‌بار حساب می‌شه، نه هر فریم
  function tzOffsetMin(tz, at = new Date()) {
    const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
      timeZone: tz, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric",
    }).formatToParts(at).map((x) => [x.type, x.value]));
    const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute);
    return Math.round((asUtc - Math.floor(at.getTime() / 60000) * 60000) / 60000);
  }

  function clockSvg(size) {
    const c = size / 2;
    let ticks = "";
    for (let i = 0; i < 12; i++) {
      const a = (i * 30 * Math.PI) / 180, big = i % 3 === 0;
      const r1 = c - (big ? 9 : 7), r2 = c - 3;
      ticks += `<line x1="${c + Math.sin(a) * r1}" y1="${c - Math.cos(a) * r1}" x2="${c + Math.sin(a) * r2}" y2="${c - Math.cos(a) * r2}" stroke="rgba(255,255,255,.75)" stroke-width="${big ? 2.2 : 1.4}" stroke-linecap="round"/>`;
    }
    return `<svg class="analog" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-hidden="true">
      <circle cx="${c}" cy="${c}" r="${c - 2}" fill="rgba(255,255,255,.16)" stroke="rgba(255,255,255,.55)" stroke-width="2"/>${ticks}
      <line class="h" x1="${c}" y1="${c}" x2="${c}" y2="${c - c * 0.45}" stroke="#fff" stroke-width="3.2" stroke-linecap="round"/>
      <line class="m" x1="${c}" y1="${c}" x2="${c}" y2="${c - c * 0.68}" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>
      <line class="s" x1="${c}" y1="${c + c * 0.14}" x2="${c}" y2="${c - c * 0.75}" stroke="#FFE9A8" stroke-width="1.3" stroke-linecap="round"/>
      <circle cx="${c}" cy="${c}" r="2.6" fill="#fff"/></svg>`;
  }

  function mountClocks(el) {
    const size = 58;
    el.innerHTML = `<div class="clock-pair">${CLOCKS.map((k, i) => `
      <div class="clock" data-i="${i}">
        ${clockSvg(size)}
        <div class="clock-text">
          <div class="clock-city">${k.name}</div>
          <div class="clock-digital"></div>
          <div class="clock-date"></div>
        </div>
      </div>`).join('<div class="clock-sep"></div>')}</div>
      <div class="clock-diff"></div><span class="shine-layer" aria-hidden="true"></span>`;

    const nodes = [...el.querySelectorAll(".clock")].map((n) => ({
      h: n.querySelector(".h"), m: n.querySelector(".m"), s: n.querySelector(".s"),
      digital: n.querySelector(".clock-digital"), date: n.querySelector(".clock-date"),
    }));
    let offsets = [], lastMinute = -1, lastSecond = -1;
    const fmtTime = CLOCKS.map((k) => new Intl.DateTimeFormat("fa-IR", { timeZone: k.tz, hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }));
    const fmtDate = CLOCKS.map((k) => new Intl.DateTimeFormat(`fa-IR-u-ca-${k.cal}`, { timeZone: k.tz, weekday: "long", day: "numeric", month: "long" }));
    const turn = (line, deg) => line.setAttribute("transform", `rotate(${deg.toFixed(2)} ${size / 2} ${size / 2})`);

    function draw() {
      const now = new Date();
      const minute = Math.floor(now.getTime() / 60000);
      if (minute !== lastMinute) {
        lastMinute = minute;
        offsets = CLOCKS.map((k) => tzOffsetMin(k.tz, now));
        const diff = (offsets[0] - offsets[1]) / 60;
        el.querySelector(".clock-diff").textContent = `ساعت تهران ${fa1.format(Math.abs(diff))} ساعت ${diff >= 0 ? "جلوتر از" : "عقب‌تر از"} تورنتوئه`;
        nodes.forEach((n, i) => { n.date.textContent = fmtDate[i].format(now); });
      }
      const second = Math.floor(now.getTime() / 1000);
      if (second !== lastSecond) {
        lastSecond = second;
        nodes.forEach((n, i) => { n.digital.textContent = fmtTime[i].format(now); });
      }
      nodes.forEach((n, i) => {
        const local = new Date(now.getTime() + offsets[i] * 60000);
        const s = local.getUTCSeconds() + (reduceMotion ? 0 : local.getUTCMilliseconds() / 1000);
        const m = local.getUTCMinutes() + s / 60;
        const h = (local.getUTCHours() % 12) + m / 60;
        turn(n.h, h * 30); turn(n.m, m * 6); turn(n.s, s * 6);
      });
    }
    // عقربه‌ها مثل ساعت کوارتز نرم می‌چرخن (مثل اپ شیفت)؛ وقتی صفحه دیده نمی‌شه، متوقف
    const loop = () => { if (!el.isConnected || el.offsetParent !== null) draw(); requestAnimationFrame(loop); };
    if (reduceMotion) { draw(); setInterval(draw, 1000); } else loop();
  }

  // ---------- آب‌وهوا ----------
  const CITIES = [
    { name: "مشهد", lat: 36.2605, lon: 59.6168 },
    { name: "تورنتو", lat: 43.6532, lon: -79.3832 },
    { name: "آرورا", lat: 44.0065, lon: -79.4504 },
  ];
  const WEATHER_KEY = "weatherCache";
  const WEATHER_TTL = 20 * 60000;

  function weatherUrl() {
    return "https://api.open-meteo.com/v1/forecast"
      + "?latitude=" + CITIES.map((c) => c.lat).join(",") + "&longitude=" + CITIES.map((c) => c.lon).join(",")
      + "&current=temperature_2m,apparent_temperature,weather_code,is_day,relative_humidity_2m,wind_speed_10m"
      + "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"
      + "&timezone=auto&forecast_days=5";
  }

  // کد هواشناسی WMO → ایموجی (از اپ شیفت) + ماه برای شب صاف
  function weatherEmoji(code, isDay = 1) {
    if (code <= 1 && !isDay) return "🌙";
    if (code === 2 && !isDay) return "☁️";
    if (code === 0) return "☀️";
    if (code <= 2) return "🌤";
    if (code === 3) return "☁️";
    if (code === 45 || code === 48) return "🌫";
    if ([56, 57, 66, 67].includes(code)) return "🧊";
    if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "🌨";
    if (code >= 95) return "⛈";
    if (code >= 51) return "🌧";
    return "🌡";
  }

  function weatherText(code) {
    if (code === 0) return "صاف";
    if (code <= 2) return "کمی ابری";
    if (code === 3) return "ابری";
    if (code === 45 || code === 48) return "مه";
    if ([56, 57, 66, 67].includes(code)) return "باران یخ‌زده";
    if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "برف";
    if (code >= 95) return "رعد و برق";
    if (code >= 80) return "رگبار";
    if (code >= 51) return "باران";
    return "";
  }

  // رنگ کارت از روی خودِ هوا: آسمون آبی روز، سرمه‌ای شب، خاکستری ابر/باران، آبی‌روشن برف
  function weatherSky(code, isDay) {
    if (!isDay) return "linear-gradient(160deg, #1B2350, #3B4A8C)";
    if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "linear-gradient(160deg, #6F95BC, #A9C6E2)";
    if (code >= 51) return "linear-gradient(160deg, #4B5B78, #7486A6)";
    if (code === 3 || code === 45 || code === 48) return "linear-gradient(160deg, #66778F, #93A3B8)";
    return "linear-gradient(160deg, #2F86D8, #6CC0F0)";
  }

  const deg = (t) => `${fa.format(Math.round(t))}°`;

  function loadWeatherCache() {
    try { return JSON.parse(localStorage.getItem(WEATHER_KEY)); } catch (e) { return null; }
  }

  async function fetchWeather(force) {
    const cached = loadWeatherCache();
    if (!force && cached && Date.now() - cached.at < WEATHER_TTL) return cached.data;
    const resp = await fetch(weatherUrl());
    if (!resp.ok) throw new Error(resp.status);
    const data = await resp.json();
    try { localStorage.setItem(WEATHER_KEY, JSON.stringify({ at: Date.now(), data })); } catch (e) {}
    return data;
  }

  function renderWeatherCards(el, data) {
    el.innerHTML = CITIES.map((c, i) => {
      const w = data[i], cur = w.current, d = w.daily;
      return `<a class="wx" href="#weather" style="background:${weatherSky(cur.weather_code, cur.is_day)}">
        <div class="wx-top"><span class="wx-city">${c.name}</span><span class="wx-emoji">${weatherEmoji(cur.weather_code, cur.is_day)}</span></div>
        <div class="wx-temp">${deg(cur.temperature_2m)}</div>
        <div class="wx-range">↑${deg(d.temperature_2m_max[0])} ↓${deg(d.temperature_2m_min[0])}</div>
        <span class="shine-layer" aria-hidden="true"></span>
      </a>`;
    }).join("");
  }

  async function mountWeather(el, force = false) {
    const cached = loadWeatherCache();
    if (cached && !el.children.length) renderWeatherCards(el, cached.data);
    if (!el.children.length) el.innerHTML = CITIES.map((c) => `<div class="wx wx-loading"><span class="wx-city">${c.name}</span><span>…</span></div>`).join("");
    try {
      renderWeatherCards(el, await fetchWeather(force));
    } catch (e) {
      if (!cached) el.innerHTML = `<div class="wx wx-loading" style="grid-column:1/-1">آب‌وهوا الان در دسترس نیست</div>`;
    }
  }

  function renderWeatherPage() {
    const cached = loadWeatherCache();
    if (!cached) return `<div class="empty">آب‌وهوا هنوز گرفته نشده - اینترنت رو چک کن.</div>`;
    const dayName = new Intl.DateTimeFormat("fa-IR", { weekday: "long" });
    const hm = new Intl.DateTimeFormat("fa-IR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC" });
    return `<div class="wx-pages">${CITIES.map((c, i) => {
      const w = cached.data[i], cur = w.current, d = w.daily;
      // طلوع/غروب به وقت محلی خودِ شهر میاد (timezone=auto)؛ برای نمایش، همون عدد رو UTC فرض می‌کنیم
      const t = (iso) => hm.format(new Date(iso + "Z"));
      const days = d.time.map((day, k) => `
        <div class="wx-day">
          <span class="wx-day-name">${k === 0 ? "امروز" : dayName.format(new Date(day + "T12:00:00"))}</span>
          <span class="wx-day-emoji">${weatherEmoji(d.weather_code[k])}</span>
          <span class="wx-day-rain">${d.precipitation_probability_max[k] ? `💧${fa.format(d.precipitation_probability_max[k])}٪` : ""}</span>
          <span class="wx-day-temp"><b>${deg(d.temperature_2m_max[k])}</b> ${deg(d.temperature_2m_min[k])}</span>
        </div>`).join("");
      return `<div class="wx-page">
        <div class="wx-head" style="background:${weatherSky(cur.weather_code, cur.is_day)}">
          <div><div class="wx-city">${c.name}</div><div class="wx-cond">${weatherText(cur.weather_code)}</div></div>
          <div class="wx-big">${weatherEmoji(cur.weather_code, cur.is_day)} ${deg(cur.temperature_2m)}</div>
          <div class="wx-facts">
            <span>حس‌شده ${deg(cur.apparent_temperature)}</span>
            <span>رطوبت ${fa.format(cur.relative_humidity_2m)}٪</span>
            <span>باد ${fa.format(Math.round(cur.wind_speed_10m))} کیلومتر</span>
            <span>طلوع <bdi>${t(d.sunrise[0])}</bdi></span>
            <span>غروب <bdi>${t(d.sunset[0])}</bdi></span>
          </div>
        </div>
        <div class="wx-days">${days}</div>
      </div>`;
    }).join("")}</div>
    <p class="note">منبع: Open-Meteo · به‌روزرسانی هر ۲۰ دقیقه</p>`;
  }

  // ---------- قیمت‌ها ----------
  function spark(values, up) {
    if (!values || values.length < 2) return "";
    const w = 84, h = 28, min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
    const pts = values.map((v, i) => [(i / (values.length - 1)) * w, h - 3 - ((v - min) / span) * (h - 6)]);
    const line = pts.map((p) => p.map((n) => n.toFixed(1)).join(",")).join(" ");
    const color = up ? "var(--up)" : "var(--down)";
    const last = pts[pts.length - 1];
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true">
      <polygon points="0,${h} ${line} ${w},${h}" fill="${color}" opacity=".13"/>
      <polyline points="${line}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${last[0]}" cy="${last[1]}" r="2.4" fill="${color}"/></svg>`;
  }

  function changePill(change) {
    if (change === null || change === undefined) return "";
    const up = change > 0, flat = change === 0;
    return `<span class="chg ${flat ? "flat" : up ? "up" : "down"}">${flat ? "•" : up ? "▲" : "▼"} ${fa.format(Math.abs(change))}٪</span>`;
  }

  function renderPrices(prices, { big = false } = {}) {
    if (!prices?.length) return "";
    return prices.map((p) => {
      const first = p.spark?.[0], up = first === undefined ? (p.change || 0) >= 0 : p.value >= first;
      return `<div class="px${big ? " big" : ""}">
        <div class="px-name">${escH(p.label)}</div>
        ${spark(p.spark, up)}
        <div class="px-val"><b>${fa.format(p.value)}</b><span class="unit">${escH(p.unit)}</span>${changePill(p.change)}</div>
      </div>`;
    }).join("");
  }

  return { mountClocks, mountWeather, renderWeatherPage, renderPrices, fetchWeather };
})();
