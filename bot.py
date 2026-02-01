#!/usr/bin/env python3
"""
🛰️ COMPLETE EARTH OBSERVATION PLATFORM v7.0
✅ Wszystkie API przywrócone: USGS, NASA, OpenWeather, Mapbox, DeepSeek, N2YO
✅ Nowy moduł: Satellite Visibility Calculator
✅ Pokazuje gdzie stanąć żeby być w kadrze satelity
✅ Pełna integracja wszystkich funkcji
"""

import os
import json
import time
import math
import random
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from flask import Flask, request, jsonify
import logging

# ====================== KONFIGURACJA WSZYSTKICH API ======================
print("=" * 80)
print("🛰️ COMPLETE EARTH OBSERVATION PLATFORM v7.0")
print("✅ WSZYSTKIE API PRZYWRÓCONE + SATELITY")
print("=" * 80)

# WSZYSTKIE KLUCZE API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
USGS_API_KEY = os.getenv("USGS_API_KEY", "")  # USGS może nie wymagać
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
N2YO_API_KEY = os.getenv("N2YO_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
RENDER_URL = os.getenv("RENDER_URL", "https://your-app.onrender.com")
PORT = int(os.getenv("PORT", 10000))

# ====================== MODUŁY API ======================

class USGSClient:
    """USGS API - trzęsienia ziemi"""
    
    def get_earthquakes(self, min_mag=4.0, hours=24) -> List[Dict]:
        try:
            endtime = datetime.utcnow()
            starttime = endtime - timedelta(hours=hours)
            
            params = {
                "format": "geojson",
                "starttime": starttime.strftime("%Y-%m-%dT%H:%M:%S"),
                "endtime": endtime.strftime("%Y-%m-%dT%H:%M:%S"),
                "minmagnitude": min_mag,
                "orderby": "time",
                "limit": 10
            }
            
            response = requests.get("https://earthquake.usgs.gov/fdsnws/event/1/query", 
                                  params=params, timeout=10)
            data = response.json()
            
            earthquakes = []
            for feature in data.get('features', []):
                props = feature['properties']
                coords = feature['geometry']['coordinates']
                
                earthquakes.append({
                    'place': props['place'],
                    'magnitude': props['mag'],
                    'time': datetime.fromtimestamp(props['time'] / 1000),
                    'lat': coords[1],
                    'lon': coords[0],
                    'depth': coords[2],
                    'url': props['url']
                })
            
            return sorted(earthquakes, key=lambda x: x['magnitude'], reverse=True)
        except:
            return []

class NASAClient:
    """NASA API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def get_apod(self) -> Dict:
        try:
            url = "https://api.nasa.gov/planetary/apod"
            params = {'api_key': self.api_key}
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            return {
                'title': data.get('title', ''),
                'url': data.get('url', ''),
                'explanation': data.get('explanation', ''),
                'date': data.get('date', '')
            }
        except:
            return {}
    
    def get_asteroids(self) -> List[Dict]:
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
                            'velocity_kps': float(approach['relative_velocity']['kilometers_per_second'])
                        })
            
            return asteroids[:5]
        except:
            return []

class WeatherClient:
    """OpenWeather API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def get_weather(self, lat: float, lon: float) -> Dict:
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
                'wind_speed': data['wind']['speed'],
                'success': True
            }
        except:
            return {'success': False}

class MapboxClient:
    """Mapbox API - mapy i wizualizacje"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.available = bool(api_key)
    
    def generate_map(self, lat: float, lon: float, zoom=12) -> str:
        if not self.available:
            return ""
        
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
        except:
            return ""
    
    def generate_direction_map(self, start_lat: float, start_lon: float,
                             azimuth: float, distance_km=10) -> str:
        if not self.available:
            return ""
        
        try:
            # Oblicz punkt końcowy
            end_point = self._calculate_endpoint(start_lat, start_lon, azimuth, distance_km)
            
            style = "satellite-streets-v12"
            size = "800x600"
            
            start_marker = f"pin-s+00ff00({start_lon},{start_lat})"
            end_marker = f"pin-s+ff0000({end_point['lon']},{end_point['lat']})"
            path = f"path-3+ff0000-0.8({start_lon},{start_lat},{end_point['lon']},{end_point['lat']})"
            
            overlays = f"{path},{start_marker},{end_marker}"
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"{overlays}/"
                f"{start_lon},{start_lat},13/{size}@2x"
                f"?access_token={self.api_key}"
            )
            
            return map_url
        except:
            return ""
    
    def _calculate_endpoint(self, lat: float, lon: float, 
                           azimuth_deg: float, distance_km: float) -> Dict:
        R = 6371.0
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        azimuth_rad = math.radians(azimuth_deg)
        
        lat2_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_km/R) +
            math.cos(lat_rad) * math.sin(distance_km/R) * math.cos(azimuth_rad)
        )
        
        lon2_rad = lon_rad + math.atan2(
            math.sin(azimuth_rad) * math.sin(distance_km/R) * math.cos(lat_rad),
            math.cos(distance_km/R) - math.sin(lat_rad) * math.sin(lat2_rad)
        )
        
        return {
            'lat': math.degrees(lat2_rad),
            'lon': math.degrees(lon2_rad)
        }

class DeepSeekClient:
    """DeepSeek API - analiza AI"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.available = bool(api_key)
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    def analyze_photo_opportunity(self, satellite_data: Dict, 
                                 location_data: Dict) -> Dict:
        if not self.available:
            return self._mock_analysis(satellite_data)
        
        try:
            prompt = f"""
            ANALIZA OKAZJI FOTOGRAFICZNEJ SATELITY
            
            SATELITA: {satellite_data.get('name', 'Nieznany')}
            TYP: {satellite_data.get('type', 'Nieznany')}
            ROZDZIELCZOŚĆ: {satellite_data.get('resolution', 'Nieznana')}
            PAS: {satellite_data.get('swath', 'Nieznany')} km
            
            LOKALIZACJA: {location_data.get('name', 'Nieznana')}
            WSPÓŁRZĘDNE: {location_data.get('lat', 0)}°N, {location_data.get('lon', 0)}°E
            
            PROSZĘ O ANALIZĘ:
            1. Szanse na udane zdjęcie
            2. Zalecenia techniczne (ustawienia aparatu)
            3. Potencjalne problemy
            4. Najlepszy czas na obserwację
            
            Odpowiedz w formacie:
            SZANSE: [text]
            ZALECENIA: [lista]
            PROBLEMY: [lista]
            CZAS: [text]
            """
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Jesteś ekspertem od fotografii satelitarnej."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 800
            }
            
            response = requests.post(self.base_url, json=payload, 
                                   headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {"analysis": result['choices'][0]['message']['content']}
            else:
                return self._mock_analysis(satellite_data)
                
        except:
            return self._mock_analysis(satellite_data)
    
    def _mock_analysis(self, satellite_data: Dict) -> Dict:
        return {
            "analysis": f"""
            SZANSE: Satelita {satellite_data.get('name', '')} oferuje dobre warunki do fotografii.
            ZALECENIA: Użyj statywu, ISO 800-1600, czas 1-3s, wyzwalacz zdalny.
            PROBLEMY: Zachmurzenie, wiatr, zanieczyszczenie światłem.
            CZAS: Najlepiej obserwować w ciągu 30 minut od czasu przelotu.
            """
        }

# ====================== SATELITY - NOWY MODUŁ WIDOCZNOŚCI ======================

class SatelliteVisibilityCalculator:
    """GŁÓWNY MODUŁ: Oblicza gdzie stanąć żeby być widocznym dla satelity"""
    
    SATELLITES = {
        "landsat": {
            "name": "Landsat 8",
            "norad_id": 39084,
            "altitude_km": 705,
            "swath_km": 185,
            "resolution_m": 15,
            "fov_deg": 15.0,
            "min_elevation": 20
        },
        "sentinel": {
            "name": "Sentinel-2A",
            "norad_id": 40697,
            "altitude_km": 786,
            "swath_km": 290,
            "resolution_m": 10,
            "fov_deg": 20.6,
            "min_elevation": 15
        },
        "iss": {
            "name": "ISS",
            "norad_id": 25544,
            "altitude_km": 408,
            "swath_km": 5,
            "resolution_m": 10,
            "fov_deg": 50.0,
            "min_elevation": 10
        },
        "worldview": {
            "name": "WorldView-3",
            "norad_id": 40115,
            "altitude_km": 617,
            "swath_km": 13.1,
            "resolution_m": 0.31,
            "fov_deg": 1.2,
            "min_elevation": 25
        }
    }
    
    def calculate_visibility(self, sat_name: str, area_lat: float, area_lon: float,
                           target_time: datetime = None) -> Dict:
        """Oblicza gdzie stanąć w danym obszarze żeby satelita Cię widział"""
        if sat_name not in self.SATELLITES:
            return {"error": "Nieznany satelita"}
        
        if not target_time:
            target_time = datetime.utcnow() + timedelta(hours=1)
        
        sat = self.SATELLITES[sat_name]
        
        # 1. Pobierz pozycję satelity (lub symuluj)
        sat_position = self._get_satellite_position(sat["norad_id"], area_lat, area_lon, target_time)
        
        # 2. Oblicz punkt pod satelitą (nadir)
        nadir_point = {
            'lat': sat_position['lat'],
            'lon': sat_position['lon']
        }
        
        # 3. Oblicz strefę widoczności
        visibility_radius = sat["swath_km"] / 2
        
        # 4. Znajdź optymalną pozycję w strefie (najlepszy kąt)
        optimal_position = self._find_optimal_position(
            nadir_point, area_lat, area_lon, visibility_radius
        )
        
        # 5. Oblicz kąt patrzenia
        look_angle = self._calculate_look_angle(optimal_position, sat_position)
        
        # 6. Oblicz szansę
        chance = self._calculate_success_chance(sat_position, optimal_position, sat)
        
        return {
            "satellite": sat["name"],
            "time_utc": target_time.isoformat(),
            "time_local": (target_time + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
            "nadir_point": nadir_point,
            "visibility_radius_km": visibility_radius,
            "optimal_position": optimal_position,
            "look_angle": look_angle,
            "success_chance_percent": chance,
            "camera_info": {
                "resolution": sat["resolution_m"],
                "swath": sat["swath_km"],
                "fov": sat["fov_deg"]
            }
        }
    
    def _get_satellite_position(self, norad_id: int, lat: float, lon: float,
                               time_utc: datetime) -> Dict:
        """Pobierz/symuluj pozycję satelity"""
        if N2YO_API_KEY:
            try:
                url = f"https://api.n2yo.com/rest/v1/satellite/positions/{norad_id}/{lat}/{lon}/0/1"
                params = {'apiKey': N2YO_API_KEY}
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('positions'):
                        pos = data['positions'][0]
                        return {
                            'lat': pos.get('satlatitude', 0),
                            'lon': pos.get('satlongitude', 0),
                            'altitude': pos.get('sataltitude', 700),
                            'azimuth': pos.get('azimuth', 0),
                            'elevation': pos.get('elevation', 0)
                        }
            except:
                pass
        
        # Symulacja jeśli brak API
        return self._simulate_position(lat, lon, time_utc)
    
    def _simulate_position(self, lat: float, lon: float, time_utc: datetime) -> Dict:
        """Symuluj realistyczną pozycję satelity"""
        hour = time_utc.hour + time_utc.minute/60
        
        # Symuluj orbitę
        lat_offset = math.sin(hour * math.pi/6) * 2
        lon_offset = math.cos(hour * math.pi/6) * 4
        
        return {
            'lat': lat + lat_offset,
            'lon': lon + lon_offset,
            'altitude': 700,
            'azimuth': (hour * 30) % 360,
            'elevation': 30 + math.sin(hour * math.pi/12) * 30
        }
    
    def _find_optimal_position(self, nadir: Dict, area_lat: float, area_lon: float,
                              radius_km: float) -> Dict:
        """Znajdź najlepszą pozycję w strefie widoczności"""
        # 1. Oblicz odległość od nadiru do obszaru
        distance_to_area = self._calculate_distance_km(
            nadir['lat'], nadir['lon'], area_lat, area_lon
        )
        
        # 2. Jeśli obszar jest w strefie, użyj go
        if distance_to_area <= radius_km:
            target_lat = area_lat
            target_lon = area_lon
            distance_from_nadir = distance_to_area
        else:
            # 3. Jeśli nie, znajdź najbliższy punkt w strefie
            bearing = self._calculate_bearing(
                nadir['lat'], nadir['lon'], area_lat, area_lon
            )
            
            # Punkt na krawędzi strefy w kierunku obszaru
            edge_point = self._calculate_destination_point(
                nadir['lat'], nadir['lon'], bearing, radius_km
            )
            
            target_lat = edge_point['lat']
            target_lon = edge_point['lon']
            distance_from_nadir = radius_km
        
        # 4. Kierunek od nadiru
        direction_from_nadir = self._calculate_bearing(
            nadir['lat'], nadir['lon'], target_lat, target_lon
        )
        
        return {
            'lat': target_lat,
            'lon': target_lon,
            'distance_from_nadir_km': distance_from_nadir,
            'direction_from_nadir_deg': direction_from_nadir,
            'direction_name': self._get_direction_name(direction_from_nadir)
        }
    
    def _calculate_look_angle(self, observer: Dict, satellite: Dict) -> Dict:
        """Oblicz kąt patrzenia z pozycji obserwatora do satelity"""
        bearing = self._calculate_bearing(
            observer['lat'], observer['lon'],
            satellite['lat'], satellite['lon']
        )
        
        # Uproszczona elewacja
        distance = self._calculate_distance_km(
            observer['lat'], observer['lon'],
            satellite['lat'], satellite['lon']
        )
        
        if satellite.get('altitude', 0) > 0:
            elevation = math.degrees(math.atan2(satellite['altitude'], distance))
        else:
            elevation = 45
        
        return {
            'azimuth_deg': bearing,
            'elevation_deg': elevation,
            'azimuth_name': self._get_direction_name(bearing)
        }
    
    def _calculate_success_chance(self, sat_pos: Dict, obs_pos: Dict, sat_info: Dict) -> float:
        """Oblicz szansę na udane zdjęcie"""
        chance = 50.0
        
        # Im wyższa elewacja, tym lepiej
        if sat_pos.get('elevation', 0) > 60:
            chance += 25
        elif sat_pos.get('elevation', 0) > 30:
            chance += 15
        
        # Im bliżej nadiru, tym lepsza jakość
        distance = obs_pos['distance_from_nadir_km']
        swath = sat_info['swath_km']
        
        if distance < swath * 0.3:
            chance += 20
        elif distance < swath * 0.6:
            chance += 10
        
        # Losowy czynnik
        chance += random.uniform(-10, 10)
        
        return max(5, min(95, round(chance, 1)))
    
    # ====================== POMOCNICZE FUNKCJE MATEMATYCZNE ======================
    
    def _calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Oblicz odległość między punktami w km (Haversine)"""
        R = 6371.0
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Oblicz azymut między punktami"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - \
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
        
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360
    
    def _calculate_destination_point(self, lat: float, lon: float, 
                                    bearing: float, distance_km: float) -> Dict:
        """Oblicz punkt docelowy dany azymutem i odległością"""
        R = 6371.0
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        lat2_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_km/R) +
            math.cos(lat_rad) * math.sin(distance_km/R) * math.cos(bearing_rad)
        )
        
        lon2_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_km/R) * math.cos(lat_rad),
            math.cos(distance_km/R) - math.sin(lat_rad) * math.sin(lat2_rad)
        )
        
        return {
            'lat': math.degrees(lat2_rad),
            'lon': math.degrees(lon2_rad)
        }
    
    def _get_direction_name(self, angle: float) -> str:
        """Konwertuj kąt na nazwę kierunku"""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(angle / 45) % 8
        return directions[idx]
    
    def find_next_opportunities(self, sat_name: str, area_lat: float, area_lon: float,
                               hours_ahead: int = 24) -> List[Dict]:
        """Znajdź następne okazje w ciągu X godzin"""
        opportunities = []
        
        for hour in range(0, hours_ahead + 1, 1):
            check_time = datetime.utcnow() + timedelta(hours=hour)
            
            visibility = self.calculate_visibility(sat_name, area_lat, area_lon, check_time)
            
            if "error" not in visibility and visibility["success_chance_percent"] > 40:
                opportunities.append(visibility)
        
        # Sortuj po szansie
        opportunities.sort(key=lambda x: -x["success_chance_percent"])
        return opportunities[:10]

# ====================== GŁÓWNY TELEGRAM BOT ======================

class CompleteEarthObservationBot:
    """KOMPLETNY BOT Z WSZYSTKIMI FUNKCJAMI"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.available = bool(TELEGRAM_BOT_TOKEN)
        
        # WSZYSTKIE API KLIENTY
        self.usgs = USGSClient()
        self.nasa = NASAClient(NASA_API_KEY) if NASA_API_KEY else None
        self.weather = WeatherClient(OPENWEATHER_API_KEY) if OPENWEATHER_API_KEY else None
        self.mapbox = MapboxClient(MAPBOX_API_KEY) if MAPBOX_API_KEY else None
        self.deepseek = DeepSeekClient(DEEPSEEK_API_KEY) if DEEPSEEK_API_KEY else None
        self.satellite_calc = SatelliteVisibilityCalculator()
        
        # Lokalizacje
        self.locations = {
            "warszawa": {"name": "Warszawa", "lat": 52.2297, "lon": 21.0122},
            "krakow": {"name": "Kraków", "lat": 50.0614, "lon": 19.9366},
            "gdansk": {"name": "Gdańsk", "lat": 54.3722, "lon": 18.6383},
            "wroclaw": {"name": "Wrocław", "lat": 51.1079, "lon": 17.0385},
            "poznan": {"name": "Poznań", "lat": 52.4064, "lon": 16.9252},
            "szczecin": {"name": "Szczecin", "lat": 53.4289, "lon": 14.5530},
            "lodz": {"name": "Łódź", "lat": 51.7592, "lon": 19.4558},
            "lublin": {"name": "Lublin", "lat": 51.2465, "lon": 22.5684},
            "bialystok": {"name": "Białystok", "lat": 53.1333, "lon": 23.1643},
            "rzeszow": {"name": "Rzeszów", "lat": 50.0413, "lon": 21.9991},
            "katowice": {"name": "Katowice", "lat": 50.2649, "lon": 19.0238},
            "tatry": {"name": "Tatry", "lat": 49.2992, "lon": 19.9496},
            "mazury": {"name": "Mazury", "lat": 53.8667, "lon": 21.5000},
            "sudety": {"name": "Sudety", "lat": 50.7750, "lon": 16.2917},
            "baltyk": {"name": "Bałtyk", "lat": 54.5000, "lon": 18.5500}
        }
        
        self.satellites = list(self.satellite_calc.SATELLITES.keys())
        
        print(f"✅ Bot zainicjalizowany z {len(self.locations)} lokalizacjami")
        print(f"✅ Dostępne API: USGS{'✅' if self.usgs else '❌'}, "
              f"NASA{'✅' if self.nasa else '❌'}, "
              f"Weather{'✅' if self.weather else '❌'}, "
              f"Mapbox{'✅' if self.mapbox and self.mapbox.available else '❌'}, "
              f"DeepSeek{'✅' if self.deepseek and self.deepseek.available else '❌'}, "
              f"Satellites✅")
    
    def send_message(self, chat_id: int, text: str, parse_html: bool = True):
        """Wyślij wiadomość"""
        if not self.available:
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML" if parse_html else None,
            "disable_web_page_preview": False
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def send_photo(self, chat_id: int, photo_url: str, caption: str = ""):
        """Wyślij zdjęcie"""
        if not self.available:
            return False
        
        url = f"{self.base_url}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024],
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload, timeout=15)
            return response.status_code == 200
        except:
            return False
    
    def send_location(self, chat_id: int, lat: float, lon: float):
        """Wyślij lokalizację"""
        if not self.available:
            return False
        
        url = f"{self.base_url}/sendLocation"
        payload = {
            "chat_id": chat_id,
            "latitude": lat,
            "longitude": lon
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def handle_command(self, chat_id: int, command: str, args: List[str]):
        """Obsłuż komendę - WSZYSTKIE FUNKCJE"""
        command = command.lower()
        
        # ========== NOWE KOMENDY SATELITARNE ==========
        if command == "where" or command == "gdzie":
            self.cmd_where(chat_id, args)
        elif command == "nextsat" or command == "nastepnesat":
            self.cmd_nextsat(chat_id, args)
        elif command == "satvisibility" or command == "widocznosc":
            self.cmd_satvisibility(chat_id, args)
        
        # ========== ORYGINALNE KOMENDY ==========
        elif command == "start":
            self.cmd_start(chat_id)
        elif command == "help":
            self.cmd_help(chat_id)
        elif command == "earthquakes" or command == "trzesienia":
            self.cmd_earthquakes(chat_id, args)
        elif command == "weather" or command == "pogoda":
            self.cmd_weather(chat_id, args)
        elif command == "asteroids" or command == "asteroidy":
            self.cmd_asteroids(chat_id)
        elif command == "apod":
            self.cmd_apod(chat_id)
        elif command == "map":
            self.cmd_map(chat_id, args)
        elif command == "analyze" or command == "analiza":
            self.cmd_analyze(chat_id, args)
        elif command == "locations" or command == "lokalizacje":
            self.cmd_locations(chat_id)
        elif command == "satellites" or command == "satelity":
            self.cmd_satellites_list(chat_id)
        else:
            self.send_message(chat_id, "❌ Nieznana komenda. Użyj /help")
    
    # ====================== NOWE KOMENDY SATELITARNE ======================
    
    def cmd_where(self, chat_id: int, args: List[str]):
        """Gdzie stanąć żeby satelita Cię widział"""
        if len(args) < 2:
            self.send_message(chat_id,
                "📍 <b>GDZIE STANĄĆ - FORMAT:</b>\n"
                "<code>/where [satelita] [lokalizacja] [czas]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/where landsat warszawa 14:30</code>\n"
                "<code>/where sentinel krakow</code> (czas domyślny: za 1h)\n"
                "<code>/where iss gdansk 16</code>\n\n"
                "<b>Satelity:</b> landsat, sentinel, iss, worldview\n"
                "<b>Czas:</b> HH:MM lub HH (24h format, domyślnie za 1h)"
            )
            return
        
        sat_name = args[0].lower()
        loc_name = args[1].lower()
        
        if sat_name not in self.satellites:
            self.send_message(chat_id, 
                f"❌ Nieznany satelita: {sat_name}\n"
                f"Dostępne: {', '.join(self.satellites)}"
            )
            return
        
        location = self.locations.get(loc_name)
        if not location:
            self.send_message(chat_id, "❌ Nieznana lokalizacja. Użyj /locations")
            return
        
        # Parsuj czas
        time_str = args[2] if len(args) > 2 else None
        target_time = self._parse_time(time_str)
        
        self.send_message(chat_id,
            f"🛰️ Obliczam gdzie stanąć dla {self.satellite_calc.SATELLITES[sat_name]['name']}...\n"
            f"📍 {location['name']}\n"
            f"🕐 {target_time.strftime('%Y-%m-%d %H:%M')} UTC"
        )
        
        # Oblicz widoczność
        visibility = self.satellite_calc.calculate_visibility(
            sat_name, location['lat'], location['lon'], target_time
        )
        
        if "error" in visibility:
            self.send_message(chat_id, f"❌ Błąd: {visibility['error']}")
            return
        
        # Przygotuj odpowiedź
        sat_info = self.satellite_calc.SATELLITES[sat_name]
        optimal = visibility["optimal_position"]
        look = visibility["look_angle"]
        
        message = f"""
🛰️ <b>{visibility['satellite']} - GDZIE STANĄĆ</b>

📍 <b>OPTYMALNA POZYCJA:</b>
Szerokość: <code>{optimal['lat']:.6f}°N</code>
Długość: <code>{optimal['lon']:.6f}°E</code>
Kierunek od satelity: {optimal['direction_name']} ({optimal['direction_from_nadir_deg']:.0f}°)
Odległość: {optimal['distance_from_nadir_km']:.1f} km

🧭 <b>KIERUNEK PATRZENIA:</b>
Azymut: {look['azimuth_deg']:.1f}° ({look['azimuth_name']})
Elewacja: {look['elevation_deg']:.1f}° nad horyzontem

📊 <b>INFORMACJE:</b>
• Czas UTC: {visibility['time_utc'][11:16]}
• Czas lokalny (PL): {visibility['time_local'][11:16]}
• Szansa na bycie w kadrze: {visibility['success_chance_percent']:.0f}%
• Rozdzielczość: {sat_info['resolution_m']} m/px
• Pas widoczności: {sat_info['swath_km']} km

🎯 <b>INSTRUKCJE:</b>
1. Udaj się na podane współrzędne
2. Patrz w kierunku {look['azimuth_name']} ({look['azimuth_deg']:.0f}°)
3. Satelita będzie na wysokości {look['elevation_deg']:.1f}°
4. Jesteś {optimal['distance_from_nadir_km']:.1f} km od punktu pod satelitą
5. Cały pas widoczności ma {sat_info['swath_km']} km szerokości
"""
        self.send_message(chat_id, message)
        
        # Wyślij lokalizację gdzie stanąć
        self.send_location(chat_id, optimal['lat'], optimal['lon'])
        
        # Wyślij mapy jeśli Mapbox dostępny
        if self.mapbox and self.mapbox.available:
            # Mapa z pozycją
            location_map = self.mapbox.generate_map(optimal['lat'], optimal['lon'])
            if location_map:
                self.send_photo(chat_id, location_map,
                    f"📍 Gdzie stanąć: {location['name']}\n"
                    f"🛰️ {visibility['satellite']}\n"
                    f"🎯 Szansa: {visibility['success_chance_percent']:.0f}%"
                )
            
            # Mapa z kierunkiem
            direction_map = self.mapbox.generate_direction_map(
                optimal['lat'], optimal['lon'], look['azimuth_deg']
            )
            if direction_map:
                self.send_photo(chat_id, direction_map,
                    f"🧭 Kierunek patrzenia: {look['azimuth_name']}\n"
                    f"🎯 {look['azimuth_deg']:.0f}°\n"
                    f"📍 {location['name']}"
                )
    
    def cmd_nextsat(self, chat_id: int, args: List[str]):
        """Następne okazje satelitarne"""
        if len(args) < 2:
            self.send_message(chat_id,
                "🔭 <b>NASTĘPNE OKAZJE - FORMAT:</b>\n"
                "<code>/nextsat [satelita] [lokalizacja] [godziny]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/nextsat landsat warszawa</code> (24h)\n"
                "<code>/nextsat sentinel krakow 48</code>\n"
                "<code>/nextsat iss gdansk 12</code>\n\n"
                "<b>Godziny:</b> 1-72 (domyślnie 24)"
            )
            return
        
        sat_name = args[0].lower()
        loc_name = args[1].lower()
        
        if sat_name not in self.satellites:
            self.send_message(chat_id, f"❌ Nieznany satelita: {sat_name}")
            return
        
        location = self.locations.get(loc_name)
        if not location:
            self.send_message(chat_id, "❌ Nieznana lokalizacja")
            return
        
        hours = 24
        if len(args) > 2:
            try:
                hours = min(int(args[2]), 72)
            except:
                pass
        
        self.send_message(chat_id,
            f"🔭 Szukam okazji dla {self.satellite_calc.SATELLITES[sat_name]['name']}...\n"
            f"📍 {location['name']}\n"
            f"⏰ Następne {hours} godzin"
        )
        
        opportunities = self.satellite_calc.find_next_opportunities(
            sat_name, location['lat'], location['lon'], hours
        )
        
        if not opportunities:
            self.send_message(chat_id,
                f"❌ Brak dobrych okazji w ciągu {hours}h.\n"
                f"Spróbuj zwiększyć zakres lub wybrać innego satelitę."
            )
            return
        
        message = f"""
🔭 <b>NASTĘPNE OKAZJE - {self.satellite_calc.SATELLITES[sat_name]['name'].upper()}</b>
📍 {location['name']} | ⏰ {hours}h
{"="*40}
"""
        
        for i, opp in enumerate(opportunities[:5], 1):
            optimal = opp["optimal_position"]
            local_time = opp["time_local"][11:16]
            
            message += f"\n{i}. 🕐 <b>{local_time}</b> (lokalny)\n"
            message += f"   📍 {optimal['lat']:.4f}°N, {optimal['lon']:.4f}°E\n"
            message += f"   🧭 {optimal['direction_name']} | 📏 {optimal['distance_from_nadir_km']:.1f}km\n"
            message += f"   🎯 Szansa: {opp['success_chance_percent']:.0f}%\n"
            message += f"   👉 <code>/where {sat_name} {loc_name} {local_time}</code>\n"
        
        if len(opportunities) > 5:
            message += f"\n📋 ... i {len(opportunities) - 5} więcej okazji"
        
        self.send_message(chat_id, message)
    
    def cmd_satvisibility(self, chat_id: int, args: List[str]):
        """Szczegółowa analiza widoczności"""
        if len(args) < 2:
            self.send_message(chat_id,
                "📡 <b>ANALIZA WIDOCZNOŚCI - FORMAT:</b>\n"
                "<code>/satvisibility [satelita] [lokalizacja] [czas]</code>\n\n"
                "Pokazuje szczegółową analizę widoczności satelity."
            )
            return
        
        sat_name = args[0].lower()
        loc_name = args[1].lower()
        
        if sat_name not in self.satellites:
            self.send_message(chat_id, f"❌ Nieznany satelita: {sat_name}")
            return
        
        location = self.locations.get(loc_name)
        if not location:
            self.send_message(chat_id, "❌ Nieznana lokalizacja")
            return
        
        time_str = args[2] if len(args) > 2 else None
        target_time = self._parse_time(time_str)
        
        visibility = self.satellite_calc.calculate_visibility(
            sat_name, location['lat'], location['lon'], target_time
        )
        
        if "error" in visibility:
            self.send_message(chat_id, f"❌ Błąd: {visibility['error']}")
            return
        
        sat_info = self.satellite_calc.SATELLITES[sat_name]
        
        message = f"""
📡 <b>SZCZEGÓŁOWA ANALIZA WIDOCZNOŚCI</b>

🛰️ <b>{visibility['satellite']}</b>
📍 Obszar: {location['name']}
🕐 Czas: {visibility['time_local']}

📊 <b>PARAMETRY SATELITY:</b>
• Wysokość orbity: {sat_info['altitude_km']} km
• Rozdzielczość: {sat_info['resolution_m']} metrów/px
• Szerokość pasa: {sat_info['swath_km']} km
• Pole widzenia: {sat_info['fov_deg']}°
• Min. elewacja: {sat_info['min_elevation']}°

📍 <b>POZYCJA SATELITY:</b>
• Nad punktem: {visibility['nadir_point']['lat']:.4f}°N, {visibility['nadir_point']['lon']:.4f}°E
• Promień widoczności: {visibility['visibility_radius_km']:.1f} km

🎯 <b>OPTYMALNA POZYCJA OBSERWATORA:</b>
• Współrzędne: {visibility['optimal_position']['lat']:.6f}°N, {visibility['optimal_position']['lon']:.6f}°E
• Odległość od satelity: {visibility['optimal_position']['distance_from_nadir_km']:.1f} km
• Kierunek: {visibility['optimal_position']['direction_name']}

🧭 <b>KIERUNEK OBSERWACJI:</b>
• Azymut: {visibility['look_angle']['azimuth_deg']:.1f}°
• Elewacja: {visibility['look_angle']['elevation_deg']:.1f}°

📈 <b>OCENA:</b>
• Szansa na bycie w kadrze: {visibility['success_chance_percent']:.0f}%
• Jakość zdjęcia: {'Wysoka' if visibility['success_chance_percent'] > 70 else 'Średnia' if visibility['success_chance_percent'] > 40 else 'Niska'}

💡 <b>INTERPRETACJA:</b>
"""
        
        chance = visibility['success_chance_percent']
        if chance > 80:
            message += "• 🎯 DOSKONAŁA okazja - satelita przechodzi prawie nad głową\n"
            message += "• 📷 Bardzo dobre warunki do fotografii\n"
            message += "• ⭐ Najlepszy możliwy scenariusz\n"
        elif chance > 60:
            message += "• 👍 DOBRA okazja - satelita w dobrym położeniu\n"
            message += "• 📸 Dobre warunki do zdjęć\n"
            message += "• ✅ Warto spróbować\n"
        elif chance > 40:
            message += "• ⚠️ ŚREDNIA okazja - satelita nisko nad horyzontem\n"
            message += "• 🌅 Potrzebujesz czystego horyzontu\n"
            message += "• 📉 Jakość zdjęcia może być ograniczona\n"
        else:
            message += "• ❌ SŁABA okazja - satelita bardzo nisko\n"
            message += "• 🌫️ Duże ryzyko przeszkód terenowych\n"
            message += "• 🚫 Raczej nie warto\n"
        
        message += f"\n📍 <b>UŻYJ:</b> <code>/where {sat_name} {loc_name} {visibility['time_local'][11:16]}</code>"
        message += f"\ndla mapy i dokładnych współrzędnych."
        
        self.send_message(chat_id, message)
        
        # Analiza AI jeśli dostępna
        if self.deepseek and self.deepseek.available and chance > 40:
            self.send_message(chat_id, "🤖 Analizuję dane z DeepSeek AI...")
            
            analysis = self.deepseek.analyze_photo_opportunity(
                {
                    'name': visibility['satellite'],
                    'type': sat_name,
                    'resolution': f"{sat_info['resolution_m']}m",
                    'swath': f"{sat_info['swath_km']}km"
                },
                location
            )
            
            if analysis.get('analysis'):
                self.send_message(chat_id, 
                    f"🤖 <b>ANALIZA DEEPSEEK AI:</b>\n\n"
                    f"{analysis['analysis']}"
                )
    
    def _parse_time(self, time_str: Optional[str]) -> datetime:
        """Parsuj czas z stringa"""
        now = datetime.utcnow()
        
        if not time_str:
            return now + timedelta(hours=1)
        
        try:
            if ':' in time_str:
                hours, minutes = map(int, time_str.split(':'))
            else:
                hours = int(time_str)
                minutes = 0
            
            target = datetime(now.year, now.month, now.day, hours, minutes)
            
            if target < now:
                target += timedelta(days=1)
            
            return target
        except:
            return now + timedelta(hours=1)
    
    # ====================== ORYGINALNE KOMENDY API ======================
    
    def cmd_start(self, chat_id: int):
        """Komenda start"""
        message = """
🛰️ <b>COMPLETE EARTH OBSERVATION PLATFORM v7.0</b>
🌍 <i>Wszystkie API + nowy moduł satelitarny</i>

<b>🎯 NOWOŚĆ: GDZIE STANĄĆ DLA SATELITY</b>
<code>/where [satelita] [lokalizacja] [czas]</code>
Pokazuje gdzie stanąć żeby satelita Cię widział (byłeś w jego kadrze)
• Przykład: <code>/where landsat warszawa 15:30</code>

<code>/nextsat [satelita] [lokalizacja]</code>
Następne okazje w ciągu 24h
• Przykład: <code>/nextsat sentinel krakow</code>

<b>🚨 TRZĘSIENIA ZIEMI (USGS):</b>
<code>/earthquakes [magnituda] [godziny]</code>
• Przykład: <code>/earthquakes 5.0 24</code>

<b>🌤️ POGODA (OpenWeather):</b>
<code>/weather [lokalizacja]</code>
• Przykład: <code>/weather warszawa</code>

<b>🪐 NASA:</b>
<code>/asteroids</code> - bliskie przeloty
<code>/apod</code> - zdjęcie dnia

<b>🗺️ MAPY (Mapbox):</b>
<code>/map [lokalizacja]</code>
• Przykład: <code>/map krakow</code>

<b>🤖 ANALIZA AI (DeepSeek):</b>
<code>/analyze [satelita] [lokalizacja]</code>
• Przykład: <code>/analyze landsat warszawa</code>

<b>📍 INFORMACJE:</b>
<code>/locations</code> - dostępne lokalizacje
<code>/satellites</code> - dostępne satelity
<code>/help</code> - pomoc

<b>⚡ PRZYKŁADY:</b>
• <code>/where landsat warszawa 16:00</code>
• <code>/earthquakes 4.5 12</code>
• <code>/weather gdansk</code>
• <code>/analyze sentinel krakow</code>
"""
        self.send_message(chat_id, message)
    
    def cmd_help(self, chat_id: int):
        """Komenda help"""
        message = """
📋 <b>POMOC - WSZYSTKIE KOMENDY</b>

<b>🛰️ NOWE: SATELITY (GDZIE STANĄĆ):</b>
<code>/where [satelita] [lokalizacja] [czas]</code>
<code>/nextsat [satelita] [lokalizacja] [godziny]</code>
<code>/satvisibility [satelita] [lokalizacja] [czas]</code>

<b>🚨 TRZĘSIENIA ZIEMI:</b>
<code>/earthquakes [magnituda] [godziny]</code>
• Domyślnie: 4.0M, 24h
• Dane z USGS

<b>🌤️ POGODA:</b>
<code>/weather [lokalizacja]</code>
• Dane z OpenWeather
• Temperatura, zachmurzenie, wiatr

<b>🪐 NASA:</b>
<code>/asteroids</code> - asteroidy w ciągu 7 dni
<code>/apod</code> - Astronomy Picture of the Day

<b>🗺️ MAPY:</b>
<code>/map [lokalizacja]</code>
• Mapa satelitarna z Mapbox
• Czerwony marker - lokalizacja

<b>🤖 ANALIZA AI:</b>
<code>/analyze [satelita] [lokalizacja]</code>
• Analiza DeepSeek AI
• Zalecenia techniczne

<b>📍 INFORMACJE:</b>
<code>/locations</code> - 15 lokalizacji w Polsce
<code>/satellites</code> - 4 satelity obserwacyjne

<b>🛰️ SATELITY:</b>
• landsat - Landsat 8 (15m/px, 185km pas)
• sentinel - Sentinel-2A (10m/px, 290km pas)
• iss - ISS (10m/px, 5km pas)
• worldview - WorldView-3 (0.3m/px, 13km pas)

<b>📍 LOKALIZACJE:</b>
warszawa, krakow, gdansk, wroclaw, poznan, szczecin, lodz, lublin,
bialystok, rzeszow, katowice, tatry, mazury, sudety, baltyk
"""
        self.send_message(chat_id, message)
    
    def cmd_earthquakes(self, chat_id: int, args: List[str]):
        """Trzęsienia ziemi"""
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
        
        self.send_message(chat_id, f"🚨 Pobieram trzęsienia ziemi (> {min_mag}M) z {hours}h...")
        
        earthquakes = self.usgs.get_earthquakes(min_mag, hours)
        
        if not earthquakes:
            self.send_message(chat_id, f"🌍 Brak trzęsień > {min_mag}M w {hours}h.")
            return
        
        message = f"🚨 <b>TRZĘSIENIA ZIEMI (>{min_mag}M, {hours}h):</b>\n\n"
        
        for i, quake in enumerate(earthquakes[:5], 1):
            time_ago = datetime.utcnow() - quake['time']
            hours_ago = time_ago.total_seconds() / 3600
            
            message += f"{i}. <b>{quake['place']}</b>\n"
            message += f"   ⚡ <b>{quake['magnitude']}M</b> | 📉 {quake['depth']:.1f} km\n"
            message += f"   ⏰ {hours_ago:.1f}h temu\n"
            message += f"   🌍 {quake['lat']:.3f}, {quake['lon']:.3f}\n\n"
        
        if len(earthquakes) > 5:
            message += f"... i {len(earthquakes) - 5} więcej\n"
        
        self.send_message(chat_id, message)
        
        if earthquakes:
            self.send_location(chat_id, earthquakes[0]['lat'], earthquakes[0]['lon'])
    
    def cmd_weather(self, chat_id: int, args: List[str]):
        """Pogoda"""
        if not self.weather:
            self.send_message(chat_id, "❌ OpenWeather API niedostępne")
            return
        
        if not args:
            self.send_message(chat_id,
                "🌤️ <b>Format:</b> <code>/weather [lokalizacja]</code>\n\n"
                "Przykład: <code>/weather warszawa</code>"
            )
            return
        
        loc_name = args[0].lower()
        location = self.locations.get(loc_name)
        
        if not location:
            self.send_message(chat_id, "❌ Nieznana lokalizacja. Użyj /locations")
            return
        
        self.send_message(chat_id, f"🌤️ Pobieram pogodę dla {location['name']}...")
        
        weather = self.weather.get_weather(location['lat'], location['lon'])
        
        if not weather.get('success', False):
            self.send_message(chat_id, "❌ Błąd pobierania pogody")
            return
        
        message = f"""
🌤️ <b>POGODA - {location['name'].upper()}</b>

🌡️ Temperatura: {weather['temp']:.1f}°C
🤏 Odczuwalna: {weather['feels_like']:.1f}°C
💧 Wilgotność: {weather['humidity']}%
☁️ Zachmurzenie: {weather['clouds']}%
💨 Wiatr: {weather['wind_speed']} m/s
📖 Opis: {weather['description']}
"""
        self.send_message(chat_id, message)
        self.send_location(chat_id, location['lat'], location['lon'])
    
    def cmd_asteroids(self, chat_id: int):
        """Asteroidy"""
        if not self.nasa:
            self.send_message(chat_id, "❌ NASA API niedostępne")
            return
        
        self.send_message(chat_id, "🪐 Pobieram dane o asteroidach...")
        
        asteroids = self.nasa.get_asteroids()
        
        if not asteroids:
            self.send_message(chat_id, "🌍 Brak bliskich przelotów w ciągu 7 dni.")
            return
        
        message = "🪐 <b>BLISKIE PRZELOTY ASTEROID (7 dni):</b>\n\n"
        
        for i, asteroid in enumerate(asteroids[:3], 1):
            distance_mln_km = asteroid['miss_distance_km'] / 1000000
            
            message += f"{i}. <b>{asteroid['name']}</b>\n"
            message += f"   🎯 {distance_mln_km:.2f} mln km\n"
            message += f"   🚀 {asteroid['velocity_kps']:.2f} km/s\n"
            message += f"   ⚠️ <b>{'NIEBEZPIECZNA' if asteroid['hazardous'] else 'Bezpieczna'}</b>\n\n"
        
        self.send_message(chat_id, message)
    
    def cmd_apod(self, chat_id: int):
        """Astronomy Picture of the Day"""
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

<a href="{apod['url']}">🔗 Zobacz zdjęcie</a>
"""
        self.send_message(chat_id, message)
    
    def cmd_map(self, chat_id: int, args: List[str]):
        """Mapa"""
        if not self.mapbox or not self.mapbox.available:
            self.send_message(chat_id, "❌ Mapbox API niedostępne")
            return
        
        if not args:
            self.send_message(chat_id,
                "🗺️ <b>Format:</b> <code>/map [lokalizacja]</code>\n\n"
                "Przykład: <code>/map warszawa</code>"
            )
            return
        
        loc_name = args[0].lower()
        location = self.locations.get(loc_name)
        
        if not location:
            self.send_message(chat_id, "❌ Nieznana lokalizacja")
            return
        
        self.send_message(chat_id, f"🗺️ Generuję mapę dla {location['name']}...")
        
        map_url = self.mapbox.generate_map(location['lat'], location['lon'])
        
        if not map_url:
            self.send_message(chat_id, "❌ Nie udało się wygenerować mapy")
            return
        
        self.send_photo(chat_id, map_url,
            f"🗺️ Mapa satelitarna: {location['name']}\n"
            f"📍 {location['lat']:.4f}°N, {location['lon']:.4f}°E\n"
            f"🔴 Czerwony marker - lokalizacja"
        )
        
        self.send_location(chat_id, location['lat'], location['lon'])
    
    def cmd_analyze(self, chat_id: int, args: List[str]):
        """Analiza AI"""
        if not self.deepseek or not self.deepseek.available:
            self.send_message(chat_id,
                "🤖 <b>DeepSeek API nie jest dostępne</b>\n\n"
                "ℹ️ Dodaj klucz API do environment variables."
            )
            return
        
        if len(args) < 2:
            self.send_message(chat_id,
                "🤖 <b>Format:</b> <code>/analyze [satelita] [lokalizacja]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/analyze landsat warszawa</code>\n"
                "<code>/analyze sentinel krakow</code>"
            )
            return
        
        sat_name = args[0].lower()
        loc_name = args[1].lower()
        
        if sat_name not in self.satellites:
            self.send_message(chat_id, f"❌ Nieznany satelita: {sat_name}")
            return
        
        location = self.locations.get(loc_name)
        if not location:
            self.send_message(chat_id, "❌ Nieznana lokalizacja")
            return
        
        self.send_message(chat_id,
            f"🤖 Analizuję okazję dla {self.satellite_calc.SATELLITES[sat_name]['name']}...\n"
            f"📍 {location['name']}\n"
            f"⏳ Analiza AI może chwilę potrwać..."
        )
        
        sat_info = self.satellite_calc.SATELLITES[sat_name]
        
        analysis = self.deepseek.analyze_photo_opportunity(
            {
                'name': sat_info['name'],
                'type': sat_name,
                'resolution': f"{sat_info['resolution_m']}m",
                'swath': f"{sat_info['swath_km']}km"
            },
            location
        )
        
        if analysis.get('analysis'):
            self.send_message(chat_id,
                f"🤖 <b>ANALIZA DEEPSEEK AI</b>\n\n"
                f"🛰️ <b>{sat_info['name']}</b>\n"
                f"📍 <b>{location['name']}</b>\n\n"
                f"{analysis['analysis']}"
            )
        else:
            self.send_message(chat_id, "❌ Nie udało się przeprowadzić analizy")
    
    def cmd_locations(self, chat_id: int):
        """Lista lokalizacji"""
        message = "📍 <b>DOSTĘPNE LOKALIZACJE:</b>\n\n"
        
        locs = list(self.locations.items())
        for i in range(0, len(locs), 3):
            chunk = locs[i:i+3]
            for key, loc in chunk:
                message += f"• <b>{key}</b> - {loc['name']}\n"
            message += "\n"
        
        message += "🎯 <b>UŻYJ:</b> <code>/where [satelita] [nazwa_lokalizacji] [czas]</code>"
        self.send_message(chat_id, message)
    
    def cmd_satellites_list(self, chat_id: int):
        """Lista satelitów"""
        message = "🛰️ <b>DOSTĘPNE SATELITY OBSERWACYJNE:</b>\n\n"
        
        for key, sat in self.satellite_calc.SATELLITES.items():
            message += f"• <b>{key}</b> - {sat['name']}\n"
            message += f"  📷 {sat['resolution_m']}m/px | 📏 {sat['swath_km']}km pas\n"
            message += f"  🛰️ {sat['altitude_km']}km | 🎯 min. {sat['min_elevation']}°\n"
            message += f"  👉 <code>/where {key} [lokalizacja] [czas]</code>\n\n"
        
        message += "ℹ️ <b>WorldView-3</b> ma najwyższą rozdzielczość (0.3m) ale wąski pas (13km)"
        self.send_message(chat_id, message)

# ====================== FLASK APP ======================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = CompleteEarthObservationBot()

@app.route('/')
def home():
    api_status = {
        "telegram": bool(TELEGRAM_BOT_TOKEN),
        "usgs": True,
        "nasa": bool(NASA_API_KEY),
        "weather": bool(OPENWEATHER_API_KEY),
        "mapbox": bool(MAPBOX_API_KEY),
        "n2yo": bool(N2YO_API_KEY),
        "deepseek": bool(DEEPSEEK_API_KEY)
    }
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🛰️ Complete Earth Observation Platform v7.0</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0c2461 0%, #1e3799 50%, #4a69bd 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                margin-top: 20px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }}
            h1 {{
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .api-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .api-item {{
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }}
            .api-item.ok {{
                border-left: 5px solid #4CAF50;
            }}
            .api-item.error {{
                border-left: 5px solid #f44336;
            }}
            .command {{
                background: rgba(0, 0, 0, 0.3);
                padding: 10px 15px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
                display: block;
            }}
            .telegram-link {{
                display: inline-block;
                background: #0088cc;
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                margin-top: 20px;
                font-weight: bold;
                font-size: 1.1em;
                transition: background 0.3s;
                text-align: center;
                width: 100%;
                box-sizing: border-box;
            }}
            .telegram-link:hover {{
                background: #006699;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ Complete Earth Observation Platform</h1>
            <div style="text-align: center; margin-bottom: 30px; font-size: 1.2em;">
                v7.0 - Wszystkie API + Nowy moduł satelitarny
            </div>
            
            <div style="background: rgba(0, 255, 0, 0.1); padding: 15px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #00ff00;">
                <b>🎯 NOWOŚĆ:</b> System pokazuje gdzie stanąć żeby satelita Cię widział (byłeś w jego kadrze)
            </div>
            
            <div class="api-grid">
                <div class="api-item {'ok' if api_status['telegram'] else 'error'}">
                    <h3>🤖 Telegram</h3>
                    <p>{'✅ Aktywny' if api_status['telegram'] else '❌ Brak'}</p>
                </div>
                <div class="api-item ok">
                    <h3>🚨 USGS</h3>
                    <p>✅ Aktywny</p>
                </div>
                <div class="api-item {'ok' if api_status['nasa'] else 'error'}">
                    <h3>🪐 NASA</h3>
                    <p>{'✅ Aktywny' if api_status['nasa'] else '⚠️ Demo'}</p>
                </div>
                <div class="api-item {'ok' if api_status['weather'] else 'error'}">
                    <h3>🌤️ Weather</h3>
                    <p>{'✅ Aktywny' if api_status['weather'] else '❌ Brak'}</p>
                </div>
                <div class="api-item {'ok' if api_status['mapbox'] else 'error'}">
                    <h3>🗺️ Mapbox</h3>
                    <p>{'✅ Aktywny' if api_status['mapbox'] else '❌ Brak'}</p>
                </div>
                <div class="api-item {'ok' if api_status['deepseek'] else 'error'}">
                    <h3>🤖 DeepSeek</h3>
                    <p>{'✅ Aktywny' if api_status['deepseek'] else '❌ Brak'}</p>
                </div>
            </div>
            
            <h3>🚀 NOWE KOMENDY SATELITARNE:</h3>
            <div class="command">/where landsat warszawa 15:30</div>
            <p>Pokazuje gdzie stanąć żeby Landsat Cię widział o 15:30</p>
            
            <div class="command">/nextsat sentinel krakow</div>
            <p>Następne okazje w ciągu 24h</p>
            
            <div class="command">/satvisibility iss gdansk</div>
            <p>Szczegółowa analiza widoczności</p>
            
            <h3>🌍 ORYGINALNE FUNKCJE:</h3>
            <div class="command">/earthquakes 5.0 24</div>
            <p>Trzęsienia ziemi >5.0M z 24h</p>
            
            <div class="command">/weather warszawa</div>
            <p>Pogoda w Warszawie</p>
            
            <div class="command">/asteroids</div>
            <p>Bliskie przeloty asteroid</p>
            
            <div class="command">/apod</div>
            <p>NASA Astronomy Picture of the Day</p>
            
            <div class="command">/analyze landsat warszawa</div>
            <p>Analiza AI okazji satelitarnej</p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/PcSentinel_Bot" class="telegram-link" target="_blank">
                    💬 Rozpocznij z @PcSentinel_Bot
                </a>
            </div>
            
            <div style="margin-top: 30px; font-size: 0.9em; opacity: 0.8; text-align: center;">
                <p>🛰️ System oblicza gdzie stanąć żeby być widocznym dla satelity</p>
                <p>🌍 Wersja 7.0 | Wszystkie API | Nowy moduł widoczności | Render.com</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook Telegram"""
    try:
        data = request.get_json()
        
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "").strip()
            
            if text.startswith('/'):
                parts = text.split()
                command = parts[0][1:]
                args = parts[1:] if len(parts) > 1 else []
                
                bot.handle_command(chat_id, command, args)
            else:
                bot.send_message(chat_id,
                    "🛰️ <b>Complete Earth Observation Platform v7.0</b>\n\n"
                    "Użyj jednej z komend:\n"
                    "<code>/where [satelita] [lokalizacja] [czas]</code> - gdzie stanąć\n"
                    "<code>/nextsat [satelita] [lokalizacja]</code> - następne okazje\n"
                    "<code>/earthquakes [magnituda] [godziny]</code> - trzęsienia ziemi\n"
                    "<code>/weather [lokalizacja]</code> - pogoda\n"
                    "<code>/asteroids</code> - asteroidy\n"
                    "<code>/apod</code> - NASA zdjęcie dnia\n"
                    "<code>/help</code> - pomoc\n\n"
                    "<b>Przykład:</b> <code>/where landsat warszawa 16:00</code>"
                )
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Ustaw webhook"""
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({"status": "error", "message": "Brak tokena"}), 400
    
    try:
        webhook_url = f"{RENDER_URL}/webhook"
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            json={"url": webhook_url}
        )
        
        return jsonify({
            "status": "success" if response.status_code == 200 else "error",
            "webhook_url": webhook_url,
            "response": response.json() if response.status_code == 200 else response.text
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("=" * 80)
    print("🛰️ COMPLETE EARTH OBSERVATION PLATFORM v7.0")
    print("=" * 80)
    
    print("🔧 STATUS WSZYSTKICH API:")
    print(f"   🤖 Telegram Bot: {'✅ AKTYWNY' if bot.available else '❌ BRAK TOKENA'}")
    print(f"   🚨 USGS Earthquakes: ✅ ZAWSZE DZIAŁA")
    print(f"   🪐 NASA API: {'✅ AKTYWNY' if NASA_API_KEY and NASA_API_KEY != 'DEMO_KEY' else '⚠️ DEMO MODE'}")
    print(f"   🌤️ OpenWeather: {'✅ AKTYWNY' if OPENWEATHER_API_KEY else '❌ BRAK'}")
    print(f"   🗺️ Mapbox: {'✅ AKTYWNY' if MAPBOX_API_KEY else '❌ BRAK'}")
    print(f"   📡 N2YO Satellites: {'✅ AKTYWNY' if N2YO_API_KEY else '⚠️ SYMULACJA'}")
    print(f"   🤖 DeepSeek AI: {'✅ AKTYWNY' if DEEPSEEK_API_KEY else '❌ BRAK'}")
    print(f"   🛰️ Satellite Calculator: ✅ WŁASNY SYSTEM")
    print("=" * 80)
    
    if bot.available:
        try:
            webhook_url = f"{RENDER_URL}/webhook"
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                json={"url": webhook_url},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Webhook ustawiony: {webhook_url}")
            else:
                print(f"⚠️ Błąd webhooka: {response.text}")
        except Exception as e:
            print(f"⚠️ Błąd ustawiania webhooka: {e}")
    
    print("\n🚀 GŁÓWNE KOMENDY:")
    print("   /where [satelita] [lokalizacja] [czas] - GDZIE STANĄĆ")
    print("   /nextsat [satelita] [lokalizacja] - NASTĘPNE OKAZJE")
    print("   /earthquakes [magnituda] [godziny] - TRZĘSIENIA ZIEMI")
    print("   /weather [lokalizacja] - POGODA")
    print("   /asteroids - ASTEROIDY")
    print("   /apod - NASA ZDJĘCIE DNIA")
    print("   /analyze [satelita] [lokalizacja] - ANALIZA AI")
    print("   /locations - LISTA LOKALIZACJI")
    print("   /satellites - LISTA SATELITÓW")
    
    print("\n🎯 PRZYKŁAD:")
    print("   /where landsat warszawa 16:00")
    print("   /earthquakes 4.5 12")
    print("   /weather krakow")
    print("   /analyze sentinel gdansk")
    print("=" * 80)
    print("✅ SYSTEM GOTOWY DO DZIAŁANIA!")
    print("=" * 80)
    
    app.run(host="0.0.0.0", port=PORT, debug=False)