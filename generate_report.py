# -*- coding: utf-8 -*-
"""
ساخت گزارش HTML - نسخه‌ی پاکسازی‌شده و یکدست.
یک کامپوننت واحد (.row) برای همه‌ی ردیف‌های اطلاعاتی (ارز/طلا/کریپتو/شرکت) استفاده می‌شه
تا ظاهر یکدست بمونه. نمودارها همیشه dir="ltr" دارن تا تو صفحه‌ی راست‌به‌چپ به‌هم نریزن.
"""

import base64
import io
import os
import re
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from jalali import format_dual_date, to_persian_digits

CATEGORY_STYLE = {
    "اقتصادی": {"icon": "💰", "color": "#1f3864"},
    "سیاسی داخلی": {"icon": "🏛️", "color": "#6c4f8c"},
    "سیاسی خارجی": {"icon": "🌍", "color": "#2e7d5b"},
    "ورزشی": {"icon": "⚽", "color": "#b5651d"},
    "جنگ ایران": {"icon": "⚠️", "color": "#a5352b"},
    "مهاجرت کانادا": {"icon": "🍁", "color": "#c0392b"},
    "فناوری و IT": {"icon": "💻", "color": "#2874a6"},
    "بازی و گجت": {"icon": "🎮", "color": "#7d3c98"},
}


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", text)


def _fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _line_chart(series, title):
    if not series:
        return ""
    dates = [d for d, v in series]
    values = [v for d, v in series]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    up = values[-1] >= values[0]
    color = "#1e8449" if up else "#c0392b"
    ax.plot(dates, values, color=color, linewidth=2.2)
    ax.fill_between(range(len(values)), values, min(values), color=color, alpha=0.08)
    ax.set_title(title, fontsize=12)
    ax.grid(alpha=0.25)
    step = max(1, len(dates) // 7)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=35, fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    plt.tight_layout()
    return _fig_to_base64(fig)


def _bar_chart(labels, values, title):
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    colors = ["#1e8449" if v >= 0 else "#c0392b" for v in values]
    ax.bar(labels, values, color=colors)
    ax.set_title(title, fontsize=12)
    ax.axhline(0, color="#333", linewidth=0.8)
    ax.grid(alpha=0.25, axis="y")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    plt.tight_layout()
    return _fig_to_base64(fig)


def _chart_overlay(slug, title, note, daily_b64, monthly_b64, yearly_b64):
    """پنجره‌ی نمودار با ۳ تب - همیشه dir=ltr تا نمودارها به‌هم نریزن."""
    return f"""
    <div class="overlay" id="chart-{slug}">
      <div class="overlay-inner">
        <a href="#_" class="overlay-close">✕ بستن</a>
        <h3>{title}</h3>
        {f'<p class="overlay-note">{note}</p>' if note else ''}
        <input type="radio" name="tabs-{slug}" id="{slug}-d" class="tab-radio" checked>
        <input type="radio" name="tabs-{slug}" id="{slug}-m" class="tab-radio">
        <input type="radio" name="tabs-{slug}" id="{slug}-y" class="tab-radio">
        <div class="tab-buttons">
          <label for="{slug}-d">روزانه</label>
          <label for="{slug}-m">ماهانه</label>
          <label for="{slug}-y">سالانه</label>
        </div>
        <div class="tab-panels" dir="ltr">
          <div class="panel panel-d"><img src="data:image/png;base64,{daily_b64}" alt="daily"/></div>
          <div class="panel panel-m"><img src="data:image/png;base64,{monthly_b64}" alt="monthly"/></div>
          <div class="panel panel-y"><img src="data:image/png;base64,{yearly_b64}" alt="yearly"/></div>
        </div>
      </div>
    </div>
    """


def _info_row(icon, title, code, value_text, change_pct=None, href=None, external=False):
    """یک ردیف اطلاعاتی یکدست - برای ارز، طلا، کریپتو، شرکت‌ها. همه یک شکل و یک اندازه."""
    change_html = ""
    if change_pct is not None:
        up = change_pct >= 0
        cls = "up" if up else "down"
        arrow = "▲" if up else "▼"
        change_html = f'<span class="row-change {cls}">{arrow} {to_persian_digits(f"{abs(change_pct):.2f}")}٪</span>'

    inner = f"""
      <div class="row-icon">{icon}</div>
      <div class="row-main">
        <div class="row-title">{title}{f' <span class="row-code">{code}</span>' if code else ''}</div>
      </div>
      <div class="row-value">
        <div class="row-price">{value_text}</div>
        {change_html}
      </div>
    """
    if href:
        target = ' target="_blank"' if external else ''
        return f'<a class="row" href="{href}"{target}>{inner}</a>'
    return f'<div class="row">{inner}</div>'


def _toman_hero_pair(toman_rates, resampled_currencies):
    usd_toman = toman_rates.get("USD")
    cad_toman = toman_rates.get("CAD")
    if not usd_toman or not cad_toman:
        return ""
    usd_cad_daily = resampled_currencies.get("USD/CAD", {}).get("daily", [])
    day_change = 0
    if len(usd_cad_daily) > 1:
        latest, prev = usd_cad_daily[-1][1], usd_cad_daily[-2][1]
        day_change = -((latest - prev) / prev * 100) if prev else 0
    up = day_change >= 0
    return f"""
    <div class="hero-pair">
      <div class="hero-card">
        <div class="hero-label">💵 دلار آمریکا</div>
        <div class="hero-value">{to_persian_digits(f"{usd_toman:,.0f}")}</div>
        <div class="hero-unit">تومان</div>
      </div>
      <div class="hero-card">
        <div class="hero-label">🍁 دلار کانادا</div>
        <div class="hero-value">{to_persian_digits(f"{cad_toman:,.0f}")}</div>
        <div class="hero-unit">تومان &nbsp; {'▲' if up else '▼'} {to_persian_digits(f"{abs(day_change):.2f}")}٪</div>
      </div>
    </div>
    """


def _currency_section(toman_rates, resampled_currencies):
    rows = ""
    overlays = ""
    names = {"EUR": ("یورو", "🇪🇺"), "GBP": ("پوند انگلیس", "🇬🇧"), "JPY": ("ین ژاپن", "🇯🇵"),
             "CNY": ("یوان چین", "🇨🇳"), "TRY": ("لیر ترکیه", "🇹🇷")}
    for pair_name, resampled in resampled_currencies.items():
        if pair_name == "USD/CAD":
            continue
        code = pair_name.split("/")[0]
        toman_value = toman_rates.get(code)
        daily = resampled.get("daily", [])
        if not toman_value or not daily:
            continue
        slug = _slug(pair_name)
        prev = daily[-2][1] if len(daily) > 1 else daily[-1][1]
        latest = daily[-1][1]
        change_pct = ((latest - prev) / prev * 100) if prev else 0
        title, flag = names.get(code, (code, "💱"))

        rows += _info_row(flag, title, code, f'{to_persian_digits(f"{toman_value:,.0f}")} <span class="row-unit">تومان</span>',
                           change_pct=change_pct, href=f"#chart-{slug}")
        overlays += _chart_overlay(
            slug, f"{title} ({code})",
            "نمودار بر اساس نرخ رسمی CAD رسم شده (تاریخچه تومانی در دسترس نیست)",
            _line_chart(resampled.get("daily", []), f"{pair_name} - Daily"),
            _line_chart(resampled.get("monthly", []), f"{pair_name} - Monthly"),
            _line_chart(resampled.get("yearly", []), f"{pair_name} - Yearly"),
        )
    return rows, overlays


def _gold_coin_section(gold_coin_prices):
    if not gold_coin_prices:
        return ""
    rows = ""
    for title, info in gold_coin_prices.items():
        price_str = to_persian_digits(f"{info['price']:,.0f}")
        chart_url = config.TGJU_CHART_URL_TMPL.format(slug=info.get("slug", ""))
        label = title + (' <span class="row-code">تقریبی</span>' if info.get("approx") else "")
        rows += _info_row("🥇", label, "", f'{price_str} <span class="row-unit">تومان</span>',
                           href=chart_url, external=True)
    return f"""
    <section class="card" style="border-top-color:#c9971f;">
      <h2 style="color:#c9971f;">🥇 طلا و سکه (بازار ایران)</h2>
      {rows}
      <p class="card-note">داده لحظه‌ای از tgju.org. چون این شاخص‌ها تاریخچه رایگان ندارن، با کلیک
      روی هرکدوم به نمودار واقعی خود سایت می‌ری.</p>
    </section>
    """


def _crypto_section(crypto_market, crypto_text):
    if not crypto_market:
        return ""
    rows = ""
    for c in crypto_market:
        chg = c["change_24h_pct"] or 0
        price = c["price_usd"]
        price_str = f"${price:,.4f}" if price < 1 else f"${price:,.2f}"
        rows += _info_row("₿", c["name"], c["symbol"], price_str, change_pct=chg)

    labels = [c["symbol"] for c in crypto_market]
    values = [c["change_24h_pct"] or 0 for c in crypto_market]
    chart_b64 = _bar_chart(labels, values, "24h Change (%)")

    return f"""
    <section class="card" style="border-top-color:#c48a2e;">
      <h2 style="color:#c48a2e;">₿ کریپتوکارنسی</h2>
      <div dir="ltr"><img class="chart-img" src="data:image/png;base64,{chart_b64}" alt="crypto"/></div>
      {rows}
      {f'<p class="card-note">{crypto_text}</p>' if crypto_text else ''}
      <p class="card-note">⚠️ این گزارش صرفا داده و روند بازار است، توصیه مالی/خرید/فروش نیست.</p>
    </section>
    """


def _stocks_section(stock_movers):
    if not stock_movers:
        return ""
    rows = ""
    for s in stock_movers:
        chg_day = s.get("change_day_pct") or 0
        week = s.get("change_week_pct")
        week_str = f' <span class="row-code">هفتگی {week:+.1f}٪</span>' if week is not None else ""
        rows += _info_row("🏢", s["name"] + week_str, s["symbol"].split(".")[0].upper(),
                           f"${s['price']:,.2f}", change_pct=chg_day)
    return f"""
    <section class="card" style="border-top-color:#2874a6;">
      <h2 style="color:#2874a6;">🏢 برترین شرکت‌ها (آمریکا + کانادا)</h2>
      {rows}
      <p class="card-note">مرتب‌شده بر اساس بیشترین رشد روزانه. توصیه سرمایه‌گذاری نیست.</p>
    </section>
    """


def _render_news_item(it, accent_color, item_analysis):
    dual_date = format_dual_date(it.get("published_dt_obj")) if it.get("published_dt_obj") else ""
    new_badge = '<span class="badge-new">جدید</span>' if it.get("is_new") else ""
    analysis_block = ""
    if item_analysis:
        analysis_block = f"""
        <details class="analysis-toggle">
          <summary>🔍 تحلیل خبر</summary>
          <div class="analysis-text">{item_analysis}</div>
        </details>
        """
    return f"""
    <div class="news-item" style="border-right-color:{accent_color};">
      <div class="news-source">{it['source']}{new_badge}</div>
      <div class="news-title">{it['title']}</div>
      <div class="news-meta">{dual_date}</div>
      <div class="news-actions">
        <a class="news-link" href="{it['link']}" target="_blank">مشاهده متن کامل خبر ←</a>
        {analysis_block}
      </div>
    </div>
    """


def _render_category_section(category, analysis):
    style = CATEGORY_STYLE.get(category, {"icon": "📰", "color": "#333"})
    icon, color = style["icon"], style["color"]
    items = analysis.get("items", [])
    item_analyses = analysis.get("item_analyses", [])
    items_html = "".join(
        _render_news_item(it, color, item_analyses[i] if i < len(item_analyses) else "")
        for i, it in enumerate(items)
    )
    return f"""
    <section class="card" style="border-top-color:{color};">
      <h2 style="color:{color};">{icon} {category} <span class="count-badge">{len(items)} خبر</span></h2>
      <p class="summary-box"><strong>جمع‌بندی:</strong> {analysis.get('summary', '')}</p>
      {f'<p class="comparison-box"><strong>مقایسه منابع:</strong> {analysis.get("comparison")}</p>' if analysis.get('comparison') else ''}
      <div class="items-list">
        {items_html if items_html else '<p class="empty">خبر جدیدی یافت نشد.</p>'}
      </div>
    </section>
    """


def build_report(category_analyses: dict, currencies: dict, iran_usd_toman,
                  forecast_text: str, political_text: str,
                  gold_coin_prices=None, crypto_market=None, crypto_text: str = "",
                  stock_movers=None, weather_data=None, rollups: dict = None, output_dir: str = None) -> str:
    output_dir = output_dir or config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    rollups = rollups or {}
    currencies = currencies or {}

    for cat_analysis in category_analyses.values():
        for it in cat_analysis.get("items", []):
            if "published_dt_obj" not in it:
                try:
                    it["published_dt_obj"] = datetime.fromisoformat(it["published"])
                except Exception:
                    it["published_dt_obj"] = None

    import fetch_rates as _fr
    resampled_currencies = {name: _fr.resample_by_period(series) for name, series in currencies.items()}
    toman_rates = _fr.compute_toman_rates(iran_usd_toman, resampled_currencies)

    hero_html = _toman_hero_pair(toman_rates, resampled_currencies)
    currency_rows, currency_overlays = _currency_section(toman_rates, resampled_currencies)
    currency_section_html = f"""
    <section class="card" style="border-top-color:#1f3864;">
      <h2 style="color:#1f3864;">💱 ارزهای دیگر</h2>
      {currency_rows}
    </section>
    """ if currency_rows else ""

    gold_html = _gold_coin_section(gold_coin_prices or {})
    crypto_html = _crypto_section(crypto_market or [], crypto_text)
    stocks_html = _stocks_section(stock_movers or [])

    rollup_html = "".join(
        f'<div class="note-card purple"><strong>📌 مهم‌ترین اخبار {label}:</strong> {text}</div>'
        for label, text in rollups.items() if text
    )

    sections_html = "".join(
        _render_category_section(category, category_analyses.get(category, {"summary": "داده‌ای موجود نیست.", "items": [], "item_analyses": []}))
        for category in config.RSS_SOURCES.keys()
    )

    weather_html = ""
    for w in (weather_data or []):
        temp = w.get("temp")
        temp_str = to_persian_digits(f"{temp:.0f}°") if temp is not None else ""
        weather_html += f'<span class="weather-chip">{w["icon"]} {w["name"]} {temp_str} · {to_persian_digits(w["time"])}</span>'
    user_name = config.USER_NAME
    now_str = format_dual_date(datetime.now()) + " — " + to_persian_digits(datetime.now().strftime("%H:%M"))

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>خلاصه اخبار - {now_str}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #eef1f5;
    --card: #ffffff;
    --navy: #1f3864;
    --navy-dark: #142544;
    --text: #202531;
    --muted: #757c8a;
    --up: #1e8449;
    --down: #c0392b;
    --border: #e3e7ee;
  }}
  * {{ box-sizing: border-box; }}
  html, body, div, span, h1, h2, h3, p, a, label, summary, input {{
    font-family: 'Vazirmatn', Tahoma, Arial, sans-serif !important;
  }}
  body {{
    background: var(--bg); color: var(--text); margin: 0; padding: 0;
    font-size: 15px; line-height: 1.85;
  }}
  header {{
    background: linear-gradient(135deg, var(--navy), var(--navy-dark));
    color: #fff; padding: 22px 18px; border-radius: 0 0 20px 20px;
  }}
  .header-top {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
  .weather-chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .weather-chip {{ background: rgba(255,255,255,.15); border-radius: 20px; padding: 3px 11px; font-size: 11px; white-space: nowrap; }}
  .header-name {{ font-weight: 700; font-size: 13px; }}
  header h1 {{ margin: 0; font-size: 21px; font-weight: 800; }}
  header p {{ margin: 6px 0 0; opacity: .85; font-size: 12.5px; }}

  .container {{ max-width: 760px; margin: 0 auto; padding: 14px; }}

  .hero-pair {{ display: flex; gap: 10px; margin-bottom: 12px; }}
  .hero-card {{
    flex: 1; background: linear-gradient(135deg, var(--navy), var(--navy-dark)); color: #fff;
    border-radius: 16px; padding: 16px; text-align: center;
  }}
  .hero-label {{ font-size: 12.5px; opacity: .85; margin-bottom: 4px; }}
  .hero-value {{ font-size: 24px; font-weight: 800; }}
  .hero-unit {{ font-size: 11.5px; opacity: .85; margin-top: 3px; }}

  .rate-note {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 10px 14px; margin-bottom: 12px; font-size: 13px; font-weight: 600; }}

  .note-card {{ border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; font-size: 13.5px; border-right: 4px solid; }}
  .note-card.amber {{ background: #fdf6e3; border-color: #c48a2e; }}
  .note-card.blue {{ background: #eaf1f8; border-color: var(--navy); }}
  .note-card.purple {{ background: #f1ecf6; border-color: #6c4f8c; }}

  .card {{
    background: var(--card); border-radius: 16px; padding: 16px; margin-bottom: 14px;
    border-top: 4px solid; box-shadow: 0 1px 4px rgba(20,30,50,.06);
  }}
  .card h2 {{ margin: 0 0 10px; font-size: 17px; display: flex; align-items: center; gap: 6px; }}
  .count-badge {{ margin-right: auto; font-size: 10.5px; font-weight: 600; color: var(--muted); background: #f1f3f7; border-radius: 20px; padding: 2px 9px; }}
  .card-note {{ font-size: 11px; color: var(--muted); margin: 8px 0 0; }}

  .summary-box {{ background: #eef4fb; border-radius: 10px; padding: 10px 12px; font-size: 13.5px; margin: 0 0 6px; }}
  .comparison-box {{ background: #fdf3e7; border-radius: 10px; padding: 10px 12px; font-size: 12.5px; margin: 0 0 10px; }}

  /* یک ردیف واحد برای ارز / طلا / کریپتو / شرکت */
  .row {{
    display: flex; align-items: center; gap: 10px; padding: 9px 4px;
    border-bottom: 1px solid var(--border); text-decoration: none; color: inherit;
  }}
  .row:last-of-type {{ border-bottom: none; }}
  .row-icon {{ font-size: 16px; width: 22px; text-align: center; flex-shrink: 0; }}
  .row-main {{ flex: 1; min-width: 0; }}
  .row-title {{ font-weight: 700; font-size: 13.5px; }}
  .row-code {{ font-size: 10.5px; color: var(--muted); font-weight: 500; }}
  .row-value {{ text-align: left; flex-shrink: 0; }}
  .row-price {{ font-weight: 700; font-size: 13.5px; white-space: nowrap; }}
  .row-unit {{ font-size: 10.5px; color: var(--muted); font-weight: 500; }}
  .row-change {{ display: block; font-size: 11px; font-weight: 700; margin-top: 1px; }}
  .row-change.up {{ color: var(--up); }}
  .row-change.down {{ color: var(--down); }}

  .chart-img {{ width: 100%; border-radius: 10px; margin-bottom: 8px; }}

  /* پنجره نمودار - CSS خالص، بدون جاوااسکریپت */
  .overlay {{ display: none; position: fixed; inset: 0; background: rgba(15,20,30,.75); z-index: 50; align-items: center; justify-content: center; padding: 14px; }}
  .overlay:target {{ display: flex; }}
  .overlay-inner {{ background: #fff; border-radius: 16px; padding: 18px; max-width: 560px; width: 100%; max-height: 88vh; overflow-y: auto; position: relative; }}
  .overlay-inner h3 {{ margin: 0 0 4px; color: var(--navy); font-size: 16px; }}
  .overlay-note {{ font-size: 11px; color: var(--muted); margin: 0 0 10px; }}
  .overlay-close {{ position: absolute; top: 12px; left: 12px; background: #f1f3f7; color: var(--text); text-decoration: none; font-size: 11px; padding: 4px 11px; border-radius: 20px; font-weight: 600; }}
  .tab-radio {{ display: none; }}
  .tab-buttons {{ display: flex; gap: 6px; margin: 6px 0 12px; }}
  .tab-buttons label {{ flex: 1; text-align: center; padding: 7px; border-radius: 9px; background: #f1f3f7; font-size: 12.5px; font-weight: 600; cursor: pointer; color: var(--muted); }}
  .panel {{ display: none; }}
  .panel img {{ width: 100%; border-radius: 10px; }}
  input[id$="-d"]:checked ~ .tab-buttons label[for$="-d"],
  input[id$="-m"]:checked ~ .tab-buttons label[for$="-m"],
  input[id$="-y"]:checked ~ .tab-buttons label[for$="-y"] {{ background: var(--navy); color: #fff; }}
  input[id$="-d"]:checked ~ .tab-panels .panel-d,
  input[id$="-m"]:checked ~ .tab-panels .panel-m,
  input[id$="-y"]:checked ~ .tab-panels .panel-y {{ display: block; }}

  /* خبر */
  .news-item {{ padding: 10px 10px 10px 0; border-bottom: 1px solid var(--border); border-right: 3px solid; margin-bottom: 2px; }}
  .news-item:last-child {{ border-bottom: none; }}
  .news-source {{ font-size: 10.5px; font-weight: 700; color: #b91c1c; margin-bottom: 3px; }}
  .badge-new {{ display: inline-block; background: var(--up); color: #fff; font-size: 9.5px; padding: 1px 7px; border-radius: 20px; margin-right: 6px; font-weight: 600; }}
  .news-title {{ font-weight: 700; font-size: 14.5px; line-height: 1.6; }}
  .news-meta {{ font-size: 11px; color: var(--muted); margin-top: 3px; }}
  .news-actions {{ margin-top: 6px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .news-link {{ font-size: 12px; color: var(--navy); text-decoration: none; font-weight: 600; }}
  .analysis-toggle {{ font-size: 12px; }}
  .analysis-toggle summary {{ cursor: pointer; color: #6c4f8c; font-weight: 700; list-style: none; }}
  .analysis-toggle summary::-webkit-details-marker {{ display: none; }}
  .analysis-text {{ margin-top: 5px; background: #f1ecf6; padding: 9px 11px; border-radius: 8px; font-size: 12.5px; line-height: 1.75; }}
  .empty {{ color: var(--muted); font-size: 13px; }}

  footer {{ text-align: center; padding: 22px; font-size: 11px; color: var(--muted); }}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <div class="weather-chips">{weather_html}</div>
    <div class="header-name">👋 {user_name}</div>
  </div>
  <h1>📊 خلاصه اخبار</h1>
  <p>{now_str}</p>
</header>
<div class="container">
  {hero_html}
  {currency_section_html}
  {currency_overlays}
  {rollup_html}
  <div class="note-card amber">📈 <strong>پیش‌بینی اقتصادی:</strong> {forecast_text}</div>
  <div class="note-card blue">🏛️ <strong>تحلیل سیاسی:</strong> {political_text}</div>
  {crypto_html}
  {stocks_html}
  {gold_html}
  {sections_html}
</div>
<footer>این گزارش به‌صورت خودکار توسط اسکریپت شخصی و Gemini API تولید شده و جایگزین منابع خبری رسمی یا مشاوره مالی نیست.</footer>
</body>
</html>"""

    path = os.path.join(output_dir, f"digest_{datetime.now().strftime('%Y%m%d_%H%M')}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    for alias in ("latest.html", "index.html"):
        with open(os.path.join(output_dir, alias), "w", encoding="utf-8") as f:
            f.write(html)
    return path
