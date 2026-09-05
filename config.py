# -*- coding: utf-8 -*-
"""
تنظیمات پروژه Persian News Digest
منابع خبری رو اینجا اضافه/حذف/تغییر بده.
نکته مهم: بعضی از این RSS ها رو من نتونستم زنده تست کنم (چون این محیط به اینترنت وصل نیست).
اولین باری که main.py رو اجرا می‌کنی، لاگ می‌گیره کدوم منبع جواب نداده - اونا رو حذف یا جایگزین کن.

نکته درباره ایران اینترنشنال و VOA فارسی:
این دو منبع عمدا به چند دسته اضافه شدن (سیاسی داخلی/خارجی/جنگ) چون دیدگاه "خارج از کشور"
میدن و مکمل BBC/ایرنا هستن - در تحلیل (analyze.py) از Claude خواسته شده این تفاوت دیدگاه رو
توی بخش "مقایسه منابع" مشخص کنه. آدرس iranintl.com/fa/feed با علامت "TO VERIFY" مشخصه چون
در این محیط قابل تست زنده نبود. آدرس VOA فارسی (ir.voanews.com/api/) تایید شده و زنده است
(آدرس قبلی ir.voanews.com/rssfeeds یک صفحه لیست‌فید بود نه یک فید واقعی، برای همین هیچ‌وقت
خبر نمی‌آورد - اصلاحش کردیم).
همچنین توجه: سرویس VOA فارسی مارس ۲۰۲۵ به‌خاطر دستور اجرایی دولت آمریکا موقتا تعطیل شد
و ژوئن ۲۰۲۵ دوباره فعال شد - اگه فید کار نکرد یعنی احتمالا دوباره وضعیتش تغییر کرده،
با یک جستجوی سریع بررسی کن.
"""

import os

# ---------------------------------------------------------------
# ۰) کانال‌های خبری تلگرام (از طریق پل RSSHub - t.me/channel_name)
# ---------------------------------------------------------------
# نکته مهم: تلگرام خودش RSS نداره، از RSSHub استفاده می‌کنیم. یوزرنیم‌های واقعی
# (تایید شده - از لینک‌های t.me خود کاربر گرفته و زنده بررسی شدن).
TELEGRAM_CHANNELS = [
    {"name": "وحید هدلاین", "username": "VahidHeadline"},
    {"name": "چرک‌نویس مدیا (CMO)", "username": "Rfrens"},
    {"name": "هدف آزادی", "username": "hadafazadi2022"},
    {"name": "IndyPersian", "username": "Indypersian"},
    {"name": "شب‌نامه", "username": "Rppress0"},
    {"name": "مملکته", "username": "mamlekate"},
    {"name": "وحید آنلاین", "username": "VahidOnline"},
    {"name": "Iranwire", "username": "Farsi_Iranwire"},
]
# نکته مهم (کشف‌شده و رفع‌شده): سرور اصلی rsshub.app اخیرا پشت محافظت ضدـربات
# Cloudflare قرار گرفته و به هر درخواست خودکار/سرور به سرور (مثل GitHub Actions)
# فقط یک صفحه "Just a moment..." برمی‌گردونه، نه فید RSS واقعی - برای همین همه‌ی
# ۸ کانال تلگرام همیشه با خطای "منبع جواب نداد" شکست می‌خوردن (ربطی به یوزرنیم‌ها نداشت).
# rsshub.rss3.workers.dev یک آینه‌ی عمومی و رایگان RSSHub روی Cloudflare Workers‌ه که
# پشت اون محافظت ضدربات نیست - زنده تست شد و برای چند کانال جواب درست و کامل داد.
RSSHUB_BASE_URL = "https://rsshub.rss3.workers.dev"


def _telegram_source(channel, tag):
    return {
        "name": f"تلگرام: {channel['name']}",
        "url": f"{RSSHUB_BASE_URL}/telegram/channel/{channel['username']}",
        "tag": tag,
    }


# ---------------------------------------------------------------
# ۱) منابع RSS به تفکیک دسته (گروه‌بندی خواسته‌شده توسط کاربر)
# ---------------------------------------------------------------
# ترتیب دسته‌ها عمدا اینجا مشخصه (نه فقط اسم کلید): دسته‌های «اخبار جدی/روز» (اقتصاد،
# سیاست داخلی/خارجی، جنگ) همه کنار هم میان تا خواننده گیج نشه که چرا یهو از سیاست پرید
# به ورزش و برگشت به جنگ؛ بعدش دسته‌های سبک‌تر (ورزش، مهاجرت، تک/گیم) میان. همینترتیب
# هم تو گزارش HTML و هم تو خلاصه تلگرام استفاده می‌شه (main.py از همین دیکشنری می‌خونه).
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
        {"name": "صدای آمریکا فارسی - VOA (دیدگاه خارج از کشور)", "url": "https://ir.voanews.com/api/",
         "tag": "سیاست ایران - دیدگاه دولت آمریکا/خارج از کشور"},
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
    "جنگ ایران": [
        {"name": "BBC Persian", "url": "https://feeds.bbci.co.uk/persian/rss.xml", "tag": "جنگ"},
        {"name": "Al Jazeera - Middle East", "url": "https://www.aljazeera.com/xml/rss/all.xml", "tag": "middle east"},
        {"name": "Reuters World (via Google News)",
         "url": "https://news.google.com/rss/search?q=Iran+war&hl=en-US&gl=US&ceid=US:en", "tag": "iran war"},
        {"name": "ایران اینترنشنال (دیدگاه خارج از کشور)", "url": "https://www.iranintl.com/fa/feed",
         "tag": "جنگ - دیدگاه خارج از کشور - TO VERIFY"},
        {"name": "صدای آمریکا فارسی (دیدگاه دولت آمریکا)", "url": "https://ir.voanews.com/api/",
         "tag": "جنگ - دیدگاه آمریکا"},
        _telegram_source(TELEGRAM_CHANNELS[1], "کانال تلگرام - جنگ"),
        _telegram_source(TELEGRAM_CHANNELS[2], "کانال تلگرام - جنگ"),
        _telegram_source(TELEGRAM_CHANNELS[3], "کانال تلگرام - جنگ"),
    ],
    "ورزشی": [
        {"name": "BBC Persian - ورزشی", "url": "https://feeds.bbci.co.uk/persian/sport/rss.xml", "tag": "ورزش"},
        {"name": "BBC Sport (EN)", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "tag": "sport"},
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
# نرخ رسمی/بین‌بانکی کانادا (Bank of Canada - رسمی و پایدار)
# ۱۰ ارز برتر - در برابر دلار کانادا. لیست کامل سری‌ها:
# https://www.bankofcanada.ca/valet/lists/series/json (دنبال FX... بگرد)
# ۹ تا از این ۱۰ ارز سری مستقیم بانک مرکزی کانادا دارن (تایید شده - زنده بررسی شد).
TRACKED_CURRENCIES = {
    "USD/CAD": "FXUSDCAD",
    "EUR/CAD": "FXEURCAD",
    "GBP/CAD": "FXGBPCAD",
    "JPY/CAD": "FXJPYCAD",
    "CNY/CAD": "FXCNYCAD",
    "TRY/CAD": "FXTRYCAD",
    "AUD/CAD": "FXAUDCAD",
    "CHF/CAD": "FXCHFCAD",
    "INR/CAD": "FXINRCAD",
}
# درهم امارات (AED) تو لیست سری‌های بانک مرکزی کانادا نیست (بررسی شد - وجود نداره)، چون
# درهم از سال ۱۹۹۷ نرخش به دلار آمریکا کاملا ثابته (Peg رسمی، هیچ‌وقت تغییر نمی‌کنه).
# برای همین AED/CAD مستقیم واکشی نمی‌شه، بلکه از روی سری USD/CAD که همینجا داریم محاسبه می‌شه:
# AED/CAD = (USD/CAD) ÷ AED_PER_USD
AED_PER_USD = 3.6725
COMPUTED_CURRENCIES = {
    "AED/CAD": {"base": "USD/CAD", "divide_by": AED_PER_USD},
}
# برای نمودار سالانه به چند سال تاریخچه نیاز داریم - این تعداد سال رو از امروز به عقب می‌گیره
BOC_HISTORY_YEARS = 6
BOC_OBSERVATIONS_URL_TMPL = "https://www.bankofcanada.ca/valet/observations/{series}/json?start_date={start_date}"

# نرخ دلار بازار آزاد ایران (غیررسمی - ممکنه تغییر کنه، نیاز به بررسی دوره‌ای)
IRAN_USD_TOMAN_URL = "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl"

# ---------------------------------------------------------------
# ۲.۰) طلا و سکه ایران (به سبک tgju.org - قیمت زنده + درصد تغییر)
# ---------------------------------------------------------------
# این‌ها اسلاگ‌های رسمی شاخص‌های tgju.org هستن (تایید شده). طلای دست دوم شاخص رسمی نداره،
# پس با یک تخمین معقول (۹۹٪ نرخ ۱۸ عیار، طبق افت معمول در بازار دست دوم) محاسبه می‌شه و
# در گزارش با برچسب «تقریبی» مشخصه.
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
# لینک مستقیم به نمودار تاریخی خود tgju.org - چون این شاخص‌ها API تاریخچه رایگان ندارن،
# دکمه «نمودار» کاربر رو مستقیم به نمودار واقعی و زنده خود tgju.org می‌بره (به‌جای نمودار جعلی).
TGJU_CHART_URL_TMPL = "https://www.tgju.org/chart/{slug}"

# ---------------------------------------------------------------
# ۲.۳) هوا و ساعت (تورنتو + مشهد) - Open-Meteo کاملا رایگان و بدون کلید
# ---------------------------------------------------------------
USER_NAME = "امید"
WEATHER_CITIES = [
    {"name": "تورنتو", "lat": 43.6532, "lon": -79.3832, "tz": "America/Toronto"},
    {"name": "مشهد", "lat": 36.2605, "lon": 59.6168, "tz": "Asia/Tehran"},
]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ---------------------------------------------------------------
# ۲.۲) برترین شرکت‌ها (روزانه/هفتگی) - پیشنهاد: ترکیب آمریکا + کانادا
# ---------------------------------------------------------------
# ۵ غول تک آمریکا + ۵ شرکت بزرگ بورس کانادا (TSX) - چون این ترکیبی‌ه که هم به تو (مقیم کانادا)
# مرتبطه هم شرکت‌های شناخته‌شده جهانی رو پوشش می‌ده. هر وقت خواستی می‌تونی شرکت‌های
# جهانی دیگه (مثل TSM, ASML) رو هم اضافه کنی.
# نکته: منبع قبلی (Stooq) کاملا از کار افتاده بود (همه‌ی این ۱۰ نماد ۴۰۴ برمی‌گردوندن).
# جایگزین شد با API غیررسمی و رایگان Chart یاهو فایننس (نیاز به کلید نداره، زنده تست شد).
# فرمت نماد یاهو: شرکت‌های آمریکایی بدون پسوند (AAPL)، شرکت‌های بورس تورنتو با پسوند .TO (RY.TO).
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
# ۵ روز اخیر رو یکجا می‌گیریم (هم برای تغییر روزانه هم هفتگی کافیه - یک درخواست به‌جای دوتا).
YAHOO_CHART_URL_TMPL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"

# ---------------------------------------------------------------
# ۲.۱) طلا و کریپتوکارنسی
# ---------------------------------------------------------------
# GoldAPI.io - نیاز به یک API Key رایگان داره (ثبت‌نام رایگان تو goldapi.io، پلن رایگان کافیه)
GOLD_API_KEY = os.environ.get("GOLD_API_KEY", "")
GOLD_API_URL = "https://www.goldapi.io/api/XAU/USD"

# CoinGecko - کاملا رایگان و بدون نیاز به API Key (برای درخواست‌های زیاد بهتره از API Key رایگانشون استفاده کنی)
COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
# کوین‌هایی که پیگیری می‌شن - ۱۵ ارز مهم (شناسه دقیق CoinGecko لازمه، هرچقدر خواستی عوض کن)
TRACKED_COINS = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana", "ripple", "usd-coin",
    "dogecoin", "cardano", "tron", "avalanche-2", "chainlink", "polkadot", "litecoin", "shiba-inu",
]

# ---------------------------------------------------------------
# ۳) تنظیمات مدل هوش مصنوعی (LLM)
# ---------------------------------------------------------------
# MODEL_PROVIDER: "gemini" (رایگان و پیشنهادی) یا "anthropic" (پولی، کیفیت بالاتر)
# Gemini از طریق Google AI Studio کاملا رایگانه (بدون کارت بانکی، بدون انقضا):
# https://aistudio.google.com/apikey
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "gemini")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"  # طبق پیام خود گوگل: حساب‌های جدید فقط این نسخه به بعد رو می‌بینن

CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------
# ۴) تنظیمات تلگرام (برای ارسال خودکار گزارش)
# ---------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------
# ۵) تنظیمات عمومی
# ---------------------------------------------------------------
NOTIFY_LOOKBACK_HOURS = 1     # هر ساعت چک می‌کنه چه خبر واقعا جدیدیه (برای تصمیم "پیام بفرستم یا نه")
DISPLAY_LOOKBACK_HOURS = 96   # ولی خود گزارش تا ۴ روز اخیر رو نشون می‌ده تا هر بخش پر و کامل باشه
HEADLINES_PER_CATEGORY = 10   # دقیقا همونی که خواستی: ۱۰ عنوان مهم در هر بخش خبری
MAX_ITEMS_PER_SOURCE = 15     # حداکثر خبر خام از هر منبع (قبل از انتخاب ۱۰ تای برتر)
DB_PATH = "seen_news.db"      # دیتابیس جلوگیری از تکرار خبر
OUTPUT_DIR = "output"

# چند خبر مهم واسه خلاصه هفتگی/ماهانه از هر دسته نگه داریم (از دیتابیس تاریخچه می‌خونه)
WEEKLY_ROLLUP_WEEKDAY = 4    # 0=دوشنبه ... 4=جمعه (طبق استاندارد پایتون: 0=Monday)
MONTHLY_ROLLUP_DAY = 1       # روز اول هر ماه میلادی
