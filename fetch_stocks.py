# -*- coding: utf-8 -*-
"""
برترین شرکت‌ها (روزانه/هفتگی) - از Yahoo Finance (رایگان، بدون نیاز به کلید API).
"""

import logging

import requests

import config

log = logging.getLogger(__name__)


def _fetch_chart(symbol):
    url = config.YAHOO_CHART_URL_TMPL.format(symbol=symbol)
    resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    data = resp.json()
    result = data.get("chart", {}).get("result")
    if not result:
        return None
    return result[0]


def get_stock_movers():
    """
    خروجی: لیست دیکشنری {name, symbol, price, change_day_pct, change_week_pct}
    مرتب‌شده بر اساس بیشترین رشد روزانه (برای «برترین شرکت‌ها»).
    یه خطا رو یک نماد باعث نمی‌شه بقیه یا کل گزارش خراب بشه.
    """
    results = []
    for stock in config.WATCHLIST_STOCKS:
        symbol = stock["symbol"]
        try:
            chart = _fetch_chart(symbol)
            if not chart:
                continue
            meta = chart.get("meta", {})
            price = meta.get("regularMarketPrice")
            prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
            if not price or not prev_close:
                continue
            change_day = (price - prev_close) / prev_close * 100

            change_week = None
            closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                change_week = (closes[-1] - closes[0]) / closes[0] * 100

            results.append({
                "name": stock["name"],
                "symbol": symbol,
                "price": price,
                "change_day_pct": change_day,
                "change_week_pct": change_week,
            })
        except Exception as e:
            log.error(f"خطا در دریافت قیمت {symbol}: {e}")

    results.sort(key=lambda s: s["change_day_pct"], reverse=True)
    return results


if __name__ == "__main__":
    for s in get_stock_movers():
        print(s)
