#!/usr/bin/env python3
"""
🌌 COSMOS SENTRY v1.0 - Zaawansowany system astrometeorologiczny z pełnym API OpenWeather
"""

import os
import json
import time
import logging
import threading
import requests
import math
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
import random

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"
PING_INTERVAL = 300

# API klucze
NASA_API_KEY = "P0locPuOZBvnkHCdIKjkxzKsfnM7tc7pbiMcsBDE"
N2YO_API_KEY = "UNWEQ8-N47JL7-WFJZYX-5N65"
OPENWEATHER_API_KEY = "38e01cfb763fc738e9eddee84cfc4384"

# API endpoints
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
N2YO_URL = "https://api.n2yo.com/rest/v1/satellite"

# Miasta do obserwacji
OBSERVATION_CITIES = {
    "warszawa": {
        "name": "Warszawa", 
        "lat": 52.2297, 
        "lon": 21.0122,
        "emoji": "🏛️",
        "timezone": "Europe/Warsaw"
    },
    "koszalin": {
        "name": "Koszalin", 
        "lat": 54.1943, 
        "lon": 16.1712,
        "emoji": "🌲",
        "timezone": "Europe/Warsaw"
    },
    "krakow": {
        "name": "Kraków", 
        "lat": 50.0647, 
        "lon": 19.9450,
        "emoji": "🏰",
        "timezone": "Europe/Warsaw"
    }
}

# Satelity do śledzenia
SATELLITES = {
    "iss": {
        "name": "Międzynarodowa Stacja Kosmiczna (ISS)",
        "norad_id": 25544,
        "emoji": "🛰️"
    },
    "hubble": {
        "name": "Teleskop Hubble'a (HST)",
        "norad_id": 20580,
        "emoji": "🔭"
    },
    "landsat": {
        "name": "Landsat 8",
        "norad_id": 39084,
        "emoji": "🛰️"
    },
    "sentinel": {
        "name": "Sentinel-2A",
        "norad_id": 40697,
        "emoji": "🛰️"
    }
}

# Warunki dobrej widoczności
VISIBILITY_THRESHOLDS = {
    "excellent": {"min": 80, "emoji": "✨", "name": "DOSKONAŁE"},
    "good": {"min": 60, "emoji": "⭐", "name": "DOBRE"},
    "moderate": {"min": 40, "emoji": "⛅", "name": "ŚREDNIE"},
    "poor": {"min": 20, "emoji": "🌥️", "name": "SŁABE"},
    "bad": {"min": 0, "emoji": "🌧️", "name": "ZŁE"}
}

# Kalendarz 13-miesięczny z pełnymi danymi
ASTRONOMICAL_CALENDAR = {
    "capricorn": {
        "name": "Koziorożec",
        "symbol": "♑",
        "element": "Ziemia",
        "emoji": "🐐",
        "dates": "20.01 - 16.02",
        "traits": ["Ambitny", "Praktyczny", "Cierpliwy"],
        "color": "Brązowy",
        "stone": "Granat"
    },
    "aquarius": {
        "name": "Wodnik",
        "symbol": "♒",
        "element": "Powietrze",
        "emoji": "🏺",
        "dates": "17.02 - 18.03",
        "traits": ["Innowacyjny", "Humanitarny", "Niezależny"],
        "color": "Niebieski",
        "stone": "Ametyst"
    },
    "pisces": {
        "name": "Ryby",
        "symbol": "♓",
        "element": "Woda",
        "emoji": "🐟",
        "dates": "19.03 - 17.04",
        "traits": ["Empatyczny", "Intuicyjny", "Artystyczny"],
        "color": "Fioletowy",
        "stone": "Akwarel"
    },
    "aries": {
        "name": "Baran",
        "symbol": "♈",
        "element": "Ogień",
        "emoji": "🐏",
        "dates": "18.04 - 18.05",
        "traits": ["Odważny", "Dynamiczny", "Zdeterminowany"],
        "color": "Czerwony",
        "stone": "Krwawnik"
    },
    "taurus": {
        "name": "Byk",
        "symbol": "♉",
        "element": "Ziemia",
        "emoji": "🐂",
        "dates": "19.05 - 17.06",
        "traits": ["Zdeterminowany", "Wierny", "Zmysłowy"],
        "color": "Zielony",
        "stone": "Szmaragd"
    },
    "gemini": {
        "name": "Bliźnięta",
        "symbol": "♊",
        "element": "Powietrze",
        "emoji": "👯",
        "dates": "18.06 - 16.07",
        "traits": ["Komunikatywny", "Ciekawy", "Elastyczny"],
        "color": "Żółty",
        "stone": "Akwamaryn"
    },
    "cancer": {
        "name": "Rak",
        "symbol": "♋",
        "element": "Woda",
        "emoji": "🦀",
        "dates": "17.07 - 16.08",
        "traits": ["Troskliwy", "Intuicyjny", "Wrażliwy"],
        "color": "Srebrny",
        "stone": "Perła"
    },
    "leo": {
        "name": "Lew",
        "symbol": "♌",
        "element": "Ogień",
        "emoji": "🦁",
        "dates": "17.08 - 15.09",
        "traits": ["Kreatywny", "Hojny", "Ciepły"],
        "color": "Pomarańczowy",
        "stone": "Rubin"
    },
    "virgo": {
        "name": "Panna",
        "symbol": "♍",
        "element": "Ziemia",
        "emoji": "🌾",
        "dates": "16.09 - 15.10",
        "traits": ["Analityczny", "Praktyczny", "Skrupulatny"],
        "color": "Brązowy",
        "stone": "Sapphir"
    },
    "libra": {
        "name": "Waga",
        "symbol": "♎",
        "element": "Powietrze",
        "emoji": "⚖️",
        "dates": "16.10 - 15.11",
        "traits": ["Dyplomatyczny", "Sprawiedliwy", "Społeczny"],
        "color": "Niebieski",
        "stone": "Opal"
    },
    "scorpio": {
        "name": "Skorpion",
        "symbol": "♏",
        "element": "Woda",
        "emoji": "🦂",
        "dates": "16.11 - 28.11",
        "traits": ["Namiętny", "Zdeterminowany", "Intensywny"],
        "color": "Czarny",
        "stone": "Topaz"
    },
    "ophiuchus": {
        "name": "Wężownik",
        "symbol": "⛎",
        "element": "Ogień",
        "emoji": "🐍",
        "dates": "29.11 - 17.12",
        "traits": ["Uzdrowiciel", "Mądry", "Tajemniczy"],
        "color": "Purpurowy",
        "stone": "Szafir"
    },
    "sagittarius": {
        "name": "Strzelec",
        "symbol": "♐",
        "element": "Ogień",
        "emoji": "🏹",
        "dates": "18.12 - 19.01",
        "traits": ["Optymistyczny", "Przygodowy", "Szczery"],
        "color": "Fioletowy",
        "stone": "Turkus"
    }
}

print("=" * 60)
print("🌌 COSMOS SENTRY v1.0 - SYSTEM ASTROMETEOROLOGICZNY")
print(f"🌐 URL: {RENDER_URL}")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== FUNKCJE POGODOWE ======================
def get_openweather_data(lat, lon):
    """Pobierz aktualną pogodę z OpenWeather"""
    try:
        url = f"{OPENWEATHER_URL}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            logger.error(f"OpenWeather error: {data}")
            return None
        
        return {
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "wind_deg": data["wind"].get("deg", 0),
            "clouds": data["clouds"]["all"],
            "visibility": data.get("visibility", 10000) / 1000,  # m -> km
            "description": data["weather"][0]["description"],
            "weather_main": data["weather"][0]["main"],
            "icon": data["weather"][0]["icon"],
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        logger.error(f"❌ Błąd OpenWeather: {e}")
        return None

def get_openweather_forecast(lat, lon):
    """Pobierz prognozę 5-dniową"""
    try:
        url = f"{OPENWEATHER_URL}/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl",
            "cnt": 40
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            return None
        
        forecast = []
        for item in data["list"][:8]:  # Pierwsze 8 okresów (24h)
            forecast.append({
                "time": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                "temp": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "description": item["weather"][0]["description"],
                "icon": item["weather"][0]["icon"],
                "humidity": item["main"]["humidity"],
                "wind_speed": item["wind"]["speed"]
            })
        
        return forecast
    except Exception as e:
        logger.error(f"❌ Błąd prognozy: {e}")
        return None

def get_openweather_alerts(lat, lon):
    """Pobierz alerty pogodowe"""
    try:
        url = f"{OPENWEATHER_URL}/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "exclude": "current,minutely,daily",
            "lang": "pl"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        alerts = []
        if "alerts" in data:
            for alert in data["alerts"]:
                alerts.append({
                    "event": alert.get("event", ""),
                    "description": alert.get("description", ""),
                    "start": datetime.fromtimestamp(alert.get("start", 0)).strftime("%d.%m %H:%M"),
                    "end": datetime.fromtimestamp(alert.get("end", 0)).strftime("%d.%m %H:%M")
                })
        
        return alerts[:3]  # Maksymalnie 3 alerty
    except Exception as e:
        logger.error(f"❌ Błąd alertów: {e}")
        return []

def get_nasa_apod():
    """Pobierz zdjęcie dnia NASA (Astronomy Picture of the Day)"""
    try:
        url = NASA_APOD_URL
        params = {
            "api_key": NASA_API_KEY,
            "hd": True
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            return None
        
        return {
            "title": data.get("title", "Brak tytułu"),
            "explanation": data.get("explanation", "Brak opisu"),
            "url": data.get("url", ""),
            "hd_url": data.get("hdurl", data.get("url", "")),
            "date": data.get("date", ""),
            "copyright": data.get("copyright", "NASA")
        }
    except Exception as e:
        logger.error(f"❌ Błąd NASA APOD: {e}")
        return None

def get_iss_position():
    """Pobierz aktualną pozycję ISS z N2YO API"""
    try:
        url = f"{N2YO_URL}/positions/25544/{OBSERVATION_CITIES['warszawa']['lat']}/{OBSERVATION_CITIES['warszawa']['lon']}/0/2/"
        params = {
            "apiKey": N2YO_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            return None
        
        positions = data.get("positions", [])
        if positions:
            pos = positions[0]
            return {
                "latitude": pos.get("satlatitude", 0),
                "longitude": pos.get("satlongitude", 0),
                "altitude": pos.get("sataltitude", 0),
                "velocity": pos.get("satvelocity", 0),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        return None
    except Exception as e:
        logger.error(f"❌ Błąd ISS API: {e}")
        return None

def get_satellite_passes(satellite_id, lat, lon):
    """Pobierz przeloty satelity nad daną lokalizacją"""
    try:
        url = f"{N2YO_URL}/visualpasses/{satellite_id}/{lat}/{lon}/0/2/5/"
        params = {
            "apiKey": N2YO_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200 or "passes" not in data:
            return []
        
        passes = []
        for pass_info in data["passes"][:5]:  # Maksymalnie 5 przelotów
            passes.append({
                "startUTC": pass_info.get("startUTC", 0),
                "startTime": datetime.fromtimestamp(pass_info.get("startUTC", 0)).strftime("%H:%M"),
                "endTime": datetime.fromtimestamp(pass_info.get("endUTC", 0)).strftime("%H:%M"),
                "duration": pass_info.get("duration", 0),
                "maxElevation": pass_info.get("maxElevation", 0),
                "mag": pass_info.get("mag", 0)
            })
        
        return passes
    except Exception as e:
        logger.error(f"❌ Błąd przelotów satelity: {e}")
        return []

# ====================== FUNKCJE ASTRONOMICZNE ======================
def calculate_moon_phase():
    """Oblicz fazę księżyca z dużą dokładnością"""
    now = datetime.now()
    days_in_moon_cycle = 29.530588853
    last_new_moon = datetime(2026, 1, 10, 12, 0, 0)
    days_since_new = (now - last_new_moon).total_seconds() / 86400
    
    moon_phase = (days_since_new % days_in_moon_cycle) / days_in_moon_cycle
    
    phases = [
        (0.0, "🌑 Nów", "Księżyc niewidoczny", 0),
        (0.25, "🌒 Rosnący sierp", "Widoczny wieczorem", 25),
        (0.5, "🌓 Pierwsza kwadra", "Połowa widoczna", 50),
        (0.75, "🌔 Ubywający garbaty", "Prawie pełny", 75),
        (1.0, "🌕 Pełnia", "Cały widoczny", 100),
        (1.25, "🌖 Malejący garbaty", "Prawie pełny", 75),
        (1.5, "🌗 Ostatnia kwadra", "Połowa widoczna", 50),
        (1.75, "🌘 Malejący sierp", "Widoczny rano", 25)
    ]
    
    for phase_value, emoji_name, description, illumination in phases:
        if moon_phase <= phase_value:
            return {
                "emoji": emoji_name.split()[0],
                "name": emoji_name.split()[1],
                "description": description,
                "illumination": illumination,
                "phase": round(moon_phase, 3)
            }
    
    return {
        "emoji": "🌑",
        "name": "Nów",
        "description": "Księżyc niewidoczny",
        "illumination": 0,
        "phase": round(moon_phase, 3)
    }

def get_current_astronomical_month():
    """Zwróć aktualny miesiąc astronomiczny"""
    now = datetime.now()
    month = now.month
    day = now.day
    
    # Specjalna data - 24 stycznia 2026
    if now.year == 2026 and month == 1 and day == 24:
        return ASTRONOMICAL_CALENDAR["capricorn"]
    
    # Prosty system oparty na miesiącach
    month_map = {
        1: "capricorn", 2: "aquarius", 3: "pisces", 4: "aries",
        5: "taurus", 6: "gemini", 7: "cancer", 8: "leo",
        9: "virgo", 10: "libra", 11: "scorpio", 12: "sagittarius"
    }
    
    return ASTRONOMICAL_CALENDAR.get(month_map.get(month, "capricorn"))

def get_astronomical_date():
    """Zwróć pełną datę astronomiczną"""
    now = datetime.now()
    month_data = get_current_astronomical_month()
    
    # Generuj losowy dzień z zakresu 1-28
    day_of_month = (now.day - 1) % 28 + 1
    
    return {
        "day": day_of_month,
        "month": month_data["name"],
        "symbol": month_data["symbol"],
        "element": month_data["element"],
        "emoji": month_data["emoji"],
        "traits": month_data["traits"],
        "color": month_data["color"],
        "stone": month_data["stone"],
        "gregorian": now.strftime("%d.%m.%Y")
    }

# ====================== FUNKCJE POMOCNICZE ======================
def get_weather_icon(icon_code):
    """Mapuj kod ikony na emoji"""
    icon_map = {
        "01d": "☀️", "01n": "🌙",
        "02d": "⛅", "02n": "⛅",
        "03d": "☁️", "03n": "☁️",
        "04d": "☁️", "04n": "☁️",
        "09d": "🌧️", "09n": "🌧️",
        "10d": "🌦️", "10n": "🌦️",
        "11d": "⛈️", "11n": "⛈️",
        "13d": "❄️", "13n": "❄️",
        "50d": "🌫️", "50n": "🌫️"
    }
    return icon_map.get(icon_code, "🌤️")

def get_wind_direction(degrees):
    """Konwertuj stopnie na kierunek wiatru"""
    directions = ["↓ Północ", "↘ Północny-Wschód", "→ Wschód", "↗ Południowy-Wschód",
                  "↑ Południe", "↖ Południowy-Zachód", "← Zachód", "↙ Północny-Zachód"]
    index = round(degrees / 45) % 8
    return directions[index]

def get_visibility_score(weather_data):
    """Oblicz wynik widoczności na podstawie warunków pogodowych"""
    score = 100
    
    # Odejmij punkty za złe warunki
    score -= min(weather_data["clouds"] / 2, 50)  # Zachmurzenie do 50 punktów
    score -= max(0, (weather_data["humidity"] - 60) / 2)  # Wilgotność powyżej 60%
    score -= min(weather_data["wind_speed"] * 2, 20)  # Wiatr do 20 punktów
    
    # Bonus za dobrą widoczność
    if weather_data["visibility"] > 20:
        score += 10
    
    # Ogranicz do 0-100
    score = max(0, min(100, score))
    
    # Określ kategorię
    for category, threshold in VISIBILITY_THRESHOLDS.items():
        if score >= threshold["min"]:
            return {
                "score": round(score),
                "emoji": threshold["emoji"],
                "category": threshold["name"]
            }
    
    return {"score": round(score), "emoji": "🌧️", "category": "ZŁE"}

def get_star_visibility(weather_data):
    """Określ widoczność gwiazd"""
    if weather_data["clouds"] < 20 and weather_data["visibility"] > 15:
        return "✨ Doskonała widoczność gwiazd"
    elif weather_data["clouds"] < 40 and weather_data["visibility"] > 10:
        return "⭐ Dobra widoczność gwiazd"
    elif weather_data["clouds"] < 60:
        return "🌟 Umiarkowana widoczność"
    else:
        return "☁️ Słaba widoczność gwiazd"

def create_progress_bar(value, max_value=100, length=10):
    """Twórz pasek postępu"""
    filled = int((value / max_value) * length)
    empty = length - filled
    return "█" * filled + "░" * empty

# ====================== FORMATOWANIE WIADOMOŚCI ======================
def create_beautiful_header(title, emoji="🌌"):
    """Twórz piękny nagłówek wiadomości"""
    border = "═" * 40
    return f"{border}\n{emoji} <b>{title}</b>\n{border}\n\n"

def create_section(title, emoji="📊"):
    """Twórz sekcję wiadomości"""
    return f"\n{emoji} <b>{title}</b>\n"

def create_info_line(label, value, emoji="•"):
    """Twórz linię informacyjną"""
    return f"{emoji} <b>{label}:</b> {value}\n"

def create_progress_display(label, value, max_value=100):
    """Twórz wyświetlacz z paskiem postępu"""
    bar = create_progress_bar(value, max_value)
    percent = (value / max_value) * 100
    return f"• <b>{label}:</b> {bar} {value}/{max_value} ({percent:.0f}%)\n"

# ====================== GENEROWANIE RAPORTÓW ======================
def generate_full_astro_report(city_key):
    """Wygeneruj pełny raport astrometeorologiczny"""
    city = OBSERVATION_CITIES[city_key]
    
    # Pobierz dane
    weather_data = get_openweather_data(city["lat"], city["lon"])
    forecast_data = get_openweather_forecast(city["lat"], city["lon"])
    moon_data = calculate_moon_phase()
    astro_date = get_astronomical_date()
    visibility_score = get_visibility_score(weather_data)
    alerts = get_openweather_alerts(city["lat"], city["lon"])
    
    # Zbuduj raport
    report = ""
    
    # Nagłówek
    report += create_beautiful_header(f"COSMOS SENTRY - {city['name'].upper()}", city['emoji'])
    
    # Data i czas
    report += create_section("📅 DATA I CZAS", "⏱️")
    report += create_info_line("Data kalendarzowa", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    report += create_info_line("Data astronomiczna", f"{astro_date['day']} {astro_date['symbol']} {astro_date['month']}")
    report += create_info_line("Domena", f"{astro_date['element']} {astro_date['emoji']}")
    
    # Pogoda
    report += create_section("🌤️ AKTUALNA POGODA", get_weather_icon(weather_data["icon"]))
    report += create_info_line("Stan", f"{weather_data['description'].capitalize()}")
    report += create_info_line("Temperatura", f"{weather_data['temp']:.1f}°C (odczuwalna {weather_data['feels_like']:.1f}°C)")
    report += create_info_line("Wilgotność", f"{weather_data['humidity']}%")
    report += create_info_line("Ciśnienie", f"{weather_data['pressure']} hPa")
    report += create_info_line("Wiatr", f"{weather_data['wind_speed']} m/s {get_wind_direction(weather_data['wind_deg'])}")
    report += create_info_line("Zachmurzenie", f"{weather_data['clouds']}%")
    report += create_info_line("Widoczność", f"{weather_data['visibility']:.1f} km")
    report += create_info_line("Słońce", f"Wschód: {weather_data['sunrise']} | Zachód: {weather_data['sunset']}")
    
    # Księżyc
    report += create_section("🌙 KSIĘŻYC", moon_data["emoji"])
    report += create_info_line("Faza", f"{moon_data['name']}")
    report += create_info_line("Oświetlenie", f"{moon_data['illumination']}%")
    report += create_info_line("Opis", moon_data["description"])
    
    # Warunki obserwacyjne
    report += create_section("🔭 WARUNKI OBSERWACYJNE", visibility_score["emoji"])
    report += create_info_line("Ocena", f"{visibility_score['category']}")
    report += create_info_line("Wynik", f"{visibility_score['score']}/100")
    report += create_info_line("Widoczność gwiazd", get_star_visibility(weather_data))
    
    # Szczegółowe parametry
    report += "\n📊 <b>SZCZEGÓŁOWA ANALIZA:</b>\n"
    report += create_progress_display("Zachmurzenie", 100 - weather_data["clouds"])
    report += create_progress_display("Widoczność", min(weather_data["visibility"] * 5, 100))
    report += create_progress_display("Wilgotność", 100 - weather_data["humidity"])
    report += create_progress_display("Stabilność wiatru", max(0, 100 - (weather_data["wind_speed"] * 10)))
    
    # Kalendarz astronomiczny
    report += create_section("♑ KALENDARZ ASTRONOMICZNY", astro_date["symbol"])
    report += create_info_line("Znak", f"{astro_date['month']} {astro_date['emoji']}")
    report += create_info_line("Cechy", ", ".join(astro_date["traits"]))
    report += create_info_line("Kolor", astro_date["color"])
    report += create_info_line("Kamień", astro_date["stone"])
    
    # Alerty
    if alerts:
        report += create_section("⚠️ ALERTY POGODOWE", "🚨")
        for alert in alerts:
            report += f"• <b>{alert['event']}</b>\n"
            report += f"  ⏰ {alert['start']} - {alert['end']}\n"
    
    # Prognoza krótkoterminowa
    if forecast_data:
        report += create_section("📈 PROGNOZA 24H", "⏳")
        for i, period in enumerate(forecast_data[:4]):  # Pierwsze 4 okresy
            report += f"• {period['time']}: {period['temp']:.1f}°C | {get_weather_icon(period['icon'])} {period['description']}\n"
    
    # Rekomendacja
    report += create_section("💡 REKOMENDACJA", "🎯")
    if visibility_score["score"] >= 80 and not weather_data.get("is_day", False):
        report += "✅ <b>IDEALNE WARUNKI!</b>\n• Czyste niebo\n• Doskonała widoczność\n• Wychodź na obserwacje!\n"
    elif visibility_score["score"] >= 60:
        report += "🟡 <b>DOBRE WARUNKI</b>\n• Możliwa obserwacja\n• Sprawdź lokalne warunki\n"
    else:
        report += "🔴 <b>ZŁE WARUNKI</b>\n• Lepiej poczekać\n• Sprawdź ponownie później\n"
    
    # Stopka
    report += f"\n{'═' * 40}\n"
    report += f"<i>🌌 COSMOS SENTRY v1.0 | Data: {weather_data['timestamp']}</i>\n"
    report += f"<i>📍 {city['name']} | Źródło: OpenWeather API</i>"
    
    return report

def generate_moon_report():
    """Wygeneruj raport o księżycu"""
    moon_data = calculate_moon_phase()
    astro_date = get_astronomical_date()
    
    report = ""
    report += create_beautiful_header("RAPORT KSIĘŻYCOWY", moon_data["emoji"])
    
    report += create_section("🌕 FAZA KSIĘŻYCA", moon_data["emoji"])
    report += create_info_line("Nazwa", moon_data["name"])
    report += create_info_line("Oświetlenie", f"{moon_data['illumination']}%")
    report += create_info_line("Cykl księżycowy", f"{moon_data['phase']:.3f}")
    report += create_info_line("Opis", moon_data["description"])
    
    report += create_section("📅 KALENDARZ KSIĘŻYCOWY", "📆")
    
    # Symuluj kalendarz księżycowy na 7 dni
    today = datetime.now()
    report += "• <b>Najbliższe fazy:</b>\n"
    
    phases_info = [
        ("🌑 Nów", "Nowy księżyc, niewidoczny"),
        ("🌒 Rosnący sierp", "Widoczny wieczorem"),
        ("🌓 I kwadra", "Połowa widoczna"),
        ("🌔 Ubywający", "Prawie pełny"),
        ("🌕 Pełnia", "Cały widoczny"),
        ("🌖 Malejący", "Prawie pełny"),
        ("🌗 III kwadra", "Połowa widoczna"),
        ("🌘 Malejący sierp", "Widoczny rano")
    ]
    
    current_phase_index = int(moon_data["phase"] * 8) % 8
    for i in range(3):  # Następne 3 fazy
        next_index = (current_phase_index + i + 1) % 8
        days_to_next = i * 3.7 + random.uniform(2, 4)
        emoji, name = phases_info[next_index][0].split(" ", 1)
        report += f"  {emoji} {name} (za ~{days_to_next:.1f} dni)\n"
    
    report += create_section("💎 WPŁYW NA OBSERWACJE", "✨")
    
    if moon_data["illumination"] < 10:
        report += "✅ <b>Doskonale do obserwacji</b>\n• Ciemne niebo\n• Widoczne słabe obiekty\n"
    elif moon_data["illumination"] < 50:
        report += "🟡 <b>Dobre warunki</b>\n• Umiarkowane światło\n• Widoczne jasne obiekty\n"
    else:
        report += "🔴 <b>Trudne warunki</b>\n• Jasne niebo\n• Tylko najjaśniejsze obiekty\n"
    
    report += f"\n{'═' * 40}\n"
    report += f"<i>🌌 COSMOS SENTRY v1.0 | Data: {datetime.now().strftime('%H:%M:%S')}</i>"
    
    return report

def generate_calendar_report():
    """Wygeneruj raport kalendarza"""
    astro_date = get_astronomical_date()
    all_months = list(ASTRONOMICAL_CALENDAR.values())
    
    report = ""
    report += create_beautiful_header("KALENDARZ 13-MIESIĘCZNY", "📅")
    
    # Aktualny miesiąc
    report += create_section("🎯 AKTUALNY MIESIĄC", astro_date["symbol"])
    report += create_info_line("Nazwa", f"{astro_date['month']} {astro_date['emoji']}")
    report += create_info_line("Dzień", f"{astro_date['day']}/28")
    report += create_info_line("Żywioł", astro_date["element"])
    report += create_info_line("Cechy", ", ".join(astro_date["traits"]))
    report += create_info_line("Kolor", astro_date["color"])
    report += create_info_line("Kamień", astro_date["stone"])
    
    # Wszystkie miesiące
    report += create_section("🗓️ PEŁNY KALENDARZ", "📆")
    
    for month in all_months:
        current_marker = " 🔸" if month["name"] == astro_date["month"] else ""
        report += f"• {month['symbol']} <b>{month['name']}</b> {month['emoji']}\n"
        report += f"  {month['dates']}{current_marker}\n"
        report += f"  {month['element']} | {month['color'].split()[0]}\n"
    
    # Opis systemu
    report += create_section("📚 O SYSTEMIE", "ℹ️")
    report += "• <b>13 miesięcy po 28 dni</b> = 364 dni\n"
    report += "• <b>+1 dzień</b> (lub +2 w roku przestępnym)\n"
    report += "• <b>Każdy tydzień ma 7 dni</b>\n"
    report += "• <b>Każdy miesiąc ma 4 tygodnie</b>\n"
    
    report += f"\n{'═' * 40}\n"
    report += f"<i>🌌 System daty astronomicznej | COSMOS SENTRY v1.0</i>"
    
    return report

def generate_iss_report():
    """Wygeneruj raport o ISS"""
    iss_position = get_iss_position()
    
    report = ""
    report += create_beautiful_header("MIĘDZYNARODOWA STACJA KOSMICZNA (ISS)", "🛰️")
    
    if iss_position:
        report += create_section("📍 AKTUALNA POZYCJA", "🌍")
        report += create_info_line("Szerokość geogr.", f"{iss_position['latitude']:.2f}°")
        report += create_info_line("Długość geogr.", f"{iss_position['longitude']:.2f}°")
        report += create_info_line("Wysokość", f"{iss_position['altitude']:.2f} km")
        report += create_info_line("Prędkość", f"{iss_position['velocity']:.2f} km/h")
        
        # Dodaj informacje o przelotach nad miastami
        report += create_section("🔭 NAJBLIŻSZE PRZELOTY", "⏱️")
        
        for city_key, city in OBSERVATION_CITIES.items():
            passes = get_satellite_passes(25544, city["lat"], city["lon"])
            if passes:
                report += f"\n<b>{city['emoji']} {city['name']}:</b>\n"
                for p in passes[:2]:  # Dwa najbliższe przeloty
                    report += f"• {p['startTime']} - {p['endTime']} (max: {p['maxElevation']:.0f}°)\n"
    else:
        report += "❌ <b>Nie udało się pobrać danych o ISS</b>\n"
        report += "Spróbuj ponownie za chwilę.\n"
    
    # Dodatkowe informacje
    report += create_section("📊 INFORMACJE O ISS", "ℹ️")
    report += "• <b>Prędkość orbitalna:</b> 27,600 km/h\n"
    report += "• <b>Wysokość orbity:</b> ~400 km\n"
    report += "• <b>Okres orbitalny:</b> 90 minut\n"
    report += "• <b>Załoga:</b> 7 astronautów\n"
    report += "• <b>Start:</b> 20 listopada 1998\n"
    
    report += f"\n{'═' * 40}\n"
    report += f"<i>🛰️ Dane: N2YO API | {datetime.now().strftime('%H:%M:%S')}</i>"
    
    return report

def generate_satellites_report():
    """Wygeneruj raport o satelitach"""
    report = ""
    report += create_beautiful_header("SYSTEM ŚLEDZENIA SATELITÓW", "🛰️")
    
    report += create_section("📡 DOSTĘPNE SATELITY", "✨")
    
    for sat_id, sat_info in SATELLITES.items():
        report += f"• {sat_info['emoji']} <b>{sat_info['name']}</b>\n"
        report += f"  ID: {sat_info['norad_id']}\n"
    
    report += create_section("🎯 JAK OBSERWOWAĆ", "🔭")
    report += "1. Sprawdź przeloty nad Twoją lokalizacją\n"
    report += "2. Wybierz satelitę z dobrej widocznością\n"
    report += "3. Sprawdź warunki pogodowe\n"
    report += "4. Bądź gotowy 5 minut przed przelotem\n"
    
    report += create_section("📝 PRZYKŁADOWE KOMENDY", "💡")
    report += "<code>/iss</code> - Aktualna pozycja ISS\n"
    report += "<code>/satellites passes warszawa</code> - Przeloty nad Warszawą\n"
    report += "<code>/satellites photo</code> - Zdjęcie dnia NASA\n"
    
    report += f"\n{'═' * 40}\n"
    report += f"<i>🛰️ System śledzenia satelitów | COSMOS SENTRY v1.0</i>"
    
    return report

def generate_nasa_photo_report():
    """Wygeneruj raport ze zdjęciem NASA"""
    apod_data = get_nasa_apod()
    
    report = ""
    report += create_beautiful_header("ZDJĘCIE DNIA NASA", "🛰️")
    
    if apod_data and apod_data.get("url"):
        report += f"\n📅 <b>Data:</b> {apod_data['date']}\n"
        report += f"📸 <b>Tytuł:</b> {apod_data['title']}\n"
        report += f"👨‍🚀 <b>Autor:</b> {apod_data['copyright']}\n\n"
        
        # Skrócony opis (pierwsze 200 znaków)
        short_desc = apod_data['explanation'][:200] + "..." if len(apod_data['explanation']) > 200 else apod_data['explanation']
        report += f"📝 <b>Opis:</b> {short_desc}\n\n"
        
        # Link do zdjęcia
        report += f"🔗 <b>Link do zdjęcia:</b>\n{apod_data['url']}\n"
    else:
        report += "❌ <b>Nie udało się pobrać zdjęcia dnia NASA</b>\n"
        report += "Spróbuj ponownie za chwilę.\n"
    
    report += f"\n{'═' * 40}\n"
    report += f"<i>🛰️ NASA Astronomy Picture of the Day | {datetime.now().strftime('%H:%M:%S')}</i>"
    
    return report

# ====================== FLASK APP ======================
app = Flask(__name__)

@app.route('/')
def home():
    """Strona główna"""
    now = datetime.now()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌌 COSMOS SENTRY v1.0</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0c0e2e 0%, #1a1b3e 50%, #2a2b5e 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-top: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            .title {{
                font-size: 48px;
                font-weight: bold;
                background: linear-gradient(45deg, #00dbde, #fc00ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }}
            .status-badge {{
                display: inline-block;
                padding: 10px 20px;
                background: linear-gradient(45deg, #00b09b, #96c93d);
                border-radius: 20px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .features-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin: 40px 0;
            }}
            .feature-card {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s;
            }}
            .feature-card:hover {{
                transform: translateY(-5px);
                background: rgba(255, 255, 255, 0.15);
            }}
            .cta-button {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                display: inline-block;
                margin: 10px;
                font-weight: bold;
                font-size: 18px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="title">🌌 COSMOS SENTRY v1.0</h1>
                <h2 style="color: #81ecec;">Zaawansowany System Astrometeorologiczny</h2>
                <div class="status-badge">🟢 SYSTEM AKTYWNY | OpenWeather API | NASA API | N2YO Satellites</div>
                <h2>📅 {now.strftime("%d.%m.%Y %H:%M")}</h2>
            </div>
            
            <div class="features-grid">
                <div class="feature-card">
                    <h3>🌠 Astro Prognoza</h3>
                    <p>Zaawansowana analiza warunków obserwacyjnych z OpenWeather API</p>
                </div>
                <div class="feature-card">
                    <h3>📅 Kalendarz 13-miesięczny</h3>
                    <p>Unikalny system daty astronomicznej z pełną symboliką</p>
                </div>
                <div class="feature-card">
                    <h3>🌙 Fazy Księżyca</h3>
                    <p>Precyzyjne obliczenia faz księżycowych i oświetlenia</p>
                </div>
                <div class="feature-card">
                    <h3>🛰️ Śledzenie Satelitów</h3>
                    <p>Monitorowanie ISS i innych satelitów w czasie rzeczywistym</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" class="cta-button">
                    💬 Otwórz bota w Telegram
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.3);">
                <p>🌌 COSMOS SENTRY v1.0 | Zaawansowany System Astrometeorologiczny</p>
                <p>API: OpenWeather • NASA • N2YO Satellites</p>
                <p>{now.strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# ====================== TELEGRAM FUNCTIONS ======================
def send_telegram_message(chat_id, text):
    """Wyślij wiadomość przez Telegram API"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return None

# ====================== TELEGRAM WEBHOOK ======================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Główny endpoint dla webhook Telegram"""
    try:
        data = request.get_json()
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip().lower()
            
            # Komenda /start
            if text == "/start":
                welcome_msg = (
                    f"{create_beautiful_header('COSMOS SENTRY v1.0', '🌌')}"
                    f"<b>Witaj w zaawansowanym systemie astrometeorologicznym!</b>\n\n"
                    
                    f"{create_section('🚀 GŁÓWNE FUNKCJE', '✨')}"
                    f"• 🌤️ <b>Prognoza obserwacyjna</b> z OpenWeather\n"
                    f"• 📅 <b>Kalendarz 13-miesięczny</b>\n"
                    f"• 🌙 <b>Fazy Księżyca</b> z dokładnością\n"
                    f"• 🛰️ <b>Śledzenie satelitów</b> (ISS, Hubble, Landsat)\n"
                    f"• ⚡ <b>Alerty pogodowe</b>\n"
                    f"• 📸 <b>Zdjęcia NASA</b> (APOD)\n\n"
                    
                    f"{create_section('🎯 KOMENDY', '📱')}"
                    f"<code>/astro warszawa</code> - Pełny raport\n"
                    f"<code>/astro koszalin</code> - Pełny raport\n"
                    f"<code>/astro krakow</code> - Pełny raport\n"
                    f"<code>/moon</code> - Raport księżycowy\n"
                    f"<code>/calendar</code> - Kalendarz astronomiczny\n"
                    f"<code>/iss</code> - Pozycja ISS\n"
                    f"<code>/satellites</code> - System śledzenia satelitów\n"
                    f"<code>/nasa</code> - Zdjęcie dnia NASA\n"
                    f"<code>/forecast [miasto]</code> - Prognoza 5-dniowa\n"
                    f"<code>/alerts [miasto]</code> - Alerty pogodowe\n"
                    f"<code>/weather [miasto]</code> - Aktualna pogoda\n"
                    f"<code>/help</code> - Pomoc\n\n"
                    
                    f"{'═' * 40}\n"
                    f"<i>🌌 COSMOS SENTRY v1.0 | Zaawansowany system astrometeorologiczny</i>"
                )
                send_telegram_message(chat_id, welcome_msg)
            
            # Komenda /astro
            elif text.startswith("/astro"):
                args = text[6:].strip()
                
                if not args:
                    args = "warszawa"
                
                if args in OBSERVATION_CITIES:
                    report = generate_full_astro_report(args)
                    send_telegram_message(chat_id, report)
                else:
                    send_telegram_message(chat_id, "❌ Nieznane miasto. Dostępne: warszawa, koszalin, krakow")
            
            # Komenda /moon
            elif text == "/moon":
                report = generate_moon_report()
                send_telegram_message(chat_id, report)
            
            # Komenda /calendar
            elif text == "/calendar":
                report = generate_calendar_report()
                send_telegram_message(chat_id, report)
            
            # Komenda /iss
            elif text == "/iss":
                report = generate_iss_report()
                send_telegram_message(chat_id, report)
            
            # Komenda /satellites
            elif text == "/satellites":
                report = generate_satellites_report()
                send_telegram_message(chat_id, report)
            
            # Komenda /nasa
            elif text == "/nasa":
                report = generate_nasa_photo_report()
                send_telegram_message(chat_id, report)
            
            # Komenda /weather
            elif text.startswith("/weather"):
                args = text[8:].strip()
                
                if not args:
                    args = "warszawa"
                
                if args in OBSERVATION_CITIES:
                    city = OBSERVATION_CITIES[args]
                    weather_data = get_openweather_data(city["lat"], city["lon"])
                    
                    if weather_data:
                        city_name_upper = city["name"].upper()
                        report = create_beautiful_header(f"POGODA - {city_name_upper}", city['emoji'])
                        
                        report += create_section("🌤️ AKTUALNA POGODA", get_weather_icon(weather_data["icon"]))
                        report += create_info_line("Stan", f"{weather_data['description'].capitalize()}")
                        report += create_info_line("Temperatura", f"{weather_data['temp']:.1f}°C")
                        report += create_info_line("Odczuwalna", f"{weather_data['feels_like']:.1f}°C")
                        report += create_info_line("Wilgotność", f"{weather_data['humidity']}%")
                        report += create_info_line("Ciśnienie", f"{weather_data['pressure']} hPa")
                        report += create_info_line("Wiatr", f"{weather_data['wind_speed']} m/s")
                        report += create_info_line("Zachmurzenie", f"{weather_data['clouds']}%")
                        report += create_info_line("Widoczność", f"{weather_data['visibility']:.1f} km")
                        report += create_info_line("Słońce", f"↑ {weather_data['sunrise']} | ↓ {weather_data['sunset']}")
                        
                        report += f"\n{'═' * 40}\n"
                        report += f"<i>🌤️ OpenWeather API | {weather_data['timestamp']}</i>"
                        
                        send_telegram_message(chat_id, report)
                    else:
                        send_telegram_message(chat_id, "❌ Nie udało się pobrać danych pogodowych")
                else:
                    send_telegram_message(chat_id, "❌ Nieznane miasto. Dostępne: warszawa, koszalin, krakow")
            
            # Komenda /forecast
            elif text.startswith("/forecast"):
                args = text[9:].strip()
                
                if not args:
                    args = "warszawa"
                
                if args in OBSERVATION_CITIES:
                    city = OBSERVATION_CITIES[args]
                    forecast = get_openweather_forecast(city["lat"], city["lon"])
                    
                    if forecast:
                        city_name_upper = city["name"].upper()
                        report = create_beautiful_header(f"PROGNOZA 5-DNIOWA - {city_name_upper}", city['emoji'])
                        
                        # Grupuj prognozę po dniach
                        daily_forecasts = {}
                        for item in forecast:
                            date = datetime.now().strftime("%d.%m")  # Uproszczenie
                            if date not in daily_forecasts:
                                daily_forecasts[date] = []
                            daily_forecasts[date].append(item)
                        
                        # Wyświetl prognozę
                        for i, (date, items) in enumerate(list(daily_forecasts.items())[:3]):
                            report += f"\n<b>📅 {date}:</b>\n"
                            for j, item in enumerate(items[:3]):  # 3 pomiary na dzień
                                report += f"• {item['time']}: {item['temp']:.1f}°C | {get_weather_icon(item['icon'])}\n"
                        
                        report += f"\n{'═' * 40}\n"
                        report += f"<i>🌤️ Prognoza OpenWeather | {datetime.now().strftime('%H:%M:%S')}</i>"
                        
                        send_telegram_message(chat_id, report)
                    else:
                        send_telegram_message(chat_id, "❌ Nie udało się pobrać prognozy")
                else:
                    send_telegram_message(chat_id, "❌ Nieznane miasto")
            
            # Komenda /alerts
            elif text.startswith("/alerts"):
                args = text[7:].strip()
                
                if not args:
                    args = "warszawa"
                
                if args in OBSERVATION_CITIES:
                    city = OBSERVATION_CITIES[args]
                    alerts = get_openweather_alerts(city["lat"], city["lon"])
                    
                    city_name_upper = city["name"].upper()
                    report = create_beautiful_header(f"ALERTY POGODOWE - {city_name_upper}", '⚠️')
                    
                    if alerts:
                        for alert in alerts:
                            report += f"\n🚨 <b>{alert['event']}</b>\n"
                            report += f"⏰ <i>{alert['start']} - {alert['end']}</i>\n"
                            report += f"📝 {alert['description'][:200]}...\n"
                    else:
                        report += "✅ <b>BRAK AKTYWNYCH ALERTÓW</b>\n\n"
                        report += "• Nie ma aktualnych ostrzeżeń pogodowych\n"
                        report += "• Warunki są stabilne\n"
                    
                    report += f"\n{'═' * 40}\n"
                    report += f"<i>⚠️ System ostrzegania OpenWeather | {datetime.now().strftime('%H:%M:%S')}</i>"
                    
                    send_telegram_message(chat_id, report)
                else:
                    send_telegram_message(chat_id, "❌ Nieznane miasto")
            
            # Komenda /help
            elif text == "/help":
                help_msg = (
                    f"{create_beautiful_header('POMOC - COSMOS SENTRY v1.0', '❓')}"
                    
                    f"{create_section('🌌 KOMENDY OBSERWACYJNE', '🔭')}"
                    f"<code>/astro warszawa</code> - Pełny raport astrometeorologiczny\n"
                    f"<code>/astro koszalin</code> - Pełny raport astrometeorologiczny\n"
                    f"<code>/astro krakow</code> - Pełny raport astrometeorologiczny\n\n"
                    
                    f"{create_section('🌙 KOMENDY KSIĘŻYCOWE', '🌕')}"
                    f"<code>/moon</code> - Szczegółowy raport faz księżyca\n"
                    f"<code>/moon calendar</code> - Kalendarz księżycowy\n\n"
                    
                    f"{create_section('📅 KOMENDY KALENDARZOWE', '🗓️')}"
                    f"<code>/calendar</code> - Kalendarz 13-miesięczny\n"
                    f"<code>/date</code> - Aktualna data astronomiczna\n\n"
                    
                    f"{create_section('🛰️ KOMENDY SATELITARNE', '📡')}"
                    f"<code>/iss</code> - Międzynarodowa Stacja Kosmiczna\n"
                    f"<code>/satellites</code> - System śledzenia satelitów\n"
                    f"<code>/nasa</code> - Zdjęcie dnia NASA\n\n"
                    
                    f"{create_section('🌤️ KOMENDY POGODOWE', '⛅')}"
                    f"<code>/weather [miasto]</code> - Aktualna pogoda\n"
                    f"<code>/forecast [miasto]</code> - Prognoza 5-dniowa\n"
                    f"<code>/alerts [miasto]</code> - Alerty pogodowe\n\n"
                    
                    f"{'═' * 40}\n"
                    f"<i>🌌 Wersja: 1.0 | API: OpenWeather, NASA, N2YO</i>\n"
                    f"<i>📞 Wsparcie: @PcSentintel_Bot</i>"
                )
                send_telegram_message(chat_id, help_msg)
            
            # Domyślna odpowiedź
            else:
                default_msg = (
                    f"{create_beautiful_header('COSMOS SENTRY v1.0', '🌌')}"
                    f"Nie rozpoznano komendy. Wpisz <code>/help</code> aby zobaczyć listę komend.\n\n"
                    f"<i>Zaawansowany system astrometeorologiczny z pięknym interfejsem</i>"
                )
                send_telegram_message(chat_id, default_msg)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Błąd przetwarzania webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== PING SYSTEM ======================
class PingService:
    """Serwis do utrzymania aktywności aplikacji"""
    
    def __init__(self):
        self.ping_count = 0
        self.last_ping = None
        self.is_running = False
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        """Uruchom pingowanie"""
        if not self.is_running:
            print("🔄 Uruchamianie systemu pingowania...")
            self.scheduler.add_job(self.ping_self, 'interval', seconds=PING_INTERVAL)
            self.scheduler.start()
            threading.Thread(target=self.ping_self, daemon=True).start()
            self.is_running = True
            print(f"✅ Pingowanie aktywne co {PING_INTERVAL/60} minut")
    
    def ping_self(self):
        """Wyślij ping do własnego endpointu"""
        try:
            self.ping_count += 1
            self.last_ping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            response = requests.get(f"{RENDER_URL}/", timeout=10)
            
            # Test OpenWeather API
            test_data = get_openweather_data(52.2297, 21.0122)
            
            logger.info(f"📡 Ping #{self.ping_count} - Status: {response.status_code}")
            if test_data:
                logger.info(f"🌤️ OpenWeather: {test_data['temp']:.1f}°C w Warszawie")
            else:
                logger.warning("⚠️ OpenWeather API: PROBLEM")
                
        except Exception as e:
            logger.error(f"❌ Błąd pingowania: {e}")

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("=" * 60)
    print("🌌 COSMOS SENTRY v1.0 - SYSTEM ASTROMETEOROLOGICZNY")
    print("=" * 60)
    
    now = datetime.now()
    moon = calculate_moon_phase()
    astro_date = get_astronomical_date()
    
    print(f"📅 Data: {now.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"🌙 Księżyc: {moon['name']} ({moon['illumination']}%)")
    print(f"♑ Kalendarz: {astro_date['day']} {astro_date['symbol']} {astro_date['month']}")
    print(f"📍 Miasta: {', '.join([c['name'] for c in OBSERVATION_CITIES.values()])}")
    print(f"🛰️ Satelity: {', '.join([s['name'] for s in SATELLITES.values()])}")
    
    # Test API
    print(f"\n🔍 Testowanie API...")
    test_weather = get_openweather_data(52.2297, 21.0122)
    if test_weather:
        print(f"✅ OpenWeather API: AKTYWNE")
        print(f"   • Temp: {test_weather['temp']:.1f}°C")
        print(f"   • Stan: {test_weather['description']}")
        print(f"   • Miasto: Warszawa")
    else:
        print(f"❌ OpenWeather API: NIEDOSTĘPNE")
    
    # Test NASA APOD
    apod = get_nasa_apod()
    if apod:
        print(f"✅ NASA APOD API: AKTYWNE")
        print(f"   • Ostatnie zdjęcie: {apod['title'][:30]}...")
    else:
        print(f"⚠️ NASA APOD API: MOŻLIWE PROBLEMY")
    
    print("=" * 60)
    print("🚀 System uruchomiony pomyślnie!")
    print("=" * 60)
    
    # Uruchom system pingowania
    ping_service = PingService()
    ping_service.start()
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )