# -*- coding: utf-8 -*-
"""
برترین شرکت‌ها (روزانه/هفتگی) - از Stooq (رایگان، بدون نیاز به کلید API).
"""

import csv
import io
import logging
from datetime import datetime, timedelta

import requests

import config

log = logging.getLogger(__name__)


def _fetch_daily_quote(symbol):
    """قیمت باز/بسته امروز - برای محاسبه تغییر روزانه."""
    url = config.STOOQ_QUOTE_URL_TMPL.format(symbol=symbol)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        row = next(reader, None)
        if not row or row.get("Open") in (None, "N/D"):
            return None
        open_price = float(row["Open"])
        close_price = float(row["Close"])
        return {"open": open_price, "close": close_price}
    except Exception as e:
        log.error(f"خطا در دریافت قیمت روزانه {symbol}: {e}")
        return None


def _fetch_weekly_change(symbol):
    """۵ روز اخیر معاملاتی - برای محاسبه تغییر هفتگی."""
    url = config.STOOQ_HISTORY_URL_TMPL.format(symbol=symbol)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        reader = list(csv.DictReader(io.StringIO(resp.text)))
        if len(reader) < 6:
            return None
        last5 = reader[-5:]
        start_price = float(last5[0]["Open"])
        end_price = float(last5[-1]["Close"])
        if not start_price:
            return None
        return (end_price - start_price) / start_price * 100
    except Exception as e:
        log.error(f"خطا در دریافت تاریخچه هفتگی {symbol}: {e}")
        return None


def get_stock_movers():
    """
    خروجی: لیست دیکشنری {name, symbol, price, change_day_pct, change_week_pct}
    مرتب‌شده بر اساس بیشترین رشد روزانه (برای «برترین شرکت‌ها»).
    """
    results = []
    for stock in config.WATCHLIST_STOCKS:
        symbol = stock["symbol"]
        daily = _fetch_daily_quote(symbol)
        if not daily or not daily["open"]:
            continue
        change_day = (daily["close"] - daily["open"]) / daily["open"] * 100
        change_week = _fetch_weekly_change(symbol)
        results.append({
            "name": stock["name"],
            "symbol": symbol,
            "price": daily["close"],
            "change_day_pct": change_day,
            "change_week_pct": change_week,
        })
    results.sort(key=lambda s: s["change_day_pct"], reverse=True)
    return results


if __name__ == "__main__":
    for s in get_stock_movers():
        print(s)
