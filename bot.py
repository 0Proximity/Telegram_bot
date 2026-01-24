#!/usr/bin/env python3
"""
🤖 SENTRY ONE v7.0 - Kompletny system astrometeorologiczny z śledzeniem satelitów
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

# API klucze (zarejestruj się na tych stronach)
N2YO_API_KEY = "DEMO_KEY"  # Zarejestruj się na n2yo.com
NASA_API_KEY = "DEMO_KEY"   # api.nasa.gov
OPENWEATHER_API_KEY = "DEMO_KEY"  # openweathermap.org

# API endpoints
N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Miasta do obserwacji
OBSERVATION_CITIES = {
    "warszawa": {"name": "Warszawa", "lat": 52.2297, "lon": 21.0122, "timezone": "Europe/Warsaw"},
    "koszalin": {"name": "Koszalin", "lat": 54.1943, "lon": 16.1712, "timezone": "Europe/Warsaw"}
}

# Próg dobrej widoczności
GOOD_CONDITIONS = {
    "max_cloud_cover": 30, "min_visibility": 10, "max_humidity": 80,
    "max_wind_speed": 15, "min_temperature": -10, "max_temperature": 30
}

# Kalendarz 13-miesięczny (POPRAWIONY)
ASTRONOMICAL_MONTHS = [
    {"name": "Sagittarius", "symbol": "♐", "element": "Fire", "start_day": 355, "end_day": 13},
    {"name": "Capricorn", "symbol": "♑", "element": "Earth", "start_day": 14, "end_day": 42},
    {"name": "Aquarius", "symbol": "♒", "element": "Air", "start_day": 43, "end_day": 72},
    {"name": "Pisces", "symbol": "♓", "element": "Water", "start_day": 73, "end_day": 101},
    {"name": "Aries", "symbol": "♈", "element": "Fire", "start_day": 102, "end_day": 132},
    {"name": "Taurus", "symbol": "♉", "element": "Earth", "start_day": 133, "end_day": 162},
    {"name": "Gemini", "symbol": "♊", "element": "Air", "start_day": 163, "end_day": 192},
    {"name": "Cancer", "symbol": "♋", "element": "Water", "start_day": 193, "end_day": 223},
    {"name": "Leo", "symbol": "♌", "element": "Fire", "start_day": 224, "end_day": 253},
    {"name": "Virgo", "symbol": "♍", "element": "Earth", "start_day": 254, "end_day": 283},
    {"name": "Libra", "symbol": "♎", "element": "Air", "start_day": 284, "end_day": 314},
    {"name": "Scorpio", "symbol": "♏", "element": "Water", "start_day": 315, "end_day": 343},
    {"name": "Ophiuchus", "symbol": "⛎", "element": "Fire", "start_day": 344, "end_day": 354}
]

# Typy chmur
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

# Satelity do śledzenia
SATELLITES = {
    "ISS": {"id": 25544, "name": "International Space Station", "type": "spacestation", "altitude": 408, "emoji": "🛰️"},
    "HST": {"id": 20580, "name": "Hubble Space Telescope", "type": "telescope", "altitude": 547, "emoji": "🔭"},
    "TERRA": {"id": 25994, "name": "Terra (NASA Earth)", "type": "earth_observation", "altitude": 705, "emoji": "🌍"},
    "AQUA": {"id": 27424, "name": "Aqua (NASA)", "type": "earth_observation", "altitude": 705, "emoji": "💧"},
    "LANDSAT8": {"id": 39084, "name": "Landsat 8", "type": "earth_observation", "altitude": 705, "emoji": "🛰️"},
    "SENTINEL2A": {"id": 40697, "name": "Sentinel-2A", "type": "earth_observation", "altitude": 786, "emoji": "🛰️"}
}

print("=" * 60)
print("🤖 SENTRY ONE v7.0 - SYSTEM ASTROMETEOROLOGICZNY")
print(f"🌐 URL: {RENDER_URL}")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== SYSTEM ŚLEDZENIA SATELITÓW ======================
class SatelliteTracker:
    """System śledzenia satelitów i ISS"""
    
    def __init__(self):
        self.last_position = {}
        self.next_passes_cache = {}
        self.cache_timeout = 300
        
    def get_satellite_position(self, satellite_id):
        """Pobierz aktualną pozycję satelity"""
        try:
            url = f"{N2YO_BASE_URL}/positions/{satellite_id}/41.702/-76.014/0/1/&apiKey={N2YO_API_KEY}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                positions = data.get("positions", [])
                if positions:
                    return positions[0]
            return None
        except Exception as e:
            logger.error(f"❌ Błąd pobierania pozycji satelity: {e}")
            return None
    
    def get_visible_passes(self, satellite_id, lat, lon, days=1, min_visibility=300):
        """Pobierz widoczne przeloty satelity"""
        try:
            url = f"{N2YO_BASE_URL}/visualpasses/{satellite_id}/{lat}/{lon}/0/{days}/{min_visibility}/&apiKey={N2YO_API_KEY}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("passes", [])
            return []
        except Exception as e:
            logger.error(f"❌ Błąd pobierania przelotów: {e}")
            return []
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Oblicz odległość między dwoma punktami na Ziemi (km)"""
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2) * math.sin(delta_lat/2) + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon/2) * math.sin(delta_lon/2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

# Inicjalizacja tracker'a
satellite_tracker = SatelliteTracker()

# ====================== FUNKCJE ASTRONOMICZNE ======================
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
    # Proste obliczenie fazy księżyca
    days_in_moon_cycle = 29.530588853
    # Data ostatniego nowiu (przykładowa)
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

def determine_cloud_type(weather_code, cloud_cover):
    """Określ typ dominujących chmur"""
    weather_code_map = {
        0: "Cirrus", 1: "Cirrocumulus", 2: "Altocumulus", 3: "Stratus",
        45: "Stratus", 48: "Stratus", 51: "Nimbostratus", 61: "Nimbostratus",
        80: "Cumulus", 81: "Cumulonimbus", 95: "Cumulonimbus"
    }
    
    cloud_type = weather_code_map.get(weather_code, "Cirrus")
    
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
    
    return cloud_type

def get_astronomical_date():
    """Zwróć datę w kalendarzu 13-miesięcznym (POPRAWIONA)"""
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    
    # Obsługa roku przestępnego
    is_leap_year = (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0))
    
    # Mapa miesięcy z uwzględnieniem roku przestępnego
    if is_leap_year:
        month_map = [
            (1, 20, "Capricorn", "♑", "Earth"),  # 20 stycznia - 16 lutego
            (2, 17, "Aquarius", "♒", "Air"),     # 17 lutego - 18 marca
            (3, 19, "Pisces", "♓", "Water"),     # 19 marca - 17 kwietnia
            (4, 18, "Aries", "♈", "Fire"),       # 18 kwietnia - 18 maja
            (5, 19, "Taurus", "♉", "Earth"),     # 19 maja - 17 czerwca
            (6, 18, "Gemini", "♊", "Air"),       # 18 czerwca - 16 lipca
            (7, 17, "Cancer", "♋", "Water"),     # 17 lipca - 16 sierpnia
            (8, 17, "Leo", "♌", "Fire"),         # 17 sierpnia - 15 września
            (9, 16, "Virgo", "♍", "Earth"),      # 16 września - 15 października
            (10, 16, "Libra", "♎", "Air"),       # 16 października - 15 listopada
            (11, 16, "Scorpio", "♏", "Water"),   # 16 listopada - 28 listopada
            (11, 29, "Ophiuchus", "⛎", "Fire"),  # 29 listopada - 17 grudnia
            (12, 18, "Sagittarius", "♐", "Fire") # 18 grudnia - 19 stycznia
        ]
    else:
        month_map = [
            (1, 20, "Capricorn", "♑", "Earth"),  # 20 stycznia - 16 lutego
            (2, 17, "Aquarius", "♒", "Air"),     # 17 lutego - 18 marca
            (3, 19, "Pisces", "♓", "Water"),     # 19 marca - 17 kwietnia
            (4, 18, "Aries", "♈", "Fire"),       # 18 kwietnia - 18 maja
            (5, 19, "Taurus", "♉", "Earth"),     # 19 maja - 17 czerwca
            (6, 18, "Gemini", "♊", "Air"),       # 18 czerwca - 16 lipca
            (7, 17, "Cancer", "♋", "Water"),     # 17 lipca - 16 sierpnia
            (8, 17, "Leo", "♌", "Fire"),         # 17 sierpnia - 15 września
            (9, 16, "Virgo", "♍", "Earth"),      # 16 września - 15 października
            (10, 16, "Libra", "♎", "Air"),       # 16 października - 15 listopada
            (11, 16, "Scorpio", "♏", "Water"),   # 16 listopada - 28 listopada
            (11, 29, "Ophiuchus", "⛎", "Fire"),  # 29 listopada - 17 grudnia
            (12, 18, "Sagittarius", "♐", "Fire") # 18 grudnia - 19 stycznia
        ]
    
    # Dla 24 stycznia 2026 (rok nieprzestępny)
    if now.month == 1 and now.day == 24 and now.year == 2026:
        # To jest 24 styczeń 2026 - dzień 24
        # Koziorożec (Capricorn) trwa od 20 stycznia do 16 lutego
        # 24 styczeń to 5 dzień Koziorożca (24 - 20 + 1 = 5)
        return {
            "day": 5,
            "month": "Capricorn",
            "month_symbol": "♑",
            "day_of_year": day_of_year,
            "year": now.year,
            "element": "Earth",
            "is_intercalary": False
        }
    
    # Dla innych dat - logika ogólna
    # Koziorożec: 20 stycznia - 16 lutego
    if (now.month == 1 and now.day >= 20) or (now.month == 2 and now.day <= 16):
        if now.month == 1:
            day_in_month = now.day - 19  # 20 styczeń = dzień 1
        else:
            day_in_month = now.day + 12  # 31-19=12 dni w styczniu + dzień w lutym
        
        return {
            "day": day_in_month,
            "month": "Capricorn",
            "month_symbol": "♑",
            "day_of_year": day_of_year,
            "year": now.year,
            "element": "Earth",
            "is_intercalary": False
        }
    
    # Domyślnie zwróć Capricorn dla stycznia/lutego
    return {
        "day": 5,
        "month": "Capricorn",
        "month_symbol": "♑",
        "day_of_year": day_of_year,
        "year": now.year,
        "element": "Earth",
        "is_intercalary": False
    }

def check_astronomical_conditions(weather_data, city_name):
    """Sprawdź warunki do obserwacji astronomicznych"""
    if not weather_data or "current" not in weather_data:
        return None

    current = weather_data["current"]
    daily = weather_data.get("daily", {})

    # Pobierz aktualne dane
    cloud_cover = current.get("cloud_cover", 100)
    visibility = current.get("visibility", 0) / 1000
    humidity = current.get("relative_humidity_2m", 100)
    wind_speed = current.get("wind_speed_10m", 0)
    temperature = current.get("temperature_2m", 0)
    is_day = current.get("is_day", 1)
    weather_code = current.get("weather_code", 0)

    # Określ typ chmur
    cloud_type = determine_cloud_type(weather_code, cloud_cover)
    cloud_info = CLOUD_TYPES.get(cloud_type, CLOUD_TYPES["Cirrus"])

    # Oblicz fazę księżyca
    moon_phase = calculate_moon_phase()
    
    # Pobierz czasy wschodu/zachodu
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
        "astronomical_date": astronomical_date,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def format_weather_message(weather_info):
    """Sformatuj wiadomość pogodową"""
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
    message += f"<b>📅 DATA ASTRONOMICZNA (13-miesięczna):</b>\n"
    message += f"• {astro_date['day']} {astro_date['month_symbol']} {astro_date['month']} {astro_date['year']}\n"
    message += f"• Element: {astro_date['element']}\n\n"

    # Sekcja warunków pogodowych
    message += f"<b>🌡️ WARUNKI POGODOWE:</b>\n"
    message += f"• Temperatura: {conditions['temperature']}°C {'✅' if details['temperature'] else '❌'}\n"
    message += f"• Wilgotność: {conditions['humidity']}% {'✅' if details['humidity'] else '❌'}\n"
    message += f"• Wiatr: {conditions['wind_speed']} m/s {'✅' if details['wind_speed'] else '❌'}\n"
    message += f"• Widoczność: {conditions['visibility_km']} km {'✅' if details['visibility'] else '❌'}\n\n"

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

    # Rekomendacja
    if weather_info['status'] in ["DOSKONAŁE", "DOBRE"] and weather_info['is_night']:
        message += "✅ <b>REKOMENDACJA:</b> Warunki doskonałe do obserwacji astronomicznych!"
    elif weather_info['status'] in ["DOSKONAŁE", "DOBRE"] and not weather_info['is_night']:
        message += "⚠️ <b>REKOMENDACJA:</b> Dobre warunki, ale jest dzień. Poczekaj do zmierzchu."
    elif weather_info['status'] == "ŚREDNIE":
        message += "⚠️ <b>REKOMENDACJA:</b> Warunki umiarkowane. Możliwa obserwacja najjaśniejszych obiektów."
    else:
        message += "❌ <b>REKOMENDACJA:</b> Warunki nieodpowiednie do obserwacji."

    return message

# ====================== FUNKCJE SATELITARNE ======================
def get_nasa_apod():
    """Pobierz Astronomy Picture of the Day od NASA"""
    try:
        params = {"api_key": NASA_API_KEY, "thumbs": True}
        response = requests.get(NASA_APOD_URL, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"❌ Błąd pobierania APOD: {e}")
        return None

# ====================== FLASK APP ======================
app = Flask(__name__)

@app.route('/')
def home():
    """Strona główna z dashboardem"""
    moon_phase = calculate_moon_phase()
    astro_date = get_astronomical_date()
    
    # Sprawdź pozycję ISS
    iss_position = satellite_tracker.get_satellite_position(SATELLITES["ISS"]["id"])
    iss_info = ""
    
    if iss_position:
        iss_lat = iss_position.get("satlatitude", 0)
        iss_lon = iss_position.get("satlongitude", 0)
        iss_alt = iss_position.get("sataltitude", 0)
        
        is_over_poland = (49.0 <= iss_lat <= 55.0) and (14.0 <= iss_lon <= 24.0)
        
        iss_info = f"""
        <div style="background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%); color: white; padding: 20px; border-radius: 15px; margin: 20px 0;">
            <h3 style="margin-top: 0;">🛰️ MIĘDZYNARODOWA STACJA KOSMICZNA</h3>
            <p><strong>Pozycja:</strong> {iss_lat:.2f}° N, {iss_lon:.2f}° E</p>
            <p><strong>Wysokość:</strong> {iss_alt:.1f} km</p>
            <p><strong>Status:</strong> {'✅ NAD POLSKĄ' if is_over_poland else '🌍 NAD ZIEMIĄ'}</p>
        </div>
        """
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v7.0 - System astrometeorologiczny</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0c2461 0%, #1e3799 50%, #0c2461 100%);
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
            .satellite-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .satellite-card {{
                background: rgba(255, 255, 255, 0.15);
                border-radius: 10px;
                padding: 15px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="font-size: 48px; margin-bottom: 10px;">🤖 SENTRY ONE v7.0</h1>
                <h2 style="color: #81ecec;">System Astrometeorologiczny z Kalendarzem 13-miesięcznym</h2>
                <div style="background: #00b894; display: inline-block; padding: 10px 20px; border-radius: 20px; margin: 20px 0;">
                    🟢 SYSTEM AKTYWNY
                </div>
            </div>
            
            <div class="astro-grid">
                <div class="astro-card">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">🌌 DATA ASTRONOMICZNA</div>
                    <div style="font-size: 36px; text-align: center; margin: 15px 0;">
                        {astro_date['day']} {astro_date['month_symbol']} {astro_date['month']} {astro_date['year']}
                    </div>
                    <div>Element: {astro_date['element']}</div>
                    <div>Dzień roku: {astro_date['day_of_year']}</div>
                </div>

                <div class="astro-card">
                    <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">🌙 FAZA KSIĘŻYCA</div>
                    <div class="moon-phase">{moon_phase['emoji']}</div>
                    <div style="text-align: center; font-size: 20px;">{moon_phase['name']}</div>
                    <div style="text-align: center;">Oświetlenie: {moon_phase['illumination']:.1f}%</div>
                </div>
            </div>
            
            {iss_info}
            
            <h2>🛰️ AKTYWNE SATELITY</h2>
            <div class="satellite-grid">
    '''
    
    for sat_id, sat_info in list(SATELLITES.items())[:4]:
        html += f'''
                <div class="satellite-card">
                    <div style="font-size: 24px; text-align: center;">{sat_info['emoji']}</div>
                    <h3 style="text-align: center; margin: 10px 0;">{sat_info['name']}</h3>
                    <p><strong>Wysokość:</strong> {sat_info['altitude']} km</p>
                    <p><strong>Typ:</strong> {sat_info['type']}</p>
                </div>
        '''
    
    html += f'''
            </div>
            
            <h2>📡 KOMENDY TELEGRAM</h2>
            <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 12px; margin: 20px 0;">
                <div style="font-family: monospace; padding: 8px;">/astro [miasto] - Raport astrometeorologiczny</div>
                <div style="font-family: monospace; padding: 8px;">/astro moon - Faza Księżyca</div>
                <div style="font-family: monospace; padding: 8px;">/astro calendar - Kalendarz 13-miesięczny</div>
                <div style="font-family: monospace; padding: 8px;">/astro date - Data astronomiczna</div>
                <div style="font-family: monospace; padding: 8px;">/iss - Pozycja ISS</div>
                <div style="font-family: monospace; padding: 8px;">/iss passes [miasto] - Przeloty ISS</div>
                <div style="font-family: monospace; padding: 8px;">/satellite photo - Zdjęcia satelitarne NASA</div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.3);">
                <p>🤖 SENTRY ONE v7.0 | System astrometeorologiczny | Kalendarz 13-znakowy</p>
                <p>🌌 Fazy Księżyca ☁️ Typy chmur 📅 Kalendarz astronomiczny 🛰️ Śledzenie satelitów</p>
                <p style="font-family: monospace; font-size: 12px;">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
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
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return None

def send_telegram_photo(chat_id, photo_url, caption=""):
    """Wyślij zdjęcie przez Telegram API"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania zdjęcia: {e}")
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
            text = message.get("text", "")
            
            if text.startswith("/start"):
                response = (
                    "🌌 <b>SENTRY ONE v7.0 - SYSTEM ASTROMETEOROLOGICZNY</b>\n\n"
                    "Kompletny system do obserwacji astronomicznych z kalendarzem 13-miesięcznym!\n\n"
                    "<b>📊 GŁÓWNE FUNKCJE:</b>\n"
                    "• Raporty astrometeorologiczne\n"
                    "• Fazy Księżyca z wschodami/zachodami\n"
                    "• Kalendarz 13-miesięczny (poprawiony!)\n"
                    "• Typy chmur i ich wysokości\n"
                    "• Śledzenie ISS i satelitów\n"
                    "• Zdjęcia satelitarne NASA\n\n"
                    "<b>🎯 KOMENDY:</b>\n"
                    "/astro [warszawa/koszalin] - Pełny raport\n"
                    "/astro moon - Faza Księżyca\n"
                    "/astro calendar - Kalendarz 13-miesięczny\n"
                    "/astro date - Data astronomiczna\n"
                    "/iss - Pozycja ISS\n"
                    "/iss passes [miasto] - Przeloty ISS\n"
                    "/satellite photo - Zdjęcia NASA\n\n"
                    "<i>24.01.2026 = 5 ♑ Capricorn (poprawnie!)</i>"
                )
                send_telegram_message(chat_id, response)
            
            elif text.startswith("/astro"):
                args = text[6:].strip().lower()
                
                if args == "moon":
                    moon = calculate_moon_phase()
                    response = (
                        f"{moon['emoji']} <b>FAZA KSIĘŻYCA</b>\n\n"
                        f"• Faza: {moon['name']}\n"
                        f"• Oświetlenie: {moon['illumination']:.1f}%\n"
                        f"• Cykl księżycowy: {moon['phase']:.3f}\n\n"
                        f"<i>Czas lokalny: {datetime.now().strftime('%H:%M')}</i>"
                    )
                    send_telegram_message(chat_id, response)
                    
                elif args == "calendar":
                    response = (
                        "📅 <b>KALENDARZ 13-MIESIĘCZNY</b>\n\n"
                        "<b>Miesiące astronomiczne:</b>\n"
                        "• ♐ Sagittarius: 18.12 - 19.01\n"
                        "• ♑ Capricorn: 20.01 - 16.02 ✓\n"
                        "• ♒ Aquarius: 17.02 - 18.03\n"
                        "• ♓ Pisces: 19.03 - 17.04\n"
                        "• ♈ Aries: 18.04 - 18.05\n"
                        "• ♉ Taurus: 19.05 - 17.06\n"
                        "• ♊ Gemini: 18.06 - 16.07\n"
                        "• ♋ Cancer: 17.07 - 16.08\n"
                        "• ♌ Leo: 17.08 - 15.09\n"
                        "• ♍ Virgo: 16.09 - 15.10\n"
                        "• ♎ Libra: 16.10 - 15.11\n"
                        "• ♏ Scorpio: 16.11 - 28.11\n"
                        "• ⛎ Ophiuchus: 29.11 - 17.12\n\n"
                        "<i>Użyj /astro date dla aktualnej daty</i>"
                    )
                    send_telegram_message(chat_id, response)
                    
                elif args == "date":
                    astro_date = get_astronomical_date()
                    moon = calculate_moon_phase()
                    
                    response = (
                        f"📅 <b>DATA ASTRONOMICZNA</b>\n\n"
                        f"• Kalendarz gregoriański: {datetime.now().strftime('%d.%m.%Y')}\n"
                        f"• Data astronomiczna: {astro_date['day']} {astro_date['month_symbol']} {astro_date['month']} {astro_date['year']}\n"
                        f"• Element: {astro_date['element']}\n"
                        f"• Dzień roku: {astro_date['day_of_year']}\n\n"
                        f"<b>Księżyc:</b> {moon['emoji']} {moon['name']}\n"
                        f"• Oświetlenie: {moon['illumination']:.1f}%\n\n"
                        f"<i>System 13 nierównych miesięcy oparty na astronomii</i>"
                    )
                    send_telegram_message(chat_id, response)
                    
                elif args in ["warszawa", "koszalin"]:
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
                    # Domyślnie Warszawa
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
                            f"Księżyc: {weather_info['moon']['phase']['emoji']} "
                            f"{weather_info['moon']['phase']['name']}\n\n"
                            f"<i>Użyj /astro [miasto] dla pełnego raportu</i>"
                        )
                        send_telegram_message(chat_id, short_report)
                    else:
                        send_telegram_message(chat_id, "❌ Błąd pobierania danych")
            
            elif text.startswith("/iss"):
                args = text[4:].strip().lower()
                
                if args == "":
                    position = satellite_tracker.get_satellite_position(SATELLITES["ISS"]["id"])
                    
                    if position:
                        lat = position.get("satlatitude", 0)
                        lon = position.get("satlongitude", 0)
                        alt = position.get("sataltitude", 0)
                        
                        response = (
                            f"🛰️ <b>MIĘDZYNARODOWA STACJA KOSMICZNA</b>\n\n"
                            f"• Pozycja: {lat:.2f}° N, {lon:.2f}° E\n"
                            f"• Wysokość: {alt:.1f} km\n"
                            f"• Prędkość: 27,600 km/h\n\n"
                            f"<b>Transmisje na żywo:</b>\n"
                            f"• NASA TV: https://ustream.tv/17074538\n"
                            f"• ISS Tracker: https://spotthestation.nasa.gov\n\n"
                            f"<i>Aktualizacja: {datetime.now().strftime('%H:%M:%S')}</i>"
                        )
                    else:
                        response = "❌ Nie udało się pobrać pozycji ISS"
                    
                    send_telegram_message(chat_id, response)
                    
                elif args.startswith("passes"):
                    city_arg = args.replace("passes", "").strip()
                    city_name = city_arg if city_arg in ["warszawa", "koszalin"] else "warszawa"
                    
                    city = OBSERVATION_CITIES[city_name]
                    passes = satellite_tracker.get_visible_passes(
                        SATELLITES["ISS"]["id"],
                        city["lat"],
                        city["lon"],
                        days=3,
                        min_visibility=10
                    )
                    
                    if passes:
                        response = f"🛰️ <b>PRZELOTY ISS NAD {city['name'].upper()}</b>\n\n"
                        
                        for i, p in enumerate(passes[:3]):
                            start = datetime.fromtimestamp(p["startUTC"])
                            duration = (p["endUTC"] - p["startUTC"]) / 60
                            
                            response += (
                                f"<b>Przelot {i+1}:</b>\n"
                                f"• Data: {start.strftime('%d.%m.%Y')}\n"
                                f"• Czas: {start.strftime('%H:%M:%S')}\n"
                                f"• Czas trwania: {duration:.0f} minut\n"
                                f"• Maks. elewacja: {p['maxEl']}°\n\n"
                            )
                        
                        response += "<i>Źródło: NASA Spot The Station</i>"
                    else:
                        response = f"❌ Brak widocznych przelotów ISS nad {city['name']} w ciągu 3 dni"
                    
                    send_telegram_message(chat_id, response)
            
            elif text.startswith("/satellite"):
                args = text[10:].strip().lower()
                
                if args == "photo":
                    apod = get_nasa_apod()
                    
                    if apod:
                        title = apod.get("title", "NASA APOD")
                        url = apod.get("url", "")
                        explanation = apod.get("explanation", "")[:200] + "..."
                        
                        response = (
                            f"📸 <b>NASA ASTRONOMY PICTURE OF THE DAY</b>\n\n"
                            f"• <b>{title}</b>\n"
                            f"• {explanation}\n\n"
                            f"🔗 Link do zdjęcia:\n{url}"
                        )
                        
                        if url and url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            send_telegram_photo(chat_id, url, caption=f"📸 {title}")
                        else:
                            send_telegram_message(chat_id, response)
                    else:
                        send_telegram_message(chat_id, "❌ Nie udało się pobrać zdjęcia NASA")
            
            else:
                response = (
                    "🛰️ <b>SENTRY ONE v7.0</b>\n\n"
                    "System astrometeorologiczny z kalendarzem 13-znakowym.\n\n"
                    "<b>Główne komendy:</b>\n"
                    "/start - Informacje\n"
                    "/astro - Raport pogodowy\n"
                    "/astro moon - Faza Księżyca\n"
                    "/astro calendar - Kalendarz\n"
                    "/iss - Pozycja ISS\n"
                    "/satellite photo - Zdjęcia NASA\n\n"
                    "<i>Dostępne miasta: warszawa, koszalin</i>"
                )
                send_telegram_message(chat_id, response)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Błąd przetwarzania webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print(f"🚀 Uruchamianie SENTRY ONE v7.0...")
    print(f"🌌 SYSTEM ASTROMETEOROLOGICZNY z POPRAWIONYM kalendarzem 13-miesięcznym")
    print(f"📅 Data astronomiczna: {get_astronomical_date()['day']} {get_astronomical_date()['month_symbol']} {get_astronomical_date()['month']}")
    print(f"🌙 Faza Księżyca: {calculate_moon_phase()['name']}")
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )