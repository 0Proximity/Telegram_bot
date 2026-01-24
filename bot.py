#!/usr/bin/env python3
"""
🌌 COSMOS SENTRY v2.0 - Zaawansowany system astrometeorologiczny z pełnymi prognozami i śledzeniem satelit
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
from typing import Dict, List, Optional

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
    },
    "gdansk": {
        "name": "Gdańsk",
        "lat": 54.3520,
        "lon": 18.6466,
        "emoji": "⚓",
        "timezone": "Europe/Warsaw"
    },
    "wroclaw": {
        "name": "Wrocław",
        "lat": 51.1079,
        "lon": 17.0385,
        "emoji": "🌉",
        "timezone": "Europe/Warsaw"
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

# Satelity do śledzenia
SATELLITES = {
    "iss": {
        "name": "Międzynarodowa Stacja Kosmiczna",
        "id": 25544,
        "emoji": "🛰️",
        "description": "Największy sztuczny satelita na orbicie"
    },
    "hst": {
        "name": "Teleskop Hubble'a",
        "id": 20580,
        "emoji": "🔭",
        "description": "Kosmiczny teleskop optyczny"
    },
    "landsat8": {
        "name": "Landsat 8",
        "id": 39084,
        "emoji": "🌍",
        "description": "Satelita obserwacji Ziemi"
    },
    "sentinel2a": {
        "name": "Sentinel-2A",
        "id": 40697,
        "emoji": "🛰️",
        "description": "Satelita programu Copernicus"
    },
    "tiangong": {
        "name": "Tiangong (Chińska stacja)",
        "id": 48274,
        "emoji": "🇨🇳",
        "description": "Chińska stacja kosmiczna"
    },
    "starlink": {
        "name": "Starlink",
        "id": 45917,
        "emoji": "🛰️",
        "description": "Konstelacja satelitów SpaceX"
    }
}

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

def get_5day_forecast(lat: float, lon: float) -> Optional[List]:
    """Pobierz pełną prognozę 5-dniową"""
    try:
        url = f"{OPENWEATHER_URL}/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl",
            "cnt": 40  # 5 dni * 8 prognoz na dzień
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            logger.error(f"OpenWeather 5-day error: {data}")
            return None
        
        # Grupuj prognozy według dni
        daily_forecasts = {}
        for item in data["list"]:
            dt = datetime.fromtimestamp(item["dt"])
            day_key = dt.strftime("%d.%m")  # Klucz w formacie DD.MM
            
            if day_key not in daily_forecasts:
                daily_forecasts[day_key] = []
            
            daily_forecasts[day_key].append({
                "time": dt.strftime("%H:%M"),
                "temp": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "description": item["weather"][0]["description"],
                "icon": item["weather"][0]["icon"],
                "humidity": item["main"]["humidity"],
                "pressure": item["main"]["pressure"],
                "wind_speed": item["wind"]["speed"],
                "wind_deg": item["wind"].get("deg", 0)
            })
        
        # Przekształć na listę 5 dni
        forecast_list = []
        for idx, (day, periods) in enumerate(daily_forecasts.items()):
            if idx >= 5:  # Maksymalnie 5 dni
                break
            
            # Weź 3 okresy z każdego dnia (rano, popołudnie, wieczór)
            selected_periods = []
            for period in periods:
                hour = int(period["time"].split(":")[0])
                if hour in [6, 12, 18] or (hour == 0 and len(selected_periods) < 3):
                    selected_periods.append(period)
            
            if len(selected_periods) > 3:
                selected_periods = selected_periods[:3]
            
            forecast_list.append({
                "date": day,
                "periods": selected_periods,
                "temp_min": min(p["temp"] for p in periods),
                "temp_max": max(p["temp"] for p in periods)
            })
        
        return forecast_list
        
    except Exception as e:
        logger.error(f"❌ Błąd pobierania prognozy 5-dniowej: {e}")
        return None

def get_satellite_position(satellite_id: int, lat: float, lon: float) -> Optional[Dict]:
    """Pobierz aktualną pozycję satelity"""
    try:
        url = f"{N2YO_URL}/positions/{satellite_id}/{lat}/{lon}/0/1/"
        params = {"apiKey": N2YO_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            return None
        
        if "positions" in data and len(data["positions"]) > 0:
            pos = data["positions"][0]
            return {
                "lat": pos["satlatitude"],
                "lon": pos["satlongitude"],
                "alt": pos["sataltitude"],
                "velocity": pos.get("velocity", 0),
                "timestamp": datetime.fromtimestamp(pos["timestamp"]).strftime("%H:%M:%S")
            }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Błąd pobierania pozycji satelity: {e}")
        return None

def get_satellite_passes(satellite_id: int, lat: float, lon: float) -> Optional[List]:
    """Pobierz nadchodzące przeloty satelity"""
    try:
        url = f"{N2YO_URL}/visualpasses/{satellite_id}/{lat}/{lon}/0/5/300/"
        params = {"apiKey": N2YO_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            return None
        
        if "passes" in data:
            passes = []
            for pass_data in data["passes"][:3]:  # Tylko 3 najbliższe przeloty
                passes.append({
                    "start": datetime.fromtimestamp(pass_data["startUTC"]).strftime("%d.%m %H:%M"),
                    "end": datetime.fromtimestamp(pass_data["endUTC"]).strftime("%H:%M"),
                    "duration": pass_data["duration"],
                    "max_elevation": pass_data["maxEl"],
                    "brightness": pass_data.get("mag", "N/A")
                })
            return passes
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Błąd pobierania przelotów satelity: {e}")
        return None

def get_nasa_apod() -> Optional[Dict]:
    """Pobierz Astronomy Picture of the Day z NASA"""
    try:
        url = f"{NASA_APOD_URL}?api_key={NASA_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "title": data.get("title", "Astronomy Picture of the Day"),
                "explanation": data.get("explanation", ""),
                "url": data.get("url", ""),
                "hdurl": data.get("hdurl", ""),
                "date": data.get("date", ""),
                "copyright": data.get("copyright", "NASA")
            }
        return None
    except Exception as e:
        logger.error(f"❌ Błąd pobierania APOD: {e}")
        return None

def calculate_sun_position(lat: float, lon: float, date=None):
    """Oblicz pozycję Słońca dla danej lokalizacji"""
    from datetime import datetime
    import math
    
    if date is None:
        date = datetime.now()
    
    # Uproszczone obliczenia astronomiczne
    day_of_year = date.timetuple().tm_yday
    declination = 23.45 * math.sin(math.radians(360/365 * (day_of_year - 81)))
    
    # Przybliżone obliczenia wschodu/zachodu
    hour_angle = math.degrees(math.acos(
        -math.tan(math.radians(lat)) * math.tan(math.radians(declination))
    ))
    
    sunrise_hour = 12 - hour_angle/15
    sunset_hour = 12 + hour_angle/15
    
    return {
        "declination": round(declination, 2),
        "sunrise": f"{int(sunrise_hour):02d}:{int((sunrise_hour % 1) * 60):02d}",
        "sunset": f"{int(sunset_hour):02d}:{int((sunset_hour % 1) * 60):02d}"
    }

def get_extended_weather_data(lat: float, lon: float) -> Optional[Dict]:
    """Pobierz rozszerzone dane pogodowe"""
    try:
        # Dane z OpenWeather
        ow_data = get_openweather_data(lat, lon)
        if not ow_data:
            return None
        
        # Dodaj pozycję Słońca
        sun_pos = calculate_sun_position(lat, lon)
        ow_data["sun_position"] = sun_pos
        
        return ow_data
        
    except Exception as e:
        logger.error(f"❌ Błąd pobierania rozszerzonych danych: {e}")
        return ow_data  # Zwróć przynajmniej podstawowe dane

# ====================== KALENDARZ 13-MIESIĘCZNY ======================
ASTRONOMICAL_CALENDAR = [
    # Zaczynamy od Koziorożca (Capricorn) - Słońce w Koziorożcu
    {
        "name": "Koziorożec",
        "symbol": "♑",
        "element": "Ziemia",
        "emoji": "🐐",
        "start_date": (1, 20),  # 20 stycznia
        "end_date": (2, 16),    # 16 lutego
        "days": 28,
        "traits": ["Ambitny", "Praktyczny", "Cierpliwy"],
        "color": "Brązowy",
        "stone": "Granat"
    },
    # Wodnik (Aquarius) - Słońce w Wodniku
    {
        "name": "Wodnik",
        "symbol": "♒",
        "element": "Powietrze",
        "emoji": "🏺",
        "start_date": (2, 17),  # 17 lutego
        "end_date": (3, 12),    # 12 marca
        "days": 24,
        "traits": ["Innowacyjny", "Humanitarny", "Niezależny"],
        "color": "Niebieski",
        "stone": "Ametyst"
    },
    # Ryby (Pisces) - Słońce w Rybach
    {
        "name": "Ryby",
        "symbol": "♓",
        "element": "Woda",
        "emoji": "🐟",
        "start_date": (3, 13),  # 13 marca
        "end_date": (4, 18),    # 18 kwietnia
        "days": 37,
        "traits": ["Empatyczny", "Intuicyjny", "Artystyczny"],
        "color": "Fioletowy",
        "stone": "Akwarel"
    },
    # Baran (Aries) - Słońce w Baranie
    {
        "name": "Baran",
        "symbol": "♈",
        "element": "Ogień",
        "emoji": "🐏",
        "start_date": (4, 19),  # 19 kwietnia
        "end_date": (5, 14),    # 14 maja
        "days": 26,
        "traits": ["Odważny", "Dynamiczny", "Zdeterminowany"],
        "color": "Czerwony",
        "stone": "Krwawnik"
    },
    # Byk (Taurus) - Słońce w Byku
    {
        "name": "Byk",
        "symbol": "♉",
        "element": "Ziemia",
        "emoji": "🐂",
        "start_date": (5, 15),  # 15 maja
        "end_date": (6, 21),    # 21 czerwca
        "days": 38,
        "traits": ["Zdeterminowany", "Wierny", "Zmysłowy"],
        "color": "Zielony",
        "stone": "Szmaragd"
    },
    # Bliźnięta (Gemini) - Słońce w Bliźniętach
    {
        "name": "Bliźnięta",
        "symbol": "♊",
        "element": "Powietrze",
        "emoji": "👯",
        "start_date": (6, 22),  # 22 czerwca
        "end_date": (7, 20),    # 20 lipca
        "days": 29,
        "traits": ["Komunikatywny", "Ciekawy", "Elastyczny"],
        "color": "Żółty",
        "stone": "Akwamaryn"
    },
    # Rak (Cancer) - Słońce w Raku
    {
        "name": "Rak",
        "symbol": "♋",
        "element": "Woda",
        "emoji": "🦀",
        "start_date": (7, 21),  # 21 lipca
        "end_date": (8, 10),    # 10 sierpnia
        "days": 21,
        "traits": ["Troskliwy", "Intuicyjny", "Wrażliwy"],
        "color": "Srebrny",
        "stone": "Perła"
    },
    # Lew (Leo) - Słońce w Lwie
    {
        "name": "Lew",
        "symbol": "♌",
        "element": "Ogień",
        "emoji": "🦁",
        "start_date": (8, 11),  # 11 sierpnia
        "end_date": (9, 16),    # 16 września
        "days": 37,
        "traits": ["Kreatywny", "Hojny", "Ciepły"],
        "color": "Pomarańczowy",
        "stone": "Rubin"
    },
    # Panna (Virgo) - Słońce w Pannie
    {
        "name": "Panna",
        "symbol": "♍",
        "element": "Ziemia",
        "emoji": "🌾",
        "start_date": (9, 17),  # 17 września
        "end_date": (10, 30),   # 30 października
        "days": 44,
        "traits": ["Analityczny", "Praktyczny", "Skrupulatny"],
        "color": "Brązowy",
        "stone": "Sapphir"
    },
    # Waga (Libra) - Słońce w Wadze
    {
        "name": "Waga",
        "symbol": "♎",
        "element": "Powietrze",
        "emoji": "⚖️",
        "start_date": (10, 31),  # 31 października
        "end_date": (11, 23),    # 23 listopada
        "days": 24,
        "traits": ["Dyplomatyczny", "Sprawiedliwy", "Społeczny"],
        "color": "Niebieski",
        "stone": "Opal"
    },
    # Skorpion (Scorpio) - Słońce w Skorpionie
    {
        "name": "Skorpion",
        "symbol": "♏",
        "element": "Woda",
        "emoji": "🦂",
        "start_date": (11, 24),  # 24 listopada
        "end_date": (11, 29),    # 29 listopada
        "days": 6,
        "traits": ["Namiętny", "Zdeterminowany", "Intensywny"],
        "color": "Czarny",
        "stone": "Topaz"
    },
    # Wężownik (Ophiuchus) - Słońce w Wężowniku
    {
        "name": "Wężownik",
        "symbol": "⛎",
        "element": "Ogień",
        "emoji": "🐍",
        "start_date": (11, 30),  # 30 listopada
        "end_date": (12, 17),    # 17 grudnia
        "days": 18,
        "traits": ["Uzdrowiciel", "Mądry", "Tajemniczy"],
        "color": "Purpurowy",
        "stone": "Szafir"
    },
    # Strzelec (Sagittarius) - Słońce w Strzelcu
    {
        "name": "Strzelec",
        "symbol": "♐",
        "element": "Ogień",
        "emoji": "🏹",
        "start_date": (12, 18),  # 18 grudnia
        "end_date": (1, 19),     # 19 stycznia
        "days": 33,
        "traits": ["Optymistyczny", "Przygodowy", "Szczery"],
        "color": "Fioletowy",
        "stone": "Turkus"
    }
]

def get_astronomical_date():
    """Zwróć prawidłową datę astronomiczną"""
    now = datetime.now()
    current_month = now.month
    current_day = now.day
    
    # Sprawdź w którym miesiącu astronomicznym jesteśmy
    for month in ASTRONOMICAL_CALENDAR:
        start_month, start_day = month["start_date"]
        end_month, end_day = month["end_date"]
        
        if (current_month == start_month and current_day >= start_day) or \
           (current_month == end_month and current_day <= end_day) or \
           (start_month > end_month and 
            ((current_month == start_month and current_day >= start_day) or
             (current_month == end_month and current_day <= end_day) or
             (current_month > start_month or current_month < end_month))):
            
            # Oblicz dzień w miesiącu astronomicznym
            if start_month <= end_month:
                if current_month == start_month:
                    day_in_month = current_day - start_day + 1
                else:
                    days_from_start = 0
                    if current_month > start_month:
                        for m in range(start_month, current_month):
                            if m == start_month:
                                days_in_month = 31 if m in [1, 3, 5, 7, 8, 10, 12] else 30 if m in [4, 6, 9, 11] else 28
                                days_from_start += days_in_month - start_day + 1
                            else:
                                days_in_month = 31 if m in [1, 3, 5, 7, 8, 10, 12] else 30 if m in [4, 6, 9, 11] else 28
                                days_from_start += days_in_month
                    day_in_month = days_from_start + current_day
            else:
                if current_month >= start_month:
                    if current_month == start_month:
                        day_in_month = current_day - start_day + 1
                    else:
                        days_in_december = 31 - start_day + 1
                        day_in_month = days_in_december + current_day
                else:
                    day_in_month = current_day + (31 - start_day + 1)
            
            return {
                "day": day_in_month,
                "month": month["name"],
                "symbol": month["symbol"],
                "element": month["element"],
                "emoji": month["emoji"],
                "traits": month["traits"],
                "color": month["color"],
                "stone": month["stone"],
                "gregorian": now.strftime("%d.%m.%Y"),
                "days_in_month": month["days"],
                "day_of_year": now.timetuple().tm_yday
            }
    
    return {
        "day": 1,
        "month": "Koziorożec",
        "symbol": "♑",
        "element": "Ziemia",
        "emoji": "🐐",
        "traits": ["Ambitny", "Praktyczny", "Cierpliwy"],
        "color": "Brązowy",
        "stone": "Granat",
        "gregorian": now.strftime("%d.%m.%Y"),
        "days_in_month": 28,
        "day_of_year": now.timetuple().tm_yday
    }

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
    if not weather_data:
        return {"score": 0, "emoji": "🌧️", "category": "ZŁE"}
    
    score = 100
    
    score -= min(weather_data["clouds"] / 2, 50)
    score -= max(0, (weather_data["humidity"] - 60) / 2)
    score -= min(weather_data["wind_speed"] * 2, 20)
    
    if weather_data["visibility"] > 20:
        score += 10
    
    score = max(0, min(100, score))
    
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
    if not weather_data:
        return "☁️ Brak danych"
    
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

# ====================== GENEROWANIE RAPORTÓW ======================
def generate_full_astro_report(city_key):
    """Wygeneruj pełny raport astrometeorologiczny"""
    city = OBSERVATION_CITIES.get(city_key)
    if not city:
        return "❌ Nieznane miasto"
    
    weather_data = get_openweather_data(city["lat"], city["lon"])
    if not weather_data:
        return "❌ Nie udało się pobrać danych pogodowych"
    
    forecast_data = get_openweather_forecast(city["lat"], city["lon"])
    moon_data = calculate_moon_phase()
    astro_date = get_astronomical_date()
    visibility_score = get_visibility_score(weather_data)
    
    report = ""
    
    report += create_beautiful_header(f"COSMOS SENTRY - {city['name'].upper()}", city['emoji'])
    
    report += create_section("📅 DATA I CZAS", "⏱️")
    report += create_info_line("Data kalendarzowa", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    report += create_info_line("Data astronomiczna", f"{astro_date['day']}/{astro_date['days_in_month']} {astro_date['symbol']} {astro_date['month']}")
    report += create_info_line("Domena", f"{astro_date['element']} {astro_date['emoji']}")
    
    report += create_section("🌤️ AKTUALNA POGODA", get_weather_icon(weather_data["icon"]))
    report += create_info_line("Stan", f"{weather_data['description'].capitalize()}")
    report += create_info_line("Temperatura", f"{weather_data['temp']:.1f}°C (odczuwalna {weather_data['feels_like']:.1f}°C)")
    report += create_info_line("Wilgotność", f"{weather_data['humidity']}%")
    report += create_info_line("Ciśnienie", f"{weather_data['pressure']} hPa")
    report += create_info_line("Wiatr", f"{weather_data['wind_speed']} m/s {get_wind_direction(weather_data['wind_deg'])}")
    report += create_info_line("Zachmurzenie", f"{weather_data['clouds']}%")
    report += create_info_line("Widoczność", f"{weather_data['visibility']:.1f} km")
    report += create_info_line("Słońce", f"Wschód: {weather_data['sunrise']} | Zachód: {weather_data['sunset']}")
    
    report += create_section("🌙 KSIĘŻYC", moon_data["emoji"])
    report += create_info_line("Faza", f"{moon_data['name']}")
    report += create_info_line("Oświetlenie", f"{moon_data['illumination']}%")
    
    report += create_section("🔭 WARUNKI OBSERWACYJNE", visibility_score["emoji"])
    report += create_info_line("Ocena", f"{visibility_score['category']}")
    report += create_info_line("Wynik", f"{visibility_score['score']}/100")
    
    report += f"\n{'═' * 40}\n"
    report += f"<i>🌌 COSMOS SENTRY v2.0 | Data: {weather_data['timestamp']}</i>"
    
    return report

def generate_calendar_report():
    """Wygeneruj raport kalendarza"""
    now = datetime.now()
    current_astro_date = get_astronomical_date()
    
    report = ""
    report += create_beautiful_header("PRAWIDŁOWY KALENDARZ 13-MIESIĘCZNY", "📅")
    
    report += create_section("🎯 AKTUALNY MIESIĄC", current_astro_date["symbol"])
    report += create_info_line("Nazwa", f"{current_astro_date['month']} {current_astro_date['emoji']}")
    report += create_info_line("Dzień", f"{current_astro_date['day']}/{current_astro_date['days_in_month']}")
    report += create_info_line("Żywioł", current_astro_date["element"])
    report += create_info_line("Cechy", ", ".join(current_astro_date["traits"]))
    
    report += create_section("🗓️ PEŁNY KALENDARZ 13-MIESIĘCZNY", "📆")
    
    for month in ASTRONOMICAL_CALENDAR:
        start_month, start_day = month["start_date"]
        end_month, end_day = month["end_date"]
        
        start_str = f"{start_day:02d}.{start_month:02d}"
        end_str = f"{end_day:02d}.{end_month:02d}"
        
        current_marker = " 🔸" if month["name"] == current_astro_date["month"] else ""
        report += f"• {month['symbol']} <b>{month['name']}</b> {month['emoji']}\n"
        report += f"  {start_str} - {end_str} ({month['days']} dni){current_marker}\n"
    
    report += f"\n{'═' * 40}\n"
    report += f"<i>🌌 Prawdziwy kalendarz astronomiczny | COSMOS SENTRY v2.0</i>"
    
    return report

# ====================== FORMATOWANIE PROGNOZ ======================
def format_5day_forecast(forecast_data: List, city_name: str) -> str:
    """Sformatuj prognozę 5-dniową"""
    if not forecast_data:
        return "❌ Nie udało się pobrać prognozy"
    
    message = create_beautiful_header(f"PROGNOZA 5-DNIOWA - {city_name.upper()}", "📅")
    
    day_names_pl = {
        0: "Poniedziałek",
        1: "Wtorek",
        2: "Środa",
        3: "Czwartek",
        4: "Piątek",
        5: "Sobota",
        6: "Niedziela"
    }
    
    today = datetime.now()
    
    for day_idx, day_data in enumerate(forecast_data[:5]):
        date_obj = datetime.strptime(f"{day_data['date']}.{today.year}", "%d.%m.%Y")
        day_name = day_names_pl[date_obj.weekday()]
        
        message += f"\n{create_section(f'{day_data['date']} ({day_name}):', '📅')}"
        message += f"🌡️ <b>Temp:</b> {day_data['temp_min']:.1f}°C / {day_data['temp_max']:.1f}°C\n"
        
        for period in day_data["periods"][:3]:
            emoji = get_weather_icon(period["icon"])
            message += f"• <b>{period['time']}:</b> {period['temp']:.1f}°C | {emoji} {period['description']}\n"
    
    message += f"\n{'═' * 40}\n"
    message += f"<i>🌤️ Prognoza OpenWeather | {datetime.now().strftime('%H:%M:%S')}</i>"
    
    return message

def format_satellite_info(satellite_key: str, city_key: str = "warszawa") -> str:
    """Sformatuj informacje o satelicie"""
    if satellite_key not in SATELLITES:
        return "❌ Nieznany satelita"
    
    city = OBSERVATION_CITIES.get(city_key, OBSERVATION_CITIES["warszawa"])
    satellite = SATELLITES[satellite_key]
    
    message = create_beautiful_header(f"SATELLITE TRACKING - {satellite['name'].upper()}", satellite['emoji'])
    
    position = get_satellite_position(satellite["id"], city["lat"], city["lon"])
    if position:
        message += create_section("📍 AKTUALNA POZYCJA", "🛰️")
        message += create_info_line("Szerokość", f"{position['lat']:.4f}°")
        message += create_info_line("Długość", f"{position['lon']:.4f}°")
        message += create_info_line("Wysokość", f"{position['alt']:.2f} km")
        message += create_info_line("Prędkość", f"{position['velocity']:.1f} km/s")
    
    passes = get_satellite_passes(satellite["id"], city["lat"], city["lon"])
    if passes:
        message += create_section("🕐 NADCHODZĄCE PRZELOTY", "⏰")
        for pass_data in passes[:2]:
            message += f"• <b>{pass_data['start']} - {pass_data['end']}</b>\n"
            message += f"  Czas: {pass_data['duration']}s | Wysokość: {pass_data['max_elevation']}°\n"
    
    message += create_section("📋 INFORMACJE", "ℹ️")
    message += create_info_line("ID satelity", str(satellite["id"]))
    message += create_info_line("Opis", satellite["description"])
    
    message += f"\n{'═' * 40}\n"
    message += f"<i>🛰️ Źródło: N2YO API | Lokalizacja: {city['name']}</i>"
    
    return message

def format_satellites_list() -> str:
    """Sformatuj listę dostępnych satelit"""
    message = create_beautiful_header("SYSTEM ŚLEDZENIA SATELITÓW", "🛰️")
    
    message += create_section("📡 DOSTĘPNE SATELITY", "🛰️")
    for key, sat in SATELLITES.items():
        message += f"• {sat['emoji']} <b>{sat['name']}</b>\n"
        message += f"  ID: {sat['id']} | /sat_{key}\n"
    
    message += create_section("👀 JAK OBSERWOWAĆ", "🎯")
    message += "1. Sprawdź przeloty nad Twoją lokalizacją\n"
    message += "2. Wybierz satelitę z dobrej widoczności\n"
    message += "3. Sprawdź warunki pogodowe\n"
    message += "4. Bądź gotowy 5 minut przed przelotem\n"
    
    message += create_section("⌨️ PRZYKŁADOWE KOMENDY", "💻")
    message += "<code>/sat_iss</code> - Aktualna pozycja ISS\n"
    message += "<code>/sat_hst</code> - Teleskop Hubble'a\n"
    message += "<code>/forecast5 warszawa</code> - Prognoza 5-dniowa\n"
    message += "<code>/nasa_apod</code> - Zdjęcie dnia NASA\n"
    
    message += f"\n{'═' * 40}\n"
    message += "<i>🛰️ Użyj komendy z nazwą satelity, np. /sat_iss</i>"
    
    return message

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
        <title>🌌 COSMOS SENTRY v2.0</title>
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
            .satellite-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 30px 0;
            }}
            .satellite-card {{
                background: rgba(0, 150, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                border: 1px solid rgba(0, 150, 255, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="title">🌌 COSMOS SENTRY v2.0</h1>
                <h2 style="color: #81ecec;">Zaawansowany System Astrometeorologiczny</h2>
                <div class="status-badge">🟢 SYSTEM AKTYWNY | v2.0 z śledzeniem satelit</div>
                <h2>📅 {now.strftime("%d.%m.%Y %H:%M")}</h2>
            </div>
            
            <div class="features-grid">
                <div class="feature-card">
                    <h3>🌠 Pełna Prognoza 5-dniowa</h3>
                    <p>Rozbudowana prognoza z godzinowymi danymi dla 5 dni</p>
                </div>
                <div class="feature-card">
                    <h3>🛰️ Śledzenie Satelit</h3>
                    <p>Pozycje i przeloty ISS, Hubble'a, Landsat i innych</p>
                </div>
                <div class="feature-card">
                    <h3>🌙 Zaawansowana Astrometeorologia</h3>
                    <p>Pozycje Słońca, fazy Księżyca, warunki obserwacyjne</p>
                </div>
            </div>
            
            <h3 style="text-align: center; margin-top: 40px;">🛰️ ŚLEDZONE SATELITY</h3>
            <div class="satellite-grid">
                <div class="satellite-card">🛰️ ISS</div>
                <div class="satellite-card">🔭 Hubble</div>
                <div class="satellite-card">🌍 Landsat 8</div>
                <div class="satellite-card">🛰️ Sentinel-2A</div>
                <div class="satellite-card">🇨🇳 Tiangong</div>
                <div class="satellite-card">🛰️ Starlink</div>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" class="cta-button">
                    💬 Otwórz bota w Telegram
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.3);">
                <p>🌌 COSMOS SENTRY v2.0 | Zaawansowany System Astrometeorologiczny</p>
                <p>🛰️ Śledzenie satelit | 📅 Prawidłowy kalendarz 13-miesięczny</p>
                <p>{now.strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# ====================== TELEGRAM WEBHOOK ======================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Główny endpoint dla webhook Telegram"""
    try:
        data = request.get_json()
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()
            
            # Komenda /start
            if text == "/start":
                welcome_msg = (
                    f"{create_beautiful_header('COSMOS SENTRY v2.0', '🌌')}"
                    f"<b>Zaawansowany system astrometeorologiczny z śledzeniem satelit!</b>\n\n"
                    
                    f"{create_section('🚀 NOWE FUNKCJE v2.0', '✨')}"
                    f"• 🛰️ <b>Śledzenie satelit</b> (ISS, Hubble, Landsat, Sentinel)\n"
                    f"• 📅 <b>Pełna prognoza 5-dniowa</b> z godzinowymi danymi\n"
                    f"• 🌤️ <b>Rozszerzone dane pogodowe</b>\n"
                    f"• 🛰️ <b>Pozycje i przeloty satelit</b> w czasie rzeczywistym\n\n"
                    
                    f"{create_section('🎯 GŁÓWNE KOMENDY', '📱')}"
                    f"<code>/astro [miasto]</code> - Pełny raport astrometeorologiczny\n"
                    f"<code>/forecast5 [miasto]</code> - Prognoza 5-dniowa\n"
                    f"<code>/satellites</code> - Lista satelit do śledzenia\n"
                    f"<code>/sat_iss</code> - Pozycja ISS\n"
                    f"<code>/sat_hst</code> - Teleskop Hubble'a\n"
                    f"<code>/weather [miasto]</code> - Aktualna pogoda\n"
                    f"<code>/moon</code> - Faza Księżyca\n"
                    f"<code>/calendar</code> - Kalendarz 13-miesięczny\n"
                    f"<code>/nasa_apod</code> - Zdjęcie dnia NASA\n"
                    f"<code>/help</code> - Pomoc\n\n"
                    
                    f"<b>Dostępne miasta:</b> warszawa, koszalin, krakow, gdansk, wroclaw\n\n"
                    
                    f"{'═' * 40}\n"
                    f"<i>🌌 COSMOS SENTRY v2.0 | System śledzenia satelit online!</i>"
                )
                send_telegram_message(chat_id, welcome_msg)
            
            # Komenda /forecast5
            elif text.startswith("/forecast5"):
                args = text[10:].strip().lower()
                
                if not args:
                    args = "warszawa"
                
                if args in OBSERVATION_CITIES:
                    city = OBSERVATION_CITIES[args]
                    forecast = get_5day_forecast(city["lat"], city["lon"])
                    
                    if forecast:
                        report = format_5day_forecast(forecast, city["name"])
                        send_telegram_message(chat_id, report)
                    else:
                        send_telegram_message(chat_id, "❌ Nie udało się pobrać prognozy 5-dniowej")
                else:
                    send_telegram_message(chat_id, "❌ Nieznane miasto. Dostępne: warszawa, koszalin, krakow, gdansk, wroclaw")
            
            # Komenda /satellites
            elif text == "/satellites" or text == "/Satellites":
                report = format_satellites_list()
                send_telegram_message(chat_id, report)
            
            # Komendy dla poszczególnych satelit
            elif text.startswith("/sat_"):
                sat_key = text[5:].lower()
                if sat_key in SATELLITES:
                    city_key = "warszawa"
                    if "_" in sat_key:
                        parts = sat_key.split("_")
                        sat_key = parts[0]
                        if len(parts) > 1 and parts[1] in OBSERVATION_CITIES:
                            city_key = parts[1]
                    
                    report = format_satellite_info(sat_key, city_key)
                    send_telegram_message(chat_id, report)
                else:
                    send_telegram_message(chat_id, "❌ Nieznany satelita. Użyj /satellites")
            
            # Komenda /nasa_apod
            elif text == "/nasa_apod":
                apod_data = get_nasa_apod()
                if apod_data:
                    report = create_beautiful_header("NASA: ASTRONOMY PICTURE OF THE DAY", "🛰️")
                    report += create_section(apod_data["title"], "🌟")
                    
                    if len(apod_data["explanation"]) > 800:
                        explanation = apod_data["explanation"][:800] + "..."
                    else:
                        explanation = apod_data["explanation"]
                    
                    report += f"<i>{explanation}</i>\n\n"
                    report += create_info_line("Data", apod_data["date"])
                    report += create_info_line("Autor", apod_data["copyright"])
                    
                    if apod_data["url"]:
                        report += f"\n🔗 <a href='{apod_data['url']}'>Zobacz zdjęcie</a>"
                    
                    report += f"\n{'═' * 40}\n"
                    report += "<i>🛰️ Źródło: NASA APOD API</i>"
                    
                    send_telegram_message(chat_id, report)
                else:
                    send_telegram_message(chat_id, "❌ Nie udało się pobrać zdjęcia dnia NASA")
            
            # Komenda /astro
            elif text.startswith("/astro"):
                args = text[6:].strip().lower()
                
                if not args:
                    args = "warszawa"
                
                if args in OBSERVATION_CITIES:
                    report = generate_full_astro_report(args)
                    send_telegram_message(chat_id, report)
                else:
                    send_telegram_message(chat_id, "❌ Nieznane miasto. Dostępne: warszawa, koszalin, krakow, gdansk, wroclaw")
            
            # Komenda /calendar
            elif text == "/calendar":
                report = generate_calendar_report()
                send_telegram_message(chat_id, report)
            
            # Komenda /weather
            elif text.startswith("/weather"):
                args = text[8:].strip().lower()
                
                if not args:
                    args = "warszawa"
                
                if args in OBSERVATION_CITIES:
                    city = OBSERVATION_CITIES[args]
                    weather_data = get_openweather_data(city["lat"], city["lon"])
                    
                    if weather_data:
                        report = create_beautiful_header(f"POGODA - {city['name'].upper()}", city['emoji'])
                        
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
                    send_telegram_message(chat_id, "❌ Nieznane miasto. Dostępne: warszawa, koszalin, krakow, gdansk, wroclaw")
            
            # Komenda /forecast (stara wersja)
            elif text.startswith("/forecast"):
                if "forecast5" not in text:  # To nie jest forecast5
                    args = text[9:].strip().lower()
                    
                    if not args:
                        args = "warszawa"
                    
                    if args in OBSERVATION_CITIES:
                        city = OBSERVATION_CITIES[args]
                        forecast = get_openweather_forecast(city["lat"], city["lon"])
                        
                        if forecast:
                            report = create_beautiful_header(f"PROGNOZA - {city['name'].upper()}", city['emoji'])
                            
                            for i, period in enumerate(forecast[:6]):
                                report += f"• {period['time']}: {period['temp']:.1f}°C | {get_weather_icon(period['icon'])} {period['description']}\n"
                            
                            report += f"\n{'═' * 40}\n"
                            report += f"<i>🌤️ Prognoza OpenWeather | {datetime.now().strftime('%H:%M:%S')}</i>"
                            
                            send_telegram_message(chat_id, report)
                        else:
                            send_telegram_message(chat_id, "❌ Nie udało się pobrać prognozy")
                    else:
                        send_telegram_message(chat_id, "❌ Nieznane miasto. Spróbuj /forecast5")
            
            # Komenda /moon
            elif text == "/moon":
                moon_data = calculate_moon_phase()
                report = create_beautiful_header("FAZA KSIĘŻYCA", moon_data["emoji"])
                
                report += create_section("🌕 FAZA KSIĘŻYCA", moon_data["emoji"])
                report += create_info_line("Nazwa", moon_data["name"])
                report += create_info_line("Oświetlenie", f"{moon_data['illumination']}%")
                report += create_info_line("Opis", moon_data["description"])
                
                report += f"\n{'═' * 40}\n"
                report += f"<i>🌙 Obliczenia faz księżyca | {datetime.now().strftime('%H:%M:%S')}</i>"
                
                send_telegram_message(chat_id, report)
            
            # Komenda /help
            elif text == "/help":
                help_msg = (
                    f"{create_beautiful_header('POMOC - COSMOS SENTRY v2.0', '❓')}"
                    
                    f"{create_section('🌌 KOMENDY OBSERWACYJNE', '🔭')}"
                    f"<code>/astro [miasto]</code> - Pełny raport astrometeorologiczny\n"
                    f"<code>/moon</code> - Szczegółowy raport faz księżyca\n\n"
                    
                    f"{create_section('🛰️ KOMENDY SATELITARNE', '🛰️')}"
                    f"<code>/satellites</code> - Lista satelit do śledzenia\n"
                    f"<code>/sat_iss</code> - Pozycja ISS\n"
                    f"<code>/sat_hst</code> - Teleskop Hubble'a\n"
                    f"<code>/sat_landsat8</code> - Landsat 8\n"
                    f"<code>/sat_sentinel2a</code> - Sentinel-2A\n\n"
                    
                    f"{create_section('🌤️ KOMENDY POGODOWE', '⛅')}"
                    f"<code>/weather [miasto]</code> - Aktualna pogoda\n"
                    f"<code>/forecast5 [miasto]</code> - Prognoza 5-dniowa\n\n"
                    
                    f"{create_section('📅 KOMENDY KALENDARZOWE', '🗓️')}"
                    f"<code>/calendar</code> - Prawdziwy kalendarz 13-miesięczny\n\n"
                    
                    f"{create_section('🛰️ KOMENDY NASA', '🚀')}"
                    f"<code>/nasa_apod</code> - Zdjęcie dnia NASA\n\n"
                    
                    f"{create_section('📍 DOSTĘPNE MIASTA', '🏙️')}"
                    f"warszawa, koszalin, krakow, gdansk, wroclaw\n\n"
                    
                    f"{'═' * 40}\n"
                    f"<i>🌌 Wersja: 2.0 | System śledzenia satelit | Pełne prognozy 5-dniowe</i>\n"
                    f"<i>📞 Wsparcie: @PcSentintel_Bot</i>"
                )
                send_telegram_message(chat_id, help_msg)
            
            # Domyślna odpowiedź
            else:
                default_msg = (
                    f"{create_beautiful_header('COSMOS SENTRY v2.0', '🌌')}"
                    f"Nie rozpoznano komendy. Wpisz <code>/help</code> aby zobaczyć listę komend.\n\n"
                    f"<i>Zaawansowany system astrometeorologiczny z pięknym interfejsem</i>\n\n"
                    f"<b>Nowe w v2.0:</b>\n"
                    f"• 🛰️ Śledzenie satelit (ISS, Hubble, Landsat)\n"
                    f"• 📅 Pełna prognoza 5-dniowa\n"
                    f"• 🛰️ Zdjęcia dnia NASA\n\n"
                    f"Spróbuj: <code>/satellites</code> lub <code>/forecast5 warszawa</code>"
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
    print("🌌 COSMOS SENTRY v2.0 - ZAAWANSOWANY SYSTEM ASTROMETEOROLOGICZNY")
    print("=" * 60)
    
    now = datetime.now()
    
    print(f"📅 Data: {now.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"📍 Obserwowane miasta: {', '.join([c['name'] for c in OBSERVATION_CITIES.values()])}")
    print(f"🛰️ Śledzone satelity: {', '.join([s['name'] for s in SATELLITES.values()])}")
    
    # Test API
    print(f"\n🔍 Testowanie API...")
    test_weather = get_openweather_data(52.2297, 21.0122)
    if test_weather:
        print(f"✅ OpenWeather API: AKTYWNE ({test_weather['temp']:.1f}°C)")
    
    test_sat = get_satellite_position(25544, 52.2297, 21.0122)
    if test_sat:
        print(f"✅ N2YO API: AKTYWNE (ISS: {test_sat['lat']:.1f}°, {test_sat['lon']:.1f}°)")
    else:
        print(f"⚠️ N2YO API: Może wymagać klucza API")
    
    print("=" * 60)
    print("🚀 System v2.0 uruchomiony pomyślnie!")
    print("=" * 60)
    
    # Uruchom pingowanie
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