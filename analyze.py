# -*- coding: utf-8 -*-
"""
ارسال اخبار جمع‌آوری‌شده به Claude API برای:
- خلاصه‌سازی هر دسته
- مقایسه‌ی زاویه دید منابع مختلف (نه فقط خلاصه ساده)
- پیش‌بینی اقتصادی
- تحلیل سیاسی
"""

import json
import logging
import time
import requests

import config

log = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2000, retries: int = 2) -> str:
    """
    پل یکپارچه بین Gemini (رایگان، پیش‌فرض) و Claude - بر اساس config.MODEL_PROVIDER.
    اگه یه خطای موقتی (503/429/timeout) پیش بیاد، خودکار ۱-۲ بار دوباره امتحان می‌کنه
    قبل از اینکه واقعاً fail بشه - اکثر خطاهای گاه‌به‌گاه API با این حل می‌شن.
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            if config.MODEL_PROVIDER == "gemini":
                return _call_gemini(system_prompt, user_prompt, max_tokens)
            return _call_claude(system_prompt, user_prompt, max_tokens)
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 2 * (attempt + 1)
                log.warning(f"تلاش {attempt + 1} ناموفق بود ({e}) - {wait} ثانیه صبر و تلاش دوباره...")
                time.sleep(wait)
    raise last_error


def _call_gemini(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    url = GEMINI_URL_TMPL.format(model=config.GEMINI_MODEL, key=config.GEMINI_API_KEY)
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    try:
        resp = requests.post(url, json=body, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"پاسخ خالی از Gemini: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(p.get("text", "") for p in parts).strip()
    except requests.exceptions.HTTPError as e:
        # متن دقیق خطا رو لاگ می‌کنیم چون خیلی وقتا خود پیام گوگل دقیقا می‌گه مشکل چیه
        detail = e.response.text if e.response is not None else str(e)
        log.error(f"خطای HTTP در فراخوانی Gemini (مدل: {config.GEMINI_MODEL}): {detail}")
        raise RuntimeError(f"Gemini API Error: {e}")


def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    headers = {
        "x-api-key": config.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": config.CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    resp = requests.post(ANTHROPIC_URL, headers=headers, json=body, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(parts).strip()


def _format_items_for_prompt(items):
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. [{it['source']}] {it['title']}\n   خلاصه اولیه: {it['summary'][:300]}\n   لینک: {it['link']}")
    return "\n\n".join(lines)


def summarize_category(category: str, items: list) -> dict:
    """
    خروجی: {"summary": "...", "comparison": "...", "item_analyses": [...], "items": items}
    item_analyses به همون ترتیب items هست - برای دکمه «تحلیل» زیر هر خبر استفاده می‌شه.
    اگر items خالی باشه، تحلیل انجام نمی‌شه.
    """
    if not items:
        return {"summary": "خبر جدیدی در این دسته یافت نشد.", "comparison": "", "item_analyses": [], "items": []}

    system_prompt = (
        "تو یک تحلیلگر و مترجم خبری حرفه‌ای فارسی‌زبان هستی. برای هر خبر داده‌شده سه کار می‌کنی: "
        "۱) اگه تیتر خبر انگلیسی یا هر زبان دیگه‌ای غیر از فارسیه، اون رو به فارسیِ روان و طبیعی "
        "ترجمه می‌کنی (بدون افزودن یا حذف اطلاعات، فقط ترجمه دقیق - اسم افراد/شرکت‌ها/مکان‌ها رو "
        "درست بنویس). اگه تیتر از قبل فارسیه، دقیقاً همون رو بدون تغییر برگردون. "
        "۲) یک تحلیل کوتاه برای هر خبر می‌نویسی. ۳) خلاصه کلی و مقایسه منابع کل دسته رو می‌نویسی. "
        "هرگز نظر شخصی سیاسی نده، فقط تفاوت لحن/زاویه دید منابع رو توصیف کن. "
        "توی summary و comparison هرگز با جمله‌ی کلی و تکراری مثل «این دسته خبری شامل مجموعه‌ای "
        "از اخبار...» یا «این خبرها طیف متنوعی از موضوعات را پوشش می‌دهند» شروع نکن - این‌جور "
        "مقدمه‌چینی هیچ اطلاعاتی نداره. مستقیم برو سر مهم‌ترین خبر/نکته‌ی واقعی این دسته. خروجی رو "
        "دقیقا به فرمت JSON زیر بده و هیچ متن اضافه‌ای ننویس:\n"
        '{"summary": "خلاصه کلی ۳-۵ جمله‌ای، مستقیم و بدون مقدمه، شامل مهم‌ترین خبرهای این دسته", '
        '"comparison": "مقایسه دیدگاه منابع مختلف، ۲-۴ جمله", '
        '"titles_fa": ["ترجمه فارسی تیتر خبر شماره ۱", "برای خبر شماره ۲", "..."], '
        '"item_analyses": ["تحلیل ۱-۲ جمله‌ای برای خبر شماره ۱", "برای خبر شماره ۲", "..."]}\n'
        "طول آرایه‌های titles_fa و item_analyses باید دقیقا برابر تعداد خبرهای داده‌شده باشه و به همون ترتیب."
    )
    user_prompt = f"دسته خبری: {category}\n\nاخبار جمع‌آوری‌شده (به ترتیب شماره):\n\n{_format_items_for_prompt(items)}"

    try:
        raw = _call_llm(system_prompt, user_prompt, max_tokens=3000)
        raw_clean = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw_clean)
        # اطمینان از اینکه طول آرایه‌ها درسته - اگه نه، با مقدار پیش‌فرض پر می‌کنیم
        analyses = parsed.get("item_analyses", [])
        while len(analyses) < len(items):
            analyses.append("تحلیل جداگانه برای این خبر در دسترس نیست.")
        parsed["item_analyses"] = analyses[: len(items)]

        titles_fa = parsed.get("titles_fa", [])
        for i, it in enumerate(items):
            if i < len(titles_fa) and titles_fa[i]:
                it["title"] = titles_fa[i]  # تیتر رو با نسخه فارسی جایگزین می‌کنیم؛ لینک اصلی دست‌نخورده می‌مونه
    except Exception as e:
        log.error(f"خطا در تحلیل دسته {category}: {e}")
        parsed = {
            "summary": "خطا در تحلیل خودکار - لطفا لاگ را بررسی کنید.",
            "comparison": "",
            "item_analyses": ["تحلیل در دسترس نیست."] * len(items),
        }

    parsed["items"] = items
    return parsed


def economic_forecast(economic_items: list, usd_cad_series: list, iran_usd_toman) -> str:
    """تولید یک بخش «پیش‌بینی اقتصادی» کوتاه بر اساس اخبار اقتصادی و نرخ ارز."""
    if not economic_items and not usd_cad_series:
        return "داده کافی برای پیش‌بینی اقتصادی امروز موجود نیست."

    system_prompt = (
        "تو یک تحلیلگر اقتصادی هستی. بر اساس اخبار و نرخ ارز داده‌شده، یک پیش‌بینی کوتاه "
        "و محتاطانه (۳-۵ جمله) درباره روند احتمالی اقتصاد/بازار ارز بنویس. حتما تاکید کن "
        "که این یک تحلیل خودکار است، نه توصیه مالی رسمی."
    )
    user_prompt = (
        f"اخبار اقتصادی:\n{_format_items_for_prompt(economic_items)}\n\n"
        f"نرخ اخیر USD/CAD: {usd_cad_series[-5:] if usd_cad_series else 'نامشخص'}\n"
        f"نرخ دلار بازار آزاد ایران: {iran_usd_toman if iran_usd_toman else 'نامشخص'}"
    )
    try:
        return _call_llm(system_prompt, user_prompt, max_tokens=500)
    except Exception as e:
        log.error(f"خطا در پیش‌بینی اقتصادی: {e}")
        return "خطا در تولید پیش‌بینی اقتصادی."


def political_analysis(domestic_items: list, foreign_items: list, war_items: list) -> str:
    """بخش تحلیل سیاسی کلی - بی‌طرفانه."""
    all_items = domestic_items + foreign_items + war_items
    if not all_items:
        return "خبر سیاسی جدیدی برای تحلیل موجود نیست."

    system_prompt = (
        "تو یک تحلیلگر سیاسی بی‌طرف هستی. بر اساس اخبار سیاسی داخلی، خارجی و اخبار جنگ ایران، "
        "یک تحلیل کوتاه (۴-۶ جمله) بنویس که رویدادهای مهم را به هم مرتبط کند. کاملا بی‌طرف باش، "
        "چند دیدگاه مختلف را ذکر کن، و نظر شخصی نده."
    )
    user_prompt = (
        f"سیاست داخلی:\n{_format_items_for_prompt(domestic_items)}\n\n"
        f"سیاست خارجی:\n{_format_items_for_prompt(foreign_items)}\n\n"
        f"اخبار جنگ ایران:\n{_format_items_for_prompt(war_items)}"
    )
    try:
        return _call_llm(system_prompt, user_prompt, max_tokens=700)
    except Exception as e:
        log.error(f"خطا در تحلیل سیاسی: {e}")
        return "خطا در تولید تحلیل سیاسی."


def crypto_analysis(crypto_market: list, crypto_news_items: list) -> str:
    """
    خلاصه‌ی بازار کریپتو + مهم‌ترین اخبار.
    مهم: هرگز توصیه مستقیم «بخر» یا «بفروش» نمی‌ده - فقط داده و روند رو گزارش می‌کنه.
    این محدودیت عمدی و برای محافظت از خودته - تصمیم مالی نهایی باید با خودت باشه.
    """
    if not crypto_market and not crypto_news_items:
        return "داده کافی برای گزارش کریپتو موجود نیست."

    market_lines = []
    for c in crypto_market:
        market_lines.append(
            f"{c['name']} ({c['symbol']}): ${c['price_usd']:,} | تغییر ۲۴ساعته: {c['change_24h_pct']:.2f}% "
            f"| تغییر ۷روزه: {c['change_7d_pct']:.2f}%" if c.get('change_24h_pct') is not None and c.get('change_7d_pct') is not None
            else f"{c['name']} ({c['symbol']}): ${c['price_usd']}"
        )

    system_prompt = (
        "تو یک گزارشگر داده‌های بازار کریپتوکارنسی هستی، نه یک مشاور مالی. وظیفه‌ات فقط "
        "گزارش واقعیت‌هاست: کدام کوین بیشترین رشد/افت رو داشته، مهم‌ترین اخبار مرتبط چیه، "
        "و این تغییرات احتمالا به چه رویدادی مرتبطه. "
        "قوانین سخت‌گیرانه: هرگز نگو «بخر»، «بفروش»، «زمان مناسب خرید/فروش است» یا هر پیشنهاد "
        "مستقیم معامله‌ای. هرگز پیش‌بینی قیمت آینده نده. فقط داده‌ی گذشته و اخبار رو توصیف کن "
        "و در انتها حتما یادآوری کن که این گزارش توصیه مالی نیست و بازار کریپتو بسیار پرریسک است."
    )
    user_prompt = (
        f"وضعیت بازار (قیمت لحظه‌ای):\n" + "\n".join(market_lines) +
        f"\n\nاخبار مرتبط کریپتو:\n{_format_items_for_prompt(crypto_news_items)}"
    )
    try:
        return _call_llm(system_prompt, user_prompt, max_tokens=700)
    except Exception as e:
        log.error(f"خطا در تحلیل کریپتو: {e}")
        return "خطا در تولید گزارش کریپتو."


def periodic_top_news(history_items: list, period_label: str) -> str:
    """
    خلاصه «مهم‌ترین اخبار» برای یک بازه (روز/هفته/ماه) بر اساس تاریخچه دیتابیس.
    history_items: لیست دیکشنری با کلیدهای title, source, category
    (توجه: چون فقط عنوان و منبع ذخیره می‌شه نه متن کامل، این یک برآورد تقریبیه نه تحلیل عمیق)
    """
    if not history_items:
        return f"خبری برای {period_label} در تاریخچه یافت نشد."

    system_prompt = (
        "تو یک سردبیر خبری هستی. از بین عناوین خبری داده‌شده (که فقط عنوان و منبع و دسته دارن، "
        "نه متن کامل)، ۵ تا ۸ مورد که به‌نظر مهم‌ترین/پرتکرارترین موضوعات بودن رو انتخاب کن. "
        "اگه موضوعی در چند منبع مختلف تکرار شده، احتمالا مهم‌تره.\n"
        "فرمت خروجی: مستقیم با آیتم شماره ۱ شروع کن - هیچ مقدمه یا جمله‌ی اضافه قبل از لیست "
        "ننویس (مثلا ننویس «به عنوان سردبیر...» یا «موارد زیر انتخاب شده‌اند»)، و بعد از لیست هم "
        "هیچ جمع‌بندی یا نتیجه‌گیری اضافه نکن. هر آیتم دقیقا یک خط به این شکل:\n"
        "۱. **عنوان کوتاه موضوع:** یک جمله‌ی مشخص و پر از اطلاعات واقعی درباره‌ش (نه کلی‌گویی)."
    )
    lines = [f"[{it['category']}] {it['title']} (منبع: {it['source']})" for it in history_items[:200]]
    user_prompt = f"بازه زمانی: {period_label}\n\nعناوین:\n" + "\n".join(lines)

    try:
        return _call_llm(system_prompt, user_prompt, max_tokens=800)
    except Exception as e:
        log.error(f"خطا در خلاصه {period_label}: {e}")
        return f"خطا در تولید خلاصه {period_label}."
