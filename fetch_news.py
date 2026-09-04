# -*- coding: utf-8 -*-
"""
گرفتن خبر از منابع RSS.

منطق دو لایه‌ست:
1) "نمایش": گزارش همیشه تا ۱۰ عنوان مهم از هر دسته رو نشون می‌ده (حتی اگه قبلا دیده شده باشن)
   تا هر بخش پر و کامل به‌نظر برسه، نه خالی.
2) "اطلاع‌رسانی": فقط وقتی حداقل یک خبر واقعا تازه (در ۱ ساعت اخیر اولین‌بار دیده شده) باشه،
   پیام تلگرام/آپدیت Netlify واقعا انجام می‌شه - که در main.py تصمیم‌گیری می‌شه.
هر آیتم یک فلگ is_new داره که تو گزارش با یک نشان «جدید» مشخص می‌شه.
"""

import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import feedparser

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def _init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_news (
            id TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            category TEXT,
            first_seen_at TEXT
        )
    """)
    conn.commit()
    return conn


def _news_id(link: str, title: str) -> str:
    return hashlib.sha256((link or title).encode("utf-8")).hexdigest()


def _get_or_mark_first_seen(conn, news_id, title, source, category):
    """اگه قبلا دیده شده، تاریخ اولین بار دیدن رو برمی‌گردونه. اگه نه، الان رو ثبت می‌کنه و الان رو برمی‌گردونه."""
    cur = conn.execute("SELECT first_seen_at FROM seen_news WHERE id = ?", (news_id,))
    row = cur.fetchone()
    if row:
        return row[0]
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO seen_news (id, title, source, category, first_seen_at) VALUES (?, ?, ?, ?, ?)",
        (news_id, title, source, category, now_iso),
    )
    conn.commit()
    return now_iso


def _parse_entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return None


def fetch_all(db_path: str = None):
    """
    خروجی: dict {category: [ {title, link, summary, source, published, is_new} ]}
    هر دسته حداکثر HEADLINES_PER_CATEGORY آیتم داره (جدیدترین‌ها، از همه منابع اون دسته با هم).
    """
    db_path = db_path or config.DB_PATH
    conn = _init_db(db_path)
    display_cutoff = datetime.now(timezone.utc) - timedelta(hours=config.DISPLAY_LOOKBACK_HOURS)
    notify_cutoff = datetime.now(timezone.utc) - timedelta(hours=config.NOTIFY_LOOKBACK_HOURS)

    results = {cat: [] for cat in config.RSS_SOURCES}

    for category, sources in config.RSS_SOURCES.items():
        category_items = []
        for src in sources:
            try:
                feed = feedparser.parse(src["url"])
                if feed.bozo and not feed.entries:
                    log.warning(f"منبع جواب نداد یا خراب است: {src['name']} ({src['url']})")
                    continue

                for entry in feed.entries[: config.MAX_ITEMS_PER_SOURCE]:
                    title = getattr(entry, "title", "").strip()
                    link = getattr(entry, "link", "").strip()
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    if not title:
                        continue

                    pub_time = _parse_entry_time(entry)
                    if pub_time and pub_time < display_cutoff:
                        continue  # قدیمی‌تر از بازه نمایش

                    nid = _news_id(link, title)
                    first_seen_str = _get_or_mark_first_seen(conn, nid, title, src["name"], category)
                    first_seen_dt = datetime.fromisoformat(first_seen_str)
                    is_new = first_seen_dt >= notify_cutoff

                    category_items.append({
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "source": src["name"],
                        "published": pub_time.isoformat() if pub_time else first_seen_str,
                        "published_dt": pub_time or first_seen_dt,
                        "is_new": is_new,
                    })

            except Exception as e:
                log.error(f"خطا در دریافت {src['name']}: {e}")

        # جدیدترین‌ها اول، بعد فقط ۱۰ تای برتر رو نگه دار
        category_items.sort(key=lambda x: x["published_dt"], reverse=True)
        top_items = category_items[: config.HEADLINES_PER_CATEGORY]
        for it in top_items:
            it.pop("published_dt", None)  # فقط برای مرتب‌سازی لازم بود
        results[category] = top_items

        new_count = sum(1 for it in top_items if it["is_new"])
        log.info(f"[{category}] {len(top_items)} خبر نمایش داده می‌شه، {new_count} تاش واقعا جدیده")

    conn.close()
    return results


def get_history(hours: int, db_path: str = None):
    """برای خلاصه‌های دوره‌ای (هفتگی/ماهانه) - عنوان/منبع/دسته خبرهایی که در N ساعت اخیر اولین‌بار دیده شدن."""
    db_path = db_path or config.DB_PATH
    conn = sqlite3.connect(db_path)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    cur = conn.execute(
        "SELECT title, source, category FROM seen_news WHERE first_seen_at >= ? ORDER BY first_seen_at DESC",
        (cutoff,),
    )
    rows = [{"title": r[0], "source": r[1], "category": r[2]} for r in cur.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    data = fetch_all()
    for cat, items in data.items():
        print(f"\n=== {cat} ({len(items)} خبر) ===")
        for it in items[:3]:
            print(" -", it["title"], "|", it["source"], "| جدید:" , it["is_new"])
