# -*- coding: utf-8 -*-
"""آب‌وهوا و ساعت محلی تورنتو و مشهد - Open-Meteo (کاملا رایگان، بدون کلید)."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import config

log = logging.getLogger(__name__)

# کد وضعیت آب‌وهوای Open-Meteo -> ایموجی (نسخه ساده‌شده)
WEATHER_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


def get_city_weather(city):
    try:
        resp = requests.get(config.OPEN_METEO_URL, params={
            "latitude": city["lat"],
            "longitude": city["lon"],
            "current_weather": "true",
            "temperature_unit": "celsius",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("current_weather", {})
        temp = data.get("temperature")
        code = data.get("weathercode", 0)
        icon = WEATHER_ICONS.get(code, "🌡️")
        local_time = datetime.now(ZoneInfo(city["tz"])).strftime("%H:%M")
        return {"name": city["name"], "temp": temp, "icon": icon, "time": local_time}
    except Exception as e:
        log.error(f"خطا در دریافت آب‌وهوای {city['name']}: {e}")
        # حتی اگه آب‌وهوا نگرفتیم، حداقل ساعت محلی رو نشون بده
        try:
            local_time = datetime.now(ZoneInfo(city["tz"])).strftime("%H:%M")
        except Exception:
            local_time = "--:--"
        return {"name": city["name"], "temp": None, "icon": "🌡️", "time": local_time}


def get_all_weather():
    return [get_city_weather(c) for c in config.WEATHER_CITIES]


if __name__ == "__main__":
    for w in get_all_weather():
        print(w)
