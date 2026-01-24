#!/usr/bin/env python3
"""
🤖 SENTRY ONE v5.0 - z zaawansowaną astrometeorologią
Render.com Telegram Bot z obserwacją astronomiczną
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
PING_INTERVAL = 300  # 5 minut (300 sekund)

# Konfiguracja Open-Meteo (BEZPŁATNE API)
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Miasta do obserwacji astronomicznych
OBSERVATION_CITIES = {
    "warszawa": {
        "name": "Warszawa",
        "lat": 52.2297,
        "lon": 21.0122,
        "timezone": "Europe/Warsaw"
    },
    "koszalin": {
        "name": "Koszalin",
        "lat": 54.1943,
        "lon": 16.1712,
        "timezone": "Europe/Warsaw"
    }
}

# Próg dobrej widoczności dla obserwacji astronomicznych
GOOD_CONDITIONS = {
    "max_cloud_cover": 30,      # Maksymalne zachmurzenie w %
    "min_visibility": 10,       # Minimalna widoczność w km
    "max_humidity": 80,         # Maksymalna wilgotność w %
    "max_wind_speed": 15,       # Maksymalna prędkość wiatru w m/s
    "min_temperature": -10,     # Minimalna temperatura w °C
    "max_temperature": 30       # Maksymalna temperatura w °C
}

# Kalendarz 13-miesięczny (astronomiczny)
ASTRONOMICAL_MONTHS = [
    {"name": "Ophiuchus", "days": 28, "symbol": "⛎", "element": "Fire", "dates": "Nov 29 - Dec 17"},
    {"name": "Sagittarius", "days": 31, "symbol": "♐", "element": "Fire", "dates": "Dec 18 - Jan 19"},
    {"name": "Capricorn", "days": 28, "symbol": "♑", "element": "Earth", "dates": "Jan 20 - Feb 16"},
    {"name": "Aquarius", "days": 30, "symbol": "♒", "element": "Air", "dates": "Feb 17 - Mar 18"},
    {"name": "Pisces", "days": 29, "symbol": "♓", "element": "Water", "dates": "Mar 19 - Apr 17"},
    {"name": "Aries", "days": 31, "symbol": "♈", "element": "Fire", "dates": "Apr 18 - May 18"},
    {"name": "Taurus", "days": 30, "symbol": "♉", "element": "Earth", "dates": "May 19 - Jun 17"},
    {"name": "Gemini", "days": 29, "symbol": "♊", "element": "Air", "dates": "Jun 18 - Jul 16"},
    {"name": "Cancer", "days": 31, "symbol": "♋", "element": "Water", "dates": "Jul 17 - Aug 16"},
    {"name": "Leo", "days": 30, "symbol": "♌", "element": "Fire", "dates": "Aug 17 - Sep 15"},
    {"name": "Virgo", "days": 29, "symbol": "♍", "element": "Earth", "dates": "Sep 16 - Oct 15"},
    {"name": "Libra", "days": 31, "symbol": "♎", "element": "Air", "dates": "Oct 16 - Nov 15"},
    {"name": "Scorpio", "days": 30, "symbol": "♏", "element": "Water", "dates": "Nov 16 - Nov 28"}
]

# Typy chmur i ich opisy
CLOUD_TYPES = {
    "Cirrus": {"emoji": "🌤️", "description": "Cienkie, włókniste chmury wysokie", "altitude": "6-12 km"},
    "Cirrocumulus": {"emoji": "🌤️", "description": "Drobne, kłębiaste chmury wysokie", "altitude": "6-12 km"},
    "Cirrostratus": {"emoji": "🌥️", "description": "Cienka, mglista warstwa wysoka", "altitude": "6-12 km"},
    "Altocumulus": {"emoji": "🌥️", "description": "Średnie chmury kłębiaste", "altitude": "2-6 km"},
    "Altostratus": {"emoji": "☁️", "description": "Szara lub niebieskawa warstwa średnia", "altitude": "2-6 km"},
    "Stratus": {"emoji": "🌫️", "description": "Niska, jednolita warstwa mglista", "altitude": "0-2 km"},
    "Stratocumulus": {"emoji": "☁️", "description": "Niskie chmury w postaci płatów", "altitude": "0-2 km"},
    "Nimbostratus": {"emoji": "🌧️", "description": "Ciemna warstwa dająca opady", "altitude": "0-3 km"},
    "Cumulus": {"emoji": "⛅", "description": "Białe, puszyste chmury konwekcyjne", "altitude": "0-2 km"},
    "Cumulonimbus": {"emoji": "⛈️", "description": "Potężne chmury burzowe", "altitude": "0-16 km"}
}

print("=" * 60)
print("🤖 SENTRY ONE v5.0 - ZAWIERA ASTROMETEOROLOGIĘ")
print(f"🌐 URL: {RENDER_URL}")
print(f"🔗 Webhook: {WEBHOOK_URL}")
print(f"⏰ Ping interval: {PING_INTERVAL}s")
print(f"🌤️  API Pogodowe: Open-Meteo (bezpłatne)")
print(f"🌙 Zawiera: Fazy Księżyca, Typy chmur, Kalendarz 13-miesięczny")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== DANE AGENTÓW ======================
AGENTS = {
    "echo": {"name": "Echo", "status": "online", "type": "phone", "icon": "📱"},
    "vector": {"name": "Vector", "status": "online", "type": "tablet", "icon": "📟"},
    "visor": {"name": "Visor", "status": "offline", "type": "oculus", "icon": "🕶️"},
    "synergic": {"name": "Synergic", "status": "online", "type": "computer", "icon": "💻"},
    "observator": {"name": "Observator", "status": "online", "type": "weather", "icon": "🌌"},
    "lunaris": {"name": "Lunaris", "status": "online", "type": "moon", "icon": "🌙"},
    "nebula": {"name": "Nebula", "status": "online", "type": "clouds", "icon": "☁️"},
    "chronos": {"name": "Chronos", "status": "online", "type": "calendar", "icon": "📅"}
}

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

            # Dodaj zadanie pingowania co 5 minut
            self.scheduler.add_job(self.ping_self, 'interval', seconds=PING_INTERVAL)
            self.scheduler.start()

            # Pierwszy ping natychmiast
            threading.Thread(target=self.ping_self, daemon=True).start()

            self.is_running = True
            print(f"✅ Pingowanie aktywne co {PING_INTERVAL/60} minut")

    def ping_self(self):
        """Wyślij ping do własnego endpointu"""
        try:
            self.ping_count += 1
            self.last_ping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Ping główny endpoint
            response = requests.get(f"{RENDER_URL}/health", timeout=10)

            # Dodatkowy ping do dashboardu
            requests.get(f"{RENDER_URL}/", timeout=5)

            logger.info(f"📡 Ping #{self.ping_count} wysłany o {self.last_ping} - Status: {response.status_code}")

            # Zapisuj logi pingów do pliku (opcjonalnie)
            with open("ping_log.txt", "a") as f:
                f.write(f"{self.last_ping} - Ping #{self.ping_count} - Status: {response.status_code}\n")

        except Exception as e:
            logger.error(f"❌ Błąd pingowania: {e}")

    def get_stats(self):
        """Zwróć statystyki pingowania"""
        return {
            "ping_count": self.ping_count,
            "last_ping": self.last_ping,
            "is_running": self.is_running,
            "interval_seconds": PING_INTERVAL,
            "next_ping_in": PING_INTERVAL - (time.time() % PING_INTERVAL) if self.is_running else None
        }

    def stop(self):
        """Zatrzymaj pingowanie"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("⏹️  Pingowanie zatrzymane")

# Inicjalizacja serwisu pingowania
ping_service = PingService()

# ====================== FUNKCJE ASTRONOMICZNE ======================
def get_weather_forecast(lat, lon):
    """Pobierz prognozę pogody z Open-Meteo z dodatkowymi parametrami"""
    try:
        url = OPENMETEO_BASE_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,wind_direction_10m,visibility,is_day,precipitation,pressure_msl,weather_code",
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,visibility,weather_code,precipitation",
            "daily": "sunrise,sunset,moonrise,moonset,moonphase",
            "timezone": "auto",
            "forecast_days": 3
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd pobierania pogody: {e}")
        return None

def calculate_moon_phase(jd=None):
    """Oblicz fazę księżyca na podstawie daty Julian"""
    if jd is None:
        # Oblicz datę Julian dla teraz
        now = datetime.now()
        a = (14 - now.month) // 12
        y = now.year + 4800 - a
        m = now.month + 12 * a - 3
        jd = now.day + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        
        # Dodaj czas dzienny
        jd += (now.hour - 12) / 24.0 + now.minute / 1440.0 + now.second / 86400.0
    
    # Oblicz wiek księżyca w dniach
    days_since_new = jd - 2451550.1
    moon_phase = days_since_new / 29.530588853
    moon_phase -= math.floor(moon_phase)
    
    # Określ nazwę fazy
    if moon_phase < 0.03 or moon_phase > 0.97:
        return {"phase": 0, "name": "Nów", "emoji": "🌑", "illumination": 0}
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

def determine_cloud_type(weather_code, cloud_cover, humidity, wind_speed):
    """Określ typ dominujących chmur na podstawie kodu pogody i parametrów"""
    # Mapa kodów pogody WMO do typów chmur
    weather_code_map = {
        0: ("Clear sky", "Cirrus"),
        1: ("Mainly clear", "Cirrocumulus"),
        2: ("Partly cloudy", "Altocumulus"),
        3: ("Overcast", "Stratus"),
        45: ("Fog", "Stratus"),
        48: ("Depositing rime fog", "Stratus"),
        51: ("Light drizzle", "Nimbostratus"),
        53: ("Moderate drizzle", "Nimbostratus"),
        55: ("Dense drizzle", "Nimbostratus"),
        56: ("Light freezing drizzle", "Nimbostratus"),
        57: ("Dense freezing drizzle", "Nimbostratus"),
        61: ("Slight rain", "Nimbostratus"),
        63: ("Moderate rain", "Nimbostratus"),
        65: ("Heavy rain", "Nimbostratus"),
        66: ("Light freezing rain", "Nimbostratus"),
        67: ("Heavy freezing rain", "Nimbostratus"),
        71: ("Slight snow fall", "Nimbostratus"),
        73: ("Moderate snow fall", "Nimbostratus"),
        75: ("Heavy snow fall", "Nimbostratus"),
        77: ("Snow grains", "Nimbostratus"),
        80: ("Slight rain showers", "Cumulus"),
        81: ("Moderate rain showers", "Cumulonimbus"),
        82: ("Violent rain showers", "Cumulonimbus"),
        85: ("Slight snow showers", "Cumulus"),
        86: ("Heavy snow showers", "Cumulonimbus"),
        95: ("Thunderstorm", "Cumulonimbus"),
        96: ("Thunderstorm with slight hail", "Cumulonimbus"),
        99: ("Thunderstorm with heavy hail", "Cumulonimbus")
    }
    
    # Domyślny typ chmur
    cloud_type = "Cirrus"
    if weather_code in weather_code_map:
        cloud_type = weather_code_map[weather_code][1]
    
    # Korekta na podstawie zachmurzenia
    if cloud_cover < 10:
        cloud_type = "Cirrus"
    elif cloud_cover < 30:
        if cloud_type in ["Stratus", "Nimbostratus"]:
            cloud_type = "Altocumulus"
    elif cloud_cover < 70:
        if cloud_type in ["Cirrus", "Cirrocumulus"]:
            cloud_type = "Altocumulus"
    else:
        if cloud_type in ["Cirrus", "Cirrocumulus", "Altocumulus"]:
            cloud_type = "Stratus"
    
    # Korekta na podstawie wilgotności
    if humidity > 80 and cloud_type in ["Cirrus", "Cirrocumulus", "Cirrostratus"]:
        cloud_type = "Altostratus"
    
    # Korekta na podstawie wiatru
    if wind_speed > 10 and cloud_type in ["Stratus", "Stratocumulus"]:
        cloud_type = "Altocumulus"
    
    return cloud_type

def get_astronomical_date():
    """Zwróć datę w kalendarzu 13-miesięcznym (astronomicznym)"""
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    
    # Oblicz, w którym miesiącu astronomicznym jesteśmy
    cumulative_days = 0
    current_month = None
    day_in_month = 0
    
    for month in ASTRONOMICAL_MONTHS:
        cumulative_days += month["days"]
        if day_of_year <= cumulative_days:
            current_month = month
            day_in_month = month["days"] - (cumulative_days - day_of_year)
            break
    
    # Jeśli to ostatni dzień roku (po 13 miesiącu)
    if not current_month:
        current_month = ASTRONOMICAL_MONTHS[-1]
        day_in_month = 0
        return {
            "day": 0,
            "month": "Intercalary Day",
            "month_symbol": "✨",
            "day_of_year": day_of_year,
            "year": now.year,
            "element": "Cosmic",
            "is_intercalary": True
        }
    
    return {
        "day": day_in_month,
        "month": current_month["name"],
        "month_symbol": current_month["symbol"],
        "day_of_year": day_of_year,
        "year": now.year,
        "element": current_month["element"],
        "is_intercalary": False,
        "dates_range": current_month["dates"]
    }

def check_astronomical_conditions(weather_data, city_name):
    """Sprawdź warunki do obserwacji astronomicznych z nowymi danymi"""
    if not weather_data or "current" not in weather_data:
        return None

    current = weather_data["current"]
    daily = weather_data.get("daily", {})

    # Pobierz aktualne dane
    cloud_cover = current.get("cloud_cover", 100)
    visibility = current.get("visibility", 0) / 1000  # konwertuj na km
    humidity = current.get("relative_humidity_2m", 100)
    wind_speed = current.get("wind_speed_10m", 0)
    temperature = current.get("temperature_2m", 0)
    is_day = current.get("is_day", 1)
    weather_code = current.get("weather_code", 0)
    pressure = current.get("pressure_msl", 1013)

    # Określ typ chmur
    cloud_type = determine_cloud_type(weather_code, cloud_cover, humidity, wind_speed)
    cloud_info = CLOUD_TYPES.get(cloud_type, CLOUD_TYPES["Cirrus"])

    # Oblicz fazę księżyca
    moon_phase = calculate_moon_phase()
    
    # Pobierz czasy wschodu/zachodu słońca i księżyca
    sunrise = daily.get("sunrise", [""])[0] if daily.get("sunrise") else None
    sunset = daily.get("sunset", [""])[0] if daily.get("sunset") else None
    moonrise = daily.get("moonrise", [""])[0] if daily.get("moonrise") else None
    moonset = daily.get("moonset", [""])[0] if daily.get("moonset") else None

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

    # Ocena ogólna
    if conditions_met == total_conditions:
        status = "DOSKONAŁE"
        emoji = "✨"
        description = "Idealne warunki do obserwacji!"
    elif conditions_met >= 4:
        status = "DOBRE"
        emoji = "⭐"
        description = "Dobre warunki do obserwacji"
    elif conditions_met == 3:
        status = "ŚREDNIE"
        emoji = "⛅"
        description = "Warunki umiarkowane"
    elif conditions_met >= 1:
        status = "SŁABE"
        emoji = "🌥️"
        description = "Warunki niekorzystne"
    else:
        status = "ZŁE"
        emoji = "🌧️"
        description = "Nieodpowiednie warunki do obserwacji"

    # Sprawdź najbliższe godziny (prognoza)
    hourly_forecast = []
    if "hourly" in weather_data:
        times = weather_data["hourly"].get("time", [])[:24]
        clouds = weather_data["hourly"].get("cloud_cover", [])[:24]
        temps = weather_data["hourly"].get("temperature_2m", [])[:24]
        winds = weather_data["hourly"].get("wind_speed_10m", [])[:24]
        humidities = weather_data["hourly"].get("relative_humidity_2m", [])[:24]

        for i, (time_str, cloud, temp, wind, hum) in enumerate(zip(times, clouds, temps, winds, humidities)):
            if (cloud <= GOOD_CONDITIONS["max_cloud_cover"] and
                hum <= GOOD_CONDITIONS["max_humidity"] and
                wind <= GOOD_CONDITIONS["max_wind_speed"] and
                GOOD_CONDITIONS["min_temperature"] <= temp <= GOOD_CONDITIONS["max_temperature"]):
                
                forecast_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                hourly_forecast.append({
                    "time": forecast_time.strftime("%H:%M"),
                    "cloud_cover": cloud,
                    "temperature": temp,
                    "hour": i
                })

    # Pobierz datę astronomiczną
    astronomical_date = get_astronomical_date()

    return {
        "city": city_name,
        "status": status,
        "emoji": emoji,
        "description": description,
        "score": round((conditions_met / total_conditions) * 100),
        "is_night": is_day == 0,
        "conditions": {
            "cloud_cover": cloud_cover,
            "visibility_km": round(visibility, 1),
            "humidity": humidity,
            "wind_speed": wind_speed,
            "temperature": temperature,
            "pressure": pressure,
            "details": conditions_check
        },
        "cloud_analysis": {
            "type": cloud_type,
            "emoji": cloud_info["emoji"],
            "description": cloud_info["description"],
            "altitude": cloud_info["altitude"]
        },
        "moon": {
            "phase": moon_phase,
            "rise": moonrise,
            "set": moonset
        },
        "sun": {
            "rise": sunrise,
            "set": sunset
        },
        "forecast": {
            "next_good_hours": hourly_forecast[:5],
            "total_good_hours": len(hourly_forecast)
        },
        "astronomical_date": astronomical_date,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def format_weather_message(weather_info):
    """Sformatuj wiadomość pogodową z nowymi danymi"""
    city = weather_info["city"]
    conditions = weather_info["conditions"]
    details = conditions["details"]
    cloud_info = weather_info["cloud_analysis"]
    moon_info = weather_info["moon"]["phase"]
    astro_date = weather_info["astronomical_date"]

    message = (
        f"{weather_info['emoji']} <b>{city.upper()} - RAPORT ASTROMETEOROLOGICZNY</b>\n"
        f"Status: <b>{weather_info['status']}</b> ({weather_info['score']}%)\n"
        f"{weather_info['description']}\n"
        f"⌚ {weather_info['timestamp']}\n\n"
    )

    # Sekcja daty astronomicznej
    if astro_date["is_intercalary"]:
        message += f"<b>📅 DATA ASTRONOMICZNA:</b>\n"
        message += f"• {astro_date['month_symbol']} Dzień Interkalarny {astro_date['year']}\n"
        message += f"• Dzień poza miesiącami - czas refleksji\n"
    else:
        message += f"<b>📅 DATA ASTRONOMICZNA (13-miesięczna):</b>\n"
        message += f"• {astro_date['day']} {astro_date['month_symbol']} {astro_date['month']} {astro_date['year']}\n"
        message += f"• Element: {astro_date['element']}\n"
        message += f"• Zakres: {astro_date.get('dates_range', 'N/A')}\n"
    message += "\n"

    # Sekcja warunków pogodowych
    message += f"<b>🌡️ WARUNKI POGODOWE:</b>\n"
    message += f"• Temperatura: {conditions['temperature']}°C {'✅' if details['temperature'] else '❌'}\n"
    message += f"• Wilgotność: {conditions['humidity']}% {'✅' if details['humidity'] else '❌'}\n"
    message += f"• Wiatr: {conditions['wind_speed']} m/s {'✅' if details['wind_speed'] else '❌'}\n"
    message += f"• Widoczność: {conditions['visibility_km']} km {'✅' if details['visibility'] else '❌'}\n"
    message += f"• Ciśnienie: {conditions['pressure']} hPa\n\n"

    # Sekcja analizy chmur
    message += f"<b>{cloud_info['emoji']} ANALIZA CHMUR:</b>\n"
    message += f"• Zachmurzenie: {conditions['cloud_cover']}% {'✅' if details['cloud_cover'] else '❌'}\n"
    message += f"• Dominujący typ: {cloud_info['type']}\n"
    message += f"• Wysokość: {cloud_info['altitude']}\n"
    message += f"• Opis: {cloud_info['description']}\n\n"

    # Sekcja Słońca
    if weather_info['sun']['rise'] and weather_info['sun']['set']:
        sunrise = datetime.fromisoformat(weather_info['sun']['rise'].replace('Z', '+00:00'))
        sunset = datetime.fromisoformat(weather_info['sun']['set'].replace('Z', '+00:00'))
        message += f"<b>🌅 CZAS SŁONECZNY:</b>\n"
        message += f"• Wschód: {sunrise.strftime('%H:%M')}\n"
        message += f"• Zachód: {sunset.strftime('%H:%M')}\n"
        message += f"• Długość dnia: {sunset - sunrise}\n"
    message += "\n"

    # Sekcja Księżyca
    message += f"<b>{moon_info['emoji']} FAZA KSIĘŻYCA:</b>\n"
    message += f"• {moon_info['name']}\n"
    message += f"• Oświetlenie: {moon_info['illumination']:.1f}%\n"
    if weather_info['moon']['rise'] and weather_info['moon']['set']:
        moonrise = datetime.fromisoformat(weather_info['moon']['rise'].replace('Z', '+00:00'))
        moonset = datetime.fromisoformat(weather_info['moon']['set'].replace('Z', '+00:00'))
        message += f"• Wschód: {moonrise.strftime('%H:%M')}\n"
        message += f"• Zachód: {moonset.strftime('%H:%M')}\n"
    message += "\n"

    # Sekcja prognozy
    if weather_info['forecast']['next_good_hours']:
        message += f"<b>📅 NAJLEPSZE GODZINY DO OBSERWACJI:</b>\n"
        for hour in weather_info['forecast']['next_good_hours']:
            message += f"• {hour['time']} (zachmurzenie: {hour['cloud_cover']}%, temp: {hour['temperature']}°C)\n"

        if weather_info['forecast']['total_good_hours'] > 5:
            message += f"• ... i {weather_info['forecast']['total_good_hours'] - 5} więcej\n"
    else:
        message += "<b>📅 PROGNOZA:</b>\nBrak dobrych warunków w ciągu 24h\n"

    # Rekomendacja
    if weather_info['status'] in ["DOSKONAŁE", "DOBRE"] and weather_info['is_night']:
        message += "\n✅ <b>REKOMENDACJA:</b> Warunki doskonałe do obserwacji astronomicznych!"
    elif weather_info['status'] in ["DOSKONAŁE", "DOBRE"] and not weather_info['is_night']:
        message += "\n⚠️ <b>REKOMENDACJA:</b> Dobre warunki, ale jest dzień. Poczekaj do zmierzchu."
    elif weather_info['status'] == "ŚREDNIE":
        message += "\n⚠️ <b>REKOMENDACJA:</b> Warunki umiarkowane. Możliwa obserwacja najjaśniejszych obiektów."
    else:
        message += "\n❌ <b>REKOMENDACJA:</b> Warunki nieodpowiednie do obserwacji."

    return message

# ====================== FUNKCJE POMOCNICZE ======================
def send_telegram_message(chat_id, text):
    """Wyślij wiadomość przez Telegram API"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return None

# ====================== FLASK APP ======================
app = Flask(__name__)

@app.before_request
def log_request():
    if request.path not in ['/health', '/ping']:
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")

@app.route('/')
def home():
    online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
    ping_stats = ping_service.get_stats()
    astro_date = get_astronomical_date()
    moon_phase = calculate_moon_phase()

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v5.0 - Astrometeorologia</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
                color: #333;
                min-height: 100vh;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                margin-top: 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 15px;
            }}
            .astro-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .astro-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .moon-phase {{
                font-size: 60px;
                text-align: center;
                margin: 10px 0;
            }}
            .calendar-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin: 20px 0;
            }}
            .month-card {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                border-left: 5px solid #667eea;
            }}
            .current-month {{
                background: #e3f2fd;
                border-left-color: #2196f3;
                font-weight: bold;
            }}
            .cloud-type {{
                background: #e8f5e9;
                padding: 10px;
                border-radius: 8px;
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 42px; margin-bottom: 10px;">🤖 SENTRY ONE v5.0</h1>
                <h2 style="color: #e0e0e0;">System Astrometeorologiczny z Kalendarzem 13-miesięcznym</h2>
                <div style="background: #4CAF50; display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold;">
                    🟢 SYSTEM AKTYWNY
                </div>
            </div>

            <div class="astro-grid">
                <div class="astro-card">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">🌌 DATA ASTRONOMICZNA</div>
                    <div style="font-size: 36px; text-align: center; margin: 15px 0;">
                        {astro_date['day'] if not astro_date['is_intercalary'] else '✨'} 
                        {astro_date['month_symbol']} 
                        {astro_date['month']} 
                        {astro_date['year']}
                    </div>
                    <div>Element: {astro_date['element']}</div>
                    <div>Dzień roku: {astro_date['day_of_year']}</div>
                    {'<div style="color: gold;">✨ DZIEŃ INTERKALARNY ✨</div>' if astro_date['is_intercalary'] else ''}
                </div>

                <div class="astro-card">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">🌙 FAZA KSIĘŻYCA</div>
                    <div class="moon-phase">{moon_phase['emoji']}</div>
                    <div style="text-align: center; font-size: 20px;">{moon_phase['name']}</div>
                    <div style="text-align: center;">Oświetlenie: {moon_phase['illumination']:.1f}%</div>
                    <div style="margin-top: 15px; background: rgba(255,255,255,0.2); padding: 10px; border-radius: 8px;">
                        Kalendarz księżycowy: {datetime.now().strftime("%d.%m.%Y %H:%M")}
                    </div>
                </div>
            </div>

            <h2>📅 KALENDARZ 13-MIESIĘCZNY</h2>
            <div class="calendar-grid">
    '''
    
    for i, month in enumerate(ASTRONOMICAL_MONTHS):
        is_current = (i == astro_date.get('month_number', 0) - 1) if not astro_date['is_intercalary'] else False
        html += f'''
                <div class="month-card {'current-month' if is_current else ''}">
                    <div style="font-size: 24px;">{month['symbol']}</div>
                    <div style="font-weight: bold;">{month['name']}</div>
                    <div>{month['days']} dni</div>
                    <div style="font-size: 12px; color: #666;">{month['dates']}</div>
                    {'<div style="color: #2196f3; font-weight: bold;">▶ AKTUALNY</div>' if is_current else ''}
                </div>
        '''
    
    html += f'''
            </div>

            <h2>☁️ TYPY CHMUR</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0;">
    '''
    
    for cloud_type, info in list(CLOUD_TYPES.items())[:6]:
        html += f'''
                <div class="cloud-type">
                    <div style="font-size: 20px;">{info['emoji']} {cloud_type}</div>
                    <div style="font-size: 12px;">{info['description']}</div>
                    <div style="font-size: 11px; color: #666;">Wysokość: {info['altitude']}</div>
                </div>
        '''
    
    html += f'''
            </div>

            <h2>🧭 AGENCI SYSTEMU</h2>
    '''
    
    for agent in AGENTS.values():
        status_color = "#4CAF50" if agent["status"] == "online" else "#f44336"
        html += f'''
            <div style="border: 2px solid {status_color}; border-radius: 12px; padding: 15px; margin: 15px 0; display: flex; align-items: center;">
                <div style="font-size: 40px; margin-right: 20px;">{agent['icon']}</div>
                <div style="flex: 1;">
                    <div style="font-weight: bold; font-size: 18px;">{agent['name']}</div>
                    <div>Typ: {agent['type']}</div>
                    <div style="color: {status_color}; font-weight: bold;">{agent['status'].upper()}</div>
                </div>
            </div>
        '''
    
    html += f'''
            <h2>📡 NOWE KOMENDY TELEGRAM</h2>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 12px; margin: 20px 0;">
                <div style="font-family: monospace; padding: 5px;">/astro - Pełny raport astrometeorologiczny</div>
                <div style="font-family: monospace; padding: 5px;">/astro moon - Szczegóły fazy księżyca</div>
                <div style="font-family: monospace; padding: 5px;">/astro clouds - Analiza typów chmur</div>
                <div style="font-family: monospace; padding: 5px;">/astro calendar - Kalendarz 13-miesięczny</div>
                <div style="font-family: monospace; padding: 5px;">/astro date - Aktualna data astronomiczna</div>
                <div style="font-family: monospace; padding: 5px;">/astro cities - Warunki dla wszystkich miast</div>
            </div>

            <div style="text-align: center; margin-top: 40px; color: #666; padding-top: 20px; border-top: 1px solid #eee;">
                <p>🤖 SENTRY ONE v5.0 | System Astrometeorologiczny | Kalendarz 13-znakowy</p>
                <p>🌌 Fazy Księżyca ☁️ Typy chmur 📅 Kalendarz astronomiczny</p>
                <p style="font-family: monospace;">Ostatnia aktualizacja: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# ====================== ENDPOINTY API ======================
@app.route('/health')
def health():
    moon = calculate_moon_phase()
    return jsonify({
        "status": "healthy",
        "version": "5.0",
        "service": "sentry-one-astrometeorology",
        "moon_phase": moon,
        "astronomical_date": get_astronomical_date(),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/moon')
def moon_phase():
    """Informacje o fazie księżyca"""
    moon = calculate_moon_phase()
    astro_date = get_astronomical_date()
    
    return jsonify({
        "moon_phase": moon,
        "astronomical_date": astro_date,
        "current_time": datetime.now().isoformat(),
        "next_full_moon": "Obliczanie...",
        "next_new_moon": "Obliczanie..."
    })

@app.route('/astrocalendar')
def astro_calendar():
    """Pełny kalendarz astronomiczny"""
    current_date = get_astronomical_date()
    all_months = []
    
    for month in ASTRONOMICAL_MONTHS:
        all_months.append({
            "name": month["name"],
            "symbol": month["symbol"],
            "days": month["days"],
            "element": month["element"],
            "dates": month["dates"]
        })
    
    return jsonify({
        "current_date": current_date,
        "all_months": all_months,
        "total_days": sum(m["days"] for m in ASTRONOMICAL_MONTHS),
        "system": "13-miesięczny kalendarz astronomiczny"
    })

@app.route('/clouds')
def cloud_info():
    """Informacje o typach chmur"""
    return jsonify({
        "cloud_types": CLOUD_TYPES,
        "current_time": datetime.now().isoformat()
    })

# ====================== TELEGRAM WEBHOOK ======================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Główny endpoint dla webhook Telegram"""
    try:
        data = request.get_json()
        logger.info(f"📥 Otrzymano webhook od Telegram")

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            if text.startswith("/start"):
                response_text = (
                    "🌌 <b>SENTRY ONE v5.0 - SYSTEM ASTROMETEOROLOGICZNY</b>\n\n"
                    "Witaj w zaawansowanym systemie obserwacji astronomicznych!\n\n"
                    "<b>NOWE FUNKCJE:</b>\n"
                    "• Fazy Księżyca z wschodami/zachodami\n"
                    "• Analiza typów chmur i wysokości\n"
                    "• Kalendarz 13-miesięczny (astronomiczny)\n"
                    "• Dokładne czasy wschodu/zachodu Słońca\n\n"
                    "<b>KOMENDY:</b>\n"
                    "/astro - Pełny raport dla miasta\n"
                    "/astro moon - Faza Księżyca\n"
                    "/astro clouds - Typy chmur\n"
                    "/astro calendar - Kalendarz 13-miesięczny\n"
                    "/astro date - Data astronomiczna\n"
                    "/astro cities - Wszystkie miasta\n\n"
                    "<i>Wybierz miasto po /astro (np. /astro warszawa)</i>"
                )
                send_telegram_message(chat_id, response_text)

            elif text.startswith("/astro"):
                args = text[6:].strip().lower()
                
                if args == "moon":
                    moon = calculate_moon_phase()
                    response_text = (
                        f"{moon['emoji']} <b>FAZA KSIĘŻYCA</b>\n\n"
                        f"• Faza: {moon['name']}\n"
                        f"• Oświetlenie: {moon['illumination']:.1f}%\n"
                        f"• Cykl księżycowy: {moon['phase']:.3f}\n\n"
                        f"<b>Najbliższe fazy:</b>\n"
                        f"• Nów: co 29.5 dnia\n"
                        f"• Pełnia: między 14-15 dniem cyklu\n\n"
                        f"<i>Czas lokalny: {datetime.now().strftime('%H:%M')}</i>"
                    )
                    send_telegram_message(chat_id, response_text)
                    
                elif args == "clouds":
                    response_text = (
                        "☁️ <b>TYPY CHMUR - PRZEWODNIK</b>\n\n"
                        "<b>Wysokie chmury (6-12 km):</b>\n"
                        "• Cirrus 🌤️ - cienkie, włókniste\n"
                        "• Cirrocumulus 🌤️ - drobne, kłębiaste\n"
                        "• Cirrostratus 🌥️ - mglista warstwa\n\n"
                        "<b>Średnie chmury (2-6 km):</b>\n"
                        "• Altocumulus 🌥️ - kłębiaste\n"
                        "• Altostratus ☁️ - szara warstwa\n\n"
                        "<b>Niskie chmury (0-2 km):</b>\n"
                        "• Stratus 🌫️ - mglista warstwa\n"
                        "• Stratocumulus ☁️ - płaty\n"
                        "• Cumulus ⛅ - puszyste\n\n"
                        "<b>Chmury opadowe:</b>\n"
                        "• Nimbostratus 🌧️ - opady ciągłe\n"
                        "• Cumulonimbus ⛈️ - burzowe\n"
                    )
                    send_telegram_message(chat_id, response_text)
                    
                elif args == "calendar":
                    astro_date = get_astronomical_date()
                    response_text = (
                        f"📅 <b>KALENDARZ 13-MIESIĘCZNY</b>\n\n"
                        f"<b>Aktualna data:</b>\n"
                        f"{astro_date['day']} {astro_date['month_symbol']} "
                        f"{astro_date['month']} {astro_date['year']}\n\n"
                        f"<b>Miesiące astronomiczne:</b>\n"
                    )
                    
                    for month in ASTRONOMICAL_MONTHS[:7]:
                        response_text += f"• {month['symbol']} {month['name']}: {month['days']} dni\n"
                    
                    response_text += "\n<i>Użyj /astro date dla szczegółów</i>"
                    send_telegram_message(chat_id, response_text)
                    
                elif args == "date":
                    astro_date = get_astronomical_date()
                    moon = calculate_moon_phase()
                    
                    if astro_date["is_intercalary"]:
                        date_display = f"✨ Dzień Interkalarny {astro_date['year']} ✨"
                    else:
                        date_display = f"{astro_date['day']} {astro_date['month_symbol']} {astro_date['month']} {astro_date['year']}"
                    
                    response_text = (
                        f"🌌 <b>DATA ASTRONOMICZNA</b>\n\n"
                        f"• Kalendarz gregoriański: {datetime.now().strftime('%d.%m.%Y')}\n"
                        f"• Data astronomiczna: {date_display}\n"
                        f"• Element: {astro_date['element']}\n"
                        f"• Dzień roku: {astro_date['day_of_year']}\n\n"
                        f"<b>Księżyc:</b> {moon['emoji']} {moon['name']}\n"
                        f"• Oświetlenie: {moon['illumination']:.1f}%\n\n"
                        f"<i>System 13 nierównych miesięcy oparty na astronomii</i>"
                    )
                    send_telegram_message(chat_id, response_text)
                    
                elif args == "cities":
                    # Sprawdź wszystkie miasta
                    for city_key, city_info in OBSERVATION_CITIES.items():
                        weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
                        if weather_data:
                            weather_info = check_astronomical_conditions(weather_data, city_info["name"])
                            if weather_info:
                                short_report = (
                                    f"{weather_info['emoji']} <b>{city_info['name']}</b>\n"
                                    f"Status: {weather_info['status']} ({weather_info['score']}%)\n"
                                    f"Temp: {weather_info['conditions']['temperature']}°C\n"
                                    f"Chmury: {weather_info['cloud_analysis']['type']} {weather_info['cloud_analysis']['emoji']}\n"
                                    f"Księżyc: {weather_info['moon']['phase']['emoji']} "
                                    f"{weather_info['moon']['phase']['name']}\n"
                                )
                                send_telegram_message(chat_id, short_report)
                                time.sleep(0.5)
                    
                    send_telegram_message(chat_id, "ℹ️ Użyj /astro [miasto] dla pełnego raportu")
                    
                elif args in ["warszawa", "koszalin"]:
                    # Pełny raport dla miasta
                    city_info = OBSERVATION_CITIES[args]
                    weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
                    
                    if weather_data:
                        weather_info = check_astronomical_conditions(weather_data, city_info["name"])
                        if weather_info:
                            message_text = format_weather_message(weather_info)
                            send_telegram_message(chat_id, message_text)
                        else:
                            send_telegram_message(chat_id, "❌ Nie udało się przeanalizować warunków")
                    else:
                        send_telegram_message(chat_id, "❌ Błąd pobierania danych pogodowych")
                        
                else:
                    # Domyślnie: krótki raport dla Warszawy
                    city_info = OBSERVATION_CITIES["warszawa"]
                    weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
                    
                    if weather_data:
                        weather_info = check_astronomical_conditions(weather_data, city_info["name"])
                        short_report = (
                            f"{weather_info['emoji']} <b>SZYBKI RAPORT - {city_info['name'].upper()}</b>\n\n"
                            f"Status: {weather_info['status']} ({weather_info['score']}%)\n"
                            f"Temp: {weather_info['conditions']['temperature']}°C\n"
                            f"Chmury: {weather_info['cloud_analysis']['type']} "
                            f"({weather_info['conditions']['cloud_cover']}%)\n"
                            f"Widoczność: {weather_info['conditions']['visibility_km']} km\n"
                            f"Księżyc: {weather_info['moon']['phase']['emoji']} "
                            f"{weather_info['moon']['phase']['name']}\n\n"
                            f"<i>Użyj /astro [miasto] dla pełnego raportu</i>"
                        )
                        send_telegram_message(chat_id, short_report)
                    else:
                        send_telegram_message(chat_id, "❌ Błąd pobierania danych")

            else:
                response_text = (
                    "🌌 <b>SENTRY ONE v5.0</b>\n\n"
                    "System astrometeorologiczny z kalendarzem 13-znakowym.\n\n"
                    "<b>Główne komendy:</b>\n"
                    "/start - Informacje\n"
                    "/astro - Raport pogodowy\n"
                    "/astro moon - Faza Księżyca\n"
                    "/astro calendar - Kalendarz\n\n"
                    "<i>Dostępne miasta: warszawa, koszalin</i>"
                )
                send_telegram_message(chat_id, response_text)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Błąd przetwarzania webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print(f"🚀 Uruchamianie SENTRY ONE v5.0...")
    print(f"🌌 SYSTEM ASTROMETEOROLOGICZNY z kalendarzem 13-miesięcznym")
    print(f"📅 Data astronomiczna: {get_astronomical_date()['day']} {get_astronomical_date()['month']}")
    print(f"🌙 Faza Księżyca: {calculate_moon_phase()['name']}")
    
    # Uruchom system pingowania
    ping_service.start()
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )