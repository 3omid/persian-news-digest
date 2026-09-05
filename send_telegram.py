# -*- coding: utf-8 -*-
"""ارسال گزارش نهایی به تلگرام (فایل HTML به‌عنوان سند + خلاصه متنی کوتاه)."""

import logging
import requests

import config

log = logging.getLogger(__name__)


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
                "text": short_summary[:4000],
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
