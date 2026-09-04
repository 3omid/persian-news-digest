# -*- coding: utf-8 -*-
"""
گرفتن قیمت طلا (GoldAPI) و کریپتوکارنسی‌ها (CoinGecko - رایگان و بدون کلید).
هیچ‌کدوم از این توابع توصیه خرید/فروش نمی‌دن - فقط داده خام قیمت و درصد تغییر.
"""

import logging
import requests

import config

log = logging.getLogger(__name__)


def get_gold_price():
    """قیمت هر اونس طلا به دلار. اگه GOLD_API_KEY تنظیم نشده باشه، None برمی‌گردونه."""
    if not config.GOLD_API_KEY:
        log.warning("GOLD_API_KEY تنظیم نشده - بخش طلا رد می‌شه.")
        return None
    try:
        resp = requests.get(
            config.GOLD_API_URL,
            headers={"x-access-token": config.GOLD_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "price_usd_oz": data.get("price"),
            "change": data.get("ch"),
            "change_percent": data.get("chp"),
            "price_gram_24k": data.get("price_gram_24k"),
        }
    except Exception as e:
        log.error(f"خطا در دریافت قیمت طلا: {e}")
        return None


def get_crypto_market():
    """
    خروجی: لیستی از دیکشنری برای هر کوین ردیابی‌شده شامل قیمت، تغییر ۲۴ ساعته و ۷ روزه.
    کاملا رایگان - بدون نیاز به کلید (CoinGecko public API).
    """
    try:
        resp = requests.get(
            config.COINGECKO_MARKETS_URL,
            params={
                "vs_currency": "usd",
                "ids": ",".join(config.TRACKED_COINS),
                "order": "market_cap_desc",
                "price_change_percentage": "24h,7d",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        result = []
        for coin in data:
            result.append({
                "id": coin.get("id"),
                "name": coin.get("name"),
                "symbol": (coin.get("symbol") or "").upper(),
                "price_usd": coin.get("current_price"),
                "change_24h_pct": coin.get("price_change_percentage_24h_in_currency"),
                "change_7d_pct": coin.get("price_change_percentage_7d_in_currency"),
                "market_cap": coin.get("market_cap"),
            })
        # مرتب‌سازی بر اساس بیشترین رشد ۲۴ ساعته - برای بخش "بیشترین رشد/افت"
        result.sort(key=lambda c: (c["change_24h_pct"] or 0), reverse=True)
        return result
    except Exception as e:
        log.error(f"خطا در دریافت قیمت کریپتو: {e}")
        return []


if __name__ == "__main__":
    print("Gold:", get_gold_price())
    print("Crypto:", get_crypto_market())
