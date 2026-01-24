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

# ====================== NOWE FUNKCJE POGODOWE ======================
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
    # Rzeczywiste obliczenia wymagałyby bardziej skomplikowanych formuł
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

# ====================== FORMATOWANIE PROGNOZ ======================
def format_5day_forecast(forecast_data: List, city_name: str) -> str:
    """Sformatuj prognozę 5-dniową w piękny sposób"""
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
    
    for day_idx, day_data in enumerate(forecast_data[:5]):  # Maksymalnie 5 dni
        date_obj = datetime.strptime(f"{day_data['date']}.{today.year}", "%d.%m.%Y")
        day_name = day_names_pl[date_obj.weekday()]
        
        message += f"\n{create_section(f'{day_data['date']} ({day_name}):', '📅')}"
        message += f"🌡️ <b>Temp:</b> {day_data['temp_min']:.1f}°C / {day_data['temp_max']:.1f}°C\n"
        
        for period in day_data["periods"][:3]:  # 3 okresy dziennie
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
    
    # Pozycja satelity
    position = get_satellite_position(satellite["id"], city["lat"], city["lon"])
    if position:
        message += create_section("📍 AKTUALNA POZYCJA", "🛰️")
        message += create_info_line("Szerokość", f"{position['lat']:.4f}°")
        message += create_info_line("Długość", f"{position['lon']:.4f}°")
        message += create_info_line("Wysokość", f"{position['alt']:.2f} km")
        message += create_info_line("Prędkość", f"{position['velocity']:.1f} km/s")
        message += create_info_line("Czas danych", position['timestamp'])
    else:
        message += "⚠️ Brak danych o pozycji\n"
    
    # Nadchodzące przeloty
    passes = get_satellite_passes(satellite["id"], city["lat"], city["lon"])
    if passes:
        message += create_section("🕐 NADCHODZĄCE PRZELOTY", "⏰")
        for pass_data in passes[:2]:  # 2 najbliższe przeloty
            message += f"• <b>{pass_data['start']} - {pass_data['end']}</b>\n"
            message += f"  Czas: {pass_data['duration']}s | Wysokość: {pass_data['max_elevation']}°\n"
    else:
        message += "⚠️ Brak nadchodzących przelotów\n"
    
    # Informacje ogólne
    message += create_section("📋 INFORMACJE", "ℹ️")
    message += create_info_line("ID satelity", str(satellite["id"]))
    message += create_info_line("Opis", satellite["description"])
    message += create_info_line("Lokalizacja", f"{city['name']} {city['emoji']}")
    
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

# ====================== ROZSZERZONE FUNKCJE POMOCNICZE ======================
def get_extended_weather_data(lat: float, lon: float) -> Optional[Dict]:
    """Pobierz rozszerzone dane pogodowe z OpenWeather i OpenMeteo"""
    try:
        # Dane z OpenWeather
        ow_data = get_openweather_data(lat, lon)
        if not ow_data:
            return None
        
        # Dodatkowe dane z OpenMeteo
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": ["temperature_2m", "precipitation", "cloud_cover", "visibility"],
                "forecast_days": 2
            }
            response = requests.get(OPENMETEO_URL, params=params, timeout=10)
            meteodata = response.json()
            
            if "hourly" in meteodata:
                ow_data["hourly"] = meteodata["hourly"]
        except:
            pass
        
        # Oblicz pozycję Słońca
        sun_pos = calculate_sun_position(lat, lon)
        ow_data["sun_position"] = sun_pos
        
        return ow_data
        
    except Exception as e:
        logger.error(f"❌ Błąd pobierania rozszerzonych danych: {e}")
        return ow_data  # Zwróć przynajmniej podstawowe dane

# ====================== KALENDARZ (pozostał bez zmian) ======================
ASTRONOMICAL_CALENDAR = [
    # ... (tu pozostaje cały istniejący kalendarz bez zmian)
]

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== FLASK APP z nowymi komendami ======================
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

# ====================== TELEGRAM WEBHOOK z nowymi komendami ======================
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
            
            # Komenda /forecast5 (prognoza 5-dniowa)
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
                    # Można dodać opcjonalne miasto: /sat_iss_warszawa
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
            
            # Komenda /help (zaktualizowana)
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
            
            # Pozostałe komendy pozostają bez zmian...
            elif text.startswith("/astro"):
                # ... (istniejący kod)
                pass
            elif text == "/calendar":
                # ... (istniejący kod)
                pass
            elif text.startswith("/weather"):
                # ... (istniejący kod)
                pass
            elif text.startswith("/forecast"):
                # ... (istniejący kod)
                pass
            elif text == "/moon":
                # ... (istniejący kod)
                pass
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

# ====================== FUNKCJE POMOCNICZE (pozostałe bez zmian) ======================
# ... (tu pozostają wszystkie istniejące funkcje pomocnicze bez zmian)

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
    
    print("=" * 60)
    print("🚀 System v2.0 uruchomiony pomyślnie!")
    print("=" * 60)
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )