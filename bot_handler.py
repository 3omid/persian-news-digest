# -*- coding: utf-8 -*-
"""
ربات تعاملی تلگرام. این اسکریپت هر چند دقیقه (از طریق یک workflow جدا) اجرا می‌شه،
پیام‌ها/کلیک‌های جدید رو از تلگرام می‌گیره (Telegram getUpdates - بدون نیاز به سرور همیشه‌روشن)
و بهشون جواب می‌ده:

- کسی که /start بزنه: خودکار عضو می‌شه (نیاز به تایید نداره) + پیام خوش‌آمد و منوی دکمه‌ای می‌گیره.
- کسی رو دکمه بزنه: آخرین خبر همون دسته رو فوری (زنده از RSS) براش می‌فرسته.
- لیست اعضا تو فایل config.BOT_STATE_FILE ذخیره می‌شه (خودکار commit می‌شه تو ریپو) -
  از همونجا می‌تونی هر وقت خواستی ببینی کیا عضو شدن.
"""

import json
import logging
import os
from datetime import datetime, timezone

import feedparser
import requests

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


# ---------------------------------------------------------------
# ذخیره/بارگذاری وضعیت (لیست اعضا + آخرین آپدیت پردازش‌شده)
# ---------------------------------------------------------------
def _load_state():
    if os.path.exists(config.BOT_STATE_FILE):
        with open(config.BOT_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_update_id": 0, "subscribers": []}


def _save_state(state):
    with open(config.BOT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _add_subscriber(state, chat_id, user):
    existing = next((s for s in state["subscribers"] if s["chat_id"] == chat_id), None)
    if existing:
        return False
    state["subscribers"].append({
        "chat_id": chat_id,
        "name": (user.get("first_name", "") + " " + user.get("last_name", "")).strip(),
        "username": user.get("username", ""),
        "joined": datetime.now(timezone.utc).isoformat(),
    })
    return True


# ---------------------------------------------------------------
# فراخوانی‌های تلگرام
# ---------------------------------------------------------------
def _get_updates(offset):
    resp = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 0}, timeout=20)
    resp.raise_for_status()
    return resp.json().get("result", [])


def _send_welcome(chat_id):
    keyboard = [[{"text": label, "callback_data": key}] for label, key in config.BOT_MENU_BUTTONS]
    text = (
        "👋 خوش اومدی!\n\n"
        "از این پس هر ساعت خلاصه‌ی کامل اخبار برات می‌فرستم.\n"
        "همین الان هم می‌تونی یکی از دسته‌ها رو انتخاب کنی تا آخرین خبرش رو فوری ببینی:"
    )
    requests.post(f"{API}/sendMessage", json={
        "chat_id": chat_id, "text": text,
        "reply_markup": {"inline_keyboard": keyboard},
    }, timeout=20)


def _answer_callback(callback_id):
    try:
        requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": callback_id}, timeout=10)
    except Exception:
        pass


def _send_message(chat_id, text):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True,
    }, timeout=20)


def _notify_admin(text):
    """به خودت (شناسه‌هایی که تو سیکرت TELEGRAM_CHAT_ID گذاشتی) خبر می‌ده - نه به اعضای عادی."""
    admin_targets = [t.strip() for t in (config.TELEGRAM_CHAT_ID or "").split(",") if t.strip()]
    for admin_id in admin_targets:
        try:
            _send_message(admin_id, text)
        except Exception as e:
            log.warning(f"خطا در اطلاع‌رسانی به ادمین {admin_id}: {e}")


# ---------------------------------------------------------------
# گرفتن «آخرین خبر» یک دسته به‌صورت زنده (سبک و سریع - بدون تحلیل AI)
# ---------------------------------------------------------------
def _latest_item_for_category(category_key):
    sources = config.RSS_SOURCES.get(category_key, [])
    best = None
    for src in sources[:4]:
        try:
            feed = feedparser.parse(src["url"])
            if not feed.entries:
                continue
            entry = feed.entries[0]
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if title and not best:
                best = f"📰 {category_key}\n\n{title}\n({src['name']})\n{link}"
                break
        except Exception as e:
            log.warning(f"خطا در گرفتن {src['name']}: {e}")
    return best or f"فعلاً خبر جدیدی تو دسته {category_key} پیدا نشد."


def _gold_currency_snapshot():
    import fetch_rates
    lines = ["🥇 قیمت لحظه‌ای ارز و طلا:\n"]
    try:
        usd_cad = fetch_rates.get_currency_series("FXUSDCAD")
        if usd_cad:
            lines.append(f"دلار آمریکا/کانادا: {usd_cad[-1][1]:.4f}")
    except Exception as e:
        log.warning(f"خطا در نرخ ارز: {e}")
    try:
        toman = fetch_rates.get_iran_usd_toman()
        if toman:
            lines.append(f"دلار بازار آزاد ایران: {toman:,.0f} تومان")
    except Exception as e:
        log.warning(f"خطا در نرخ تومان: {e}")
    try:
        gold = fetch_rates.get_gold_coin_prices()
        if gold.get("طلای ۱۸ عیار"):
            lines.append(f"طلای ۱۸ عیار: {gold['طلای ۱۸ عیار']['price']:,.0f} تومان")
    except Exception as e:
        log.warning(f"خطا در قیمت طلا: {e}")
    lines.append("\nبرای جزئیات کامل و نمودار، گزارش ساعتی رو چک کن.")
    return "\n".join(lines)


def _all_categories_snapshot():
    lines = ["📰 آخرین خبر هر دسته:\n"]
    for category_key in config.RSS_SOURCES.keys():
        sources = config.RSS_SOURCES.get(category_key, [])
        for src in sources[:2]:
            try:
                feed = feedparser.parse(src["url"])
                if feed.entries:
                    title = getattr(feed.entries[0], "title", "").strip()
                    if title:
                        lines.append(f"• {category_key}: {title}")
                        break
            except Exception:
                continue
    return "\n".join(lines)


def _handle_category_request(chat_id, key):
    if key == "gold_currency":
        text = _gold_currency_snapshot()
    elif key == "all":
        text = _all_categories_snapshot()
    elif key == "سیاسی":
        a = _latest_item_for_category("سیاسی داخلی")
        b = _latest_item_for_category("سیاسی خارجی")
        text = f"{a}\n\n---\n\n{b}"
    else:
        text = _latest_item_for_category(key)
    _send_message(chat_id, text)


# ---------------------------------------------------------------
# اجرای اصلی
# ---------------------------------------------------------------
def run():
    if not config.TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN تنظیم نشده - ربات نمی‌تونه اجرا بشه.")
        return False

    state = _load_state()
    offset = state.get("last_update_id", 0) + 1
    updates = _get_updates(offset)

    if not updates:
        log.info("آپدیت جدیدی نیست.")
        return False

    changed = False
    for update in updates:
        state["last_update_id"] = update["update_id"]

        message = update.get("message")
        if message and message.get("text", "").strip().startswith("/start"):
            chat_id = message["chat"]["id"]
            user = message.get("from", {})
            is_new = _add_subscriber(state, chat_id, user)
            _send_welcome(chat_id)
            log.info(f"عضو {'جدید' if is_new else 'قدیمی'}: {chat_id} ({user.get('first_name', '')})")
            if is_new:
                display_name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip() or "بدون‌نام"
                username_part = f"@{user['username']}" if user.get("username") else "بدون یوزرنیم"
                _notify_admin(f"🆕 عضو جدید به ربات پیوست:\n{display_name} ({username_part})\nشناسه: {chat_id}")
            changed = True
            continue

        callback = update.get("callback_query")
        if callback:
            chat_id = callback["message"]["chat"]["id"]
            key = callback.get("data", "")
            _answer_callback(callback["id"])
            log.info(f"درخواست دسته «{key}» از {chat_id}")
            try:
                _handle_category_request(chat_id, key)
            except Exception as e:
                log.error(f"خطا در پردازش درخواست دسته {key}: {e}")
                _send_message(chat_id, "متاسفانه الان نتونستم این خبر رو بگیرم، دوباره امتحان کن.")
            changed = True

    _save_state(state)
    log.info(f"تعداد کل اعضا: {len(state['subscribers'])}")
    return changed


if __name__ == "__main__":
    run()
