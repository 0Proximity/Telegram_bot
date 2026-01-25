#!/usr/bin/env python3
"""
🤖 SENTRY ONE v10.0 - Ultimate Astrometeorological System
Inteligentne pingowanie bez spamowania użytkowników
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
from typing import Dict, List, Optional

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"

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

print("=" * 60)
print("🤖 SENTRY ONE v10.0 - ULTIMATE SYSTEM")
print(f"🌐 URL: {RENDER_URL}")
print("🛰️ NASA API + N2YO + OpenWeather")
print("🔔 System pingowania: INTELEGENTNY")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== BAZA DANYCH ======================
def init_database():
    """Inicjalizacja bazy danych"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            satellite_notifications BOOLEAN DEFAULT 0,
            observation_alerts BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_settings(chat_id: int) -> Dict:
    """Pobierz ustawienia użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT chat_id, satellite_notifications, observation_alerts
        FROM users WHERE chat_id = ?
    ''', (chat_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "chat_id": result[0],
            "satellite_notifications": bool(result[1]),
            "observation_alerts": bool(result[2])
        }
    else:
        return {
            "chat_id": chat_id,
            "satellite_notifications": False,
            "observation_alerts": True
        }

def update_user_settings(chat_id: int, settings: Dict):
    """Aktualizuj ustawienia użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (chat_id, satellite_notifications, observation_alerts)
        VALUES (?, ?, ?)
    ''', (
        chat_id,
        1 if settings.get("satellite_notifications") else 0,
        1 if settings.get("observation_alerts") else 0
    ))
    
    conn.commit()
    conn.close()

def get_all_users_with_notifications():
    """Pobierz wszystkich użytkowników z włączonymi powiadomieniami"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT chat_id FROM users 
        WHERE satellite_notifications = 1 OR observation_alerts = 1
    ''')
    
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

# ====================== NASA FUNCTIONS ======================
def get_nasa_apod():
    """Pobierz Astronomy Picture of the Day z NASA"""
    try:
        url = f"{NASA_APOD_URL}?api_key={NASA_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "title": data.get("title", "NASA APOD"),
            "explanation": data.get("explanation", ""),
            "url": data.get("url", ""),
            "media_type": data.get("media_type", "image"),
            "date": data.get("date", "")
        }
    except Exception as e:
        logger.error(f"❌ Błąd NASA APOD: {e}")
        return None

def get_weather_forecast(lat, lon):
    """Pobierz prognozę pogody z Open-Meteo"""
    try:
        url = OPENMETEO_BASE_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,visibility,is_day",
            "daily": "sunrise,sunset",
            "timezone": "auto",
            "forecast_days": 2
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
        
        return {
            "pressure": data.get("main", {}).get("pressure", 0),
            "feels_like": data.get("main", {}).get("feels_like", 0),
            "weather_description": data.get("weather", [{}])[0].get("description", ""),
            "sunrise": datetime.fromtimestamp(data.get("sys", {}).get("sunrise", 0)).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data.get("sys", {}).get("sunset", 0)).strftime("%H:%M"),
        }
        
    except Exception as e:
        logger.error(f"❌ Błąd OpenWeather API: {e}")
        return None

# ====================== ASTRONOMICAL CALCULATIONS ======================
def calculate_moon_phase(date: datetime = None) -> Dict:
    """Oblicz dokładną fazę księżyca"""
    if not date:
        date = datetime.now()
    
    # Ostatni nów: 11 stycznia 2025, 11:57 UTC
    last_new_moon = datetime(2025, 1, 11, 11, 57)
    
    delta_days = (date - last_new_moon).total_seconds() / 86400.0
    moon_age = delta_days % 29.530588
    
    illumination = 50 * (1 - math.cos(2 * math.pi * moon_age / 29.530588))
    
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
        "age_days": moon_age
    }

def get_astronomical_date():
    """Zwróć datę w kalendarzu 13-miesięcznym"""
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    
    for month in [
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
    ]:
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
    """Pobierz czasy wschodu/zachodu Słońca"""
    city = OBSERVATION_CITIES[city_key]
    
    try:
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
        
        moon = calculate_moon_phase()
        
        return {
            "sun": {"rise": sunrise, "set": sunset},
            "moon_phase": moon
        }
        
    except Exception as e:
        return {
            "sun": {"rise": "07:30", "set": "16:30"},
            "moon_phase": calculate_moon_phase()
        }

# ====================== OBSERVATION CONDITIONS ======================
def check_city_conditions(city_key: str):
    """Sprawdź warunki obserwacyjne dla miasta"""
    city = OBSERVATION_CITIES[city_key]
    weather_data = get_weather_forecast(city["lat"], city["lon"])
    
    if not weather_data or "current" not in weather_data:
        return None
    
    current = weather_data["current"]
    
    cloud_cover = current.get("cloud_cover", 100)
    visibility = current.get("visibility", 0) / 1000
    humidity = current.get("relative_humidity_2m", 100)
    wind_speed = current.get("wind_speed_10m", 0)
    temperature = current.get("temperature_2m", 0)
    is_day = current.get("is_day", 1)
    
    conditions_check = {
        "cloud_cover": cloud_cover <= GOOD_CONDITIONS["max_cloud_cover"],
        "visibility": visibility >= GOOD_CONDITIONS["min_visibility"],
        "humidity": humidity <= GOOD_CONDITIONS["max_humidity"],
        "wind_speed": wind_speed <= GOOD_CONDITIONS["max_wind_speed"],
        "temperature": GOOD_CONDITIONS["min_temperature"] <= temperature <= GOOD_CONDITIONS["max_temperature"]
    }
    
    conditions_met = sum(conditions_check.values())
    total_conditions = len(conditions_check)
    
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
        "total_conditions": total_conditions
    }

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
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return False

def send_photo(chat_id, photo_url, caption=""):
    """Wyślij zdjęcie"""
    return send_telegram_message(chat_id, caption, photo_url)

# ====================== FLASK APP ======================
app = Flask(__name__)

# Globalna zmienna do śledzenia ostatniego pinga
last_ping_time = datetime.now()
ping_count = 0

@app.route('/')
def home():
    """Strona główna - ten endpoint jest pingowany"""
    global last_ping_time, ping_count
    last_ping_time = datetime.now()
    ping_count += 1
    
    now = datetime.now()
    astro_date = get_astronomical_date()
    moon = calculate_moon_phase()
    
    # Sprawdź czy to ping zewnętrzny (nie od użytkownika)
    user_agent = request.headers.get('User-Agent', '')
    is_auto_ping = 'python-requests' in user_agent or 'UptimeRobot' in user_agent
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v10.0</title>
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
                background: linear-gradient(to right, #00b09b, #96c93d);
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
            }}
            .ping-info {{
                background: rgba(0, 0, 0, 0.3);
                padding: 15px;
                border-radius: 10px;
                margin-top: 20px;
                font-family: monospace;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 48px; margin-bottom: 10px;">🤖 SENTRY ONE v10.0</h1>
                <h2 style="color: #81ecec; margin-bottom: 20px;">Ultimate Astrometeorological System</h2>
                
                <div class="moon-phase">
                    {moon['emoji']}
                </div>
                
                <div style="margin: 20px 0;">
                    <span class="api-status">🛰️ NASA API</span>
                    <span class="api-status">🌤️ OPENWEATHER</span>
                    <span class="api-status">🛰️ N2YO SATELLITES</span>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>🌌 Faza Księżyca</h3>
                    <p style="font-size: 24px; margin: 10px 0;">{moon['emoji']} {moon['name']}</p>
                    <p>Oświetlenie: {moon['illumination']:.1f}%</p>
                </div>
                
                <div class="stat-card">
                    <h3>📅 Kalendarz Astronomiczny</h3>
                    <p style="font-size: 24px; margin: 10px 0;">{astro_date['day']} {astro_date['month_symbol']}</p>
                    <p>{astro_date['month_polish']}</p>
                </div>
                
                <div class="stat-card">
                    <h3>📍 Obserwowane miasta</h3>
                    <p>🏛️ Warszawa</p>
                    <p>🌲 Koszalin</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" class="btn">
                    💬 Otwórz bota w Telegram
                </a>
            </div>
            
            <div class="ping-info">
                <h4>📡 Status systemu:</h4>
                <p>• Ostatni ping: {last_ping_time.strftime('%H:%M:%S')}</p>
                <p>• Liczba pingów: {ping_count}</p>
                <p>• Czas pracy: {(datetime.now() - last_ping_time).seconds // 60} minut</p>
                <p>• Ping automatyczny: {'✅ TAK' if is_auto_ping else '❌ NIE'}</p>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                <p>🤖 SENTRY ONE v10.0 | System monitoringu astronomicznego</p>
                <p style="font-family: monospace; font-size: 12px; opacity: 0.8;">
                    {now.strftime("%Y-%m-%d %H:%M:%S")} | Ping #{ping_count}
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/health')
def health_check():
    """Prosty endpoint do sprawdzania zdrowia aplikacji"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "ping_count": ping_count,
        "last_ping": last_ping_time.isoformat()
    }), 200

@app.route('/ping')
def ping():
    """Endpoint tylko do pingowania - nie wysyła powiadomień!"""
    global last_ping_time, ping_count
    last_ping_time = datetime.now()
    ping_count += 1
    
    logger.info(f"📡 Ping #{ping_count} o {last_ping_time.strftime('%H:%M:%S')}")
    
    return jsonify({
        "status": "pong",
        "ping_count": ping_count,
        "timestamp": last_ping_time.isoformat(),
        "message": "System aktywny - NIE WYSYŁAM POWIADOMIEŃ!"
    }), 200

@app.route('/status')
def status():
    """Status systemu"""
    users = get_all_users_with_notifications()
    
    return jsonify({
        "status": "operational",
        "users_with_notifications": len(users),
        "last_ping": last_ping_time.isoformat(),
        "ping_count": ping_count,
        "observation_cities": list(OBSERVATION_CITIES.keys())
    }), 200

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
            
            user_settings = get_user_settings(chat_id)
            
            if text == "/start":
                # NASA APOD
                nasa_apod = get_nasa_apod()
                
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
                
                # ========== BUDUJEMY RAPORT ==========
                report = ""
                
                # 1. NASA APOD
                if nasa_apod and nasa_apod.get('url'):
                    send_photo(chat_id, nasa_apod['url'], 
                             f"🛰️ <b>NASA ASTRONOMY PICTURE OF THE DAY</b>\n\n"
                             f"<b>{nasa_apod['title']}</b>\n"
                             f"Data: {nasa_apod['date']}\n\n"
                             f"{nasa_apod['explanation'][:200]}...")
                    time.sleep(1)
                
                # 2. GŁÓWNY RAPORT
                report += f"🌌 <b>SENTRY ONE v10.0 - RAPORT POCZĄTKOWY</b>\n\n"
                
                report += f"<b>📅 DATA:</b> {now.strftime('%d.%m.%Y %H:%M:%S')}\n"
                report += f"<b>📊 Kalendarz:</b> {astro_date['day']} {astro_date['month_symbol']} {astro_date['month_polish']}\n"
                report += f"<b>{astro_date['element_emoji']} Element:</b> {astro_date['element']}\n\n"
                
                report += f"<b>{moon['emoji']} KSIĘŻYC:</b>\n"
                report += f"• Faza: {moon['name']}\n"
                report += f"• Oświetlenie: {moon['illumination']:.1f}%\n\n"
                
                # 3. WARSZAWA
                report += f"<b>🏛️ WARSZAWA:</b>\n"
                report += f"🌞 Słońce: {warszawa_times['sun']['rise']} ↑ | {warszawa_times['sun']['set']} ↓\n"
                
                if warszawa_conditions:
                    report += f"📊 Warunki: {warszawa_conditions['emoji']} {warszawa_conditions['status']}\n"
                    report += f"🌡️ Temp: {warszawa_conditions['temperature']:.1f}°C\n"
                    report += f"☁️ Chmury: {warszawa_conditions['cloud_cover']}%\n\n"
                
                # 4. KOSZALIN
                report += f"<b>🌲 KOSZALIN:</b>\n"
                report += f"🌞 Słońce: {koszalin_times['sun']['rise']} ↑ | {koszalin_times['sun']['set']} ↓\n"
                
                if koszalin_conditions:
                    report += f"📊 Warunki: {koszalin_conditions['emoji']} {koszalin_conditions['status']}\n"
                    report += f"🌡️ Temp: {koszalin_conditions['temperature']:.1f}°C\n"
                    report += f"☁️ Chmury: {koszalin_conditions['cloud_cover']}%\n\n"
                
                # 5. USTAWIENIA
                report += f"<b>🔔 TWOJE USTAWIENIA:</b>\n"
                report += f"• Powiadomienia satelitarne: {'✅ WŁĄCZONE' if user_settings['satellite_notifications'] else '❌ WYŁĄCZONE'}\n"
                report += f"• Alerty obserwacyjne: {'✅ WŁĄCZONE' if user_settings['observation_alerts'] else '❌ WYŁĄCZONE'}\n\n"
                
                # 6. KOMENDY
                report += f"<b>🚀 KOMENDY:</b>\n"
                report += f"<code>/nasa</code> - Zdjęcie dnia NASA\n"
                report += f"<code>/satellites on/off</code> - Powiadomienia o satelitach\n"
                report += f"<code>/alerts on/off</code> - Alerty obserwacyjne\n"
                report += f"<code>/iss</code> - Przeloty ISS\n"
                report += f"<code>/moon</code> - Szczegóły Księżyca\n"
                report += f"<code>/weather [miasto]</code> - Prognoza\n"
                report += f"<code>/help</code> - Wszystkie komendy\n"
                
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
                    send_telegram_message(chat_id, "✅ <b>POWIADOMIENIA SATELITARNE WŁĄCZONE</b>\n\nBędziesz otrzymywać powiadomienia o przelotach ISS nad Warszawą.")
                
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
                # Informacja o ISS bez automatycznych powiadomień
                response = (
                    f"🛰️ <b>MIĘDZYNARODOWA STACJA KOSMICZNA</b>\n\n"
                    f"Aktualnie system monitoruje przeloty ISS nad Warszawą.\n\n"
                    f"<b>Użyj komend:</b>\n"
                    f"<code>/satellites on</code> - włącz powiadomienia o przelotach\n"
                    f"<code>/satellites off</code> - wyłącz powiadomienia\n\n"
                    f"<i>Powiadomienia są wysyłane tylko gdy ISS jest widoczna nad Warszawą w ciągu najbliższych 2 godzin.</i>"
                )
                send_telegram_message(chat_id, response)
            
            elif text == "/moon":
                moon = calculate_moon_phase()
                
                response = (
                    f"{moon['emoji']} <b>SZCZEGÓŁOWY RAPORT KSIĘŻYCA</b>\n\n"
                    f"• <b>Faza:</b> {moon['name']}\n"
                    f"• <b>Oświetlenie:</b> {moon['illumination']:.1f}%\n"
                    f"• <b>Wiek:</b> {moon['age_days']:.2f} dni\n\n"
                    
                    f"<b>Najlepsze warunki do obserwacji:</b>\n"
                    f"• Faza: 30-70% (pierwsza/ostatnia kwadra)\n"
                    f"• Księżyc nisko nad horyzontem\n"
                    f"• Noc bezchmurna\n"
                )
                send_telegram_message(chat_id, response)
            
            elif text.startswith("/weather"):
                args = text[8:].strip().lower()
                
                if args in ["warszawa", "koszalin"]:
                    conditions = check_city_conditions(args)
                    times = get_sun_moon_times(args)
                    
                    if conditions:
                        response = (
                            f"{conditions['city_emoji']} <b>PROGNOZA - {conditions['city_name'].upper()}</b>\n\n"
                            
                            f"<b>🌡️ AKTUALNIE:</b>\n"
                            f"• {conditions['temperature']:.1f}°C | "
                            f"Chmury: {conditions['cloud_cover']}%\n"
                            f"• Wiatr: {conditions['wind_speed']} m/s | "
                            f"Wilgotność: {conditions['humidity']}%\n"
                            f"• Widoczność: {conditions['visibility']} km\n"
                            f"• Status: {conditions['emoji']} {conditions['status']}\n\n"
                            
                            f"<b>🌞 SŁOŃCE:</b> {times['sun']['rise']} ↑ | {times['sun']['set']} ↓\n\n"
                            
                            f"<b>📊 OCENA OBSERWACYJNA:</b> {conditions['score']}%\n"
                        )
                        send_telegram_message(chat_id, response)
            
            elif text == "/help":
                response = (
                    f"🤖 <b>SENTRY ONE v10.0 - POMOC</b>\n\n"
                    
                    f"<b>🛰️ NASA I SATELITY:</b>\n"
                    f"<code>/nasa</code> - Zdjęcie dnia NASA\n"
                    f"<code>/iss</code> - Informacje o ISS\n\n"
                    
                    f"<b>🔔 POWIADOMIENIA:</b>\n"
                    f"<code>/satellites on/off</code> - Powiadomienia o satelitach\n"
                    f"<code>/alerts on/off</code> - Alerty obserwacyjne\n\n"
                    
                    f"<b>🌌 ASTRONOMIA:</b>\n"
                    f"<code>/moon</code> - Szczegóły Księżyca\n\n"
                    
                    f"<b>🌤️ POGODA:</b>\n"
                    f"<code>/weather warszawa/koszalin</code> - Prognoza\n\n"
                    
                    f"<b>📍 OBSERWOWANE MIASTA:</b>\n"
                    f"• warszawa\n• koszalin\n\n"
                    
                    f"<i>🤖 System działa 24/7 z NASA, N2YO i OpenWeather API</i>"
                )
                send_telegram_message(chat_id, response)
            
            else:
                response = (
                    f"🤖 <b>SENTRY ONE v10.0</b>\n\n"
                    f"Ultimate astrometeorological monitoring system\n\n"
                    f"<b>📍 Obserwowane miasta:</b>\n"
                    f"🏛️ Warszawa | 🌲 Koszalin\n\n"
                    f"<i>Użyj /start dla pełnego raportu lub /help dla listy komend</i>"
                )
                send_telegram_message(chat_id, response)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Błąd webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== AUTO-PING SYSTEM ======================
class AutoPingService:
    """Serwis do automatycznego pingowania bez spamowania użytkowników"""
    
    def __init__(self):
        self.ping_count = 0
        self.last_ping = None
        
    def start_auto_ping(self):
        """Uruchom automatyczne pingowanie w osobnym wątku"""
        def ping_loop():
            while True:
                try:
                    # Pinguj co 10 minut (600 sekund)
                    time.sleep(600)
                    
                    # Ping tylko główną stronę - NIE wysyłaj do użytkowników!
                    response = requests.get(RENDER_URL, timeout=30)
                    self.ping_count += 1
                    self.last_ping = datetime.now()
                    
                    logger.info(f"📡 Auto-ping #{self.ping_count} - Status: {response.status_code}")
                    
                    # Raz dziennie wyślij status do admina (opcjonalnie)
                    if self.ping_count % 144 == 0:  # Co 144 pingi = 24 godziny
                        self.send_daily_status()
                        
                except Exception as e:
                    logger.error(f"❌ Błąd auto-ping: {e}")
        
        # Uruchom wątki
        threading.Thread(target=ping_loop, daemon=True).start()
        print("✅ Auto-ping service uruchomiony (co 10 minut)")
    
    def send_daily_status(self):
        """Wyślij dzienny raport statusu (opcjonalnie do admina)"""
        try:
            users = get_all_users_with_notifications()
            status_msg = (
                f"📊 <b>DAILY STATUS - SENTRY ONE v10.0</b>\n\n"
                f"• Ping count: {self.ping_count}\n"
                f"• Last ping: {self.last_ping.strftime('%H:%M:%S')}\n"
                f"• Users with notifications: {len(users)}\n"
                f"• System: ACTIVE ✅\n\n"
                f"<i>Automatic daily report</i>"
            )
            
            # Tylko jeśli chcesz otrzymywać te raporty - odkomentuj poniższą linię
            # send_telegram_message(TWÓJ_CHAT_ID, status_msg)
            
        except Exception as e:
            logger.error(f"❌ Błąd daily status: {e}")

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 SENTRY ONE v10.0 - ULTIMATE SYSTEM")
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
    
    # Uruchom auto-ping service
    ping_service = AutoPingService()
    ping_service.start_auto_ping()
    
    print("\n" + "=" * 60)
    print("✅ SYSTEM URUCHOMIONY POMYŚLNIE")
    print("=" * 60)
    print("\n📡 Endpointy dostępne:")
    print(f"• {RENDER_URL}/ - Strona główna")
    print(f"• {RENDER_URL}/ping - Ping (NIE wysyła powiadomień!)")
    print(f"• {RENDER_URL}/health - Status zdrowia")
    print(f"• {RENDER_URL}/status - Status systemu")
    print(f"• {WEBHOOK_URL} - Webhook Telegram")
    print("\n🔔 Powiadomienia są WYŁĄCZONE domyślnie!")
    print("   Użyj /satellites on lub /alerts on aby włączyć")
    print("\n🤖 Bot będzie aktywny 24/7 dzięki inteligentnemu pingowaniu")
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )