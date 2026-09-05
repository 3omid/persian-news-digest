# -*- coding: utf-8 -*-
"""
گرفتن نرخ ۵ ارز مهم (رسمی، بانک مرکزی کانادا - چند سال تاریخچه برای نمودار روزانه/ماهانه/سالانه)
و دلار بازار آزاد ایران (غیررسمی).
"""

import bisect
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


def _parse_tgju_change_percent(data):
    """
    درصد تغییر روزانه رو از همون پاسخ جدول تاریخچه‌ی tgju.org می‌خونه (نه یک endpoint جدا).
    فرمت: ستون ۵ (index) یک رشته HTML شبیه '<span class="high"><span>+2.99%</span></span>' یا
    برای افت '<span class="low">...-1.23%...</span>' هست. اگه ساختار قابل تشخیص نبود، None برمی‌گردونه
    (نه صفر) تا کد بالادستی بتونه تشخیص بده که داده در دسترس نبوده، نه اینکه واقعا صفر درصد تغییر کرده.
    """
    if isinstance(data, dict) and isinstance(data.get("data"), list) and data["data"]:
        row = data["data"][0]
        if isinstance(row, list) and len(row) > 5:
            raw = str(row[5])
            m = re.search(r"([+-]?[\d.]+)\s*%", raw)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
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


_LIVE_TICKER_URLS = [
    "https://call4.tgju.org/ajax.json",
    "https://call3.tgju.org/ajax.json",
    "https://call2.tgju.org/ajax.json",
    "https://call1.tgju.org/ajax.json",
]
_live_ticker_cache = None


def _get_live_ticker():
    """
    نرخ لحظه‌ای (نه فقط آخرین کندل بسته‌شده‌ی روز قبل) رو از فید عمومی تیکر خود tgju
    می‌گیره - همون فیدی که خود سایت tgju.org برای نمایش «نرخ فعلی» بالای هر صفحه استفاده
    می‌کنه. چرا این لازم شد: endpoint قبلی که فقط استفاده می‌کردیم (summary-table-data)
    یک جدول تاریخچه‌ی روزانه‌ست و ردیف اولش «آخرین روزِ کامل‌شده» است، نه لحظه‌ی الان -
    وقتی بازار ایران (دلار/طلا) روزی چند درصد نوسان می‌کنه، این می‌تونست باعث بشه عددی که
    نشون می‌دادیم یک تا دو روز و چند درصد از قیمت واقعی لحظه‌ای عقب‌تر باشه - دقیقا همون
    چیزی که کاربر بهش گیر داد. نتیجه برای کل یک اجرای برنامه cache می‌شه که برای هر
    شاخص (دلار، هر طلا/سکه) دوباره کل فایل (~۱۷۰KB) دانلود نشه.
    """
    global _live_ticker_cache
    if _live_ticker_cache is not None:
        return _live_ticker_cache
    for url in _LIVE_TICKER_URLS:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            current = resp.json().get("current")
            if isinstance(current, dict) and current:
                _live_ticker_cache = current
                return current
        except Exception as e:
            log.warning(f"فید لحظه‌ای tgju از {url} در دسترس نبود: {e}")
    _live_ticker_cache = {}
    return _live_ticker_cache


def _live_price_and_change(slug):
    """
    از فید لحظه‌ای، قیمت (p) و درصد تغییر روزانه (dp) شاخص slug رو برمی‌گردونه (به ریال،
    مثل جدول تاریخچه). اگه شاخص تو فید لحظه‌ای نبود یا قابل‌پارس نبود، (None, None)
    برمی‌گردونه تا کد بالادستی خودش بره سراغ روش قدیمی (جدول تاریخچه) به‌عنوان جایگزین.
    """
    entry = _get_live_ticker().get(slug)
    if not isinstance(entry, dict):
        return None, None
    try:
        price = float(str(entry.get("p", "")).replace(",", "").strip())
    except (ValueError, TypeError):
        return None, None
    if price <= 0:
        return None, None
    change = entry.get("dp")
    try:
        change = float(change) if change not in (None, "") else None
    except (ValueError, TypeError):
        change = None
    return price, change


def _prefer_live(live_value, fallback_value, tolerance=0.3):
    """
    اگه قیمت لحظه‌ای در دسترس بود و با قیمت جدول تاریخچه (fallback) خیلی فرق نداشت
    (حداکثر ۳۰٪ فاصله - چون دلار/طلای ایران گاهی روزی چند درصد نوسان می‌کنه ولی نه چند
    برابر)، قیمت لحظه‌ای (تازه‌تر) رو برمی‌گردونه. اگه فاصله غیرمنطقی بود (نشونه‌ی یک
    باگ پارس/واحد پول تو فید لحظه‌ای) یا جدول تاریخچه در دسترس نبود، به‌جای ریسک نمایش
    عدد غلط، به fallback امن قدیمی برمی‌گرده (یا اگه اونم نبود، به همون قیمت لحظه‌ای).
    """
    if live_value is None:
        return fallback_value
    if fallback_value is None or fallback_value <= 0:
        return live_value
    ratio = live_value / fallback_value
    if (1 - tolerance) <= ratio <= (1 + tolerance):
        return live_value
    log.warning(
        f"قیمت لحظه‌ای ({live_value}) خیلی با قیمت جدول تاریخچه ({fallback_value}) فرق "
        f"داره (نسبت {ratio:.2f}) - احتمال باگه، از قیمت جدول تاریخچه استفاده می‌شه."
    )
    return fallback_value


def get_gold_coin_prices():
    """
    قیمت طلا و سکه ایران به سبک tgju.org (تومان).
    خروجی: dict {"طلای ۱۸ عیار": {"price": 19054200, "change_percent": None}, ...}
    نکته: این endpoint فقط قیمت لحظه‌ای می‌ده، نه تاریخچه - برای همین دکمه «نمودار» تو گزارش
    مستقیم به نمودار واقعی خود tgju.org لینک می‌شه، نه یک نمودار جعلی از داده نداشته.
    نکته مهم: اسلاگ‌های اندیکاتور tgju (مثل price_dollar_rl) با پسوند "_rl" مقدار را به
    **ریال** برمی‌گردانند، نه تومان (۱ تومان = ۱۰ ریال). چون کل سایت مقادیر را با برچسب
    «تومان» نمایش می‌دهد، باید همینجا بر ۱۰ تقسیم شود تا عدد نمایش‌داده‌شده درست باشد.
    برای تازه بودن قیمت، اول فید لحظه‌ای امتحان می‌شه و در صورت نبود/غیرمنطقی بودن، به
    جدول تاریخچه (روش قبلی) برمی‌گرده - رجوع کن به _prefer_live.
    """
    results = {}
    for title, slug in config.GOLD_COIN_INDICATORS.items():
        history_price = None
        url = config.TGJU_INDICATOR_URL_TMPL.format(slug=slug)
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            raw = _parse_tgju_price(resp.json())
            if raw is not None:
                history_price = raw / 10
        except Exception as e:
            log.error(f"خطا در دریافت {title} ({slug}) از جدول تاریخچه: {e}")

        live_raw, _ = _live_price_and_change(slug)
        live_price = (live_raw / 10) if live_raw is not None else None
        price = _prefer_live(live_price, history_price)

        if price:
            results[title] = {"price": price, "slug": slug}
        else:
            log.warning(f"نه فید لحظه‌ای نه جدول تاریخچه برای {title} ({slug}) در دسترس نبود.")

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
    نکته مهم: اسلاگ endpoint (price_dollar_rl) با پسوند "_rl" نشون می‌ده مقدار برگشتی
    **ریال** است نه تومان (۱ تومان = ۱۰ ریال) - برای همین اینجا بر ۱۰ تقسیم می‌شه تا
    عددی که در همه‌جای سایت با برچسب «تومان» نمایش داده می‌شه واقعاً تومان باشه.
    برای تازه بودن نرخ (نه فقط آخرین کندل بسته‌شده‌ی روز قبل که می‌تونست چند درصد عقب‌تر
    از بازار لحظه‌ای باشه)، اول فید لحظه‌ای تیکر tgju امتحان می‌شه؛ رجوع کن به _prefer_live
    برای منطق برگشت به جدول تاریخچه در صورت نبود/غیرمنطقی بودن فید لحظه‌ای.
    """
    history_price = None
    try:
        resp = requests.get(config.IRAN_USD_TOMAN_URL, timeout=15)
        resp.raise_for_status()
        raw = _parse_tgju_price(resp.json())
        if raw is not None:
            history_price = raw / 10
        else:
            log.warning("ساختار پاسخ tgju (جدول تاریخچه) قابل شناسایی نبود.")
    except Exception as e:
        log.error(f"خطا در دریافت نرخ دلار بازار آزاد ایران (جدول تاریخچه): {e}")

    live_raw, _ = _live_price_and_change("price_dollar_rl")
    live_price = (live_raw / 10) if live_raw is not None else None

    price = _prefer_live(live_price, history_price)
    if price is None:
        log.warning("نه فید لحظه‌ای نه جدول تاریخچه‌ی دلار در دسترس نبود - بخش تومانی رد می‌شه.")
    return price


def get_iran_usd_toman_change_percent():
    """
    درصد تغییر روزانه‌ی دلار بازار آزاد تهران (مثبت یعنی گران‌تر شده، منفی یعنی ارزان‌تر).
    اول از فید لحظه‌ای تیکر tgju (تازه‌تر) استفاده می‌کنه؛ اگه در دسترس نبود یا عدد
    غیرمنطقی بود (بیشتر از ۳۰٪ که برای نوسان یک‌روزه دلار ایران بعیده)، از همون جدول
    تاریخچه‌ی قبلی (IRAN_USD_TOMAN_URL) به‌عنوان جایگزین استفاده می‌شه.
    اگه هیچ‌کدوم قابل شناسایی نبود، None برمی‌گردونه (کارت دلار در گزارش این حالت رو
    با نمایش «بدون درصد تغییر» به‌جای عدد غلط/صفر مدیریت می‌کنه).
    """
    _, live_change = _live_price_and_change("price_dollar_rl")
    if live_change is not None and abs(live_change) <= 30:
        return live_change

    try:
        resp = requests.get(config.IRAN_USD_TOMAN_URL, timeout=15)
        resp.raise_for_status()
        return _parse_tgju_change_percent(resp.json())
    except Exception as e:
        log.error(f"خطا در دریافت درصد تغییر دلار بازار آزاد ایران: {e}")
        return None


def get_iran_usd_toman_series():
    """
    برخلاف get_iran_usd_toman (که فقط آخرین قیمت رو می‌ده)، این تابع کل تاریخچه‌ی روزانه‌ی
    نرخ دلار بازار آزاد تهران رو برمی‌گردونه: [(تاریخ "YYYY-MM-DD", قیمت به تومان), ...]
    به ترتیب صعودی (قدیم -> جدید).

    چرا این لازم شد: قبلا نمودار «دلار آمریکا» و «دلار کانادا» توی گزارش هر دو مستقیم از
    روی همون یک سری نرخ رسمی USD/CAD (بانک مرکزی کانادا) رسم می‌شدن - یعنی دقیقا یک نمودار
    با دو عنوان مختلف (کاربر درست متوجه شد که «انگار نمودار کپی شده»). دلیلش این فرض غلط بود
    که «تاریخچه‌ی رایگان نرخ تومانی در دسترس نیست» - ولی همون endpoint که get_iran_usd_toman
    ازش قیمت لحظه‌ای می‌گیره (IRAN_USD_TOMAN_URL)، در واقع یک جدول تاریخچه‌ی کامل (چند صد تا
    چند هزار روز) برمی‌گردونه، نه فقط یک عدد؛ فقط قبلا فقط ردیف اول (جدیدترین روز) ازش
    خونده می‌شد. این تابع همه‌ی ردیف‌ها رو می‌خونه تا نمودار «دلار آمریکا» بتونه از روی
    تاریخچه‌ی واقعی و مستقیم نرخ تومانی رسم بشه (نه یک نمودار جایگزین/کپی).
    """
    try:
        # length/start تلاشیه برای گرفتن بیشترین تاریخچه‌ی ممکن از این API غیررسمی
        # (که مستندات رسمی نداره)؛ اگه سرور این پارامترها رو نادیده بگیره، همون رفتار
        # پیش‌فرضش (چند صد روز اخیر) هم برای نمودار روزانه/ماهانه کاملا کافیه.
        resp = requests.get(config.IRAN_USD_TOMAN_URL, params={"length": 5000, "start": 0}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            log.warning("ساختار پاسخ تاریخچه‌ی دلار بازار آزاد ایران قابل شناسایی نبود.")
            return []

        by_date = {}
        for row in rows:
            if not isinstance(row, list) or len(row) <= 6:
                continue
            try:
                price_rial = float(str(row[3]).replace(",", "").strip())
            except (ValueError, TypeError):
                continue
            # ستون ۶ تاریخ میلادی به فرمت "2026/09/03"ه؛ برای سازگاری با سری‌های بانک
            # مرکزی کانادا (که ISO "YYYY-MM-DD" هستن) به همون فرمت تبدیل می‌شه.
            date_parts = str(row[6]).strip().split("/")
            if len(date_parts) != 3:
                continue
            y, m, d = date_parts
            date_iso = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
            if price_rial > 0:
                by_date[date_iso] = price_rial / 10  # ریال -> تومان

        return sorted(by_date.items())
    except Exception as e:
        log.error(f"خطا در دریافت تاریخچه‌ی نرخ دلار بازار آزاد ایران: {e}")
        return []


def compute_cad_toman_series(usd_toman_series, usd_cad_series):
    """
    چون بازار آزاد ایران نرخ مستقیم «دلار کانادا به تومان» منتشر نمی‌کنه (فقط دلار آمریکا)،
    تاریخچه‌ی دلار کانادا/تومان از روی همین دو داده‌ی واقعی محاسبه می‌شه، نه کپی از نمودار
    نرخ رسمی USD/CAD: CAD_Toman(تاریخ) = USD_Toman(تاریخ) ÷ USD/CAD(نزدیک‌ترین روز کاری قبل).
    (همون فرمولی که compute_toman_rates برای عدد لحظه‌ای «الان» استفاده می‌کنه، اینجا برای
    کل تاریخچه تکرار می‌شه.) چون بانک مرکزی کانادا فقط روزهای کاری نرخ منتشر می‌کنه ولی بازار
    آزاد ایران هرروزه‌ست، برای هر تاریخ دلار/تومان، آخرین نرخ USD/CAD موجود تا همون تاریخ
    (نه لزوما دقیقا همون روز) استفاده می‌شه - نه یک تطبیق دقیق روز‌به‌روز که خیلی از روزها
    خالی می‌موند.
    """
    if not usd_toman_series or not usd_cad_series:
        return []
    cad_dates = [d for d, _ in usd_cad_series]
    cad_values = [v for _, v in usd_cad_series]

    result = []
    for date_str, usd_toman_val in usd_toman_series:
        idx = bisect.bisect_right(cad_dates, date_str) - 1
        if idx < 0:
            continue
        cad_rate = cad_values[idx]
        if cad_rate:
            result.append((date_str, usd_toman_val / cad_rate))
    return result


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
