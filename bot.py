#!/usr/bin/env python3
"""
🛰️ EARTH OBSERVATION PLATFORM v6.0 - PRODUCTION
✅ Wszystkie API w zmiennych środowiskowych
✅ Działa na Renderze
✅ Bezpieczne klucze API
"""

import os
import json
import time
import math
import sqlite3
import threading
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from flask import Flask, request, jsonify
import logging

# ====================== KONFIGURACJA Z ENVIRONMENT ======================
print("=" * 80)
print("🚀 EARTH OBSERVATION PLATFORM v6.0 - PRODUCTION")
print("🔐 Wszystkie API ukryte w zmiennych środowiskowych")
print("=" * 80)

# Pobierz WSZYSTKIE klucze z environment variables
TELEGRAM_BOT_API = os.getenv("TELEGRAM_BOT_API","")
USGS_API_KEY = os.getenv("USGS_API_KEY", "")  # USGS może nie wymagać klucza
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")  # NASA ma darmowy demo
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
N2YO_API_KEY = os.getenv("N2YO_API_KEY", "DEMO_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
RENDER_URL = os.getenv("RENDER_URL", "https://your-app.onrender.com")
PORT = int(os.getenv("PORT", 10000))

# Sprawdź wymagane klucze
if not TELEGRAM_BOT_API:
    print("❌ BRAK TELEGRAM_BOT_API! Bot nie będzie działać.")
    print("ℹ️ Ustaw TELEGRAM_BOT_API w environment variables na Renderze.")
    # Możemy kontynuować, ale funkcje Telegram nie będą działać

# Konfiguracja systemu
WEBHOOK_URL = f"{RENDER_URL}/webhook"
DB_FILE = "/tmp/earth_observation.db"
CHECK_INTERVAL = 300

# ====================== LOGGING ======================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ====================== DATA STRUCTURES ======================
@dataclass
class Satellite:
    norad_id: int
    name: str
    type: str
    camera: str
    swath_km: float
    resolution_m: float
    min_elevation: float

@dataclass
class ObservationPoint:
    name: str
    lat: float
    lon: float
    elevation: float = 0

# ====================== MODUŁY API ======================

class USGSClient:
    """Klient USGS API - trzęsienia ziemi"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://earthquake.usgs.gov/fdsnws/event/1"
    
    def get_earthquakes(self, min_mag=4.0, hours=24, limit=10) -> List[Dict]:
        """Pobierz trzęsienia ziemi"""
        try:
            endtime = datetime.utcnow()
            starttime = endtime - timedelta(hours=hours)
            
            params = {
                "format": "geojson",
                "starttime": starttime.strftime("%Y-%m-%dT%H:%M:%S"),
                "endtime": endtime.strftime("%Y-%m-%dT%H:%M:%S"),
                "minmagnitude": min_mag,
                "orderby": "time",
                "limit": limit
            }
            
            response = requests.get(f"{self.base_url}/query", params=params, timeout=10)
            data = response.json()
            
            earthquakes = []
            for feature in data.get('features', []):
                props = feature['properties']
                coords = feature['geometry']['coordinates']
                
                earthquake = {
                    'id': feature['id'],
                    'place': props['place'],
                    'magnitude': props['mag'],
                    'time': datetime.fromtimestamp(props['time'] / 1000),
                    'lat': coords[1],
                    'lon': coords[0],
                    'depth': coords[2],
                    'url': props['url']
                }
                earthquakes.append(earthquake)
            
            logger.info(f"📊 Pobrano {len(earthquakes)} trzęsień ziemi")
            return sorted(earthquakes, key=lambda x: x['magnitude'], reverse=True)
            
        except Exception as e:
            logger.error(f"❌ Błąd USGS: {e}")
            return []
    
    def get_significant_events(self) -> List[Dict]:
        """Pobierz znaczące zdarzenia"""
        try:
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            events = []
            for feature in data.get('features', []):
                props = feature['properties']
                coords = feature['geometry']['coordinates']
                
                event = {
                    'place': props['place'],
                    'magnitude': props['mag'],
                    'time': datetime.fromtimestamp(props['time'] / 1000),
                    'lat': coords[1],
                    'lon': coords[0]
                }
                events.append(event)
            
            return events
        except Exception as e:
            logger.error(f"❌ Błąd significant events: {e}")
            return []

class NASAClient:
    """Klient NASA API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def get_apod(self) -> Dict:
        """Astronomy Picture of the Day"""
        try:
            url = "https://api.nasa.gov/planetary/apod"
            params = {'api_key': self.api_key}
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            return {
                'title': data.get('title', ''),
                'url': data.get('url', ''),
                'explanation': data.get('explanation', ''),
                'date': data.get('date', ''),
                'copyright': data.get('copyright', '')
            }
        except Exception as e:
            logger.error(f"❌ Błąd APOD: {e}")
            return {}
    
    def get_asteroids(self) -> List[Dict]:
        """Pobierz przeloty asteroid"""
        try:
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            
            url = "https://api.nasa.gov/neo/rest/v1/feed"
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            asteroids = []
            for date in data.get('near_earth_objects', {}):
                for asteroid in data['near_earth_objects'][date]:
                    for approach in asteroid.get('close_approach_data', []):
                        asteroids.append({
                            'name': asteroid['name'],
                            'hazardous': asteroid['is_potentially_hazardous_asteroid'],
                            'miss_distance_km': float(approach['miss_distance']['kilometers']),
                            'velocity_kps': float(approach['relative_velocity']['kilometers_per_second']),
                            'approach_time': approach['close_approach_date_full']
                        })
            
            return asteroids[:10]  # Pierwsze 10
        except Exception as e:
            logger.error(f"❌ Błąd asteroid: {e}")
            return []

class WeatherClient:
    """Klient OpenWeather API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def get_weather(self, lat: float, lon: float) -> Dict:
        """Pobierz aktualną pogodę"""
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pl'
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            return {
                'temp': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'clouds': data['clouds']['all'],
                'visibility': data.get('visibility', 10000) / 1000,
                'wind_speed': data['wind']['speed'],
                'wind_deg': data['wind'].get('deg', 0),
                'success': True
            }
        except Exception as e:
            logger.error(f"❌ Błąd pogody: {e}")
            return {'success': False, 'error': str(e)}

class MapboxClient:
    """Klient Mapbox API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def generate_map(self, lat: float, lon: float, zoom=10) -> str:
        """Wygeneruj mapę satelitarną"""
        try:
            style = "satellite-streets-v12"
            size = "800x600"
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"pin-s+ff0000({lon},{lat})/"
                f"{lon},{lat},{zoom}/{size}@2x"
                f"?access_token={self.api_key}"
            )
            
            return map_url
        except Exception as e:
            logger.error(f"❌ Błąd Mapbox: {e}")
            return ""

# ====================== TELEGRAM BOT ======================

class TelegramBot:
    """Główny bot Telegram"""
    
    def __init__(self):
        # Sprawdź czy mamy token
        if not TELEGRAM_BOT_API:
            logger.error("❌ BRAK TELEGRAM_BOT_API! Bot nie będzie działać.")
            self.available = False
            return
        
        self.token = TELEGRAM_BOT_API
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.available = True
        
        # Inicjalizuj klientów API
        self.usgs = USGSClient(USGS_API_KEY)
        self.nasa = NASAClient(NASA_API_KEY)
        self.weather = WeatherClient(OPENWEATHER_API_KEY) if OPENWEATHER_API_KEY else None
        self.mapbox = MapboxClient(MAPBOX_API_KEY) if MAPBOX_API_KEY else None
        
        # Punkty obserwacyjne
        self.points = {
            "warszawa": {"name": "Warszawa", "lat": 52.2297, "lon": 21.0122},
            "krakow": {"name": "Kraków", "lat": 50.0614, "lon": 19.9366},
            "gdansk": {"name": "Gdańsk", "lat": 54.3722, "lon": 18.6383},
            "wroclaw": {"name": "Wrocław", "lat": 51.1079, "lon": 17.0385},
            "poznan": {"name": "Poznań", "lat": 52.4064, "lon": 16.9252},
            "szczecin": {"name": "Szczecin", "lat": 53.4289, "lon": 14.5530},
            "lodz": {"name": "Łódź", "lat": 51.7592, "lon": 19.4558},
            "lublin": {"name": "Lublin", "lat": 51.2465, "lon": 22.5684}
        }
        
        # Satelity
        self.satellites = {
            25544: {"name": "ISS", "type": "stacja", "camera": "EarthKAM"},
            39084: {"name": "Landsat 8", "type": "obserwacja", "camera": "OLI/TIRS"},
            40697: {"name": "Sentinel-2A", "type": "obserwacja", "camera": "MSI"},
            42969: {"name": "Sentinel-2B", "type": "obserwacja", "camera": "MSI"}
        }
        
        logger.info("✅ Bot Telegram zainicjalizowany")
    
    def send_message(self, chat_id: int, text: str, parse_html: bool = True):
        """Wyślij wiadomość"""
        if not self.available:
            logger.error("❌ Bot nie jest dostępny - brak tokena")
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML" if parse_html else None,
            "disable_web_page_preview": True
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Błąd wysyłania: {e}")
            return False
    
    def send_location(self, chat_id: int, lat: float, lon: float):
        """Wyślij lokalizację"""
        if not self.available:
            return
        
        url = f"{self.base_url}/sendLocation"
        payload = {
            "chat_id": chat_id,
            "latitude": lat,
            "longitude": lon
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except:
            pass
    
    def handle_command(self, chat_id: int, command: str, args: List[str]):
        """Obsłuż komendę"""
        command = command.lower()
        
        if command == "start":
            self.cmd_start(chat_id)
        elif command == "help":
            self.cmd_help(chat_id)
        elif command == "points":
            self.cmd_points(chat_id)
        elif command == "satellites":
            self.cmd_satellites(chat_id)
        elif command == "earthquakes":
            self.cmd_earthquakes(chat_id, args)
        elif command == "asteroids":
            self.cmd_asteroids(chat_id)
        elif command == "apod":
            self.cmd_apod(chat_id)
        elif command == "weather":
            self.cmd_weather(chat_id, args)
        elif command == "map":
            self.cmd_map(chat_id, args)
        else:
            self.send_message(chat_id, "❌ Nieznana komenda. Użyj /help")
    
    def cmd_start(self, chat_id: int):
        """Komenda /start"""
        message = """
🚀 <b>EARTH OBSERVATION BOT v6.0</b>
🌍 <i>Produkcyjna wersja - wszystkie API ukryte</i>

📡 <b>Dostępne funkcje:</b>
"""
        
        # Sprawdź które API są dostępne
        if self.usgs:
            message += "• 🚨 Trzęsienia ziemi (USGS)\n"
        
        if self.nasa:
            message += "• 🪐 Asteroidy i APOD (NASA)\n"
        
        if self.weather:
            message += "• 🌤️ Pogoda (OpenWeather)\n"
        
        if self.mapbox:
            message += "• 🗺️ Mapy (Mapbox)\n"
        
        message += """
📋 <b>Główne komendy:</b>
<code>/help</code> - pomoc
<code>/points</code> - punkty obserwacyjne
<code>/earthquakes [magnituda] [godziny]</code> - trzęsienia ziemi
<code>/weather [punkt]</code> - pogoda
<code>/asteroids</code> - asteroidy
<code>/apod</code> - zdjęcie dnia NASA
<code>/map [punkt]</code> - mapa satelitarna

🚀 <b>Przykłady:</b>
• <code>/earthquakes 5.0 24</code>
• <code>/weather warszawa</code>
• <code>/map krakow</code>

<b>Bot gotowy do działania! 🌍</b>
"""
        self.send_message(chat_id, message)
    
    def cmd_help(self, chat_id: int):
        """Komenda /help"""
        message = """
📋 <b>DOSTĘPNE KOMENDY:</b>

<b>📍 PUNKTY OBSERWACYJNE:</b>
<code>/points</code> - 8 głównych miast Polski

<b>🚨 TRZĘSIENIA ZIEMI:</b>
<code>/earthquakes [magnituda] [godziny]</code>
• Przykład: <code>/earthquakes 5.0 24</code>
• Domyślnie: 4.0M, 24h
• Dane z USGS

<b>🪐 NASA:</b>
<code>/asteroids</code> - przeloty asteroid (7 dni)
<code>/apod</code> - Astronomy Picture of the Day

<b>🌤️ POGODA:</b>
<code>/weather [punkt]</code>
• Przykład: <code>/weather warszawa</code>
• Punkty: warszawa, krakow, gdansk, wroclaw, poznan, szczecin, lodz, lublin
• Dane z OpenWeather

<b>🗺️ MAPY:</b>
<code>/map [punkt]</code> - mapa satelitarna
• Przykład: <code>/map warszawa</code>

<b>🔧 TECHNICZNE:</b>
• Wersja: 6.0
• Hosting: Render.com
• API: wszystkie ukryte w environment variables
• Status: <b>AKTYWNY</b>
"""
        self.send_message(chat_id, message)
    
    def cmd_points(self, chat_id: int):
        """Komenda /points"""
        message = "📍 <b>PUNKTY OBSERWACYJNE W POLSCE:</b>\n\n"
        
        for key, point in self.points.items():
            message += f"• <b>{key}</b> - {point['name']}\n"
            message += f"  🌍 {point['lat']:.4f}, {point['lon']:.4f}\n\n"
        
        message += "🎯 <b>Użyj:</b> <code>/weather [nazwa_punktu]</code>"
        self.send_message(chat_id, message)
    
    def cmd_satellites(self, chat_id: int):
        """Komenda /satellites"""
        message = "🛰️ <b>SATELITY OBSERWACYJNE:</b>\n\n"
        
        for norad_id, sat in self.satellites.items():
            message += f"• <b>{norad_id}</b> - {sat['name']}\n"
            message += f"  📡 {sat['type']} | 📷 {sat['camera']}\n\n"
        
        self.send_message(chat_id, message)
    
    def cmd_earthquakes(self, chat_id: int, args: List[str]):
        """Komenda /earthquakes"""
        if not self.usgs:
            self.send_message(chat_id, "❌ USGS API niedostępne")
            return
        
        # Parsuj argumenty
        min_mag = 4.0
        hours = 24
        
        if len(args) >= 1:
            try:
                min_mag = float(args[0])
            except:
                pass
        
        if len(args) >= 2:
            try:
                hours = int(args[1])
            except:
                pass
        
        self.send_message(chat_id, f"🌋 Pobieram trzęsienia ziemi (> {min_mag}M) z {hours}h...")
        
        earthquakes = self.usgs.get_earthquakes(min_mag, hours)
        
        if not earthquakes:
            self.send_message(chat_id, f"🌍 Brak trzęsień ziemi > {min_mag}M w ostatnich {hours}h.")
            return
        
        message = f"🌋 <b>TRZĘSIENIA ZIEMI (>{min_mag}M, {hours}h):</b>\n\n"
        
        for i, quake in enumerate(earthquakes[:5], 1):
            time_ago = datetime.utcnow() - quake['time']
            hours_ago = time_ago.total_seconds() / 3600
            
            message += f"{i}. <b>{quake['place']}</b>\n"
            message += f"   ⚡ <b>{quake['magnitude']}M</b> | 📉 {quake['depth']:.1f} km\n"
            message += f"   ⏰ {hours_ago:.1f}h temu\n"
            message += f"   🌍 {quake['lat']:.3f}, {quake['lon']:.3f}\n\n"
        
        if len(earthquakes) > 5:
            message += f"... i {len(earthquakes) - 5} więcej\n"
        
        message += f"🔗 <a href='https://earthquake.usgs.gov/earthquakes/map/'>Mapa trzęsień</a>"
        
        self.send_message(chat_id, message)
        
        # Wyślij lokalizację największego trzęsienia
        if earthquakes:
            biggest_eq = earthquakes[0]
            self.send_location(chat_id, biggest_eq['lat'], biggest_eq['lon'])
    
    def cmd_asteroids(self, chat_id: int):
        """Komenda /asteroids"""
        if not self.nasa:
            self.send_message(chat_id, "❌ NASA API niedostępne")
            return
        
        self.send_message(chat_id, "🪐 Pobieram dane o asteroidach...")
        
        asteroids = self.nasa.get_asteroids()
        
        if not asteroids:
            self.send_message(chat_id, "🌍 Brak bliskich przelotów asteroid w ciągu 7 dni.")
            return
        
        message = "🪐 <b>BLISKIE PRZELOTY ASTEROID (7 dni):</b>\n\n"
        
        for i, asteroid in enumerate(asteroids[:3], 1):
            distance_mln_km = asteroid['miss_distance_km'] / 1000000
            
            message += f"{i}. <b>{asteroid['name']}</b>\n"
            message += f"   🎯 {distance_mln_km:.2f} mln km\n"
            message += f"   🚀 {asteroid['velocity_kps']:.2f} km/s\n"
            message += f"   ⏰ {asteroid['approach_time']}\n"
            message += f"   ⚠️ <b>{'NIEBEZPIECZNA' if asteroid['hazardous'] else 'Bezpieczna'}</b>\n\n"
        
        self.send_message(chat_id, message)
    
    def cmd_apod(self, chat_id: int):
        """Komenda /apod"""
        if not self.nasa:
            self.send_message(chat_id, "❌ NASA API niedostępne")
            return
        
        apod = self.nasa.get_apod()
        
        if not apod or 'url' not in apod:
            self.send_message(chat_id, "❌ Nie udało się pobrać APOD")
            return
        
        message = f"""
🪐 <b>ASTRONOMY PICTURE OF THE DAY</b>

📅 <b>{apod.get('date', 'Dzisiaj')}</b>
🏷️ <b>{apod.get('title', 'Brak tytułu')}</b>

📖 {apod.get('explanation', 'Brak opisu')[:300]}...

👨‍🎨 <b>Autor:</b> {apod.get('copyright', 'Nieznany')}

<a href="{apod['url']}">🔗 Zobacz zdjęcie</a>
"""
        
        self.send_message(chat_id, message)
    
    def cmd_weather(self, chat_id: int, args: List[str]):
        """Komenda /weather"""
        if not self.weather:
            self.send_message(chat_id, "❌ OpenWeather API niedostępne")
            return
        
        if not args:
            self.send_message(chat_id,
                "❌ <b>Format:</b> <code>/weather [punkt]</code>\n\n"
                "Przykład: <code>/weather warszawa</code>\n\n"
                "Użyj <code>/points</code> aby zobaczyć punkty."
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznany punkt. Użyj /points")
            return
        
        self.send_message(chat_id, f"🌤️ Pobieram pogodę dla {point['name']}...")
        
        weather = self.weather.get_weather(point['lat'], point['lon'])
        
        if not weather.get('success', False):
            self.send_message(chat_id, f"❌ Błąd pobierania pogody: {weather.get('error', 'Nieznany błąd')}")
            return
        
        # Oblicz ocenę warunków obserwacyjnych
        score = 10.0
        
        # Zachmurzenie
        if weather['clouds'] > 20:
            score -= (weather['clouds'] - 20) * 0.1
        
        # Widoczność
        if weather['visibility'] < 5:
            score -= 2
        
        # Wilgotność
        if weather['humidity'] > 80:
            score -= (weather['humidity'] - 80) * 0.05
        
        # Wiatr
        if weather['wind_speed'] > 10:
            score -= (weather['wind_speed'] - 10) * 0.1
        
        score = max(0, min(10, round(score, 1)))
        
        message = f"""
🌤️ <b>POGODA - {point['name'].upper()}</b>

🌡️ <b>Temperatura:</b> {weather['temp']:.1f}°C
🤏 <b>Odczuwalna:</b> {weather['feels_like']:.1f}°C
💧 <b>Wilgotność:</b> {weather['humidity']}%
☁️ <b>Zachmurzenie:</b> {weather['clouds']}%
👁️ <b>Widoczność:</b> {weather['visibility']:.1f} km
💨 <b>Wiatr:</b> {weather['wind_speed']} m/s
📖 <b>Opis:</b> {weather['description']}

📊 <b>OCENA WARUNKÓW OBSERWACYJNYCH:</b>
<b>{score:.1f}/10</b>

{"✅ <b>Doskonale warunki do obserwacji!</b>" if score >= 8 else ""}
{"⚠️ <b>Warunki średnie</b>" if 5 <= score < 8 else ""}
{"❌ <b>Złe warunki do obserwacji</b>" if score < 5 else ""}
"""
        
        self.send_message(chat_id, message)
        self.send_location(chat_id, point['lat'], point['lon'])
    
    def cmd_map(self, chat_id: int, args: List[str]):
        """Komenda /map"""
        if not self.mapbox:
            self.send_message(chat_id, "❌ Mapbox API niedostępne")
            return
        
        if not args:
            self.send_message(chat_id,
                "❌ <b>Format:</b> <code>/map [punkt]</code>\n\n"
                "Przykład: <code>/map warszawa</code>"
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznany punkt. Użyj /points")
            return
        
        self.send_message(chat_id, f"🗺️ Generuję mapę dla {point['name']}...")
        
        map_url = self.mapbox.generate_map(point['lat'], point['lon'])
        
        if not map_url:
            self.send_message(chat_id, "❌ Nie udało się wygenerować mapy")
            return
        
        message = f"""
🗺️ <b>MAPA SATELITARNA</b>
📍 <b>{point['name'].upper()}</b>
🌍 {point['lat']:.4f}, {point['lon']:.4f}

<a href="{map_url}">🔗 Kliknij aby zobaczyć mapę</a>

<b>Informacje:</b>
• Zdjęcie satelitarne z Mapbox
• Czerwony znacznik - lokalizacja punktu
• Zoom: 10x
"""
        
        self.send_message(chat_id, message)
        self.send_location(chat_id, point['lat'], point['lon'])

# ====================== FLASK APP ======================
app = Flask(__name__)
bot = TelegramBot()

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌍 Earth Observation Bot v6.0</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                margin-top: 20px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }
            h1 {
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 10px;
                color: white;
            }
            .subtitle {
                text-align: center;
                font-size: 1.2em;
                margin-bottom: 30px;
                opacity: 0.9;
            }
            .status {
                background: rgba(76, 175, 80, 0.2);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin: 20px 0;
                border-left: 5px solid #4CAF50;
            }
            .api-status {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .api-item {
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            .api-item.ok {
                border-left: 5px solid #4CAF50;
            }
            .api-item.error {
                border-left: 5px solid #f44336;
            }
            .commands {
                background: rgba(0, 0, 0, 0.2);
                padding: 25px;
                border-radius: 15px;
                margin-top: 30px;
            }
            code {
                background: rgba(0, 0, 0, 0.3);
                padding: 5px 10px;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                display: inline-block;
                margin: 5px;
            }
            .telegram-link {
                display: inline-block;
                background: #0088cc;
                color: white;
                padding: 12px 25px;
                border-radius: 10px;
                text-decoration: none;
                margin-top: 20px;
                font-weight: bold;
                transition: background 0.3s;
            }
            .telegram-link:hover {
                background: #006699;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ Earth Observation Bot</h1>
            <div class="subtitle">v6.0 - Produkcyjna wersja z ukrytymi API</div>
            
            <div class="status">
                ✅ <b>SYSTEM AKTYWNY</b> | 🌍 Wersja 6.0 | 🔐 API ukryte | 🚀 Render.com
            </div>
            
            <div class="api-status">
                <div class="api-item ''' + ('ok' if TELEGRAM_BOT_API else 'error') + '''">
                    <h3>🤖 Telegram Bot</h3>
                    <p>''' + ('✅ Aktywny' if TELEGRAM_BOT_API else '❌ Brak tokena') + '''</p>
                </div>
                <div class="api-item ok">
                    <h3>🚨 USGS</h3>
                    <p>✅ Aktywny</p>
                </div>
                <div class="api-item ''' + ('ok' if NASA_API_KEY else 'error') + '''">
                    <h3>🪐 NASA</h3>
                    <p>''' + ('✅ Aktywny' if NASA_API_KEY else '⚠️ Demo mode') + '''</p>
                </div>
                <div class="api-item ''' + ('ok' if OPENWEATHER_API_KEY else 'error') + '''">
                    <h3>🌤️ OpenWeather</h3>
                    <p>''' + ('✅ Aktywny' if OPENWEATHER_API_KEY else '❌ Brak klucza') + '''</p>
                </div>
                <div class="api-item ''' + ('ok' if MAPBOX_API_KEY else 'error') + '''">
                    <h3>🗺️ Mapbox</h3>
                    <p>''' + ('✅ Aktywny' if MAPBOX_API_KEY else '❌ Brak klucza') + '''</p>
                </div>
            </div>
            
            <div class="commands">
                <h3>📋 Dostępne komendy w Telegramie:</h3>
                <p><code>/start</code> - Informacje o bocie</p>
                <p><code>/help</code> - Lista wszystkich komend</p>
                <p><code>/points</code> - Punkty obserwacyjne</p>
                <p><code>/earthquakes [magnituda] [godziny]</code> - Trzęsienia ziemi</p>
                <p><code>/weather [punkt]</code> - Pogoda dla punktu</p>
                <p><code>/asteroids</code> - Przeloty asteroid</p>
                <p><code>/apod</code> - Astronomy Picture of the Day</p>
                <p><code>/map [punkt]</code> - Mapa satelitarna</p>
                
                <h3>📍 Przykładowe punkty:</h3>
                <p><code>warszawa</code>, <code>krakow</code>, <code>gdansk</code>, <code>wroclaw</code></p>
                <p><code>poznan</code>, <code>szczecin</code>, <code>lodz</code>, <code>lublin</code></p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/your_bot_username" class="telegram-link" target="_blank">
                    💬 Rozpocznij rozmowę z botem
                </a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook dla Telegrama"""
    try:
        data = request.get_json()
        
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "").strip()
            
            logger.info(f"📨 Otrzymano: {text} od {chat_id}")
            
            if text.startswith('/'):
                parts = text.split()
                command = parts[0][1:]  # Usuń '/'
                args = parts[1:] if len(parts) > 1 else []
                
                bot.handle_command(chat_id, command, args)
            else:
                bot.send_message(chat_id,
                    "🛰️ <b>Earth Observation Bot v6.0</b>\n\n"
                    "Użyj /help aby zobaczyć dostępne komendy.\n\n"
                    "<b>Przykłady:</b>\n"
                    "• /earthquakes 5.0 24\n"
                    "• /weather warszawa\n"
                    "• /map krakow\n"
                    "• /asteroids"
                )
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Ustaw webhook (dla testów)"""
    try:
        webhook_url = f"{RENDER_URL}/webhook"
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_API}/setWebhook",
            json={"url": webhook_url}
        )
        
        return jsonify({
            "status": "success" if response.status_code == 200 else "error",
            "webhook_url": webhook_url,
            "response": response.json() if response.status_code == 200 else response.text
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/status', methods=['GET'])
def status():
    """Strona statusu API"""
    return jsonify({
        "status": "online",
        "version": "6.0",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "telegram_bot_api": "configured" if TELEGRAM_BOT_API else "missing",
            "usgs_api_key": "configured" if USGS_API_KEY else "not_required",
            "nasa_api_key": "configured" if NASA_API_KEY and NASA_API_KEY != "DEMO_KEY" else "demo",
            "openweather_api_key": "configured" if OPENWEATHER_API_KEY else "missing",
            "mapbox_api_key": "configured" if MAPBOX_API_KEY else "missing",
            "n2yo_api_key": "configured" if N2YO_API_KEY and N2YO_API_KEY != "DEMO_KEY" else "demo",
            "deepseek_api_key": "configured" if DEEPSEEK_API_KEY else "missing"
        },
        "apis": {
            "usgs": "active",
            "nasa": "active" if NASA_API_KEY else "demo_mode",
            "openweather": "active" if OPENWEATHER_API_KEY else "inactive",
            "mapbox": "active" if MAPBOX_API_KEY else "inactive"
        }
    })

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 URUCHAMIANIE EARTH OBSERVATION BOT v6.0 - PRODUCTION")
    print("=" * 80)
    
    # Log status API
    print("🔧 STATUS API:")
    print(f"   🤖 Telegram Bot: {'✅ SKONFIGUROWANY' if TELEGRAM_BOT_API else '❌ BRAK TOKENA'}")
    print(f"   🚨 USGS: ✅ DOSTĘPNE")
    print(f"   🪐 NASA: {'✅ SKONFIGUROWANY' if NASA_API_KEY and NASA_API_KEY != 'DEMO_KEY' else '⚠️ DEMO MODE'}")
    print(f"   🌤️ OpenWeather: {'✅ SKONFIGUROWANY' if OPENWEATHER_API_KEY else '❌ BRAK KLUCZA'}")
    print(f"   🗺️ Mapbox: {'✅ SKONFIGUROWANY' if MAPBOX_API_KEY else '❌ BRAK KLUCZA'}")
    print("=" * 80)
    
    # Ustaw webhook jeśli mamy token
    if TELEGRAM_BOT_API:
        try:
            webhook_url = f"{RENDER_URL}/webhook"
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_API}/setWebhook",
                json={"url": webhook_url},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Webhook ustawiony: {webhook_url}")
            else:
                print(f"⚠️ Błąd ustawiania webhooka: {response.text}")
        except Exception as e:
            print(f"⚠️ Nie udało się ustawić webhooka: {e}")
            print(f"ℹ️ Możesz ustawić ręcznie: https://api.telegram.org/bot{TELEGRAM_BOT_API}/setWebhook?url={RENDER_URL}/webhook")
    else:
        print("⚠️ Brak TELEGRAM_BOT_API - webhook nie będzie działać")
    
    print("🤖 BOT AKTYWNY!")
    print("=" * 80)
    print(f"🌐 Strona główna: {RENDER_URL}")
    print(f"📊 Status API: {RENDER_URL}/status")
    print(f"🔄 Webhook: {RENDER_URL}/webhook")
    print("=" * 80)
    
    # Uruchom aplikację
    app.run(host="0.0.0.0", port=PORT, debug=False)