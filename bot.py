#!/usr/bin/env python3
"""
🛰️ EARTH OBSERVATION PLATFORM v6.5 - SATELLITE TRACKER ADDED
✅ Kompletne śledzenie satelitów z obliczaniem szans na zdjęcia
✅ Integracja z DeepSeek API dla zaawansowanych analiz
✅ Bez zależności od SciPy - kompatybilne z Renderem
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

# ====================== KONFIGURACJA Z ENVIRONMENT ======================
print("=" * 80)
print("🛰️ EARTH OBSERVATION PLATFORM v6.5 - SATELLITE TRACKER")
print("📸 Dodano obliczanie szans na zdjęcia z satelitów")
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

# ====================== POMOCNICZE FUNKCJE MATEMATYCZNE ======================

def degrees_to_radians(deg):
    """Konwertuj stopnie na radiany"""
    return deg * math.pi / 180.0

def radians_to_degrees(rad):
    """Konwertuj radiany na stopnie"""
    return rad * 180.0 / math.pi

def calculate_distance(lat1, lon1, lat2, lon2):
    """Oblicz odległość między dwoma punktami na Ziemi (w km) - uproszczone"""
    # Uproszczona formuła dla małych odległości
    R = 6371  # Promień Ziemi w km
    
    lat1_rad = degrees_to_radians(lat1)
    lon1_rad = degrees_to_radians(lon1)
    lat2_rad = degrees_to_radians(lat2)
    lon2_rad = degrees_to_radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_angle_from_components(dx, dy, dz):
    """Oblicz kąt z komponentów wektora"""
    if dx == 0 and dy == 0 and dz == 0:
        return 0
    
    magnitude = math.sqrt(dx*dx + dy*dy + dz*dz)
    if magnitude == 0:
        return 0
    
    # Dla uproszczenia - zwróć kąt w płaszczyźnie poziomej
    angle_rad = math.atan2(dy, dx)
    angle_deg = radians_to_degrees(angle_rad)
    
    if angle_deg < 0:
        angle_deg += 360
    
    return angle_deg

# ====================== MODUŁ ŚLEDZENIA SATELITÓW ======================

class SatelliteTracker:
    """Zaawansowany system śledzenia satelitów i obliczania szans na zdjęcia"""
    
    def __init__(self, n2yo_api_key=None):
        self.n2yo_api_key = n2yo_api_key
        self.base_url = "https://api.n2yo.com/rest/v1/satellite"
        
        # Baza danych satelitów obserwacyjnych
        self.observation_satellites = {
            # Satelity optyczne
            "landsat-8": {
                "norad_id": 39084,
                "name": "Landsat 8",
                "type": "optical",
                "camera": "OLI/TIRS",
                "resolution": 15,  # metry
                "swath_width": 185,  # km
                "fov_deg": 15.3,  # pole widzenia
                "min_altitude": 705,  # km
                "max_altitude": 705,
                "imaging_angle_range": (-30, 30)  # kąt nachylenia kamery
            },
            "sentinel-2a": {
                "norad_id": 40697,
                "name": "Sentinel-2A",
                "type": "multispectral",
                "camera": "MSI",
                "resolution": 10,
                "swath_width": 290,
                "fov_deg": 20.6,
                "min_altitude": 786,
                "max_altitude": 786,
                "imaging_angle_range": (-25, 25)
            },
            "sentinel-2b": {
                "norad_id": 42969,
                "name": "Sentinel-2B",
                "type": "multispectral",
                "camera": "MSI",
                "resolution": 10,
                "swath_width": 290,
                "fov_deg": 20.6,
                "min_altitude": 786,
                "max_altitude": 786,
                "imaging_angle_range": (-25, 25)
            },
            # Satelity wysokiej rozdzielczości
            "worldview-3": {
                "norad_id": 40115,
                "name": "WorldView-3",
                "type": "vhr",
                "camera": "CAVIS",
                "resolution": 0.31,
                "swath_width": 13.1,
                "fov_deg": 1.2,
                "min_altitude": 617,
                "max_altitude": 617,
                "imaging_angle_range": (-45, 45)
            },
            # Stacja ISS
            "iss": {
                "norad_id": 25544,
                "name": "International Space Station",
                "type": "station",
                "camera": "EarthKAM/Nikon",
                "resolution": 10,
                "swath_width": 5,
                "fov_deg": 50,
                "min_altitude": 408,
                "max_altitude": 410,
                "imaging_angle_range": (-90, 90)
            },
            # Dodatkowe satelity
            "modis-aqua": {
                "norad_id": 27424,
                "name": "Aqua (MODIS)",
                "type": "multispectral",
                "camera": "MODIS",
                "resolution": 250,
                "swath_width": 2330,
                "fov_deg": 55,
                "min_altitude": 705,
                "max_altitude": 705,
                "imaging_angle_range": (-20, 20)
            },
            "terra": {
                "norad_id": 25994,
                "name": "Terra",
                "type": "multispectral",
                "camera": "ASTER",
                "resolution": 15,
                "swath_width": 60,
                "fov_deg": 4,
                "min_altitude": 705,
                "max_altitude": 705,
                "imaging_angle_range": (-24, 24)
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
                    url = f"{self.base_url}/radiopasses/{sat_data['norad_id']}/{lat}/{lon}/{alt}/{days}/{min_elevation}"
                    params = {'apiKey': self.n2yo_api_key}
                    
                    response = requests.get(url, params=params, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        
                        for pass_data in data.get('passes', []):
                            # Oblicz szansę na zdjęcie
                            photo_chance = self.calculate_photo_chance(
                                sat_data, pass_data, lat, lon
                            )
                            
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
                                'recommended_angle': self.calculate_optimal_angle(pass_data, lat, lon),
                                'peak_azimuth': pass_data.get('maxAz', 0),
                                'peak_altitude': pass_data.get('maxEl', 0),
                                'satellite_type': sat_data['type']
                            }
                            passes.append(pass_info)
                except Exception as e:
                    logger.warning(f"⚠️ Błąd pobierania dla {sat_name}: {e}")
                    continue
            
            # Sortuj po dacie i szansie
            passes.sort(key=lambda x: (x['start_utc'], -x['photo_chance']))
            return passes[:25]  # Zwróć max 25 przelotów
            
        except Exception as e:
            logger.error(f"❌ Błąd pobierania przelotów: {e}")
            return self._generate_mock_passes(lat, lon, days)
    
    def _generate_mock_passes(self, lat: float, lon: float, days: int) -> List[Dict]:
        """Wygeneruj przykładowe przeloty gdy brak API"""
        passes = []
        now = datetime.utcnow()
        
        # Generuj realistyczne przeloty dla różnych satelitów
        satellites = list(self.observation_satellites.values())
        
        for day_offset in range(days):
            for hour in [6, 10, 14, 18, 22]:  # Kilka przelotów dziennie
                sat_data = random.choice(satellites)
                base_time = now + timedelta(days=day_offset, hours=hour)
                
                # Losowe odchylenie czasowe
                time_offset = random.randint(-30, 30)
                start_time = base_time + timedelta(minutes=time_offset)
                
                # Czas trwania zależny od typu satelity
                if sat_data['type'] == 'station':  # ISS
                    duration = random.randint(300, 600)  # 5-10 minut
                else:
                    duration = random.randint(120, 300)  # 2-5 minut
                
                # Maksymalna wysokość
                max_elevation = random.uniform(15, 85)
                
                # Oblicz szansę na zdjęcie
                base_chance = 40
                if max_elevation > 60:
                    base_chance += 25
                elif max_elevation > 30:
                    base_chance += 15
                
                if sat_data['type'] == 'vhr':  # Very High Resolution
                    base_chance += 10
                elif sat_data['type'] == 'optical':
                    base_chance += 5
                
                # Losowe wahania
                photo_chance = base_chance + random.uniform(-10, 15)
                photo_chance = min(95, max(5, photo_chance))
                
                # Kąt zalecany
                recommended_angle = random.randint(0, 359)
                
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
                    'recommended_angle': recommended_angle,
                    'peak_azimuth': random.randint(0, 359),
                    'peak_altitude': max_elevation,
                    'satellite_type': sat_data['type']
                }
                passes.append(pass_info)
        
        # Sortuj po czasie
        passes.sort(key=lambda x: x['start_utc'])
        return passes[:25]
    
    def calculate_photo_chance(self, sat_data: Dict, pass_data: Dict, 
                              lat: float, lon: float) -> float:
        """Oblicz prawdopodobieństwo wykonania zdjęcia"""
        # Czynniki wpływające na szansę:
        chance = 50.0  # Podstawowa szansa
        
        # 1. Wysokość maksymalna przelotu
        max_elev = pass_data.get('maxEl', 0)
        if max_elev > 60:
            chance += 25
        elif max_elev > 40:
            chance += 15
        elif max_elev > 20:
            chance += 8
        
        # 2. Typ satelity
        sat_type = sat_data.get('type', '')
        if sat_type == 'vhr':  # Very High Resolution
            chance += 15
        elif sat_type == 'optical':
            chance += 10
        elif sat_type == 'station':  # ISS
            chance += 5
        
        # 3. Czas trwania przelotu
        duration = pass_data.get('endUTC', 0) - pass_data.get('startUTC', 0)
        if duration > 600:  # >10 minut
            chance += 15
        elif duration > 300:  # >5 minut
            chance += 8
        
        # 4. Porównanie z charakterystyką kamery
        fov = sat_data.get('fov_deg', 10)
        if fov > 30:  # Szerokie pole widzenia
            chance += 10
        
        # 5. Losowe czynniki
        random_factor = random.uniform(0.8, 1.2)
        chance *= random_factor
        
        # 6. Współczynnik pory dnia (symulacja)
        # Zakładamy, że dane pass_data mają timestamp w sekundach
        pass_time = datetime.utcfromtimestamp(pass_data.get('maxUTC', 0))
        hour = pass_time.hour
        
        if 8 <= hour <= 16:  # Dzien
            chance *= 1.1
        elif 6 <= hour <= 19:  # Przedświt/zmierzch
            chance *= 1.0
        else:  # Noc
            chance *= 0.9
        
        return min(98, max(2, round(chance, 1)))
    
    def calculate_optimal_angle(self, pass_data: Dict, lat: float, lon: float) -> float:
        """Oblicz optymalny kąt ustawienia kamery"""
        # Uproszczone obliczenia bez SciPy
        max_az = pass_data.get('maxAz', 0)
        max_el = pass_data.get('maxEl', 0)
        
        # Proste obliczenie kąta optymalnego na podstawie trajektorii
        # Dla wysokich przejść - patrz bardziej w zenit
        # Dla niskich - podążaj za trajektorią
        
        if max_el > 60:
            # Wysokie przejście - patrz w zenit z lekkim przesunięciem
            return (max_az + 90) % 360
        elif max_el > 30:
            # Średnie przejście - kieruj się w stronę maksymalnej wysokości
            return (max_az + 45) % 360
        else:
            # Niskie przejście - podążaj dokładnie za trajektorią
            return max_az
    
    def get_satellite_positions(self, lat: float, lon: float) -> List[Dict]:
        """Pobierz aktualne pozycje satelitów"""
        positions = []
        
        for sat_name, sat_data in list(self.observation_satellites.items())[:5]:  # Tylko 5 pierwszych
            try:
                if self.n2yo_api_key:
                    url = f"{self.base_url}/positions/{sat_data['norad_id']}/{lat}/{lon}/0/1"
                    params = {'apiKey': self.n2yo_api_key}
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if 'positions' in data and len(data['positions']) > 0:
                            pos = data['positions'][0]
                            positions.append({
                                'name': sat_data['name'],
                                'azimuth': pos.get('azimuth', 0),
                                'elevation': pos.get('elevation', 0),
                                'altitude': pos.get('sataltitude', sat_data['min_altitude']),
                                'range': pos.get('sataltitude', 500),
                                'type': sat_data['type']
                            })
            except Exception as e:
                logger.debug(f"Debug: Błąd pozycji {sat_name}: {e}")
                # Symulacja pozycji
                positions.append({
                    'name': sat_data['name'],
                    'azimuth': random.uniform(0, 360),
                    'elevation': random.uniform(-10, 90),
                    'altitude': sat_data['min_altitude'],
                    'range': random.uniform(400, 800),
                    'type': sat_data['type']
                })
        
        # Sortuj po wysokości (najwyższe na górze)
        positions.sort(key=lambda x: x['elevation'], reverse=True)
        return positions
    
    def get_best_photo_opportunity(self, lat: float, lon: float, 
                                  hours: int = 24) -> Optional[Dict]:
        """Znajdź najlepszą okazję do zrobienia zdjęcia w ciągu najbliższych godzin"""
        passes = self.get_satellite_passes(lat, lon, days=1)
        
        if not passes:
            return None
        
        # Filtruj tylko przeloty w zadanym oknie czasowym
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)
        
        relevant_passes = [
            p for p in passes 
            if now <= p['start_utc'] <= end_time and p['photo_chance'] > 40
        ]
        
        if not relevant_passes:
            # Jeśli nie ma z szansą >40%, weź najlepszy w ogóle
            relevant_passes = [
                p for p in passes 
                if now <= p['start_utc'] <= end_time
            ]
        
        if not relevant_passes:
            return None
        
        # Znajdź przelot z największą szansą
        best_pass = max(relevant_passes, key=lambda x: x['photo_chance'])
        
        # Dodaj szczegółowe instrukcje
        best_pass['instructions'] = self._generate_instructions(best_pass, lat, lon)
        best_pass['equipment_recommendation'] = self._get_equipment_recommendation(best_pass)
        best_pass['weather_tips'] = self._get_weather_tips(best_pass)
        
        return best_pass
    
    def _generate_instructions(self, pass_data: Dict, lat: float, lon: float) -> str:
        """Wygeneruj instrukcje dla fotografa"""
        instructions = []
        
        # Pozycja
        instructions.append(f"📍 Stanowisko: {lat:.4f}°N, {lon:.4f}°E")
        
        # Czas
        local_time = pass_data['start_utc'] + timedelta(hours=1)  # Dla Polski (UTC+1)
        instructions.append(f"🕐 Rozpoczęcie: {local_time.strftime('%Y-%m-%d %H:%M:%S')} czasu lokalnego")
        instructions.append(f"⏱️ Czas trwania: {int(pass_data['duration']//60)} minut")
        
        # Kąty
        instructions.append(f"🧭 Maksymalna wysokość: {pass_data['max_elevation']:.1f}°")
        instructions.append(f"🎯 Zalecany azymut: {pass_data['recommended_angle']:.0f}°")
        
        # Szansa
        chance = pass_data['photo_chance']
        if chance > 80:
            rating = "DOSKONAŁA"
            emoji = "🌟🌟🌟"
        elif chance > 65:
            rating = "DOBRA"
            emoji = "🌟🌟"
        elif chance > 50:
            rating = "ŚREDNIA"
            emoji = "🌟"
        else:
            rating = "NISKA"
            emoji = "⚠️"
        
        instructions.append(f"{emoji} Szansa na zdjęcie: {chance:.0f}% - {rating}")
        
        # Dodatkowe wskazówki
        if pass_data['max_elevation'] > 70:
            instructions.append("🔭 UWAGA: Satelita przejdzie blisko zenitu - użyj szerokokątnego obiektywu")
        elif pass_data['max_elevation'] < 25:
            instructions.append("🌅 UWAGA: Niski przelot - potrzebujesz czystego horyzontu")
        
        if pass_data.get('satellite_type') == 'vhr':
            instructions.append("📡 SATELITA: Bardzo wysoka rozdzielczość - potrzebny teleobiektyw")
        elif 'ISS' in pass_data['satellite']:
            instructions.append("🚀 STACJA ISS: Jasna, szybka - dobre dla początkujących")
        
        return "\n".join(instructions)
    
    def _get_equipment_recommendation(self, pass_data: Dict) -> str:
        """Zalecenia dotyczące sprzętu"""
        sat_type = pass_data.get('satellite_type', '')
        
        if sat_type == 'vhr':
            return "📸 Zalecany sprzęt: Teleobiektyw 300mm+, statyw, wyzwalacz zdalny, ISO 400-800"
        elif sat_type == 'optical':
            return "📸 Zalecany sprzęt: Obiektyw 70-200mm, statyw, wyzwalacz, ISO 800-1600"
        elif 'ISS' in pass_data['satellite']:
            return "📸 Zalecany sprzęt: Szerokokątny 24mm, statyw, czas 2-5s, ISO 1600-3200"
        elif sat_type == 'station':
            return "📸 Zalecany sprzęt: Obiektyw 50mm, statyw, czas 1-3s, ISO 800-1600"
        else:
            return "📸 Zalecany sprzęt: Standardowy zestaw do astrofotografii, statyw, wyzwalacz"
    
    def _get_weather_tips(self, pass_data: Dict) -> str:
        """Wskazówki pogodowe"""
        tips = []
        
        if pass_data['max_elevation'] < 30:
            tips.append("🌫️ Przy niskim kącie, wilgoć i mgła mogą być problemem")
        
        if pass_data['photo_chance'] > 70:
            tips.append("☀️ Doskonałe warunki - sprawdź tylko zachmurzenie")
        else:
            tips.append("⛅ Sprawdź szczegółową prognozę przed wyjściem")
        
        return " | ".join(tips)
    
    def get_satellite_details(self, satellite_name: str) -> Optional[Dict]:
        """Pobierz szczegóły konkretnego satelity"""
        for key, sat_data in self.observation_satellites.items():
            if satellite_name.lower() in key.lower() or satellite_name.lower() in sat_data['name'].lower():
                return sat_data
        return None

# ====================== INTEGRACJA Z DEEPSEEK API ======================

class DeepSeekAnalyzer:
    """Zaawansowana analiza danych satelitarnych przy użyciu DeepSeek API"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.available = bool(api_key)
    
    def analyze_satellite_opportunity(self, satellite_data: Dict, 
                                     location_data: Dict, 
                                     weather_data: Dict) -> Dict:
        """Przeanalizuj okazję satelitarną przy użyciu AI"""
        if not self.available:
            return self._generate_mock_analysis(satellite_data, location_data)
        
        try:
            # Przygotuj pogodę
            weather_desc = "Nieznane"
            if weather_data.get('success', False):
                weather_desc = f"{weather_data.get('clouds', 0)}% zachmurzenia, {weather_data.get('temp', 0)}°C"
            
            prompt = f"""
            ANALIZA OKAZJI SATELITARNEJ - SPECJALISTYCZNA PORADA
            
            DANE SATELITY:
            - Nazwa: {satellite_data.get('satellite', 'Nieznany')}
            - Typ: {satellite_data.get('type', 'Nieznany')}
            - Szansa na zdjęcie: {satellite_data.get('photo_chance', 0)}%
            - Maksymalna wysokość: {satellite_data.get('max_elevation', 0)}°
            - Czas trwania: {satellite_data.get('duration', 0)} sekund
            - Zalecany azymut: {satellite_data.get('recommended_angle', 0)}°
            
            DANE LOKALIZACJI:
            - Szerokość: {location_data.get('lat', 0):.4f}°
            - Długość: {location_data.get('lon', 0):.4f}°
            - Nazwa: {location_data.get('name', 'Lokalizacja')}
            
            DANE POGODOWE: {weather_desc}
            
            JESTEŚ EKSPERTEM OD FOTOGRAFII SATELITARNEJ. PROSZĘ O:
            
            1. SZCZEGÓŁOWĄ ANALIZĘ:
               - Ocenę realnej szansy na udane zdjęcie
               - Czynniki zwiększające/zmniejszające szansę
               - Specyfika tego konkretnego satelity
            
            2. KONKRETNE ZALECENIA TECHNICZNE:
               - Ustawienia aparatu (ISO, czas, przysłona)
               - Konkretny sprzęt do użycia
               - Techniki śledzenia
            
            3. PRAKTYCZNE WSKAZÓWKI:
               - Gdzie dokładnie stanąć
               - Jak przygotować się wcześniej
               - Co sprawdzić przed wyjściem
            
            4. ALTERNATYWNE SCENARIUSZE:
               - Co zrobić jeśli warunki się zmienią
               - Alternatywne ustawienia
               - Plan B
            
            Odpowiedz w formacie:
            📊 ANALIZA: [3-4 zdania podsumowania]
            
            ⚙️ ZALECENIA TECHNICZNE:
            - [zalecenie 1]
            - [zalecenie 2]
            
            📋 PRZYGOTOWANIE:
            - [krok 1]
            - [krok 2]
            
            ⚠️ POTENCJALNE PROBLEMY:
            - [problem 1]
            - [problem 2]
            
            🔄 ALTERNATYWY:
            - [alternatywa 1]
            - [alternatywa 2]
            
            ⏱️ CZAS PRZYGOTOWANIA: [X] minut
            """
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Jesteś ekspertem od fotografii satelitarnej i astrofotografii z 15-letnim doświadczeniem."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1200,
                "temperature": 0.7
            }
            
            response = requests.post(self.base_url, json=payload, 
                                   headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result['choices'][0]['message']['content']
                
                # Przetwarzaj odpowiedź
                return self._parse_analysis_response(analysis_text, satellite_data)
            else:
                logger.error(f"❌ Błąd DeepSeek API: {response.status_code}")
                return self._generate_mock_analysis(satellite_data, location_data)
                
        except Exception as e:
            logger.error(f"❌ Błąd analizy DeepSeek: {e}")
            return self._generate_mock_analysis(satellite_data, location_data)
    
    def _parse_analysis_response(self, text: str, satellite_data: Dict) -> Dict:
        """Przetwórz odpowiedź z DeepSeek"""
        sections = {
            'ANALIZA': '',
            'ZALECENIA TECHNICZNE': [],
            'PRZYGOTOWANIE': [],
            'POTENCJALNE PROBLEMY': [],
            'ALTERNATYWY': [],
            'CZAS PRZYGOTOWANIA': '20'
        }
        
        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Sprawdź nagłówki sekcji (z emoji)
            for section in sections.keys():
                if section in line:
                    current_section = section
                    # Usuń emoji i nagłówek
                    line = line.replace('📊', '').replace('⚙️', '').replace('📋', '')
                    line = line.replace('⚠️', '').replace('🔄', '').replace('⏱️', '')
                    line = line.replace(section, '').replace(':', '').strip()
                    if current_section != 'ANALIZA':
                        sections[current_section] = []
                    break
            
            if current_section and line:
                if current_section == 'ANALIZA':
                    sections[current_section] += ' ' + line
                elif line.startswith('-') or line.startswith('•'):
                    sections[current_section].append(line.lstrip('-• ').strip())
                elif current_section == 'CZAS PRZYGOTOWANIA':
                    # Spróbuj wyciągnąć liczby
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        sections[current_section] = numbers[0]
        
        return {
            'analysis': sections['ANALIZA'].strip(),
            'technical_recommendations': sections['ZALECENIA TECHNICZNE'][:5],
            'preparation_steps': sections['PRZYGOTOWANIE'][:4],
            'potential_problems': sections['POTENCJALNE PROBLEMY'][:3],
            'alternatives': sections['ALTERNATYWY'][:3],
            'prep_time_minutes': int(sections['CZAS PRZYGOTOWANIA'] or '20'),
            'satellite': satellite_data.get('satellite', ''),
            'chance': satellite_data.get('photo_chance', 0)
        }
    
    def _generate_mock_analysis(self, satellite_data: Dict, location_data: Dict) -> Dict:
        """Generuj przykładową analizę gdy brak API"""
        sat_name = satellite_data.get('satellite', 'Satelita')
        location = location_data.get('name', 'Twoja lokalizacja')
        
        return {
            'analysis': f"Satelita {sat_name} oferuje dobrą okazję na zdjęcie z {location}. Wysokość przejścia {satellite_data.get('max_elevation', 0)}° zapewnia odpowiedni czas na ujęcie, a czas trwania {satellite_data.get('duration', 0)//60} minut daje margines błędu.",
            'technical_recommendations': [
                'Użyj statywu dla maksymalnej stabilności',
                'ISO 800-1600 dla optymalnego stosunku sygnału do szumu',
                'Czas naświetlania 1-3 sekundy w zależności od jasności',
                'Użyj wyzwalacza zdalnego lub samowyzwalacza',
                'Przetestuj kilka ustawień przed właściwym przelotem'
            ],
            'preparation_steps': [
                'Sprawdź prognozę pogody na godzinę przelotu',
                'Przygotuj sprzęt minimum 30 minut wcześniej',
                'Znajdź miejsce bez bezpośrednich świateł w okolicy',
                'Ustaw aplikację do śledzenia satelitów'
            ],
            'potential_problems': [
                'Nagłe zachmurzenie może uniemożliwić obserwację',
                'Wiatr może poruszać statywem przy dłuższych czasach',
                'Wilgoć może skraplać się na obiektywie'
            ],
            'alternatives': [
                'Jeśli satelita jest zbyt jasny, zmniejsz czas naświetlania',
                'Przy niskiej wysokości, spróbuj z miejsca z lepszym horyzontem',
                'W przypadku problemów, skup się na śledzeniu bez fotografii'
            ],
            'prep_time_minutes': 25,
            'satellite': sat_name,
            'chance': satellite_data.get('photo_chance', 0)
        }

# ====================== GŁÓWNA APLIKACJA FLASK ======================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================== TELEGRAM BOT (UPROSZCZONY) ======================

class SimpleTelegramBot:
    """Uproszczony bot Telegram z funkcjami satelitarnymi"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_API
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.available = bool(TELEGRAM_BOT_API)
        
        # Inicjalizuj moduły
        self.tracker = SatelliteTracker(N2YO_API_KEY)
        self.deepseek = DeepSeekAnalyzer(DEEPSEEK_API_KEY) if DEEPSEEK_API_KEY else None
        
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
            "tatry": {"name": "Tatry", "lat": 49.1795, "lon": 20.0884, "note": "Góry"},
            "bialowieza": {"name": "Białowieża", "lat": 52.7000, "lon": 23.8667, "note": "Park Narodowy"}
        }
        
        if self.available:
            logger.info("✅ Bot Telegram zainicjalizowany")
        else:
            logger.warning("⚠️ Bot Telegram niedostępny - brak tokena")
    
    def send_message(self, chat_id: int, text: str, parse_html: bool = True):
        """Wyślij wiadomość"""
        if not self.available:
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
                        "🛰️ <b>Satellite Photo Predictor</b>\n\n"
                        "Użyj jednej z komend:\n"
                        "<code>/passes [miasto]</code> - przeloty satelitów\n"
                        "<code>/best [miasto]</code> - najlepsza okazja\n"
                        "<code>/track [miasto]</code> - śledź satelity\n"
                        "<code>/help</code> - pomoc\n\n"
                        "Przykład: <code>/passes warszawa</code>"
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
        elif command == "passes" or command == "satpass":
            self.cmd_passes(chat_id, args)
        elif command == "best" or command == "nextphoto":
            self.cmd_best(chat_id, args)
        elif command == "track" or command == "satposition":
            self.cmd_track(chat_id, args)
        elif command == "analyze":
            self.cmd_analyze(chat_id, args)
        elif command == "points" or command == "locations":
            self.cmd_points(chat_id)
        elif command == "satellites":
            self.cmd_satellites(chat_id)
        else:
            self.send_message(chat_id, "❌ Nieznana komenda. Użyj /help")
    
    def cmd_start(self, chat_id: int):
        """Komenda /start"""
        message = """
🛰️ <b>SATELLITE PHOTO PREDICTOR</b>
📸 <i>System przewidywania szans na zdjęcia satelitarne</i>

<b>Główne funkcje:</b>
• 📅 Przeloty satelitów obserwacyjnych
• 📊 Obliczanie szans na udane zdjęcie
• 🎯 Zalecenia dotyczące ustawień
• 🤖 Analiza AI (z DeepSeek)

<b>Podstawowe komendy:</b>
<code>/passes [miasto]</code> - przeloty satelitów
<code>/best [miasto]</code> - najlepsza okazja
<code>/track [miasto]</code> - śledzenie na żywo
<code>/analyze [miasto] [satelita]</code> - analiza AI

<b>Przykłady:</b>
• <code>/passes warszawa</code>
• <code>/best krakow</code>
• <code>/track gdansk</code>
• <code>/analyze wroclaw iss</code>

Użyj <code>/points</code> aby zobaczyć dostępne lokalizacje.
"""
        self.send_message(chat_id, message)
    
    def cmd_help(self, chat_id: int):
        """Komenda /help"""
        message = """
📋 <b>DOSTĘPNE KOMENDY:</b>

<b>🛰️ OBSERWACJE SATELITARNE:</b>
<code>/passes [miasto] [dni]</code> - przeloty satelitów
<code>/best [miasto] [godziny]</code> - najlepsza okazja
<code>/track [miasto]</code> - aktualne pozycje
<code>/analyze [miasto] [satelita]</code> - analiza AI

<b>📍 LOKALIZACJE:</b>
<code>/points</code> - dostępne miasta
<code>/satellites</code> - lista satelitów

<b>⚙️ PARAMETRY:</b>
• [miasto] - np. warszawa, krakow (zobacz /points)
• [dni] - liczba dni do przodu (domyślnie 3, max 10)
• [godziny] - zakres wyszukiwania (domyślnie 24)

<b>📊 PRZYKŁADY:</b>
<code>/passes warszawa 5</code> - przeloty na 5 dni
<code>/best krakow 48</code> - najlepsza w 48h
<code>/track gdansk</code> - śledzenie na żywo
<code>/analyze wroclaw landsat-8</code> - analiza

<b>🎯 CEL:</b>
System pomaga przewidzieć kiedy i gdzie stanąć, aby zrobić zdjęcie satelity!
"""
        self.send_message(chat_id, message)
    
    def cmd_points(self, chat_id: int):
        """Komenda /points"""
        message = "📍 <b>DOSTĘPNE LOKALIZACJE:</b>\n\n"
        
        points_list = list(self.points.items())
        for i in range(0, len(points_list), 2):
            chunk = points_list[i:i+2]
            for key, point in chunk:
                message += f"• <b>{key}</b> - {point['name']}"
                if 'note' in point:
                    message += f" ({point['note']})"
                message += "\n"
            message += "\n"
        
        message += "🎯 <b>Użyj:</b> <code>/passes [nazwa_miasta]</code>"
        self.send_message(chat_id, message)
    
    def cmd_satellites(self, chat_id: int):
        """Komenda /satellites"""
        message = "🛰️ <b>OBSERWOWANE SATELITY:</b>\n\n"
        
        sats = self.tracker.observation_satellites
        for key, sat in list(sats.items())[:8]:  # Pierwsze 8
            message += f"• <b>{sat['name']}</b>\n"
            message += f"  📡 {sat['type'].upper()} | 📷 {sat['camera']}\n"
            message += f"  🎯 {sat['resolution']}m | 📏 {sat['swath_width']}km\n\n"
        
        message += "ℹ️ Użyj <code>/analyze [miasto] [nazwa]</code> dla szczegółów"
        self.send_message(chat_id, message)
    
    def cmd_passes(self, chat_id: int, args: List[str]):
        """Komenda /passes - przeloty satelitów"""
        if len(args) < 1:
            self.send_message(chat_id,
                "🛰️ <b>Format:</b> <code>/passes [miasto] [dni]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/passes warszawa</code> - przeloty na 3 dni\n"
                "<code>/passes krakow 5</code> - przeloty na 5 dni\n\n"
                "<b>Dostępne miasta:</b> warszawa, krakow, gdansk, wroclaw, poznan, bialystok, rzeszow, katowice, szczecin, lodz, lublin, tatry, bialowieza"
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto. Użyj /points")
            return
        
        # Parsuj parametry
        days = 3
        if len(args) > 1:
            try:
                days = min(int(args[1]), 10)  # Maksymalnie 10 dni
            except:
                pass
        
        self.send_message(chat_id, 
            f"🛰️ Szukam przelotów satelitów nad {point['name']}...\n"
            f"📅 Okres: {days} dni\n"
            f"⏳ To może chwilę potrwać..."
        )
        
        passes = self.tracker.get_satellite_passes(
            point['lat'], point['lon'], 
            days=days, min_elevation=15
        )
        
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
        
        # Pokaż najbliższe 3 dni
        today = datetime.utcnow().strftime('%Y-%m-%d')
        days_shown = 0
        
        for day in sorted(passes_by_day.keys())[:3]:  # Maksymalnie 3 dni
            day_passes = passes_by_day[day]
            if not day_passes:
                continue
            
            # Formatuj datę
            if day == today:
                day_str = "DZISIAJ"
            else:
                day_date = datetime.strptime(day, '%Y-%m-%d')
                day_str = day_date.strftime('%d.%m')
            
            message += f"📅 <b>{day_str}</b>\n"
            
            for i, p in enumerate(day_passes[:3], 1):  # Maksymalnie 3 na dzień
                start_local = p['start_utc'] + timedelta(hours=1)
                duration_min = int(p['duration'] // 60)
                
                # Emoji dla szansy
                if p['photo_chance'] > 75:
                    chance_emoji = "📈"
                elif p['photo_chance'] > 50:
                    chance_emoji = "📊"
                else:
                    chance_emoji = "📉"
                
                message += f"  {i}. {p['satellite'][:15]}...\n"
                message += f"     {chance_emoji} {p['photo_chance']:.0f}% | 🕐 {start_local.strftime('%H:%M')}\n"
                message += f"     📈 {p['max_elevation']:.0f}° | ⏱️ {duration_min}min\n"
            
            message += "\n"
            days_shown += 1
        
        if days_shown == 0:
            message += "📭 Brak przelotów w najbliższych dniach\n\n"
        
        # Statystyki
        total_passes = len(passes)
        high_chance = len([p for p in passes if p['photo_chance'] > 70])
        best_sat = max(passes, key=lambda x: x['photo_chance']) if passes else None
        
        message += f"📊 <b>STATYSTYKI ({total_passes} przelotów):</b>\n"
        message += f"• 🎯 Wysoka szansa (>70%): {high_chance}\n"
        
        if best_sat:
            best_time = best_sat['start_utc'] + timedelta(hours=1)
            message += f"• 🏆 <b>Najlepszy:</b> {best_sat['satellite']}\n"
            message += f"  ⭐ {best_sat['photo_chance']:.0f}% | 🕐 {best_time.strftime('%d.%m %H:%M')}\n"
        
        message += f"\n🎯 <b>Użyj:</b> <code>/best {point_name}</code> dla szczegółów najlepszej okazji"
        
        self.send_message(chat_id, message)
    
    def cmd_best(self, chat_id: int, args: List[str]):
        """Komenda /best - najlepsza okazja"""
        if len(args) < 1:
            self.send_message(chat_id,
                "🎯 <b>Format:</b> <code>/best [miasto] [godziny]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/best warszawa</code> - najlepsza w 24h\n"
                "<code>/best krakow 48</code> - najlepsza w 48h"
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
            f"⏰ Okres: {hours} godzin"
        )
        
        best = self.tracker.get_best_photo_opportunity(
            point['lat'], point['lon'], hours
        )
        
        if not best:
            self.send_message(chat_id, 
                f"❌ Brak dobrych okazji w ciągu {hours}h.\n"
                f"ℹ️ Spróbuj zwiększyć okres wyszukiwania lub wybierz inne miasto."
            )
            return
        
        # Formatuj czas
        start_local = best['start_utc'] + timedelta(hours=1)
        duration_min = int(best['duration'] // 60)
        
        message = f"🏆 <b>NAJLEPSZA OKAZJA - {point['name'].upper()}</b>\n\n"
        
        # Nagłówek
        message += f"🛰️ <b>{best['satellite']}</b>\n"
        message += f"⭐ <b>Szansa:</b> {best['photo_chance']:.0f}%\n"
        message += f"📅 <b>Data:</b> {start_local.strftime('%d.%m.%Y')}\n"
        message += f"🕐 <b>Czas:</b> {start_local.strftime('%H:%M')} lokalnego\n"
        message += f"⏱️ <b>Trwanie:</b> {duration_min} minut\n"
        message += f"📈 <b>Maks. wysokość:</b> {best['max_elevation']:.1f}°\n"
        message += f"🧭 <b>Azymut:</b> {best['recommended_angle']:.0f}°\n\n"
        
        # Instrukcje
        if 'instructions' in best:
            lines = best['instructions'].split('\n')
            message += "📋 <b>INSTRUKCJE:</b>\n"
            for line in lines[:6]:  # Pierwsze 6 linii
                message += f"{line}\n"
            message += "\n"
        
        # Sprzęt
        if 'equipment_recommendation' in best:
            message += f"🎒 <b>SPRZĘT:</b>\n{best['equipment_recommendation']}\n\n"
        
        # Wskazówki pogodowe
        if 'weather_tips' in best:
            message += f"🌤️ <b>POGODA:</b> {best['weather_tips']}\n\n"
        
        # Analiza AI jeśli dostępna
        if self.deepseek and self.deepseek.available:
            message += "🤖 <b>ANALIZA AI DOSTĘPNA:</b>\n"
            message += f"Użyj: <code>/analyze {point_name} {best['satellite'].split()[0].lower()}</code>\n"
        
        message += f"📍 <b>LOKALIZACJA:</b>\n{point['lat']:.4f}°N, {point['lon']:.4f}°E\n"
        message += f"🏙️ <b>MIEJSCOWOŚĆ:</b> {point['name']}"
        
        if 'note' in point:
            message += f" ({point['note']})"
        
        self.send_message(chat_id, message)
    
    def cmd_track(self, chat_id: int, args: List[str]):
        """Komenda /track - aktualne pozycje"""
        if len(args) < 1:
            self.send_message(chat_id,
                "📍 <b>Format:</b> <code>/track [miasto]</code>\n\n"
                "Pokazuje aktualne pozycje satelitów nad danym miastem."
            )
            return
        
        point_name = args[0]
        point = self.points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto")
            return
        
        self.send_message(chat_id, f"📍 Pobieram aktualne pozycje nad {point['name']}...")
        
        positions = self.tracker.get_satellite_positions(point['lat'], point['lon'])
        
        if not positions:
            self.send_message(chat_id, "❌ Nie udało się pobrać pozycji")
            return
        
        message = f"📍 <b>AKTUALNE POZYCJE - {point['name'].upper()}</b>\n"
        message += f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"
        
        visible_count = 0
        for i, pos in enumerate(positions[:6], 1):  # Maksymalnie 6
            if pos['elevation'] > 0:
                status = "👁️ WIDOCZNY"
                emoji = "🟢"
                visible_count += 1
            else:
                status = "🌚 POD HORYZONTEM"
                emoji = "🔴"
            
            message += f"{i}. <b>{pos['name'][:15]}</b> {emoji}\n"
            message += f"   {status}\n"
            
            if pos['elevation'] > 0:
                message += f"   🧭 {pos['azimuth']:.0f}° | 📈 {pos['elevation']:.1f}°\n"
                message += f"   🌍 {pos['altitude']:.0f}km | 📏 {pos['range']:.0f}km\n"
            
            message += "\n"
        
        message += f"📊 <b>PODSUMOWANIE:</b>\n"
        message += f"• 👁️ Widocznych teraz: {visible_count}/{len(positions)}\n"
        message += f"• 🛰️ Śledzonych satelitów: {len(positions)}\n"
        message += f"• 📍 Lokalizacja: {point['lat']:.2f}°N, {point['lon']:.2f}°E\n\n"
        
        message += "ℹ️ Dane aktualizowane na żywo. Pozycje zmieniają się szybko!"
        
        self.send_message(chat_id, message)
    
    def cmd_analyze(self, chat_id: int, args: List[str]):
        """Komenda /analyze - analiza AI"""
        if not self.deepseek or not self.deepseek.available:
            self.send_message(chat_id,
                "🤖 <b>DeepSeek API nie jest dostępne</b>\n\n"
                "ℹ️ Aby używać analizy AI, dodaj klucz API:\n"
                "<code>DEEPSEEK_API_KEY=twój_klucz_tutaj</code>\n\n"
                "Do zmiennych środowiskowych na Renderze."
            )
            return
        
        if len(args) < 2:
            self.send_message(chat_id,
                "🤖 <b>Format:</b> <code>/analyze [miasto] [satelita]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/analyze warszawa iss</code>\n"
                "<code>/analyze krakow landsat</code>\n"
                "<code>/analyze gdansk sentinel</code>\n\n"
                "<b>Dostępne satelity:</b> iss, landsat, sentinel, worldview, terra, modis"
            )
            return
        
        point_name = args[0]
        satellite_name = args[1]
        
        point = self.points.get(point_name)
        if not point:
            self.send_message(chat_id, "❌ Nieznane miasto")
            return
        
        # Znajdź najbliższy przelot dla tego satelity
        passes = self.tracker.get_satellite_passes(point['lat'], point['lon'], days=3)
        
        # Szukaj pasującego satelity
        target_passes = []
        for p in passes:
            if (satellite_name.lower() in p['satellite'].lower() or 
                satellite_name.lower() in p.get('type', '').lower()):
                target_passes.append(p)
        
        if not target_passes:
            self.send_message(chat_id, 
                f"❌ Brak przelotów '{satellite_name}' nad {point['name']} w ciągu 3 dni.\n"
                f"ℹ️ Spróbuj inne miasto lub satelitę."
            )
            return
        
        # Weź najlepszy przelot
        best_pass = max(target_passes, key=lambda x: x['photo_chance'])
        
        self.send_message(chat_id, 
            f"🤖 Analizuję przelot {best_pass['satellite']}...\n"
            f"📍 {point['name']} | ⭐ {best_pass['photo_chance']:.0f}%\n"
            f"⏳ Analiza AI może chwilę potrwać..."
        )
        
        # Pobierz dane pogodowe (mock)
        weather_data = {
            'success': True,
            'clouds': random.randint(10, 80),
            'temp': random.uniform(5, 25),
            'wind_speed': random.uniform(1, 10)
        }
        
        # Wykonaj analizę
        analysis = self.deepseek.analyze_satellite_opportunity(
            best_pass, point, weather_data
        )
        
        message = f"🤖 <b>ANALIZA AI - {point['name'].upper()}</b>\n\n"
        message += f"🛰️ <b>{analysis['satellite']}</b>\n"
        message += f"⭐ <b>Szansa ogólna:</b> {analysis['chance']:.0f}%\n\n"
        
        # Analiza
        if analysis['analysis']:
            message += "📊 <b>ANALIZA:</b>\n"
            # Ogranicz długość
            analysis_text = analysis['analysis']
            if len(analysis_text) > 400:
                analysis_text = analysis_text[:397] + "..."
            message += analysis_text + "\n\n"
        
        # Zalecenia
        if analysis['technical_recommendations']:
            message += "⚙️ <b>ZALECENIA TECHNICZNE:</b>\n"
            for rec in analysis['technical_recommendations'][:4]:
                message += f"• {rec}\n"
            message += "\n"
        
        # Przygotowanie
        if analysis['preparation_steps']:
            message += "📋 <b>PRZYGOTOWANIE:</b>\n"
            for step in analysis['preparation_steps'][:3]:
                message += f"• {step}\n"
            message += "\n"
        
        # Problemy
        if analysis['potential_problems']:
            message += "⚠️ <b>POTENCJALNE PROBLEMY:</b>\n"
            for prob in analysis['potential_problems'][:2]:
                message += f"• {prob}\n"
            message += "\n"
        
        message += f"⏱️ <b>Czas przygotowania:</b> {analysis['prep_time_minutes']} minut\n"
        
        # Dodaj szczegóły przelotu
        start_local = best_pass['start_utc'] + timedelta(hours=1)
        message += f"🕐 <b>Czas przelotu:</b> {start_local.strftime('%d.%m %H:%M')}\n"
        message += f"📍 <b>Lokalizacja:</b> {point['lat']:.3f}°N, {point['lon']:.3f}°E"
        
        self.send_message(chat_id, message)

# ====================== INICJALIZACJA ======================

bot = SimpleTelegramBot()

# ====================== ENDPOINTY FLASK ======================

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🛰️ Satellite Photo Predictor</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
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
            .feature {
                background: rgba(255, 255, 255, 0.05);
                padding: 20px;
                border-radius: 10px;
                margin: 15px 0;
                border-left: 5px solid #0088cc;
            }
            .commands {
                background: rgba(0, 0, 0, 0.2);
                padding: 25px;
                border-radius: 15px;
                margin-top: 30px;
            }
            code {
                background: rgba(0, 0, 0, 0.3);
                padding: 8px 12px;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                display: inline-block;
                margin: 5px;
                font-size: 0.9em;
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
            .api-status {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .api-item {
                background: rgba(255, 255, 255, 0.05);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            .api-item.ok {
                border-left: 5px solid #4CAF50;
            }
            .api-item.warning {
                border-left: 5px solid #ff9800;
            }
            .api-item.error {
                border-left: 5px solid #f44336;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ Satellite Photo Predictor</h1>
            <div class="subtitle">v6.5 - System przewidywania szans na zdjęcia satelitarne</div>
            
            <div class="status">
                ✅ <b>SYSTEM AKTYWNY</b> | 📡 Śledzenie satelitów | 🤖 Analiza AI | 🌍 Render.com
            </div>
            
            <div class="feature">
                <h3>🎯 Cel systemu:</h3>
                <p>Pomagam przewidzieć kiedy i gdzie stanąć, aby zrobić dobre zdjęcie satelity obserwacyjnego przelatującego nad Twoją lokalizacją.</p>
            </div>
            
            <div class="api-status">
                <div class="api-item ''' + ('ok' if TELEGRAM_BOT_API else 'error') + '''">
                    <h3>🤖 Telegram Bot</h3>
                    <p>''' + ('✅ Aktywny' if TELEGRAM_BOT_API else '❌ Brak tokena') + '''</p>
                </div>
                <div class="api-item ''' + ('ok' if N2YO_API_KEY else 'warning') + '''">
                    <h3>🛰️ N2YO API</h3>
                    <p>''' + ('✅ Aktywny' if N2YO_API_KEY else '⚠️ Tryb demo') + '''</p>
                </div>
                <div class="api-item ''' + ('ok' if DEEPSEEK_API_KEY else 'warning') + '''">
                    <h3>🤖 DeepSeek AI</h3>
                    <p>''' + ('✅ Aktywny' if DEEPSEEK_API_KEY else '⚠️ Brak klucza') + '''</p>
                </div>
            </div>
            
            <div class="commands">
                <h3>📋 Główne komendy Telegram:</h3>
                
                <p><code>/start</code> - Informacje o bocie</p>
                <p><code>/help</code> - Pomoc i przykłady</p>
                <p><code>/points</code> - Dostępne lokalizacje</p>
                
                <h4>🛰️ Obserwacje satelitarne:</h4>
                <p><code>/passes [miasto]</code> - Przeloty satelitów</p>
                <p><code>/best [miasto]</code> - Najlepsza okazja</p>
                <p><code>/track [miasto]</code> - Śledzenie na żywo</p>
                <p><code>/analyze [miasto] [sat]</code> - Analiza AI</p>
                
                <h4>📍 Przykładowe miasta:</h4>
                <p><code>warszawa</code>, <code>krakow</code>, <code>gdansk</code>, <code>wroclaw</code></p>
                <p><code>poznan</code>, <code>bialystok</code>, <code>rzeszow</code>, <code>katowice</code></p>
                
                <h4>🛰️ Przykładowe satelity:</h4>
                <p><code>iss</code>, <code>landsat</code>, <code>sentinel</code>, <code>worldview</code></p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/PcSentinel_Bot" class="telegram-link" target="_blank">
                    💬 Rozpocznij z botem @PcSentinel_Bot
                </a>
            </div>
            
            <div style="margin-top: 30px; font-size: 0.9em; opacity: 0.8; text-align: center;">
                <p>🌍 System oblicza szanse na zdjęcia na podstawie trajektorii, wysokości przelotu, typu satelity i warunków obserwacyjnych.</p>
                <p>🚀 Wersja 6.5 | Bez SciPy | Optymalizacja dla Render.com</p>
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
        "version": "6.5",
        "timestamp": datetime.now().isoformat(),
        "system": "Satellite Photo Predictor",
        "features": [
            "satellite_tracking",
            "photo_chance_calculation",
            "ai_analysis",
            "telegram_bot"
        ],
        "apis": {
            "telegram": bool(TELEGRAM_BOT_API),
            "n2yo": bool(N2YO_API_KEY),
            "deepseek": bool(DEEPSEEK_API_KEY),
            "satellite_count": len(bot.tracker.observation_satellites),
            "location_count": len(bot.points)
        }
    })

@app.route('/api/satellite/passes', methods=['GET'])
def api_satellite_passes():
    """API do pobierania przelotów satelitów"""
    try:
        lat = float(request.args.get('lat', 52.2297))
        lon = float(request.args.get('lon', 21.0122))
        days = int(request.args.get('days', 3))
        min_elevation = float(request.args.get('min_elevation', 15))
        
        passes = bot.tracker.get_satellite_passes(lat, lon, days=days, 
                                                 min_elevation=min_elevation)
        
        # Formatuj dla API
        formatted_passes = []
        for p in passes:
            formatted_passes.append({
                'satellite': p['satellite'],
                'satellite_id': p['satellite_id'],
                'type': p['type'],
                'start_utc': p['start_utc'].isoformat(),
                'max_elevation': p['max_elevation'],
                'duration': p['duration'],
                'photo_chance': p['photo_chance'],
                'recommended_angle': p['recommended_angle']
            })
        
        return jsonify({
            'status': 'success',
            'count': len(formatted_passes),
            'passes': formatted_passes,
            'location': {'lat': lat, 'lon': lon},
            'parameters': {'days': days, 'min_elevation': min_elevation}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/satellite/best', methods=['GET'])
def api_satellite_best():
    """API do znalezienia najlepszej okazji"""
    try:
        lat = float(request.args.get('lat', 52.2297))
        lon = float(request.args.get('lon', 21.0122))
        hours = int(request.args.get('hours', 24))
        
        opportunity = bot.tracker.get_best_photo_opportunity(lat, lon, hours)
        
        if opportunity:
            return jsonify({
                'status': 'success',
                'opportunity': {
                    'satellite': opportunity['satellite'],
                    'photo_chance': opportunity['photo_chance'],
                    'start_utc': opportunity['start_utc'].isoformat(),
                    'max_elevation': opportunity['max_elevation'],
                    'duration': opportunity['duration'],
                    'recommended_angle': opportunity['recommended_angle'],
                    'instructions': opportunity.get('instructions', ''),
                    'equipment': opportunity.get('equipment_recommendation', '')
                }
            })
        else:
            return jsonify({
                'status': 'success',
                'message': 'No good opportunities found',
                'opportunity': None
            })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🛰️ URUCHAMIANIE SATELLITE PHOTO PREDICTOR v6.5")
    print("=" * 80)
    
    # Log status API
    print("🔧 STATUS SYSTEMU:")
    print(f"   🤖 Telegram Bot: {'✅ AKTYWNY' if bot.available else '❌ NIEDOSTĘPNY'}")
    print(f"   🛰️ N2YO API: {'✅ AKTYWNY' if N2YO_API_KEY else '⚠️ TRYB DEMO'}")
    print(f"   🤖 DeepSeek AI: {'✅ AKTYWNY' if DEEPSEEK_API_KEY else '⚠️ BRAK'}")
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
                print(f"ℹ️ Ustaw ręcznie: https://api.telegram.org/bot{TELEGRAM_BOT_API}/setWebhook?url={webhook_url}")
        except Exception as e:
            print(f"⚠️ Nie udało się ustawić webhooka: {e}")
    else:
        print("⚠️ Brak tokena Telegram - webhook nieaktywny")
    
    print("\n📡 KOMENDY TELEGRAM:")
    print("   /passes [miasto] - przeloty satelitów")
    print("   /best [miasto] - najlepsza okazja")
    print("   /track [miasto] - śledzenie na żywo")
    print("   /analyze [miasto] [satelita] - analiza AI")
    
    print("\n🌐 DOSTĘPNE ENDPOINTY:")
    print(f"   {RENDER_URL}/ - strona główna")
    print(f"   {RENDER_URL}/status - status systemu")
    print(f"   {RENDER_URL}/api/satellite/passes - API przelotów")
    print(f"   {RENDER_URL}/api/satellite/best - API najlepszej okazji")
    print("=" * 80)
    print("🚀 SYSTEM GOTOWY DO DZIAŁANIA!")
    print("=" * 80)
    
    # Uruchom aplikację
    app.run(host="0.0.0.0", port=PORT, debug=False)