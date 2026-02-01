#!/usr/bin/env python3
"""
🛰️ EARTH OBSERVATION PLATFORM v6.0 - COMPLETE EDITION
✅ Skyfield Orbital Tracking
✅ USGS Real-Time Events
✅ NASA Earth Data
✅ Mapbox Visualization
✅ DeepSeek AI Analysis
✅ OpenWeather Conditions
✅ Telegram Notifications
✅ Render Cloud Ready
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
from queue import Queue
import logging

# Import Skyfield
from skyfield.api import load, EarthSatellite, Topos, utc
import pytz

# ====================== KONFIGURACJA ======================
print("=" * 80)
print("🚀 EARTH OBSERVATION PLATFORM v6.0")
print("🌍 Kompletna integracja 6 API")
print("=" * 80)

# Tokeny API z środowiska
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
USGS_API_KEY  = od.getenv("USGS_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY", "")
N2YO_API_KEY = os.getenv("N2YO_API_KEY", "")
NASA_API_KEY = os.getenv("NASA_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
RENDER_URL = os.getenv("RENDER_URL", "https://telegram-bot-1-7l4g.onrender.com")
PORT = int(os.getenv("PORT", 10000))

# Konfiguracja systemu
WEBHOOK_URL = f"{RENDER_URL}/webhook"
DB_FILE = "earth_observation_v6.db"
CHECK_INTERVAL = 300  # 5 minut

# ====================== LOGGING ======================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('earth_observation.log')
    ]
)
logger = logging.getLogger(__name__)

# ====================== DATA STRUCTURES ======================
@dataclass
class Satellite:
    """Struktura danych satelity"""
    norad_id: int
    name: str
    type: str
    camera: str
    swath_km: float
    resolution_m: float
    min_elevation: float
    tle_line1: str = ""
    tle_line2: str = ""
    skyfield_sat: Any = None
    last_update: datetime = None

@dataclass
class ObservationPoint:
    """Punkt obserwacyjny"""
    name: str
    lat: float
    lon: float
    elevation: float = 0
    skyfield_topos: Any = None

@dataclass
class Earthquake:
    """Dane trzęsienia ziemi"""
    id: str
    place: str
    magnitude: float
    time: datetime
    lat: float
    lon: float
    depth: float
    url: str
    significance: int

# ====================== SKYFIELD INIT ======================
try:
    ts = load.timescale()
    logger.info("✅ Skyfield timescale załadowany")
except Exception as e:
    logger.error(f"⚠️ Skyfield error: {e}")
    ts = None

# ====================== MODUŁ USGS ======================
class USGSIntegration:
    """Integracja z USGS API - trzęsienia ziemi, wulkany"""
    
    BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1"
    EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
    
    def get_recent_earthquakes(self, min_magnitude=4.0, hours=24, limit=20) -> List[Earthquake]:
        """Pobierz ostatnie trzęsienia ziemi"""
        try:
            endtime = datetime.utcnow()
            starttime = endtime - timedelta(hours=hours)
            
            params = {
                "format": "geojson",
                "starttime": starttime.strftime("%Y-%m-%dT%H:%M:%S"),
                "endtime": endtime.strftime("%Y-%m-%dT%H:%M:%S"),
                "minmagnitude": min_magnitude,
                "orderby": "time",
                "limit": limit
            }
            
            response = requests.get(f"{self.BASE_URL}/query", params=params, timeout=10)
            data = response.json()
            
            earthquakes = []
            for feature in data.get('features', []):
                props = feature['properties']
                coords = feature['geometry']['coordinates']
                
                quake = Earthquake(
                    id=feature['id'],
                    place=props['place'],
                    magnitude=props['mag'],
                    time=datetime.fromtimestamp(props['time'] / 1000),
                    lat=coords[1],
                    lon=coords[0],
                    depth=coords[2],
                    url=props['url'],
                    significance=props.get('sig', 0)
                )
                earthquakes.append(quake)
            
            logger.info(f"📊 Pobrano {len(earthquakes)} trzęsień ziemi")
            return sorted(earthquakes, key=lambda x: x.magnitude, reverse=True)
            
        except Exception as e:
            logger.error(f"❌ Błąd USGS: {e}")
            return []
    
    def get_significant_earthquakes(self, min_magnitude=5.5) -> List[Earthquake]:
        """Pobierz znaczące trzęsienia ziemi"""
        try:
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            earthquakes = []
            for feature in data.get('features', []):
                props = feature['properties']
                if props['mag'] >= min_magnitude:
                    coords = feature['geometry']['coordinates']
                    
                    quake = Earthquake(
                        id=feature['id'],
                        place=props['place'],
                        magnitude=props['mag'],
                        time=datetime.fromtimestamp(props['time'] / 1000),
                        lat=coords[1],
                        lon=coords[0],
                        depth=coords[2],
                        url=props['url'],
                        significance=props.get('sig', 0)
                    )
                    earthquakes.append(quake)
            
            return earthquakes
        except Exception as e:
            logger.error(f"❌ Błąd significant earthquakes: {e}")
            return []
    
    def get_natural_events(self) -> List[Dict]:
        """Pobierz naturalne zdarzenia (EONET)"""
        try:
            params = {'status': 'open', 'limit': 50}
            response = requests.get(self.EONET_URL, params=params, timeout=10)
            data = response.json()
            
            events = []
            for event in data.get('events', []):
                event_data = {
                    'id': event['id'],
                    'title': event['title'],
                    'description': event.get('description', ''),
                    'categories': [cat['title'] for cat in event.get('categories', [])],
                    'coordinates': None,
                    'date': None
                }
                
                if event.get('geometries'):
                    geom = event['geometries'][0]
                    if 'coordinates' in geom:
                        event_data['coordinates'] = {
                            'lon': geom['coordinates'][0],
                            'lat': geom['coordinates'][1]
                        }
                        event_data['date'] = geom.get('date', '')
                
                events.append(event_data)
            
            logger.info(f"🌪️ Pobrano {len(events)} zdarzeń naturalnych")
            return events
        except Exception as e:
            logger.error(f"❌ Błąd EONET: {e}")
            return []
    
    def get_landsat_archive(self, lat: float, lon: float, 
                           date: str = None) -> Optional[Dict]:
        """Sprawdź dostępność zdjęć Landsat"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Landsat Look URL (przykładowy)
            base_url = "https://landsatlook.usgs.gov/stac-server"
            
            # W praktyce potrzebne byłoby konto i autoryzacja
            # Tutaj zwracamy mock danych
            return {
                'available': True,
                'date': date,
                'coordinates': {'lat': lat, 'lon': lon},
                'satellites': ['Landsat 8', 'Landsat 9'],
                'note': 'Wymaga konta USGS EarthExplorer'
            }
        except Exception as e:
            logger.error(f"❌ Błąd Landsat: {e}")
            return None

# ====================== MODUŁ NASA ======================
class NASAIntegration:
    """Integracja z NASA API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def get_earth_imagery(self, lat: float, lon: float, date: str = None) -> Optional[Dict]:
        """Pobierz zdjęcia Ziemi"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            url = "https://api.nasa.gov/planetary/earth/imagery"
            params = {
                'lat': lat,
                'lon': lon,
                'date': date,
                'dim': 0.1,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return {
                    'url': response.url,
                    'date': date,
                    'coordinates': {'lat': lat, 'lon': lon},
                    'success': True
                }
            else:
                # Fallback: zdjęcie archiwalne
                return {
                    'url': f"https://api.nasa.gov/planetary/earth/assets?lon={lon}&lat={lat}&date={date}&dim=0.1&api_key={self.api_key}",
                    'date': date,
                    'coordinates': {'lat': lat, 'lon': lon},
                    'success': False,
                    'note': 'Brak aktualnego zdjęcia, spróbuj archiwalnego'
                }
                
        except Exception as e:
            logger.error(f"❌ Błąd NASA Earth: {e}")
            return None
    
    def get_asteroids(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Pobierz przeloty asteroid"""
        try:
            if start_date is None:
                start_date = datetime.now().strftime('%Y-%m-%d')
            if end_date is None:
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
                        miss_km = float(approach['miss_distance']['kilometers'])
                        if miss_km < 10000000:  # 10 mln km
                            asteroids.append({
                                'name': asteroid['name'],
                                'diameter_min': asteroid['estimated_diameter']['kilometers']['estimated_diameter_min'],
                                'diameter_max': asteroid['estimated_diameter']['kilometers']['estimated_diameter_max'],
                                'hazardous': asteroid['is_potentially_hazardous_asteroid'],
                                'miss_distance_km': miss_km,
                                'velocity_kps': float(approach['relative_velocity']['kilometers_per_second']),
                                'approach_time': approach['close_approach_date_full']
                            })
            
            logger.info(f"🪐 Znaleziono {len(asteroids)} asteroid")
            return sorted(asteroids, key=lambda x: x['miss_distance_km'])
            
        except Exception as e:
            logger.error(f"❌ Błąd asteroid: {e}")
            return []
    
    def get_apod(self, date: str = None) -> Dict:
        """Astronomy Picture of the Day"""
        try:
            url = "https://api.nasa.gov/planetary/apod"
            params = {'api_key': self.api_key}
            if date:
                params['date'] = date
            
            response = requests.get(url, params=params, timeout=15)
            return response.json()
        except Exception as e:
            logger.error(f"❌ Błąd APOD: {e}")
            return {}

# ====================== MODUŁ MAPBOX ======================
class MapboxVisualizer:
    """Generowanie map i wizualizacji"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def generate_satellite_map(self, center_lat: float, center_lon: float,
                              markers: List[Dict] = None, zoom: int = 10) -> str:
        """Wygeneruj mapę satelitarną"""
        try:
            style = "satellite-streets-v12"
            size = "800x600"
            
            # Marker string
            marker_str = ""
            if markers:
                for marker in markers:
                    color = marker.get('color', 'ff0000')
                    label = marker.get('label', 's')
                    marker_str += f"pin-{label}+{color}({marker['lon']},{marker['lat']})/"
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"{marker_str}"
                f"{center_lon},{center_lat},{zoom}/{size}@2x"
                f"?access_token={self.api_key}"
            )
            
            return map_url
        except Exception as e:
            logger.error(f"❌ Błąd Mapbox: {e}")
            return ""
    
    def generate_trajectory_map(self, trajectory: List[Tuple[float, float]],
                               center_lat: float, center_lon: float) -> str:
        """Wygeneruj mapę z trajektorią"""
        try:
            style = "satellite-streets-v12"
            
            # Konwertuj trajektorię do stringa
            path_coords = ""
            for lat, lon in trajectory:
                path_coords += f"{lon},{lat};"
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"path-5+f44-0.5({path_coords[:-1]})/"
                f"{center_lon},{center_lat},9/800x600@2x"
                f"?access_token={self.api_key}"
            )
            
            return map_url
        except Exception as e:
            logger.error(f"❌ Błąd trajektorii: {e}")
            return ""

# ====================== MODUŁ DEEPSEEK AI ======================
class DeepSeekAnalyzer:
    """Analiza AI przez DeepSeek"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
    
    async def analyze_async(self, prompt: str, max_tokens: int = 1000) -> str:
        """Asynchroniczna analiza AI"""
        if not self.api_key:
            return "❌ Brak klucza API DeepSeek"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "Jesteś ekspertem od obserwacji satelitarnych, astronomii i geologii."
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                    
        except Exception as e:
            logger.error(f"❌ Błąd DeepSeek: {e}")
            return f"❌ Błąd analizy AI: {str(e)}"
    
    async def analyze_observation(self, observation_data: Dict) -> str:
        """Przeanalizuj okno obserwacyjne"""
        prompt = f"""
        Przeanalizuj okno obserwacyjne satelity:
        
        SATELITA: {observation_data.get('satellite_name', 'Nieznany')}
        TYP: {observation_data.get('satellite_type', 'Nieznany')}
        CZAS: {observation_data.get('time', 'Nieznany')}
        ELEWACJA: {observation_data.get('elevation', 0)}°
        PRAWDOPODOBIEŃSTWO: {observation_data.get('probability', 0)*100:.0f}%
        
        Warunki pogodowe: {observation_data.get('weather', 'Nieznane')}
        
        Oceń jakość okna (1-10) i daj praktyczne porady dla obserwatora.
        """
        
        return await self.analyze_async(prompt)
    
    async def analyze_earthquake(self, earthquake_data: Dict) -> str:
        """Przeanalizuj trzęsienie ziemi"""
        prompt = f"""
        Przeanalizuj trzęsienie ziemi:
        
        LOKALIZACJA: {earthquake_data.get('place', 'Nieznane')}
        MAGNITUDA: {earthquake_data.get('magnitude', 0)}
        GŁĘBOKOŚĆ: {earthquake_data.get('depth', 0)} km
        CZAS: {earthquake_data.get('time', 'Nieznany')}
        
        Oceń znaczenie tego zdarzenia i potencjalne skutki.
        Poradź jakie satelity mogą być przydatne do obserwacji.
        """
        
        return await self.analyze_async(prompt)

# ====================== MODUŁ POGODY ======================
class WeatherIntegration:
    """Integracja z OpenWeather"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def get_current_weather(self, lat: float, lon: float) -> Dict:
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
                'rain_1h': data.get('rain', {}).get('1h', 0),
                'snow_1h': data.get('snow', {}).get('1h', 0),
                'success': True
            }
        except Exception as e:
            logger.error(f"❌ Błąd pogody: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_forecast(self, lat: float, lon: float, hours: int = 24) -> List[Dict]:
        """Pobierz prognozę pogody"""
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pl',
                'cnt': hours // 3
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            forecast = []
            for item in data['list']:
                forecast.append({
                    'time': datetime.fromtimestamp(item['dt']),
                    'temp': item['main']['temp'],
                    'temp_min': item['main']['temp_min'],
                    'temp_max': item['main']['temp_max'],
                    'humidity': item['main']['humidity'],
                    'description': item['weather'][0]['description'],
                    'clouds': item['clouds']['all'],
                    'wind_speed': item['wind']['speed'],
                    'precipitation': item.get('pop', 0)
                })
            
            return forecast
        except Exception as e:
            logger.error(f"❌ Błąd prognozy: {e}")
            return []
    
    def calculate_observation_score(self, weather: Dict) -> float:
        """Oblicz ocenę warunków obserwacyjnych (0-10)"""
        if not weather.get('success', False):
            return 5.0  # Średnia jeśli brak danych
        
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
        
        # Opady
        if weather.get('rain_1h', 0) > 0:
            score -= 3
        elif weather.get('snow_1h', 0) > 0:
            score -= 1
        
        # Wiatr
        if weather['wind_speed'] > 10:
            score -= (weather['wind_speed'] - 10) * 0.1
        
        return max(0, min(10, round(score, 1)))

# ====================== TLE MANAGER ======================
class TLEManager:
    """Menadżer danych orbitalnych"""
    
    def __init__(self):
        self.satellites: Dict[int, Satellite] = {}
        self.load_satellites()
    
    def load_satellites(self):
        """Załaduj katalog satelitów"""
        self.satellites = {
            39084: Satellite(39084, "LANDSAT 8", "observation", "OLI/TIRS", 185, 15, 30),
            40697: Satellite(40697, "SENTINEL-2A", "observation", "MSI", 290, 10, 30),
            42969: Satellite(42969, "SENTINEL-2B", "observation", "MSI", 290, 10, 30),
            25544: Satellite(25544, "ISS", "station", "EarthKAM", 10, 10, 20),
            25994: Satellite(25994, "TERRA", "observation", "MODIS", 2330, 250, 25),
            27424: Satellite(27424, "AQUA", "observation", "MODIS", 2330, 250, 25),
            49260: Satellite(49260, "LANDSAT 9", "observation", "OLI-2/TIRS-2", 185, 15, 30),
            43013: Satellite(43013, "NOAA-20", "weather", "VIIRS", 3000, 375, 20)
        }
        logger.info(f"📡 Załadowano {len(self.satellites)} satelitów")
    
    def fetch_tle(self, norad_id: int) -> Optional[Tuple[str, str]]:
        """Pobierz aktualne TLE"""
        try:
            urls = [
                f'https://celestrak.com/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE',
                f'https://tle.ivanstanojevic.me/api/tle/{norad_id}',
                f'https://data.ivanstanojevic.me/api/tle/{norad_id}'
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        if 'celestrak' in url:
                            lines = response.text.strip().split('\n')
                            if len(lines) >= 3:
                                return lines[1], lines[2]
                        else:
                            data = response.json()
                            if 'line1' in data and 'line2' in data:
                                return data['line1'], data['line2']
                except:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"❌ Błąd TLE {norad_id}: {e}")
            return None
    
    def get_satellite(self, norad_id: int) -> Optional[Satellite]:
        """Pobierz satelitę z TLE"""
        sat = self.satellites.get(norad_id)
        if not sat:
            return None
        
        # Aktualizuj TLE jeśli stare
        if sat.last_update is None or (datetime.utcnow() - sat.last_update).total_seconds() > 43200:
            tle = self.fetch_tle(norad_id)
            if tle:
                sat.tle_line1, sat.tle_line2 = tle
                try:
                    sat.skyfield_sat = EarthSatellite(sat.tle_line1, sat.tle_line2, sat.name, ts)
                    sat.last_update = datetime.utcnow()
                    logger.info(f"✅ Zaktualizowano {sat.name}")
                except Exception as e:
                    logger.error(f"❌ Błąd Skyfield {norad_id}: {e}")
        
        return sat

# ====================== PREDYKTOR PRZELOTÓW ======================
class PassPredictor:
    """Predykcja przelotów satelitów"""
    
    def __init__(self, tle_manager: TLEManager):
        self.tle_manager = tle_manager
        self.EARTH_RADIUS_KM = 6371
    
    def predict_passes(self, norad_id: int, point: ObservationPoint,
                      days_ahead: int = 7, min_elevation: float = 10) -> List[Dict]:
        """Przewiduj przeloty satelity"""
        satellite = self.tle_manager.get_satellite(norad_id)
        if not satellite or not satellite.skyfield_sat:
            return []
        
        passes = []
        observer = point.skyfield_topos
        
        # Oblicz przeloty
        try:
            difference = satellite.skyfield_sat - observer
            t0 = ts.now()
            t1 = ts.from_datetime((datetime.utcnow() + timedelta(days=days_ahead)).replace(tzinfo=utc))
            
            # Znajdź zdarzenia (rise/set)
            t, events = satellite.skyfield_sat.find_events(observer, t0, t1, altitude_degrees=min_elevation)
            
            for i, (ti, event) in enumerate(zip(t, events)):
                if event == 0:  # Rise
                    rise_time = ti.utc_datetime()
                    
                    # Znajdź odpowiadający set
                    for j in range(i + 1, len(events)):
                        if events[j] == 2:  # Set
                            set_time = t[j].utc_datetime()
                            
                            # Oblicz maksymalną elewację
                            max_elevation = 0
                            max_time = rise_time
                            max_azimuth = 0
                            
                            # Próbkuj trajektorię
                            dt = (set_time - rise_time).total_seconds()
                            steps = min(10, max(3, int(dt / 60)))
                            
                            for k in range(steps + 1):
                                sample_time = rise_time + timedelta(seconds=dt * k / steps)
                                t_sample = ts.from_datetime(sample_time.replace(tzinfo=utc))
                                topocentric = difference.at(t_sample)
                                alt, az, _ = topocentric.altaz()
                                
                                if alt.degrees > max_elevation:
                                    max_elevation = alt.degrees
                                    max_time = sample_time
                                    max_azimuth = az.degrees
                            
                            if max_elevation >= min_elevation:
                                passes.append({
                                    'satellite': satellite,
                                    'point': point,
                                    'rise_time': rise_time,
                                    'set_time': set_time,
                                    'max_time': max_time,
                                    'max_elevation': max_elevation,
                                    'max_azimuth': max_azimuth,
                                    'duration_min': dt / 60,
                                    'probability': self.calculate_probability(satellite, max_elevation)
                                })
                            break
        except Exception as e:
            logger.error(f"❌ Błąd predykcji {norad_id}: {e}")
        
        return passes
    
    def calculate_probability(self, satellite: Satellite, elevation: float) -> float:
        """Oblicz prawdopodobieństwo obserwacji"""
        base_prob = min(elevation / 90.0, 1.0)
        
        if satellite.type == "observation":
            base_prob *= 0.9
        elif satellite.type == "station":
            base_prob *= 0.7
        
        return round(base_prob, 2)

# ====================== TELEGRAM NOTIFIER ======================
class TelegramNotifier:
    """System powiadomień Telegram"""
    
    def __init__(self, token: str):
        self.token = token
    
    def send_message(self, chat_id: int, text: str, parse_html: bool = True):
        """Wyślij wiadomość"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
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
        url = f"https://api.telegram.org/bot{self.token}/sendLocation"
        payload = {
            "chat_id": chat_id,
            "latitude": lat,
            "longitude": lon
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass
    
    def send_photo(self, chat_id: int, photo_url: str, caption: str = ""):
        """Wyślij zdjęcie"""
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024]
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"❌ Błąd zdjęcia: {e}")

# ====================== GŁÓWNY SYSTEM ======================
class EarthObservationSystem:
    """Główny system obserwacji Ziemi"""
    
    def __init__(self):
        # Inicjalizacja wszystkich modułów
        self.tle_manager = TLEManager()
        self.predictor = PassPredictor(self.tle_manager)
        self.notifier = TelegramNotifier(TOKEN)
        
        # API integracje
        self.usgs = USGSIntegration()
        self.nasa = NASAIntegration(NASA_API_KEY)
        self.mapbox = MapboxVisualizer(MAPBOX_API_KEY) if MAPBOX_API_KEY else None
        self.deepseek = DeepSeekAnalyzer(DEEPSEEK_API_KEY) if DEEPSEEK_API_KEY else None
        self.weather = WeatherIntegration(OPENWEATHER_API_KEY) if OPENWEATHER_API_KEY else None
        
        # Punkty obserwacyjne
        self.observation_points = self.load_points()
        
        # Baza danych
        self.init_database()
        
        # Monitoring w tle
        self.monitoring_active = True
        threading.Thread(target=self.monitoring_loop, daemon=True).start()
        
        logger.info("✅ System obserwacji Ziemi gotowy!")
    
    def load_points(self) -> Dict[str, ObservationPoint]:
        """Załaduj punkty obserwacyjne"""
        points_data = {
            "warszawa_centrum": ("Warszawa Centrum", 52.2297, 21.0122, 100),
            "warszawa_park": ("Park Skaryszewski", 52.2381, 21.0485, 90),
            "warszawa_lazienki": ("Łazienki Królewskie", 52.2155, 21.0355, 95),
            "koszalin": ("Koszalin Wzgórze", 54.1955, 16.1839, 150),
            "krakow": ("Kraków Kopiec", 50.0550, 19.8936, 280),
            "gdansk": ("Gdańsk", 54.3722, 18.6383, 10),
            "wroclaw": ("Wrocław", 51.1079, 17.0385, 120),
            "poznan": ("Poznań", 52.4064, 16.9252, 80)
        }
        
        points = {}
        for name, (full_name, lat, lon, elev) in points_data.items():
            topos = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=elev)
            points[name] = ObservationPoint(full_name, lat, lon, elev, topos)
        
        return points
    
    def init_database(self):
        """Inicjalizuj bazę danych"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Tabela obserwacji
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    satellite_id INTEGER,
                    satellite_name TEXT,
                    point_name TEXT,
                    observation_time TEXT,
                    max_elevation REAL,
                    probability REAL,
                    azimuth REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela trzęsień ziemi
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS earthquakes (
                    id TEXT PRIMARY KEY,
                    place TEXT,
                    magnitude REAL,
                    time TEXT,
                    lat REAL,
                    lon REAL,
                    depth REAL,
                    url TEXT,
                    significance INTEGER,
                    notified BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Baza danych zainicjalizowana")
        except Exception as e:
            logger.error(f"❌ Błąd bazy danych: {e}")
    
    def monitoring_loop(self):
        """Pętla monitorująca w tle"""
        logger.info("🔄 Uruchomiono monitoring w tle")
        
        while self.monitoring_active:
            try:
                # Sprawdź trzęsienia ziemi co 5 minut
                self.check_earthquakes()
                
                # Sprawdź zaplanowane obserwacje
                self.check_scheduled_observations()
                
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"❌ Błąd monitoringu: {e}")
                time.sleep(60)
    
    def check_earthquakes(self):
        """Sprawdź nowe trzęsienia ziemi"""
        try:
            earthquakes = self.usgs.get_significant_earthquakes(min_magnitude=5.0)
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            for quake in earthquakes:
                # Sprawdź czy już mamy w bazie
                cursor.execute("SELECT id FROM earthquakes WHERE id = ?", (quake.id,))
                if not cursor.fetchone():
                    # Zapisz nowe trzęsienie
                    cursor.execute('''
                        INSERT INTO earthquakes 
                        (id, place, magnitude, time, lat, lon, depth, url, significance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        quake.id, quake.place, quake.magnitude,
                        quake.time.isoformat(), quake.lat, quake.lon,
                        quake.depth, quake.url, quake.significance
                    ))
                    
                    # Wyślij alert do zapisanych użytkowników
                    self.send_earthquake_alert(quake)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Błąd sprawdzania trzęsień: {e}")
    
    def send_earthquake_alert(self, quake: Earthquake):
        """Wyślij alert o trzęsieniu ziemi"""
        alert_chats = [123456789]  # Tutaj dodaj chat_id
        
        for chat_id in alert_chats:
            message = f"""
🚨 <b>TRZĘSIENIE ZIEMI!</b>

📍 <b>{quake.place}</b>
⚡ <b>Magnituda: {quake.magnitude}</b>
⏰ {quake.time.strftime('%Y-%m-%d %H:%M:%S UTC')}
📍 {quake.lat:.3f}, {quake.lon:.3f}
📉 Głębokość: {quake.depth:.1f} km

🛰️ <b>SATELLITY NAD EPICENTRUM:</b>
"""
            
            # Znajdź satelity które przelatują nad epicentrum
            temp_point = ObservationPoint(
                f"Epicentrum: {quake.place}",
                quake.lat,
                quake.lon,
                0,
                Topos(latitude_degrees=quake.lat, longitude_degrees=quake.lon)
            )
            
            observation_sats = [s for s in self.tle_manager.satellites.values() 
                              if s.type in ["observation", "station"]]
            
            found = False
            for sat in observation_sats[:3]:
                passes = self.predictor.predict_passes(
                    sat.norad_id, temp_point, days_ahead=2
                )
                
                if passes:
                    best = max(passes, key=lambda x: x['probability'])
                    message += f"\n• {sat.name}: {best['max_time'].strftime('%d.%m %H:%M')} (🎯 {best['probability']*100:.0f}%)"
                    found = True
            
            if not found:
                message += "\n• Brak obserwacji w ciągu 2 dni"
            
            message += f"\n\n🔗 <a href='{quake.url}'>Szczegóły trzęsienia</a>"
            
            self.notifier.send_message(chat_id, message)
            
            # Wyślij lokalizację epicentrum
            self.notifier.send_location(chat_id, quake.lat, quake.lon)
    
    def check_scheduled_observations(self):
        """Sprawdź zaplanowane obserwacje"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Znajdź obserwacje w ciągu najbliższych 24h
            now = datetime.utcnow()
            next_24h = now + timedelta(hours=24)
            
            cursor.execute('''
                SELECT * FROM observations 
                WHERE observation_time BETWEEN ? AND ?
                ORDER BY observation_time
            ''', (now.isoformat(), next_24h.isoformat()))
            
            observations = cursor.fetchall()
            
            for obs in observations:
                obs_time = datetime.fromisoformat(obs[6])  # observation_time
                
                # Powiadomienia: 24h, 1h, 10min przed
                notification_times = [
                    (24, "24 godzin"),
                    (1, "1 godzinę"),
                    (0.167, "10 minut")
                ]
                
                for hours_before, text in notification_times:
                    notification_time = obs_time - timedelta(hours=hours_before)
                    
                    if now <= notification_time <= now + timedelta(minutes=5):
                        self.send_observation_notification(obs, hours_before)
            
            conn.close()
        except Exception as e:
            logger.error(f"❌ Błąd sprawdzania obserwacji: {e}")
    
    def send_observation_notification(self, observation_data, hours_before: int):
        """Wyślij powiadomienie o obserwacji"""
        chat_id = observation_data[1]  # chat_id
        satellite_id = observation_data[2]
        point_name = observation_data[4]
        obs_time = datetime.fromisoformat(observation_data[6])
        
        satellite = self.tle_manager.get_satellite(satellite_id)
        point = self.observation_points.get(point_name)
        
        if not satellite or not point:
            return
        
        # Znajdź aktualne dane przelotu
        passes = self.predictor.predict_passes(satellite_id, point, days_ahead=1)
        current_pass = None
        
        for p in passes:
            if abs((p['max_time'] - obs_time).total_seconds()) < 3600:
                current_pass = p
                break
        
        if not current_pass:
            return
        
        # Pobierz pogodę jeśli API dostępne
        weather_info = ""
        weather_score = 0
        
        if self.weather:
            weather = self.weather.get_current_weather(point.lat, point.lon)
            if weather.get('success', False):
                weather_score = self.weather.calculate_observation_score(weather)
                weather_info = f"""
🌤️ <b>Pogoda:</b> {weather['description']}
🌡️ {weather['temp']:.1f}°C | 💧 {weather['humidity']}%
☁️ {weather['clouds']}% chmur | 💨 {weather['wind_speed']} m/s
📊 <b>Ocena warunków:</b> {weather_score:.1f}/10
"""
        
        # Wygeneruj mapę jeśli API dostępne
        map_url = ""
        if self.mapbox:
            markers = [
                {'lat': point.lat, 'lon': point.lon, 'color': 'ff0000', 'label': 's'}
            ]
            map_url = self.mapbox.generate_satellite_map(point.lat, point.lon, markers)
        
        if hours_before == 24:
            message = f"""
🛰️ <b>PRZYPOMNIENIE OBSERWACYJNE - ZA 24h</b>

📡 <b>{satellite.name}</b> nad <b>{point.name}</b>
⏰ <b>{obs_time.strftime('%Y-%m-%d %H:%M:%S')}</b>
📈 Elewacja: {current_pass['max_elevation']:.1f}°
🧭 Azymut: {current_pass['max_azimuth']:.1f}° ({self.degrees_to_compass(current_pass['max_azimuth'])})
⏱️ Czas obserwacji: {current_pass['duration_min']:.0f} minut
🎯 Prawdopodobieństwo: {current_pass['probability']*100:.0f}%

{weather_info}
"""
            if map_url:
                message += f"\n🗺️ <a href='{map_url}'>Zobacz mapę lokalizacji</a>"
                
        elif hours_before == 1:
            message = f"""
🚀 <b>OBSERWACJA ZA 1 GODZINĘ!</b>

🛰️ <b>{satellite.name}</b> nad {point.name}
⏰ <b>{obs_time.strftime('%H:%M:%S')}</b>

🧭 <b>KIERUNEK:</b> {self.degrees_to_compass(current_pass['max_azimuth'])}
📐 <b>WYSOKOŚĆ:</b> {current_pass['max_elevation']:.1f}° nad horyzontem
⏱️ <b>TRWANIE:</b> {current_pass['duration_min']:.0f} minut

{weather_info if weather_score >= 5 else "⚠️ <b>Uwaga: Złe warunki pogodowe!</b>"}

🎯 <b>INSTRUKCJA:</b>
1. Bądź na miejscu 10 minut przed
2. Ustaw się twarzą w kierunku {self.degrees_to_compass(current_pass['max_azimuth'])}
3. Patrz pod kątem {current_pass['max_elevation']:.1f}° nad horyzontem
4. Satelita będzie widoczny przez {current_pass['duration_min']:.0f} minut
"""
            if map_url:
                self.notifier.send_photo(chat_id, map_url, f"Mapa obserwacji: {satellite.name}")
                
        else:  # 10 minut
            message = f"""
⏰ <b>OBSERWACJA ZA 10 MINUT!</b>

🛰️ <b>{satellite.name}</b> NADLATUJE!

🎯 <b>KIERUNEK:</b> {self.degrees_to_compass(current_pass['max_azimuth'])}
📐 <b>WYSOKOŚĆ:</b> {current_pass['max_elevation']:.1f}°
⏱️ <b>CZAS OBSERWACJI:</b> {current_pass['duration_min']:.0f} minut

🚀 <b>NA MIEJSCE! PATRZ W NIEBO!</b>
"""
        
        self.notifier.send_message(chat_id, message)
        
        if hours_before <= 1:
            self.notifier.send_location(chat_id, point.lat, point.lon)
    
    def degrees_to_compass(self, degrees: float) -> str:
        """Konwertuj stopnie na kierunek kompasu"""
        directions = ["Północ", "Północny-Wschód", "Wschód", "Południowy-Wschód",
                     "Południe", "Południowy-Zachód", "Zachód", "Północny-Zachód"]
        index = round(degrees / 45) % 8
        return directions[index]
    
    def schedule_observation(self, chat_id: int, point_name: str, 
                           satellite_id: int) -> Optional[Dict]:
        """Zaplanuj obserwację"""
        point = self.observation_points.get(point_name)
        if not point:
            return None
        
        passes = self.predictor.predict_passes(satellite_id, point, days_ahead=7)
        
        if not passes:
            return None
        
        # Wybierz najlepszy przelot (najwyższa elewacja)
        best_pass = max(passes, key=lambda x: x['max_elevation'])
        
        # Zapisz w bazie
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO observations 
                (chat_id, satellite_id, satellite_name, point_name, 
                 observation_time, max_elevation, probability, azimuth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chat_id,
                satellite_id,
                best_pass['satellite'].name,
                point_name,
                best_pass['max_time'].isoformat(),
                best_pass['max_elevation'],
                best_pass['probability'],
                best_pass['max_azimuth']
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Zaplanowano obserwację dla chat_id {chat_id}")
            
            # Wyślij potwierdzenie
            confirmation = f"""
✅ <b>OBSERWACJA ZAPLANOWANA!</b>

🛰️ {best_pass['satellite'].name}
📍 {point.name}
⏰ {best_pass['max_time'].strftime('%Y-%m-%d %H:%M:%S')}
📈 {best_pass['max_elevation']:.1f}° | 🎯 {best_pass['probability']*100:.0f}%

🔔 <b>Otrzymasz powiadomienia:</b>
• 24 godzin przed
• 1 godzinę przed
• 10 minut przed
"""
            self.notifier.send_message(chat_id, confirmation)
            
            return best_pass
            
        except Exception as e:
            logger.error(f"❌ Błąd planowania: {e}")
            return None
    
    async def get_full_report(self, point_name: str) -> Dict:
        """Wygeneruj pełny raport obserwacyjny"""
        point = self.observation_points.get(point_name)
        if not point:
            return {"error": "Nieznany punkt"}
        
        report = {
            "point": point.__dict__,
            "timestamp": datetime.now().isoformat(),
            "observations": [],
            "earthquakes": [],
            "weather": None,
            "ai_analysis": None,
            "maps": []
        }
        
        # 1. Obserwacje satelitarne
        observation_sats = [s for s in self.tle_manager.satellites.values() 
                          if s.type in ["observation", "station"]]
        
        for sat in observation_sats[:5]:
            passes = self.predictor.predict_passes(sat.norad_id, point, days_ahead=2)
            if passes:
                best = max(passes, key=lambda x: x['probability'])
                report["observations"].append({
                    "satellite": sat.name,
                    "time": best['max_time'].isoformat(),
                    "elevation": best['max_elevation'],
                    "probability": best['probability'],
                    "duration": best['duration_min']
                })
        
        # 2. Trzęsienia ziemi w pobliżu
        earthquakes = self.usgs.get_recent_earthquakes(min_magnitude=4.0, hours=48)
        nearby_quakes = []
        
        for quake in earthquakes[:5]:
            # Oblicz odległość od punktu
            distance = self.calculate_distance(
                point.lat, point.lon, quake.lat, quake.lon
            )
            
            if distance < 1000:  # 1000 km
                nearby_quakes.append({
                    "place": quake.place,
                    "magnitude": quake.magnitude,
                    "time": quake.time.isoformat(),
                    "distance_km": distance
                })
        
        report["earthquakes"] = nearby_quakes
        
        # 3. Pogoda
        if self.weather:
            weather = self.weather.get_current_weather(point.lat, point.lon)
            if weather.get('success', False):
                report["weather"] = {
                    "temperature": weather['temp'],
                    "conditions": weather['description'],
                    "clouds": weather['clouds'],
                    "score": self.weather.calculate_observation_score(weather)
                }
        
        # 4. Mapy
        if self.mapbox:
            markers = [{'lat': point.lat, 'lon': point.lon, 'color': 'ff0000'}]
            report["maps"].append({
                "type": "location",
                "url": self.mapbox.generate_satellite_map(point.lat, point.lon, markers)
            })
        
        # 5. Analiza AI
        if self.deepseek and report["observations"]:
            best_obs = max(report["observations"], key=lambda x: x['probability'])
            prompt = f"Przeanalizuj obserwację satelity {best_obs['satellite']} nad {point.name} o {best_obs['time']}. Elewacja: {best_obs['elevation']}°. Warunki pogodowe: {report['weather'] if report['weather'] else 'nieznane'}. Oceń jakość obserwacji i daj praktyczne porady."
            report["ai_analysis"] = await self.deepseek.analyze_async(prompt, 500)
        
        return report
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Oblicz odległość między punktami w km"""
        R = 6371
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

# ====================== FLASK APP ======================
app = Flask(__name__)
observation_system = EarthObservationSystem()

@app.route('/')
def home():
    return '''
    <h1>🌍 Earth Observation Platform v6.0</h1>
    <p><b>Zintegrowany system obserwacji Ziemi</b></p>
    <ul>
        <li>🛰️ Śledzenie satelitów (Skyfield)</li>
        <li>🚨 Alerty USGS (trzęsienia ziemi)</li>
        <li>🪐 Dane NASA (asteroidy, APOD)</li>
        <li>🗺️ Mapy Mapbox</li>
        <li>🧠 Analiza AI DeepSeek</li>
        <li>🌤️ Pogoda OpenWeather</li>
    </ul>
    <p>Bot Telegram gotowy do działania!</p>
    '''

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook Telegram"""
    try:
        data = request.get_json()
        
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "").strip().lower()
            
            # Prosta obsługa komend
            if text.startswith("/start"):
                send_message(chat_id, start_message())
            elif text.startswith("/help"):
                send_message(chat_id, help_message())
            elif text.startswith("/points"):
                send_message(chat_id, points_message())
            elif text.startswith("/satellites"):
                send_message(chat_id, satellites_message())
            elif text.startswith("/observe"):
                handle_observe(chat_id, text)
            elif text.startswith("/schedule"):
                handle_schedule(chat_id, text)
            elif text.startswith("/earthquakes"):
                handle_earthquakes(chat_id, text)
            elif text.startswith("/asteroids"):
                handle_asteroids(chat_id)
            elif text.startswith("/apod"):
                handle_apod(chat_id)
            elif text.startswith("/weather"):
                handle_weather(chat_id, text)
            elif text.startswith("/fullreport"):
                asyncio.run(handle_fullreport(chat_id, text))
            else:
                send_message(chat_id, 
                    "🛰️ <b>EARTH OBSERVATION PLATFORM</b>\n\n"
                    "Użyj /help aby zobaczyć dostępne komendy."
                )
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def send_message(chat_id: int, text: str, parse_html: bool = True):
    """Wyślij wiadomość Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML" if parse_html else None,
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")

def start_message() -> str:
    return """
🚀 <b>EARTH OBSERVATION PLATFORM v6.0</b>

🌍 <b>Kompletny system obserwacji Ziemi:</b>
• 🛰️ Śledzenie satelitów
• 🚨 Alerty trzęsień ziemi (USGS)
• 🪐 Przeloty asteroid (NASA)
• 🗺️ Mapy i wizualizacje
• 🧠 Analiza AI
• 🌤️ Warunki pogodowe

📋 <b>Główne komendy:</b>
<code>/points</code> - punkty obserwacyjne
<code>/observe [punkt]</code> - znajdź obserwacje
<code>/schedule [punkt] [id_satelity]</code> - zaplanuj obserwację
<code>/earthquakes</code> - ostatnie trzęsienia ziemi
<code>/fullreport [punkt]</code> - pełny raport z AI

📡 <b>Przykłady:</b>
• <code>/observe warszawa_centrum</code>
• <code>/schedule warszawa_centrum 25544</code> (ISS)
• <code>/fullreport krakow</code>

🚀 <b>Zaczynajmy!</b> <code>/points</code>
"""

def help_message() -> str:
    return """
📋 <b>DOSTĘPNE KOMENDY</b>

<b>🌍 PUNKTY OBSERWACYJNE:</b>
<code>/points</code> - lista punktów

<b>🛰️ OBSERWACJE SATELITARNE:</b>
<code>/observe [punkt]</code> - znajdź przeloty
<code>/schedule [punkt] [id]</code> - zaplanuj obserwację
<code>/satellites</code> - lista satelitów

<b>🚨 ALERTY ZDARZEŃ:</b>
<code>/earthquakes</code> - trzęsienia ziemi
<code>/asteroids</code> - przeloty asteroid
<code>/apod</code> - zdjęcie dnia NASA

<b>🌤️ POGODA I RAPORTY:</b>
<code>/weather [punkt]</code> - aktualna pogoda
<code>/fullreport [punkt]</code> - pełny raport z AI

<b>🛰️ DOSTĘPNE SATELITY:</b>
• 25544 - ISS (stacja kosmiczna)
• 39084 - Landsat 8 (obserwacja Ziemi)
• 40697 - Sentinel-2A (obserwacja)
• 42969 - Sentinel-2B (obserwacja)
• 49260 - Landsat 9 (obserwacja Ziemi)
• 43013 - NOAA-20 (pogoda)
"""

def points_message() -> str:
    points = observation_system.observation_points
    message = "📍 <b>DOSTĘPNE PUNKTY OBSERWACYJNE:</b>\n\n"
    
    for name, point in points.items():
        message += f"• <b>{name}</b>\n"
        message += f"  📍 {point.name}\n"
        message += f"  🌍 {point.lat:.4f}, {point.lon:.4f}\n\n"
    
    message += "🎯 <b>Użyj:</b> <code>/observe [nazwa_punktu]</code>"
    return message

def satellites_message() -> str:
    satellites = observation_system.tle_manager.satellites
    message = "🛰️ <b>DOSTĘPNE SATELITY:</b>\n\n"
    
    for sat_id, sat in satellites.items():
        message += f"• <b>{sat_id}</b> - {sat.name}\n"
        message += f"  📷 {sat.camera} | 📡 {sat.type}\n"
        message += f"  🎯 {sat.resolution_m}m | 🌐 {sat.swath_km}km\n\n"
    
    message += "📅 <b>Użyj:</b> <code>/schedule [punkt] [id_satelity]</code>"
    return message

def handle_observe(chat_id: int, command: str):
    parts = command.split()
    
    if len(parts) < 2:
        send_message(chat_id,
            "❌ <b>Format:</b> <code>/observe [punkt]</code>\n\n"
            "Przykład: <code>/observe warszawa_centrum</code>\n\n"
            "Użyj <code>/points</code> aby zobaczyć punkty."
        )
        return
    
    point_name = parts[1]
    point = observation_system.observation_points.get(point_name)
    
    if not point:
        send_message(chat_id, "❌ Nieznany punkt obserwacyjny")
        return
    
    send_message(chat_id, "🔍 Szukam obserwacji... Proszę czekać.")
    
    # Znajdź obserwacje
    message = f"📡 <b>OBSERWACJE DLA {point.name.upper()}</b>\n\n"
    
    observation_sats = [s for s in observation_system.tle_manager.satellites.values() 
                      if s.type in ["observation", "station"]]
    
    found = False
    
    for sat in observation_sats[:6]:
        passes = observation_system.predictor.predict_passes(
            sat.norad_id, point, days_ahead=2
        )
        
        if passes:
            best = max(passes, key=lambda x: x['probability'])
            
            message += f"🛰️ <b>{sat.name}</b>\n"
            message += f"   📅 {best['max_time'].strftime('%d.%m %H:%M')}\n"
            message += f"   📈 {best['max_elevation']:.0f}° | 🎯 {best['probability']*100:.0f}%\n"
            message += f"   ⏱️ {best['duration_min']:.0f} min\n"
            message += f"   📷 {sat.camera}\n\n"
            
            found = True
    
    if not found:
        message += "😔 Brak obserwacji w najbliższych 2 dniach.\n"
        message += "Spróbuj później lub wybierz inny punkt."
    
    send_message(chat_id, message)

def handle_schedule(chat_id: int, command: str):
    parts = command.split()
    
    if len(parts) < 3:
        send_message(chat_id,
            "❌ <b>Format:</b> <code>/schedule [punkt] [id_satelity]</code>\n\n"
            "Przykład: <code>/schedule warszawa_centrum 25544</code>\n\n"
            "Użyj <code>/satellites</code> aby zobaczyć dostępne satelity."
        )
        return
    
    point_name = parts[1]
    
    try:
        satellite_id = int(parts[2])
    except ValueError:
        send_message(chat_id, "❌ Nieprawidłowy ID satelity")
        return
    
    # Zaplanuj obserwację
    observation = observation_system.schedule_observation(chat_id, point_name, satellite_id)
    
    if not observation:
        send_message(chat_id,
            "❌ <b>BRAK OBSERWACJI</b>\n\n"
            "Satelita nie przelatuje nad tym punktem w najbliższych 7 dniach."
        )

def handle_earthquakes(chat_id: int, command: str):
    parts = command.split()
    
    min_magnitude = 4.0
    hours = 24
    
    if len(parts) >= 2:
        try:
            min_magnitude = float(parts[1])
        except:
            pass
    
    if len(parts) >= 3:
        try:
            hours = int(parts[2])
        except:
            pass
    
    send_message(chat_id, f"🌋 Pobieram trzęsienia ziemi (> {min_magnitude}M) z {hours}h...")
    
    earthquakes = observation_system.usgs.get_recent_earthquakes(min_magnitude, hours)
    
    if not earthquakes:
        send_message(chat_id, f"🌍 Brak trzęsień ziemi > {min_magnitude}M w ostatnich {hours}h.")
        return
    
    message = f"🌋 <b>TRZĘSIENIA ZIEMI (>{min_magnitude}M, {hours}h):</b>\n\n"
    
    for i, quake in enumerate(earthquakes[:5], 1):
        time_ago = datetime.utcnow() - quake.time
        hours_ago = time_ago.total_seconds() / 3600
        
        message += f"{i}. <b>{quake.place}</b>\n"
        message += f"   ⚡ <b>{quake.magnitude}M</b> | 📉 {quake.depth:.1f} km\n"
        message += f"   ⏰ {hours_ago:.1f}h temu\n"
        message += f"   🌍 {quake.lat:.3f}, {quake.lon:.3f}\n\n"
    
    if len(earthquakes) > 5:
        message += f"... i {len(earthquakes) - 5} więcej\n"
    
    message += f"🔗 <a href='https://earthquake.usgs.gov/earthquakes/map/'>Mapa trzęsień</a>"
    
    send_message(chat_id, message)

def handle_asteroids(chat_id: int):
    send_message(chat_id, "🪐 Pobieram dane o asteroidach...")
    
    asteroids = observation_system.nasa.get_asteroids()
    
    if not asteroids:
        send_message(chat_id, "🌍 Brak bliskich przelotów asteroid w ciągu 7 dni.")
        return
    
    message = "🪐 <b>BLISKIE PRZELOTY ASTEROID (7 dni):</b>\n\n"
    
    for i, asteroid in enumerate(asteroids[:5], 1):
        distance_mln_km = asteroid['miss_distance_km'] / 1000000
        
        message += f"{i}. <b>{asteroid['name']}</b>\n"
        message += f"   📏 {asteroid['diameter_min']:.2f}-{asteroid['diameter_max']:.2f} km\n"
        message += f"   🎯 {distance_mln_km:.2f} mln km\n"
        message += f"   🚀 {asteroid['velocity_kps']:.2f} km/s\n"
        message += f"   ⏰ {asteroid['approach_time']}\n"
        message += f"   ⚠️ <b>{'NIEBEZPIECZNA' if asteroid['hazardous'] else 'Bezpieczna'}</b>\n\n"
    
    if len(asteroids) > 5:
        message += f"... i {len(asteroids) - 5} więcej"
    
    send_message(chat_id, message)

def handle_apod(chat_id: int):
    apod = observation_system.nasa.get_apod()
    
    if not apod or 'url' not in apod:
        send_message(chat_id, "❌ Nie udało się pobrać APOD")
        return
    
    message = f"""
🪐 <b>ASTRONOMY PICTURE OF THE DAY</b>

📅 <b>{apod.get('date', 'Dzisiaj')}</b>
🏷️ <b>{apod.get('title', 'Brak tytułu')}</b>

📖 {apod.get('explanation', 'Brak opisu')[:300]}...

👨‍🎨 <b>Autor:</b> {apod.get('copyright', 'Nieznany')}

<a href="{apod['url']}">🔗 Zobacz pełne zdjęcie</a>
"""
    
    send_message(chat_id, message)

def handle_weather(chat_id: int, command: str):
    parts = command.split()
    
    if len(parts) < 2:
        send_message(chat_id,
            "❌ <b>Format:</b> <code>/weather [punkt]</code>\n\n"
            "Przykład: <code>/weather warszawa_centrum</code>"
        )
        return
    
    point_name = parts[1]
    point = observation_system.observation_points.get(point_name)
    
    if not point:
        send_message(chat_id, "❌ Nieznany punkt")
        return
    
    if not observation_system.weather:
        send_message(chat_id, "❌ Brak klucza OpenWeather API")
        return
    
    send_message(chat_id, "🌤️ Pobieram dane pogodowe...")
    
    weather = observation_system.weather.get_current_weather(point.lat, point.lon)
    
    if not weather.get('success', False):
        send_message(chat_id, "❌ Nie udało się pobrać pogody")
        return
    
    score = observation_system.weather.calculate_observation_score(weather)
    
    message = f"""
🌤️ <b>POGODA DLA {point.name.upper()}</b>

🌡️ <b>Temperatura:</b> {weather['temp']:.1f}°C
🤏 <b>Odczuwalna:</b> {weather['feels_like']:.1f}°C
💧 <b>Wilgotność:</b> {weather['humidity']}%
☁️ <b>Zachmurzenie:</b> {weather['clouds']}%
👁️ <b>Widoczność:</b> {weather['visibility']:.1f} km
💨 <b>Wiatr:</b> {weather['wind_speed']} m/s
📖 <b>Opis:</b> {weather['description']}

📊 <b>OCENA WARUNKÓW OBSERWACYJNYCH:</b>
<b>{score:.1f}/10</b>

{"✅ <b>Doskonale warunki!</b>" if score >= 8 else ""}
{"⚠️ <b>Warunki średnie</b>" if 5 <= score < 8 else ""}
{"❌ <b>Złe warunki do obserwacji</b>" if score < 5 else ""}
"""
    
    send_message(chat_id, message)

async def handle_fullreport(chat_id: int, command: str):
    parts = command.split()
    
    if len(parts) < 2:
        send_message(chat_id,
            "❌ <b>Format:</b> <code>/fullreport [punkt]</code>\n\n"
            "Przykład: <code>/fullreport warszawa_centrum</code>"
        )
        return
    
    point_name = parts[1]
    
    send_message(chat_id, 
        "📊 Generuję pełny raport...\n"
        "Pobieram dane z wszystkich API...\n"
        "To może potrwać do 30 sekund."
    )
    
    try:
        report = await observation_system.get_full_report(point_name)
        
        if "error" in report:
            send_message(chat_id, f"❌ {report['error']}")
            return
        
        message = f"""
📊 <b>PEŁNY RAPORT OBSERWACYJNY</b>
📍 <b>{point_name.upper()}</b>
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}

<b>NAJLEPSZE OBSERWACJE:</b>
"""
        
        for i, obs in enumerate(report["observations"][:3], 1):
            message += f"\n{i}. 🛰️ <b>{obs['satellite']}</b>\n"
            message += f"   ⏰ {datetime.fromisoformat(obs['time']).strftime('%d.%m %H:%M')}\n"
            message += f"   📈 {obs['elevation']:.0f}° | 🎯 {obs['probability']*100:.0f}%\n"
        
        if report["earthquakes"]:
            message += "\n<b>🚨 TRZĘSIENIA ZIEMI W POBLIŻU:</b>\n"
            for quake in report["earthquakes"][:2]:
                message += f"\n📍 {quake['place']}\n"
                message += f"   ⚡ {quake['magnitude']}M | 📏 {quake['distance_km']:.0f} km\n"
        
        if report["weather"]:
            message += f"\n<b>🌤️ POGODA:</b>\n"
            message += f"🌡️ {report['weather']['temperature']:.1f}°C\n"
            message += f"☁️ {report['weather']['clouds']}% chmur\n"
            message += f"📊 Ocena: {report['weather']['score']:.1f}/10\n"
        
        if report["ai_analysis"]:
            message += f"\n<b>🧠 ANALIZA AI:</b>\n"
            message += f"{report['ai_analysis'][:300]}...\n"
        
        if report["maps"]:
            message += f"\n🗺️ <a href='{report['maps'][0]['url']}'>Zobacz mapę lokalizacji</a>"
        
        send_message(chat_id, message)
        
    except Exception as e:
        logger.error(f"❌ Błąd pełnego raportu: {e}")
        send_message(chat_id, f"❌ Błąd generowania raportu: {str(e)}")

# ====================== RUN ======================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 URUCHAMIANIE EARTH OBSERVATION PLATFORM v6.0")
    print("=" * 80)
    
    print(f"✅ Skyfield: gotowy")
    print(f"✅ USGS: gotowy")
    print(f"✅ NASA: {'gotowy' if NASA_API_KEY else 'brak klucza'}")
    print(f"✅ Mapbox: {'gotowy' if MAPBOX_API_KEY else 'brak klucza'}")
    print(f"✅ DeepSeek: {'gotowy' if DEEPSEEK_API_KEY else 'brak klucza'}")
    print(f"✅ OpenWeather: {'gotowy' if OPENWEATHER_API_KEY else 'brak klucza'}")
    print(f"✅ Telegram Bot: gotowy")
    print("=" * 80)
    
    # Uruchom webhook
    try:
        # Ustaw webhook
        webhook_url = f"{RENDER_URL}/webhook"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", 
                     json={"url": webhook_url})
        print(f"🌐 Webhook ustawiony: {webhook_url}")
    except:
        print("⚠️ Nie udało się ustawić webhooka (może być już ustawiony)")
    
    print("🤖 SYSTEM OBSERWACJI ZIEMI GOTOWY!")
    print("=" * 80)
    
    app.run(host="0.0.0.0", port=PORT, debug=False)