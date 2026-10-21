# -*- coding: utf-8 -*-
"""
ساخت داده‌ی اپ موبایل (PWA) - جایگزین ربات تلگرام (bot_handler.py).

اپ روی گوشی (اندروید یا آیفون) خودش مستقیم نمی‌تونه RSS سایت‌های خبری رو بخونه (مرورگر به‌خاطر
CORS اجازه نمی‌ده)، برای همین این اسکریپت تو GitHub Actions هر ۱۵ دقیقه یک‌بار اجرا می‌شه،
آخرین خبرهای هر دکمه‌ی منو + قیمت ارز و طلا رو جمع می‌کنه و تو یک فایل JSON
(app/data.json) می‌ریزه. اپ با زدن هر دکمه همون بخش از این فایل رو نشون می‌ده - دقیقا همون
کاری که دکمه‌های ربات تلگرام می‌کردن.

دکمه‌ها از config.BOT_MENU_BUTTONS خونده می‌شن، پس اضافه/حذف دکمه فقط تو config.py انجام می‌شه.

اجرا:
    python build_app_data.py            # خروجی: app/data.json
    python build_app_data.py out.json   # مسیر دلخواه
"""

import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import feedparser
import requests

import config
from jalali import format_dual_date

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ITEMS_PER_CATEGORY = 12
ITEMS_PER_SOURCE = 6
DEFAULT_OUTPUT = os.path.join("app", "data.json")


def _fetch_feed(url, timeout=10):
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def _entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return None


def _fetch_source(src):
    """آیتم‌های یک منبع - اگه منبع جواب نده، لیست خالی (نه exception) تا بقیه منابع خراب نشن."""
    try:
        feed = _fetch_feed(src["url"])
    except Exception as e:
        log.warning(f"منبع جواب نداد: {src['name']} ({e})")
        return []
    items = []
    for entry in feed.entries[:ITEMS_PER_SOURCE]:
        title = getattr(entry, "title", "").strip()
        if not title:
            continue
        pub = _entry_time(entry)
        items.append({
            "title": title,
            "link": getattr(entry, "link", "").strip(),
            "source": src["name"].replace("تلگرام: ", ""),
            "published": pub.isoformat() if pub else None,
        })
    return items


def _fetch_all_categories():
    """همه منابع همه دسته‌ها رو موازی می‌گیره (یک منبع مشترک بین چند دسته فقط یک‌بار دانلود می‌شه)."""
    urls = {}
    for sources in config.RSS_SOURCES.values():
        for src in sources:
            urls.setdefault(src["url"], src)

    with ThreadPoolExecutor(max_workers=12) as pool:
        fetched = dict(zip(urls, pool.map(_fetch_source, urls.values())))

    result = {}
    for category, sources in config.RSS_SOURCES.items():
        seen_titles = set()
        items = []
        for src in sources:
            for it in fetched.get(src["url"], []):
                if it["title"] in seen_titles:
                    continue
                seen_titles.add(it["title"])
                items.append(_clean_google_news(dict(it, source=src["name"].replace("تلگرام: ", ""))))
        # خبرهای بدون تاریخ میرن ته لیست
        items.sort(key=lambda x: x["published"] or "", reverse=True)
        result[category] = items[:ITEMS_PER_CATEGORY]
        log.info(f"[{category}] {len(result[category])} خبر")
    return result


def _rates_snapshot():
    """همون اطلاعات دکمه «طلا و ارز» ربات، به‌صورت ساخت‌یافته."""
    import fetch_rates

    rows = []
    try:
        usd_cad = fetch_rates.get_currency_series("FXUSDCAD")
        if usd_cad:
            rows.append({"label": "۱ دلار آمریکا", "value": round(usd_cad[-1][1], 4), "unit": "دلار کانادا"})
    except Exception as e:
        log.warning(f"خطا در نرخ ارز: {e}")
    try:
        toman = fetch_rates.get_iran_usd_toman()
        if toman:
            rows.append({"label": "دلار بازار آزاد ایران", "value": round(toman), "unit": "تومان"})
    except Exception as e:
        log.warning(f"خطا در نرخ تومان: {e}")
    try:
        for title, info in fetch_rates.get_gold_coin_prices().items():
            rows.append({"label": title, "value": round(info["price"]), "unit": "تومان"})
    except Exception as e:
        log.warning(f"خطا در قیمت طلا: {e}")
    return rows


def _clean_google_news(item):
    """تیترهای Google News آخرشون « - اسم سایت» دارن؛ اسم سایت رو جدا می‌کنیم و منبع می‌کنیم."""
    if "news.google.com" in item.get("link", "") and " - " in item["title"]:
        title, _, publisher = item["title"].rpartition(" - ")
        if title and publisher and len(publisher) < 60:
            item["title"], item["source"] = title.strip(), publisher.strip()
    return item


SPARK_DAYS = 30
# قیمت‌های صفحه اصلی (به ترتیب نمایش): کلید، عنوان، شاخص tgju (None = حساب‌شده)
DASHBOARD_PRICES = [
    ("usd", "دلار آمریکا", "price_dollar_rl"),
    ("cad", "دلار کانادا", None),
    ("sekee", "سکه تمام (امامی)", "sekee"),
    ("nim", "نیم سکه", "nim"),
    ("geram18", "طلای ۱۸ عیار (گرم)", "geram18"),
]


def _pct(now, prev):
    return round((now - prev) / prev * 100, 2) if now and prev else None


def _dashboard_prices():
    """
    قیمت‌های کوچیک صفحه اصلی: قیمت الان (تومان)، درصد تغییر روزانه، و قیمت ۳۰ روز اخیر برای
    نمودار کوچیک (sparkline). دلار کانادا به تومان مستقیم منتشر نمی‌شه و از دلار/تومان ÷ USD/CAD
    حساب می‌شه (همون روش گزارش).
    """
    import fetch_rates

    def safe(func, default):
        try:
            return func()
        except Exception as e:
            log.warning(f"خطا در قیمت‌های صفحه اصلی: {e}")
            return default

    usd_hist = safe(fetch_rates.get_iran_usd_toman_series, [])
    usd_cad_hist = safe(lambda: fetch_rates.get_currency_series("FXUSDCAD"), [])
    usd_now = safe(fetch_rates.get_iran_usd_toman, None)
    gold_now = safe(fetch_rates.get_gold_coin_prices, {})
    gold_by_slug = {v["slug"]: v["price"] for k, v in gold_now.items() if not v.get("approx")}

    out = []
    for key, label, slug in DASHBOARD_PRICES:
        if key == "usd":
            now, hist = usd_now, usd_hist
        elif key == "cad":
            hist = fetch_rates.compute_cad_toman_series(usd_hist, usd_cad_hist)
            now = usd_now / usd_cad_hist[-1][1] if usd_now and usd_cad_hist else None
        else:
            now = gold_by_slug.get(slug)
            hist = safe(lambda: fetch_rates._get_tgju_history_series(
                config.TGJU_INDICATOR_URL_TMPL.format(slug=slug)), [])
        if not now:
            continue
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        past = [v for d, v in hist if d < today][-SPARK_DAYS:]
        change = fetch_rates._live_price_and_change(slug)[1] if slug else None
        if change is None or abs(change) > 30:
            change = _pct(now, past[-1] if past else None)
        out.append({
            "key": key, "label": label, "value": round(now), "unit": "تومان",
            "change": change, "spark": [round(v) for v in past] + [round(now)],
        })
    return out


def _unique(groups, per_group=None):
    """چند لیست خبر رو پشت هم می‌چینه و خبرهای تکراری (هم‌عنوان) بین لیست‌ها رو حذف می‌کنه."""
    seen, out = set(), []
    for items in groups:
        taken = 0
        for it in items:
            if it["title"] in seen:
                continue
            seen.add(it["title"])
            out.append(it)
            taken += 1
            if per_group and taken >= per_group:
                break
    return out


def build(output_path=DEFAULT_OUTPUT):
    news = _fetch_all_categories()
    sections = []
    for label, key in config.BOT_MENU_BUTTONS:
        section = {"key": key, "label": label}
        if key == "gold_currency":
            section["type"] = "rates"
            section["rates"] = _rates_snapshot()
        elif key == "all":
            # مثل ربات: آخرین خبر هر دسته (خبری که تو دسته‌ی قبلی اومده، تکرار نمی‌شه)
            section["type"] = "news"
            section["items"] = _unique([
                [dict(it, category=cat) for it in items] for cat, items in news.items()
            ], per_group=1)
        elif key == "سیاسی":
            section["type"] = "news"
            section["items"] = _unique([
                [dict(it, category=cat) for it in news.get(cat, [])]
                for cat in ("سیاسی داخلی", "سیاسی خارجی")
            ])
        else:
            section["type"] = "news"
            section["items"] = news.get(key, [])
        sections.append(section)

    now = datetime.now(timezone.utc)
    data = {
        "generated_at": now.isoformat(),
        "generated_at_label": format_dual_date(now),
        "prices": _dashboard_prices(),
        "sections": sections,
    }
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    log.info(f"داده‌ی اپ ساخته شد: {output_path}")
    return output_path


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT)
