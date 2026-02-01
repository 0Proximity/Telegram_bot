#!/usr/bin/env python3
"""
🛰️ SATELLITE VISIBILITY CALCULATOR v6.7
✅ Oblicza gdzie stanąć żeby być widocznym dla satelity
✅ Pokazuje dokładne współrzędne w zasięgu kamery
✅ Wylicza optymalną pozycję dla fotografii
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

# ====================== KONFIGURACJA ======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
N2YO_API_KEY = os.getenv("N2YO_API_KEY")
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
RENDER_URL = os.getenv("RENDER_URL", "https://your-app.onrender.com")
PORT = int(os.getenv("PORT", 10000))

# ====================== KALKULATOR WIDOCZNOŚCI SATELITY ======================

class SatelliteVisibilityCalculator:
    """Oblicza gdzie stanąć żeby być widocznym dla satelity"""
    
    # Charakterystyki kamer satelitarnych
    SATELLITE_CAMERAS = {
        "landsat-8": {
            "name": "Landsat 8",
            "norad_id": 39084,
            "altitude_km": 705,
            "fov_deg": 15.0,  # Pole widzenia
            "swath_width_km": 185,  # Szerokość pasa
            "pixel_size_m": 15,
            "min_elevation": 20,  # Minimalny kąt dla dobrego zdjęcia
            "max_off_nadir_deg": 30  # Maksymalne odchylenie od pionu
        },
        "sentinel-2": {
            "name": "Sentinel-2",
            "norad_id": 40697,
            "altitude_km": 786,
            "fov_deg": 20.6,
            "swath_width_km": 290,
            "pixel_size_m": 10,
            "min_elevation": 15,
            "max_off_nadir_deg": 25
        },
        "iss": {
            "name": "ISS",
            "norad_id": 25544,
            "altitude_km": 408,
            "fov_deg": 50.0,
            "swath_width_km": 5,  # EarthKAM ma wąskie pole
            "pixel_size_m": 10,
            "min_elevation": 10,
            "max_off_nadir_deg": 90
        },
        "worldview-3": {
            "name": "WorldView-3",
            "norad_id": 40115,
            "altitude_km": 617,
            "fov_deg": 1.2,
            "swath_width_km": 13.1,
            "pixel_size_m": 0.31,
            "min_elevation": 25,
            "max_off_nadir_deg": 45
        }
    }
    
    def calculate_visibility_zone(self, sat_name: str, lat: float, lon: float, 
                                 time_utc: datetime) -> Dict:
        """Oblicza strefę widoczności satelity w danym momencie"""
        sat = self.SATELLITE_CAMERAS.get(sat_name)
        if not sat:
            return {"error": "Nieznany satelita"}
        
        # Pobierz pozycję satelity
        sat_pos = self._get_satellite_position(sat["norad_id"], lat, lon, time_utc)
        if not sat_pos:
            return {"error": "Nie udało się pobrać pozycji"}
        
        # Oblicz miejsce pod satelitą (nadir point)
        nadir_point = self._calculate_nadir_point(sat_pos, sat["altitude_km"])
        
        # Oblicz strefę widoczności
        visibility_zone = self._calculate_visibility_circle(
            nadir_point, sat["swath_width_km"], sat["fov_deg"]
        )
        
        # Oblicz optymalną pozycję dla fotografa
        optimal_position = self._calculate_optimal_position(
            nadir_point, visibility_zone, sat["min_elevation"], sat["altitude_km"]
        )
        
        # Oblicz kąt patrzenia
        look_angle = self._calculate_look_angle(optimal_position, sat_pos)
        
        return {
            "satellite": sat["name"],
            "time_utc": time_utc.isoformat(),
            "satellite_position": sat_pos,
            "nadir_point": nadir_point,
            "visibility_zone": visibility_zone,
            "optimal_position": optimal_position,
            "look_angle": look_angle,
            "camera_info": {
                "fov_deg": sat["fov_deg"],
                "swath_km": sat["swath_width_km"],
                "resolution_m": sat["pixel_size_m"],
                "min_elevation": sat["min_elevation"]
            }
        }
    
    def _get_satellite_position(self, norad_id: int, lat: float, lon: float, 
                               time_utc: datetime) -> Optional[Dict]:
        """Pobierz pozycję satelity"""
        try:
            if N2YO_API_KEY:
                # Konwertuj czas na timestamp
                timestamp = int(time_utc.timestamp())
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
                            'altitude': pos.get('sataltitude', 0),
                            'azimuth': pos.get('azimuth', 0),
                            'elevation': pos.get('elevation', 0)
                        }
        except:
            pass
        
        # Fallback: symulacja pozycji
        return self._simulate_satellite_position(lat, lon, time_utc)
    
    def _simulate_satellite_position(self, lat: float, lon: float, 
                                    time_utc: datetime) -> Dict:
        """Symuluj pozycję satelity"""
        # Prosta symulacja - satelita przechodzi nad głową
        hour = time_utc.hour + time_utc.minute/60
        orbit_phase = (hour % 2) * 180  # Co 2 godziny
        
        return {
            'lat': lat + math.sin(orbit_phase * math.pi/180) * 5,
            'lon': lon + math.cos(orbit_phase * math.pi/180) * 10,
            'altitude': 700,
            'azimuth': (orbit_phase * 2) % 360,
            'elevation': 45 + math.sin(orbit_phase * math.pi/180) * 30
        }
    
    def _calculate_nadir_point(self, sat_pos: Dict, altitude_km: float) -> Dict:
        """Oblicz punkt bezpośrednio pod satelitą (nadir)"""
        # Dla uproszczenia: nadir jest w przybliżeniu pod satelitą
        return {
            'lat': sat_pos['lat'],
            'lon': sat_pos['lon']
        }
    
    def _calculate_visibility_circle(self, center: Dict, swath_km: float, 
                                    fov_deg: float) -> Dict:
        """Oblicz okrąg widoczności satelity"""
        radius_km = swath_km / 2
        
        return {
            'center': center,
            'radius_km': radius_km,
            'area_sqkm': math.pi * radius_km * radius_km,
            'bounding_box': self._calculate_bounding_box(center, radius_km)
        }
    
    def _calculate_bounding_box(self, center: Dict, radius_km: float) -> Dict:
        """Oblicz bounding box dla okręgu"""
        # 1 stopień ≈ 111 km
        lat_offset = radius_km / 111
        lon_offset = radius_km / (111 * math.cos(math.radians(center['lat'])))
        
        return {
            'north': center['lat'] + lat_offset,
            'south': center['lat'] - lat_offset,
            'east': center['lon'] + lon_offset,
            'west': center['lon'] - lon_offset
        }
    
    def _calculate_optimal_position(self, nadir: Dict, zone: Dict, 
                                   min_elevation: float, altitude_km: float) -> Dict:
        """Oblicz optymalną pozycję dla fotografa"""
        # Najlepsza pozycja jest na krawędzi strefy widoczności
        # gdzie satelita ma minimalną wymaganą elewację
        radius_km = zone['radius_km']
        
        # Wybierz losowy punkt na obwodzie (w praktyce wybierz północny wschód)
        angle_deg = 45  # Północny wschód dla dobrego światła
        angle_rad = math.radians(angle_deg)
        
        # Przesunięcie w km
        dx = radius_km * math.cos(angle_rad)
        dy = radius_km * math.sin(angle_rad)
        
        # Konwertuj na stopnie
        lat_offset = dy / 111
        lon_offset = dx / (111 * math.cos(math.radians(nadir['lat'])))
        
        return {
            'lat': nadir['lat'] + lat_offset,
            'lon': nadir['lon'] + lon_offset,
            'distance_from_nadir_km': radius_km,
            'direction_deg': angle_deg,
            'direction_name': self._get_direction_name(angle_deg)
        }
    
    def _calculate_look_angle(self, observer_pos: Dict, sat_pos: Dict) -> Dict:
        """Oblicz kąt patrzenia z pozycji obserwatora do satelity"""
        # Różnice współrzędnych
        dlat = sat_pos['lat'] - observer_pos['lat']
        dlon = sat_pos['lon'] - observer_pos['lon']
        
        # Oblicz azymut
        y = math.sin(math.radians(dlon)) * math.cos(math.radians(sat_pos['lat']))
        x = (math.cos(math.radians(observer_pos['lat'])) * 
             math.sin(math.radians(sat_pos['lat'])) - 
             math.sin(math.radians(observer_pos['lat'])) * 
             math.cos(math.radians(sat_pos['lat'])) * 
             math.cos(math.radians(dlon)))
        
        azimuth = math.degrees(math.atan2(y, x))
        if azimuth < 0:
            azimuth += 360
        
        # Oblicz elewację (uproszczone)
        distance_deg = math.sqrt(dlat*dlat + dlon*dlon)
        distance_km = distance_deg * 111
        
        if sat_pos.get('altitude', 700) > 0:
            elevation = math.degrees(math.atan2(sat_pos['altitude'], distance_km))
        else:
            elevation = 45  # Domyślna
        
        return {
            'azimuth_deg': round(azimuth, 1),
            'elevation_deg': round(elevation, 1),
            'azimuth_name': self._get_direction_name(azimuth)
        }
    
    def _get_direction_name(self, angle_deg: float) -> str:
        """Konwertuj kąt na nazwę kierunku"""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(angle_deg / 45) % 8
        return directions[idx]
    
    def find_next_visibility(self, sat_name: str, lat: float, lon: float, 
                            hours_ahead: int = 24) -> List[Dict]:
        """Znajdź następne okazje kiedy satelita będzie widoczny"""
        opportunities = []
        now = datetime.utcnow()
        
        sat = self.SATELLITE_CAMERAS.get(sat_name)
        if not sat:
            return opportunities
        
        # Sprawdź co godzinę przez następne godziny
        for hour in range(0, hours_ahead + 1, 1):
            check_time = now + timedelta(hours=hour)
            
            # Pobierz pozycję satelity
            sat_pos = self._get_satellite_position(sat["norad_id"], lat, lon, check_time)
            if not sat_pos:
                continue
            
            # Sprawdź czy satelita jest wystarczająco wysoko
            if sat_pos.get('elevation', 0) >= sat["min_elevation"]:
                # Oblicz strefę widoczności
                visibility = self.calculate_visibility_zone(sat_name, lat, lon, check_time)
                
                if "error" not in visibility:
                    # Dodaj jeśli pozycja obserwatora jest w strefie widoczności
                    distance = self._calculate_distance_km(
                        lat, lon, 
                        visibility["optimal_position"]["lat"],
                        visibility["optimal_position"]["lon"]
                    )
                    
                    if distance <= visibility["visibility_zone"]["radius_km"]:
                        opportunities.append({
                            "time_utc": check_time,
                            "local_time": (check_time + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
                            "visibility_info": visibility,
                            "distance_to_zone_km": distance,
                            "chance_percentage": self._calculate_chance(visibility, sat_pos)
                        })
        
        # Sortuj po szansie i czasie
        opportunities.sort(key=lambda x: (-x["chance_percentage"], x["time_utc"]))
        return opportunities[:10]  # Max 10 wyników
    
    def _calculate_distance_km(self, lat1: float, lon1: float, 
                              lat2: float, lon2: float) -> float:
        """Oblicz odległość między punktami w km"""
        R = 6371  # Promień Ziemi w km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon/2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def _calculate_chance(self, visibility: Dict, sat_pos: Dict) -> float:
        """Oblicz szansę na dobre zdjęcie"""
        chance = 70.0  # Podstawowa szansa
        
        # Im wyższa elewacja, tym lepiej
        elevation = sat_pos.get('elevation', 0)
        if elevation > 60:
            chance += 20
        elif elevation > 30:
            chance += 10
        
        # Im bliżej nadiru, tym lepsza jakość
        distance = visibility["optimal_position"]["distance_from_nadir_km"]
        swath = visibility["camera_info"]["swath_km"]
        
        if distance < swath * 0.3:
            chance += 15
        elif distance < swath * 0.6:
            chance += 5
        
        # Satelity o wyższej rozdzielczości mają większą szansę
        resolution = visibility["camera_info"]["resolution_m"]
        if resolution < 1:
            chance += 10
        elif resolution < 10:
            chance += 5
        
        return min(99, max(1, round(chance, 1)))

# ====================== MAPBOX HELPER ======================

class SatelliteMapGenerator:
    """Generuje mapy z pozycjami satelity i obserwatora"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.available = bool(api_key)
    
    def generate_visibility_map(self, observer_pos: Dict, sat_pos: Dict, 
                               zone_center: Dict, zone_radius_km: float) -> str:
        """Generuje mapę z strefą widoczności"""
        if not self.available:
            return ""
        
        try:
            style = "satellite-streets-v12"
            size = "800x600"
            
            # Marker obserwatora (gdzie stanąć)
            observer_marker = f"pin-l+00ff00({observer_pos['lon']},{observer_pos['lat']})"
            
            # Marker satelity (nadir point)
            sat_marker = f"pin-l+ff0000({zone_center['lon']},{zone_center['lat']})"
            
            # Okrąg strefy widoczności (przybliżenie przez polygon)
            circle_points = self._generate_circle_polygon(
                zone_center['lat'], zone_center['lon'], zone_radius_km
            )
            
            # Tworzymy polygon dla strefy
            polygon_coords = ",".join([f"{lon},{lat}" for lat, lon in circle_points])
            zone_polygon = f"path-2+00ff00-0.2({polygon_coords})"
            
            # Łączymy wszystkie elementy
            overlays = f"{zone_polygon},{observer_marker},{sat_marker}"
            
            # Centrum mapy - między obserwatorem a satelitą
            center_lat = (observer_pos['lat'] + zone_center['lat']) / 2
            center_lon = (observer_pos['lon'] + zone_center['lon']) / 2
            
            # Zoom dostosowany do odległości
            distance = self._calculate_distance_km(
                observer_pos['lat'], observer_pos['lon'],
                zone_center['lat'], zone_center['lon']
            )
            zoom = max(9, min(14, 14 - math.log2(distance/10)))
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"{overlays}/"
                f"{center_lon},{center_lat},{zoom}/{size}@2x"
                f"?access_token={self.api_key}"
                f"&attribution=false"
                f"&logo=false"
            )
            
            return map_url
        except Exception as e:
            print(f"Błąd generowania mapy: {e}")
            return ""
    
    def generate_direction_map(self, observer_pos: Dict, azimuth: float, 
                              distance_km: float = 10) -> str:
        """Generuje mapę z strzałką kierunku"""
        if not self.available:
            return ""
        
        try:
            # Oblicz punkt końcowy strzałki
            end_point = self._calculate_endpoint(
                observer_pos['lat'], observer_pos['lon'], azimuth, distance_km
            )
            
            style = "satellite-streets-v12"
            size = "800x600"
            
            # Marker obserwatora
            start_marker = f"pin-s+00ff00({observer_pos['lon']},{observer_pos['lat']})"
            
            # Strzałka kierunku (linia)
            path = f"path-3+ff0000-0.8({observer_pos['lon']},{observer_pos['lat']},{end_point['lon']},{end_point['lat']})"
            
            # Marker końcowy
            end_marker = f"pin-s+ff0000({end_point['lon']},{end_point['lat']})"
            
            overlays = f"{path},{start_marker},{end_marker}"
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"{overlays}/"
                f"{observer_pos['lon']},{observer_pos['lat']},13/{size}@2x"
                f"?access_token={self.api_key}"
                f"&attribution=false"
                f"&logo=false"
            )
            
            return map_url
        except Exception as e:
            print(f"Błąd generowania mapy kierunku: {e}")
            return ""
    
    def _calculate_distance_km(self, lat1: float, lon1: float, 
                              lat2: float, lon2: float) -> float:
        """Oblicz odległość między punktami w km"""
        R = 6371
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon/2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def _calculate_endpoint(self, lat: float, lon: float, 
                           azimuth_deg: float, distance_km: float) -> Dict:
        """Oblicz punkt końcowy w danym kierunku"""
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
    
    def _generate_circle_polygon(self, lat: float, lon: float, 
                                radius_km: float, points: int = 36) -> List[Tuple]:
        """Generuje punkty dla okręgu"""
        circle_points = []
        
        for i in range(points):
            angle = 2 * math.pi * i / points
            dx = radius_km * math.cos(angle)
            dy = radius_km * math.sin(angle)
            
            # Konwertuj przesunięcie na stopnie
            lat_offset = dy / 111
            lon_offset = dx / (111 * math.cos(math.radians(lat)))
            
            circle_points.append((
                lat + lat_offset,
                lon + lon_offset
            ))
        
        return circle_points

# ====================== TELEGRAM BOT ======================

class SatelliteVisibilityBot:
    """Bot który pokazuje gdzie stanąć żeby być widocznym dla satelity"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.available = bool(TELEGRAM_BOT_TOKEN)
        
        self.calculator = SatelliteVisibilityCalculator()
        self.map_generator = SatelliteMapGenerator(MAPBOX_API_KEY)
        
        # Lokalizacje w Polsce
        self.locations = {
            "warszawa": {"name": "Warszawa", "lat": 52.2297, "lon": 21.0122},
            "krakow": {"name": "Kraków", "lat": 50.0614, "lon": 19.9366},
            "gdansk": {"name": "Gdańsk", "lat": 54.3722, "lon": 18.6383},
            "wroclaw": {"name": "Wrocław", "lat": 51.1079, "lon": 17.0385},
            "poznan": {"name": "Poznań", "lat": 52.4064, "lon": 16.9252},
            "bialystok": {"name": "Białystok", "lat": 53.1333, "lon": 23.1643},
            "rzeszow": {"name": "Rzeszów", "lat": 50.0413, "lon": 21.9991},
            "katowice": {"name": "Katowice", "lat": 50.2649, "lon": 19.0238},
            "szczecin": {"name": "Szczecin", "lat": 53.4289, "lon": 14.5530},
            "lodz": {"name": "Łódź", "lat": 51.7592, "lon": 19.4558},
            "lublin": {"name": "Lublin", "lat": 51.2465, "lon": 22.5684},
            "tatry": {"name": "Tatry", "lat": 49.2992, "lon": 19.9496},
            "sudety": {"name": "Sudety", "lat": 50.7750, "lon": 16.2917},
            "mazury": {"name": "Mazury", "lat": 53.8667, "lon": 21.5000},
            "baltyk": {"name": "Bałtyk", "lat": 54.5000, "lon": 18.5500},
        }
        
        self.satellites = list(self.calculator.SATELLITE_CAMERAS.keys())
    
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
        except Exception as e:
            print(f"Błąd wysyłania: {e}")
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
        except Exception as e:
            print(f"Błąd wysyłania zdjęcia: {e}")
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
        except Exception as e:
            print(f"Błąd wysyłania lokalizacji: {e}")
            return False
    
    def handle_command(self, chat_id: int, command: str, args: List[str]):
        """Obsłuż komendę"""
        command = command.lower()
        
        if command == "start":
            self.cmd_start(chat_id)
        elif command == "help":
            self.cmd_help(chat_id)
        elif command == "where" or command == "gdzie":
            self.cmd_where(chat_id, args)
        elif command == "next" or command == "nastepne":
            self.cmd_next(chat_id, args)
        elif command == "locations" or command == "lokalizacje":
            self.cmd_locations(chat_id)
        elif command == "satellites" or command == "satelity":
            self.cmd_satellites(chat_id)
        else:
            self.send_message(chat_id, "❌ Nieznana komenda. Użyj /help")
    
    def cmd_start(self, chat_id: int):
        """Komenda /start"""
        message = """
🛰️ <b>SATELLITE VISIBILITY CALCULATOR</b>
📍 <i>Pokazuje gdzie stanąć żeby być w kadrze satelity</i>

<b>DZIAŁANIE:</b>
System oblicza gdzie musisz stanąć, aby satelita Cię widział (byłeś w jego polu widzenia). Nie pokazuje Twojej aktualnej pozycji, tylko OPTYMALNĄ POZYCJĘ OBSERWACYJNĄ.

<b>GŁÓWNE KOMENDY:</b>
<code>/where [satelita] [lokalizacja] [czas]</code>
• Pokazuje gdzie stanąć w konkretnym czasie
• Przykład: <code>/where landsat warszawa 14:00</code>

<code>/next [satelita] [lokalizacja] [godziny]</code>
• Znajduje następne okazje
• Przykład: <code>/next sentinel krakow 24</code>

<code>/locations</code> - dostępne lokalizacje
<code>/satellites</code> - dostępne satelity
<code>/help</code> - pomoc

<b>PRZYKŁAD:</b>
Chcesz, żeby Landsat 8 Cię sfotografował?
Użyj: <code>/where landsat warszawa 15:30</code>

System pokaże Ci:
1. 🗺️ Gdzie stanąć (współrzędne)
2. 🧭 W którą stronę patrzeć
3. 📏 W jakiej odległości jesteś od satelity
4. 🎯 Czy jesteś w jego polu widzenia
"""
        self.send_message(chat_id, message)
    
    def cmd_help(self, chat_id: int):
        """Komenda /help"""
        message = """
📋 <b>POMOC - SATELLITE VISIBILITY CALCULATOR</b>

<b>🎯 CEL SYSTEMU:</b>
Pokazuje dokładnie gdzie stanąć, żeby być widocznym dla satelity (być w jego kadrze).

<b>🚀 DOSTĘPNE SATELITY:</b>
• <b>landsat</b> - Landsat 8 (15m/px, pas 185km)
• <b>sentinel</b> - Sentinel-2 (10m/px, pas 290km)  
• <b>iss</b> - Międzynarodowa Stacja Kosmiczna
• <b>worldview</b> - WorldView-3 (0.3m/px, wąski pas)

<b>📍 DOSTĘPNE LOKALIZACJE:</b>
warszawa, krakow, gdansk, wroclaw, poznan, bialystok, rzeszow, katowice, szczecin, lodz, lublin, tatry, sudety, mazury, baltyk

<b>🛰️ GŁÓWNE KOMENDY:</b>
<code>/where [satelita] [lokalizacja] [czas]</code>
Przykład: <code>/where landsat warszawa 14:30</code>

<code>/next [satelita] [lokalizacja] [godziny]</code>
Przykład: <code>/next sentinel gdansk 48</code>

<code>/locations</code> - lista lokalizacji
<code>/satellites</code> - lista satelitów

<b>⏰ FORMAT CZASU:</b>
• Godzina: <code>14:30</code>
• Godzina bez minut: <code>14</code>
• Domyślnie: aktualny czas + 1 godzina

<b>🗺️ WYNIK ZAWIERA:</b>
• Współrzędne gdzie stanąć
• Kierunek patrzenia (azymut)
• Odległość od satelity
• Szansę na bycie w kadrze
• Mapę z Twoją pozycją i satelitą
"""
        self.send_message(chat_id, message)
    
    def cmd_where(self, chat_id: int, args: List[str]):
        """Komenda /where - gdzie stanąć w konkretnym czasie"""
        if len(args) < 2:
            self.send_message(chat_id,
                "📍 <b>Format:</b> <code>/where [satelita] [lokalizacja] [czas]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/where landsat warszawa 14:30</code>\n"
                "<code>/where sentinel krakow 15</code>\n"
                "<code>/where iss gdansk</code> (czas domyślny: za 1h)\n\n"
                "<b>Satelity:</b> landsat, sentinel, iss, worldview\n"
                "<b>Czas:</b> HH:MM lub HH (24h format)"
            )
            return
        
        sat_name = args[0].lower()
        loc_name = args[1].lower()
        
        # Sprawdź satelitę
        if sat_name not in self.satellites:
            self.send_message(chat_id, 
                f"❌ Nieznany satelita: {sat_name}\n"
                f"Dostępne: {', '.join(self.satellites)}"
            )
            return
        
        # Sprawdź lokalizację
        location = self.locations.get(loc_name)
        if not location:
            self.send_message(chat_id, "❌ Nieznana lokalizacja. Użyj /locations")
            return
        
        # Parsuj czas
        time_str = None
        if len(args) > 2:
            time_str = args[2]
        
        target_time = self._parse_time(time_str)
        
        self.send_message(chat_id, 
            f"🛰️ Obliczam gdzie stanąć dla {self.calculator.SATELLITE_CAMERAS[sat_name]['name']}...\n"
            f"📍 {location['name']}\n"
            f"🕐 {target_time.strftime('%Y-%m-%d %H:%M')} UTC"
        )
        
        # Oblicz widoczność
        visibility = self.calculator.calculate_visibility_zone(
            sat_name, location['lat'], location['lon'], target_time
        )
        
        if "error" in visibility:
            self.send_message(chat_id, f"❌ Błąd: {visibility['error']}")
            return
        
        # Przygotuj wiadomość
        sat_info = self.calculator.SATELLITE_CAMERAS[sat_name]
        optimal_pos = visibility["optimal_position"]
        look_angle = visibility["look_angle"]
        zone = visibility["visibility_zone"]
        
        message = f"""
🛰️ <b>{visibility['satellite']} - OPTYMALNA POZYCJA</b>

📍 <b>GDZIE STAĆ:</b>
Szerokość: <code>{optimal_pos['lat']:.6f}°N</code>
Długość: <code>{optimal_pos['lon']:.6f}°E</code>
Kierunek: {optimal_pos['direction_name']} ({optimal_pos['direction_deg']:.0f}°)
Odległość od satelity: {optimal_pos['distance_from_nadir_km']:.1f} km

🧭 <b>KIERUNEK PATRZENIA:</b>
Azymut: {look_angle['azimuth_deg']:.1f}° ({look_angle['azimuth_name']})
Elewacja: {look_angle['elevation_deg']:.1f}°

📏 <b>STREFA WIDOCZNOŚCI SATELITY:</b>
Środek: {zone['center']['lat']:.4f}°N, {zone['center']['lon']:.4f}°E
Promień: {zone['radius_km']:.1f} km
Powierzchnia: {zone['area_sqkm']:.0f} km²

📷 <b>KAMERA:</b>
Pole widzenia: {sat_info['fov_deg']}°
Szerokość pasa: {sat_info['swath_width_km']} km
Rozdzielczość: {sat_info['pixel_size_m']} m/px
Min. elewacja: {sat_info['min_elevation']}°

⏰ <b>CZAS:</b>
UTC: {target_time.strftime('%Y-%m-%d %H:%M:%S')}
Lokalny (PL): {(target_time + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')}

🎯 <b>WSKAZÓWKI:</b>
1. Udaj się na współrzędne podane wyżej
2. Patrz w kierunku {look_angle['azimuth_name']} ({look_angle['azimuth_deg']:.0f}°)
3. Satelita będzie na wysokości {look_angle['elevation_deg']:.1f}° nad horyzontem
4. Jesteś {optimal_pos['distance_from_nadir_km']:.1f} km od punktu pod satelitą
5. Cała strefa widoczności ma {zone['radius_km']:.1f} km promienia
"""
        self.send_message(chat_id, message)
        
        # Wyślij lokalizację gdzie stanąć
        self.send_location(chat_id, optimal_pos['lat'], optimal_pos['lon'])
        
        # Generuj i wyślij mapy jeśli Mapbox dostępny
        if self.map_generator.available:
            # Mapa z pozycją obserwatora i satelitą
            observer_pos = {
                'lat': optimal_pos['lat'],
                'lon': optimal_pos['lon']
            }
            
            sat_pos = {
                'lat': visibility['satellite_position']['lat'],
                'lon': visibility['satellite_position']['lon']
            }
            
            zone_center = {
                'lat': zone['center']['lat'],
                'lon': zone['center']['lon']
            }
            
            visibility_map = self.map_generator.generate_visibility_map(
                observer_pos, sat_pos, zone_center, zone['radius_km']
            )
            
            if visibility_map:
                self.send_photo(chat_id, visibility_map,
                    f"🗺️ Mapa widoczności: {visibility['satellite']}\n"
                    f"🟢 Zielony marker - gdzie stanąć\n"
                    f"🔴 Czerwony marker - satelita nad Tobą\n"
                    f"📏 Zielony okrąg - strefa widoczności ({zone['radius_km']:.1f} km)"
                )
            
            # Mapa z kierunkiem patrzenia
            direction_map = self.map_generator.generate_direction_map(
                observer_pos, look_angle['azimuth_deg']
            )
            
            if direction_map:
                self.send_photo(chat_id, direction_map,
                    f"🧭 Kierunek patrzenia: {look_angle['azimuth_name']}\n"
                    f"🟢 Twoja pozycja\n"
                    f"🔴 Kierunek: {look_angle['azimuth_deg']:.0f}°\n"
                    f"👉 Podążaj za czerwoną linią"
                )
        else:
            self.send_message(chat_id,
                "⚠️ <b>Mapy niedostępne</b>\n\n"
                "Aby zobaczyć mapy, skonfiguruj MAPBOX_API_KEY w environment variables."
            )
    
    def _parse_time(self, time_str: Optional[str]) -> datetime:
        """Parsuj czas z stringa"""
        now = datetime.utcnow()
        
        if not time_str:
            # Domyślnie: za 1 godzinę
            return now + timedelta(hours=1)
        
        try:
            # Format HH:MM
            if ':' in time_str:
                hours, minutes = map(int, time_str.split(':'))
            else:
                hours = int(time_str)
                minutes = 0
            
            # Ustaw na dzisiaj, z podaną godziną
            target = datetime(now.year, now.month, now.day, hours, minutes)
            
            # Jeśli już była dzisiaj, weź jutro
            if target < now:
                target += timedelta(days=1)
            
            return target
        except:
            # W razie błędu: za 1 godzinę
            return now + timedelta(hours=1)
    
    def cmd_next(self, chat_id: int, args: List[str]):
        """Komenda /next - następne okazje"""
        if len(args) < 2:
            self.send_message(chat_id,
                "🔭 <b>Format:</b> <code>/next [satelita] [lokalizacja] [godziny]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/next landsat warszawa</code> - następne 24h\n"
                "<code>/next sentinel krakow 48</code> - następne 48h\n\n"
                "<b>Satelity:</b> landsat, sentinel, iss, worldview\n"
                "<b>Godziny:</b> 1-72 (domyślnie 24)"
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
        
        hours = 24
        if len(args) > 2:
            try:
                hours = min(int(args[2]), 72)
            except:
                pass
        
        self.send_message(chat_id,
            f"🔭 Szukam okazji dla {self.calculator.SATELLITE_CAMERAS[sat_name]['name']}...\n"
            f"📍 {location['name']}\n"
            f"⏰ Następne {hours} godzin"
        )
        
        opportunities = self.calculator.find_next_visibility(
            sat_name, location['lat'], location['lon'], hours
        )
        
        if not opportunities:
            self.send_message(chat_id,
                f"❌ Brak okazji w ciągu {hours}h.\n"
                f"Spróbuj zwiększyć zakres czasowy lub wybierz inny satelitę."
            )
            return
        
        message = f"""
🔭 <b>NASTĘPNE OKAZJE - {self.calculator.SATELLITE_CAMERAS[sat_name]['name'].upper()}</b>
📍 {location['name']} | ⏰ {hours}h
{"="*40}
"""
        
        for i, opp in enumerate(opportunities[:5], 1):
            vis = opp["visibility_info"]
            optimal = vis["optimal_position"]
            
            message += f"\n{i}. 🕐 <b>{opp['local_time']}</b>\n"
            message += f"   📍 {optimal['lat']:.4f}°N, {optimal['lon']:.4f}°E\n"
            message += f"   🧭 {optimal['direction_name']} | 📏 {optimal['distance_from_nadir_km']:.1f}km\n"
            message += f"   🎯 Szansa: {opp['chance_percentage']:.0f}%\n"
            message += f"   👉 <code>/where {sat_name} {loc_name} {opp['local_time'][-5:]}</code>\n"
        
        if len(opportunities) > 5:
            message += f"\n📋 ... i {len(opportunities) - 5} więcej okazji\n"
        
        message += f"\n🎯 <b>UŻYJ:</b> <code>/where {sat_name} {loc_name} [czas]</code>"
        message += f"\ndla szczegółów konkretnej okazji."
        
        self.send_message(chat_id, message)
    
    def cmd_locations(self, chat_id: int):
        """Komenda /locations"""
        message = "📍 <b>DOSTĘPNE LOKALIZACJE:</b>\n\n"
        
        locations_list = list(self.locations.items())
        for i in range(0, len(locations_list), 3):
            chunk = locations_list[i:i+3]
            for key, loc in chunk:
                message += f"• <b>{key}</b> - {loc['name']}\n"
            message += "\n"
        
        message += "🎯 <b>PRZYKŁAD:</b> <code>/where landsat warszawa 15:30</code>"
        self.send_message(chat_id, message)
    
    def cmd_satellites(self, chat_id: int):
        """Komenda /satellites"""
        message = "🛰️ <b>DOSTĘPNE SATELITY:</b>\n\n"
        
        for key, sat in self.calculator.SATELLITE_CAMERAS.items():
            message += f"• <b>{key}</b> - {sat['name']}\n"
            message += f"  📷 {sat['pixel_size_m']}m/px | 📏 {sat['swath_width_km']}km\n"
            message += f"  🎯 Min. elewacja: {sat['min_elevation']}°\n"
            message += f"  👉 <code>/where {key} [lokalizacja] [czas]</code>\n\n"
        
        message += "ℹ️ <b>UWAGA:</b> WorldView-3 ma wąskie pole widzenia (13km) ale wysoką rozdzielczość (0.3m)"
        self.send_message(chat_id, message)

# ====================== FLASK APP ======================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = SatelliteVisibilityBot()

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🛰️ Satellite Visibility Calculator</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0c2461 0%, #1e3799 50%, #4a69bd 100%);
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
            }
            .highlight {
                background: rgba(255, 255, 255, 0.2);
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 5px solid #00ff00;
            }
            .command {
                background: rgba(0, 0, 0, 0.3);
                padding: 10px 15px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
                display: block;
            }
            .telegram-link {
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
            }
            .telegram-link:hover {
                background: #006699;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ Satellite Visibility Calculator</h1>
            <div style="text-align: center; margin-bottom: 30px; font-size: 1.2em;">
                Pokazuje gdzie stanąć żeby być widocznym dla satelity
            </div>
            
            <div class="highlight">
                <b>🎯 NIE POKAZUJE TWOJEJ POZYCJI!</b><br>
                Pokazuje <b>OPTYMALNĄ POZYCJĘ OBSERWACYJNĄ</b> - miejsce gdzie musisz stanąć, 
                aby satelita Cię widział (byłeś w jego polu widzenia).
            </div>
            
            <h3>🚀 JAK TO DZIAŁA:</h3>
            <p>1. Wybierasz satelitę (Landsat, Sentinel, ISS, WorldView)</p>
            <p>2. Wybierasz obszar (Warszawa, Kraków, Gdańsk...)</p>
            <p>3. Podajesz czas obserwacji</p>
            <p>4. System oblicza gdzie stanąć i w którą stronę patrzeć</p>
            
            <h3>📋 GŁÓWNE KOMENDY:</h3>
            <div class="command">/where landsat warszawa 14:30</div>
            <p>Pokazuje gdzie stanąć o 14:30 żeby Landsat Cię widział</p>
            
            <div class="command">/next sentinel krakow 48</div>
            <p>Znajduje następne okazje w ciągu 48h</p>
            
            <div class="command">/locations</div>
            <p>Lista dostępnych lokalizacji</p>
            
            <div class="command">/satellites</div>
            <p>Lista dostępnych satelitów</p>
            
            <h3>📍 PRZYKŁADOWE LOKALIZACJE:</h3>
            <p>warszawa, krakow, gdansk, wroclaw, poznan, bialystok, rzeszow, katowice, 
            szczecin, lodz, lublin, tatry, sudety, mazury, baltyk</p>
            
            <h3>🛰️ SATELITY:</h3>
            <p><b>Landsat 8</b> - 15m/px, szeroki pas 185km (łatwo trafić)</p>
            <p><b>Sentinel-2</b> - 10m/px, bardzo szeroki pas 290km</p>
            <p><b>ISS</b> - Stacja kosmiczna, wąski pas ale niska orbita</p>
            <p><b>WorldView-3</b> - 0.3m/px, wąski pas 13km (trudno trafić)</p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/PcSentinel_Bot" class="telegram-link" target="_blank">
                    💬 Rozpocznij z @PcSentinel_Bot
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
            
            if text.startswith('/'):
                parts = text.split()
                command = parts[0][1:]  # Usuń '/'
                args = parts[1:] if len(parts) > 1 else []
                
                bot.handle_command(chat_id, command, args)
            else:
                bot.send_message(chat_id,
                    "🛰️ <b>Satellite Visibility Calculator</b>\n\n"
                    "Użyj jednej z komend:\n"
                    "<code>/where [satelita] [lokalizacja] [czas]</code>\n"
                    "<code>/next [satelita] [lokalizacja] [godziny]</code>\n"
                    "<code>/locations</code> - lista lokalizacji\n"
                    "<code>/satellites</code> - lista satelitów\n"
                    "<code>/help</code> - pomoc\n\n"
                    "<b>Przykład:</b> <code>/where landsat warszawa 15:30</code>"
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
    print("🛰️ SATELLITE VISIBILITY CALCULATOR v6.7")
    print("=" * 80)
    
    print("🔧 STATUS:")
    print(f"   🤖 Telegram Bot: {'✅ AKTYWNY' if bot.available else '❌ BRAK TOKENA'}")
    print(f"   🗺️ Mapbox API: {'✅ AKTYWNY' if MAPBOX_API_KEY else '⚠️ BRAK'}")
    print(f"   📡 N2YO API: {'✅ AKTYWNY' if N2YO_API_KEY else '⚠️ TRYB SYMULACJI'}")
    print(f"   📍 Lokalizacje: {len(bot.locations)}")
    print(f"   🛰️ Satelity: {len(bot.satellites)}")
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
                print(f"✅ Webhook: {webhook_url}")
            else:
                print(f"⚠️ Błąd webhooka: {response.text}")
        except Exception as e:
            print(f"⚠️ Błąd ustawiania webhooka: {e}")
    
    print("\n🚀 KOMENDY:")
    print("   /where [satelita] [lokalizacja] [czas]")
    print("   /next [satelita] [lokalizacja] [godziny]")
    print("   /locations - lista lokalizacji")
    print("   /satellites - lista satelitów")
    print("\n🎯 PRZYKŁAD:")
    print("   /where landsat warszawa 15:30")
    print("=" * 80)
    
    app.run(host="0.0.0.0", port=PORT, debug=False)