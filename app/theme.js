// اعمال تم (کپی از روش اپ شیفت: src/ui/theme.js). این فایل قبل از رسم صفحه اجرا می‌شه
// تا اپ از همون اول با تم انتخابی باز بشه، نه این‌که اول سفید بشه بعد رنگ بگیره.
// حالت «خودکار» مثل اپ شیفت: روز روشن، شب تیره (از روی طلوع/غروب آفتاب تورنتو).

const Theme = (() => {
  const store = {
    get(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };

  const LAT = 43.65, LON = -79.38, rad = Math.PI / 180;
  function isDaytime(date = new Date()) {
    const start = Date.UTC(date.getUTCFullYear(), 0, 0);
    const n = Math.floor((date.getTime() - start) / 864e5);
    const decl = 23.44 * Math.sin(2 * Math.PI * (284 + n) / 365);
    const b = 2 * Math.PI * (n - 81) / 364;
    const eot = 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
    const noon = 12 - LON / 15 - eot / 60;
    const h = Math.acos(Math.min(1, Math.max(-1, -Math.tan(LAT * rad) * Math.tan(decl * rad)))) / rad;
    const sunrise = noon - h / 15, sunset = noon + h / 15;
    const hrs = date.getUTCHours() + date.getUTCMinutes() / 60;
    const after = (a, c) => ((a - c) % 24 + 24) % 24;
    return after(hrs, sunrise) < after(sunset, sunrise);
  }

  let style = store.get("themeStyle", "universal");
  let mode = store.get("themeMode", "auto");

  function find(id) { return THEMES.find((t) => t.id === id) || THEMES[0]; }
  function shownMode() { return mode === "auto" ? (isDaytime() ? "light" : "dark") : mode; }

  function apply() {
    const th = find(style);
    const m = shownMode();
    const p = th[m];
    const gloss = th.gloss ? "linear-gradient(180deg, rgba(255,255,255,0.26) 0%, rgba(255,255,255,0.08) 46%, rgba(255,255,255,0) 54%, rgba(0,0,0,0.08) 100%), " : "";
    const g = (pair) => `${gloss}linear-gradient(135deg, ${pair[0]}, ${pair[1]})`;
    const vars = {
      "--bg": p.bg, "--card": p.card, "--border": p.border, "--text": p.text, "--muted": p.muted, "--accent": p.accent,
      "--radius": th.radius || "12px", "--hero-g": g(th.hero), "--hero": th.hero[0], "--my-g": g(th.my), "--my": th.my[0],
      "--clock-g": `${gloss}linear-gradient(120deg, ${th.clock.join(", ")})`, "--accent2": th.accent2[m === "dark" ? 1 : 0],
    };
    th.tiles.forEach((pair, i) => { vars[`--t${i}-g`] = g(pair); vars[`--t${i}`] = pair[0]; });
    const root = document.documentElement;
    for (const [k, v] of Object.entries(vars)) root.style.setProperty(k, v);
    root.dataset.mode = m;
    root.style.colorScheme = m;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = th.hero[0];
    // تو اپ اندروید: رنگ نوار بالا/پایین گوشی هم با تم عوض بشه
    try { window.NewsApp?.setBarColors(th.hero[0], p.bg); } catch (e) {}
  }

  apply();
  setInterval(() => { if (mode === "auto") apply(); }, 60000);

  return {
    get style() { return style; },
    get mode() { return mode; },
    setStyle(id, save = true) { style = id; if (save) store.set("themeStyle", id); apply(); },
    setMode(m, save = true) { mode = m; if (save) store.set("themeMode", m); apply(); },
    save() { store.set("themeStyle", style); store.set("themeMode", mode); },
    apply,
  };
})();
