# -*- coding: utf-8 -*-
"""ارسال گزارش نهایی به تلگرام (فایل HTML به‌عنوان سند + خلاصه متنی کوتاه)."""

import logging
import requests

import config

log = logging.getLogger(__name__)

TELEGRAM_TEXT_LIMIT = 4096


def _safe_truncate_html(text: str, limit: int) -> str:
    """
    برش امن یک متن با تگ‌های ساده‌ی <b>...</b> (همونایی که main.py برای عنوان هر دسته
    می‌سازه) در مرز محدودیت کاراکتری تلگرام. قبلا این برش با یک [:limit] ساده انجام
    می‌شد که ممکن بود دقیقا وسط یک تگ <b> یا </b> ببره؛ در اون حالت تلگرام کل پیام رو با
    خطای "can't find end of the entity" رد می‌کنه (نه فقط قسمت بریده‌شده رو). اینجا اگه
    بعد از برش یک <b> بدون </b> بسته‌کننده باقی بمونه، متن تا آخرین خط کامل قبلی کوتاه
    می‌شه و در صورت لزوم </b> بسته می‌شه تا پیام همیشه سالم بمونه.
    """
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if cut.count("<b>") > cut.count("</b>"):
        last_safe_nl = cut.rfind("\n")
        if last_safe_nl > 0:
            cut = cut[:last_safe_nl]
        if cut.count("<b>") > cut.count("</b>"):
            cut += "</b>"
    return cut.rstrip() + "\n…"


def send_report(html_path: str, short_summary: str = ""):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        log.warning("توکن یا chat_id تلگرام تنظیم نشده - ارسال انجام نشد.")
        return False

    base = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

    if short_summary:
        try:
            # parse_mode=HTML تا <b>...</b> که تو main.py برای عنوان هر دسته ساخته می‌شه
            # واقعا بولد نمایش داده بشه، نه به‌صورت تگ خام تو پیام.
            resp = requests.post(f"{base}/sendMessage", data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": _safe_truncate_html(short_summary, TELEGRAM_TEXT_LIMIT - 96),
                "parse_mode": "HTML",
            }, timeout=20)
            if not resp.ok:
                log.error(f"خطا در ارسال پیام متنی تلگرام: {resp.status_code} - {resp.text}")
        except Exception as e:
            log.error(f"خطا در ارسال پیام متنی تلگرام: {e}")

    try:
        with open(html_path, "rb") as f:
            resp = requests.post(f"{base}/sendDocument", data={
                "chat_id": config.TELEGRAM_CHAT_ID,
            }, files={"document": f}, timeout=30)
        if not resp.ok:
            log.error(f"خطا در ارسال فایل گزارش به تلگرام: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
        return True
    except Exception as e:
        log.error(f"خطا در ارسال فایل گزارش به تلگرام: {e}")
        return False
