# -*- coding: utf-8 -*-
"""
برترین شرکت‌ها (روزانه/هفتگی) - از API غیررسمی و رایگان Chart یاهو فایننس.
(منبع قبلی، Stooq، کاملا از کار افتاده بود - همه نمادها ۴۰۴ برمی‌گردوندن.)
"""

import logging

import requests

import config

log = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _fetch_daily_history(symbol):
    """
    ۵ روز اخیر معاملاتی روزانه (باز/بسته) رو یکجا می‌گیره - هم برای محاسبه تغییر
    روزانه (امروز) هم تغییر هفتگی (نسبت به ۵ روز پیش) کافیه، بدون نیاز به دو درخواست جدا.
    """
    url = config.YAHOO_CHART_URL_TMPL.format(symbol=symbol)
    try:
        resp = requests.get(url, timeout=15, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        result = ((data or {}).get("chart") or {}).get("result") or []
        if not result:
            return None
        quotes = result[0]["indicators"]["quote"][0]
        raw_opens = quotes.get("open", [])
        raw_closes = quotes.get("close", [])
        # نکته مهم (اصلاح باگ): قبلا open و close هرکدوم جدا از دیگری فیلتر می‌شدن (None
        # هاشون مستقل حذف می‌شد)، بدون توجه به این‌که ایندکس‌هاشون به چه روزی اشاره داره.
        # وقتی بازار هنوز بازه، یاهو برای کندل امروز معمولا open داره ولی close هنوز None
        # است (روز کامل نشده) - فیلتر مستقل باعث می‌شد opens[-1] (باز شدن امروز) با
        # closes[-1] (در واقع بسته‌شدن دیروز، چون آخرین close غیر-None امروز نبود) مقایسه
        # بشه؛ یعنی «تغییر روزانه» در واقع یک گپ شبانه‌ی غلط بود، نه تغییر واقعی امروز.
        # الان فقط روزهایی که هم open و هم close دارن (هم‌ایندکس) نگه داشته می‌شن.
        paired = [(o, c) for o, c in zip(raw_opens, raw_closes) if o is not None and c is not None]
        if not paired:
            return None
        return {
            "today_open": paired[-1][0],
            "today_close": paired[-1][1],
            "week_open": paired[0][0],
        }
    except Exception as e:
        log.error(f"خطا در دریافت تاریخچه قیمت {symbol}: {e}")
        return None


def get_stock_movers():
    """
    خروجی: لیست دیکشنری {name, symbol, price, change_day_pct, change_week_pct}
    مرتب‌شده بر اساس بیشترین رشد روزانه (برای «برترین شرکت‌ها»).
    """
    results = []
    for stock in config.WATCHLIST_STOCKS:
        symbol = stock["symbol"]
        hist = _fetch_daily_history(symbol)
        if not hist or not hist["today_open"]:
            continue
        change_day = (hist["today_close"] - hist["today_open"]) / hist["today_open"] * 100
        change_week = None
        if hist.get("week_open"):
            change_week = (hist["today_close"] - hist["week_open"]) / hist["week_open"] * 100
        results.append({
            "name": stock["name"],
            "symbol": symbol,
            "price": hist["today_close"],
            "change_day_pct": change_day,
            "change_week_pct": change_week,
        })
    results.sort(key=lambda s: s["change_day_pct"], reverse=True)
    return results


if __name__ == "__main__":
    for s in get_stock_movers():
        print(s)
