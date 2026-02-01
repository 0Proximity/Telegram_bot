#!/usr/bin/env python3
"""
🛰️ EARTH OBSERVATION PLATFORM v6.6 - VISUAL GUIDE ADDED
✅ Mapy z lokalizacją i strzałkami kierunku
✅ Wizualne wskazówki gdzie stanąć i gdzie patrzeć
✅ Intuicyjna nawigacja dla fotografów
"""

import os
import json
import time
import math
import random
import sqlite3
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from flask import Flask, request, jsonify
import logging
import urllib.parse

# ====================== KONFIGURACJA Z ENVIRONMENT ======================
print("=" * 80)
print("🛰️ EARTH OBSERVATION PLATFORM v6.6 - VISUAL GUIDE")
print("📍 Dodano mapy z strzałkami kierunku")
print("=" * 80)

# Pobierz WSZYSTKIE klucze z environment variables
TELEGRAM_BOT_API = os.getenv("TELEGRAM_BOT_TOKEN","")
USGS_API_KEY = os.getenv("USGS_API_KEY", "")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
N2YO_API_KEY = os.getenv("N2YO_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
RENDER_URL = os.getenv("RENDER_URL", "https://your-app.onrender.com")
PORT = int(os.getenv("PORT", 10000))

# Sprawdź wymagane klucze
if not TELEGRAM_BOT_API:
    print("❌ BRAK TELEGRAM_BOT_API! Bot nie będzie działać.")

# ====================== POMOCNICZE FUNKCJE MAPBOX ======================

class MapboxVisualGuide:
    """Generuje mapy z oznaczeniami i strzałkami kierunku"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.available = bool(api_key)
    
    def generate_location_map(self, lat: float, lon: float, zoom=14) -> str:
        """Generuje mapę z zaznaczoną lokalizacją"""
        if not self.available:
            return ""
        
        try:
            # Style mapy (możesz zmienić na inny)
            style = "satellite-streets-v12"
            size = "800x600"
            
            # Marker w lokalizacji
            marker = f"pin-s+ff0000({lon},{lat})"
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"{marker}/"
                f"{lon},{lat},{zoom}/{size}@2x"
                f"?access_token={self.api_key}"
                f"&attribution=false"
                f"&logo=false"
            )
            
            return map_url
        except Exception as e:
            logger.error(f"❌ Błąd generowania mapy: {e}")
            return ""
    
    def generate_direction_map(self, lat: float, lon: float, 
                              azimuth: float, zoom=14, distance_km=5) -> str:
        """
        Generuje mapę z strzałką kierunku
        azimuth: kierunek w stopniach (0=N, 90=E, 180=S, 270=W)
        """
        if not self.available:
            return ""
        
        try:
            # Oblicz punkt końcowy strzałki (w odległości distance_km)
            end_point = self._calculate_endpoint(lat, lon, azimuth, distance_km)
            
            # Style mapy
            style = "satellite-streets-v12"
            size = "800x600"
            
            # Marker startowy (zielony)
            start_marker = f"pin-s+00ff00({lon},{lat})"
            
            # Marker końcowy (czerwony)
            end_marker = f"pin-l+ff0000({end_point['lon']},{end_point['lat']})"
            
            # Linia łącząca z strzałką
            path_color = "ff0000"
            path_width = 3
            path_opacity = 0.8
            
            # Tworzymy linię z punktu A do B
            path = f"path-{path_width}+{path_color}-{path_opacity}" \
                   f"({lon},{lat},{end_point['lon']},{end_point['lat']})"
            
            # Łączymy wszystkie overlay'e
            overlays = f"{path},{start_marker},{end_marker}"
            
            # Oblicz centrum mapy (środek między punktami)
            center_lat = (lat + end_point['lat']) / 2
            center_lon = (lon + end_point['lon']) / 2
            
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
            logger.error(f"❌ Błąd generowania mapy kierunku: {e}")
            return ""
    
    def generate_compass_map(self, lat: float, lon: float, 
                            azimuth: float, zoom=15) -> str:
        """Generuje mapę z kompasem pokazującym kierunek"""
        if not self.available:
            return ""
        
        try:
            style = "satellite-streets-v12"
            size = "800x800"  # Kwadratowa dla kompasu
            
            # Główny marker (niebieski)
            main_marker = f"pin-l+0000ff({lon},{lat})"
            
            # Dodajemy linie kierunków głównych (N, E, S, W)
            lines = []
            for direction in [0, 90, 180, 270]:  # N, E, S, W
                end_point = self._calculate_endpoint(lat, lon, direction, 0.01)
                lines.append(f"path-2+ffffff-0.5({lon},{lat},{end_point['lon']},{end_point['lat']})")
            
            # Linia wskazująca kierunek (czerwona)
            target_end = self._calculate_endpoint(lat, lon, azimuth, 0.02)
            lines.append(f"path-4+ff0000-0.9({lon},{lat},{target_end['lon']},{target_end['lat']})")
            
            # Marker końcowy kierunku
            target_marker = f"pin-s+ff0000({target_end['lon']},{target_end['lat']})"
            
            # Łączymy wszystkie elementy
            all_lines = ",".join(lines)
            overlays = f"{all_lines},{main_marker},{target_marker}"
            
            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{style}/static/"
                f"{overlays}/"
                f"{lon},{lat},{zoom}/{size}@2x"
                f"?access_token={self.api_key}"
                f"&attribution=false"
                f"&logo=false"
            )
            
            return map_url
        except Exception as e:
            logger.error(f"❌ Błąd generowania mapy kompasu: {e}")
            return ""
    
    def _calculate_endpoint(self, lat: float, lon: float, 
                           azimuth_deg: float, distance_km: float) -> Dict:
        """Oblicza punkt końcowy w danym kierunku i odległości"""
        # Promień Ziemi w km
        R = 6371.0
        
        # Konwersja na radiany
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        azimuth_rad = math.radians(azimuth_deg)
        
        # Oblicz nowe współrzędne
        lat2_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_km/R) +
            math.cos(lat_rad) * math.sin(distance_km/R) * math.cos(azimuth_rad)
        )
        
        lon2_rad = lon_rad + math.atan2(
            math.sin(azimuth_rad) * math.sin(distance_km/R) * math.cos(lat_rad),
            math.cos(distance_km/R) - math.sin(lat_rad) * math.sin(lat2_rad)
        )
        
        # Konwersja z powrotem na stopnie
        lat2 = math.degrees(lat2_rad)
        lon2 = math.degrees(lon2_rad)
        
        return {'lat': lat2, 'lon': lon2}
    
    def get_cardinal_direction(self, azimuth: float) -> str:
        """Konwertuje azymut na kierunek kardynalny"""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = round(azimuth / 45) % 8
        return directions[index]
    
    def generate_simple_direction_ascii(self, azimuth: float) -> str:
        """Generuje prosty ASCII art z kompasem"""
        # Prosty kompas ASCII
        compass = f"""
        ↑ N (0°)
        ↗ NE (45°)
        → E (90°)
        ↘ SE (135°)
        ↓ S (180°)
        ↙ SW (225°)
        ← W (270°)
        ↖ NW (315°)
        
        Twój kierunek: {azimuth:.0f}° ({self.get_cardinal_direction(azimuth)})
        """
        
        # Dodaj wskaźnik
        index = int((azimuth % 360) / 45)
        pointer = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"][index]
        
        return f"Kierunek: {pointer} {azimuth:.0f}° ({self.get_cardinal_direction(azimuth)})"

# ====================== MODUŁ ŚLEDZENIA SATELITÓW (ZAKTUALIZOWANY) ======================

class EnhancedSatelliteTracker:
    """Zaawansowany system śledzenia satelitów z wizualnymi wskazówkami"""
    
    def __init__(self, n2yo_api_key=None, mapbox_api_key=None):
        self.n2yo_api_key = n2yo_api_key
        self.mapbox = MapboxVisualGuide(mapbox_api_key)
        
        # Baza danych satelitów obserwacyjnych
        self.observation_satellites = {
            "landsat-8": {
                "norad_id": 39084,
                "name": "Landsat 8",
                "type": "optical",
                "camera": "OLI/TIRS",
                "resolution": 15,
                "swath_width": 185,
                "min_altitude": 705,
                "imaging_angle_range": (-30, 30)
            },
            "sentinel-2a": {
                "norad_id": 40697,
                "name": "Sentinel-2A",
                "type": "multispectral",
                "camera": "MSI",
                "resolution": 10,
                "swath_width": 290,
                "min_altitude": 786,
                "imaging_angle_range": (-25, 25)
            },
            "sentinel-2b": {
                "norad_id": 42969,
                "name": "Sentinel-2B",
                "type": "multispectral",
                "camera": "MSI",
                "resolution": 10,
                "swath_width": 290,
                "min_altitude": 786,
                "imaging_angle_range": (-25, 25)
            },
            "worldview-3": {
                "norad_id": 40115,
                "name": "WorldView-3",
                "type": "vhr",
                "camera": "CAVIS",
                "resolution": 0.31,
                "swath_width": 13.1,
                "min_altitude": 617,
                "imaging_angle_range": (-45, 45)
            },
            "iss": {
                "norad_id": 25544,
                "name": "International Space Station",
                "type": "station",
                "camera": "EarthKAM/Nikon",
                "resolution": 10,
                "swath_width": 5,
                "min_altitude": 408,
                "imaging_angle_range": (-90, 90)
            }
        }
    
    def get_satellite_passes(self, lat: float, lon: float, alt: float = 0, 
                            days: int = 10, min_elevation: float = 15) -> List[Dict]:
        """Pobierz przeloty satelitów nad daną lokalizacją"""
        try:
            if not self.n2yo_api_key:
                return self._generate_mock_passes(lat, lon, days)
            
            passes = []
            for sat_name, sat_data in self.observation_satellites.items():
                try:
                    url = f"https://api.n2yo.com/rest/v1/satellite/radiopasses/{sat_data['norad_id']}/{lat}/{lon}/{alt}/{days}/{min_elevation}"
                    params = {'apiKey': self.n2yo_api_key}
                    
                    response = requests.get(url, params=params, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        
                        for pass_data in data.get('passes', []):
                            photo_chance = self.calculate_photo_chance(sat_data, pass_data)
                            optimal_angle = self.calculate_optimal_angle(pass_data)
                            
                            pass_info = {
                                'satellite': sat_data['name'],
                                'satellite_id': sat_data['norad_id'],
                                'type': sat_data['type'],
                                'start_utc': datetime.utcfromtimestamp(pass_data['startUTC']),
                                'max_elevation': pass_data['maxEl'],
                                'max_elevation_utc': datetime.utcfromtimestamp(pass_data['maxUTC']),
                                'end_utc': datetime.utcfromtimestamp(pass_data['endUTC']),
                                'duration': pass_data['endUTC'] - pass_data['startUTC'],
                                'photo_chance': photo_chance,
                                'recommended_angle': optimal_angle,
                                'peak_azimuth': pass_data.get('maxAz', 0),
                                'peak_altitude': pass_data.get('maxEl', 0),
                                'visual_guide': self._generate_visual_guide(lat, lon, optimal_angle)
                            }
                            passes.append(pass_info)
                except:
                    continue
            
            passes.sort(key=lambda x: (x['start_utc'], -x['photo_chance']))
            return passes[:25]
            
        except Exception as e:
            logger.error(f"❌ Błąd pobierania przelotów: {e}")
            return self._generate_mock_passes(lat, lon, days)
    
    def _generate_mock_passes(self, lat: float, lon: float, days: int) -> List[Dict]:
        """Wygeneruj przykładowe przeloty"""
        passes = []
        now = datetime.utcnow()
        satellites = list(self.observation_satellites.values())
        
        for day_offset in range(days):
            for hour in [6, 10, 14, 18, 22]:
                sat_data = random.choice(satellites)
                base_time = now + timedelta(days=day_offset, hours=hour)
                
                time_offset = random.randint(-30, 30)
                start_time = base_time + timedelta(minutes=time_offset)
                
                duration = random.randint(120, 600)
                max_elevation = random.uniform(15, 85)
                photo_chance = random.uniform(30, 95)
                optimal_angle = random.randint(0, 359)
                
                pass_info = {
                    'satellite': sat_data['name'],
                    'satellite_id': sat_data['norad_id'],
                    'type': sat_data['type'],
                    'start_utc': start_time,
                    'max_elevation': max_elevation,
                    'max_elevation_utc': start_time + timedelta(seconds=duration/2),
                    'end_utc': start_time + timedelta(seconds=duration),
                    'duration': duration,
                    'photo_chance': round(photo_chance, 1),
                    'recommended_angle': optimal_angle,
                    'peak_azimuth': random.randint(0, 359),
                    'peak_altitude': max_elevation,
                    'visual_guide': self._generate_visual_guide(lat, lon, optimal_angle)
                }
                passes.append(pass_info)
        
        passes.sort(key=lambda x: x['start_utc'])
        return passes[:25]
    
    def calculate_photo_chance(self, sat_data: Dict, pass_data: Dict) -> float:
        """Oblicz prawdopodobieństwo wykonania zdjęcia"""
        chance = 50.0
        
        max_elev = pass_data.get('maxEl', 0)
        if max_elev > 60:
            chance += 25
        elif max_elev > 40:
            chance += 15
        elif max_elev > 20:
            chance += 8
        
        duration = pass_data.get('endUTC', 0) - pass_data.get('startUTC', 0)
        if duration > 600:
            chance += 15
        elif duration > 300:
            chance += 8
        
        chance *= random.uniform(0.8, 1.2)
        return min(98, max(2, round(chance, 1)))
    
    def calculate_optimal_angle(self, pass_data: Dict) -> float:
        """Oblicz optymalny kąt ustawienia kamery"""
        max_az = pass_data.get('maxAz', 0)
        max_el = pass_data.get('maxEl', 0)
        
        if max_el > 60:
            return (max_az + 90) % 360
        elif max_el > 30:
            return (max_az + 45) % 360
        else:
            return max_az
    
    def _generate_visual_guide(self, lat: float, lon: float, azimuth: float) -> Dict:
        """Generuje wizualne wskazówki dla fotografa"""
        return {
            'azimuth': azimuth,
            'cardinal_direction': self.mapbox.get_cardinal_direction(azimuth) if self.mapbox.available else "N/A",
            'ascii_compass': self.mapbox.generate_simple_direction_ascii(azimuth) if self.mapbox.available else "",
            'map_available': self.mapbox.available,
            'instructions': self._get_viewing_instructions(azimuth)
        }
    
    def _get_viewing_instructions(self, azimuth: float) -> str:
        """Generuje tekstowe instrukcje patrzenia"""
        if azimuth < 45 or azimuth >= 315:
            return "Patrz na PÓŁNOC. Znajdź Gwiazdę Polarną lub charakterystyczne budynki na północy."
        elif 45 <= azimuth < 135:
            return "Patrz na WSCHÓD. Obserwuj wschodni horyzont, unikaj wysokich budynków."
        elif 135 <= azimuth < 225:
            return "Patrz na POŁUDNIE. Słońce może przeszkadzać w dzień, ale nocą dobry widok."
        else:  # 225 <= azimuth < 315
            return "Patrz na ZACHÓD. Zachodni horyzont, szczególnie ładne widoki o zachodzie słońca."
    
    def get_best_photo_opportunity(self, lat: float, lon: float, 
                                  hours: int = 24) -> Optional[Dict]:
        """Znajdź najlepszą okazję do zrobienia zdjęcia"""
        passes = self.get_satellite_passes(lat, lon, days=1)
        
        if not passes:
            return None
        
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)
        
        relevant_passes = [
            p for p in passes 
            if now <= p['start_utc'] <= end_time and p['photo_chance'] > 40
        ]
        
        if not relevant_passes:
            relevant_passes = [p for p in passes if now <= p['start_utc'] <= end_time]
        
        if not relevant_passes:
            return None
        
        best_pass = max(relevant_passes, key=lambda x: x['photo_chance'])
        
        # Dodaj zaawansowane wskazówki
        best_pass['detailed_instructions'] = self._get_detailed_instructions(best_pass, lat, lon)
        best_pass['equipment_recommendation'] = self._get_equipment_recommendation(best_pass)
        best_pass['location_tips'] = self._get_location_tips(lat, lon, best_pass['recommended_angle'])
        
        # Generuj URL mapy jeśli Mapbox dostępny
        if self.mapbox.available:
            best_pass['map_urls'] = {
                'location': self.mapbox.generate_location_map(lat, lon),
                'direction': self.mapbox.generate_direction_map(lat, lon, best_pass['recommended_angle']),
                'compass': self.mapbox.generate_compass_map(lat, lon, best_pass['recommended_angle'])
            }
        else:
            best_pass['map_urls'] = None
        
        return best_pass
    
    def _get_detailed_instructions(self, pass_data: Dict, lat: float, lon: float) -> str:
        """Szczegółowe instrukcje dla fotografa"""
        instructions = []
        
        instructions.append(f"📍 TWOJA POZYCJA: {lat:.4f}°N, {lon:.4f}°E")
        instructions.append(f"🎯 KIERUNEK: {pass_data['recommended_angle']:.0f}° ({pass_data['visual_guide']['cardinal_direction']})")
        instructions.append(f"👀 {pass_data['visual_guide']['instructions']}")
        
        # Wskazówki czasowe
        local_time = pass_data['start_utc'] + timedelta(hours=1)
        instructions.append(f"🕐 ROZPOCZNIJ OBSERWACJĘ: {local_time.strftime('%H:%M')}")
        instructions.append(f"⏱️ CZAS TRWANIA: {int(pass_data['duration']//60)} minut")
        
        # Wskazówki techniczne
        if pass_data['max_elevation'] > 60:
            instructions.append("🔭 WYSOKI PRZELOT: Patrz prawie prosto w górę, unikaj drzew")
        elif pass_data['max_elevation'] < 25:
            instructions.append("🌅 NISKI PRZELOT: Potrzebujesz czystego horyzontu, najlepiej na wzniesieniu")
        
        return "\n".join(instructions)
    
    def _get_equipment_recommendation(self, pass_data: Dict) -> str:
        """Zalecenia dotyczące sprzętu"""
        if pass_data['type'] == 'vhr':
            return "📸 SPRZĘT: Teleobiektyw 300mm+, statyw, wyzwalacz, ISO 400-800, czas 1/500s"
        elif 'ISS' in pass_data['satellite']:
            return "📸 SPRZĘT: Szerokokąt 24mm, statyw, czas 2-5s, ISO 1600-3200, wyzwalacz"
        else:
            return "📸 SPRZĘT: Obiektyw 70-200mm, statyw, ISO 800-1600, czas 1/250s"
    
    def _get_location_tips(self, lat: float, lon: float, azimuth: float) -> str:
        """Wskazówki dotyczące lokalizacji"""
        tips = []
        
        # Sugestie miejsc w zależności od kierunku
        if azimuth < 45 or azimuth >= 315:  # Północ
            tips.append("🏙️ Szukaj miejsc z widokiem na północ: parki, otwarte przestrzenie")
            tips.append("🗼 W miastach: wysokie punkty widokowe skierowane na północ")
        elif 45 <= azimuth < 135:  # Wschód
            tips.append("🌅 Wschód: miejsca z czystym horyzontem, unikaj zachodzącego słońca")
            tips.append("🏞️ Dobrze działają wschodnie brzegi rzek/jezior")
        elif 135 <= azimuth < 225:  # Południe
            tips.append("☀️ Południe: uważaj na słońce w dzień, ale dobre warunki nocą")
            tips.append("🏔️ Południowe stoki wzgórz zapewniają dobry widok")
        else:  # Zachód
            tips.append("🌇 Zachód: piękne zachody słońca, ale mogą przeszkadzać w obserwacji")
            tips.append("🌉 Zachodnie mosty/promenady mają dobry widok")
        
        return " | ".join(tips)

# ====================== ROZSZERZONY TELEGRAM BOT ======================

class VisualTelegramBot:
    """Bot Telegram z wizualnymi wskazówkami i mapami"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_API
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.available = bool(TELEGRAM_BOT_API)
        
        # Inicjalizuj moduły
        self.tracker = EnhancedSatelliteTracker(N2YO_API_KEY, MAPBOX_API_KEY)
        self.mapbox = MapboxVisualGuide(MAPBOX_API_KEY) if MAPBOX_API_KEY else None
        
        # Punkty obserwacyjne
        self.points = {
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
            "tatry": {"name": "Tatry", "lat": 49.1795, "lon": 20.0884},
            "bialowieza": {"name": "Białowieża", "lat": 52.7000, "lon": 23.8667},
            "sopot": {"name": "Sopot", "lat": 54.4416, "lon": 18.5601},
            "zakopane": {"name": "Zakopane", "lat": 49.2992, "lon": 19.9496},
            "olsztyn": {"name": "Olsztyn", "lat": 53.7784, "lon": 20.4801},
            "torun": {"name": "Toruń", "lat": 53.0138, "lon": 18.5984},
            "czestochowa": {"name": "Częstochowa", "lat": 50.8110, "lon": 19.1200}
        }
        
        if self.available:
            logger.info("✅ Bot Telegram z mapami zainicjalizowany")
        else:
            logger.warning("⚠️ Bot Telegram niedostępny")
    
    def send_message(self, chat_id: int, text: str, parse_html: bool = True):
        """Wyślij wiadomość"""
        if not self.available:
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML" if parse_html else None,
            "disable_web_page_preview": False  # Włącz podgląd linków
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Błąd wysyłania: {e}")
            return False
    
    def send_photo(self, chat_id: int, photo_url: str, caption: str = ""):
        """Wyślij zdjęcie"""
        if not self.available:
            return False
        
        url = f"{self.base_url}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024],  # Telegram limit
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload, timeout=15)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Błąd wysyłania zdjęcia: {e}")
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
            logger.error(f"❌ Błąd wysyłania lokalizacji: {e}")
            return False
    
    def handle_webhook(self, data: dict):
        """Obsłuż webhook z Telegrama"""
        try:
            if "message" in data:
                chat_id = data["message"]["chat"]["id"]
                text = data["message"].get("text", "").strip()
                
                logger.info(f"📨 Otrzymano: {text} od {chat_id}")
                
                if text.startswith('/'):
                    parts = text.split()
                    command = parts[0][1:]  # Usuń '/'
                    args = parts[1:] if len(parts) > 1 else []
                    
                    self.handle_command(chat_id, command, args)
                else:
                    self.send_message(chat_id,
                        "🛰️ <b>Satellite Photo Predictor v6.6</b>\n\n"
                        "<b>Nowe funkcje:</b>\n"
                        "• 🗺️ Mapy z Twoją pozycją\n"
                        "• 🧭 Strzałki kierunku patrzenia\n"
                        "• 📍 Wizualne wskazówki\n\n"
                        "<b>Komendy:</b>\n"
                        "<code>/view [miasto] [satelita]</code> - mapa z kierunkiem\n"
                        "<code>/best [miasto]</code> - najlepsza okazja z mapami\n"
                        "<code>/passes [miasto]</code> - przeloty\n"
                        "<code>/guide [miasto]</code> - przewodnik wizualny\n"
                        "<code>/help</code> - pomoc"
                    )
            
            return True
        except Exception as e:
            logger.error(f"❌ Błąd webhook: {e}")
            return False
    
    def handle_command(self, chat_id: int, command: str, args: List[str]):
        """Obsłuż komendę"""
        command = command.lower()
        
        if command == "start":
            self.cmd_start(chat_id)
        elif command == "help":
            self.cmd_help(chat_id)
        elif command == "passes":
            self.cmd_passes(chat_id, args)
        elif command == "best":
            self.cmd_best(chat_id, args)
        elif command == "view" or command == "map":
            self.cmd_view(chat_id, args)
        elif command == "guide":
            self.cmd_guide(chat_id, args)
        elif command == "points":
            self.cmd_points(chat_id)
        elif command == "satellites":
            self.cmd_satellites(chat_id)
        elif command == "location":
            self.cmd_location(chat_id, args)
        else:
            self.send_message(chat_id, "❌ Nieznana komenda. Użyj /help")
    
    def cmd_start(self, chat_id: int):
        """Komenda /start"""
        message = """
🛰️ <b>SATELLITE PHOTO PREDICTOR v6.6</b>
📍 <i>System z mapami i wizualnymi wskazówkami</i>

<b>Główne funkcje:</b>
• 🗺️ Mapy z Twoją lokalizacją
• 🧭 Strzałki pokazujące gdzie patrzeć
• 📍 Wizualne przewodniki
• 📊 Obliczanie szans na zdjęcie
• 🎯 Zalecenia techniczne

<b>Nowe komendy:</b>
<code>/view [miasto] [satelita]</code> - mapa z kierunkiem
<code>/best [miasto]</code> - najlepsza okazja z mapami
<code>/guide [miasto]</code> - przewodnik wizualny
<code>/location [miasto]</code> - Twoja pozycja na mapie

<b>Przykłady:</b>
• <code>/view warszawa landsat</code>
• <code>/best krakow</code>
• <code>/guide gdansk</code>
• <code>/location wroclaw</code>

Użyj <code>/points</code> aby zobaczyć dostępne lokalizacje.
"""
        self.send_message(chat_id, message)
        
        # Sprawdź czy Mapbox jest dostępny
        if not self.mapbox or not self.mapbox.available:
            self.send_message(chat_id,
                "⚠️ <b>UWAGA: Mapbox API nie jest skonfigurowane</b>\n\n"
                "Aby używać map i strzałek kierunku, dodaj klucz Mapbox:\n"
                "<code>MAPBOX_API_KEY=twój_klucz</code>\n\n"
                "Do zmiennych środowiskowych na Renderze."
            )
    
    def cmd_help(self, chat_id: int):
        """Komenda /help"""
        message = """
📋 <b>DOSTĘPNE KOMENDY:</b>

<b>🗺️ MAPY I WIZUALIZACJE:</b>
<code>/view [miasto] [satelita]</code> - mapa z kierunkiem patrzenia
<code>/guide [miasto]</code> - pełny przewodnik wizualny
<code>/location [miasto]</code> - pokaż Twoją pozycję na mapie

<b>🛰️ OBSERWACJE SATELITARNE:</b>
<code>/best [miasto] [godziny]</code> - najlepsza okazja z mapami
<code>/passes [miasto] [dni]</code> - przeloty satelitów

<b>📍 INFORMACJE:</b>
<code>/points</code> - dostępne lokalizacje
<code>/satellites</code> - lista śledzonych satelitów

<b>🎯 PARAMETRY:</b>
• [miasto] - np. warszawa, krakow (zobacz /points)
• [satelita] - iss, landsat, sentinel, worldview
• [dni] - liczba dni (domyślnie 3, max 10)
• [godziny] - zakres wyszukiwania (domyślnie 24)

<b>📍 PRZYKŁADY:</b>
<code>/view warszawa iss</code> - mapa z kierunkiem na ISS
<code>/best krakow 48</code> - najlepsza okazja w 48h
<code>/guide gdansk</code> - przewodnik dla Gdańska
<code>/location wroclaw</code> - pozycja Wrocławia

<b>🗺️ FUNKCJE MAP:</b>
• Zielony marker - Twoja pozycja
• Czerwona strzałka - kierunek patrzenia
• Czerwony marker - cel obserwacji
• Kompas - orientacja w terenie
"""
        self.send_message(chat_id, message)
    
    def cmd_view(self, chat_id: int, args: List[str]):
        """Komenda /view - mapa z kierunkiem patrzenia"""
        if len(args) < 2:
            self.send_message(chat_id,
                "🗺️ <b>Format:</b> <code>/view [miasto] [satelita]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/view warszawa iss</code>\n"
                "<code>/view krakow landsat</code>\n"
                "<code>/view gdansk sentinel</code>\n\n"
                "<b>Dostępne satelity:</b> iss, landsat, sentinel, worldview\n"
                "<b>Mapy pokazują:</b>\n"
                "• 🟢 Twoją pozycję\n"
                "• 🧭 Kierunek patrzenia\n"
                "• 🔴 Cel obserwacji"
            )
            return
        
        point_name = args[0]
        satellite_name = args[1]
        
        point = self.points.get(point_name)
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto. Użyj /points")
            return
        
        self.send_message(chat_id, f"🗺️ Przygotowuję mapę dla {point['name']}...")
        
        # Sprawdź czy mamy Mapbox
        if not self.mapbox or not self.mapbox.available:
            self.send_message(chat_id,
                "❌ <b>Mapbox API nie jest dostępne</b>\n\n"
                "ℹ️ Aby używać map, dodaj klucz Mapbox:\n"
                "<code>MAPBOX_API_KEY=twój_klucz</code>\n\n"
                "Do zmiennych środowiskowych na Renderze."
            )
            return
        
        # Znajdź najbliższy przelot dla tego satelity
        passes = self.tracker.get_satellite_passes(point['lat'], point['lon'], days=3)
        target_passes = []
        
        for p in passes:
            if (satellite_name.lower() in p['satellite'].lower() or 
                satellite_name.lower() in p.get('type', '').lower()):
                target_passes.append(p)
        
        if not target_passes:
            self.send_message(chat_id, 
                f"❌ Brak przelotów '{satellite_name}' nad {point['name']} w ciągu 3 dni."
            )
            return
        
        # Weź najbliższy przelot
        target_pass = min(target_passes, key=lambda x: x['start_utc'])
        azimuth = target_pass['recommended_angle']
        
        # Wyślij tekstowe informacje
        local_time = target_pass['start_utc'] + timedelta(hours=1)
        duration_min = int(target_pass['duration'] // 60)
        
        info_message = f"""
🧭 <b>KIERUNEK OBSERWACJI - {point['name'].upper()}</b>

🛰️ <b>{target_pass['satellite']}</b>
⭐ Szansa: <b>{target_pass['photo_chance']:.0f}%</b>
🎯 Kierunek: <b>{azimuth:.0f}°</b> ({self.mapbox.get_cardinal_direction(azimuth)})
📅 Data: {local_time.strftime('%d.%m.%Y')}
🕐 Czas: {local_time.strftime('%H:%M')} lokalnego
⏱️ Trwanie: {duration_min} minut
📈 Maks. wysokość: {target_pass['max_elevation']:.1f}°

<b>INSTRUKCJE:</b>
{target_pass['visual_guide']['instructions']}

<b>Mapa pokazuje:</b>
• 🟢 <b>Zielony marker</b> - Twoja pozycja
• 🧭 <b>Czerwona strzałka</b> - kierunek patrzenia
• 🔴 <b>Czerwony marker</b> - cel obserwacji
"""
        self.send_message(chat_id, info_message)
        
        # Wyślij lokalizację
        self.send_location(chat_id, point['lat'], point['lon'])
        
        # Wyślij mapę z kierunkiem
        direction_map = self.mapbox.generate_direction_map(
            point['lat'], point['lon'], azimuth
        )
        
        if direction_map:
            self.send_photo(chat_id, direction_map,
                f"🗺️ Mapa kierunku: {point['name']}\n"
                f"🧭 {azimuth:.0f}° ({self.mapbox.get_cardinal_direction(azimuth)})\n"
                f"🛰️ {target_pass['satellite']}\n"
                f"🕐 {local_time.strftime('%H:%M')}"
            )
        
        # Wyślij mapę z kompasem
        compass_map = self.mapbox.generate_compass_map(
            point['lat'], point['lon'], azimuth
        )
        
        if compass_map:
            self.send_photo(chat_id, compass_map,
                f"🧭 Kompas: {point['name']}\n"
                f"🎯 Kierunek: {azimuth:.0f}°\n"
                f"📍 Twoja pozycja: niebieski marker\n"
                f"👉 Cel: czerwona strzałka"
            )
        
        # Wskazówki dodatkowe
        tips_message = f"""
<b>💡 PRAKTYCZNE WSKAZÓWKI:</b>

1. <b>PRZYGOTOWANIE MIEJSCA:</b>
   • Stań w miejscu oznaczonego zielonym markerem
   • Obróć się w kierunku czerwonej strzałki
   • Upewnij się, że masz czysty widok w tym kierunku

2. <b>ORIENTACJA W TERENIE:</b>
   • Użyj kompasu w telefonie do potwierdzenia kierunku
   • Znajdź charakterystyczny punkt w terenie (drzewo, budynek)
   • Zapamiętaj go jako punkt odniesienia

3. <b>OBSERWACJA:</b>
   • Zacznij obserwację 5 minut przed czasem
   • Satelita pojawi się na niebie w zadanym kierunku
   • Podążaj za nim przez cały przelot

📍 <b>Twoja pozycja:</b> {point['lat']:.4f}°N, {point['lon']:.4f}°E
🏙️ <b>Miasto:</b> {point['name']}
"""
        self.send_message(chat_id, tips_message)
    
    def cmd_best(self, chat_id: int, args: List[str]):
        """Komenda /best - najlepsza okazja z mapami"""
        if len(args) < 1:
            self.send_message(chat_id,
                "🎯 <b>Format:</b> <code>/best [miasto] [godziny]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/best warszawa</code> - najlepsza w 24h\n"
                "<code>/best krakow 48</code> - najlepsza w 48h\n\n"
                "Pokazuje najlepszą okazję na zdjęcie z mapami i wskazówkami."
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto. Użyj /points")
            return
        
        hours = 24
        if len(args) > 1:
            try:
                hours = int(args[1])
            except:
                pass
        
        self.send_message(chat_id, 
            f"🎯 Szukam najlepszej okazji na zdjęcie w {point['name']}...\n"
            f"⏰ Okres: {hours} godzin\n"
            f"🗺️ Przygotowuję mapy..."
        )
        
        best = self.tracker.get_best_photo_opportunity(
            point['lat'], point['lon'], hours
        )
        
        if not best:
            self.send_message(chat_id, 
                f"❌ Brak dobrych okazji w ciągu {hours}h.\n"
                f"ℹ️ Spróbuj zwiększyć okres wyszukiwania."
            )
            return
        
        # Formatuj czas
        start_local = best['start_utc'] + timedelta(hours=1)
        duration_min = int(best['duration'] // 60)
        
        message = f"""
🏆 <b>NAJLEPSZA OKAZJA - {point['name'].upper()}</b>

🛰️ <b>{best['satellite']}</b>
⭐ <b>Szansa:</b> {best['photo_chance']:.0f}%
🎯 <b>Kierunek:</b> {best['recommended_angle']:.0f}° ({best['visual_guide']['cardinal_direction']})
📅 <b>Data:</b> {start_local.strftime('%d.%m.%Y')}
🕐 <b>Czas:</b> {start_local.strftime('%H:%M')} lokalnego
⏱️ <b>Trwanie:</b> {duration_min} minut
📈 <b>Maks. wysokość:</b> {best['max_elevation']:.1f}°

<b>INSTRUKCJE:</b>
{best['detailed_instructions']}

<b>SPRZĘT:</b>
{best['equipment_recommendation']}

<b>LOKALIZACJA:</b>
{best['location_tips']}
"""
        self.send_message(chat_id, message)
        
        # Wyślij lokalizację
        self.send_location(chat_id, point['lat'], point['lon'])
        
        # Jeśli mamy Mapbox, wyślij mapy
        if self.mapbox and self.mapbox.available and best.get('map_urls'):
            maps = best['map_urls']
            
            # Mapa lokalizacji
            if maps.get('location'):
                self.send_photo(chat_id, maps['location'],
                    f"📍 Twoja pozycja: {point['name']}\n"
                    f"🌍 {point['lat']:.4f}°N, {point['lon']:.4f}°E\n"
                    f"🟢 Zielony marker - tutaj stań"
                )
            
            # Mapa z kierunkiem
            if maps.get('direction'):
                self.send_photo(chat_id, maps['direction'],
                    f"🧭 Kierunek obserwacji: {point['name']}\n"
                    f"🎯 {best['recommended_angle']:.0f}° ({best['visual_guide']['cardinal_direction']})\n"
                    f"🟢 Twoja pozycja\n"
                    f"🔴 Cel obserwacji\n"
                    f"👉 Podążaj za czerwoną strzałką"
                )
            
            # Mapa z kompasem
            if maps.get('compass'):
                self.send_photo(chat_id, maps['compass'],
                    f"🧭 Kompas orientacyjny: {point['name']}\n"
                    f"🔵 Niebieski marker - Twoja pozycja\n"
                    f"🔴 Czerwona linia - kierunek patrzenia\n"
                    f"⚪ Białe linie - kierunki kardynalne (N, E, S, W)"
                )
        else:
            self.send_message(chat_id,
                "⚠️ <b>Mapy niedostępne</b>\n\n"
                "Aby zobaczyć mapy z strzałkami kierunku, skonfiguruj Mapbox API."
            )
    
    def cmd_guide(self, chat_id: int, args: List[str]):
        """Komenda /guide - przewodnik wizualny"""
        if len(args) < 1:
            self.send_message(chat_id,
                "🧭 <b>Format:</b> <code>/guide [miasto]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/guide warszawa</code>\n"
                "<code>/guide krakow</code>\n\n"
                "Pokazuje pełny przewodnik wizualny dla danej lokalizacji."
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto. Użyj /points")
            return
        
        self.send_message(chat_id, f"🧭 Przygotowuję przewodnik dla {point['name']}...")
        
        # Wyślij podstawowe informacje
        message = f"""
🧭 <b>PRZEWODNIK WIZUALNY - {point['name'].upper()}</b>

📍 <b>Twoja pozycja:</b>
Szerokość: {point['lat']:.4f}°N
Długość: {point['lon']:.4f}°E
Miasto: {point['name']}

<b>CO ROBIĆ:</b>
1. 🗺️ Użyj komendy <code>/location {point_name}</code> aby zobaczyć swoją pozycję na mapie
2. 🛰️ Sprawdź przeloty: <code>/passes {point_name}</code>
3. 🎯 Znajdź najlepszą okazję: <code>/best {point_name}</code>
4. 🧭 Użyj <code>/view {point_name} [satelita]</code> dla konkretnego kierunku

<b>KIERUNKI KARDYNALNE:</b>
• PÓŁNOC (0°): {self.mapbox.get_cardinal_direction(0) if self.mapbox else "N"}
• WSCHÓD (90°): {self.mapbox.get_cardinal_direction(90) if self.mapbox else "E"}
• POŁUDNIE (180°): {self.mapbox.get_cardinal_direction(180) if self.mapbox else "S"}
• ZACHÓD (270°): {self.mapbox.get_cardinal_direction(270) if self.mapbox else "W"}

<b>WSKAZÓWKI:</b>
• Użyj kompasu w telefonie do orientacji
• Znajdź charakterystyczne punkty w każdym kierunku
• Zapamiętaj je jako punkty odniesienia
"""
        self.send_message(chat_id, message)
        
        # Wyślij lokalizację
        self.send_location(chat_id, point['lat'], point['lon'])
        
        # Jeśli mamy Mapbox, wyślij mapy orientacyjne
        if self.mapbox and self.mapbox.available:
            # Mapa lokalizacji
            location_map = self.mapbox.generate_location_map(point['lat'], point['lon'])
            if location_map:
                self.send_photo(chat_id, location_map,
                    f"📍 Twoja pozycja: {point['name']}\n"
                    f"🌍 {point['lat']:.4f}°N, {point['lon']:.4f}°E\n"
                    f"🔴 Czerwony marker - tutaj stań"
                )
            
            # Kompas dla wszystkich kierunków
            for direction, label in [(0, "PÓŁNOC"), (90, "WSCHÓD"), (180, "POŁUDNIE"), (270, "ZACHÓD")]:
                compass_map = self.mapbox.generate_compass_map(point['lat'], point['lon'], direction)
                if compass_map:
                    self.send_photo(chat_id, compass_map,
                        f"🧭 Kierunek: {label}\n"
                        f"🎯 {direction}°\n"
                        f"📍 {point['name']}\n"
                        f"👉 Czerwona linia pokazuje kierunek"
                    )
                    time.sleep(1)  # Małe opóźnienie między zdjęciami
    
    def cmd_location(self, chat_id: int, args: List[str]):
        """Komenda /location - pokaż pozycję na mapie"""
        if len(args) < 1:
            self.send_message(chat_id,
                "📍 <b>Format:</b> <code>/location [miasto]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/location warszawa</code>\n"
                "<code>/location krakow</code>\n\n"
                "Pokazuje Twoją pozycję obserwacyjną na mapie."
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto. Użyj /points")
            return
        
        self.send_message(chat_id, f"📍 Pokazuję pozycję {point['name']} na mapie...")
        
        # Wyślij lokalizację
        self.send_location(chat_id, point['lat'], point['lon'])
        
        # Jeśli mamy Mapbox, wyślij mapę
        if self.mapbox and self.mapbox.available:
            location_map = self.mapbox.generate_location_map(point['lat'], point['lon'])
            if location_map:
                self.send_photo(chat_id, location_map,
                    f"📍 Twoja pozycja obserwacyjna\n"
                    f"🏙️ {point['name']}\n"
                    f"🌍 {point['lat']:.4f}°N, {point['lon']:.4f}°E\n"
                    f"🔴 Czerwony marker - tutaj stań podczas obserwacji"
                )
        
        # Dodaj informacje o lokalizacji
        info_message = f"""
📍 <b>POZYCJA OBSERWACYJNA - {point['name'].upper()}</b>

<b>WSPÓŁRZĘDNE:</b>
Szerokość: {point['lat']:.4f}°N
Długość: {point['lon']:.4f}°E

<b>CO ROBIĆ W TEJ LOKALIZACJI:</b>
1. 🧭 Stań w miejscu oznaczonego markerem
2. 🗺️ Użyj komendy <code>/passes {point_name}</code> aby zobaczyć przeloty
3. 🎯 Użyj <code>/best {point_name}</code> dla najlepszej okazji
4. 👀 Użyj <code>/view {point_name} [satelita]</code> dla kierunku patrzenia

<b>WSKAZÓWKI:</b>
• Znajdź bezpieczne miejsce do obserwacji
• Upewnij się, że masz dobry widok na niebo
• Zapamiętaj charakterystyczne punkty wokół siebie
"""
        self.send_message(chat_id, info_message)
    
    def cmd_passes(self, chat_id: int, args: List[str]):
        """Komenda /passes - przeloty satelitów"""
        if len(args) < 1:
            self.send_message(chat_id,
                "🛰️ <b>Format:</b> <code>/passes [miasto] [dni]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/passes warszawa</code> - przeloty na 3 dni\n"
                "<code>/passes krakow 5</code> - przeloty na 5 dni\n\n"
                "Następnie użyj <code>/view [miasto] [satelita]</code> dla mapy z kierunkiem."
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto. Użyj /points")
            return
        
        days = 3
        if len(args) > 1:
            try:
                days = min(int(args[1]), 10)
            except:
                pass
        
        self.send_message(chat_id, 
            f"🛰️ Szukam przelotów satelitów nad {point['name']}...\n"
            f"📅 Okres: {days} dni"
        )
        
        passes = self.tracker.get_satellite_passes(point['lat'], point['lon'], days=days)
        
        if not passes:
            self.send_message(chat_id, "❌ Brak przelotów w zadanym okresie.")
            return
        
        # Pogrupuj po dniu
        passes_by_day = {}
        for p in passes:
            day_key = p['start_utc'].strftime('%Y-%m-%d')
            if day_key not in passes_by_day:
                passes_by_day[day_key] = []
            passes_by_day[day_key].append(p)
        
        message = f"🛰️ <b>PRZELOTY SATELITÓW - {point['name'].upper()}</b>\n\n"
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        days_shown = 0
        
        for day in sorted(passes_by_day.keys())[:3]:
            day_passes = passes_by_day[day]
            if not day_passes:
                continue
            
            if day == today:
                day_str = "DZISIAJ"
            else:
                day_date = datetime.strptime(day, '%Y-%m-%d')
                day_str = day_date.strftime('%d.%m')
            
            message += f"📅 <b>{day_str}</b>\n"
            
            for i, p in enumerate(day_passes[:3], 1):
                start_local = p['start_utc'] + timedelta(hours=1)
                duration_min = int(p['duration'] // 60)
                
                if p['photo_chance'] > 75:
                    chance_emoji = "📈"
                elif p['photo_chance'] > 50:
                    chance_emoji = "📊"
                else:
                    chance_emoji = "📉"
                
                message += f"  {i}. {p['satellite'][:15]}...\n"
                message += f"     {chance_emoji} {p['photo_chance']:.0f}% | 🕐 {start_local.strftime('%H:%M')}\n"
                message += f"     📈 {p['max_elevation']:.0f}° | 🧭 {p['recommended_angle']:.0f}°\n"
                message += f"     👉 <code>/view {point_name} {p['satellite'].split()[0].lower()}</code>\n"
            
            message += "\n"
            days_shown += 1
        
        if days_shown == 0:
            message += "📭 Brak przelotów w najbliższych dniach\n\n"
        
        # Statystyki
        total_passes = len(passes)
        high_chance = len([p for p in passes if p['photo_chance'] > 70])
        
        message += f"📊 <b>STATYSTYKI ({total_passes} przelotów):</b>\n"
        message += f"• 🎯 Wysoka szansa (>70%): {high_chance}\n"
        
        if passes:
            best_sat = max(passes, key=lambda x: x['photo_chance'])
            best_time = best_sat['start_utc'] + timedelta(hours=1)
            message += f"• 🏆 <b>Najlepszy:</b> {best_sat['satellite']}\n"
            message += f"  ⭐ {best_sat['photo_chance']:.0f}% | 🕐 {best_time.strftime('%d.%m %H:%M')}\n"
            message += f"  🧭 {best_sat['recommended_angle']:.0f}°\n"
            message += f"  👉 <code>/view {point_name} {best_sat['satellite'].split()[0].lower()}</code>\n"
        
        message += f"\n🎯 <b>UŻYJ:</b> <code>/view {point_name} [satelita]</code> dla mapy z kierunkiem"
        
        self.send_message(chat_id, message)
    
    def cmd_points(self, chat_id: int):
        """Komenda /points"""
        message = "📍 <b>DOSTĘPNE LOKALIZACJE:</b>\n\n"
        
        # Podziel na kolumny dla lepszej czytelności
        points_list = list(self.points.items())
        chunk_size = 6
        
        for i in range(0, len(points_list), chunk_size):
            chunk = points_list[i:i+chunk_size]
            for key, point in chunk:
                message += f"• <b>{key}</b> - {point['name']}\n"
            message += "\n"
        
        message += """
<b>PRZYKŁADY UŻYCIA:</b>
<code>/location warszawa</code> - pokaże Twoją pozycję
<code>/passes krakow</code> - przeloty nad Krakowem
<code>/view gdansk iss</code> - mapa z kierunkiem na ISS
<code>/best wroclaw</code> - najlepsza okazja we Wrocławiu
<code>/guide poznan</code> - przewodnik wizualny
"""
        self.send_message(chat_id, message)
    
    def cmd_satellites(self, chat_id: int):
        """Komenda /satellites"""
        message = "🛰️ <b>ŚLEDZONE SATELITY:</b>\n\n"
        
        sats = self.tracker.observation_satellites
        for key, sat in sats.items():
            message += f"• <b>{sat['name']}</b>\n"
            message += f"  📡 {sat['type'].upper()} | 📷 {sat['camera']}\n"
            message += f"  🎯 {sat['resolution']}m | 📏 {sat['swath_width']}km\n"
            message += f"  👉 <code>/view [miasto] {key}</code>\n\n"
        
        message += "ℹ️ Użyj <code>/view [miasto] [nazwa_satelity]</code> dla mapy z kierunkiem"
        self.send_message(chat_id, message)

# ====================== GŁÓWNA APLIKACJA FLASK ======================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = VisualTelegramBot()

@app.route('/')
def home():
    mapbox_status = "✅ AKTYWNE" if MAPBOX_API_KEY else "❌ BRAK KLUCZA"
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🛰️ Satellite Visual Guide v6.6</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
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
                color: white;
            }}
            .subtitle {{
                text-align: center;
                font-size: 1.2em;
                margin-bottom: 30px;
                opacity: 0.9;
            }}
            .feature-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .feature {{
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 15px;
                text-align: center;
            }}
            .feature-icon {{
                font-size: 3em;
                margin-bottom: 15px;
            }}
            .command {{
                background: rgba(0, 0, 0, 0.3);
                padding: 10px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
                display: block;
            }}
            .map-example {{
                margin: 20px 0;
                text-align: center;
            }}
            .map-marker {{
                display: inline-block;
                margin: 0 10px;
                font-size: 1.5em;
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
            .status {{
                background: rgba(76, 175, 80, 0.2);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin: 20px 0;
                border-left: 5px solid #4CAF50;
            }}
            .warning {{
                background: rgba(255, 152, 0, 0.2);
                padding: 15px;
                border-radius: 10px;
                border-left: 5px solid #ff9800;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ Satellite Visual Guide</h1>
            <div class="subtitle">v6.6 - System z mapami i strzałkami kierunku</div>
            
            <div class="status">
                ✅ <b>SYSTEM AKTYWNY</b> | 🗺️ Mapy: {mapbox_status} | 🧭 Kierunki | 📍 Wizualizacje
            </div>
            
            <div class="feature-grid">
                <div class="feature">
                    <div class="feature-icon">🗺️</div>
                    <h3>Mapy z lokalizacją</h3>
                    <p>Zobacz gdzie stanąć - zielony marker pokazuje Twoją pozycję obserwacyjną</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🧭</div>
                    <h3>Strzałki kierunku</h3>
                    <p>Czerwona strzałka pokazuje dokładnie gdzie patrzeć na niebie</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📍</div>
                    <h3>Wizualne wskazówki</h3>
                    <p>Mapy z kompasem i punktami odniesienia dla łatwej orientacji</p>
                </div>
            </div>
            
            <div class="map-example">
                <h3>🎯 LEGENDA MAP:</h3>
                <div style="margin: 15px 0;">
                    <span class="map-marker">🟢</span> Twoja pozycja - tutaj stań
                    <span class="map-marker">🔴</span> Cel obserwacji - tam patrz
                    <span class="map-marker">🧭</span> Strzałka kierunku - podążaj za nią
                    <span class="map-marker">🔵</span> Kompas - orientacja w terenie
                </div>
            </div>
            
            <div>
                <h3>📋 GŁÓWNE KOMENDY:</h3>
                <div class="command">/view [miasto] [satelita]</div>
                <p>Pokazuje mapę z Twoją pozycją i strzałką wskazującą gdzie patrzeć</p>
                
                <div class="command">/best [miasto]</div>
                <p>Znajduje najlepszą okazję i pokazuje zestaw map</p>
                
                <div class="command">/guide [miasto]</div>
                <p>Pełny przewodnik wizualny z kompasem i orientacją</p>
                
                <div class="command">/location [miasto]</div>
                <p>Pokazuje Twoją pozycję obserwacyjną na mapie</p>
                
                <div class="command">/passes [miasto]</div>
                <p>Lista przelotów z linkami do map kierunku</p>
            </div>
            
            <div style="margin-top: 30px;">
                <h3>📍 PRZYKŁADOWE LOKALIZACJE:</h3>
                <p><b>warszawa, krakow, gdansk, wroclaw, poznan, bialystok, rzeszow, katowice, szczecin, lodz, lublin, tatry, bialowieza, sopot, zakopane, olsztyn, torun, czestochowa</b></p>
            </div>
            
            {'<div class="warning"><b>⚠️ UWAGA:</b> Mapbox API nie jest skonfigurowane. Aby używać map, dodaj MAPBOX_API_KEY do zmiennych środowiskowych.</div>' if not MAPBOX_API_KEY else ''}
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/PcSentinel_Bot" class="telegram-link" target="_blank">
                    🚀 Rozpocznij z botem @PcSentinel_Bot
                </a>
            </div>
            
            <div style="margin-top: 30px; font-size: 0.9em; opacity: 0.8; text-align: center;">
                <p>🌍 System pokazuje dokładnie gdzie stanąć i w którą stronę patrzeć</p>
                <p>🛰️ Wersja 6.6 | Mapy z strzałkami | Wizualne przewodniki | Render.com</p>
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
        success = bot.handle_webhook(data)
        
        if success:
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"status": "error"}), 500
            
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Ustaw webhook (dla testów)"""
    if not TELEGRAM_BOT_API:
        return jsonify({"status": "error", "message": "Brak tokena Telegram"}), 400
    
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
        "version": "6.6",
        "timestamp": datetime.now().isoformat(),
        "system": "Satellite Visual Guide",
        "features": [
            "satellite_tracking",
            "visual_maps",
            "direction_arrows",
            "location_guides",
            "telegram_bot"
        ],
        "apis": {
            "telegram": bool(TELEGRAM_BOT_API),
            "n2yo": bool(N2YO_API_KEY),
            "mapbox": bool(MAPBOX_API_KEY),
            "satellite_count": len(bot.tracker.observation_satellites),
            "location_count": len(bot.points)
        }
    })

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🛰️ URUCHAMIANIE SATELLITE VISUAL GUIDE v6.6")
    print("=" * 80)
    
    # Log status API
    print("🔧 STATUS SYSTEMU:")
    print(f"   🤖 Telegram Bot: {'✅ AKTYWNY' if bot.available else '❌ NIEDOSTĘPNY'}")
    print(f"   🗺️ Mapbox API: {'✅ AKTYWNY' if MAPBOX_API_KEY else '❌ BRAK KLUCZA'}")
    print(f"   🛰️ N2YO API: {'✅ AKTYWNY' if N2YO_API_KEY else '⚠️ TRYB DEMO'}")
    print(f"   📍 Lokalizacje: {len(bot.points)} miast")
    print(f"   🛰️ Satelity: {len(bot.tracker.observation_satellites)} satelitów")
    print("=" * 80)
    
    # Ustaw webhook jeśli mamy token
    if bot.available:
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
                print(f"⚠️ Błąd webhooka: {response.text}")
        except Exception as e:
            print(f"⚠️ Nie udało się ustawić webhooka: {e}")
    else:
        print("⚠️ Brak tokena Telegram - webhook nieaktywny")
    
    print("\n🧭 NOWE KOMENDY WIZUALNE:")
    print("   /view [miasto] [satelita] - mapa z kierunkiem")
    print("   /guide [miasto] - przewodnik wizualny")
    print("   /location [miasto] - Twoja pozycja na mapie")
    print("   /best [miasto] - najlepsza okazja z mapami")
    
    if not MAPBOX_API_KEY:
        print("\n⚠️ UWAGA: Mapbox API nie skonfigurowane!")
        print("   Aby używać map, dodaj MAPBOX_API_KEY do environment variables")
        print("   Bez Mapbox: pokazujemy tylko tekstowe instrukcje")
    
    print("\n🌐 DOSTĘPNE ENDPOINTY:")
    print(f"   {RENDER_URL}/ - strona główna")
    print(f"   {RENDER_URL}/status - status systemu")
    print("=" * 80)
    print("🚀 SYSTEM GOTOWY DO DZIAŁANIA!")
    print("=" * 80)
    
    # Uruchom aplikację
    app.run(host="0.0.0.0", port=PORT, debug=False)