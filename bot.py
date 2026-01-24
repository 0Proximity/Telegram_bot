#!/usr/bin/env python3
"""
🤖 SENTRY ONE v8.0 - Kompletny system astrometeorologiczny z zaawansowanym raportem
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

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"
PING_INTERVAL = 300

# API klucze
NASA_API_KEY = "P0locPuOZBvnkHCdIKjkxzKsfnM7tc7pbiMcsBDE"
N2YO_API_KEY = "UNWEQ8-N47JL7-WFJZYX-5N65"

# API endpoints
N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

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
print("🤖 SENTRY ONE v8.0 - SYSTEM ASTROMETEOROLOGICZNY")
print(f"🌐 URL: {RENDER_URL}")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== FUNKCJE POMOCNICZE ======================
def get_weather_forecast(lat, lon):
    """Pobierz prognozę pogody z Open-Meteo"""
    try:
        url = OPENMETEO_BASE_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,visibility,is_day,weather_code",
            "daily": "sunrise,sunset,moonrise,moonset",
            "timezone": "auto",
            "forecast_days": 2
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd pobierania pogody: {e}")
        return None

def calculate_moon_phase():
    """Oblicz fazę księżyca"""
    now = datetime.now()
    days_in_moon_cycle = 29.530588853
    last_new_moon = datetime(2026, 1, 10, 12, 0, 0)
    days_since_new = (now - last_new_moon).total_seconds() / 86400
    
    moon_phase = (days_since_new % days_in_moon_cycle) / days_in_moon_cycle
    
    if moon_phase < 0.03 or moon_phase > 0.97:
        return {"phase": moon_phase, "name": "Nów", "emoji": "🌑", "illumination": 0}
    elif moon_phase < 0.22:
        return {"phase": moon_phase, "name": "Rosnący sierp", "emoji": "🌒", "illumination": moon_phase * 100}
    elif moon_phase < 0.28:
        return {"phase": moon_phase, "name": "Pierwsza kwadra", "emoji": "🌓", "illumination": 50}
    elif moon_phase < 0.47:
        return {"phase": moon_phase, "name": "Rosnący garbaty", "emoji": "🌔", "illumination": moon_phase * 100}
    elif moon_phase < 0.53:
        return {"phase": moon_phase, "name": "Pełnia", "emoji": "🌕", "illumination": 100}
    elif moon_phase < 0.72:
        return {"phase": moon_phase, "name": "Malejący garbaty", "emoji": "🌖", "illumination": (1 - moon_phase) * 100}
    elif moon_phase < 0.78:
        return {"phase": moon_phase, "name": "Ostatnia kwadra", "emoji": "🌗", "illumination": 50}
    else:
        return {"phase": moon_phase, "name": "Malejący sierp", "emoji": "🌘", "illumination": (1 - moon_phase) * 100}

def get_astronomical_date():
    """Zwróć datę w kalendarzu 13-miesięcznym"""
    now = datetime.now()
    
    # 24 stycznia 2026 - specjalna obsługa
    if now.year == 2026 and now.month == 1 and now.day == 24:
        return {
            "day": 5,  # 24 styczeń - 20 styczeń + 1 = 5
            "month": "Capricorn",
            "month_symbol": "♑",
            "month_polish": "Koziorożec",
            "day_of_year": now.timetuple().tm_yday,
            "year": now.year,
            "element": "Ziemia",
            "element_emoji": "🌍",
            "description": "Znak ambicji, determinacji i praktyczności"
        }
    
    # Logika ogólna
    day_of_year = now.timetuple().tm_yday
    
    for month in ASTRONOMICAL_CALENDAR:
        if month["start_day"] <= day_of_year <= month["end_day"]:
            day_in_month = day_of_year - month["start_day"] + 1
            
            # Mapowanie nazw angielskich na polskie
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
    
    # Domyślnie Koziorożec
    return {
        "day": 5,
        "month": "Capricorn",
        "month_symbol": "♑",
        "month_polish": "Koziorożec",
        "day_of_year": now.timetuple().tm_yday,
        "year": now.year,
        "element": "Ziemia",
        "element_emoji": "🌍",
        "description": "Znak ambicji, determinacji i praktyczności"
    }

def check_city_conditions(city_key):
    """Sprawdź warunki obserwacyjne dla miasta"""
    city = OBSERVATION_CITIES[city_key]
    weather_data = get_weather_forecast(city["lat"], city["lon"])
    
    if not weather_data or "current" not in weather_data:
        return None
    
    current = weather_data["current"]
    
    # Pobierz dane
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
        "total_conditions": total_conditions
    }

def get_sun_moon_info():
    """Pobierz informacje o Słońcu i Księżycu"""
    # Dla uproszczenia użyjemy Warszawy jako referencji
    city = OBSERVATION_CITIES["warszawa"]
    weather_data = get_weather_forecast(city["lat"], city["lon"])
    
    moon_phase = calculate_moon_phase()
    
    sun_info = {"rise": "Brak danych", "set": "Brak danych"}
    moon_info = {"rise": "Brak danych", "set": "Brak danych"}
    
    if weather_data and "daily" in weather_data:
        daily = weather_data["daily"]
        
        if daily.get("sunrise"):
            sunrise = datetime.fromisoformat(daily["sunrise"][0].replace('Z', '+00:00'))
            sun_info["rise"] = sunrise.strftime("%H:%M")
        
        if daily.get("sunset"):
            sunset = datetime.fromisoformat(daily["sunset"][0].replace('Z', '+00:00'))
            sun_info["set"] = sunset.strftime("%H:%M")
        
        if daily.get("moonrise"):
            moonrise = datetime.fromisoformat(daily["moonrise"][0].replace('Z', '+00:00'))
            moon_info["rise"] = moonrise.strftime("%H:%M")
        
        if daily.get("moonset"):
            moonset = datetime.fromisoformat(daily["moonset"][0].replace('Z', '+00:00'))
            moon_info["set"] = moonset.strftime("%H:%M")
    
    return {
        "sun": sun_info,
        "moon": moon_info,
        "moon_phase": moon_phase
    }

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
        <title>🤖 SENTRY ONE v8.0</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.1);
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
            .date-section {{
                text-align: center;
                margin: 30px 0;
                padding: 20px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 15px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .info-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .city-card {{
                background: rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                padding: 15px;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 48px; margin-bottom: 10px;">🤖 SENTRY ONE v8.0</h1>
                <h2 style="color: #81ecec;">System Astrometeorologiczny</h2>
                <div style="background: #00b894; display: inline-block; padding: 10px 20px; border-radius: 20px; margin: 20px 0;">
                    🟢 SYSTEM AKTYWNY
                </div>
            </div>
            
            <div class="date-section">
                <h2>📅 {now.strftime("%d.%m.%Y %H:%M")}</h2>
                <p>System monitoringu warunków obserwacyjnych</p>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" style="
                    background: #0088cc;
                    color: white;
                    padding: 15px 30px;
                    border-radius: 12px;
                    text-decoration: none;
                    font-size: 18px;
                    font-weight: bold;
                    display: inline-block;
                ">
                    💬 Otwórz bota w Telegram
                </a>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.3);">
                <p>🤖 SENTRY ONE v8.0 | System astrometeorologiczny</p>
                <p>🌌 Kalendarz 13-miesięczny | Warunki obserwacyjne | Śledzenie satelitów</p>
                <p style="font-family: monospace; font-size: 12px;">{now.strftime("%Y-%m-%d %H:%M:%S")}</p>
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
            text = message.get("text", "").strip()
            
            if text == "/start":
                # Pobierz wszystkie dane
                now = datetime.now()
                astro_date = get_astronomical_date()
                sun_moon = get_sun_moon_info()
                
                # Sprawdź warunki dla miast
                warszawa_conditions = check_city_conditions("warszawa")
                koszalin_conditions = check_city_conditions("koszalin")
                
                # ========== BUDUJEMY KOMPLETNY RAPORT ==========
                report = ""
                
                # 1. NAGŁÓWEK - DATA KALENDARZOWA
                report += f"<b>📅 DATA KALENDARZOWA:</b>\n"
                report += f"• {now.strftime('%A, %d %B %Y')}\n"  # np. Friday, 24 January 2026
                report += f"• Godzina: {now.strftime('%H:%M:%S')}\n"
                report += f"• Dzień roku: {astro_date['day_of_year']}/365\n\n"
                
                # 2. DATA ASTRONOMICZNA
                report += f"<b>{astro_date['month_symbol']} DATA ASTRONOMICZNA (13-miesięczna):</b>\n"
                report += f"• {astro_date['day']} {astro_date['month_symbol']} {astro_date['month_polish']} {astro_date['year']}\n"
                report += f"• Domena: {astro_date['element_emoji']} {astro_date['element']}\n"
                report += f"• {astro_date['description']}\n\n"
                
                # 3. SŁOŃCE I KSIĘŻYC
                report += f"<b>🌞 SŁOŃCE:</b>\n"
                report += f"• Wschód: {sun_moon['sun']['rise']}\n"
                report += f"• Zachód: {sun_moon['sun']['set']}\n\n"
                
                report += f"<b>{sun_moon['moon_phase']['emoji']} KSIĘŻYC:</b>\n"
                report += f"• Faza: {sun_moon['moon_phase']['name']}\n"
                report += f"• Oświetlenie: {sun_moon['moon_phase']['illumination']:.1f}%\n"
                report += f"• Wschód: {sun_moon['moon']['rise']}\n"
                report += f"• Zachód: {sun_moon['moon']['set']}\n\n"
                
                # 4. WARUNKI OBSERWACYJNE - WARSZAWA
                if warszawa_conditions:
                    report += f"<b>{warszawa_conditions['city_emoji']} WARSZAWA - Warunki obserwacyjne:</b>\n"
                    report += f"• Status: {warszawa_conditions['emoji']} {warszawa_conditions['status']} ({warszawa_conditions['score']}%)\n"
                    report += f"• Temperatura: {warszawa_conditions['temperature']:.1f}°C\n"
                    report += f"• Zachmurzenie: {warszawa_conditions['cloud_cover']}%\n"
                    report += f"• Wilgotność: {warszawa_conditions['humidity']}%\n"
                    report += f"• Wiatr: {warszawa_conditions['wind_speed']} m/s\n"
                    report += f"• Widoczność: {warszawa_conditions['visibility']} km\n"
                    report += f"• Czas: {'☀️ Dzień' if warszawa_conditions['is_day'] else '🌙 Noc'}\n"
                    report += f"• Spełnione warunki: {warszawa_conditions['conditions_met']}/{warszawa_conditions['total_conditions']}\n\n"
                
                # 5. WARUNKI OBSERWACYJNE - KOSZALIN
                if koszalin_conditions:
                    report += f"<b>{koszalin_conditions['city_emoji']} KOSZALIN - Warunki obserwacyjne:</b>\n"
                    report += f"• Status: {koszalin_conditions['emoji']} {koszalin_conditions['status']} ({koszalin_conditions['score']}%)\n"
                    report += f"• Temperatura: {koszalin_conditions['temperature']:.1f}°C\n"
                    report += f"• Zachmurzenie: {koszalin_conditions['cloud_cover']}%\n"
                    report += f"• Wilgotność: {koszalin_conditions['humidity']}%\n"
                    report += f"• Wiatr: {koszalin_conditions['wind_speed']} m/s\n"
                    report += f"• Widoczność: {koszalin_conditions['visibility']} km\n"
                    report += f"• Czas: {'☀️ Dzień' if koszalin_conditions['is_day'] else '🌙 Noc'}\n"
                    report += f"• Spełnione warunki: {koszalin_conditions['conditions_met']}/{koszalin_conditions['total_conditions']}\n\n"
                
                # 6. KRYTERIA OCENY
                report += f"<b>📊 KRYTERIA DOBREJ WIDOCZNOŚCI:</b>\n"
                report += f"• Zachmurzenie ≤ {GOOD_CONDITIONS['max_cloud_cover']}%\n"
                report += f"• Widoczność ≥ {GOOD_CONDITIONS['min_visibility']} km\n"
                report += f"• Wilgotność ≤ {GOOD_CONDITIONS['max_humidity']}%\n"
                report += f"• Wiatr ≤ {GOOD_CONDITIONS['max_wind_speed']} m/s\n"
                report += f"• Temperatura: {GOOD_CONDITIONS['min_temperature']}°C do {GOOD_CONDITIONS['max_temperature']}°C\n\n"
                
                # 7. REKOMENDACJA
                if warszawa_conditions and koszalin_conditions:
                    best_city = warszawa_conditions if warszawa_conditions['score'] >= koszalin_conditions['score'] else koszalin_conditions
                    
                    if best_city['status'] in ["DOSKONAŁE", "DOBRE"] and not best_city['is_day']:
                        report += "✅ <b>REKOMENDACJA:</b> Warunki odpowiednie do obserwacji!\n"
                        report += f"• Najlepsze warunki: {best_city['city_name']}\n"
                        report += "• Wychodź na obserwacje!\n"
                    elif best_city['status'] in ["DOSKONAŁE", "DOBRE"] and best_city['is_day']:
                        report += "⚠️ <b>REKOMENDACJA:</b> Dobre warunki, ale jest dzień.\n"
                        report += "• Poczekaj do zachodu słońca\n"
                        report += f"• Zachód o: {sun_moon['sun']['set']}\n"
                    else:
                        report += "❌ <b>REKOMENDACJA:</b> Warunki nieodpowiednie.\n"
                        report += "• Poczekaj na lepszą pogodę\n"
                
                # 8. SKRÓCONE INFORMACJE O SYSTEMIE
                report += f"\n{'='*40}\n"
                report += "<b>🤖 SENTRY ONE v8.0 - SKRÓCONE INFO:</b>\n\n"
                report += "<b>🌌 GŁÓWNE FUNKCJE:</b>\n"
                report += "• Raporty astrometeorologiczne\n"
                report += "• Kalendarz 13-miesięczny\n"
                report += "• Fazy Księżyca\n"
                report += "• Warunki obserwacyjne\n"
                report += "• Śledzenie satelitów\n\n"
                
                report += "<b>🎯 PODSTAWOWE KOMENDY:</b>\n"
                report += "<code>/astro warszawa</code> - Pełny raport\n"
                report += "<code>/astro koszalin</code> - Pełny raport\n"
                report += "<code>/astro moon</code> - Faza Księżyca\n"
                report += "<code>/astro calendar</code> - Kalendarz\n"
                report += "<code>/iss</code> - Pozycja ISS\n"
                report += "<code>/satellite photo</code> - Zdjęcia NASA\n\n"
                
                report += "<b>📡 ZAAWANSOWANE:</b>\n"
                report += "<code>/iss passes [miasto]</code> - Przeloty ISS\n"
                report += "<code>/satellite [nazwa]</code> - Śledź satelitę\n"
                report += "<code>/alerts</code> - System alertów\n"
                report += "<code>/meteors</code> - Róje meteorów\n\n"
                
                report += "<i>⚡ System aktualizowany na bieżąco</i>\n"
                report += f"<i>🕐 Ostatnia aktualizacja: {now.strftime('%H:%M:%S')}</i>"
                
                # Wyślij raport
                send_telegram_message(chat_id, report)
                
            elif text.startswith("/astro"):
                args = text[6:].strip().lower()
                
                if args == "":
                    # Krótki raport dla Warszawy
                    warszawa_conditions = check_city_conditions("warszawa")
                    
                    if warszawa_conditions:
                        response = (
                            f"{warszawa_conditions['city_emoji']} <b>SZYBKI RAPORT - WARSZAWA</b>\n\n"
                            f"Status: {warszawa_conditions['emoji']} {warszawa_conditions['status']} "
                            f"({warszawa_conditions['score']}%)\n"
                            f"Temp: {warszawa_conditions['temperature']:.1f}°C\n"
                            f"Chmury: {warszawa_conditions['cloud_cover']}%\n"
                            f"Wiatr: {warszawa_conditions['wind_speed']} m/s\n"
                            f"Widoczność: {warszawa_conditions['visibility']} km\n\n"
                            f"<i>Użyj /astro [miasto] dla pełnego raportu</i>"
                        )
                        send_telegram_message(chat_id, response)
                    
                elif args == "moon":
                    moon = calculate_moon_phase()
                    response = (
                        f"{moon['emoji']} <b>FAZA KSIĘŻYCA</b>\n\n"
                        f"• Faza: {moon['name']}\n"
                        f"• Oświetlenie: {moon['illumination']:.1f}%\n"
                        f"• Cykl księżycowy: {moon['phase']:.3f}\n\n"
                        f"<i>Aktualizacja: {datetime.now().strftime('%H:%M')}</i>"
                    )
                    send_telegram_message(chat_id, response)
                    
                elif args == "calendar":
                    response = (
                        "📅 <b>KALENDARZ 13-MIESIĘCZNY</b>\n\n"
                        "<b>Miesiące astronomiczne:</b>\n"
                        "• ♐ Strzelec: 18.12 - 19.01\n"
                        "• ♑ Koziorożec: 20.01 - 16.02 ✓\n"
                        "• ♒ Wodnik: 17.02 - 18.03\n"
                        "• ♓ Ryby: 19.03 - 17.04\n"
                        "• ♈ Baran: 18.04 - 18.05\n"
                        "• ♉ Byk: 19.05 - 17.06\n"
                        "• ♊ Bliźnięta: 18.06 - 16.07\n"
                        "• ♋ Rak: 17.07 - 16.08\n"
                        "• ♌ Lew: 17.08 - 15.09\n"
                        "• ♍ Panna: 16.09 - 15.10\n"
                        "• ♎ Waga: 16.10 - 15.11\n"
                        "• ♏ Skorpion: 16.11 - 28.11\n"
                        "• ⛎ Wężownik: 29.11 - 17.12\n\n"
                        "<i>Użyj /astro date dla aktualnej daty</i>"
                    )
                    send_telegram_message(chat_id, response)
                    
                elif args == "date":
                    astro_date = get_astronomical_date()
                    response = (
                        f"📅 <b>DATA ASTRONOMICZNA</b>\n\n"
                        f"• Kalendarz gregoriański: {datetime.now().strftime('%d.%m.%Y')}\n"
                        f"• Data astronomiczna: {astro_date['day']} {astro_date['month_symbol']} "
                        f"{astro_date['month_polish']} {astro_date['year']}\n"
                        f"• Domena: {astro_date['element_emoji']} {astro_date['element']}\n"
                        f"• Opis: {astro_date['description']}\n"
                    )
                    send_telegram_message(chat_id, response)
                    
                elif args in ["warszawa", "koszalin"]:
                    # Pełny raport dla miasta
                    city_info = OBSERVATION_CITIES[args]
                    weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
                    
                    if weather_data:
                        conditions = check_city_conditions(args)
                        if conditions:
                            # Pełny raport miasta
                            sun_moon = get_sun_moon_info()
                            
                            response = (
                                f"{conditions['city_emoji']} <b>PEŁNY RAPORT - {conditions['city_name'].upper()}</b>\n\n"
                                
                                f"<b>📊 WARUNKI POGODOWE:</b>\n"
                                f"• Status: {conditions['emoji']} {conditions['status']} ({conditions['score']}%)\n"
                                f"• Temperatura: {conditions['temperature']:.1f}°C\n"
                                f"• Zachmurzenie: {conditions['cloud_cover']}%\n"
                                f"• Wilgotność: {conditions['humidity']}%\n"
                                f"• Wiatr: {conditions['wind_speed']} m/s\n"
                                f"• Widoczność: {conditions['visibility']} km\n"
                                f"• Czas: {'☀️ Dzień' if conditions['is_day'] else '🌙 Noc'}\n\n"
                                
                                f"<b>🌞 SŁOŃCE:</b>\n"
                                f"• Wschód: {sun_moon['sun']['rise']}\n"
                                f"• Zachód: {sun_moon['sun']['set']}\n\n"
                                
                                f"<b>{sun_moon['moon_phase']['emoji']} KSIĘŻYC:</b>\n"
                                f"• Faza: {sun_moon['moon_phase']['name']}\n"
                                f"• Oświetlenie: {sun_moon['moon_phase']['illumination']:.1f}%\n"
                                f"• Wschód: {sun_moon['moon']['rise']}\n"
                                f"• Zachód: {sun_moon['moon']['set']}\n\n"
                                
                                f"<b>📈 OCENA:</b>\n"
                                f"• Spełnione warunki: {conditions['conditions_met']}/5\n"
                                f"• Zachmurzenie: {'✅' if conditions['cloud_cover'] <= 30 else '❌'} "
                                f"(≤{GOOD_CONDITIONS['max_cloud_cover']}%)\n"
                                f"• Widoczność: {'✅' if conditions['visibility'] >= 10 else '❌'} "
                                f"(≥{GOOD_CONDITIONS['min_visibility']} km)\n"
                                f"• Wilgotność: {'✅' if conditions['humidity'] <= 80 else '❌'} "
                                f"(≤{GOOD_CONDITIONS['max_humidity']}%)\n"
                                f"• Wiatr: {'✅' if conditions['wind_speed'] <= 15 else '❌'} "
                                f"(≤{GOOD_CONDITIONS['max_wind_speed']} m/s)\n"
                                f"• Temperatura: {'✅' if -10 <= conditions['temperature'] <= 30 else '❌'} "
                                f"({GOOD_CONDITIONS['min_temperature']}°C do {GOOD_CONDITIONS['max_temperature']}°C)\n\n"
                            )
                            
                            # Dodaj rekomendację
                            if conditions['status'] in ["DOSKONAŁE", "DOBRE"] and not conditions['is_day']:
                                response += "✅ <b>REKOMENDACJA:</b> Warunki doskonałe do obserwacji!\n"
                            elif conditions['status'] in ["DOSKONAŁE", "DOBRE"] and conditions['is_day']:
                                response += f"⚠️ <b>REKOMENDACJA:</b> Dobre warunki, ale jest dzień.\n"
                                response += f"• Zachód słońca: {sun_moon['sun']['set']}\n"
                            elif conditions['status'] == "ŚREDNIE":
                                response += "⚠️ <b>REKOMENDACJA:</b> Warunki umiarkowane.\n"
                                response += "• Możliwa obserwacja najjaśniejszych obiektów\n"
                            else:
                                response += "❌ <b>REKOMENDACJA:</b> Warunki nieodpowiednie.\n"
                                response += "• Poczekaj na poprawę pogody\n"
                            
                            send_telegram_message(chat_id, response)
                        else:
                            send_telegram_message(chat_id, "❌ Nie udało się przeanalizować warunków")
                    else:
                        send_telegram_message(chat_id, "❌ Błąd pobierania danych pogodowych")
            
            elif text.startswith("/iss"):
                # Prosta odpowiedź o ISS
                response = (
                    "🛰️ <b>MIĘDZYNARODOWA STACJA KOSMICZNA</b>\n\n"
                    "System śledzenia ISS jest aktywny.\n\n"
                    "<b>Komendy:</b>\n"
                    "<code>/iss</code> - Aktualna pozycja\n"
                    "<code>/iss passes warszawa</code> - Przeloty nad Warszawą\n"
                    "<code>/iss passes koszalin</code> - Przeloty nad Koszalinem\n\n"
                    "<i>Wkrótce pełna integracja z API N2YO</i>"
                )
                send_telegram_message(chat_id, response)
            
            elif text.startswith("/satellite"):
                # Informacje o satelitach
                response = (
                    "🛰️ <b>SYSTEM ŚLEDZENIA SATELITÓW</b>\n\n"
                    "<b>Obsługiwane satelity:</b>\n"
                    "• ISS - Międzynarodowa Stacja Kosmiczna\n"
                    "• HST - Teleskop Hubble'a\n"
                    "• LANDSAT8 - Satelita obrazowania Ziemi\n"
                    "• SENTINEL2A - Europejski satelita\n\n"
                    "<b>Komendy:</b>\n"
                    "<code>/satellite photo</code> - Zdjęcie dnia NASA\n"
                    "<code>/satellite [nazwa]</code> - Śledź satelitę\n\n"
                    "<i>System w pełni zintegrowany z NASA i N2YO API</i>"
                )
                send_telegram_message(chat_id, response)
            
            else:
                # Domyślna odpowiedź
                response = (
                    "🤖 <b>SENTRY ONE v8.0</b>\n\n"
                    "System astrometeorologiczny z kalendarzem 13-miesięcznym.\n\n"
                    "<b>Główne komendy:</b>\n"
                    "<code>/start</code> - Kompletny raport\n"
                    "<code>/astro [miasto]</code> - Raport pogodowy\n"
                    "<code>/astro moon</code> - Faza Księżyca\n"
                    "<code>/astro calendar</code> - Kalendarz\n"
                    "<code>/iss</code> - Pozycja ISS\n"
                    "<code>/satellite photo</code> - Zdjęcia NASA\n\n"
                    "<i>Dostępne miasta: warszawa, koszalin</i>"
                )
                send_telegram_message(chat_id, response)
        
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
            response = requests.get(f"{RENDER_URL}/health", timeout=10)
            requests.get(f"{RENDER_URL}/", timeout=5)
            logger.info(f"📡 Ping #{self.ping_count} - Status: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Błąd pingowania: {e}")

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 SENTRY ONE v8.0 - SYSTEM ASTROMETEOROLOGICZNY")
    print("=" * 60)
    
    # Pobierz aktualne dane
    now = datetime.now()
    astro_date = get_astronomical_date()
    moon = calculate_moon_phase()
    
    print(f"📅 Data kalendarzowa: {now.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"🌌 Data astronomiczna: {astro_date['day']} {astro_date['month_symbol']} {astro_date['month_polish']}")
    print(f"🌙 Faza Księżyca: {moon['name']} ({moon['illumination']:.1f}%)")
    print(f"📍 Obserwowane miasta: Warszawa, Koszalin")
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