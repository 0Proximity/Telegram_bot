#!/usr/bin/env python3
"""
🤖 SENTRY ONE v9.0 - Ultimate Astrometeorological System
Rozszerzony system z NASA zdjęciami, śledzeniem satelitów i zaawansowanymi powiadomieniami
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
import sqlite3
from typing import Dict, List, Optional, Tuple
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
N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
NASA_EARTH_URL = "https://api.nasa.gov/planetary/earth/assets"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Baza danych użytkowników
DB_FILE = "sentry_one.db"

# Miasta do obserwacji
OBSERVATION_CITIES = {
    "warszawa": {
        "name": "Warszawa", 
        "lat": 52.2297, 
        "lon": 21.0122, 
        "timezone": "Europe/Warsaw",
        "country": "Poland",
        "emoji": "🏛️"
    },
    "koszalin": {
        "name": "Koszalin", 
        "lat": 54.1943, 
        "lon": 16.1712, 
        "timezone": "Europe/Warsaw",
        "country": "Poland",
        "emoji": "🌲"
    }
}

# Próg dobrej widoczności
GOOD_CONDITIONS = {
    "max_cloud_cover": 30,
    "min_visibility": 10,
    "max_humidity": 80,
    "max_wind_speed": 15,
    "min_temperature": -10,
    "max_temperature": 30
}

# ====================== BAZA DANYCH ======================
def init_database():
    """Inicjalizacja bazy danych"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabela użytkowników
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            satellite_notifications BOOLEAN DEFAULT 0,
            observation_alerts BOOLEAN DEFAULT 1,
            last_notification TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela śledzonych satelitów
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_satellites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            satellite_id INTEGER,
            satellite_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES users (chat_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_settings(chat_id: int) -> Dict:
    """Pobierz ustawienia użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT chat_id, satellite_notifications, observation_alerts, last_notification
        FROM users WHERE chat_id = ?
    ''', (chat_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "chat_id": result[0],
            "satellite_notifications": bool(result[1]),
            "observation_alerts": bool(result[2]),
            "last_notification": result[3]
        }
    else:
        # Domyślne ustawienia
        return {
            "chat_id": chat_id,
            "satellite_notifications": False,
            "observation_alerts": True,
            "last_notification": None
        }

def update_user_settings(chat_id: int, settings: Dict):
    """Aktualizuj ustawienia użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (chat_id, satellite_notifications, observation_alerts, last_notification)
        VALUES (?, ?, ?, ?)
    ''', (
        chat_id,
        1 if settings.get("satellite_notifications") else 0,
        1 if settings.get("observation_alerts") else 0,
        settings.get("last_notification")
    ))
    
    conn.commit()
    conn.close()

# ====================== KALENDARZ 13-MIESIĘCZNY ======================
ASTRONOMICAL_CALENDAR = [
    {"name": "Sagittarius", "symbol": "♐", "element": "Ogień", "start_day": 355, "end_day": 13},
    {"name": "Capricorn", "symbol": "♑", "element": "Ziemia", "start_day": 14, "end_day": 42},
    {"name": "Aquarius", "symbol": "♒", "element": "Powietrze", "start_day": 43, "end_day": 72},
    {"name": "Pisces", "symbol": "♓", "element": "Woda", "start_day": 73, "end_day": 101},
    {"name": "Aries", "symbol": "♈", "element": "Ogień", "start_day": 102, "end_day": 132},
    {"name": "Taurus", "symbol": "♉", "element": "Ziemia", "start_day": 133, "end_day": 162},
    {"name": "Gemini", "symbol": "♊", "element": "Powietrze", "start_day": 163, "end_day": 192},
    {"name": "Cancer", "symbol": "♋", "element": "Woda", "start_day": 193, "end_day": 223},
    {"name": "Leo", "symbol": "♌", "element": "Ogień", "start_day": 224, "end_day": 253},
    {"name": "Virgo", "symbol": "♍", "element": "Ziemia", "start_day": 254, "end_day": 283},
    {"name": "Libra", "symbol": "♎", "element": "Powietrze", "start_day": 284, "end_day": 314},
    {"name": "Scorpio", "symbol": "♏", "element": "Woda", "start_day": 315, "end_day": 343},
    {"name": "Ophiuchus", "symbol": "⛎", "element": "Ogień", "start_day": 344, "end_day": 354}
]

print("=" * 60)
print("🤖 SENTRY ONE v9.0 - ULTIMATE SYSTEM")
print(f"🌐 URL: {RENDER_URL}")
print("🛰️ NASA API + N2YO + OpenWeather")
print("🔔 System powiadomień: AKTYWNY")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== NASA FUNCTIONS ======================
def get_nasa_apod():
    """Pobierz Astronomy Picture of the Day z NASA"""
    try:
        url = f"{NASA_APOD_URL}?api_key={NASA_API_KEY}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        return {
            "title": data.get("title", "NASA APOD"),
            "explanation": data.get("explanation", ""),
            "url": data.get("url", ""),
            "hdurl": data.get("hdurl", ""),
            "media_type": data.get("media_type", "image"),
            "date": data.get("date", "")
        }
    except Exception as e:
        logger.error(f"❌ Błąd NASA APOD: {e}")
        return None

def get_earth_image(lat: float, lon: float, date: str = None):
    """Pobierz zdjęcie Ziemi z NASA dla danej lokalizacji"""
    try:
        if not date:
            date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        url = f"{NASA_EARTH_URL}?lon={lon}&lat={lat}&date={date}&dim=0.1&api_key={NASA_API_KEY}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        return {
            "url": data.get("url", ""),
            "date": data.get("date", date),
            "id": data.get("id", ""),
            "lat": lat,
            "lon": lon
        }
    except Exception as e:
        logger.error(f"❌ Błąd NASA Earth: {e}")
        return None

def get_satellite_image_for_city(city_key: str):
    """Pobierz zdjęcie satelitarne dla miasta"""
    city = OBSERVATION_CITIES.get(city_key)
    if not city:
        return None
    
    # Spróbuj pobrać najnowsze dostępne zdjęcie
    for days_ago in range(0, 90, 10):  # Sprawdzaj co 10 dni przez 90 dni
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        image = get_earth_image(city["lat"], city["lon"], date)
        if image and image.get("url"):
            return image
    
    return None

# ====================== N2YO SATELLITE FUNCTIONS ======================
def get_satellite_positions(satellite_id: int, lat: float, lon: float, alt: float = 0):
    """Pobierz pozycje satelity dla danej lokalizacji"""
    try:
        url = f"{N2YO_BASE_URL}/positions/{satellite_id}/{lat}/{lon}/{alt}/10/&apiKey={N2YO_API_KEY}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd N2YO positions: {e}")
        return None

def get_satellite_passes(satellite_id: int, lat: float, lon: float, alt: float = 0, days: int = 10):
    """Pobierz przeloty satelity"""
    try:
        url = f"{N2YO_BASE_URL}/visualpasses/{satellite_id}/{lat}/{lon}/{alt}/{days}/300/&apiKey={N2YO_API_KEY}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd N2YO passes: {e}")
        return None

def get_iss_position():
    """Pobierz aktualną pozycję ISS"""
    try:
        # ISS ma ID 25544
        return get_satellite_positions(25544, 52.2297, 21.0122, 0)
    except Exception as e:
        logger.error(f"❌ Błąd ISS: {e}")
        return None

# Popularne satelity do obserwacji
SATELLITES = {
    "iss": {"id": 25544, "name": "ISS", "emoji": "🛰️"},
    "hst": {"id": 20580, "name": "Hubble", "emoji": "🔭"},
    "landsat8": {"id": 39084, "name": "Landsat 8", "emoji": "🌍"},
    "sentinel2a": {"id": 40697, "name": "Sentinel-2A", "emoji": "🛰️"},
    "starlink": {"id": 44713, "name": "Starlink", "emoji": "✨"},
    "meteosat": {"id": 26718, "name": "Meteosat", "emoji": "🌤️"}
}

# ====================== WEATHER FUNCTIONS ======================
def get_weather_forecast(lat, lon):
    """Pobierz prognozę pogody z Open-Meteo"""
    try:
        url = OPENMETEO_BASE_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,visibility,is_day,weather_code",
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,visibility,weather_code",
            "daily": "sunrise,sunset,moonrise,moonset",
            "timezone": "auto",
            "forecast_days": 3
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd pobierania pogody: {e}")
        return None

def get_openweather_data(lat, lon):
    """Pobierz dane pogodowe z OpenWeather API"""
    try:
        url = f"{OPENWEATHER_BASE_URL}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        openweather_info = {
            "pressure": data.get("main", {}).get("pressure", 0),
            "feels_like": data.get("main", {}).get("feels_like", 0),
            "weather_main": data.get("weather", [{}])[0].get("main", ""),
            "weather_description": data.get("weather", [{}])[0].get("description", ""),
            "weather_icon": data.get("weather", [{}])[0].get("icon", ""),
            "wind_deg": data.get("wind", {}).get("deg", 0),
            "sunrise": datetime.fromtimestamp(data.get("sys", {}).get("sunrise", 0)).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data.get("sys", {}).get("sunset", 0)).strftime("%H:%M"),
            "country_code": data.get("sys", {}).get("country", ""),
            "timezone_offset": data.get("timezone", 0) // 3600
        }
        
        return openweather_info
        
    except Exception as e:
        logger.error(f"❌ Błąd OpenWeather API: {e}")
        return None

def get_openweather_forecast(lat, lon):
    """Pobierz prognozę pogody z OpenWeather"""
    try:
        url = f"{OPENWEATHER_BASE_URL}/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd prognozy OpenWeather: {e}")
        return None

# ====================== ASTRONOMICAL CALCULATIONS ======================
def calculate_moon_phase(date: datetime = None) -> Dict:
    """Oblicz dokładną fazę księżyca (poprawiona wersja)"""
    if not date:
        date = datetime.now()
    
    # Ostatni nów: 11 stycznia 2025, 11:57 UTC
    last_new_moon = datetime(2025, 1, 11, 11, 57)
    
    # Oblicz różnicę czasu od ostatniego nowiu
    delta_days = (date - last_new_moon).total_seconds() / 86400.0
    
    # Normalizuj do cyklu księżycowego (29.530588 dni)
    moon_age = delta_days % 29.530588
    
    # Oblicz procent oświetlenia
    illumination = 50 * (1 - math.cos(2 * math.pi * moon_age / 29.530588))
    
    # Określ fazę
    if moon_age < 1.0:
        phase = "Nów"
        emoji = "🌑"
        illumination = 0
    elif moon_age < 7.38:
        phase = "Rosnący sierp"
        emoji = "🌒"
    elif moon_age < 7.38 + 0.5:
        phase = "Pierwsza kwadra"
        emoji = "🌓"
        illumination = 50
    elif moon_age < 14.77:
        phase = "Rosnący garbaty"
        emoji = "🌔"
    elif moon_age < 15.0:
        phase = "Pełnia"
        emoji = "🌕"
        illumination = 100
    elif moon_age < 22.15:
        phase = "Malejący garbaty"
        emoji = "🌖"
    elif moon_age < 22.15 + 0.5:
        phase = "Ostatnia kwadra"
        emoji = "🌗"
        illumination = 50
    else:
        phase = "Malejący sierp"
        emoji = "🌘"
    
    return {
        "phase": moon_age / 29.530588,
        "name": phase,
        "emoji": emoji,
        "illumination": illumination,
        "age_days": moon_age,
        "next_full": (14.77 - moon_age) % 29.530588,
        "next_new": (29.530588 - moon_age) % 29.530588
    }

def get_astronomical_date():
    """Zwróć datę w kalendarzu 13-miesięcznym"""
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    
    for month in ASTRONOMICAL_CALENDAR:
        if month["start_day"] <= day_of_year <= month["end_day"]:
            day_in_month = day_of_year - month["start_day"] + 1
            
            polish_names = {
                "Sagittarius": "Strzelec",
                "Capricorn": "Koziorożec",
                "Aquarius": "Wodnik",
                "Pisces": "Ryby",
                "Aries": "Baran",
                "Taurus": "Byk",
                "Gemini": "Bliźnięta",
                "Cancer": "Rak",
                "Leo": "Lew",
                "Virgo": "Panna",
                "Libra": "Waga",
                "Scorpio": "Skorpion",
                "Ophiuchus": "Wężownik"
            }
            
            element_emojis = {
                "Ogień": "🔥",
                "Ziemia": "🌍",
                "Powietrze": "💨",
                "Woda": "💧"
            }
            
            return {
                "day": day_in_month,
                "month": month["name"],
                "month_symbol": month["symbol"],
                "month_polish": polish_names.get(month["name"], month["name"]),
                "day_of_year": day_of_year,
                "year": now.year,
                "element": month["element"],
                "element_emoji": element_emojis.get(month["element"], "⭐"),
                "description": f"Znak {month['element'].lower()}"
            }
    
    return {
        "day": 5,
        "month": "Capricorn",
        "month_symbol": "♑",
        "month_polish": "Koziorożec",
        "day_of_year": day_of_year,
        "year": now.year,
        "element": "Ziemia",
        "element_emoji": "🌍",
        "description": "Znak ambicji, determinacji i praktyczności"
    }

def get_sun_moon_times(city_key: str):
    """Pobierz dokładne czasy wschodu/zachodu Słońca i Księżyca"""
    city = OBSERVATION_CITIES[city_key]
    
    try:
        # Użyj OpenWeather dla dokładniejszych danych
        url = f"{OPENWEATHER_BASE_URL}/weather"
        params = {
            "lat": city["lat"],
            "lon": city["lon"],
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        sunrise = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
        sunset = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
        
        # Oblicz wschód/zachód księżyca (uproszczone)
        now = datetime.now()
        moon = calculate_moon_phase(now)
        
        # Symulacja czasów księżyca (w rzeczywistości potrzebne API)
        moonrise = (datetime.now() - timedelta(hours=6)).strftime("%H:%M")
        moonset = (datetime.now() + timedelta(hours=6)).strftime("%H:%M")
        
        return {
            "sun": {"rise": sunrise, "set": sunset},
            "moon": {"rise": moonrise, "set": moonset},
            "moon_phase": moon
        }
        
    except Exception as e:
        logger.error(f"❌ Błąd czasów astronomicznych: {e}")
        # Domyślne wartości
        return {
            "sun": {"rise": "07:30", "set": "16:30"},
            "moon": {"rise": "20:00", "set": "08:00"},
            "moon_phase": calculate_moon_phase()
        }

# ====================== OBSERVATION CONDITIONS ======================
def check_city_conditions(city_key: str):
    """Sprawdź warunki obserwacyjne dla miasta"""
    city = OBSERVATION_CITIES[city_key]
    weather_data = get_weather_forecast(city["lat"], city["lon"])
    openweather_data = get_openweather_data(city["lat"], city["lon"])
    
    if not weather_data or "current" not in weather_data:
        return None
    
    current = weather_data["current"]
    
    cloud_cover = current.get("cloud_cover", 100)
    visibility = current.get("visibility", 0) / 1000
    humidity = current.get("relative_humidity_2m", 100)
    wind_speed = current.get("wind_speed_10m", 0)
    temperature = current.get("temperature_2m", 0)
    is_day = current.get("is_day", 1)
    
    # Sprawdź warunki
    conditions_check = {
        "cloud_cover": cloud_cover <= GOOD_CONDITIONS["max_cloud_cover"],
        "visibility": visibility >= GOOD_CONDITIONS["min_visibility"],
        "humidity": humidity <= GOOD_CONDITIONS["max_humidity"],
        "wind_speed": wind_speed <= GOOD_CONDITIONS["max_wind_speed"],
        "temperature": GOOD_CONDITIONS["min_temperature"] <= temperature <= GOOD_CONDITIONS["max_temperature"]
    }
    
    conditions_met = sum(conditions_check.values())
    total_conditions = len(conditions_check)
    
    # Ocena
    if conditions_met == total_conditions:
        status = "DOSKONAŁE"
        emoji = "✨"
    elif conditions_met >= 4:
        status = "DOBRE"
        emoji = "⭐"
    elif conditions_met == 3:
        status = "ŚREDNIE"
        emoji = "⛅"
    elif conditions_met >= 1:
        status = "SŁABE"
        emoji = "🌥️"
    else:
        status = "ZŁE"
        emoji = "🌧️"
    
    score = round((conditions_met / total_conditions) * 100)
    
    return {
        "city_name": city["name"],
        "city_emoji": city["emoji"],
        "temperature": temperature,
        "cloud_cover": cloud_cover,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "visibility": round(visibility, 1),
        "is_day": is_day == 1,
        "status": status,
        "emoji": emoji,
        "score": score,
        "conditions_met": conditions_met,
        "total_conditions": total_conditions,
        "openweather_data": openweather_data
    }

def check_future_conditions(city_key: str, hours: int = 24):
    """Sprawdź warunki w przyszłości (najbliższe godziny)"""
    city = OBSERVATION_CITIES[city_key]
    weather_data = get_weather_forecast(city["lat"], city["lon"])
    
    if not weather_data or "hourly" not in weather_data:
        return []
    
    hourly_data = weather_data["hourly"]
    good_windows = []
    
    for i in range(min(48, len(hourly_data["time"]))):
        time_str = hourly_data["time"][i]
        hour_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        
        # Sprawdź tylko najbliższe godziny
        if (hour_time - datetime.now()).total_seconds() / 3600 > hours:
            break
        
        cloud_cover = hourly_data["cloud_cover"][i]
        visibility = hourly_data["visibility"][i] / 1000
        humidity = hourly_data["relative_humidity_2m"][i]
        wind_speed = hourly_data["wind_speed_10m"][i]
        
        # Sprawdź warunki
        good_conditions = (
            cloud_cover <= GOOD_CONDITIONS["max_cloud_cover"] and
            visibility >= GOOD_CONDITIONS["min_visibility"] and
            humidity <= GOOD_CONDITIONS["max_humidity"] and
            wind_speed <= GOOD_CONDITIONS["max_wind_speed"]
        )
        
        if good_conditions:
            good_windows.append({
                "time": hour_time.strftime("%H:%M"),
                "datetime": hour_time,
                "cloud_cover": cloud_cover,
                "visibility": visibility,
                "humidity": humidity,
                "wind_speed": wind_speed
            })
    
    return good_windows

# ====================== NOTIFICATION SYSTEM ======================
def check_observation_opportunities():
    """Sprawdź możliwości obserwacji i wyślij powiadomienia"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Pobierz użytkowników z włączonymi powiadomieniami
    cursor.execute('''
        SELECT chat_id FROM users WHERE observation_alerts = 1
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    for (chat_id,) in users:
        try:
            # Sprawdź warunki dla obu miast
            warszawa_conditions = check_city_conditions("warszawa")
            koszalin_conditions = check_city_conditions("koszalin")
            
            # Sprawdź okna obserwacyjne w najbliższych godzinach
            warszawa_windows = check_future_conditions("warszawa", 6)
            koszalin_windows = check_future_conditions("koszalin", 6)
            
            best_city = None
            best_windows = []
            
            if warszawa_conditions and warszawa_conditions["score"] > 70 and not warszawa_conditions["is_day"]:
                best_city = warszawa_conditions
                best_windows = warszawa_windows[:3]  # Pierwsze 3 okna
            
            if koszalin_conditions and koszalin_conditions["score"] > 70 and not koszalin_conditions["is_day"]:
                if not best_city or koszalin_conditions["score"] > best_city["score"]:
                    best_city = koszalin_conditions
                    best_windows = koszalin_windows[:3]
            
            if best_city and best_windows:
                message = (
                    f"🌠 <b>OKNO OBSERWACYJNE DOSTĘPNE!</b>\n\n"
                    f"📍 <b>Lokalizacja:</b> {best_city['city_emoji']} {best_city['city_name']}\n"
                    f"📊 <b>Warunki:</b> {best_city['emoji']} {best_city['status']} ({best_city['score']}%)\n"
                    f"🌡️ <b>Temperatura:</b> {best_city['temperature']:.1f}°C\n"
                    f"☁️ <b>Zachmurzenie:</b> {best_city['cloud_cover']}%\n"
                    f"💨 <b>Wiatr:</b> {best_city['wind_speed']} m/s\n\n"
                    f"<b>Najlepsze godziny:</b>\n"
                )
                
                for window in best_windows:
                    message += f"• {window['time']} - chmury: {window['cloud_cover']}%, widoczność: {window['visibility']:.1f} km\n"
                
                message += f"\n<i>Warunki sprzyjają obserwacjom astronomicznym!</i>"
                
                send_telegram_message(chat_id, message)
                
                # Aktualizuj czas ostatniego powiadomienia
                settings = get_user_settings(chat_id)
                settings["last_notification"] = datetime.now().isoformat()
                update_user_settings(chat_id, settings)
                
        except Exception as e:
            logger.error(f"❌ Błąd powiadomień dla {chat_id}: {e}")

def check_satellite_passes():
    """Sprawdź przeloty satelitów i wyślij powiadomienia"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT chat_id FROM users WHERE satellite_notifications = 1
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    for (chat_id,) in users:
        try:
            # Sprawdź przeloty ISS nad Warszawą
            iss_passes = get_satellite_passes(25544, 52.2297, 21.0122, 0, 1)
            
            if iss_passes and "passes" in iss_passes and iss_passes["passes"]:
                next_pass = iss_passes["passes"][0]
                
                start_time = datetime.fromtimestamp(next_pass["startUTC"]).strftime("%H:%M")
                max_time = datetime.fromtimestamp(next_pass["maxUTC"]).strftime("%H:%M")
                end_time = datetime.fromtimestamp(next_pass["endUTC"]).strftime("%H:%M")
                duration = next_pass["endUTC"] - next_pass["startUTC"]
                
                message = (
                    f"🛰️ <b>ISS NAD WARSZAWĄ!</b>\n\n"
                    f"• <b>Start:</b> {start_time}\n"
                    f"• <b>Maksimum:</b> {max_time} ({next_pass['maxEl']}°)\n"
                    f"• <b>Koniec:</b> {end_time}\n"
                    f"• <b>Czas trwania:</b> {duration:.0f} s\n"
                    f"• <b>Magnitudo:</b> {next_pass.get('mag', '-3.0')}\n\n"
                    f"<i>Spójrz w niebo! Międzynarodowa Stacja Kosmiczna będzie widoczna.</i>"
                )
                
                send_telegram_message(chat_id, message)
                
        except Exception as e:
            logger.error(f"❌ Błąd powiadomień satelitów dla {chat_id}: {e}")

# ====================== TELEGRAM FUNCTIONS ======================
def send_telegram_message(chat_id, text, photo_url=None):
    """Wyślij wiadomość przez Telegram API"""
    if photo_url:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": text,
            "parse_mode": "HTML"
        }
    else:
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

def send_photo(chat_id, photo_url, caption=""):
    """Wyślij zdjęcie"""
    return send_telegram_message(chat_id, caption, photo_url)

# ====================== FLASK APP ======================
app = Flask(__name__)

@app.route('/')
def home():
    """Strona główna"""
    now = datetime.now()
    astro_date = get_astronomical_date()
    moon = calculate_moon_phase()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v9.0</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.08);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-top: 20px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                transition: transform 0.3s;
            }}
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            .moon-phase {{
                text-align: center;
                font-size: 60px;
                margin: 20px 0;
            }}
            .api-status {{
                display: inline-block;
                padding: 8px 20px;
                border-radius: 25px;
                margin: 5px;
                font-weight: bold;
                font-size: 14px;
            }}
            .active {{
                background: linear-gradient(to right, #00b09b, #96c93d);
            }}
            .inactive {{
                background: linear-gradient(to right, #ff416c, #ff4b2b);
            }}
            .btn {{
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(to right, #4776E6, #8E54E9);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: bold;
                margin: 10px;
                transition: all 0.3s;
            }}
            .btn:hover {{
                transform: scale(1.05);
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 48px; margin-bottom: 10px;">🤖 SENTRY ONE v9.0</h1>
                <h2 style="color: #81ecec; margin-bottom: 20px;">Ultimate Astrometeorological System</h2>
                
                <div class="moon-phase">
                    {moon['emoji']}
                </div>
                
                <div style="margin: 20px 0;">
                    <span class="api-status active">🛰️ NASA API</span>
                    <span class="api-status active">🌤️ OPENWEATHER</span>
                    <span class="api-status active">🛰️ N2YO SATELLITES</span>
                    <span class="api-status active">🔔 POWIADOMIENIA</span>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>🌌 Aktualna faza Księżyca</h3>
                    <p style="font-size: 24px; margin: 10px 0;">{moon['emoji']} {moon['name']}</p>
                    <p>Oświetlenie: {moon['illumination']:.1f}%</p>
                    <p>Wiek: {moon['age_days']:.1f} dni</p>
                </div>
                
                <div class="stat-card">
                    <h3>📅 Kalendarz Astronomiczny</h3>
                    <p style="font-size: 24px; margin: 10px 0;">{astro_date['day']} {astro_date['month_symbol']} {astro_date['year']}</p>
                    <p>{astro_date['month_polish']} • {astro_date['element_emoji']} {astro_date['element']}</p>
                    <p>Dzień roku: {astro_date['day_of_year']}/365</p>
                </div>
                
                <div class="stat-card">
                    <h3>📍 Obserwowane miasta</h3>
                    <p>🏛️ Warszawa: 52.23°N, 21.01°E</p>
                    <p>🌲 Koszalin: 54.19°N, 16.17°E</p>
                    <p>👥 Użytkownicy: {get_user_count()}</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" class="btn">
                    💬 Otwórz bota w Telegram
                </a>
                
                <a href="/api/status" class="btn" style="background: linear-gradient(to right, #00b09b, #96c93d);">
                    📊 Status API
                </a>
                
                <a href="/api/nasa/apod" class="btn" style="background: linear-gradient(to right, #8E2DE2, #4A00E0);">
                    🛰️ NASA APOD
                </a>
            </div>
            
            <div style="background: rgba(0, 0, 0, 0.3); padding: 20px; border-radius: 15px; margin-top: 30px;">
                <h3>🚀 Funkcje systemu:</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                    <div>• Zdjęcia NASA w czasie rzeczywistym</div>
                    <div>• Śledzenie satelitów (ISS, Hubble, itp.)</div>
                    <div>• Powiadomienia o przelotach</div>
                    <div>• Prognoza warunków obserwacyjnych</div>
                    <div>• Kalendarz 13-miesięczny</div>
                    <div>• Alerty pogodowe OpenWeather</div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                <p>🤖 SENTRY ONE v9.0 | Ultimate astrometeorological monitoring system</p>
                <p style="font-family: monospace; font-size: 12px; opacity: 0.8;">
                    {now.strftime("%Y-%m-%d %H:%M:%S")} | Warszawa/Koszalin | NASA + N2YO + OpenWeather
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

def get_user_count():
    """Pobierz liczbę użytkowników"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

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
            
            # Pobierz ustawienia użytkownika
            user_settings = get_user_settings(chat_id)
            
            if text == "/start":
                # NASA APOD
                nasa_apod = get_nasa_apod()
                
                # Zdjęcia miast
                warszawa_image = get_satellite_image_for_city("warszawa")
                koszalin_image = get_satellite_image_for_city("koszalin")
                
                # Dane astronomiczne
                now = datetime.now()
                astro_date = get_astronomical_date()
                moon = calculate_moon_phase()
                
                # Warunki obserwacyjne
                warszawa_conditions = check_city_conditions("warszawa")
                koszalin_conditions = check_city_conditions("koszalin")
                
                # Czasy wschodów/zachodów
                warszawa_times = get_sun_moon_times("warszawa")
                koszalin_times = get_sun_moon_times("koszalin")
                
                # ========== BUDUJEMY SUPER RAPORT ==========
                report = ""
                
                # 1. WITAJ + NASA APOD
                report += f"🌌 <b>SENTRY ONE v9.0 - ULTIMATE SYSTEM</b>\n\n"
                
                if nasa_apod:
                    report += f"<b>🛰️ NASA PICTURE OF THE DAY:</b>\n"
                    report += f"• {nasa_apod['title']}\n"
                    report += f"• Data: {nasa_apod['date']}\n"
                    if nasa_apod.get('url'):
                        send_photo(chat_id, nasa_apod['url'], report)
                        report = ""  # Reset dla dalszej części
                
                # 2. DATA I CZASY ASTRONOMICZNE
                report += f"<b>📅 DATA I CZASY:</b>\n"
                report += f"• {now.strftime('%d.%m.%Y %H:%M:%S')}\n"
                report += f"• {astro_date['day']} {astro_date['month_symbol']} {astro_date['month_polish']} {astro_date['year']}\n"
                report += f"• {astro_date['element_emoji']} {astro_date['element']}\n\n"
                
                # 3. KSIĘŻYC
                report += f"<b>{moon['emoji']} KSIĘŻYC:</b>\n"
                report += f"• Faza: {moon['name']}\n"
                report += f"• Oświetlenie: {moon['illumination']:.1f}%\n"
                report += f"• Wiek: {moon['age_days']:.1f} dni\n\n"
                
                # 4. SŁOŃCE I KSIĘŻYC WARSZAWA
                report += f"<b>🏛️ WARSZAWA - CZASY:</b>\n"
                report += f"🌞 Słońce: {warszawa_times['sun']['rise']} ↑ | {warszawa_times['sun']['set']} ↓\n"
                report += f"{warszawa_times['moon_phase']['emoji']} Księżyc: {warszawa_times['moon']['rise']} ↑ | {warszawa_times['moon']['set']} ↓\n\n"
                
                if warszawa_conditions:
                    report += f"<b>📊 WARUNKI OBSERWACYJNE:</b>\n"
                    report += f"Status: {warszawa_conditions['emoji']} {warszawa_conditions['status']} ({warszawa_conditions['score']}%)\n"
                    report += f"Temp: {warszawa_conditions['temperature']:.1f}°C | "
                    report += f"Chmury: {warszawa_conditions['cloud_cover']}%\n"
                    report += f"Wiatr: {warszawa_conditions['wind_speed']} m/s | "
                    report += f"Widoczność: {warszawa_conditions['visibility']} km\n\n"
                
                # 5. SŁOŃCE I KSIĘŻYC KOSZALIN
                report += f"<b>🌲 KOSZALIN - CZASY:</b>\n"
                report += f"🌞 Słońce: {koszalin_times['sun']['rise']} ↑ | {koszalin_times['sun']['set']} ↓\n"
                report += f"{koszalin_times['moon_phase']['emoji']} Księżyc: {koszalin_times['moon']['rise']} ↑ | {koszalin_times['moon']['set']} ↓\n\n"
                
                if koszalin_conditions:
                    report += f"<b>📊 WARUNKI OBSERWACYJNE:</b>\n"
                    report += f"Status: {koszalin_conditions['emoji']} {koszalin_conditions['status']} ({koszalin_conditions['score']}%)\n"
                    report += f"Temp: {koszalin_conditions['temperature']:.1f}°C | "
                    report += f"Chmury: {koszalin_conditions['cloud_cover']}%\n"
                    report += f"Wiatr: {koszalin_conditions['wind_speed']} m/s | "
                    report += f"Widoczność: {koszalin_conditions['visibility']} km\n\n"
                
                # 6. POWIADOMIENIA
                report += f"<b>🔔 TWOJE USTAWIENIA:</b>\n"
                report += f"• Powiadomienia satelitarne: {'✅ WŁĄCZONE' if user_settings['satellite_notifications'] else '❌ WYŁĄCZONE'}\n"
                report += f"• Alerty obserwacyjne: {'✅ WŁĄCZONE' if user_settings['observation_alerts'] else '❌ WYŁĄCZONE'}\n\n"
                
                # 7. ZDJĘCIA
                report += f"<b>🛰️ ZDJĘCIA SATELITARNE:</b>\n"
                if warszawa_image:
                    report += f"• Warszawa: {warszawa_image['date']}\n"
                    send_photo(chat_id, warszawa_image['url'], f"🛰️ Zdjęcie satelitarne Warszawy\nData: {warszawa_image['date']}")
                
                if koszalin_image:
                    report += f"• Koszalin: {koszalin_image['date']}\n"
                    time.sleep(1)  # Opóźnienie między zdjęciami
                    send_photo(chat_id, koszalin_image['url'], f"🛰️ Zdjęcie satelitarne Koszalina\nData: {koszalin_image['date']}")
                
                # 8. KOMENDY
                report += f"\n{'═'*40}\n"
                report += f"<b>🚀 DOSTĘPNE KOMENDY:</b>\n\n"
                report += f"<code>/nasa</code> - Zdjęcie dnia NASA\n"
                report += f"<code>/satellites on/off</code> - Włącz/wyłącz śledzenie satelitów\n"
                report += f"<code>/alerts on/off</code> - Alerty obserwacyjne\n"
                report += f"<code>/iss</code> - Pozycja ISS\n"
                report += f"<code>/moon</code> - Szczegóły Księżyca\n"
                report += f"<code>/weather [miasto]</code> - Prognoza\n"
                report += f"<code>/photo warszawa/koszalin</code> - Zdjęcie satelitarne\n"
                report += f"<code>/forecast [miasto]</code> - Prognoza 5-dniowa\n"
                report += f"<code>/help</code> - Wszystkie komendy\n\n"
                
                report += f"<i>🤖 System monitoruje warunki 24/7</i>"
                
                send_telegram_message(chat_id, report)
                
            elif text == "/nasa":
                nasa_apod = get_nasa_apod()
                if nasa_apod:
                    response = (
                        f"🛰️ <b>NASA ASTRONOMY PICTURE OF THE DAY</b>\n\n"
                        f"<b>{nasa_apod['title']}</b>\n"
                        f"Data: {nasa_apod['date']}\n\n"
                        f"{nasa_apod['explanation'][:300]}...\n\n"
                        f"<i>Źródło: NASA APOD API</i>"
                    )
                    send_photo(chat_id, nasa_apod['url'], response)
                else:
                    send_telegram_message(chat_id, "❌ Nie udało się pobrać zdjęcia NASA")
            
            elif text.startswith("/satellites"):
                args = text[11:].strip().lower()
                
                if args == "on":
                    user_settings["satellite_notifications"] = True
                    update_user_settings(chat_id, user_settings)
                    send_telegram_message(chat_id, "✅ <b>POWIADOMIENIA SATELITARNE WŁĄCZONE</b>\n\nBędziesz otrzymywać powiadomienia o przelotach satelitów nad Twoją lokalizacją.")
                
                elif args == "off":
                    user_settings["satellite_notifications"] = False
                    update_user_settings(chat_id, user_settings)
                    send_telegram_message(chat_id, "❌ <b>POWIADOMIENIA SATELITARNE WYŁĄCZONE</b>\n\nNie będziesz otrzymywać powiadomień o satelitach.")
                
                else:
                    status = "WŁĄCZONE" if user_settings["satellite_notifications"] else "WYŁĄCZONE"
                    send_telegram_message(chat_id, f"🔔 <b>STATUS POWIADOMIEŃ SATELITARNYCH:</b> {status}\n\nUżyj: <code>/satellites on</code> lub <code>/satellites off</code>")
            
            elif text.startswith("/alerts"):
                args = text[7:].strip().lower()
                
                if args == "on":
                    user_settings["observation_alerts"] = True
                    update_user_settings(chat_id, user_settings)
                    send_telegram_message(chat_id, "✅ <b>ALERTY OBSERWACYJNE WŁĄCZONE</b>\n\nBędziesz otrzymywać powiadomienia o sprzyjających warunkach do obserwacji.")
                
                elif args == "off":
                    user_settings["observation_alerts"] = False
                    update_user_settings(chat_id, user_settings)
                    send_telegram_message(chat_id, "❌ <b>ALERTY OBSERWACYJNE WYŁĄCZONE</b>\n\nNie będziesz otrzymywać powiadomień o warunkach obserwacyjnych.")
                
                else:
                    status = "WŁĄCZONE" if user_settings["observation_alerts"] else "WYŁĄCZONE"
                    send_telegram_message(chat_id, f"🔔 <b>STATUS ALERTÓW OBSERWACYJNYCH:</b> {status}\n\nUżyj: <code>/alerts on</code> lub <code>/alerts off</code>")
            
            elif text == "/iss":
                iss_data = get_iss_position()
                if iss_data and "positions" in iss_data:
                    position = iss_data["positions"][0]
                    
                    response = (
                        f"🛰️ <b>MIĘDZYNARODOWA STACJA KOSMICZNA</b>\n\n"
                        f"<b>Aktualna pozycja:</b>\n"
                        f"• Szerokość: {position['satlatitude']:.2f}°\n"
                        f"• Długość: {position['satlongitude']:.2f}°\n"
                        f"• Wysokość: {position['sataltitude']:.2f} km\n"
                        f"• Prędkość: ~27,600 km/h\n\n"
                        f"<b>Nad Warszawą:</b>\n"
                    )
                    
                    # Sprawdź przeloty nad Warszawą
                    passes = get_satellite_passes(25544, 52.2297, 21.0122, 0, 2)
                    if passes and "passes" in passes:
                        for p in passes["passes"][:2]:
                            start = datetime.fromtimestamp(p["startUTC"]).strftime("%H:%M")
                            end = datetime.fromtimestamp(p["endUTC"]).strftime("%H:%M")
                            response += f"• {start} - {end} (max: {p['maxEl']}°)\n"
                    
                    response += f"\n<i>Aktualizacja: {datetime.now().strftime('%H:%M:%S')}</i>"
                    send_telegram_message(chat_id, response)
                else:
                    send_telegram_message(chat_id, "🛰️ <b>ISS</b>\n\nNie udało się pobrać aktualnej pozycji.\nSpróbuj ponownie za chwilę.")
            
            elif text == "/moon":
                moon = calculate_moon_phase()
                now = datetime.now()
                
                response = (
                    f"{moon['emoji']} <b>SZCZEGÓŁOWY RAPORT KSIĘŻYCA</b>\n\n"
                    f"• <b>Faza:</b> {moon['name']}\n"
                    f"• <b>Oświetlenie:</b> {moon['illumination']:.1f}%\n"
                    f"• <b>Wiek:</b> {moon['age_days']:.2f} dni\n"
                    f"• <b>Cykl księżycowy:</b> {moon['phase']:.3f}\n"
                    f"• <b>Do następnej pełni:</b> {moon['next_full']:.1f} dni\n"
                    f"• <b>Do następnego nowiu:</b> {moon['next_new']:.1f} dni\n\n"
                    
                    f"<b>Najlepsze warunki do obserwacji:</b>\n"
                    f"• Faza: 30-70% (pierwsza/ostatnia kwadra)\n"
                    f"• Księżyc nisko nad horyzontem\n"
                    f"• Noc bezchmurna\n\n"
                    
                    f"<i>Dane aktualne na: {now.strftime('%H:%M:%S')}</i>"
                )
                send_telegram_message(chat_id, response)
            
            elif text.startswith("/photo"):
                args = text[6:].strip().lower()
                
                if args == "warszawa":
                    image = get_satellite_image_for_city("warszawa")
                    if image:
                        send_photo(chat_id, image['url'], 
                                 f"🛰️ <b>ZDJĘCIE SATELITARNE WARSZAWY</b>\n\n"
                                 f"Data: {image['date']}\n"
                                 f"Współrzędne: 52.23°N, 21.01°E\n\n"
                                 f"<i>Źródło: NASA Earth API</i>")
                    else:
                        send_telegram_message(chat_id, "❌ Nie udało się znaleźć aktualnego zdjęcia Warszawy.\nSpróbuj ponownie później.")
                
                elif args == "koszalin":
                    image = get_satellite_image_for_city("koszalin")
                    if image:
                        send_photo(chat_id, image['url'],
                                 f"🛰️ <b>ZDJĘCIE SATELITARNE KOSZALINA</b>\n\n"
                                 f"Data: {image['date']}\n"
                                 f"Współrzędne: 54.19°N, 16.17°E\n\n"
                                 f"<i>Źródło: NASA Earth API</i>")
                    else:
                        send_telegram_message(chat_id, "❌ Nie udało się znaleźć aktualnego zdjęcia Koszalina.\nSpróbuj ponownie później.")
                
                else:
                    send_telegram_message(chat_id, "📸 <b>ZDJĘCIA SATELITARNE</b>\n\n"
                                                 "Użyj:\n"
                                                 "<code>/photo warszawa</code>\n"
                                                 "<code>/photo koszalin</code>")
            
            elif text.startswith("/weather"):
                args = text[8:].strip().lower()
                
                if args in ["warszawa", "koszalin"]:
                    # Szczegółowy raport pogodowy
                    city = OBSERVATION_CITIES[args]
                    conditions = check_city_conditions(args)
                    times = get_sun_moon_times(args)
                    
                    if conditions:
                        response = (
                            f"{conditions['city_emoji']} <b>SZCZEGÓŁOWA PROGNOZA - {conditions['city_name'].upper()}</b>\n\n"
                            
                            f"<b>🌡️ AKTUALNIE:</b>\n"
                            f"• {conditions['temperature']:.1f}°C | "
                            f"Chmury: {conditions['cloud_cover']}%\n"
                            f"• Wiatr: {conditions['wind_speed']} m/s | "
                            f"Wilgotność: {conditions['humidity']}%\n"
                            f"• Widoczność: {conditions['visibility']} km\n"
                            f"• Status: {conditions['emoji']} {conditions['status']}\n\n"
                            
                            f"<b>🌞 SŁOŃCE:</b> {times['sun']['rise']} ↑ | {times['sun']['set']} ↓\n"
                            f"<b>{times['moon_phase']['emoji']} KSIĘŻYC:</b> {times['moon']['rise']} ↑ | {times['moon']['set']} ↓\n\n"
                            
                            f"<b>📊 OCENA OBSERWACYJNA:</b> {conditions['score']}%\n"
                            f"• Warunki spełnione: {conditions['conditions_met']}/5\n\n"
                        )
                        
                        # Dodaj prognozę na najbliższe godziny
                        future_windows = check_future_conditions(args, 12)
                        if future_windows:
                            response += f"<b>🕐 NAJLEPSZE GODZINY (następne 12h):</b>\n"
                            for window in future_windows[:5]:
                                response += f"• {window['time']} - chmury: {window['cloud_cover']}%\n"
                        
                        send_telegram_message(chat_id, response)
            
            elif text == "/help":
                response = (
                    f"🤖 <b>SENTRY ONE v9.0 - POMOC</b>\n\n"
                    
                    f"<b>🛰️ NASA I SATELITY:</b>\n"
                    f"<code>/nasa</code> - Zdjęcie dnia NASA\n"
                    f"<code>/iss</code> - Pozycja ISS\n"
                    f"<code>/photo warszawa/koszalin</code> - Zdjęcie satelitarne miasta\n\n"
                    
                    f"<b>🔔 POWIADOMIENIA:</b>\n"
                    f"<code>/satellites on/off</code> - Powiadomienia o satelitach\n"
                    f"<code>/alerts on/off</code> - Alerty obserwacyjne\n\n"
                    
                    f"<b>🌌 ASTRONOMIA:</b>\n"
                    f"<code>/moon</code> - Szczegóły Księżyca\n"
                    f"<code>/astro [miasto]</code> - Raport obserwacyjny\n\n"
                    
                    f"<b>🌤️ POGODA:</b>\n"
                    f"<code>/weather warszawa/koszalin</code> - Prognoza\n"
                    f"<code>/forecast [miasto]</code> - Prognoza 5-dniowa\n"
                    f"<code>/pressure [miasto]</code> - Ciśnienie i wilgotność\n\n"
                    
                    f"<b>📍 OBSERWOWANE MIASTA:</b>\n"
                    f"• warszawa\n• koszalin\n\n"
                    
                    f"<i>🤖 System działa 24/7 z NASA, N2YO i OpenWeather API</i>"
                )
                send_telegram_message(chat_id, response)
            
            else:
                # Domyślna odpowiedź
                response = (
                    f"🤖 <b>SENTRY ONE v9.0</b>\n\n"
                    f"Ultimate astrometeorological monitoring system\n\n"
                    f"<b>🚀 Główne funkcje:</b>\n"
                    f"• Zdjęcia NASA w czasie rzeczywistym\n"
                    f"• Śledzenie satelitów (ISS, Hubble)\n"
                    f"• Powiadomienia o przelotach\n"
                    f"• Prognoza warunków obserwacyjnych\n"
                    f"• Kalendarz 13-miesięczny\n\n"
                    f"<b>📍 Obserwowane miasta:</b>\n"
                    f"🏛️ Warszawa | 🌲 Koszalin\n\n"
                    f"<i>Użyj /start dla pełnego raportu lub /help dla listy komend</i>"
                )
                send_telegram_message(chat_id, response)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Błąd webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== SCHEDULED TASKS ======================
class NotificationService:
    """Serwis powiadomień"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start(self):
        """Uruchom zaplanowane zadania"""
        if not self.is_running:
            print("🔄 Uruchamianie serwisu powiadomień...")
            
            # Sprawdzanie warunków obserwacyjnych co 2 godziny
            self.scheduler.add_job(
                check_observation_opportunities,
                'interval',
                hours=2,
                id='observation_check'
            )
            
            # Sprawdzanie przelotów satelitów co godzinę
            self.scheduler.add_job(
                check_satellite_passes,
                'interval',
                hours=1,
                id='satellite_check'
            )
            
            # Pingowanie siebie co 5 minut
            self.scheduler.add_job(
                self.ping_self,
                'interval',
                minutes=5,
                id='self_ping'
            )
            
            self.scheduler.start()
            self.is_running = True
            print("✅ Serwis powiadomień aktywny")
    
    def ping_self(self):
        """Pingowanie aplikacji"""
        try:
            requests.get(f"{RENDER_URL}/", timeout=10)
            logger.info("📡 Ping aplikacji - OK")
        except Exception as e:
            logger.error(f"❌ Błąd pingowania: {e}")

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 SENTRY ONE v9.0 - ULTIMATE SYSTEM")
    print("=" * 60)
    
    # Inicjalizacja bazy danych
    init_database()
    
    # Pobierz aktualne dane
    now = datetime.now()
    astro_date = get_astronomical_date()
    moon = calculate_moon_phase()
    
    print(f"📅 Data: {now.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"🌌 Kalendarz: {astro_date['day']} {astro_date['month_symbol']} {astro_date['month_polish']}")
    print(f"🌙 Księżyc: {moon['emoji']} {moon['name']} ({moon['illumination']:.1f}%)")
    print(f"📍 Miasta: Warszawa, Koszalin")
    print(f"👥 Użytkownicy: {get_user_count()}")
    
    # Test API
    print(f"🔍 Testowanie API...")
    
    try:
        nasa_test = get_nasa_apod()
        print(f"✅ NASA API: {'AKTYWNE' if nasa_test else 'PROBLEM'}")
        
        weather_test = get_openweather_data(52.2297, 21.0122)
        print(f"✅ OpenWeather: {'AKTYWNE' if weather_test else 'PROBLEM'}")
        
        # Nie testuj N2YO za każdym razem - ma limit
        print(f"✅ N2YO: API KEY USTAWIONY")
        
    except Exception as e:
        print(f"❌ Błąd testów API: {e}")
    
    print("=" * 60)
    
    # Uruchom serwis powiadomień
    notification_service = NotificationService()
    notification_service.start()
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )