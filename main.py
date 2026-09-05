# -*- coding: utf-8 -*-
"""
اسکریپت اصلی.

اجرای عادی (همه دسته‌ها - برای اجرای ساعتی خودکار):
    python main.py

اجرای دستی فقط یک دسته خاص (مثلا وقتی خودت می‌خوای همون لحظه یه گزارش بگیری):
    python main.py --category ورزشی

دسته‌های معتبر دقیقا همونایی هستن که تو config.py تعریف شدن:
    اقتصادی, "سیاسی داخلی", "سیاسی خارجی", ورزشی, "جنگ ایران"

اجرای اجباری حتی اگه خبر جدیدی نباشه (برای تست):
    python main.py --force
"""

import argparse
import html
import logging
from datetime import datetime

import config
import fetch_news
import fetch_rates
import fetch_crypto
import fetch_stocks
import fetch_weather
import analyze
import generate_report
import send_telegram

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def maybe_periodic_rollups():
    """اگه امروز جمعه‌ست یا اول ماهه، خلاصه هفتگی/ماهانه هم اضافه می‌کنه."""
    rollups = {}
    now = datetime.now()

    if now.weekday() == config.WEEKLY_ROLLUP_WEEKDAY:
        log.info("امروز روز خلاصه هفتگیه...")
        weekly_items = fetch_news.get_history(hours=24 * 7)
        rollups["هفته"] = analyze.periodic_top_news(weekly_items, "هفته اخیر")

    if now.day == config.MONTHLY_ROLLUP_DAY:
        log.info("امروز روز خلاصه ماهانه‌ست...")
        monthly_items = fetch_news.get_history(hours=24 * 30)
        rollups["ماه"] = analyze.periodic_top_news(monthly_items, "ماه اخیر")

    return rollups


def _smart_truncate(text: str, limit: int) -> str:
    """
    برش متن در مرز جمله یا حداقل مرز کلمه، نه وسط کلمه/جمله - چون خلاصه‌ی کوتاهی که
    برای تلگرام می‌فرستیم قبلا با text[:150] بریده می‌شد و همیشه وسط یه کلمه/جمله
    قطع می‌شد (ناقص و بی‌معنی به‌نظر می‌رسید). اینجا سعی می‌کنیم تا نزدیک‌ترین
    نقطه/علامت سوال/تعجب قبل از حد مجاز ببریم؛ اگه پیدا نشد، حداقل سر یه کلمه کامل.
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_sentence_end = max(cut.rfind("."), cut.rfind("؟"), cut.rfind("!"))
    if last_sentence_end >= int(limit * 0.4):
        return cut[: last_sentence_end + 1]
    last_space = cut.rfind(" ")
    if last_space >= int(limit * 0.4):
        cut = cut[:last_space]
    return cut.rstrip() + " …"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default=None, help="فقط این دسته رو پردازش کن (اختیاری)")
    parser.add_argument("--force", action="store_true", help="حتی بدون خبر جدید هم گزارش بساز")
    args = parser.parse_args()

    log.info("شروع جمع‌آوری اخبار...")
    news_by_category = fetch_news.fetch_all()

    if args.category:
        if args.category not in news_by_category:
            log.error(f"دسته '{args.category}' معتبر نیست. دسته‌های معتبر: {list(news_by_category.keys())}")
            return
        news_by_category = {k: (v if k == args.category else []) for k, v in news_by_category.items()}

    total_new = sum(len(v) for v in news_by_category.values())
    log.info(f"مجموع خبر جدید: {total_new}")

    if total_new == 0 and not args.force:
        log.info("خبر جدیدی نبود - گزارش ساخته نمی‌شود. (برای اجبار از --force استفاده کن)")
        return

    log.info("دریافت نرخ ارز، طلا و کریپتو...")
    currencies = fetch_rates.get_all_currencies()
    iran_usd_toman = fetch_rates.get_iran_usd_toman()
    usd_change_percent = fetch_rates.get_iran_usd_toman_change_percent()
    gold_coin_prices = fetch_rates.get_gold_coin_prices()
    stock_movers = fetch_stocks.get_stock_movers()
    weather_data = fetch_weather.get_all_weather()
    crypto_market = fetch_crypto.get_crypto_market()

    log.info("تحلیل هر دسته با Claude API...")
    category_analyses = {}
    for category, items in news_by_category.items():
        category_analyses[category] = analyze.summarize_category(category, items)

    log.info("تولید پیش‌بینی اقتصادی، تحلیل سیاسی و گزارش کریپتو...")
    forecast_text = analyze.economic_forecast(
        news_by_category.get("اقتصادی", []), currencies.get("USD/CAD", []), iran_usd_toman
    )
    political_text = analyze.political_analysis(
        news_by_category.get("سیاسی داخلی", []),
        news_by_category.get("سیاسی خارجی", []),
        news_by_category.get("جنگ ایران", []),
    )
    crypto_news = [
        it for it in news_by_category.get("اقتصادی", [])
        if any(k in it["source"].lower() for k in ["coindesk", "cointelegraph"])
    ]
    crypto_text = analyze.crypto_analysis(crypto_market, crypto_news)
    stocks_text = analyze.stock_market_analysis(stock_movers)

    rollups = maybe_periodic_rollups() if not args.category else {}

    log.info("ساخت گزارش HTML...")
    report_path = generate_report.build_report(
        category_analyses, currencies, iran_usd_toman, forecast_text, political_text,
        gold_coin_prices=gold_coin_prices,
        crypto_market=crypto_market, crypto_text=crypto_text, stock_movers=stock_movers,
        weather_data=weather_data, rollups=rollups, usd_change_percent=usd_change_percent,
        stocks_text=stocks_text,
    )
    log.info(f"گزارش ساخته شد: {report_path}")

    # پیام تلگرام قبلا کاملا متن ساده بود (بدون بولد/بولت/جداکننده) و همه‌چیز به‌هم
    # چسبیده به‌نظر می‌رسید. اینجا با parse_mode=HTML (تو send_telegram.py) عنوان هر
    # دسته بولد می‌شه و بین دسته‌ها یه خط جداکننده می‌ذاریم تا از هم مشخص باشن.
    lines = []
    for cat, a in category_analyses.items():
        if not a.get("items"):
            continue
        icon = generate_report.CATEGORY_STYLE.get(cat, {}).get("icon", "📰")
        cat_esc = html.escape(cat)
        summary = a.get("summary", "")
        if summary.startswith("خطا در تحلیل خودکار"):
            body = "⚠️ خلاصه این بخش به‌دلیل خطای موقت آماده نشد (اخبار کامل در فایل پیوست هست)."
        else:
            body = html.escape(_smart_truncate(summary, 280))
        lines.append(f"{icon} <b>{cat_esc}</b>\n{body}")
    short_summary = "📰 <b>خلاصه اخبار</b>\n\n" + "\n\n➖➖➖➖➖\n\n".join(lines)
    send_telegram.send_report(report_path, short_summary)


if __name__ == "__main__":
    main()
