# -*- coding: utf-8 -*-
"""
ساخت گزارش HTML - نسخه‌ی پاکسازی‌شده و یکدست.
یک کامپوننت واحد (.row) برای همه‌ی ردیف‌های اطلاعاتی (ارز/طلا/کریپتو/شرکت) استفاده می‌شه
تا ظاهر یکدست بمونه. نمودارها همیشه dir="ltr" دارن تا تو صفحه‌ی راست‌به‌چپ به‌هم نریزن.
"""

import base64
import html as html_lib
import io
import os
import re
from datetime import datetime, timezone

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


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ORDERED_RE = re.compile(r"^(\d+)[.\)]\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[*\-•]\s+(.*)$")
_HR_RE = re.compile(r"^[-_*]{3,}$")


def _md(text: str) -> str:
    """
    تبدیل سبک متن مارک‌داونی که مدل‌های زبانی (Gemini/Claude) تولید می‌کنن -
    شامل **بولد**، لیست شماره‌دار «1. ...» و لیست نقطه‌ای «* ...» - به HTML واقعی.
    بدون این تابع، این نشانه‌ها و شکستن خط‌ها موقع رندر تو مرورگر گم می‌شن و
    کل متن به شکل یه پاراگراف قاطی‌شده دیده می‌شه (باگی که باعث این تابع شد).
    ورودی قبل از هر پردازشی escape می‌شه تا HTML دلخواه از مدل تزریق نشه.
    """
    if not text:
        return ""
    text = html_lib.escape(text.strip())

    def bold(s):
        return _BOLD_RE.sub(r"<strong>\1</strong>", s)

    blocks = []
    list_tag = None
    list_items = []
    para_lines = []

    def flush_para():
        if para_lines:
            blocks.append("<p>" + " ".join(para_lines) + "</p>")
            para_lines.clear()

    def flush_list():
        nonlocal list_tag
        if list_tag:
            items_html = "".join(f"<li>{it}</li>" for it in list_items)
            blocks.append(f'<{list_tag} class="md-list">{items_html}</{list_tag}>')
            list_items.clear()
            list_tag = None

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            flush_para()
            flush_list()
            continue
        if _HR_RE.match(line):
            # خط جداکننده مارک‌داونی («---») - محتوایی نداره، فقط مرز بین بخش‌هاست
            flush_para()
            flush_list()
            blocks.append('<hr class="md-hr">')
            continue
        m_ol = _ORDERED_RE.match(line)
        m_ul = None if m_ol else _BULLET_RE.match(line)
        if m_ol:
            flush_para()
            if list_tag != "ol":
                flush_list()
                list_tag = "ol"
            list_items.append(bold(m_ol.group(2)))
        elif m_ul:
            flush_para()
            if list_tag != "ul":
                flush_list()
                list_tag = "ul"
            list_items.append(bold(m_ul.group(1)))
        else:
            flush_list()
            para_lines.append(bold(line))
    flush_para()
    flush_list()
    return "".join(blocks)


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
    # عرض بیشتر و چرخش برچسب‌ها تا اسم کوین‌ها روی هم نیفتن (باگ قبلی: همه اسم‌ها چسبیده به هم).
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    colors = ["#1e8449" if v >= 0 else "#c0392b" for v in values]
    bars = ax.bar(range(len(labels)), values, color=colors)
    ax.set_title(title, fontsize=12)
    ax.axhline(0, color="#333", linewidth=0.9)
    ax.grid(alpha=0.25, axis="y")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # کمی فضای خالی بالای صفر نگه می‌داریم حتی وقتی همه مقادیر منفی‌ان،
    # وگرنه محور انگار از صفر «قطع» شده و نمودار برعکس به‌نظر می‌رسه.
    vmin, vmax = min(values), max(values)
    span = max(vmax - vmin, 1.0)
    pad = span * 0.22
    ax.set_ylim(min(vmin, 0) - pad, max(vmax, 0) + pad)

    # درصد دقیق روی/زیر هر ستون - قبلا فقط عنوان کلی «24h Change» بود و
    # هیچ عددی روی خود ستون‌ها دیده نمی‌شد.
    label_gap = span * 0.045
    for bar, v in zip(bars, values):
        y = bar.get_height() + (label_gap if v >= 0 else -label_gap)
        va = "bottom" if v >= 0 else "top"
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{v:+.1f}%",
                 ha="center", va=va, fontsize=7.5, fontweight="bold", color="#333")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
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


def _toman_hero_pair(toman_rates, resampled_currencies, usd_change_percent=None):
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

    # درصد تغییر دلار بازار آزاد ایران مستقیماً از tgju.org میاد (چون نرخ CAD/USD رسمی
    # هیچ ربطی به نوسان روزانه‌ی دلار بازار آزاد تهران نداره - این دو عدد کاملاً جدا هستن).
    # اگه این عدد در دسترس نبود (خطای شبکه/تغییر ساختار API)، به‌جای نمایش عدد اشتباه یا صفر،
    # خط درصد تغییر کلاً از کارت دلار آمریکا حذف می‌شه.
    if usd_change_percent is not None:
        usd_up = usd_change_percent >= 0
        usd_unit_line = (
            f'تومان &nbsp; {"▲" if usd_up else "▼"} '
            f'{to_persian_digits(f"{abs(usd_change_percent):.2f}")}٪'
        )
    else:
        usd_unit_line = "تومان"

    # نکته مهم (اصلاح باگ): قبلا هر دو کارت دلار آمریکا و دلار کانادا به یک اورلی
    # مشترک (#chart-usdcad) لینک می‌شدن که تیترش «دلار آمریکا به دلار کانادا» بود -
    # این تیتر برای خود کارت دلار آمریکا (که موضوعش نرخ تومانیه، نه نرخ برابری با
    # کانادا) و برای کارت دلار کانادا هم گمراه‌کننده بود. کاربر می‌خواد این نمودار
    # همینجا تو خود صفحه (نه لینک به سایت دیگه) با تب‌های روزانه/ماهانه/سالانه باز
    # بشه - درست مثل بقیه ارزها - فقط با تیتر درست و مخصوص خودش. برای همین اینجا به
    # دو اورلی داخلی جداگانه (#chart-usd و #chart-cad) لینک می‌شن که در _usd_cad_rate_note
    # ساخته می‌شن؛ هر سه اورلی (usd/cad/usdcad) از روی همون داده‌ی رسمی USD/CAD
    # (تنها سری تاریخی واقعی که این پروژه براش داره) رسم می‌شن، چون تاریخچه‌ی روزانه‌ی
    # جداگانه‌ای برای نرخ تومانی دلار/کانادا وجود نداره - ولی هرکدوم تیتر و توضیح
    # مخصوص به خودشونو دارن تا گمراه‌کننده نباشه.
    return f"""
    <div class="hero-pair">
      <a class="hero-card" href="#chart-usd">
        <div class="hero-label">💵 دلار آمریکا</div>
        <div class="hero-value">{to_persian_digits(f"{usd_toman:,.0f}")}</div>
        <div class="hero-unit">{usd_unit_line}</div>
      </a>
      <a class="hero-card" href="#chart-cad">
        <div class="hero-label">🍁 دلار کانادا</div>
        <div class="hero-value">{to_persian_digits(f"{cad_toman:,.0f}")}</div>
        <div class="hero-unit">تومان &nbsp; {'▲' if up else '▼'} {to_persian_digits(f"{abs(day_change):.2f}")}٪</div>
      </a>
    </div>
    """


def _usd_cad_rate_note(resampled_currencies, usd_toman_resampled=None, cad_toman_resampled=None):
    """
    کاربر متوجه شده بود که کارت‌های بزرگ دلار آمریکا/کانادا بالای صفحه - برخلاف
    ردیف‌های ارزهای دیگه پایین‌تر - قابل کلیک نیستن و هیچ آمار/نموداری نشون نمی‌دن،
    و درخواست کرد که میزان نرخ برابری دلار آمریکا به کانادا (۱ دلار آمریکا چند دلار
    کاناداست) و درصد تغییرش رو ببینه. این تابع یک ردیف کلیک‌شدنی می‌سازه که مستقیم
    نرخ رسمی USD/CAD (بانک مرکزی کانادا) رو نشون می‌ده و به یک اورلی نموداری
    (روزانه/ماهانه/سالانه) لینک می‌شه - دقیقا همون تجربه‌ای که ارزهای دیگه دارن.
    نکته: این درصدِ تغییرِ خودِ نرخ USD/CAD هست (مثبت = دلار آمریکا در برابر کانادا
    قوی‌تر شده)، نه درصد تغییر ارزش تومانی که تو کارت‌های بالا نمایش داده می‌شه -
    این دو مفهوم متفاوتن و عمدا اینجا علامتش برعکس نمی‌شه.

    اصلاح باگ مهم: قبلا کارت‌های «دلار آمریکا» و «دلار کانادا» (که هردو موضوعشون نرخ
    تومانیه) هر دو مستقیم از روی همین یک سری نرخ رسمی USD/CAD رسم می‌شدن - یعنی کاربر
    وقتی رو هرکدوم کلیک می‌کرد، دقیقا همون یک نمودار رو با عنوان‌های مختلف می‌دید (کاربر:
    «انگار نمودار کپی شده از نرخ دلار آمریکا به کانادا است»). الان اگه تاریخچه‌ی واقعی
    دلار/تومان در دسترس باشه (fetch_rates.get_iran_usd_toman_series)، نمودار «دلار
    آمریکا» از روی همون تاریخچه‌ی واقعی رسم می‌شه، و نمودار «دلار کانادا» از روی تاریخچه‌ی
    محاسبه‌شده‌ی dollar/تومان تقسیم بر نرخ رسمی USD/CAD (fetch_rates.compute_cad_toman_series)
    - این دو دیگه یکی نیستن. نمودار #chart-usdcad (نرخ برابری دو دلار) جدا و بدون تغییر
    می‌مونه چون موضوعش اصلا فرق داره (برابری دو ارز، نه قیمت تومانی).
    """
    usd_cad = resampled_currencies.get("USD/CAD", {})
    daily = usd_cad.get("daily", [])
    if len(daily) < 1:
        return "", ""
    latest = daily[-1][1]
    prev = daily[-2][1] if len(daily) > 1 else latest
    change_pct = ((latest - prev) / prev * 100) if prev else 0
    up = change_pct >= 0
    cls = "up" if up else "down"
    arrow = "▲" if up else "▼"

    note_html = f"""
    <a class="rate-note" href="#chart-usdcad">
      <span>💱 نرخ دلار آمریکا به کانادا: <bdi dir="ltr">۱ USD = {to_persian_digits(f"{latest:.3f}")} CAD</bdi></span>
      <span class="row-change {cls}" style="margin-top:0;">{arrow} {to_persian_digits(f"{abs(change_pct):.2f}")}٪</span>
    </a>
    """

    usd_cad_daily_b64 = _line_chart(daily, "USD/CAD - Daily")
    usd_cad_monthly_b64 = _line_chart(usd_cad.get("monthly", []), "USD/CAD - Monthly")
    usd_cad_yearly_b64 = _line_chart(usd_cad.get("yearly", []), "USD/CAD - Yearly")

    usd_toman_resampled = usd_toman_resampled or {}
    cad_toman_resampled = cad_toman_resampled or {}
    usd_toman_daily = usd_toman_resampled.get("daily", [])
    cad_toman_daily = cad_toman_resampled.get("daily", [])

    if usd_toman_daily:
        usd_note = (
            "بر اساس تاریخچه‌ی واقعی نرخ دلار بازار آزاد تهران (تومان) - نه نرخ برابری با کانادا."
        )
        usd_overlay = _chart_overlay(
            "usd", "دلار آمریکا (تومان)", usd_note,
            _line_chart(usd_toman_daily, "USD/Toman - Daily"),
            _line_chart(usd_toman_resampled.get("monthly", []), "USD/Toman - Monthly"),
            _line_chart(usd_toman_resampled.get("yearly", []), "USD/Toman - Yearly"),
        )
    else:
        # اگه واکشی تاریخچه‌ی واقعی (شبکه/API غیررسمی tgju) این‌بار شکست خورد، به‌جای
        # نمایش نمودار خالی، همون نمودار قبلی (نرخ رسمی USD/CAD) به‌عنوان جایگزین امن
        # نشون داده می‌شه - افت درجه‌ی کیفیت، نه یک صفحه‌ی خراب.
        usd_note = (
            "تاریخچه‌ی واقعی نرخ تومانی این‌بار در دسترس نبود؛ این نمودار موقتا بر اساس "
            "نرخ رسمی برابری دلار آمریکا/کانادا رسم شده."
        )
        usd_overlay = _chart_overlay(
            "usd", "دلار آمریکا (USD)", usd_note,
            usd_cad_daily_b64, usd_cad_monthly_b64, usd_cad_yearly_b64,
        )

    if cad_toman_daily:
        cad_note = (
            "چون بازار آزاد ایران نرخ مستقیم دلار کانادا منتشر نمی‌کنه، این تاریخچه از تقسیم "
            "نرخ واقعی دلار آمریکا/تومان بر نرخ رسمی USD/CAD (بانک مرکزی کانادا) محاسبه شده."
        )
        cad_overlay = _chart_overlay(
            "cad", "دلار کانادا (تومان)", cad_note,
            _line_chart(cad_toman_daily, "CAD/Toman - Daily"),
            _line_chart(cad_toman_resampled.get("monthly", []), "CAD/Toman - Monthly"),
            _line_chart(cad_toman_resampled.get("yearly", []), "CAD/Toman - Yearly"),
        )
    else:
        cad_note = (
            "تاریخچه‌ی واقعی نرخ تومانی این‌بار در دسترس نبود؛ این نمودار موقتا بر اساس "
            "نرخ رسمی برابری دلار آمریکا/کانادا رسم شده."
        )
        cad_overlay = _chart_overlay(
            "cad", "دلار کانادا (CAD)", cad_note,
            usd_cad_daily_b64, usd_cad_monthly_b64, usd_cad_yearly_b64,
        )

    usdcad_overlay = _chart_overlay(
        "usdcad", "دلار آمریکا به دلار کانادا (USD/CAD)",
        "نرخ رسمی بانک مرکزی کانادا - نشون می‌ده هر ۱ دلار آمریکا معادل چند دلار کاناداست",
        usd_cad_daily_b64, usd_cad_monthly_b64, usd_cad_yearly_b64,
    )

    return note_html, (usd_overlay + cad_overlay + usdcad_overlay)


def _currency_section(toman_rates, resampled_currencies, currency_toman_resampled=None):
    """
    اصلاح باگ مهم (درخواست کاربر): قبلا نمودار هر ارز (یورو، پوند، ین، ...) بر اساس نرخ خام
    برابری با دلار کانادا (X/CAD رسمی بانک مرکزی) رسم می‌شد، نه بر اساس قیمت تومانی که خود
    ردیف نشون می‌ده - یعنی عدد ردیف تومان بود ولی نمودارش چیز دیگه‌ای (نه‌تومان) نشون می‌داد.
    الان (وقتی fetch_rates.compute_x_toman_series موفق بشه) هم نمودار و هم درصد تغییرِ کنار
    هر ردیف، هر دو از روی همون تاریخچه‌ی واقعی تومانی محاسبه می‌شن - سازگار با عددی که ردیف
    نشون می‌ده. اگه محاسبه‌ش (به‌خاطر نبود تاریخچه‌ی دلار/تومان در این اجرا) ممکن نبود، مثل
    قبل به نمودار خام نرخ CAD برمی‌گرده تا صفحه خراب/خالی نشه.
    """
    currency_toman_resampled = currency_toman_resampled or {}
    rows = ""
    overlays = ""
    names = {"EUR": ("یورو", "🇪🇺"), "GBP": ("پوند انگلیس", "🇬🇧"), "JPY": ("ین ژاپن", "🇯🇵"),
             "CNY": ("یوان چین", "🇨🇳"), "TRY": ("لیر ترکیه", "🇹🇷"), "AUD": ("دلار استرالیا", "🇦🇺"),
             "CHF": ("فرانک سوئیس", "🇨🇭"), "INR": ("روپیه هند", "🇮🇳"), "AED": ("درهم امارات", "🇦🇪")}
    for pair_name, resampled in resampled_currencies.items():
        if pair_name == "USD/CAD":
            continue
        code = pair_name.split("/")[0]
        toman_value = toman_rates.get(code)
        daily = resampled.get("daily", [])
        if not toman_value or not daily:
            continue
        slug = _slug(pair_name)
        title, flag = names.get(code, (code, "💱"))

        toman_resampled = currency_toman_resampled.get(pair_name, {})
        toman_daily = toman_resampled.get("daily", [])

        if toman_daily:
            prev = toman_daily[-2][1] if len(toman_daily) > 1 else toman_daily[-1][1]
            latest = toman_daily[-1][1]
            change_pct = ((latest - prev) / prev * 100) if prev else 0
            note = (
                f"تاریخچه‌ی واقعی {title}/تومان - از تقسیم نرخ رسمی {code}/CAD بر USD/CAD "
                "(هر دو بانک مرکزی کانادا) و ضرب در نرخ واقعی دلار/تومان بازار آزاد ایران محاسبه شده."
            )
            daily_chart = _line_chart(toman_daily, f"{code}/Toman - Daily")
            monthly_chart = _line_chart(toman_resampled.get("monthly", []), f"{code}/Toman - Monthly")
            yearly_chart = _line_chart(toman_resampled.get("yearly", []), f"{code}/Toman - Yearly")
        else:
            prev = daily[-2][1] if len(daily) > 1 else daily[-1][1]
            latest = daily[-1][1]
            change_pct = ((latest - prev) / prev * 100) if prev else 0
            note = (
                "تاریخچه‌ی واقعی تومانی این‌بار در دسترس نبود؛ این نمودار موقتا بر اساس نرخ "
                f"رسمی {code}/CAD (بانک مرکزی کانادا) رسم شده."
            )
            daily_chart = _line_chart(daily, f"{pair_name} - Daily")
            monthly_chart = _line_chart(resampled.get("monthly", []), f"{pair_name} - Monthly")
            yearly_chart = _line_chart(resampled.get("yearly", []), f"{pair_name} - Yearly")

        rows += _info_row(flag, title, code, f'{to_persian_digits(f"{toman_value:,.0f}")} <span class="row-unit">تومان</span>',
                           change_pct=change_pct, href=f"#chart-{slug}")
        overlays += _chart_overlay(
            slug, f"{title} ({code})", note, daily_chart, monthly_chart, yearly_chart,
        )
    return rows, overlays


def _gold_coin_section(gold_coin_prices, gold_coin_resampled=None):
    """
    اصلاح باگ مهم (درخواست کاربر): قبلا کلیک روی هر ردیف طلا/سکه کاربر رو به نمودار سایت
    خارجی tgju.org می‌فرستاد، با این توضیح که «این شاخص‌ها تاریخچه‌ی رایگان ندارن». این فرض
    غلط بود - دقیقا همون endpointـی که قیمت لحظه‌ای رو می‌ده (fetch_rates.get_gold_coin_prices)
    یک جدول تاریخچه‌ی کامل هم برمی‌گردونه (رجوع کن به fetch_rates.get_gold_coin_series و
    توضیح این باگ در fetch_rates._get_tgju_history_series). الان اگه این تاریخچه در دسترس
    باشه، مثل ارزها یک اورلی نموداری (روزانه/ماهانه/سالانه) داخل خودِ صفحه باز می‌شه؛ اگه
    این‌بار در دسترس نبود (خطای شبکه/API غیررسمی)، مثل قبل به لینک خارجی برمی‌گرده.
    """
    if not gold_coin_prices:
        return "", ""
    gold_coin_resampled = gold_coin_resampled or {}
    # قیمت طلای ۱۸ و ۲۴ عیار (و طلای دست‌دوم که از رویش تخمین زده می‌شه) تو tgju.org
    # همیشه قیمت «هر یک گرم» طلاست، نه یک واحد دیگه مثل مثقال - ولی قبلا این واحد رو
    # کنار عددش ننوشته بودیم و کاربر دقیقا همینو گفت: عدد هست ولی معلوم نیست مال چه
    # مقداری از طلاست. برای سکه‌ها (که فی‌نفسه یک قطعه‌ان، نه وزن خام طلا) این برچسب
    # معنی نداره، برای همین فقط رو اسلاگ‌های «geram*» اضافه می‌شه.
    GRAM_SLUGS = ("geram18", "geram24")
    # نکته مهم (اصلاح باگ): matplotlib بدون یک کتابخونه‌ی شکل‌دهی حروف عربی/فارسی
    # (arabic-reshaper/python-bidi که این پروژه نصب نداره) متن فارسی رو تو تیتر نمودار
    # به‌هم‌ریخته و نامفهوم نشون می‌ده (حروف جدا و برعکس). برای همین - دقیقا مثل ارزها که
    # همیشه از کد لاتین (USD/CAD, EUR/Toman) به‌جای اسم فارسی استفاده می‌کنن - این‌جا هم
    # برای تیتر خودِ *نمودار* (نه ردیف/عنوان اورلی که همون‌جا با فونت درست صفحه نمایش داده
    # می‌شه) یک برچسب لاتین جایگزین می‌شه.
    GOLD_CHART_LABELS = {
        "geram18": "Gold 18k (per gram)",
        "geram24": "Gold 24k (per gram)",
        "sekee": "Emami Coin",
        "sekeb": "Bahar Azadi Coin",
        "nim": "Half Coin",
        "rob": "Quarter Coin",
        "gerami": "Gerami Coin",
    }
    rows = ""
    overlays = ""
    for i, (title, info) in enumerate(gold_coin_prices.items()):
        price_str = to_persian_digits(f"{info['price']:,.0f}")
        label = title + (' <span class="row-code">تقریبی</span>' if info.get("approx") else "")
        if info.get("slug") in GRAM_SLUGS:
            label += ' <span class="row-code">هر گرم</span>'

        resampled = gold_coin_resampled.get(title, {})
        daily = resampled.get("daily", [])
        if daily:
            # نکته مهم (اصلاح باگ): _slug() فقط حروف/رقم انگلیسی نگه می‌داره، پس رو یک
            # عنوان کاملا فارسی مثل «طلای ۱۸ عیار» رشته‌ی خالی برمی‌گردوند - یعنی همه‌ی
            # ردیف‌های طلا/سکه به یک id="chart-" یکسان (خالی) لینک می‌شدن. به‌جاش از
            # info["slug"] (اسلاگ لاتین خود tgju، مثل geram18/sekee) استفاده می‌شه که
            # یکتاست؛ فقط «طلای دست دوم» چون از رو همون اسلاگ geram18 تخمین زده می‌شه
            # باید با پسوند -approx از خود geram18 متمایز بشه تا id تکراری نشه.
            base_slug = info.get("slug") or f"gold{i}"
            slug = base_slug + ("-approx" if info.get("approx") else "")
            rows += _info_row("🥇", label, "", f'{price_str} <span class="row-unit">تومان</span>',
                               href=f"#chart-{slug}")
            chart_label = GOLD_CHART_LABELS.get(base_slug, base_slug)
            overlays += _chart_overlay(
                slug, title, "تاریخچه‌ی واقعی قیمت (تومان) از جدول تاریخچه‌ی خود tgju.org.",
                _line_chart(daily, f"{chart_label} - Daily"),
                _line_chart(resampled.get("monthly", []), f"{chart_label} - Monthly"),
                _line_chart(resampled.get("yearly", []), f"{chart_label} - Yearly"),
            )
        else:
            # جایگزین امن وقتی این‌بار تاریخچه در دسترس نبود - رفتار قبلی (لینک خارجی)
            chart_url = config.TGJU_CHART_URL_TMPL.format(slug=info.get("slug", ""))
            rows += _info_row("🥇", label, "", f'{price_str} <span class="row-unit">تومان</span>',
                               href=chart_url, external=True)

    section_html = f"""
    <section class="card" style="border-top-color:#c9971f;">
      <h2 style="color:#c9971f;">🥇 طلا و سکه (بازار ایران)</h2>
      {rows}
      <p class="card-note">داده لحظه‌ای و تاریخچه از tgju.org.</p>
    </section>
    """
    return section_html, overlays


def _crypto_cell(c):
    """یک خونه‌ی فشرده برای گرید ۲ستونه کریپتو - چون ردیف تمام‌عرض معمولی (_info_row)
    باعث می‌شد این بخش خیلی طولانی بشه و اسکرول زیادی لازم داشته باشه."""
    chg = c["change_24h_pct"] or 0
    price = c["price_usd"]
    price_str = f"${price:,.4f}" if price < 1 else f"${price:,.2f}"
    up = chg >= 0
    cls = "up" if up else "down"
    arrow = "▲" if up else "▼"
    return f"""
    <div class="crypto-cell">
      <div class="crypto-cell-name"><span class="crypto-cell-icon">₿</span>{c['name']} <span class="row-code">{c['symbol']}</span></div>
      <div class="crypto-cell-bottom">
        <span class="crypto-cell-price">{price_str}</span>
        <span class="crypto-chg {cls}">{arrow} {to_persian_digits(f"{abs(chg):.2f}")}٪</span>
      </div>
    </div>
    """


def _crypto_section(crypto_market, crypto_text):
    if not crypto_market:
        return ""
    cells = "".join(_crypto_cell(c) for c in crypto_market)

    labels = [c["symbol"] for c in crypto_market]
    values = [c["change_24h_pct"] or 0 for c in crypto_market]
    chart_b64 = _bar_chart(labels, values, "24h Change (%)")

    return f"""
    <section class="card" style="border-top-color:#c48a2e;">
      <h2 style="color:#c48a2e;">₿ کریپتوکارنسی</h2>
      <div dir="ltr"><img class="chart-img" src="data:image/png;base64,{chart_b64}" alt="crypto"/></div>
      <div class="crypto-grid">{cells}</div>
      {f'<div class="card-note">{_md(crypto_text)}</div>' if crypto_text else ''}
      <p class="card-note">⚠️ این گزارش صرفا داده و روند بازار است، توصیه مالی/خرید/فروش نیست.</p>
    </section>
    """


def _stocks_section(stock_movers, stocks_text: str = ""):
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
      {f'<div class="card-note">{_md(stocks_text)}</div>' if stocks_text else ''}
      <p class="card-note">مرتب‌شده بر اساس بیشترین رشد روزانه. هدف این بخش آشنایی با بازار سهامه، توصیه سرمایه‌گذاری نیست.</p>
    </section>
    """


def _market_education_tip():
    """
    یک نکته‌ی آموزشی چرخشی درباره‌ی مفاهیم پایه‌ی بازار فارکس/سهام از config.MARKET_EDUCATION_TIPS.
    بر اساس «روز سال» (نه ساعت اجرا) انتخاب می‌شه تا اگه گزارش چندبار در یک روز ساخته بشه،
    نکته‌ی نمایش‌داده‌شده عوض نشه - هدف اینه که در طول چند هفته، خواننده به‌ترتیب و بدون
    تکرار زیاد، مفاهیم مختلف بازار رو یاد بگیره.
    """
    tips = getattr(config, "MARKET_EDUCATION_TIPS", [])
    if not tips:
        return ""
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    tip = tips[day_of_year % len(tips)]
    return f"""
    <div class="note-card teal">
      <div class="note-label">🎓 <strong>نکته آموزشی امروز: {tip['title']}</strong></div>
      <p style="margin:6px 0 0;">{tip['text']}</p>
    </div>
    """


def _render_news_item(it, accent_color, item_analysis, number):
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
    # نکته مهم (رفع درخواست کاربر): وقتی ترجمه‌ی فارسیِ تیتر توسط analyze.py انجام نشه
    # (مثلا به‌خاطر خطای موقت API)، تیتر انگلیسی خام نمایش داده می‌شد بدون هیچ راهی برای
    # کاربر که بفهمه چرا. الان همیشه هم نسخه‌ی فارسی و هم نسخه‌ی اصلی (زبان مبدا) هر خبر تو
    # HTML موجوده؛ دکمه‌ی سراسری بالای صفحه (toggleOriginalLang در JS) بین‌شون سوییچ می‌کنه -
    # پیش‌فرض همیشه فارسیه. اگه ترجمه‌ای اتفاق نیفتاده باشه (تیتر از قبل فارسی بوده، یا
    # تحلیل این خبر اصلا انجام نشده)، دو نسخه یکی‌ان و دکمه چیز اضافه‌ای نشون نمی‌ده.
    title_fa = it["title"]
    title_orig = it.get("title_original") or title_fa
    if title_orig != title_fa:
        title_html = (
            f'<span class="title-fa">{title_fa}</span>'
            f'<span class="title-orig" dir="auto">{title_orig}</span>'
        )
    else:
        title_html = f'<span class="title-fa">{title_fa}</span>'
    return f"""
    <div class="news-item" style="border-right-color:{accent_color};">
      <div class="news-num" style="background:{accent_color};">{to_persian_digits(str(number))}</div>
      <div class="news-body">
        <div class="news-source">{it['source']}{new_badge}</div>
        <div class="news-title">{title_html}</div>
        <div class="news-meta">{dual_date}</div>
        <div class="news-actions">
          <a class="news-link" href="{it['link']}" target="_blank">مشاهده متن کامل خبر ←</a>
          {analysis_block}
        </div>
      </div>
    </div>
    """


def _render_category_section(category, analysis):
    style = CATEGORY_STYLE.get(category, {"icon": "📰", "color": "#333"})
    icon, color = style["icon"], style["color"]
    items = analysis.get("items", [])
    item_analyses = analysis.get("item_analyses", [])
    items_html = "".join(
        _render_news_item(it, color, item_analyses[i] if i < len(item_analyses) else "", i + 1)
        for i, it in enumerate(items)
    )
    return f"""
    <section class="card" style="border-top-color:{color};">
      <h2 style="color:{color};">{icon} {category} <span class="count-badge">{len(items)} خبر</span></h2>
      <div class="summary-box"><div class="note-label"><strong>جمع‌بندی</strong></div>{_md(analysis.get('summary', ''))}</div>
      {f'<div class="comparison-box"><div class="note-label"><strong>مقایسه منابع</strong></div>{_md(analysis.get("comparison"))}</div>' if analysis.get('comparison') else ''}
      <div class="items-list">
        {items_html if items_html else '<p class="empty">خبر جدیدی یافت نشد.</p>'}
      </div>
    </section>
    """


def build_report(category_analyses: dict, currencies: dict, iran_usd_toman,
                  forecast_text: str, political_text: str,
                  gold_coin_prices=None, crypto_market=None, crypto_text: str = "",
                  stock_movers=None, weather_data=None, rollups: dict = None, output_dir: str = None,
                  usd_change_percent=None, stocks_text: str = "",
                  iran_usd_toman_series=None, gold_coin_series=None) -> str:
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

    # تاریخچه‌ی واقعی دلار/تومان (برای نمودار «دلار آمریکا») + محاسبه‌ی تاریخچه‌ی دلار
    # کانادا/تومان از روی همون + نرخ رسمی USD/CAD (برای نمودار «دلار کانادا») - رجوع کن
    # به توضیح باگ داخل _usd_cad_rate_note برای این‌که چرا این دو قبلا یک نمودار تکراری بودن.
    iran_usd_toman_series = iran_usd_toman_series or []
    cad_toman_series = _fr.compute_cad_toman_series(iran_usd_toman_series, currencies.get("USD/CAD", []))
    usd_toman_resampled = _fr.resample_by_period(iran_usd_toman_series)
    cad_toman_resampled = _fr.resample_by_period(cad_toman_series)

    # همون تاریخچه‌ی واقعی تومانی، حالا برای بقیه‌ی ارزها (یورو، پوند، ین، ...) هم تکرار
    # می‌شه - رجوع کن به توضیح باگ در fetch_rates.compute_x_toman_series: قبلا نمودار هر
    # ارز از روی نرخ خام X/CAD رسم می‌شد (نه تومان)، در حالی که خود ردیف عدد تومانی نشون می‌داد.
    currency_toman_resampled = {}
    usd_cad_raw = currencies.get("USD/CAD", [])
    for pair_name, raw_series in currencies.items():
        if pair_name == "USD/CAD":
            continue
        toman_series = _fr.compute_x_toman_series(raw_series, usd_cad_raw, iran_usd_toman_series)
        if toman_series:
            currency_toman_resampled[pair_name] = _fr.resample_by_period(toman_series)

    hero_html = _toman_hero_pair(toman_rates, resampled_currencies, usd_change_percent=usd_change_percent)
    usd_cad_note_html, usd_cad_overlay_html = _usd_cad_rate_note(
        resampled_currencies, usd_toman_resampled, cad_toman_resampled
    )
    currency_rows, currency_overlays = _currency_section(toman_rates, resampled_currencies, currency_toman_resampled)
    currency_overlays = usd_cad_overlay_html + currency_overlays
    currency_section_html = f"""
    <section class="card" style="border-top-color:#1f3864;">
      <h2 style="color:#1f3864;">💱 ارزهای دیگر</h2>
      {currency_rows}
    </section>
    """ if currency_rows else ""

    gold_coin_resampled = {
        title: _fr.resample_by_period(series) for title, series in (gold_coin_series or {}).items()
    }
    gold_html, gold_overlays_html = _gold_coin_section(gold_coin_prices or {}, gold_coin_resampled)
    crypto_html = _crypto_section(crypto_market or [], crypto_text)
    stocks_html = _stocks_section(stock_movers or [], stocks_text=stocks_text)
    market_tip_html = _market_education_tip()

    rollup_html = "".join(
        f'<div class="note-card purple"><div class="note-label">📌 <strong>مهم‌ترین اخبار {label}</strong></div>{_md(text)}</div>'
        for label, text in rollups.items() if text
    )

    # توزیع دستی کارت‌های بزرگ (کریپتو/شرکت‌ها/طلا/هر دسته خبری) بین چند ستون به روش
    # حریصانه (greedy): چون این کارت‌ها با break-inside:avoid تقسیم‌ناپذیرن و ارتفاع‌شون
    # خیلی متفاوته (طلا ~۵۰۰px در برابر یک کارت خبری ۱۰تایی ~۱۸۰۰px)، اعتماد به
    # column-fill نیتیو مرورگر (چه balance چه auto) نتیجه‌ی قابل‌اعتمادی نمی‌ده.
    # نکته مهم: طول رشته‌ی HTML رندرشده معیار قابل‌اعتمادی برای تخمین ارتفاع نیست، چون
    # تحلیل هر خبر (item_analysis) داخل یک <details> جمع‌شده (مخفی) قرار می‌گیره و طولش
    # می‌تونه از ۵۰ تا ۲۰۰۰+ کاراکتر فرق کنه بدون اینکه کوچیک‌ترین تاثیری روی ارتفاع
    # واقعی صفحه (وقتی بسته‌ست) داشته باشه - همین باعث می‌شد قبلا یه دسته با تحلیل‌های
    # طولانی کل یه ستون رو به‌تنهایی اشغال کنه و بقیه‌ی ۹ بلاک تو ۲ ستون دیگه جمع بشن.
    # به‌جاش از تعداد آیتم‌های واقعی (خبر/ارز/سکه/کریپتو) که مستقیم رو ارتفاع دیده‌شده
    # تاثیر می‌ذاره برای تخمین استفاده می‌کنیم.
    HEADER_OVERHEAD = 90
    PER_NEWS_ITEM = 175
    PER_ROW_ITEM = 46
    CHART_OVERHEAD = 210

    big_blocks = []  # لیست از (تخمین_ارتفاع, html)
    for category in config.RSS_SOURCES.keys():
        analysis = category_analyses.get(category, {"summary": "داده‌ای موجود نیست.", "items": [], "item_analyses": []})
        html_piece = _render_category_section(category, analysis)
        if html_piece and html_piece.strip():
            est_height = HEADER_OVERHEAD + 130 + len(analysis.get("items", [])) * PER_NEWS_ITEM
            big_blocks.append((est_height, html_piece))

    if crypto_html and crypto_html.strip():
        n_coins = len(crypto_market or [])
        est_height = HEADER_OVERHEAD + CHART_OVERHEAD + -(-n_coins // 2) * 62  # گرید دوستونه
        big_blocks.append((est_height, crypto_html))
    if stocks_html and stocks_html.strip():
        est_height = HEADER_OVERHEAD + len(stock_movers or []) * PER_ROW_ITEM
        big_blocks.append((est_height, stocks_html))
    # نکته: gold_html عمداً اینجا به big_blocks اضافه نمی‌شه و در توزیع حریصانه‌ی ستون‌ها
    # شرکت نمی‌کنه - طبق درخواست کاربر باید همیشه بلافاصله بعد از بخش ارزها/دلار بیاد،
    # نه هرجایی که الگوریتم چیدمان براش جا پیدا کنه (پایین‌تر، در قالب نهایی درج می‌شه).

    num_cols = 3
    col_heights = [0] * num_cols
    col_parts = [[] for _ in range(num_cols)]
    for est_height, block in sorted(big_blocks, key=lambda x: x[0], reverse=True):
        idx = col_heights.index(min(col_heights))
        col_parts[idx].append(block)
        col_heights[idx] += est_height
    columns_html = '<div class="columns-row">' + "".join(
        f'<div class="col">{"".join(parts)}</div>' for parts in col_parts if parts
    ) + "</div>"

    weather_html = ""
    for w in (weather_data or []):
        temp = w.get("temp")
        temp_str = to_persian_digits(f"{temp:.0f}°") if temp is not None else ""
        weather_html += f'<span class="weather-chip">{w["icon"]} {w["name"]} {temp_str} · {to_persian_digits(w["time"])}</span>'
    user_name = config.USER_NAME
    # قبلا از datetime.now() بدون timezone استفاده می‌شد (روی رانر گیت‌هاب یعنی UTC خام)
    # و فقط یه ساعت خام نشون می‌داد که نه ساعت ایران بود نه کانادا. الان format_dual_date
    # خودش هر دو ساعت تهران و تورنتو رو از روی UTC واقعی حساب و نشون می‌ده.
    now_str = format_dual_date(datetime.now(timezone.utc))

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>خلاصه اخبار - {now_str}</title>
<style>
  /* فونت Estedad سلف‌هاست‌شده - قبلا Vazirmatn بود (کاربر رو آیفون قبول نداشت)، بعد Sahel
     (کاربر گفت زیبا نیست). درخواست بعدی «مثل tgju.org» (IRANSans/Iranyekan) بود که
     تجاری/خصوصی‌ان و مجوز توزیع رایگان ندارن. Peyda هم امتحان شد ولی معلوم شد محصول فروشی
     فونت‌ایرانه (ریسک حقوقی برای قراردادن رایگان تو یک ریپو/سایت عمومی). Estedad یک فونت
     فارسی/عربی کاملا رایگان و متن‌باز (SIL OFL 1.1، github.com/aminabedi68/Estedad - متن
     کامل مجوز کنار خود فایل‌ها در assets/fonts/ESTEDAD-OFL-LICENSE.txt) با ظاهر هندسی و
     مدرن‌تر از Sahel/Vazirmatn. مثل قبل، خودِ فایل‌های فونت (woff2) داخل مخزن (assets/fonts)
     قرار گرفته و مستقیم از همون GitHub Pages سرو می‌شه - هیچ وابستگی به دامنه‌ی خارجی
     نیست، پس رو هر دستگاه/شبکه‌ای دقیقا همون فونتیه که رو کامپیوتر دیده می‌شه. */
  @font-face {{
    font-family: 'Estedad';
    font-style: normal;
    font-weight: 300;
    font-display: swap;
    src: url('assets/fonts/estedad-light.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Estedad';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('assets/fonts/estedad-regular.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Estedad';
    font-style: normal;
    font-weight: 500 600;
    font-display: swap;
    src: url('assets/fonts/estedad-semibold.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Estedad';
    font-style: normal;
    font-weight: 700;
    font-display: swap;
    src: url('assets/fonts/estedad-bold.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Estedad';
    font-style: normal;
    font-weight: 800 900;
    font-display: swap;
    src: url('assets/fonts/estedad-black.woff2') format('woff2');
  }}
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
  html {{
    /* بدون این، سافاری آیفون گاهی خودش سایز فونت رو موقع چرخش صفحه تغییر می‌ده که
       باعث می‌شه فونت ناخواسته تار/بی‌کیفیت به نظر برسه. */
    -webkit-text-size-adjust: 100%;
    text-size-adjust: 100%;
  }}
  html, body, div, span, h1, h2, h3, p, a, label, summary, input {{
    font-family: 'Estedad', Tahoma, Arial, sans-serif !important;
    /* رندر فونت روی وب‌کیت/سافاری (به‌خصوص آیفون) بدون این پرچم‌ها ضخیم‌تر و
       کم‌کیفیت‌تر از نسخه‌ی دسکتاپ دیده می‌شه. */
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
    -webkit-text-stroke: 0;
  }}
  body {{
    background: var(--bg); color: var(--text); margin: 0; padding: 0;
    font-size: 15px; line-height: 1.65;
  }}
  header {{
    background: linear-gradient(135deg, var(--navy), var(--navy-dark));
    color: #fff; padding: 22px 18px; border-radius: 0 0 20px 20px;
  }}
  .header-top {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
  .weather-chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .weather-chip {{ background: rgba(255,255,255,.15); border-radius: 20px; padding: 3px 11px; font-size: 11px; white-space: nowrap; }}
  .header-top-left {{ display: flex; align-items: center; gap: 10px; }}
  .header-name {{ font-weight: 700; font-size: 13px; }}
  /* دکمه‌ی سراسری «نمایش زبان اصلی» - رفع درخواست کاربر: بعضی خبرها (وقتی ترجمه‌ی
     فارسی‌شون به هر دلیلی انجام نشده) به زبان اصلی (معمولا انگلیسی) می‌مونن؛ به‌جای مخفی
     کردن این موضوع، یک دکمه‌ی سراسری اضافه شده که بین «تیتر فارسی» (پیش‌فرض) و «تیتر
     اصلی/زبان مبدا» برای همه‌ی خبرهای صفحه یکجا سوییچ می‌کنه (فقط CSS+JS خالص، بدون
     نیاز به بارگذاری دوباره‌ی صفحه). خبرهایی که از قبل فارسی بودن یا ترجمه‌شون یکسانه،
     تفاوتی با سوییچ نمی‌کنن.
     نکته: title-orig پیش‌فرض مخفیه (display:none)؛ اگه body.show-original ست بشه، جای
     نمایش‌شون برعکس می‌شه - این‌کارو خود JS پایین صفحه انجام می‌ده. */
  .lang-toggle-btn {{
    background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.35); color: #fff;
    border-radius: 20px; padding: 5px 13px; font-size: 12px; cursor: pointer; white-space: nowrap;
    font-family: 'Estedad', Tahoma, Arial, sans-serif;
  }}
  .lang-toggle-btn:hover {{ background: rgba(255,255,255,.28); }}
  .title-orig {{ display: none; }}
  body.show-original .title-fa {{ display: none; }}
  body.show-original .title-orig {{ display: inline; }}
  header h1 {{ margin: 0; font-size: 21px; font-weight: 800; }}
  header p {{ margin: 6px 0 0; opacity: .85; font-size: 12.5px; }}

  .container {{ max-width: 760px; margin: 0 auto; padding: 14px; }}

  /* رو صفحه‌ی بزرگ (کامپیوتر) محتوا رو تو یه ستون باریک وسط صفحه نریزیم -
     چند ستون کنار هم پخش می‌شن تا فضای خالی دوروبر از بین بره و صفحه شبیه
     سایت‌های خبری پر و شلوغ بشه.
     نکته مهم: اینجا از column-width/column-count نیتیو CSS استفاده نمی‌کنیم، چون
     الگوریتم بالانس مرورگر (چه balance چه auto) وقتی چندتا کارت خیلی بلند
     (کارت‌های خبری ۱۰تایی، حدود ۱۷۰۰px) با break-inside:avoid کنار کارت‌های کوتاه
     (طلا، ارز) باشن، رفتار بدی نشون می‌ده - یا فاصله‌ی خالی غول‌آسا وسط صفحه می‌ذاره
     (balance) یا کل محتوا رو تو یه ستون جمع می‌کنه چون ارتفاع container از قبل
     مشخص نیست (auto). به‌جاش پایتون خودش (تابع build_report) بلاک‌های بزرگ رو با
     یک الگوریتم حریصانه (greedy) از قبل بین چند div.col توزیع می‌کنه و اینجا فقط
     با flexbox کنار هم می‌چینیم‌شون - چیدمانی که کاملا قابل پیش‌بینیه و هیچ فاصله
     خالی غیرمنتظره‌ای نداره. */
  .columns-row {{ display: block; }}
  @media (min-width: 860px) {{
    .container {{ max-width: 1500px; padding: 18px; }}
    .columns-row {{ display: flex; align-items: flex-start; gap: 18px; }}
    .columns-row > .col {{ flex: 1; min-width: 0; }}
  }}

  .hero-pair {{ display: flex; gap: 10px; margin-bottom: 12px; }}
  .hero-card {{
    flex: 1; background: linear-gradient(135deg, var(--navy), var(--navy-dark)); color: #fff;
    border-radius: 16px; padding: 16px; text-align: center;
    text-decoration: none; display: block;
  }}
  a.hero-card {{ cursor: pointer; }}
  .hero-label {{ font-size: 12.5px; opacity: .85; margin-bottom: 4px; }}
  .hero-value {{ font-size: 24px; font-weight: 800; }}
  .hero-unit {{ font-size: 11.5px; opacity: .85; margin-top: 3px; }}

  .rate-note {{
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 10px 14px; margin-bottom: 12px; font-size: 13px; font-weight: 600;
    text-decoration: none; color: inherit; cursor: pointer;
  }}
  .rate-note .row-change {{ display: inline; }}

  .note-card {{ border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; font-size: 13.5px; border-right: 4px solid; }}
  .note-card.amber {{ background: #fdf6e3; border-color: #c48a2e; }}
  .note-card.blue {{ background: #eaf1f8; border-color: var(--navy); }}
  .note-card.purple {{ background: #f1ecf6; border-color: #6c4f8c; }}
  .note-card.teal {{ background: #e6f5f2; border-color: #1e8a74; }}
  .note-label {{ font-size: 13.5px; margin-bottom: 6px; }}

  /* متن‌های تولیدشده توسط مدل (خلاصه، پیش‌بینی، تحلیل، گزارش کریپتو) - بعد از تبدیل مارک‌داون به HTML */
  .note-card p, .summary-box p, .comparison-box p, .card-note p {{ margin: 0 0 8px; }}
  .note-card p:last-child, .summary-box p:last-child, .comparison-box p:last-child, .card-note p:last-child {{ margin-bottom: 0; }}
  .md-list {{ margin: 4px 0 10px; padding-inline-start: 22px; }}
  .md-list:last-child {{ margin-bottom: 0; }}
  .md-list li {{ margin-bottom: 5px; line-height: 1.75; }}
  .md-list li::marker {{ color: var(--muted); }}
  .md-hr {{ border: none; border-top: 1px dashed var(--border); margin: 8px 0; }}

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

  /* گرید ۲ستونه کریپتو - قبلا یه ستون بلند بود که خیلی اسکرول لازم داشت */
  .crypto-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 4px 0 10px; }}
  .crypto-cell {{ border: 1px solid var(--border); border-radius: 10px; padding: 8px 9px; min-width: 0; }}
  .crypto-cell-name {{
    display: flex; align-items: center; gap: 4px; font-weight: 700; font-size: 12px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .crypto-cell-icon {{ flex-shrink: 0; font-size: 12px; }}
  .crypto-cell-bottom {{ display: flex; align-items: baseline; justify-content: space-between; gap: 6px; margin-top: 5px; }}
  .crypto-cell-price {{ font-weight: 700; font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .crypto-chg {{ font-size: 10.5px; font-weight: 700; white-space: nowrap; flex-shrink: 0; }}
  .crypto-chg.up {{ color: var(--up); }}
  .crypto-chg.down {{ color: var(--down); }}

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
  .news-item {{ display: flex; gap: 10px; padding: 10px 10px 10px 0; border-bottom: 1px solid var(--border); border-right: 3px solid; margin-bottom: 2px; }}
  .news-item:last-child {{ border-bottom: none; }}
  .news-num {{
    flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; color: #fff;
    font-size: 11.5px; font-weight: 700; display: flex; align-items: center; justify-content: center;
    margin-top: 1px;
  }}
  .news-body {{ flex: 1; min-width: 0; }}
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

  /* روی گوشی (به‌خصوص آیفون)، خیلی از متن‌های ریز این صفحه (۱۰.۵ تا ۱۲.۵ پیکسل - برای
     برچسب قیمت/واحد/منبع خبر/زمان و غیره) با وجود فونت درست (Estedad)، به‌خاطر
     ریزنقشی و پیچیدگی حروف فارسی نسبت به لاتین، در این سایزهای کوچیک کمتر واضح به‌نظر
     می‌رسن - این ربطی به نوع فونت نداره، صرفا اندازه‌ی خیلی کوچیکشه. این بخش فقط زیر
     ۴۸۰px عرض صفحه (یعنی موبایل، نه لپ‌تاپ) این سایزها رو کمی بزرگ‌تر می‌کنه تا خوانایی
     بهتر بشه، بدون اینکه چیدمان دسکتاپ (که کاربر گفته خودش خوبه) تغییری کنه. */
  @media (max-width: 480px) {{
    body {{ font-size: 16px; }}
    .hero-label, .weather-chip, header p {{ font-size: 13.5px; }}
    .hero-unit {{ font-size: 13px; }}
    .row-title, .row-price, .note-card, .note-label, .summary-box, .rate-note {{ font-size: 15px; }}
    .comparison-box, .analysis-text {{ font-size: 14px; }}
    .row-code, .row-unit, .row-change {{ font-size: 12.5px; }}
    .card-note, .overlay-note, .overlay-close, .news-meta, .empty {{ font-size: 12.5px; }}
    .news-source {{ font-size: 12px; }}
    .news-link, .analysis-toggle, .tab-buttons label {{ font-size: 13.5px; }}
    .crypto-cell-price, .crypto-chg, .crypto-cell-icon {{ font-size: 13px; }}
    .count-badge {{ font-size: 12px; }}
  }}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <div class="weather-chips">{weather_html}</div>
    <div class="header-top-left">
      <button type="button" id="lang-toggle-btn" class="lang-toggle-btn" onclick="toggleOriginalLang()"
              title="بین تیتر ترجمه‌شده فارسی و متن اصلی هر خبر سوییچ کن">🌐 نمایش زبان اصلی خبرها</button>
      <div class="header-name">👋 {user_name}</div>
    </div>
  </div>
  <h1>📊 خلاصه اخبار</h1>
  <p>{now_str}</p>
</header>
<div class="container">
  {hero_html}
  {usd_cad_note_html}
  {currency_section_html}
  {currency_overlays}
  {gold_html}
  {gold_overlays_html}
  {market_tip_html}
  {rollup_html}
  <div class="note-card amber"><div class="note-label">📈 <strong>پیش‌بینی اقتصادی</strong></div>{_md(forecast_text)}</div>
  <div class="note-card blue"><div class="note-label">🏛️ <strong>تحلیل سیاسی</strong></div>{_md(political_text)}</div>
  {columns_html}
</div>
<footer>این گزارش به‌صورت خودکار توسط اسکریپت شخصی و Gemini API تولید شده و جایگزین منابع خبری رسمی یا مشاوره مالی نیست.</footer>
<script>
  // دکمه‌ی سراسری «نمایش زبان اصلی»: کلاس show-original رو رو body toggle می‌کنه که با
  // CSS بالا (.title-fa / .title-orig) بین تیتر فارسی و تیتر اصلی هر خبر سوییچ می‌کنه.
  // انتخاب کاربر تو localStorage همین مرورگر ذخیره می‌شه تا دفعه‌ی بعد که همین صفحه رو
  // باز می‌کنه (یا گزارش ساعت بعد رو) دوباره مجبور نشه هر بار کلیک کنه.
  function toggleOriginalLang() {{
    var isOriginal = document.body.classList.toggle('show-original');
    var btn = document.getElementById('lang-toggle-btn');
    if (btn) {{
      btn.textContent = isOriginal ? '🌐 نمایش ترجمه فارسی' : '🌐 نمایش زبان اصلی خبرها';
    }}
    try {{ localStorage.setItem('newsDigestShowOriginalLang', isOriginal ? '1' : '0'); }} catch (e) {{}}
  }}
  (function () {{
    try {{
      if (localStorage.getItem('newsDigestShowOriginalLang') === '1') {{
        document.body.classList.add('show-original');
        var btn = document.getElementById('lang-toggle-btn');
        if (btn) {{ btn.textContent = '🌐 نمایش ترجمه فارسی'; }}
      }}
    }} catch (e) {{}}
  }})();
</script>
</body>
</html>"""

    path = os.path.join(output_dir, f"digest_{datetime.now().strftime('%Y%m%d_%H%M')}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    for alias in ("latest.html", "index.html"):
        with open(os.path.join(output_dir, alias), "w", encoding="utf-8") as f:
            f.write(html)
    return path
