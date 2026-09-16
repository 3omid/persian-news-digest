# -*- coding: utf-8 -*-
"""
ارسال گزارش نهایی به تلگرام - به چند مقصد هم‌زمان (فایل HTML + خلاصه متنی کوتاه).

TELEGRAM_CHAT_ID می‌تونه چند مقصد رو با کاما از هم جدا شده داشته باشه، هر ترکیبی:
- آیدی عددی شخصی (مثلا 7022880679) - برای اینکه به یه نفر خاص برسه، اون شخص باید
  قبلش رو ربات Start زده باشه.
- @یوزرنیم یه کانال تلگرام (مثلا @my_news_channel) - برای اینکه به همه اعضای کانال
  برسه، ربات باید ادمین اون کانال با اجازه‌ی «ارسال پیام» باشه.
مثال یک سیکرت با هر دو نوع ترکیب‌شده:
  7022880679,@my_news_channel,123456789
"""

import logging
import requests

import config

log = logging.getLogger(__name__)


def _get_targets():
    """
    لیست مقصدها رو از دو جا جمع می‌کنه:
    ۱) سیکرت TELEGRAM_CHAT_ID (دستی، با کاما جدا)
    ۲) فایل bot_state.json (خودکار - هرکی رو ربات /start زده)
    و بدون تکراری برمی‌گردونه.
    """
    import json
    import os

    raw = config.TELEGRAM_CHAT_ID or ""
    targets = [t.strip() for t in raw.split(",") if t.strip()]

    if os.path.exists(config.BOT_STATE_FILE):
        try:
            with open(config.BOT_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            for sub in state.get("subscribers", []):
                chat_id = str(sub.get("chat_id", "")).strip()
                if chat_id:
                    targets.append(chat_id)
        except Exception as e:
            log.warning(f"خطا در خوندن {config.BOT_STATE_FILE}: {e}")

    return list(dict.fromkeys(targets))  # حذف موارد تکراری، ترتیب حفظ می‌شه


def send_report(html_path: str, short_summary: str = ""):
    if not config.TELEGRAM_BOT_TOKEN:
        log.warning("توکن تلگرام تنظیم نشده - ارسال انجام نشد.")
        return False

    targets = _get_targets()
    if not targets:
        log.warning("هیچ مقصدی پیدا نشد (نه تو TELEGRAM_CHAT_ID نه تو bot_state.json).")
        return False

    log.info(f"شروع ارسال گزارش به {len(targets)} مقصد: {', '.join(targets)}")

    base = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
    success_list = []
    failed_list = []

    for chat_id in targets:
        if short_summary:
            try:
                resp = requests.post(f"{base}/sendMessage", data={
                    "chat_id": chat_id,
                    "text": short_summary[:4000],
                }, timeout=20)
                if not resp.ok:
                    log.error(f"خطا در ارسال پیام متنی تلگرام به {chat_id}: {resp.status_code} - {resp.text}")
            except Exception as e:
                log.error(f"خطا در ارسال پیام متنی تلگرام به {chat_id}: {e}")

        try:
            with open(html_path, "rb") as f:
                resp = requests.post(f"{base}/sendDocument", data={
                    "chat_id": chat_id,
                }, files={"document": f}, timeout=30)
            if not resp.ok:
                log.error(f"خطا در ارسال فایل گزارش به {chat_id}: {resp.status_code} - {resp.text}")
                failed_list.append(chat_id)
            else:
                success_list.append(chat_id)
        except Exception as e:
            log.error(f"خطا در ارسال فایل گزارش به {chat_id}: {e}")
            failed_list.append(chat_id)

    log.info(f"✅ خلاصه ارسال: موفق برای {len(success_list)} نفر ({', '.join(success_list) if success_list else '-'}) "
              f"| ناموفق برای {len(failed_list)} نفر ({', '.join(failed_list) if failed_list else '-'})")

    return len(success_list) > 0
