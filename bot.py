#!/usr/bin/env python3
"""
🛰️ AI-POWERED EARTH OBSERVATORY v8.0
🤖 DeepSeek AI jako centralny mózg systemu
🎯 Inteligentne raporty, prognozy i rekomendacje
🚀 Pełna integracja wszystkich API w jeden spójny system
"""

import os
import json
import time
import math
import random
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, AsyncGenerator
from flask import Flask, request, jsonify
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

# ====================== KONFIGURACJA ======================
print("=" * 80)
print("🤖 AI-POWERED EARTH OBSERVATORY v8.0")
print("🚀 DeepSeek AI jako centralny mózg systemu")
print("=" * 80)

# WSZYSTKIE API KLUCZE
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
N2YO_API_KEY = os.getenv("N2YO_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
USGS_API_KEY = os.getenv("USGS_API_KEY", "")
RENDER_URL = os.getenv("RENDER_URL", "https://your-app.onrender.com")
PORT = int(os.getenv("PORT", 10000))

# ====================== ENUMS & DATA CLASSES ======================

class ObservationType(Enum):
    SATELLITE = "satellite"
    EARTHQUAKE = "earthquake"
    ASTEROID = "asteroid"
    WEATHER = "weather"
    AURORA = "aurora"
    METEOR = "meteor"

class PriorityLevel(Enum):
    CRITICAL = "🔴"
    HIGH = "🟠" 
    MEDIUM = "🟡"
    LOW = "🟢"
    INFO = "🔵"

@dataclass
class Alert:
    type: ObservationType
    priority: PriorityLevel
    title: str
    description: str
    location: Optional[Dict[str, float]]
    time: datetime
    confidence: float  # 0-100%
    action_items: List[str]
    related_data: Dict[str, Any]

@dataclass
class SatelliteOpportunity:
    satellite: str
    time_utc: datetime
    location: Dict[str, float]  # gdzie stanąć
    look_angle: Dict[str, float]
    chance_percent: float
    camera_info: Dict[str, Any]
    weather_score: float
    equipment_recommendations: List[str]

@dataclass
class AIAnalysis:
    summary: str
    alerts: List[Alert]
    opportunities: List[SatelliteOpportunity]
    recommendations: List[str]
    risk_assessment: Dict[str, float]
    best_time_window: Dict[str, Any]
    data_sources: List[str]

# ====================== UNIVERSAL DATA COLLECTOR ======================

class UniversalDataCollector:
    """Zbiera WSZYSTKIE dane ze wszystkich API"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.CACHE_DURATION = 300  # 5 minut
        
    async def collect_all_data(self, user_location: Dict[str, float] = None) -> Dict[str, Any]:
        """Zbierz WSZYSTKIE dane z wszystkich API"""
        tasks = []
        
        # Jeśli mamy lokalizację użytkownika
        if user_location:
            tasks.extend([
                self.get_weather_data(user_location),
                self.get_satellite_passes(user_location),
                self.get_visibility_zones(user_location)
            ])
        
        # Dane globalne
        tasks.extend([
            self.get_earthquake_data(),
            self.get_asteroid_data(),
            self.get_apod_data(),
            self.get_space_weather(),
            self.get_aurora_forecast(),
            self.get_meteor_showers()
        ])
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Kompiluj wyniki
        all_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_location": user_location,
            "weather": None,
            "earthquakes": [],
            "asteroids": [],
            "satellite_passes": [],
            "visibility_zones": [],
            "apod": None,
            "space_weather": None,
            "aurora": None,
            "meteors": None
        }
        
        for result in results:
            if isinstance(result, dict):
                if "weather" in result:
                    all_data["weather"] = result["weather"]
                elif "earthquakes" in result:
                    all_data["earthquakes"] = result["earthquakes"]
                elif "asteroids" in result:
                    all_data["asteroids"] = result["asteroids"]
                elif "satellite_passes" in result:
                    all_data["satellite_passes"] = result["satellite_passes"]
                elif "visibility_zones" in result:
                    all_data["visibility_zones"] = result["visibility_zones"]
                elif "apod" in result:
                    all_data["apod"] = result["apod"]
                elif "space_weather" in result:
                    all_data["space_weather"] = result["space_weather"]
                elif "aurora" in result:
                    all_data["aurora"] = result["aurora"]
                elif "meteors" in result:
                    all_data["meteors"] = result["meteors"]
        
        return all_data
    
    async def get_weather_data(self, location: Dict[str, float]) -> Dict:
        """Pobierz dane pogodowe"""
        cache_key = f"weather_{location['lat']}_{location['lon']}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.openweathermap.org/data/2.5/onecall"
                params = {
                    'lat': location['lat'],
                    'lon': location['lon'],
                    'appid': OPENWEATHER_API_KEY,
                    'units': 'metric',
                    'exclude': 'minutely',
                    'lang': 'pl'
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result = {
                            "weather": {
                                "current": data.get('current', {}),
                                "hourly": data.get('hourly', [])[:12],
                                "daily": data.get('daily', [])[:3],
                                "alerts": data.get('alerts', [])
                            }
                        }
                        
                        self._cache_data(cache_key, result)
                        return result
        except:
            pass
        
        return {"weather": None}
    
    async def get_earthquake_data(self) -> Dict:
        """Pobierz dane o trzęsieniach ziemi"""
        cache_key = "earthquakes"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
                params = {
                    "format": "geojson",
                    "starttime": (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"),
                    "endtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                    "minmagnitude": 4.0,
                    "orderby": "time",
                    "limit": 20
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
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
                                'significance': props.get('sig', 0)
                            })
                        
                        result = {"earthquakes": earthquakes}
                        self._cache_data(cache_key, result)
                        return result
        except:
            pass
        
        return {"earthquakes": []}
    
    async def get_asteroid_data(self) -> Dict:
        """Pobierz dane o asteroidach"""
        cache_key = "asteroids"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            async with aiohttp.ClientSession() as session:
                start_date = datetime.now().strftime('%Y-%m-%d')
                end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                
                url = "https://api.nasa.gov/neo/rest/v1/feed"
                params = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'api_key': NASA_API_KEY
                }
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        asteroids = []
                        for date in data.get('near_earth_objects', {}):
                            for asteroid in data['near_earth_objects'][date]:
                                for approach in asteroid.get('close_approach_data', []):
                                    asteroids.append({
                                        'name': asteroid['name'],
                                        'hazardous': asteroid['is_potentially_hazardous_asteroid'],
                                        'diameter_min': asteroid['estimated_diameter']['meters']['estimated_diameter_min'],
                                        'diameter_max': asteroid['estimated_diameter']['meters']['estimated_diameter_max'],
                                        'miss_distance_km': float(approach['miss_distance']['kilometers']),
                                        'velocity_kps': float(approach['relative_velocity']['kilometers_per_second']),
                                        'approach_time': approach['close_approach_date_full']
                                    })
                        
                        result = {"asteroids": asteroids[:10]}
                        self._cache_data(cache_key, result)
                        return result
        except:
            pass
        
        return {"asteroids": []}
    
    async def get_satellite_passes(self, location: Dict[str, float]) -> Dict:
        """Pobierz przeloty satelitów"""
        cache_key = f"sat_passes_{location['lat']}_{location['lon']}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        # Obserwowane satelity
        satellites = [
            {"name": "ISS", "norad_id": 25544},
            {"name": "Landsat 8", "norad_id": 39084},
            {"name": "Sentinel-2A", "norad_id": 40697},
            {"name": "Hubble", "norad_id": 20580},
            {"name": "NOAA-20", "norad_id": 43013}
        ]
        
        passes = []
        
        for sat in satellites:
            try:
                if N2YO_API_KEY:
                    url = f"https://api.n2yo.com/rest/v1/satellite/radiopasses/{sat['norad_id']}/{location['lat']}/{location['lon']}/0/2/30"
                    params = {'apiKey': N2YO_API_KEY}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                for pass_data in data.get('passes', []):
                                    passes.append({
                                        'satellite': sat['name'],
                                        'start_utc': datetime.utcfromtimestamp(pass_data['startUTC']),
                                        'max_elevation': pass_data['maxEl'],
                                        'duration': pass_data['endUTC'] - pass_data['startUTC']
                                    })
            except:
                continue
        
        result = {"satellite_passes": passes[:10]}
        self._cache_data(cache_key, result)
        return result
    
    async def get_visibility_zones(self, location: Dict[str, float]) -> Dict:
        """Oblicz strefy widoczności dla satelitów"""
        cache_key = f"visibility_{location['lat']}_{location['lon']}"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        # Symulacja stref widoczności
        zones = []
        now = datetime.utcnow()
        
        for i in range(5):
            sat_time = now + timedelta(hours=i*3)
            
            # Generuj realistyczne strefy
            zone = {
                'satellite': f"Satelita_{i+1}",
                'time_utc': sat_time,
                'optimal_position': {
                    'lat': location['lat'] + random.uniform(-0.5, 0.5),
                    'lon': location['lon'] + random.uniform(-0.5, 0.5)
                },
                'visibility_radius_km': random.uniform(50, 200),
                'chance_percent': random.uniform(30, 95)
            }
            zones.append(zone)
        
        result = {"visibility_zones": zones}
        self._cache_data(cache_key, result)
        return result
    
    async def get_apod_data(self) -> Dict:
        """Astronomy Picture of the Day"""
        cache_key = "apod"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.nasa.gov/planetary/apod"
                params = {'api_key': NASA_API_KEY}
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = {"apod": data}
                        self._cache_data(cache_key, result)
                        return result
        except:
            pass
        
        return {"apod": None}
    
    async def get_space_weather(self) -> Dict:
        """Pogoda kosmiczna"""
        cache_key = "space_weather"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        # Symulacja danych o pogodzie kosmicznej
        result = {
            "space_weather": {
                "solar_flares": random.randint(0, 3),
                "geomagnetic_storm": random.choice(["quiet", "unsettled", "active", "storm"]),
                "kp_index": random.uniform(0, 9),
                "aurora_chance": random.uniform(0, 100)
            }
        }
        
        self._cache_data(cache_key, result)
        return result
    
    async def get_aurora_forecast(self) -> Dict:
        """Prognoza zorzy polarnej"""
        cache_key = "aurora"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        result = {
            "aurora": {
                "forecast": random.uniform(0, 100),
                "visibility_lat": random.uniform(50, 70),
                "best_time": (datetime.now() + timedelta(hours=random.randint(0, 12))).strftime("%H:%M")
            }
        }
        
        self._cache_data(cache_key, result)
        return result
    
    async def get_meteor_showers(self) -> Dict:
        """Deszcze meteorów"""
        cache_key = "meteors"
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        showers = [
            {"name": "Perseidy", "peak": "2024-08-12", "rate_per_hour": 100, "active": True},
            {"name": "Geminidy", "peak": "2024-12-14", "rate_per_hour": 150, "active": False},
            {"name": "Kwadrantydy", "peak": "2024-01-03", "rate_per_hour": 120, "active": False}
        ]
        
        result = {"meteors": showers}
        self._cache_data(cache_key, result)
        return result
    
    def _is_cached(self, key: str) -> bool:
        """Sprawdź czy dane są w cache"""
        if key in self.cache and key in self.cache_time:
            elapsed = time.time() - self.cache_time[key]
            return elapsed < self.CACHE_DURATION
        return False
    
    def _cache_data(self, key: str, data: Dict):
        """Zapisz dane w cache"""
        self.cache[key] = data
        self.cache_time[key] = time.time()

# ====================== DEEPSEEK AI ORCHESTRATOR ======================

class DeepSeekOrchestrator:
    """Centralny mózg systemu - analizuje WSZYSTKO i daje inteligentne rekomendacje"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.available = bool(api_key)
        
        # Prompt templates dla różnych scenariuszy
        self.prompt_templates = {
            "full_analysis": """
            JESTEŚ GŁÓWNYM ANalitykiem SYSTEMU OBSERWACJI ZIEMI AI-POWERED EARTH OBSERVATORY.
            
            TWOJE ZADANIE: Przeanalizuj WSZYSTKIE dostępne dane i przygotuj KOMPLETNY RAPORT DZIAŁANIA.
            
            DOSTĘPNE DANE:
            {all_data_summary}
            
            KONTEKST UŻYTKOWNIKA: {user_context}
            
            FORMATUJ ODPOWIEDŹ W NASTĘPUJĄCY SPOSÓB:
            
            🎯 RAPORT GŁÓWNY AI:
            [2-3 zdania podsumowania najważniejszych informacji]
            
            🔴 ALERTY KRYTYCZNE:
            [jeśli są - lista alertów z priorytetem]
            [jeśli nie ma - "Brak krytycznych alertów"]
            
            🌟 NAJLEPSZE OKAZJE OBSERWACYJNE (następne 24h):
            1. [Nazwa okazji] - [Czas] - [Szansa %] - [Krótki opis]
            2. [itd...]
            
            📊 ANALIZA WARUNKÓW:
            • Pogoda: [analiza]
            • Warunki kosmiczne: [analiza]
            • Czynniki ryzyka: [analiza]
            
            🎯 REKOMENDACJE DZIAŁANIA:
            1. [Konkretna akcja 1]
            2. [Konkretna akcja 2]
            3. [Konkretna akcja 3]
            
            📈 PROGNOZA NA NAJBLIŻSZE GODZINY:
            [Prognoza co się będzie działo]
            
            🤔 CO OBSERWOWAĆ:
            [Lista obiektów/zdarzeń wartych uwagi]
            
            Użyj emoji dla lepszej czytelności. Bądź konkretny i praktyczny.
            """,
            
            "opportunity_analysis": """
            ANALIZA KONKRETNEJ OKAZJI OBSERWACYJNEJ
            
            DANE OKAZJI:
            {opportunity_data}
            
            DANE POGODOWE:
            {weather_data}
            
            DODATKOWE CZYNNIKI:
            {additional_factors}
            
            PRZYGOTUJ SZCZEGÓŁOWĄ ANALIZĘ WRAZ Z:
            1. Dokładnymi współrzędnymi gdzie stanąć
            2. Sprzętem potrzebnym do obserwacji
            3. Ustawieniami aparatu
            4. Potencjalnymi problemami i ich rozwiązaniami
            5. Alternatywnymi planami
            """,
            
            "alert_analysis": """
            ANALIZA ALERTU I PLAN REAKCJI
            
            TYP ALERTU: {alert_type}
            PRIORYTET: {priority}
            OPIS: {description}
            
            DANE KONTEKSTOWE:
            {context_data}
            
            PRZYGOTUJ PLAN DZIAŁANIA:
            1. Natychmiastowe działania
            2. Środki ostrożności
            3. Monitorowanie sytuacji
            4. Plan ewakuacji/backup
            """,
            
            "weather_impact": """
            ANALIZA WPŁYWU POGODY NA OBSERWACJE
            
            DANE POGODOWE:
            {weather_data}
            
            PLANOWANE OBSERWACJE:
            {planned_observations}
            
            OCENA:
            1. Jaki wpływ będzie miała pogoda?
            2. Które okno czasowe jest najlepsze?
            3. Jakie alternatywne lokalizacje?
            4. Zalecany sprzęt ochronny
            """
        }
    
    async def analyze_all_data(self, all_data: Dict, user_context: str = "") -> AIAnalysis:
        """Przeanalizuj WSZYSTKIE dane i przygotuj kompletny raport"""
        if not self.available:
            return self._generate_mock_analysis(all_data)
        
        try:
            # Przygotuj podsumowanie danych
            data_summary = self._prepare_data_summary(all_data)
            
            prompt = self.prompt_templates["full_analysis"].format(
                all_data_summary=data_summary,
                user_context=user_context
            )
            
            response = await self._call_deepseek(prompt, max_tokens=2000)
            
            if response:
                # Parsuj odpowiedź
                analysis = self._parse_ai_response(response, all_data)
                return analysis
            else:
                return self._generate_mock_analysis(all_data)
                
        except Exception as e:
            print(f"DeepSeek analysis error: {e}")
            return self._generate_mock_analysis(all_data)
    
    async def analyze_opportunity(self, opportunity_data: Dict, 
                                 weather_data: Dict, context: Dict) -> Dict:
        """Przeanalizuj konkretną okazję"""
        if not self.available:
            return self._mock_opportunity_analysis(opportunity_data)
        
        try:
            prompt = self.prompt_templates["opportunity_analysis"].format(
                opportunity_data=json.dumps(opportunity_data, indent=2),
                weather_data=json.dumps(weather_data, indent=2),
                additional_factors=json.dumps(context, indent=2)
            )
            
            response = await self._call_deepseek(prompt, max_tokens=1500)
            
            if response:
                return {"analysis": response}
            else:
                return self._mock_opportunity_analysis(opportunity_data)
                
        except Exception as e:
            print(f"Opportunity analysis error: {e}")
            return self._mock_opportunity_analysis(opportunity_data)
    
    async def generate_daily_briefing(self, location: Dict[str, float]) -> Dict:
        """Wygeneruj codzienne podsumowanie dla lokalizacji"""
        collector = UniversalDataCollector()
        all_data = await collector.collect_all_data(location)
        
        analysis = await self.analyze_all_data(all_data, f"Dzienne podsumowanie dla lokalizacji: {location}")
        
        # Dodaj specyficzne elementy dla briefingu
        briefing = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "location": location,
            "analysis": analysis,
            "key_events": self._extract_key_events(all_data),
            "recommended_equipment": self._recommend_equipment(analysis, all_data),
            "weather_outlook": self._extract_weather_outlook(all_data),
            "space_conditions": all_data.get("space_weather", {}),
            "best_times": self._calculate_best_times(all_data)
        }
        
        return briefing
    
    async def answer_question(self, question: str, context_data: Dict) -> Dict:
        """Odpowiedz na dowolne pytanie na podstawie danych"""
        if not self.available:
            return {"answer": "DeepSeek API nie jest dostępne"}
        
        try:
            prompt = f"""
            JESTEŚ EKSPERTEM OD OBSERWACJI ZIEMI I ASTROFOTOGRAFII.
            
            PYTANIE UŻYTKOWNIKA: {question}
            
            DOSTĘPNE DANE KONTEKSTOWE:
            {json.dumps(context_data, indent=2)}
            
            ODPOWIEDZ:
            1. Bezpośrednio na pytanie
            2. Podaj praktyczne wskazówki
            3. Jeśli brakuje danych - powiedz czego potrzeba
            4. Zaproponuj alternatywy jeśli pytanie nie ma rozwiązania
            """
            
            response = await self._call_deepseek(prompt, max_tokens=1000)
            
            if response:
                return {
                    "answer": response,
                    "sources": list(context_data.keys()),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"answer": "Nie udało się uzyskać odpowiedzi"}
                
        except Exception as e:
            print(f"Question answering error: {e}")
            return {"answer": f"Błąd analizy: {str(e)}"}
    
    async def _call_deepseek(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Wywołaj API DeepSeek"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Jesteś głównym analitykiem AI-Powered Earth Observatory. Jesteś ekspertem od obserwacji Ziemi, astrofotografii, meteorologii i nauk o Ziemi."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=headers, timeout=60) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        print(f"DeepSeek API error: {response.status}")
                        return None
                        
        except Exception as e:
            print(f"DeepSeek call error: {e}")
            return None
    
    def _prepare_data_summary(self, all_data: Dict) -> str:
        """Przygotuj podsumowanie danych dla AI"""
        summary = []
        
        if all_data.get("weather"):
            summary.append(f"Pogoda: {len(all_data['weather'].get('hourly', []))} prognoz godzinowych")
        
        if all_data.get("earthquakes"):
            summary.append(f"Trzęsienia ziemi: {len(all_data['earthquakes'])} w ciągu 24h")
        
        if all_data.get("asteroids"):
            summary.append(f"Asteroidy: {len(all_data['asteroids'])} w ciągu 7 dni")
        
        if all_data.get("satellite_passes"):
            summary.append(f"Przeloty satelitów: {len(all_data['satellite_passes'])}")
        
        if all_data.get("visibility_zones"):
            summary.append(f"Strefy widoczności: {len(all_data['visibility_zones'])}")
        
        if all_data.get("apod"):
            summary.append("APOD: Dostępne")
        
        if all_data.get("space_weather"):
            summary.append("Pogoda kosmiczna: Dostępna")
        
        if all_data.get("aurora"):
            summary.append("Prognoza zorzy: Dostępna")
        
        if all_data.get("meteors"):
            summary.append(f"Deszcze meteorów: {len(all_data['meteors'])}")
        
        return "\n".join(summary)
    
    def _parse_ai_response(self, response: str, all_data: Dict) -> AIAnalysis:
        """Parsuj odpowiedź AI na strukturę AIAnalysis"""
        # To uproszczony parser - w rzeczywistości potrzebowałbyś bardziej zaawansowanej logiki
        lines = response.split('\n')
        
        alerts = []
        opportunities = []
        recommendations = []
        
        current_section = ""
        
        for line in lines:
            line = line.strip()
            
            if "🔴 ALERTY" in line:
                current_section = "alerts"
            elif "🌟 NAJLEPSZE OKAZJE" in line:
                current_section = "opportunities"
            elif "🎯 REKOMENDACJE" in line:
                current_section = "recommendations"
            elif line.startswith("•") or line.startswith("-") or line[0].isdigit():
                if current_section == "alerts" and line:
                    alerts.append(Alert(
                        type=ObservationType.EARTHQUAKE if "trzęsienie" in line.lower() else ObservationType.SATELLITE,
                        priority=PriorityLevel.HIGH if "🔴" in line else PriorityLevel.MEDIUM,
                        title=line[:50],
                        description=line,
                        location=None,
                        time=datetime.now(),
                        confidence=80.0,
                        action_items=["Sprawdź szczegóły"],
                        related_data={}
                    ))
                elif current_section == "opportunities" and line:
                    # Przykładowa okazja
                    opportunities.append(SatelliteOpportunity(
                        satellite="Satelita",
                        time_utc=datetime.now() + timedelta(hours=2),
                        location={"lat": 52.23, "lon": 21.01},
                        look_angle={"azimuth": 180, "elevation": 45},
                        chance_percent=random.uniform(50, 95),
                        camera_info={"resolution": "15m/px", "swath": "185km"},
                        weather_score=random.uniform(60, 100),
                        equipment_recommendations=["Statyw", "Teleobiektyw 200mm+"]
                    ))
                elif current_section == "recommendations" and line:
                    recommendations.append(line.lstrip("•- 1234567890. "))
        
        # Jeśli nie udało się sparsować, użyj mocka
        if not alerts and not opportunities and not recommendations:
            return self._generate_mock_analysis(all_data)
        
        return AIAnalysis(
            summary=response[:500] + "..." if len(response) > 500 else response,
            alerts=alerts[:3],
            opportunities=opportunities[:3],
            recommendations=recommendations[:5],
            risk_assessment={
                "weather_risk": random.uniform(0, 100),
                "visibility_risk": random.uniform(0, 100),
                "equipment_risk": random.uniform(0, 50)
            },
            best_time_window={
                "start": (datetime.now() + timedelta(hours=1)).isoformat(),
                "end": (datetime.now() + timedelta(hours=3)).isoformat(),
                "reason": "Najlepsze warunki pogodowe"
            },
            data_sources=list(all_data.keys())
        )
    
    def _generate_mock_analysis(self, all_data: Dict) -> AIAnalysis:
        """Generuj przykładową analizę gdy DeepSeek niedostępny"""
        return AIAnalysis(
            summary="Analiza AI niedostępna. Używam danych symulacyjnych.",
            alerts=[
                Alert(
                    type=ObservationType.EARTHQUAKE,
                    priority=PriorityLevel.MEDIUM,
                    title="Trzęsienie ziemi 4.5M w regionie",
                    description="Umiarkowane trzęsienie wykryte przez USGS",
                    location={"lat": 52.23, "lon": 21.01},
                    time=datetime.now() - timedelta(hours=2),
                    confidence=85.0,
                    action_items=["Sprawdź mapę trzęsień", "Monitoruj wstrząsy wtórne"],
                    related_data={}
                )
            ],
            opportunities=[
                SatelliteOpportunity(
                    satellite="Landsat 8",
                    time_utc=datetime.now() + timedelta(hours=3),
                    location={"lat": 52.25, "lon": 21.03},
                    look_angle={"azimuth": 135, "elevation": 42},
                    chance_percent=78.5,
                    camera_info={"resolution": "15m/px", "swath": "185km"},
                    weather_score=82.0,
                    equipment_recommendations=["Statyw", "Obiektyw 70-200mm", "Wyzwalacz"]
                )
            ],
            recommendations=[
                "Przygotuj sprzęt do 20:00",
                "Sprawdź prognozę pogody na wieczór",
                "Znajdź miejsce z czystym horyzontem"
            ],
            risk_assessment={
                "weather_risk": 35.0,
                "visibility_risk": 20.0,
                "equipment_risk": 15.0
            },
            best_time_window={
                "start": (datetime.now() + timedelta(hours=2)).isoformat(),
                "end": (datetime.now() + timedelta(hours=4)).isoformat(),
                "reason": "Niskie zachmurzenie i dobre warunki"
            },
            data_sources=["USGS", "OpenWeather", "NASA", "N2YO"]
        )
    
    def _mock_opportunity_analysis(self, opportunity_data: Dict) -> Dict:
        """Mock analizy okazji"""
        return {
            "analysis": f"""
            📊 ANALIZA OKAZJI OBSERWACYJNEJ
            
            🛰️ {opportunity_data.get('satellite', 'Satelita')}
            🕐 Najlepszy czas: {opportunity_data.get('time_utc', 'N/A')}
            📍 Gdzie stanąć: {opportunity_data.get('optimal_position', {})}
            
            🎯 ZALECENIA:
            1. Przyjedź na miejsce 30 minut wcześniej
            2. Użyj statywu dla stabilności
            3. ISO ustaw na 800-1600
            4. Czas naświetlania 1-3 sekundy
            
            ⚠️ POTENCJALNE PROBLEMY:
            • Zachmurzenie może się pogorszyć
            • Wiatr może wpływać na stabilność
            
            🔄 ALTERNATYWY:
            • Jeśli warunki się pogorszą, spróbuj innym razem
            • Rozważ obserwację z innej lokalizacji
            """
        }
    
    def _extract_key_events(self, all_data: Dict) -> List[Dict]:
        """Wyodrębnij kluczowe wydarzenia z danych"""
        events = []
        
        # Trzęsienia ziemi
        for eq in all_data.get("earthquakes", []):
            if eq.get('magnitude', 0) > 5.0:
                events.append({
                    "type": "earthquake",
                    "title": f"Trzęsienie {eq['magnitude']}M",
                    "time": eq.get('time'),
                    "priority": "high"
                })
        
        # Asteroidy
        for asteroid in all_data.get("asteroids", []):
            if asteroid.get('hazardous'):
                events.append({
                    "type": "asteroid",
                    "title": f"Niebezpieczna asteroida: {asteroid['name']}",
                    "time": asteroid.get('approach_time'),
                    "priority": "medium"
                })
        
        # Satelity
        for sat in all_data.get("satellite_passes", [])[:3]:
            events.append({
                "type": "satellite",
                "title": f"Przelot {sat.get('satellite')}",
                "time": sat.get('start_utc'),
                "priority": "low"
            })
        
        return events[:5]
    
    def _recommend_equipment(self, analysis: AIAnalysis, all_data: Dict) -> List[str]:
        """Zalecenia sprzętowe na podstawie analizy"""
        equipment = ["Statyw", "Wyzwalacz zdalny"]
        
        if analysis.opportunities:
            equipment.append("Teleobiektyw 200mm+")
        
        weather = all_data.get("weather", {}).get("current", {})
        if weather.get('wind_speed', 0) > 5:
            equipment.append("Wzmocniony statyw")
        
        if random.random() > 0.5:
            equipment.append("Filtr polaryzacyjny")
        
        return equipment
    
    def _extract_weather_outlook(self, all_data: Dict) -> Dict:
        """Wyodrębnij prognozę pogody"""
        weather = all_data.get("weather", {})
        
        if not weather:
            return {"summary": "Brak danych pogodowych"}
        
        current = weather.get("current", {})
        hourly = weather.get("hourly", [])
        
        return {
            "current_temp": current.get('temp', 'N/A'),
            "conditions": current.get('weather', [{}])[0].get('description', 'N/A'),
            "clouds": current.get('clouds', 'N/A'),
            "next_6h": [h.get('weather', [{}])[0].get('description', 'N/A') for h in hourly[:6]]
        }
    
    def _calculate_best_times(self, all_data: Dict) -> List[Dict]:
        """Oblicz najlepsze czasy obserwacji"""
        best_times = []
        
        # Na podstawie pogody i przelotów satelitów
        weather = all_data.get("weather", {}).get("hourly", [])
        passes = all_data.get("satellite_passes", [])
        
        for i, hour_data in enumerate(weather[:12]):
            clouds = hour_data.get('clouds', 100)
            
            # Znajdź przeloty w tym oknie czasowym
            hour_start = datetime.now() + timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_passes = []
            for sat_pass in passes:
                if hour_start <= sat_pass.get('start_utc', datetime.min) <= hour_end:
                    hour_passes.append(sat_pass)
            
            # Oceń jakość okna
            quality = 100 - clouds  # Im mniej chmur, tym lepiej
            if hour_passes:
                quality += 20 * len(hour_passes)
            
            if quality > 50:  # Tylko dobre okna
                best_times.append({
                    "start": hour_start.strftime("%H:%M"),
                    "end": hour_end.strftime("%H:%M"),
                    "quality_score": quality,
                    "satellite_passes": len(hour_passes),
                    "clouds_percent": clouds
                })
        
        return sorted(best_times, key=lambda x: x["quality_score"], reverse=True)[:3]

# ====================== TELEGRAM BOT Z INTEGRACJĄ AI ======================

class AIPoweredTelegramBot:
    """Bot z głęboką integracją AI jako centralnym mózgiem"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.available = bool(TELEGRAM_BOT_TOKEN)
        
        # Komponenty systemu
        self.data_collector = UniversalDataCollector()
        self.ai_orchestrator = DeepSeekOrchestrator(DEEPSEEK_API_KEY)
        
        # Stan użytkownika
        self.user_profiles = {}  # chat_id -> profile
        self.user_locations = {}  # chat_id -> location
        
        # Lokalizacje
        self.locations = {
            "warszawa": {"name": "Warszawa", "lat": 52.2297, "lon": 21.0122},
            "krakow": {"name": "Kraków", "lat": 50.0614, "lon": 19.9366},
            "gdansk": {"name": "Gdańsk", "lat": 54.3722, "lon": 18.6383},
            "wroclaw": {"name": "Wrocław", "lat": 51.1079, "lon": 17.0385},
            "tatry": {"name": "Tatry", "lat": 49.2992, "lon": 19.9496},
            "mazury": {"name": "Mazury", "lat": 53.8667, "lon": 21.5000},
            "baltyk": {"name": "Bałtyk", "lat": 54.5000, "lon": 18.5500}
        }
        
        # Cache AI raportów
        self.ai_reports_cache = {}
        
        print(f"🤖 AI-Powered Bot zainicjalizowany")
        print(f"   DeepSeek AI: {'✅ AKTYWNY' if self.ai_orchestrator.available else '❌ BRAK'}")
    
    async def send_message(self, chat_id: int, text: str, parse_html: bool = True):
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
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    return response.status == 200
        except:
            return False
    
    async def send_photo(self, chat_id: int, photo_url: str, caption: str = ""):
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
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=15) as response:
                    return response.status == 200
        except:
            return False
    
    async def handle_command(self, chat_id: int, command: str, args: List[str]):
        """Obsłuż komendę z głęboką integracją AI"""
        command = command.lower()
        
        # ========== KOMENDY AI ==========
        if command == "start":
            await self.cmd_ai_start(chat_id, args)
        elif command == "ai" or command == "ask":
            await self.cmd_ai_ask(chat_id, args)
        elif command == "report" or command == "raport":
            await self.cmd_ai_report(chat_id, args)
        elif command == "briefing" or command == "podsumowanie":
            await self.cmd_daily_briefing(chat_id, args)
        elif command == "analyze" or command == "analizuj":
            await self.cmd_ai_analyze(chat_id, args)
        
        # ========== TRADYCYJNE KOMENDY ==========
        elif command == "where" or command == "gdzie":
            await self.cmd_where(chat_id, args)
        elif command == "weather" or command == "pogoda":
            await self.cmd_weather(chat_id, args)
        elif command == "earthquakes" or command == "trzesienia":
            await self.cmd_earthquakes(chat_id, args)
        elif command == "asteroids" or command == "asteroidy":
            await self.cmd_asteroids(chat_id)
        elif command == "apod":
            await self.cmd_apod(chat_id)
        elif command == "locations" or command == "lokalizacje":
            await self.cmd_locations(chat_id)
        elif command == "help" or command == "pomoc":
            await self.cmd_help(chat_id)
        else:
            await self.send_message(chat_id, "❌ Nieznana komenda. Użyj /help")
    
    # ====================== NOWE KOMENDY AI ======================
    
    async def cmd_ai_start(self, chat_id: int, args: List[str]):
        """AI-Powered Start - pełny raport AI od razu"""
        location_name = args[0] if args else "warszawa"
        location = self.locations.get(location_name)
        
        if not location:
            await self.send_message(chat_id, "❌ Nieznana lokalizacja. Użyj /locations")
            return
        
        # Zapisz lokalizację użytkownika
        self.user_locations[chat_id] = location
        
        # Wysyłamy wstępną wiadomość
        await self.send_message(chat_id,
            f"🤖 <b>AI-POWERED EARTH OBSERVATORY v8.0</b>\n\n"
            f"📍 Ustawiono lokalizację: <b>{location['name']}</b>\n"
            f"⏳ <i>AI analizuje WSZYSTKIE dane... To może chwilę potrwać.</i>\n\n"
            f"📡 Zbieram dane z:\n"
            f"• 🌤️ OpenWeather\n• 🚨 USGS\n• 🪐 NASA\n• 🛰️ N2YO\n• 🌌 Space Weather\n"
            f"• 📸 APOD\n• ☄️ Meteory\n• 🌀 Aurora\n"
        )
        
        # Zbierz WSZYSTKIE dane
        all_data = await self.data_collector.collect_all_data(location)
        
        # Analiza AI
        user_context = f"Nowy użytkownik, lokalizacja: {location['name']}"
        ai_analysis = await self.ai_orchestrator.analyze_all_data(all_data, user_context)
        
        # Zapisz w cache
        self.ai_reports_cache[chat_id] = {
            "analysis": ai_analysis,
            "timestamp": datetime.now(),
            "location": location
        }
        
        # Formatuj odpowiedź AI
        response = await self._format_ai_analysis(ai_analysis, location)
        
        # Wyślij raport
        await self.send_message(chat_id, response)
        
        # Dodaj interaktywne opcje
        await self.send_message(chat_id,
            "🎯 <b>CO DALEJ?</b>\n\n"
            "<code>/report</code> - odśwież raport\n"
            "<code>/briefing</code> - dzienne podsumowanie\n"
            "<code>/where [satelita] [czas]</code> - gdzie stanąć\n"
            "<code>/ai [pytanie]</code> - zapytaj AI\n"
            "<code>/analyze [coś]</code> - głęboka analiza\n\n"
            "💡 <i>AI zna WSZYSTKIE dane. Możesz zapytać o wszystko!</i>"
        )
    
    async def cmd_ai_ask(self, chat_id: int, args: List[str]):
        """Zapytaj AI o cokolwiek"""
        if not args:
            await self.send_message(chat_id,
                "🤖 <b>ZAPYTAJ AI O COKOLWIEK</b>\n\n"
                "<code>/ai [twoje pytanie]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/ai Kiedy najlepiej obserwować ISS?</code>\n"
                "<code>/ai Jaki sprzęt potrzebuję do fotografii satelitarnej?</code>\n"
                "<code>/ai Czy dzisiaj będzie widoczna zorza polarna?</code>\n"
                "<code>/ai Gdzie są teraz trzęsienia ziemi?</code>"
            )
            return
        
        question = " ".join(args)
        location = self.user_locations.get(chat_id, self.locations["warszawa"])
        
        await self.send_message(chat_id, f"🤖 AI analizuje pytanie: <i>{question}</i>")
        
        # Zbierz dane kontekstowe
        all_data = await self.data_collector.collect_all_data(location)
        
        # Zapytaj AI
        answer = await self.ai_orchestrator.answer_question(question, all_data)
        
        # Wyślij odpowiedź
        response = f"""
🤖 <b>ODPOWIEDŹ AI:</b>

{answer.get('answer', 'Nie udało się uzyskać odpowiedzi')}

📊 <b>Źródła danych:</b> {', '.join(answer.get('sources', []))}
🕐 <b>Czas analizy:</b> {answer.get('timestamp', 'N/A')}
"""
        await self.send_message(chat_id, response)
    
    async def cmd_ai_report(self, chat_id: int, args: List[str]):
        """Odśwież raport AI"""
        # Sprawdź cache
        cached = self.ai_reports_cache.get(chat_id)
        
        if cached and (datetime.now() - cached["timestamp"]).seconds < 1800:  # 30 minut
            location = cached["location"]
            analysis = cached["analysis"]
            
            response = await self._format_ai_analysis(analysis, location)
            await self.send_message(chat_id, response)
            return
        
        # Generuj nowy raport
        location_name = args[0] if args else None
        
        if location_name:
            location = self.locations.get(location_name)
            if not location:
                await self.send_message(chat_id, "❌ Nieznana lokalizacja")
                return
        else:
            location = self.user_locations.get(chat_id, self.locations["warszawa"])
        
        await self.send_message(chat_id, f"🤖 Generuję nowy raport AI dla {location['name']}...")
        
        all_data = await self.data_collector.collect_all_data(location)
        ai_analysis = await self.ai_orchestrator.analyze_all_data(all_data, "")
        
        # Zaktualizuj cache
        self.ai_reports_cache[chat_id] = {
            "analysis": ai_analysis,
            "timestamp": datetime.now(),
            "location": location
        }
        
        response = await self._format_ai_analysis(ai_analysis, location)
        await self.send_message(chat_id, response)
    
    async def cmd_daily_briefing(self, chat_id: int, args: List[str]):
        """Codzienne podsumowanie AI"""
        location_name = args[0] if args else None
        
        if location_name:
            location = self.locations.get(location_name)
            if not location:
                await self.send_message(chat_id, "❌ Nieznana lokalizacja")
                return
        else:
            location = self.user_locations.get(chat_id, self.locations["warszawa"])
        
        await self.send_message(chat_id,
            f"📊 <b>GENERUJĘ CODZIENNE PODSUMOWANIE AI</b>\n\n"
            f"📍 {location['name']}\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
            f"⏳ <i>AI analizuje dane z ostatnich 24h...</i>"
        )
        
        # Generuj briefing
        briefing = await self.ai_orchestrator.generate_daily_briefing(location)
        
        # Formatuj odpowiedź
        response = f"""
📊 <b>CODZIENNE PODSUMOWANIE AI</b>
📍 {location['name']} | 📅 {briefing['date']}

🎯 <b>NAJWAŻNIEJSZE WYDARZENIA:</b>
"""
        
        for i, event in enumerate(briefing.get("key_events", [])[:3], 1):
            response += f"{i}. {event['title']} ({event['time']})\n"
        
        response += f"""
        
🌤️ <b>PROGNOZA POGODY:</b>
• Temperatura: {briefing['weather_outlook'].get('current_temp', 'N/A')}°C
• Warunki: {briefing['weather_outlook'].get('conditions', 'N/A')}
• Zachmurzenie: {briefing['weather_outlook'].get('clouds', 'N/A')}%

🛰️ <b>NAJLEPSZE CZASY OBSERWACJI:</b>
"""
        
        for time_slot in briefing.get("best_times", [])[:2]:
            response += f"• {time_slot['start']}-{time_slot['end']} (jakość: {time_slot['quality_score']:.0f}%)\n"
        
        response += f"""
        
🎒 <b>ZALECANY SPRZĘT:</b>
{', '.join(briefing.get('recommended_equipment', []))}

🤖 <b>ANALIZA AI:</b>
{briefing['analysis'].summary[:500]}...
"""
        
        await self.send_message(chat_id, response)
        
        # Dodaj opcje
        await self.send_message(chat_id,
            "💡 <b>CHCESZ WIĘCEJ?</b>\n\n"
            "<code>/ai [pytanie]</code> - zapytaj o szczegóły\n"
            "<code>/where [satelita]</code> - konkretna okazja\n"
            "<code>/report</code> - pełny raport\n"
        )
    
    async def cmd_ai_analyze(self, chat_id: int, args: List[str]):
        """Głęboka analiza AI konkretnego tematu"""
        if not args:
            await self.send_message(chat_id,
                "🔍 <b>GŁĘBOKA ANALIZA AI</b>\n\n"
                "<code>/analyze [temat]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/analyze warunki do fotografii satelitarnej</code>\n"
                "<code>/analyze ryzyko trzęsień ziemi</code>\n"
                "<code>/analyze najbliższe przeloty ISS</code>\n"
                "<code>/analyze wpływ pogody na obserwacje</code>"
            )
            return
        
        topic = " ".join(args)
        location = self.user_locations.get(chat_id, self.locations["warszawa"])
        
        await self.send_message(chat_id, f"🔍 AI analizuje temat: <b>{topic}</b>")
        
        # Zbierz odpowiednie dane
        all_data = await self.data_collector.collect_all_data(location)
        
        # Przygotuj kontekst dla AI
        context = {
            "topic": topic,
            "location": location,
            "timestamp": datetime.now().isoformat(),
            "relevant_data": {}
        }
        
        # Dodaj odpowiednie dane w zależności od tematu
        if "trzęsienie" in topic.lower() or "ziemi" in topic.lower():
            context["relevant_data"]["earthquakes"] = all_data.get("earthquakes", [])
        
        if "pogod" in topic.lower() or "chmur" in topic.lower():
            context["relevant_data"]["weather"] = all_data.get("weather", {})
        
        if "satelit" in topic.lower() or "iss" in topic.lower():
            context["relevant_data"]["satellite_passes"] = all_data.get("satellite_passes", [])
            context["relevant_data"]["visibility_zones"] = all_data.get("visibility_zones", [])
        
        if "asteroid" in topic.lower() or "meteor" in topic.lower():
            context["relevant_data"]["asteroids"] = all_data.get("asteroids", [])
            context["relevant_data"]["meteors"] = all_data.get("meteors", [])
        
        if "zorza" in topic.lower() or "aurora" in topic.lower():
            context["relevant_data"]["aurora"] = all_data.get("aurora", {})
            context["relevant_data"]["space_weather"] = all_data.get("space_weather", {})
        
        # Zapytaj AI o analizę
        question = f"Przeprowadź głęboką analizę tematu: {topic}. Uwzględnij dane kontekstowe."
        answer = await self.ai_orchestrator.answer_question(question, context)
        
        # Formatuj odpowiedź
        response = f"""
🔍 <b>ANALIZA AI: {topic.upper()}</b>

{answer.get('answer', 'Brak analizy')}

📈 <b>METODOLOGIA:</b>
Analiza oparta o dane z: {', '.join(context['relevant_data'].keys())}
Lokalizacja: {location['name']}
Czas analizy: {datetime.now().strftime('%H:%M')}
"""
        await self.send_message(chat_id, response)
    
    async def _format_ai_analysis(self, analysis: AIAnalysis, location: Dict) -> str:
        """Formatuj analizę AI na ładny tekst"""
        response = f"""
🤖 <b>AI-POWERED EARTH OBSERVATORY v8.0</b>
📍 {location['name']} | 🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}

{analysis.summary}

🔴 <b>ALERTY ({len(analysis.alerts)}):</b>
"""
        
        for i, alert in enumerate(analysis.alerts, 1):
            response += f"{i}. {alert.priority.value} {alert.title}\n"
        
        response += f"""
🌟 <b>NAJLEPSZE OKAZJE ({len(analysis.opportunities)}):</b>
"""
        
        for i, opp in enumerate(analysis.opportunities, 1):
            local_time = opp.time_utc + timedelta(hours=1)
            response += f"{i}. {opp.satellite} - {local_time.strftime('%H:%M')} - {opp.chance_percent:.0f}%\n"
        
        response += f"""
📊 <b>OCENA RYZYKA:</b>
• Pogoda: {analysis.risk_assessment.get('weather_risk', 0):.0f}%
• Widoczność: {analysis.risk_assessment.get('visibility_risk', 0):.0f}%
• Sprzęt: {analysis.risk_assessment.get('equipment_risk', 0):.0f}%

🎯 <b>REKOMENDACJE AI:</b>
"""
        
        for i, rec in enumerate(analysis.recommendations[:3], 1):
            response += f"{i}. {rec}\n"
        
        best_window = analysis.best_time_window
        response += f"""
⏰ <b>NAJLEPSZE OKNO CZASOWE:</b>
{best_window.get('start', 'N/A')} - {best_window.get('end', 'N/A')}
{best_window.get('reason', '')}

📡 <b>ŹRÓDŁA DANYCH:</b>
{', '.join(analysis.data_sources)}
"""
        
        return response
    
    # ====================== TRADYCYJNE KOMENDY (Z INTEGRACJĄ AI) ======================
    
    async def cmd_where(self, chat_id: int, args: List[str]):
        """Gdzie stanąć - z analizą AI"""
        if len(args) < 1:
            await self.send_message(chat_id,
                "📍 <b>GDZIE STANĄĆ - Z ANALIZĄ AI</b>\n\n"
                "<code>/where [satelita] [czas]</code>\n\n"
                "<b>Przykłady:</b>\n"
                "<code>/where landsat 20:30</code>\n"
                "<code>/where iss</code> (czas domyślny: za 1h)\n"
                "<code>/where sentinel 18:00</code>\n\n"
                "🤖 <i>AI przeanalizuje warunki i da najlepsze rekomendacje</i>"
            )
            return
        
        sat_name = args[0].lower()
        time_str = args[1] if len(args) > 1 else None
        
        location = self.user_locations.get(chat_id, self.locations["warszawa"])
        
        # Parsuj czas
        target_time = self._parse_time(time_str)
        
        await self.send_message(chat_id,
            f"📍 AI szuka najlepszego miejsca dla {sat_name}...\n"
            f"🕐 {target_time.strftime('%H:%M')} | 📍 {location['name']}"
        )
        
        # Zbierz dane
        all_data = await self.data_collector.collect_all_data(location)
        
        # Przygotuj dane o okazji
        opportunity_data = {
            "satellite": sat_name,
            "time_utc": target_time.isoformat(),
            "location": location,
            "weather_conditions": all_data.get("weather", {}).get("current", {})
        }
        
        # Analiza AI
        analysis = await self.ai_orchestrator.analyze_opportunity(
            opportunity_data,
            all_data.get("weather", {}),
            {"user_location": location}
        )
        
        # Generuj pozycję (symulacja)
        optimal_position = {
            "lat": location["lat"] + random.uniform(-0.1, 0.1),
            "lon": location["lon"] + random.uniform(-0.1, 0.1)
        }
        
        # Formatuj odpowiedź
        response = f"""
📍 <b>GDZIE STANĄĆ - {sat_name.upper()}</b>

🤖 <b>ANALIZA AI:</b>
{analysis.get('analysis', 'Brak analizy')}

🎯 <b>OPTYMALNA POZYCJA:</b>
Szerokość: {optimal_position['lat']:.6f}°N
Długość: {optimal_position['lon']:.6f}°E
📍 {location['name']}

⏰ <b>CZAS:</b>
UTC: {target_time.strftime('%H:%M')}
Lokalny (PL): {(target_time + timedelta(hours=1)).strftime('%H:%M')}

📡 <b>UŻYJ:</b>
<code>/location {optimal_position['lat']:.6f} {optimal_position['lon']:.6f}</code>
"""
        await self.send_message(chat_id, response)
        
        # Wyślij lokalizację
        await self._send_location(chat_id, optimal_position["lat"], optimal_position["lon"])
    
    async def cmd_weather(self, chat_id: int, args: List[str]):
        """Pogoda z analizą AI"""
        location_name = args[0] if args else None
        
        if location_name:
            location = self.locations.get(location_name)
            if not location:
                await self.send_message(chat_id, "❌ Nieznana lokalizacja")
                return
        else:
            location = self.user_locations.get(chat_id, self.locations["warszawa"])
        
        await self.send_message(chat_id, f"🌤️ AI analizuje pogodę dla {location['name']}...")
        
        # Zbierz dane pogodowe
        all_data = await self.data_collector.collect_all_data(location)
        weather = all_data.get("weather", {})
        
        if not weather:
            await self.send_message(chat_id, "❌ Nie udało się pobrać danych pogodowych")
            return
        
        current = weather.get("current", {})
        
        # Zapytaj AI o analizę pogody
        question = f"Przeanalizuj te dane pogodowe i oceń warunki do obserwacji astronomicznych: {json.dumps(current, indent=2)}"
        answer = await self.ai_orchestrator.answer_question(question, {"weather": weather})
        
        # Formatuj odpowiedź
        response = f"""
🌤️ <b>POGODA - {location['name'].upper()}</b>

🌡️ Temperatura: {current.get('temp', 'N/A')}°C
🤏 Odczuwalna: {current.get('feels_like', 'N/A')}°C
💧 Wilgotność: {current.get('humidity', 'N/A')}%
☁️ Zachmurzenie: {current.get('clouds', 'N/A')}%
💨 Wiatr: {current.get('wind_speed', 'N/A')} m/s
🌅 Ciśnienie: {current.get('pressure', 'N/A')} hPa

🤖 <b>ANALIZA AI DLA OBSERWACJI:</b>
{answer.get('answer', 'Brak analizy')[:500]}...

📊 <b>OCENA WARUNKÓW:</b>
{'✅ DOBRE' if current.get('clouds', 100) < 30 else '⚠️ ŚREDNIE' if current.get('clouds', 100) < 70 else '❌ ZŁE'}
"""
        await self.send_message(chat_id, response)
        
        # Wyślij lokalizację
        await self._send_location(chat_id, location["lat"], location["lon"])
    
    async def cmd_earthquakes(self, chat_id: int, args: List[str]):
        """Trzęsienia ziemi z analizą AI"""
        min_mag = float(args[0]) if args and args[0].replace('.', '').isdigit() else 4.0
        
        await self.send_message(chat_id, f"🚨 AI analizuje trzęsienia ziemi >{min_mag}M...")
        
        all_data = await self.data_collector.collect_all_data()
        earthquakes = all_data.get("earthquakes", [])
        
        filtered = [eq for eq in earthquakes if eq.get('magnitude', 0) >= min_mag]
        
        if not filtered:
            await self.send_message(chat_id, f"🌍 Brak trzęsień >{min_mag}M w ciągu 24h.")
            return
        
        # Zapytaj AI o analizę
        question = f"Przeanalizuj te trzęsienia ziemi i oceń ryzyko: {json.dumps(filtered[:3], indent=2)}"
        answer = await self.ai_orchestrator.answer_question(question, {"earthquakes": filtered})
        
        response = f"""
🚨 <b>TRZĘSIENIA ZIEMI >{min_mag}M (24h)</b>

🤖 <b>ANALIZA AI:</b>
{answer.get('answer', 'Brak analizy')[:400]}...

📋 <b>NAJWAŻNIEJSZE ({len(filtered)}):</b>
"""
        
        for i, eq in enumerate(filtered[:5], 1):
            time_ago = datetime.utcnow() - eq['time']
            hours_ago = time_ago.total_seconds() / 3600
            
            response += f"{i}. {eq['place']}\n"
            response += f"   ⚡ {eq['magnitude']}M | 📉 {eq['depth']:.1f}km\n"
            response += f"   ⏰ {hours_ago:.1f}h temu\n\n"
        
        await self.send_message(chat_id, response)
        
        if filtered:
            await self._send_location(chat_id, filtered[0]['lat'], filtered[0]['lon'])
    
    async def cmd_asteroids(self, chat_id: int):
        """Asteroidy z analizą AI"""
        await self.send_message(chat_id, "🪐 AI analizuje przeloty asteroid...")
        
        all_data = await self.data_collector.collect_all_data()
        asteroids = all_data.get("asteroids", [])
        
        # Znajdź niebezpieczne asteroidy
        hazardous = [a for a in asteroids if a.get('hazardous')]
        
        # Zapytaj AI
        question = f"Przeanalizuj te asteroidy i oceń zagrożenie: {json.dumps(hazardous[:3], indent=2)}"
        answer = await self.ai_orchestrator.answer_question(question, {"asteroids": asteroids})
        
        response = f"""
🪐 <b>ASTEROIDY (7 dni)</b>

🤖 <b>ANALIZA AI:</b>
{answer.get('answer', 'Brak analizy')[:400]}...

⚠️ <b>NIEBEZPIECZNE: {len(hazardous)}</b>
"""
        
        for i, asteroid in enumerate(hazardous[:3], 1):
            distance_mln_km = asteroid['miss_distance_km'] / 1000000
            
            response += f"{i}. {asteroid['name']}\n"
            response += f"   🎯 {distance_mln_km:.2f} mln km\n"
            response += f"   🚀 {asteroid['velocity_kps']:.2f} km/s\n\n"
        
        response += f"📊 W sumie: {len(asteroids)} asteroid w ciągu 7 dni"
        
        await self.send_message(chat_id, response)
    
    async def cmd_apod(self, chat_id: int):
        """APOD z analizą AI"""
        await self.send_message(chat_id, "📸 AI analizuje Astronomy Picture of the Day...")
        
        all_data = await self.data_collector.collect_all_data()
        apod = all_data.get("apod", {})
        
        if not apod:
            await self.send_message(chat_id, "❌ Nie udało się pobrać APOD")
            return
        
        # Zapytaj AI o analizę zdjęcia
        question = f"Przeanalizuj to zdjęcie astronomiczne: {json.dumps(apod, indent=2)}"
        answer = await self.ai_orchestrator.answer_question(question, {"apod": apod})
        
        response = f"""
📸 <b>ASTRONOMY PICTURE OF THE DAY</b>

📅 {apod.get('date', 'Dzisiaj')}
🏷️ <b>{apod.get('title', 'Brak tytułu')}</b>

🤖 <b>ANALIZA AI:</b>
{answer.get('answer', 'Brak analizy')[:500]}...

🔗 <a href="{apod.get('url', '')}">Zobacz zdjęcie</a>
👨‍🎨 Autor: {apod.get('copyright', 'Nieznany')}
"""
        await self.send_message(chat_id, response)
    
    async def cmd_locations(self, chat_id: int):
        """Lista lokalizacji"""
        response = "📍 <b>DOSTĘPNE LOKALIZACJE:</b>\n\n"
        
        for key, loc in self.locations.items():
            response += f"• <b>{key}</b> - {loc['name']}\n"
            response += f"  📍 {loc['lat']:.4f}°N, {loc['lon']:.4f}°E\n\n"
        
        response += "🎯 <b>UŻYJ:</b> <code>/start [nazwa_lokalizacji]</code>"
        
        await self.send_message(chat_id, response)
    
    async def cmd_help(self, chat_id: int):
        """Pomoc"""
        response = """
🤖 <b>AI-POWERED EARTH OBSERVATORY v8.0</b>

🚀 <b>NOWOŚCI AI:</b>
<code>/start [lokalizacja]</code> - Pełny raport AI od razu!
<code>/ai [pytanie]</code> - Zapytaj AI o cokolwiek
<code>/report</code> - Odśwież raport AI
<code>/briefing</code> - Codzienne podsumowanie AI
<code>/analyze [temat]</code> - Głęboka analiza AI

📍 <b>OBSERWACJE SATELITARNE:</b>
<code>/where [satelita] [czas]</code> - Gdzie stanąć (z AI)

🌍 <b>DANE ZIEMSKIE:</b>
<code>/weather [lokalizacja]</code> - Pogoda z analizą AI
<code>/earthquakes [magnituda]</code> - Trzęsienia ziemi z AI
<code>/asteroids</code> - Asteroidy z AI
<code>/apod</code> - NASA APOD z AI

📍 <b>INFORMACJE:</b>
<code>/locations</code> - Lista lokalizacji

🎯 <b>PRZYKŁADY:</b>
• <code>/start warszawa</code> - Pełny raport dla Warszawy
• <code>/ai Kiedy najlepszy czas na obserwacje?</code>
• <code>/where iss 20:30</code> - Gdzie stanąć dla ISS
• <code>/analyze warunki do fotografii</code>

🤖 <i>AI zna WSZYSTKIE dane. Po prostu zapytaj!</i>
"""
        await self.send_message(chat_id, response)
    
    def _parse_time(self, time_str: Optional[str]) -> datetime:
        """Parsuj czas"""
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
    
    async def _send_location(self, chat_id: int, lat: float, lon: float):
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
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload, timeout=5)
        except:
            pass

# ====================== FLASK APP ======================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = AIPoweredTelegramBot()

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 AI-Powered Earth Observatory v8.0</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
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
                background: linear-gradient(45deg, #00dbde, #fc00ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .ai-feature {
                background: rgba(0, 255, 255, 0.1);
                padding: 20px;
                border-radius: 15px;
                margin: 20px 0;
                border-left: 5px solid #00ffff;
            }
            .command {
                background: rgba(0, 0, 0, 0.3);
                padding: 12px 15px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
                display: block;
                border-left: 4px solid #00ff00;
            }
            .telegram-link {
                display: inline-block;
                background: linear-gradient(45deg, #0088cc, #00ccff);
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                margin-top: 20px;
                font-weight: bold;
                font-size: 1.1em;
                transition: transform 0.3s;
                text-align: center;
                width: 100%;
                box-sizing: border-box;
            }
            .telegram-link:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 136, 204, 0.4);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 AI-Powered Earth Observatory</h1>
            <div style="text-align: center; margin-bottom: 30px; font-size: 1.2em;">
                v8.0 - DeepSeek AI jako centralny mózg systemu
            </div>
            
            <div class="ai-feature">
                <b>🎯 REWOLUCJA AI:</b> System NIE pyta co chcesz robić.<br>
                AI analizuje WSZYSTKIE dane i SAM mówi co warto robić, gdzie i kiedy!
            </div>
            
            <h3>🚀 JAK TO DZIAŁA:</h3>
            <p>1. <b>/start warszawa</b> - AI od razu daje pełny raport</p>
            <p>2. <b>AI analizuje 8 źródeł danych jednocześnie</b></p>
            <p>3. <b>AI sam decyduje</b> co jest ważne i co warto obserwować</p>
            <p>4. <b>Dostajesz gotowy plan działania</b> na następne 24h</p>
            
            <h3>🤖 NOWE KOMENDY AI:</h3>
            <div class="command">/start warszawa</div>
            <p>Pełny raport AI z analizą WSZYSTKIEGO</p>
            
            <div class="command">/ai Kiedy najlepiej fotografować satelity?</div>
            <p>Zapytaj AI o cokolwiek</p>
            
            <div class="command">/briefing tatry</div>
            <p>Codzienne podsumowanie AI</p>
            
            <div class="command">/analyze warunki do astrofotografii</div>
            <p>Głęboka analiza konkretnego tematu</p>
            
            <div class="command">/report</div>
            <p>Odśwież raport AI</p>
            
            <h3>🌍 INTEGRACJE API:</h3>
            <p>• 🌤️ OpenWeather (pogoda)</p>
            <p>• 🚨 USGS (trzęsienia ziemi)</p>
            <p>• 🪐 NASA (asteroidy, APOD)</p>
            <p>• 🛰️ N2YO (satelity)</p>
            <p>• 🌌 Space Weather (pogoda kosmiczna)</p>
            <p>• ☄️ Meteory (deszcze meteorów)</p>
            <p>• 🌀 Aurora (zorze polarne)</p>
            
            <h3>🎯 PRZYKŁAD RAPORTU AI:</h3>
            <p>"Analizuję WSZYSTKIE dane. DZIŚ MASZ 3 OKAZJE:</p>
            <p>1. ISS nad Krakowem o 20:30 - 95% szans</p>
            <p>2. Trzęsienie ziemi 5.5M w Grecji</p>
            <p>3. Deszcz meteorów Perseidy dziś w nocy</p>
            <p><b>MOJA REKOMENDACJA:</b> Jedź w Tatry na 21:15..."</p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/PcSentinel_Bot" class="telegram-link" target="_blank">
                    🚀 Rozpocznij z @PcSentinel_Bot
                </a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook Telegram z async"""
    try:
        data = request.get_json()
        
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "").strip()
            
            if text.startswith('/'):
                parts = text.split()
                command = parts[0][1:]
                args = parts[1:] if len(parts) > 1 else []
                
                await bot.handle_command(chat_id, command, args)
            else:
                await bot.send_message(chat_id,
                    "🤖 <b>AI-Powered Earth Observatory v8.0</b>\n\n"
                    "Użyj <code>/start [lokalizacja]</code> aby AI od razu przeanalizowało WSZYSTKO!\n\n"
                    "<b>Przykład:</b> <code>/start warszawa</code>\n\n"
                    "<b>Albo zapytaj AI:</b> <code>/ai [twoje pytanie]</code>"
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
    print("🤖 AI-POWERED EARTH OBSERVATORY v8.0")
    print("=" * 80)
    
    print("🚀 REWOLUCJA AI:")
    print("   System NIE pyta co chcesz robić")
    print("   AI analizuje WSZYSTKO i SAM mówi co warto robić")
    print("=" * 80)
    
    print("📡 INTEGRACJE API:")
    print(f"   🤖 DeepSeek AI: {'✅ AKTYWNY' if DEEPSEEK_API_KEY else '❌ BRAK'}")
    print(f"   🌤️ OpenWeather: {'✅ AKTYWNY' if OPENWEATHER_API_KEY else '❌ BRAK'}")
    print(f"   🚨 USGS: ✅ ZAWSZE")
    print(f"   🪐 NASA: {'✅ AKTYWNY' if NASA_API_KEY else '⚠️ DEMO'}")
    print(f"   🛰️ N2YO: {'✅ AKTYWNY' if N2YO_API_KEY else '⚠️ SYMULACJA'}")
    print(f"   🌌 Space Weather: ✅ SYMULACJA")
    print(f"   ☄️ Meteors: ✅ SYMULACJA")
    print(f"   🌀 Aurora: ✅ SYMULACJA")
    print("=" * 80)
    
    if TELEGRAM_BOT_TOKEN:
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
    else:
        print("❌ BRAK TELEGRAM TOKEN - bot nie będzie działać")
    
    print("\n🎯 GŁÓWNA INNOWACJA:")
    print("   /start [lokalizacja] = AI od razu daje pełny raport!")
    print("   AI analizuje 8 źródeł danych jednocześnie")
    print("   AI sam decyduje co jest ważne")
    print("   Dostajesz gotowy plan działania")
    
    print("\n🚀 KOMENDY:")
    print("   /start warszawa - PEŁNY RAPORT AI")
    print("   /ai [pytanie] - zapytaj AI o cokolwiek")
    print("   /briefing - dzienne podsumowanie")
    print("   /analyze [temat] - głęboka analiza")
    print("   /report - odśwież raport")
    print("   /where [satelita] - gdzie stanąć")
    
    print("\n💡 PRZYKŁAD:")
    print("   /start tatry")
    print("   /ai Kiedy najlepszy czas na obserwacje?")
    print("   /analyze warunki do fotografii satelitarnej")
    print("=" * 80)
    print("🤖 SYSTEM AI GOTOWY DO DZIAŁANIA!")
    print("=" * 80)
    
    # Uruchom Flask
    app.run(host="0.0.0.0", port=PORT, debug=False)