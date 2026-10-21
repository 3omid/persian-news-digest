# -*- coding: utf-8 -*-
"""
منابع خبری و دکمه‌های config.py رو برای سرور Cloudflare (cloudflare/app_config.js) می‌نویسه،
تا منابع فقط یک جا (config.py) تعریف بشن. بعد از هر تغییر منابع یا دکمه‌ها تو config.py:

    python export_app_config.py

و فایل cloudflare/app_config.js رو هم commit کن.
"""

import json

import config

OUT = "cloudflare/app_config.js"


def main():
    sources = {
        cat: [{"name": s["name"], "url": s["url"]} for s in srcs if "PLACEHOLDER" not in s["url"]]
        for cat, srcs in config.RSS_SOURCES.items()
    }
    data = {
        "menu": [{"label": label, "key": key} for label, key in config.BOT_MENU_BUTTONS],
        "sources": sources,
        "goldIndicators": [{"label": t, "slug": s} for t, s in config.GOLD_COIN_INDICATORS.items()],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// ساخته‌شده با export_app_config.py از روی config.py - دستی ویرایش نکن.\n")
        f.write("export default " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(f"نوشته شد: {OUT}")


if __name__ == "__main__":
    main()
