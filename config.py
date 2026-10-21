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
    # نکته‌ها (اکتبر ۲۰۲۶، به درخواست کاربر):
    # - BBC از بخش‌های سیاسی و جنگ حذف شد؛ منابع متنوع‌تر (فارسی خارج از کشور + بین‌المللی).
    # - تیترهای انگلیسی تو اپ خودکار به فارسی ترجمه می‌شن (cloudflare/news.js، build_app_data.py).
    # - سایت‌های داخل ایران (مهر، تسنیم، فارس، ایسنا، خبرآنلاین، ورزش۳ ...) به سرورهای خارج از ایران
    #   جواب نمی‌دن؛ ایرنا و دنیای اقتصاد مونده‌ن چون گاهی جواب می‌دن (اگه ندن، اپ منتظرشون نمی‌مونه).
    # - هر بخش از هر منبع حداکثر چند خبر نشون می‌ده تا یک منبع کل لیست رو پر نکنه.
    "اقتصادی": [
        {"name": "دنیای اقتصاد", "url": "https://donya-e-eqtesad.com/rss", "tag": "اقتصاد"},
        {"name": "خبرگزاری ایسنا - اقتصادی", "url": "https://www.isna.ir/rss/tp/13", "tag": "اقتصاد"},
        {"name": "Financial Times", "url": "https://www.ft.com/world?format=rss", "tag": "economy"},
        {"name": "BBC Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "tag": "economy"},
        {"name": "CoinDesk (کریپتو)", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "tag": "crypto"},
        {"name": "Cointelegraph (کریپتو)", "url": "https://cointelegraph.com/rss", "tag": "crypto"},
        {"name": "ForexLive (فارکس)", "url": "https://www.forexlive.com/feed/news", "tag": "forex"},
        {"name": "Investing.com - فارکس", "url": "https://www.investing.com/rss/news_1.rss", "tag": "forex - TO VERIFY"},
    ],
    "سیاسی داخلی": [
        {"name": "ایران اینترنشنال", "url": "https://www.iranintl.com/fa/feed", "tag": "سیاست ایران - دیدگاه خارج از کشور"},
        {"name": "رادیو فردا", "url": "https://www.radiofarda.com/api/", "tag": "سیاست ایران - دیدگاه خارج از کشور"},
        {"name": "دویچه‌وله فارسی - ایران", "url": "https://rss.dw.com/xml/rss-per-iran", "tag": "سیاست ایران - رسانه‌ی آلمانی"},
        {"name": "یورونیوز فارسی", "url": "https://parsi.euronews.com/rss", "tag": "سیاست ایران - رسانه‌ی اروپایی"},
        {"name": "ایرنا (رسمی داخل ایران)", "url": "https://www.irna.ir/rss", "tag": "سیاست ایران - دیدگاه رسمی داخل ایران"},
        _telegram_source(TELEGRAM_CHANNELS[0], "کانال تلگرام - سیاسی داخلی"),
        _telegram_source(TELEGRAM_CHANNELS[4], "کانال تلگرام - سیاسی داخلی"),
        _telegram_source(TELEGRAM_CHANNELS[7], "کانال تلگرام - سیاسی داخلی"),
    ],
    "سیاسی خارجی": [
        {"name": "الجزیره", "url": "https://www.aljazeera.com/xml/rss/all.xml", "tag": "world"},
        {"name": "گاردین", "url": "https://www.theguardian.com/world/rss", "tag": "world"},
        {"name": "نیویورک تایمز", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "tag": "world"},
        {"name": "رویترز (Google News)",
         "url": "https://news.google.com/rss/search?q=site:reuters.com+world+when:1d&hl=en-US&gl=US&ceid=US:en", "tag": "world"},
        {"name": "CBC کانادا", "url": "https://www.cbc.ca/webfeed/rss/rss-world", "tag": "world"},
        {"name": "دویچه‌وله فارسی", "url": "https://rss.dw.com/rdf/rss-per-all", "tag": "world - فارسی"},
        _telegram_source(TELEGRAM_CHANNELS[6], "کانال تلگرام - سیاسی خارجی"),
    ],
    "ورزشی": [
        # فید ورزشی BBC فارسی (persian/sport/rss.xml) دیگه وجود نداره و به فید اصلی BBC فارسی
        # ریدایرکت می‌شه. سایت‌های ورزشی داخل ایران (ورزش۳ ...) از خارج جواب نمی‌دن؛ فوتبال ایران
        # از Google News میاد.
        {"name": "فوتبال ایران (Google News)",
         "url": "https://news.google.com/rss/search?q=Persepolis+OR+Esteghlal+OR+%22Team+Melli%22+OR+Sepahan+OR+Tractor+FC+when:3d&hl=en-US&gl=US&ceid=US:en",
         "tag": "ورزش ایران"},
        {"name": "ESPN فوتبال", "url": "https://www.espn.com/espn/rss/soccer/news", "tag": "sport"},
        {"name": "اسکای اسپورت", "url": "https://www.skysports.com/rss/12040", "tag": "sport"},
        {"name": "گاردین فوتبال", "url": "https://www.theguardian.com/football/rss", "tag": "sport"},
        {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "tag": "sport"},
    ],
    "جنگ ایران": [
        {"name": "ایران اینترنشنال", "url": "https://www.iranintl.com/fa/feed", "tag": "جنگ - دیدگاه خارج از کشور"},
        {"name": "رادیو فردا", "url": "https://www.radiofarda.com/api/", "tag": "جنگ - دیدگاه خارج از کشور"},
        {"name": "رویترز - ایران (Google News)",
         "url": "https://news.google.com/rss/search?q=Iran+war+OR+Israel+Iran+when:1d&hl=en-US&gl=US&ceid=US:en", "tag": "iran war"},
        {"name": "الجزیره", "url": "https://www.aljazeera.com/xml/rss/all.xml", "tag": "middle east"},
        {"name": "فرانس ۲۴ - خاورمیانه", "url": "https://www.france24.com/en/middle-east/rss", "tag": "middle east"},
        {"name": "المانیتور", "url": "https://www.al-monitor.com/rss", "tag": "middle east"},
        {"name": "یورونیوز فارسی", "url": "https://parsi.euronews.com/rss", "tag": "جنگ - رسانه‌ی اروپایی"},
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
