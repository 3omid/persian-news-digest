# -*- coding: utf-8 -*-
"""
تنظیمات پروژه Persian News Digest
منابع خبری رو اینجا اضافه/حذف/تغییر بده.
نکته مهم: بعضی از این RSS ها رو من نتونستم زنده تست کنم (چون این محیط به اینترنت وصل نیست).
اولین باری که main.py رو اجرا می‌کنی، لاگ می‌گیره کدوم منبع جواب نداده - اونا رو حذف یا جایگزین کن.

نکته درباره ایران اینترنشنال و VOA فارسی:
این دو منبع عمدا به چند دسته اضافه شدن (سیاسی داخلی/خارجی/جنگ) چون دیدگاه "خارج از کشور"
میدن و مکمل BBC/ایرنا هستن - در تحلیل (analyze.py) از Claude خواسته شده این تفاوت دیدگاه رو
توی بخش "مقایسه منابع" مشخص کنه. آدرس‌های iranintl.com/fa/feed و ir.voanews.com/rssfeeds
با علامت "TO VERIFY" مشخص شدن چون در این محیط قابل تست زنده نبودن.
همچنین توجه: سرویس VOA فارسی مارس ۲۰۲۵ به‌خاطر دستور اجرایی دولت آمریکا موقتا تعطیل شد
و ژوئن ۲۰۲۵ دوباره فعال شد - اگه فید کار نکرد یعنی احتمالا دوباره وضعیتش تغییر کرده،
با یک جستجوی سریع بررسی کن.
"""

import os

# ---------------------------------------------------------------
# ۰) کانال‌های خبری تلگرام (از طریق پل RSSHub - t.me/channel_name)
# ---------------------------------------------------------------
TELEGRAM_CHANNELS = [
    {"name": "وحید هدلاین", "username": "PLACEHOLDER_vahid_headline"},
    {"name": "چرک‌نویس مدیا (CMO)", "username": "PLACEHOLDER_cherlinews"},
    {"name": "هدف آزادی", "username": "PLACEHOLDER_hadaf_azadi"},
    {"name": "IndyPersian", "username": "PLACEHOLDER_indypersian"},
    {"name": "شب‌نامه", "username": "PLACEHOLDER_shabnameh"},
    {"name": "مملکته", "username": "PLACEHOLDER_mamlekate"},
    {"name": "وحید آنلاین", "username": "PLACEHOLDER_vahid_online"},
    {"name": "Iranwire", "username": "PLACEHOLDER_iranwire"},
]


def _telegram_source(channel, tag):
    return {
        "name": f"تلگرام: {channel['name']}",
        "url": f"https://rsshub.app/telegram/channel/{channel['username']}",
        "tag": tag,
    }


# ---------------------------------------------------------------
# ۱) منابع RSS به تفکیک دسته
# ---------------------------------------------------------------
RSS_SOURCES = {
    "اقتصادی": [
        {"name": "BBC Persian - اقتصادی", "url": "https://feeds.bbci.co.uk/persian/rss.xml", "tag": "اقتصاد"},
        {"name": "BBC Business (EN)", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "tag": "economy"},
        {"name": "دنیای اقتصاد", "url": "https://donya-e-eqtesad.com/rss", "tag": "اقتصاد"},
        {"name": "خبرگزاری ایسنا - اقتصادی", "url": "https://www.isna.ir/rss/tp/13", "tag": "اقتصاد"},
        {"name": "CoinDesk (کریپتو)", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "tag": "crypto"},
        {"name": "Cointelegraph (کریپتو)", "url": "https://cointelegraph.com/rss", "tag": "crypto"},
        {"name": "ForexLive (فارکس)", "url": "https://www.forexlive.com/feed/news", "tag": "forex"},
        {"name": "Investing.com - فارکس", "url": "https://www.investing.com/rss/news_1.rss", "tag": "forex - TO VERIFY"},
    ],
    "سیاسی داخلی": [
        {"name": "BBC Persian", "url": "https://feeds.bbci.co.uk/persian/rss.xml", "tag": "سیاست ایران - دیدگاه بی‌طرف"},
        {"name": "ایرنا (رسمی داخل ایران)", "url": "https://www.irna.ir/rss", "tag": "سیاست ایران - دیدگاه رسمی داخل ایران"},
        {"name": "ایران اینترنشنال (دیدگاه خارج از کشور)", "url": "https://www.iranintl.com/fa/feed",
         "tag": "سیاست ایران - دیدگاه منتقد/خارج از کشور - TO VERIFY"},
        {"name": "صدای آمریکا فارسی - VOA (دیدگاه خارج از کشور)", "url": "https://ir.voanews.com/rssfeeds",
         "tag": "سیاست ایران - دیدگاه دولت آمریکا/خارج از کشور - TO VERIFY (این صفحه لیست فیدهاست، آدرس دقیق XML رو از داخلش کپی کن)"},
        _telegram_source(TELEGRAM_CHANNELS[0], "کانال تلگرام - سیاسی داخلی"),
        _telegram_source(TELEGRAM_CHANNELS[4], "کانال تلگرام - سیاسی داخلی"),
        _telegram_source(TELEGRAM_CHANNELS[7], "کانال تلگرام - سیاسی داخلی"),
    ],
    "سیاسی خارجی": [
        {"name": "BBC World (EN)", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "tag": "world"},
        {"name": "Al Jazeera English", "url": "https://www.aljazeera.com/xml/rss/all.xml", "tag": "world"},
        {"name": "ایران اینترنشنال (پوشش سیاست خارجی مرتبط با ایران)", "url": "https://www.iranintl.com/fa/feed",
         "tag": "foreign policy re: Iran - TO VERIFY"},
        _telegram_source(TELEGRAM_CHANNELS[6], "کانال تلگرام - سیاسی خارجی"),
    ],
    "ورزشی": [
        {"name": "BBC Persian - ورزشی", "url": "https://feeds.bbci.co.uk/persian/sport/rss.xml", "tag": "ورزش"},
        {"name": "BBC Sport (EN)", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "tag": "sport"},
    ],
    "جنگ ایران": [
        {"name": "BBC Persian", "url": "https://feeds.bbci.co.uk/persian/rss.xml", "tag": "جنگ"},
        {"name": "Al Jazeera - Middle East", "url": "https://www.aljazeera.com/xml/rss/all.xml", "tag": "middle east"},
        {"name": "Reuters World (via Google News)",
         "url": "https://news.google.com/rss/search?q=Iran+war&hl=en-US&gl=US&ceid=US:en", "tag": "iran war"},
        {"name": "ایران اینترنشنال (دیدگاه خارج از کشور)", "url": "https://www.iranintl.com/fa/feed",
         "tag": "جنگ - دیدگاه خارج از کشور - TO VERIFY"},
        {"name": "صدای آمریکا فارسی (دیدگاه دولت آمریکا)", "url": "https://ir.voanews.com/rssfeeds",
         "tag": "جنگ - دیدگاه آمریکا - TO VERIFY"},
        _telegram_source(TELEGRAM_CHANNELS[1], "کانال تلگرام - جنگ"),
        _telegram_source(TELEGRAM_CHANNELS[2], "کانال تلگرام - جنگ"),
        _telegram_source(TELEGRAM_CHANNELS[3], "کانال تلگرام - جنگ"),
    ],
    "مهاجرت کانادا": [
        {"name": "CIC News", "url": "https://www.cicnews.com/feed", "tag": "immigration"},
        {"name": "IRCC - اخبار رسمی دولت کانادا", "url": "https://www.canada.ca/en/immigration-refugees-citizenship/news.atom.xml",
         "tag": "immigration official - TO VERIFY"},
        {"name": "Immigration.ca Blog", "url": "https://www.immigration.ca/feed/", "tag": "immigration - TO VERIFY"},
        {"name": "Moving2Canada", "url": "https://moving2canada.com/feed/", "tag": "immigration - TO VERIFY"},
    ],
    "فناوری و IT": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "tag": "tech"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "tag": "tech"},
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "tag": "tech"},
        {"name": "Wired", "url": "https://www.wired.com/feed/rss", "tag": "tech"},
        {"name": "KrebsOnSecurity (سایبرسکیوریتی)", "url": "https://krebsonsecurity.com/feed/", "tag": "cybersecurity"},
        {"name": "BleepingComputer (سایبرسکیوریتی)", "url": "https://www.bleepingcomputer.com/feed/", "tag": "cybersecurity"},
        {"name": "The Hacker News (سایبرسکیوریتی)", "url": "https://feeds.feedburner.com/TheHackersNews", "tag": "cybersecurity"},
    ],
    "بازی و گجت": [
        {"name": "IGN", "url": "https://feeds.ign.com/ign/games-all", "tag": "gaming"},
        {"name": "Engadget (گجت)", "url": "https://www.engadget.com/rss.xml", "tag": "gadgets"},
        {"name": "The Verge - Gaming", "url": "https://www.theverge.com/games/rss/index.xml", "tag": "gaming - TO VERIFY"},
    ],
}

# ---------------------------------------------------------------
# ۲) منابع نرخ ارز
# ---------------------------------------------------------------
TRACKED_CURRENCIES = {
    "USD/CAD": "FXUSDCAD",
    "EUR/CAD": "FXEURCAD",
    "GBP/CAD": "FXGBPCAD",
    "JPY/CAD": "FXJPYCAD",
    "CNY/CAD": "FXCNYCAD",
    "TRY/CAD": "FXTRYCAD",
}
BOC_HISTORY_YEARS = 6
BOC_OBSERVATIONS_URL_TMPL = "https://www.bankofcanada.ca/valet/observations/{series}/json?start_date={start_date}"

IRAN_USD_TOMAN_URL = "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl"

# ---------------------------------------------------------------
# ۲.۰) طلا و سکه ایران
# ---------------------------------------------------------------
GOLD_COIN_INDICATORS = {
    "طلای ۱۸ عیار": "geram18",
    "طلای ۲۴ عیار": "geram24",
    "سکه امامی": "sekee",
    "سکه بهار آزادی": "sekeb",
    "نیم سکه": "nim",
    "ربع سکه": "rob",
    "سکه گرمی": "gerami",
}
TGJU_INDICATOR_URL_TMPL = "https://api.tgju.org/v1/market/indicator/summary-table-data/{slug}"
TGJU_CHART_URL_TMPL = "https://www.tgju.org/chart/{slug}"

# ---------------------------------------------------------------
# ۲.۳) هوا و ساعت (تورنتو + مشهد)
# ---------------------------------------------------------------
USER_NAME = "امید"
WEATHER_CITIES = [
    {"name": "تورنتو", "lat": 43.6532, "lon": -79.3832, "tz": "America/Toronto"},
    {"name": "مشهد", "lat": 36.2605, "lon": 59.6168, "tz": "Asia/Tehran"},
]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ---------------------------------------------------------------
# ۲.۲) برترین شرکت‌ها (روزانه/هفتگی) - از Yahoo Finance
# ---------------------------------------------------------------
WATCHLIST_STOCKS = [
    {"symbol": "AAPL", "name": "Apple"},
    {"symbol": "MSFT", "name": "Microsoft"},
    {"symbol": "NVDA", "name": "Nvidia"},
    {"symbol": "AMZN", "name": "Amazon"},
    {"symbol": "GOOGL", "name": "Google"},
    {"symbol": "RY.TO", "name": "Royal Bank of Canada"},
    {"symbol": "SHOP.TO", "name": "Shopify"},
    {"symbol": "CNQ.TO", "name": "Canadian Natural Resources"},
    {"symbol": "ENB.TO", "name": "Enbridge"},
    {"symbol": "TD.TO", "name": "TD Bank"},
]
YAHOO_CHART_URL_TMPL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=8d"

# ---------------------------------------------------------------
# ۲.۱) طلا و کریپتوکارنسی
# ---------------------------------------------------------------
GOLD_API_KEY = os.environ.get("GOLD_API_KEY", "")
GOLD_API_URL = "https://www.goldapi.io/api/XAU/USD"

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
TRACKED_COINS = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana", "ripple", "usd-coin",
    "dogecoin", "cardano", "tron", "avalanche-2", "chainlink", "polkadot", "litecoin", "shiba-inu",
]

# ---------------------------------------------------------------
# ۳) تنظیمات مدل هوش مصنوعی (LLM)
# ---------------------------------------------------------------
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "gemini")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"

CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------
# ۴) تنظیمات تلگرام
# ---------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

BOT_STATE_FILE = "bot_state.json"

BOT_MENU_BUTTONS = [
    ("💰 اخبار اقتصادی", "اقتصادی"),
    ("🥇 طلا و ارز", "gold_currency"),
    ("⚽ اخبار ورزشی", "ورزشی"),
    ("🏛️ اخبار سیاسی", "سیاسی"),
    ("💻 اخبار فناوری", "فناوری و IT"),
    ("⚠️ اخبار جنگ", "جنگ ایران"),
    ("📰 همه اخبار", "all"),
]

# ---------------------------------------------------------------
# ۵) تنظیمات عمومی
# ---------------------------------------------------------------
NOTIFY_LOOKBACK_HOURS = 1
DISPLAY_LOOKBACK_HOURS = 96
HEADLINES_PER_CATEGORY = 10
MAX_ITEMS_PER_SOURCE = 15
DB_PATH = "seen_news.db"
OUTPUT_DIR = "output"

WEEKLY_ROLLUP_WEEKDAY = 4
MONTHLY_ROLLUP_DAY = 1
