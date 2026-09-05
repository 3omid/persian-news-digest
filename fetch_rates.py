# -*- coding: utf-8 -*-
"""
گرفتن نرخ ۵ ارز مهم (رسمی، بانک مرکزی کانادا - چند سال تاریخچه برای نمودار روزانه/ماهانه/سالانه)
و دلار بازار آزاد ایران (غیررسمی).
"""

import logging
import re
from datetime import datetime, timedelta

import requests

import config

log = logging.getLogger(__name__)


def _parse_tgju_price(data):
    """
    tgju.org چند فرمت مختلف برگردونده و بدون اطلاع فرمتش رو عوض می‌کنه (API غیررسمیه).
    فرمت جدیدی که الان برمی‌گردونه یک جدول تاریخچه‌ست:
        {"data": [["228,348,000","228,348,000","235,710,000","235,188,000", "<span...>change</span>",
                   "<span...>+2.99%</span>", "2026/09/03", "1405/06/12"], ...]}
    ردیف صفر = جدیدترین روز، ستون‌ها به ترتیب [باز, کمترین, بیشترین, بسته/آخرین].
    فرمت قدیمی‌تر (دیکشنری تک‌مقداری {"p"/"price"/"value"/"last": ...}) هم پشتیبانی می‌شه
    که اگه یه روز دوباره برگرده، بدون تغییر کد کار کنه.
    """
    if isinstance(data, dict) and isinstance(data.get("data"), list) and data["data"]:
        row = data["data"][0]
        if isinstance(row, list) and len(row) > 3:
            try:
                return float(str(row[3]).replace(",", "").strip())
            except (ValueError, TypeError):
                pass

    raw = data[0] if isinstance(data, list) and data else data
    if isinstance(raw, dict):
        for key in ("p", "price", "value", "last"):
            if key in raw and raw[key] not in (None, ""):
                try:
                    return float(str(raw[key]).replace(",", "").strip())
                except (ValueError, TypeError):
                    continue
    elif isinstance(raw, (int, float)):
        return float(raw)
    return None


def get_currency_series(series_id: str):
    """برمی‌گردونه لیستی از (تاریخ, نرخ) برای چند سال اخیر (کافی برای نمودار روزانه/ماهانه/سالانه)."""
    start_date = (datetime.now() - timedelta(days=365 * config.BOC_HISTORY_YEARS)).strftime("%Y-%m-%d")
    url = config.BOC_OBSERVATIONS_URL_TMPL.format(series=series_id, start_date=start_date)
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        series = []
        for obs in data.get("observations", []):
            date = obs.get("d")
            val = obs.get(series_id, {}).get("v")
            if date and val:
                series.append((date, float(val)))
        return series
    except Exception as e:
        log.error(f"خطا در دریافت نرخ {series_id}: {e}")
        return []


def get_all_currencies():
    """خروجی: dict {"USD/CAD": [(date, val), ...], ...}"""
    result = {}
    for pair_name, series_id in config.TRACKED_CURRENCIES.items():
        result[pair_name] = get_currency_series(series_id)

    # ارزهای بدون سری مستقیم بانک مرکزی کانادا (مثل AED که نرخش به دلار آمریکا ثابته/Peg) -
    # از روی سری پایه‌ای که بالا واکشی شده محاسبه می‌شن، نه از یک API جداگانه.
    for pair_name, spec in getattr(config, "COMPUTED_CURRENCIES", {}).items():
        base_series = result.get(spec["base"], [])
        divisor = spec.get("divide_by", 1) or 1
        result[pair_name] = [(date, val / divisor) for date, val in base_series]
    return result


def resample_by_period(daily_series):
    """
    ورودی: لیست (date_str, value) روزانه.
    خروجی: {"daily": [...آخرین ۳۰ روز...], "monthly": [...میانگین هر ماه، ۲۴ ماه اخیر...],
             "yearly": [...میانگین هر سال...]}
    """
    if not daily_series:
        return {"daily": [], "monthly": [], "yearly": []}

    daily = daily_series[-30:]

    monthly_buckets = {}
    for date_str, val in daily_series:
        key = date_str[:7]  # YYYY-MM
        monthly_buckets.setdefault(key, []).append(val)
    monthly_keys = sorted(monthly_buckets.keys())[-24:]
    monthly = [(k, sum(monthly_buckets[k]) / len(monthly_buckets[k])) for k in monthly_keys]

    yearly_buckets = {}
    for date_str, val in daily_series:
        key = date_str[:4]  # YYYY
        yearly_buckets.setdefault(key, []).append(val)
    yearly_keys = sorted(yearly_buckets.keys())
    yearly = [(k, sum(yearly_buckets[k]) / len(yearly_buckets[k])) for k in yearly_keys]

    return {"daily": daily, "monthly": monthly, "yearly": yearly}


def get_gold_coin_prices():
    """
    قیمت طلا و سکه ایران به سبک tgju.org (تومان).
    خروجی: dict {"طلای ۱۸ عیار": {"price": 19054200, "change_percent": None}, ...}
    نکته: این endpoint فقط قیمت لحظه‌ای می‌ده، نه تاریخچه - برای همین دکمه «نمودار» تو گزارش
    مستقیم به نمودار واقعی خود tgju.org لینک می‌شه، نه یک نمودار جعلی از داده نداشته.
    """
    results = {}
    for title, slug in config.GOLD_COIN_INDICATORS.items():
        url = config.TGJU_INDICATOR_URL_TMPL.format(slug=slug)
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            price = _parse_tgju_price(data)
            if price:
                results[title] = {"price": price, "slug": slug}
            else:
                log.warning(f"ساختار پاسخ tgju برای {title} ({slug}) قابل شناسایی نبود.")
        except Exception as e:
            log.error(f"خطا در دریافت {title} ({slug}): {e}")

    # طلای دست دوم شاخص رسمی نداره - تخمین تقریبی از روی طلای ۱۸ عیار
    if "طلای ۱۸ عیار" in results:
        results["طلای دست دوم (تقریبی)"] = {
            "price": results["طلای ۱۸ عیار"]["price"] * 0.99,
            "slug": "geram18",
            "approx": True,
        }
    return results


def get_iran_usd_toman():
    """
    نرخ دلار بازار آزاد تهران به تومان (عدد اعشاری خالص، نه رشته/دیکشنری).
    این یک API غیررسمی است و ممکنه ساختارش عوض بشه - در اون صورت None برمی‌گردونه
    و بقیه محاسبات ریالی (تبدیل ارزها به تومان) به‌طور خودکار غیرفعال می‌شن.
    """
    try:
        resp = requests.get(config.IRAN_USD_TOMAN_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        price = _parse_tgju_price(data)
        if price is not None:
            return price
        log.warning("ساختار پاسخ tgju قابل شناسایی نبود - بخش تومانی رد می‌شه.")
        return None
    except Exception as e:
        log.error(f"خطا در دریافت نرخ دلار بازار آزاد ایران: {e}")
        return None


def compute_toman_rates(iran_usd_toman, resampled_currencies):
    """
    با استفاده از نرخ دلار بازار آزاد ایران (تومان) + نرخ‌های رسمی کانادا،
    قیمت هر ارز رو به تومان تخمین می‌زنه.
    فرمول: تومان_ارز_X = (X/CAD) × (تومان_دلار / USD‌CAD)
    خروجی: dict {"USD": 1042000, "CAD": ..., "EUR": ..., ...}
    """
    if not iran_usd_toman:
        return {}
    usd_cad_daily = resampled_currencies.get("USD/CAD", {}).get("daily", [])
    if not usd_cad_daily:
        return {}
    usd_cad_latest = usd_cad_daily[-1][1]

    toman_rates = {"USD": iran_usd_toman, "CAD": iran_usd_toman / usd_cad_latest}
    for pair_name, resampled in resampled_currencies.items():
        if pair_name == "USD/CAD":
            continue
        code = pair_name.split("/")[0]
        daily = resampled.get("daily", [])
        if not daily:
            continue
        latest_in_cad = daily[-1][1]
        toman_rates[code] = latest_in_cad * iran_usd_toman / usd_cad_latest
    return toman_rates


if __name__ == "__main__":
    c = get_all_currencies()
    for pair, series in c.items():
        print(pair, "->", len(series), "نقطه داده")
    print("Iran USD/Toman:", get_iran_usd_toman())
