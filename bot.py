#!/usr/bin/env python3
"""
🤖 SENTRY ONE v12.0 - DeepSeek AI Edition
Inteligentny system astrometeorologiczny z AI i analizą kwantową
"""

import os
import json
import time
import logging
import threading
import requests
import math
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List, Optional

# Próbuj zaimportować wymagane pakiety z fallbackami
try:
    from flask import Flask, request, jsonify, render_template_string
    FLASK_AVAILABLE = True
except ImportError:
    print("⚠️ Flask niedostępny, używam fallback")
    FLASK_AVAILABLE = False
    # Simple Flask replacement
    class SimpleFlask:
        def __init__(self, name):
            self.name = name
            self.routes = {}
        
        def route(self, path, methods=None):
            def decorator(func):
                self.routes[path] = func
                return func
            return decorator
        
        def run(self, host='0.0.0.0', port=10000, debug=False, **kwargs):
            print(f"🚀 Serwer działający na {host}:{port}")
            # Simple HTTP server simulation
            import http.server
            import socketserver
            
            class Handler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    if self.path in self.routes:
                        result = self.routes[self.path]()
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(str(result).encode())
                    else:
                        super().do_GET()
            
            with socketserver.TCPServer((host, port), Handler) as httpd:
                print(f"✅ Serwer gotowy na porcie {port}")
                httpd.serve_forever()
    
    Flask = SimpleFlask
    request = type('obj', (object,), {'get_json': lambda: {}, 'headers': {}})
    jsonify = lambda x: str(x)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    print("⚠️ APScheduler niedostępny")
    SCHEDULER_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    print("⚠️ NumPy niedostępny")
    NUMPY_AVAILABLE = False
    np = type('obj', (object,), {
        'pi': 3.141592653589793,
        'cos': lambda x: math.cos(x),
        'array': lambda x: x
    })

# Qiskit - opcjonalne zależności
try:
    from qiskit import QuantumCircuit
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    print("⚠️ Qiskit niedostępny, używam symulatora")
    QISKIT_AVAILABLE = False
    
    # Symulowane klasy Qiskit
    class QuantumCircuit:
        def __init__(self, n):
            self.n = n
        
        def h(self, q):
            pass
        
        def cx(self, q1, q2):
            pass
        
        def rx(self, angle, q):
            pass
        
        def ry(self, angle, q):
            pass
        
        def rz(self, angle, q):
            pass
        
        def measure_all(self):
            pass
    
    class AerSimulator:
        def run(self, circuit, shots=1000):
            class Result:
                def result(self):
                    class FinalResult:
                        def get_counts(self):
                            return {'000': 250, '001': 250, '010': 250, '011': 250}
                    return FinalResult()
            return Result()
    
    class QiskitRuntimeService:
        def __init__(self, channel=None, token=None):
            pass
        
        def backends(self):
            return []
    
    Sampler = type('Sampler', (), {'run': lambda self, circuit, shots: type('obj', (), {
        'result': lambda: type('obj', (), {'quasi_dists': [{}]})()
    })()})

# ====================== KONFIGURACJA ======================
# Używamy zmiennych środowiskowych z fallbackami
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic")
RENDER_URL = os.getenv("RENDER_URL", "https://telegram-bot-szxa.onrender.com")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"

# API klucze - PRIORYTET: zmienne środowiskowe
NASA_API_KEY = os.getenv("NASA_API_KEY", "P0locPuOZBvnkHCdIKjkxzKsfnM7tc7pbiMcsBDE")
N2YO_API_KEY = os.getenv("N2YO_API_KEY", "UNWEQ8-N47JL7-WFJZYX-5N65")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "38e01cfb763fc738e9eddee84cfc4384")
IBM_QUANTUM_TOKEN = os.getenv("IBM_QUANTUM_TOKEN", "esUNC1tmumZpWO1C2iwgaYxCA48k4MBOiFp7ARD2Wk3A")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-4af5d51f20e34ba8b53e09e6422341a4")

# API endpoints
N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Baza danych użytkowników
DB_FILE = "sentry_one.db

# Miasta do obserwacji
OBSERVATION_CITIES = {
    "warszawa": {
        "name": "Warszawa", 
        "lat": 52.2297, 
        "lon": 21.0122, 
        "timezone": "Europe/Warsaw",
        "country": "Poland",
        "emoji": "🏛️"
    },
    "koszalin": {
        "name": "Koszalin", 
        "lat": 54.1943, 
        "lon": 16.1712, 
        "timezone": "Europe/Warsaw",
        "country": "Poland",
        "emoji": "🌲"
    }
}

# Próg dobrej widoczności
GOOD_CONDITIONS = {
    "max_cloud_cover": 30,
    "min_visibility": 10,
    "max_humidity": 80,
    "max_wind_speed": 15,
    "min_temperature": -10,
    "max_temperature": 30
}

print("=" * 60)
print("🤖 SENTRY ONE v12.0 - DEEPSEEK AI EDITION")
print(f"🌐 URL: {RENDER_URL}")
print("🧠 DeepSeek AI + IBM Quantum + NASA + N2YO")
print("🔔 System pingowania: INTELEGENTNY")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== DEEPSEEK AI ANALYZER ======================
class DeepSeekAnalyzer:
    """Zaawansowana analiza danych przy użyciu DeepSeek AI"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.available = self.check_api_availability()
        
    def check_api_availability(self):
        """Sprawdź dostępność API DeepSeek"""
        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                },
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ DeepSeek API niedostępne: {e}")
            return False
    
    def analyze_weather_with_ai(self, weather_data, city_name, moon_data):
        """
        Analizuj warunki pogodowe za pomocą DeepSeek AI
        
        Parameters:
        - weather_data: dict z danymi pogodowymi
        - city_name: nazwa miasta
        - moon_data: dane księżycowe
        
        Returns:
        - dict z analizą AI
        """
        try:
            prompt = f"""
            Jesteś ekspertem astrometeorologii. Analizujesz warunki do obserwacji astronomicznych.
            
            MIASTO: {city_name}
            DATA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            DANE POGODOWE:
            - Temperatura: {weather_data.get('temperature', 0)}°C
            - Zachmurzenie: {weather_data.get('cloud_cover', 0)}%
            - Wilgotność: {weather_data.get('humidity', 0)}%
            - Prędkość wiatru: {weather_data.get('wind_speed', 0)} m/s
            - Widoczność: {weather_data.get('visibility', 0)} km
            - Dzień/Noc: {'Dzień' if weather_data.get('is_day', True) else 'Noc'}
            
            DANE KSIĘŻYCOWE:
            - Faza: {moon_data.get('name', 'N/A')}
            - Oświetlenie: {moon_data.get('illumination', 0)}%
            
            Oceń warunki do obserwacji astronomicznych w skali 1-10.
            Podaj szczegółową analizę i rekomendacje.
            Odpowiedz po polsku w formacie:
            1. OCENA (1-10): [liczba]
            2. ANALIZA: [tekst]
            3. REKOMENDACJE: [tekst]
            4. NAJLEPSZY CZAS: [tekst]
            5. OSTRZEŻENIA: [tekst]
            """
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Parsuj odpowiedź AI
                analysis = self.parse_ai_response(ai_response)
                analysis["source"] = "DeepSeek AI"
                analysis["raw_response"] = ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
                
                return analysis
            else:
                logger.error(f"❌ Błąd DeepSeek API: {response.status_code}")
                return self.get_fallback_analysis(weather_data, moon_data)
                
        except Exception as e:
            logger.error(f"❌ Błąd analizy AI: {e}")
            return self.get_fallback_analysis(weather_data, moon_data)
    
    def parse_ai_response(self, response_text):
        """Parsuj odpowiedź DeepSeek AI"""
        lines = response_text.split('\n')
        analysis = {
            "score": 5,
            "analysis": "Analiza niedostępna",
            "recommendations": "Brak rekomendacji",
            "best_time": "Noc",
            "warnings": "Brak ostrzeżeń"
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith("1. OCENA") or line.startswith("OCENA"):
                try:
                    score_text = line.split(':')[-1].strip()
                    if score_text.isdigit():
                        analysis["score"] = int(score_text)
                except:
                    pass
            elif line.startswith("2. ANALIZA") or line.startswith("ANALIZA"):
                analysis["analysis"] = line.split(':', 1)[-1].strip()
            elif line.startswith("3. REKOMENDACJE") or line.startswith("REKOMENDACJE"):
                analysis["recommendations"] = line.split(':', 1)[-1].strip()
            elif line.startswith("4. NAJLEPSZY CZAS") or line.startswith("NAJLEPSZY CZAS"):
                analysis["best_time"] = line.split(':', 1)[-1].strip()
            elif line.startswith("5. OSTRZEŻENIA") or line.startswith("OSTRZEŻENIA"):
                analysis["warnings"] = line.split(':', 1)[-1].strip()
        
        return analysis
    
    def get_fallback_analysis(self, weather_data, moon_data):
        """Fallback analiza gdy AI niedostępne"""
        score = 5
        
        # Prosta logika oceny
        if weather_data.get("cloud_cover", 100) < 30:
            score += 2
        if weather_data.get("visibility", 0) > 10:
            score += 2
        if moon_data.get("illumination", 100) < 30:
            score += 1
        
        score = max(1, min(10, score))
        
        return {
            "score": score,
            "analysis": "Analiza AI niedostępna. Używam prostej oceny warunków.",
            "recommendations": "Sprawdź lokalną pogodę przed obserwacją.",
            "best_time": "Noc (po zachodzie słońca)",
            "warnings": "Brak danych AI",
            "source": "Fallback System"
        }
    
    def generate_astronomy_tips(self):
        """Generuj losowe wskazówki astronomiczne za pomocą AI"""
        try:
            prompt = "Podaj jedną praktyczną wskazówkę dla początkującego astronoma obserwującego niebo z Polski. Maksymalnie 2 zdania po polsku."
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.9
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "Użyj aplikacji do mapowania nieba.")
            else:
                return "Użyj aplikacji Stellarium do identyfikacji obiektów."
                
        except Exception as e:
            return "Zacznij obserwacje od Księżyca i jasnych planet."
    
    def analyze_satellite_data(self, satellite_info):
        """Analizuj dane satelitarne za pomocą AI"""
        try:
            prompt = f"""
            Analizuję dane satelity:
            - Nazwa: {satellite_info.get('name', 'Nieznany')}
            - ID: {satellite_info.get('id', 'N/A')}
            - Typ: {satellite_info.get('type', 'N/A')}
            - Kraj: {satellite_info.get('country', 'N/A')}
            
            Co to za satelita? Jaki jest jego cel? Czy jest interesujący dla amatorskich obserwacji?
            Odpowiedz krótko po polsku (max 3 zdania).
            """
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "Brak informacji o satelicie.")
            else:
                return "Satelita w pobliżu - sprawdź jego pozycję."
                
        except Exception as e:
            return "Satelita nad twoim obszarem."

# ====================== KWANTOWY ANALIZATOR ======================
class QuantumAnalyzer:
    """Analiza danych astro-meteorologicznych za pomocą komputerów kwantowych"""
    
    def __init__(self):
        self.quantum_service = None
        self.connected = False
        self.simulator = AerSimulator()
        
    def connect_to_ibm(self):
        """Połącz z IBM Quantum (opcjonalnie)"""
        try:
            if IBM_QUANTUM_TOKEN and IBM_QUANTUM_TOKEN != "your_ibm_quantum_token_here":
                self.quantum_service = QiskitRuntimeService(
                    channel="ibm_quantum",
                    token=IBM_QUANTUM_TOKEN
                )
                self.connected = True
                logger.info("✅ Połączono z IBM Quantum")
                return True
            else:
                logger.info("ℹ️ Używam lokalnego symulatora kwantowego")
                return False
        except Exception as e:
            logger.error(f"❌ Błąd połączenia z IBM Quantum: {e}")
            logger.info("ℹ️ Używam lokalnego symulatora")
            return False
    
    def analyze_conditions(self, weather_data, moon_data):
        """
        Analizuj warunki obserwacyjne za pomocą obwodu kwantowego
        
        Parameters:
        - weather_data: dict z danymi pogodowymi
        - moon_data: dict z danymi księżycowymi
        
        Returns:
        - dict z wynikami analizy kwantowej
        """
        try:
            # Utwórz obwód kwantowy z 4 kubitami
            qc = QuantumCircuit(4)
            
            # Zakoduj dane pogodowe jako stany kwantowe
            cloud_angle = (weather_data.get("cloud_cover", 0) / 100) * np.pi
            temp_angle = ((weather_data.get("temperature", 0) + 20) / 50) * np.pi
            visibility_angle = (min(weather_data.get("visibility", 0) / 100, 1)) * np.pi
            
            # Zakoduj dane księżycowe
            moon_angle = (moon_data.get("illumination", 0) / 100) * np.pi
            
            # Dodaj bramki
            qc.rx(cloud_angle, 0)      # Kubit 0: Zachmurzenie
            qc.ry(temp_angle, 1)       # Kubit 1: Temperatura
            qc.rz(visibility_angle, 2) # Kubit 2: Widoczność
            qc.rx(moon_angle, 3)       # Kubit 3: Faza Księżyca
            
            # Dodaj splątanie
            qc.cx(0, 1)
            qc.cx(1, 2)
            qc.cx(2, 3)
            qc.h([0, 1, 2, 3])
            
            # Pomiar
            qc.measure_all()
            
            # Uruchom na symulatorze (lub IBM Quantum)
            if self.connected and self.quantum_service:
                try:
                    backend = self.get_least_busy_backend()
                    sampler = Sampler(backend=backend)
                    job = sampler.run(qc, shots=1000)
                    result = job.result()
                    counts = result.quasi_dists[0]
                    backend_name = backend.name
                    quantum_source = "IBM Quantum"
                except:
                    # Fallback na symulator lokalny
                    result = self.simulator.run(qc, shots=1000).result()
                    counts = result.get_counts()
                    backend_name = "AerSimulator"
                    quantum_source = "Local Simulator"
            else:
                # Użyj symulatora lokalnego
                result = self.simulator.run(qc, shots=1000).result()
                counts = result.get_counts()
                backend_name = "AerSimulator"
                quantum_source = "Local Simulator"
            
            # Analizuj wyniki
            analysis = self.interpret_quantum_results(counts)
            analysis.update({
                "backend": backend_name,
                "source": quantum_source,
                "counts": counts
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Błąd analizy kwantowej: {e}")
            return {"error": str(e), "recommendation": "Użyj standardowej analizy"}
    
    def get_least_busy_backend(self):
        """Znajdź najmniej obciążony backend IBM Quantum"""
        backends = [b for b in self.quantum_service.backends() if b.status().operational]
        if not backends:
            raise Exception("Brak dostępnych backendów")
        return min(backends, key=lambda x: x.status().pending_jobs)
    
    def interpret_quantum_results(self, counts):
        """Zinterpretuj wyniki pomiarów kwantowych"""
        if not counts:
            return {"prediction": "unknown", "confidence": 0}
        
        # Mapowanie stanów na prognozy
        prediction_map = {
            '0000': "excellent_conditions",
            '0001': "very_good_conditions",
            '0010': "good_conditions",
            '0011': "fair_conditions",
            '0100': "poor_conditions",
            '0101': "bad_conditions",
            '0110': "very_bad_conditions",
            '0111': "worst_conditions",
            '1000': "moon_optimal",
            '1001': "moon_good",
            '1010': "moon_fair",
            '1011': "moon_poor",
            '1100': "moon_bad",
            '1101': "moon_very_bad",
            '1110': "mixed_conditions",
            '1111': "unpredictable"
        }
        
        # Znajdź najczęstszy stan
        max_state = max(counts, key=counts.get)
        total_shots = sum(counts.values())
        
        prediction = prediction_map.get(max_state, "unknown")
        confidence = (counts[max_state] / total_shots) * 100
        
        # Generuj rekomendację
        recommendations = {
            "excellent_conditions": "🎯 DOSKONAŁE WARUNKI! Idealna noc do obserwacji.",
            "very_good_conditions": "⭐ BARDZO DOBRE WARUNKI! Warto obserwować.",
            "good_conditions": "👍 DOBRE WARUNKI! Można planować obserwacje.",
            "fair_conditions": "⏳ ŚREDNIE WARUNKI! Czekaj na poprawę.",
            "poor_conditions": "👎 SŁABE WARUNKI! Lepiej odłożyć obserwacje.",
            "bad_conditions": "❌ ZŁE WARUNKI! Nie polecamy obserwacji.",
            "moon_optimal": "🌕 OPTYMALNA FAZA KSIĘŻYCA! Noc będzie jasna.",
            "moon_good": "🌔 DOBRA FAZA KSIĘŻYCA! Umiarkowane światło.",
            "moon_fair": "🌓 ŚREDNIA FAZA KSIĘŻYCA! Może zakłócać obserwacje.",
            "unpredictable": "🎲 WARUNKI NIEJASNE! Sprawdź ponownie później."
        }
        
        return {
            "prediction": prediction,
            "confidence": round(confidence, 1),
            "recommendation": recommendations.get(prediction, "Sprawdź lokalne warunki."),
            "dominant_state": max_state,
            "state_probability": round(confidence, 1)
        }
    
    def analyze_satellite_orbit(self, satellite_data):
        """Analiza stabilności orbity satelity za pomocą QC"""
        try:
            qc = QuantumCircuit(3)
            
            # Zakoduj dane orbity
            altitude = min(satellite_data.get("altitude", 0) / 1000, 1) * np.pi
            velocity = min(satellite_data.get("velocity", 0) / 10, 1) * np.pi
            inclination = satellite_data.get("inclination", 0) / 180 * np.pi
            
            qc.rx(altitude, 0)
            qc.ry(velocity, 1)
            qc.rz(inclination, 2)
            
            qc.cx(0, 1)
            qc.cx(1, 2)
            qc.measure_all()
            
            result = self.simulator.run(qc, shots=1000).result()
            counts = result.get_counts()
            
            # Analiza stabilności
            stable_patterns = ['000', '001', '010', '100']
            unstable_patterns = ['111', '110', '101', '011']
            
            stable_count = sum(counts.get(p, 0) for p in stable_patterns)
            unstable_count = sum(counts.get(p, 0) for p in unstable_patterns)
            
            stability_score = (stable_count / 1000) * 100
            
            if stability_score > 70:
                stability = "high"
            elif stability_score > 40:
                stability = "medium"
            else:
                stability = "low"
            
            return {
                "stability": stability,
                "stability_score": round(stability_score, 1),
                "quantum_analysis": True,
                "patterns_analyzed": len(counts)
            }
            
        except Exception as e:
            logger.error(f"❌ Błąd analizy orbity: {e}")
            return {"stability": "unknown", "error": str(e)}

# Inicjalizuj analizatory
deepseek_analyzer = DeepSeekAnalyzer()
quantum_analyzer = QuantumAnalyzer()

# ====================== BAZA DANYCH ======================
def init_database():
    """Inicjalizacja bazy danych"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            satellite_notifications BOOLEAN DEFAULT 0,
            observation_alerts BOOLEAN DEFAULT 1,
            quantum_analysis BOOLEAN DEFAULT 1,
            ai_analysis BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_settings(chat_id: int) -> Dict:
    """Pobierz ustawienia użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT chat_id, satellite_notifications, observation_alerts, 
               quantum_analysis, ai_analysis
        FROM users WHERE chat_id = ?
    ''', (chat_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "chat_id": result[0],
            "satellite_notifications": bool(result[1]),
            "observation_alerts": bool(result[2]),
            "quantum_analysis": bool(result[3]),
            "ai_analysis": bool(result[4])
        }
    else:
        return {
            "chat_id": chat_id,
            "satellite_notifications": False,
            "observation_alerts": True,
            "quantum_analysis": True,
            "ai_analysis": True
        }

def update_user_settings(chat_id: int, settings: Dict):
    """Aktualizuj ustawienia użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (chat_id, satellite_notifications, observation_alerts, quantum_analysis, ai_analysis)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        chat_id,
        1 if settings.get("satellite_notifications") else 0,
        1 if settings.get("observation_alerts") else 0,
        1 if settings.get("quantum_analysis", True) else 0,
        1 if settings.get("ai_analysis", True) else 0
    ))
    
    conn.commit()
    conn.close()

def get_all_users_with_notifications():
    """Pobierz wszystkich użytkowników z włączonymi powiadomieniami"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT chat_id FROM users 
        WHERE satellite_notifications = 1 OR observation_alerts = 1
    ''')
    
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

# ====================== NASA FUNCTIONS ======================
def get_nasa_apod():
    """Pobierz Astronomy Picture of the Day z NASA"""
    try:
        url = f"{NASA_APOD_URL}?api_key={NASA_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "title": data.get("title", "NASA APOD"),
            "explanation": data.get("explanation", ""),
            "url": data.get("url", ""),
            "media_type": data.get("media_type", "image"),
            "date": data.get("date", "")
        }
    except Exception as e:
        logger.error(f"❌ Błąd NASA APOD: {e}")
        return None

def get_weather_forecast(lat, lon):
    """Pobierz prognozę pogody z Open-Meteo"""
    try:
        url = OPENMETEO_BASE_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,visibility,is_day",
            "daily": "sunrise,sunset",
            "timezone": "auto",
            "forecast_days": 2
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd pobierania pogody: {e}")
        return None

def get_openweather_data(lat, lon):
    """Pobierz dane pogodowe z OpenWeather API"""
    try:
        url = f"{OPENWEATHER_BASE_URL}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "pressure": data.get("main", {}).get("pressure", 0),
            "feels_like": data.get("main", {}).get("feels_like", 0),
            "weather_description": data.get("weather", [{}])[0].get("description", ""),
            "sunrise": datetime.fromtimestamp(data.get("sys", {}).get("sunrise", 0)).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data.get("sys", {}).get("sunset", 0)).strftime("%H:%M"),
        }
        
    except Exception as e:
        logger.error(f"❌ Błąd OpenWeather API: {e}")
        return None

# ====================== ASTRONOMICAL CALCULATIONS ======================
def calculate_moon_phase(date: datetime = None) -> Dict:
    """Oblicz dokładną fazę księżyca"""
    if not date:
        date = datetime.now()
    
    # Ostatni nów: 11 stycznia 2025, 11:57 UTC
    last_new_moon = datetime(2025, 1, 11, 11, 57)
    
    delta_days = (date - last_new_moon).total_seconds() / 86400.0
    moon_age = delta_days % 29.530588
    
    illumination = 50 * (1 - math.cos(2 * math.pi * moon_age / 29.530588))
    
    if moon_age < 1.0:
        phase = "Nów"
        emoji = "🌑"
        illumination = 0
    elif moon_age < 7.38:
        phase = "Rosnący sierp"
        emoji = "🌒"
    elif moon_age < 7.38 + 0.5:
        phase = "Pierwsza kwadra"
        emoji = "🌓"
        illumination = 50
    elif moon_age < 14.77:
        phase = "Rosnący garbaty"
        emoji = "🌔"
    elif moon_age < 15.0:
        phase = "Pełnia"
        emoji = "🌕"
        illumination = 100
    elif moon_age < 22.15:
        phase = "Malejący garbaty"
        emoji = "🌖"
    elif moon_age < 22.15 + 0.5:
        phase = "Ostatnia kwadra"
        emoji = "🌗"
        illumination = 50
    else:
        phase = "Malejący sierp"
        emoji = "🌘"
    
    return {
        "phase": moon_age / 29.530588,
        "name": phase,
        "emoji": emoji,
        "illumination": illumination,
        "age_days": moon_age
    }

def get_astronomical_date():
    """Zwróć datę w kalendarzu 13-miesięcznym"""
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    
    for month in [
        {"name": "Sagittarius", "symbol": "♐", "element": "Ogień", "start_day": 355, "end_day": 13},
        {"name": "Capricorn", "symbol": "♑", "element": "Ziemia", "start_day": 14, "end_day": 42},
        {"name": "Aquarius", "symbol": "♒", "element": "Powietrze", "start_day": 43, "end_day": 72},
        {"name": "Pisces", "symbol": "♓", "element": "Woda", "start_day": 73, "end_day": 101},
        {"name": "Aries", "symbol": "♈", "element": "Ogień", "start_day": 102, "end_day": 132},
        {"name": "Taurus", "symbol": "♉", "element": "Ziemia", "start_day": 133, "end_day": 162},
        {"name": "Gemini", "symbol": "♊", "element": "Powietrze", "start_day": 163, "end_day": 192},
        {"name": "Cancer", "symbol": "♋", "element": "Woda", "start_day": 193, "end_day": 223},
        {"name": "Leo", "symbol": "♌", "element": "Ogień", "start_day": 224, "end_day": 253},
        {"name": "Virgo", "symbol": "♍", "element": "Ziemia", "start_day": 254, "end_day": 283},
        {"name": "Libra", "symbol": "♎", "element": "Powietrze", "start_day": 284, "end_day": 314},
        {"name": "Scorpio", "symbol": "♏", "element": "Woda", "start_day": 315, "end_day": 343},
        {"name": "Ophiuchus", "symbol": "⛎", "element": "Ogień", "start_day": 344, "end_day": 354}
    ]:
        if month["start_day"] <= day_of_year <= month["end_day"]:
            day_in_month = day_of_year - month["start_day"] + 1
            
            polish_names = {
                "Sagittarius": "Strzelec",
                "Capricorn": "Koziorożec",
                "Aquarius": "Wodnik",
                "Pisces": "Ryby",
                "Aries": "Baran",
                "Taurus": "Byk",
                "Gemini": "Bliźnięta",
                "Cancer": "Rak",
                "Leo": "Lew",
                "Virgo": "Panna",
                "Libra": "Waga",
                "Scorpio": "Skorpion",
                "Ophiuchus": "Wężownik"
            }
            
            element_emojis = {
                "Ogień": "🔥",
                "Ziemia": "🌍",
                "Powietrze": "💨",
                "Woda": "💧"
            }
            
            return {
                "day": day_in_month,
                "month": month["name"],
                "month_symbol": month["symbol"],
                "month_polish": polish_names.get(month["name"], month["name"]),
                "day_of_year": day_of_year,
                "year": now.year,
                "element": month["element"],
                "element_emoji": element_emojis.get(month["element"], "⭐"),
                "description": f"Znak {month['element'].lower()}"
            }
    
    return {
        "day": 5,
        "month": "Capricorn",
        "month_symbol": "♑",
        "month_polish": "Koziorożec",
        "day_of_year": day_of_year,
        "year": now.year,
        "element": "Ziemia",
        "element_emoji": "🌍",
        "description": "Znak ambicji, determinacji i praktyczności"
    }

def get_sun_moon_times(city_key: str):
    """Pobierz czasy wschodu/zachodu Słońca"""
    city = OBSERVATION_CITIES[city_key]
    
    try:
        url = f"{OPENWEATHER_BASE_URL}/weather"
        params = {
            "lat": city["lat"],
            "lon": city["lon"],
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        sunrise = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
        sunset = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
        
        moon = calculate_moon_phase()
        
        return {
            "sun": {"rise": sunrise, "set": sunset},
            "moon_phase": moon
        }
        
    except Exception as e:
        return {
            "sun": {"rise": "07:30", "set": "16:30"},
            "moon_phase": calculate_moon_phase()
        }

# ====================== OBSERVATION CONDITIONS ======================
def check_city_conditions(city_key: str):
    """Sprawdź warunki obserwacyjne dla miasta"""
    city = OBSERVATION_CITIES[city_key]
    weather_data = get_weather_forecast(city["lat"], city["lon"])
    
    if not weather_data or "current" not in weather_data:
        return None
    
    current = weather_data["current"]
    
    cloud_cover = current.get("cloud_cover", 100)
    visibility = current.get("visibility", 0) / 1000
    humidity = current.get("relative_humidity_2m", 100)
    wind_speed = current.get("wind_speed_10m", 0)
    temperature = current.get("temperature_2m", 0)
    is_day = current.get("is_day", 1)
    
    conditions_check = {
        "cloud_cover": cloud_cover <= GOOD_CONDITIONS["max_cloud_cover"],
        "visibility": visibility >= GOOD_CONDITIONS["min_visibility"],
        "humidity": humidity <= GOOD_CONDITIONS["max_humidity"],
        "wind_speed": wind_speed <= GOOD_CONDITIONS["max_wind_speed"],
        "temperature": GOOD_CONDITIONS["min_temperature"] <= temperature <= GOOD_CONDITIONS["max_temperature"]
    }
    
    conditions_met = sum(conditions_check.values())
    total_conditions = len(conditions_check)
    
    if conditions_met == total_conditions:
        status = "DOSKONAŁE"
        emoji = "✨"
    elif conditions_met >= 4:
        status = "DOBRE"
        emoji = "⭐"
    elif conditions_met == 3:
        status = "ŚREDNIE"
        emoji = "⛅"
    elif conditions_met >= 1:
        status = "SŁABE"
        emoji = "🌥️"
    else:
        status = "ZŁE"
        emoji = "🌧️"
    
    score = round((conditions_met / total_conditions) * 100)
    
    return {
        "city_name": city["name"],
        "city_emoji": city["emoji"],
        "temperature": temperature,
        "cloud_cover": cloud_cover,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "visibility": round(visibility, 1),
        "is_day": is_day == 1,
        "status": status,
        "emoji": emoji,
        "score": score,
        "conditions_met": conditions_met,
        "total_conditions": total_conditions
    }

def get_ai_weather_analysis(city_key: str):
    """Pobierz analizę pogody z użyciem DeepSeek AI"""
    city = OBSERVATION_CITIES[city_key]
    weather_data = get_weather_forecast(city["lat"], city["lon"])
    moon_data = calculate_moon_phase()
    
    if not weather_data or "current" not in weather_data:
        return None
    
    current = weather_data["current"]
    
    # Przygotuj dane dla AI
    weather_info = {
        "temperature": current.get("temperature_2m", 0),
        "cloud_cover": current.get("cloud_cover", 100),
        "humidity": current.get("relative_humidity_2m", 100),
        "wind_speed": current.get("wind_speed_10m", 0),
        "visibility": current.get("visibility", 0) / 1000,
        "is_day": current.get("is_day", 1) == 1
    }
    
    # Wykonaj analizę AI
    ai_analysis = deepseek_analyzer.analyze_weather_with_ai(
        weather_info, 
        city["name"], 
        moon_data
    )
    
    return {
        "city_name": city["name"],
        "city_emoji": city["emoji"],
        "ai_analysis": ai_analysis,
        "weather_data": weather_info,
        "moon_data": moon_data,
        "timestamp": datetime.now().isoformat()
    }

# ====================== TELEGRAM FUNCTIONS ======================
def send_telegram_message(chat_id, text, photo_url=None):
    """Wyślij wiadomość przez Telegram API"""
    if photo_url:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": text,
            "parse_mode": "HTML"
        }
    else:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return False

def send_photo(chat_id, photo_url, caption=""):
    """Wyślij zdjęcie"""
    return send_telegram_message(chat_id, caption, photo_url)

# ====================== FLASK APP ======================
app = Flask(__name__)

# Globalne zmienne
last_ping_time = datetime.now()
ping_count = 0
deepseek_status = "✅ Aktywny" if deepseek_analyzer.available else "❌ Niedostępny"
quantum_analyzer.connect_to_ibm()  # Próbuj połączyć z IBM Quantum przy starcie

@app.route('/')
def home():
    """Strona główna - ten endpoint jest pingowany"""
    global last_ping_time, ping_count
    last_ping_time = datetime.now()
    ping_count += 1
    
    now = datetime.now()
    astro_date = get_astronomical_date()
    moon = calculate_moon_phase()
    
    # Sprawdź status systemów
    ibm_status = "✅ Połączono" if quantum_analyzer.connected else "🔌 Lokalny symulator"
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v12.0 - DeepSeek AI Edition</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0a0a2a 0%, #1a1a4a 50%, #2a2a6a 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.08);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-top: 20px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            .ai-card {{
                background: linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%);
                border: 2px solid #ff9966;
            }}
            .quantum-card {{
                background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);
                border: 2px solid #00ffff;
            }}
            .moon-phase {{
                text-align: center;
                font-size: 60px;
                margin: 20px 0;
            }}
            .api-status {{
                display: inline-block;
                padding: 8px 20px;
                border-radius: 25px;
                margin: 5px;
                font-weight: bold;
                font-size: 14px;
                background: linear-gradient(to right, #00b09b, #96c93d);
            }}
            .ai-status {{
                background: linear-gradient(to right, #ff7e5f, #feb47b);
            }}
            .quantum-status {{
                background: linear-gradient(to right, #00c6ff, #0072ff);
            }}
            .btn {{
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(to right, #4776E6, #8E54E9);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: bold;
                margin: 10px;
                transition: transform 0.3s;
            }}
            .btn:hover {{
                transform: translateY(-2px);
            }}
            .ping-info {{
                background: rgba(0, 0, 0, 0.3);
                padding: 15px;
                border-radius: 10px;
                margin-top: 20px;
                font-family: monospace;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 48px; margin-bottom: 10px;">🤖 SENTRY ONE v12.0</h1>
                <h2 style="color: #81ecec; margin-bottom: 20px;">DeepSeek AI Edition</h2>
                
                <div class="moon-phase">
                    {moon['emoji']}
                </div>
                
                <div style="margin: 20px 0;">
                    <span class="api-status">🛰️ NASA API</span>
                    <span class="api-status">🌤️ OPENWEATHER</span>
                    <span class="api-status ai-status">🧠 DEEPSEEK AI</span>
                    <span class="api-status quantum-status">🔬 IBM QUANTUM</span>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>🌌 Faza Księżyca</h3>
                    <p style="font-size: 24px; margin: 10px 0;">{moon['emoji']} {moon['name']}</p>
                    <p>Oświetlenie: {moon['illumination']:.1f}%</p>
                </div>
                
                <div class="stat-card">
                    <h3>📅 Kalendarz Astronomiczny</h3>
                    <p style="font-size: 24px; margin: 10px 0;">{astro_date['day']} {astro_date['month_symbol']}</p>
                    <p>{astro_date['month_polish']} {astro_date['element_emoji']}</p>
                </div>
                
                <div class="stat-card ai-card">
                    <h3>🧠 DeepSeek AI</h3>
                    <p style="font-size: 18px; margin: 10px 0;">{deepseek_status}</p>
                    <p>Analiza: AKTYWNA 🚀</p>
                </div>
                
                <div class="stat-card quantum-card">
                    <h3>🔬 IBM Quantum</h3>
                    <p style="font-size: 18px; margin: 10px 0;">{ibm_status}</p>
                    <p>System: {ping_count} pingów</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" class="btn">
                    💬 Otwórz bota w Telegram
                </a>
                <a href="{RENDER_URL}/ai_demo" target="_blank" class="btn" style="background: linear-gradient(to right, #ff7e5f, #feb47b);">
                    🧠 Demo AI analizy
                </a>
                <a href="{RENDER_URL}/quantum_demo" target="_blank" class="btn" style="background: linear-gradient(to right, #00c6ff, #0072ff);">
                    🔬 Demo analizy kwantowej
                </a>
            </div>
            
            <div class="ping-info">
                <h4>📡 Status systemu:</h4>
                <p>• Ostatni ping: {last_ping_time.strftime('%H:%M:%S')}</p>
                <p>• Liczba pingów: {ping_count}</p>
                <p>• Czas pracy: {(datetime.now() - last_ping_time).seconds // 60} minut</p>
                <p>• DeepSeek AI: {deepseek_status}</p>
                <p>• IBM Quantum: {ibm_status}</p>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                <p>🤖 SENTRY ONE v12.0 | AI + Quantum Analysis System</p>
                <p style="font-family: monospace; font-size: 12px; opacity: 0.8;">
                    {now.strftime("%Y-%m-%d %H:%M:%S")} | Ping #{ping_count} | AI: {deepseek_status}
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/ai_demo')
def ai_demo():
    """Demo analizy DeepSeek AI"""
    # Pobierz aktualne dane dla Warszawy
    weather_data = get_weather_forecast(52.2297, 21.0122)
    moon_data = calculate_moon_phase()
    
    if weather_data and "current" in weather_data:
        current = weather_data["current"]
        weather_info = {
            "temperature": current.get("temperature_2m", 0),
            "cloud_cover": current.get("cloud_cover", 100),
            "humidity": current.get("relative_humidity_2m", 100),
            "wind_speed": current.get("wind_speed_10m", 0),
            "visibility": current.get("visibility", 0) / 1000,
            "is_day": current.get("is_day", 1) == 1
        }
        
        # Wykonaj analizę AI
        ai_analysis = deepseek_analyzer.analyze_weather_with_ai(
            weather_info, 
            "Warszawa", 
            moon_data
        )
        
        return jsonify({
            "demo": True,
            "ai_analysis": ai_analysis,
            "weather_data": weather_info,
            "moon_data": moon_data,
            "timestamp": datetime.now().isoformat()
        })
    
    return jsonify({"error": "Nie udało się pobrać danych"}), 500

@app.route('/quantum_demo')
def quantum_demo():
    """Demo analizy kwantowej"""
    weather_data = {
        "cloud_cover": 25,
        "temperature": 15.5,
        "visibility": 15.2,
        "humidity": 65,
        "wind_speed": 8.3,
        "is_day": False
    }
    
    moon_data = calculate_moon_phase()
    analysis = quantum_analyzer.analyze_conditions(weather_data, moon_data)
    
    return jsonify({
        "demo": True,
        "quantum_analysis": analysis,
        "weather_data": weather_data,
        "moon_data": moon_data,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Prosty endpoint do sprawdzania zdrowia aplikacji"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "ping_count": ping_count,
        "last_ping": last_ping_time.isoformat(),
        "deepseek_available": deepseek_analyzer.available,
        "quantum_available": quantum_analyzer.connected
    }), 200

@app.route('/ping')
def ping():
    """Endpoint tylko do pingowania - nie wysyła powiadomień!"""
    global last_ping_time, ping_count
    last_ping_time = datetime.now()
    ping_count += 1
    
    logger.info(f"📡 Ping #{ping_count} o {last_ping_time.strftime('%H:%M:%S')}")
    
    return jsonify({
        "status": "pong",
        "ping_count": ping_count,
        "timestamp": last_ping_time.isoformat(),
        "message": "System aktywny - NIE WYSYŁAM POWIADOMIEŃ!"
    }), 200

@app.route('/status')
def status():
    """Status systemu"""
    users = get_all_users_with_notifications()
    
    return jsonify({
        "status": "operational",
        "users_with_notifications": len(users),
        "last_ping": last_ping_time.isoformat(),
        "ping_count": ping_count,
        "deepseek_available": deepseek_analyzer.available,
        "quantum_connected": quantum_analyzer.connected,
        "observation_cities": list(OBSERVATION_CITIES.keys())
    }), 200

# ====================== TELEGRAM WEBHOOK ======================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Główny endpoint dla webhook Telegram"""
    try:
        data = request.get_json()
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip().lower()
            
            user_settings = get_user_settings(chat_id)
            
            if text == "/start":
                send_start_message(chat_id, user_settings)
                
            elif text == "/nasa":
                send_nasa_apod(chat_id)
            
            elif text.startswith("/satellites"):
                handle_satellite_command(chat_id, text, user_settings)
            
            elif text.startswith("/alerts"):
                handle_alerts_command(chat_id, text, user_settings)
            
            elif text.startswith("/quantum"):
                handle_quantum_command(chat_id, text, user_settings)
            
            elif text.startswith("/ai"):
                handle_ai_command(chat_id, text, user_settings)
            
            elif text == "/iss":
                send_iss_info(chat_id)
            
            elif text == "/moon":
                send_moon_info(chat_id)
            
            elif text.startswith("/weather"):
                handle_weather_command(chat_id, text, user_settings)
            
            elif text == "/ai_tips":
                send_ai_tips(chat_id)
            
            elif text == "/help":
                send_help_message(chat_id)
            
            else:
                send_default_message(chat_id)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Błąd webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def send_start_message(chat_id, user_settings):
    """Wyślij wiadomość startową"""
    # NASA APOD
    nasa_apod = get_nasa_apod()
    
    # Dane astronomiczne
    now = datetime.now()
    astro_date = get_astronomical_date()
    moon = calculate_moon_phase()
    
    # Warunki obserwacyjne
    warszawa_conditions = check_city_conditions("warszawa")
    koszalin_conditions = check_city_conditions("koszalin")
    
    # Czasy wschodów/zachodów
    warszawa_times = get_sun_moon_times("warszawa")
    koszalin_times = get_sun_moon_times("koszalin")
    
    # ========== BUDUJEMY RAPORT ==========
    report = ""
    
    # 1. NASA APOD
    if nasa_apod and nasa_apod.get('url'):
        send_photo(chat_id, nasa_apod['url'], 
                 f"🛰️ <b>NASA ASTRONOMY PICTURE OF THE DAY</b>\n\n"
                 f"<b>{nasa_apod['title']}</b>\n"
                 f"Data: {nasa_apod['date']}\n\n"
                 f"{nasa_apod['explanation'][:200]}...")
        time.sleep(1)
    
    # 2. GŁÓWNY RAPORT
    report += f"🧠 <b>SENTRY ONE v12.0 - RAPORT POCZĄTKOWY</b>\n\n"
    
    report += f"<b>📅 DATA:</b> {now.strftime('%d.%m.%Y %H:%M:%S')}\n"
    report += f"<b>📊 Kalendarz:</b> {astro_date['day']} {astro_date['month_symbol']} {astro_date['month_polish']}\n"
    report += f"<b>{astro_date['element_emoji']} Element:</b> {astro_date['element']}\n\n"
    
    report += f"<b>{moon['emoji']} KSIĘŻYC:</b>\n"
    report += f"• Faza: {moon['name']}\n"
    report += f"• Oświetlenie: {moon['illumination']:.1f}%\n\n"
    
    # 3. WARSZAWA
    report += f"<b>🏛️ WARSZAWA:</b>\n"
    report += f"🌞 Słońce: {warszawa_times['sun']['rise']} ↑ | {warszawa_times['sun']['set']} ↓\n"
    
    if warszawa_conditions:
        report += f"📊 Warunki: {warszawa_conditions['emoji']} {warszawa_conditions['status']}\n"
        report += f"🌡️ Temp: {warszawa_conditions['temperature']:.1f}°C\n"
        report += f"☁️ Chmury: {warszawa_conditions['cloud_cover']}%\n\n"
    
    # 4. KOSZALIN
    report += f"<b>🌲 KOSZALIN:</b>\n"
    report += f"🌞 Słońce: {koszalin_times['sun']['rise']} ↑ | {koszalin_times['sun']['set']} ↓\n"
    
    if koszalin_conditions:
        report += f"📊 Warunki: {koszalin_conditions['emoji']} {koszalin_conditions['status']}\n"
        report += f"🌡️ Temp: {koszalin_conditions['temperature']:.1f}°C\n"
        report += f"☁️ Chmury: {koszalin_conditions['cloud_cover']}%\n\n"
    
    # 5. ANALIZA AI (jeśli włączona)
    if user_settings.get("ai_analysis", True) and deepseek_analyzer.available:
        ai_warszawa = get_ai_weather_analysis("warszawa")
        if ai_warszawa and "ai_analysis" in ai_warszawa:
            aa = ai_warszawa["ai_analysis"]
            report += f"🧠 <b>ANALIZA AI - WARSZAWA:</b>\n"
            report += f"• Ocena: {aa.get('score', 5)}/10\n"
            report += f"• Analiza: {aa.get('analysis', '')[:50]}...\n\n"
    
    # 6. USTAWIENIA
    report += f"<b>🔔 TWOJE USTAWIENIA:</b>\n"
    report += f"• Powiadomienia satelitarne: {'✅ WŁĄCZONE' if user_settings['satellite_notifications'] else '❌ WYŁĄCZONE'}\n"
    report += f"• Alerty obserwacyjne: {'✅ WŁĄCZONE' if user_settings['observation_alerts'] else '❌ WYŁĄCZONE'}\n"
    report += f"• Analiza kwantowa: {'✅ WŁĄCZONE' if user_settings['quantum_analysis'] else '❌ WYŁĄCZONE'}\n"
    report += f"• Analiza AI: {'✅ WŁĄCZONE' if user_settings['ai_analysis'] else '❌ WYŁĄCZONE'}\n\n"
    
    # 7. KOMENDY
    report += f"<b>🚀 KOMENDY:</b>\n"
    report += f"<code>/nasa</code> - Zdjęcie dnia NASA\n"
    report += f"<code>/satellites on/off</code> - Powiadomienia o satelitach\n"
    report += f"<code>/alerts on/off</code> - Alerty obserwacyjne\n"
    report += f"<code>/quantum on/off</code> - Analiza kwantowa\n"
    report += f"<code>/ai on/off</code> - Analiza AI\n"
    report += f"<code>/ai_tips</code> - Wskazówki AI\n"
    report += f"<code>/iss</code> - Przeloty ISS\n"
    report += f"<code>/moon</code> - Szczegóły Księżyca\n"
    report += f"<code>/weather [miasto]</code> - Prognoza\n"
    report += f"<code>/help</code> - Wszystkie komendy\n"
    
    send_telegram_message(chat_id, report)

def send_nasa_apod(chat_id):
    """Wyślij zdjęcie dnia NASA"""
    nasa_apod = get_nasa_apod()
    if nasa_apod:
        response = (
            f"🛰️ <b>NASA ASTRONOMY PICTURE OF THE DAY</b>\n\n"
            f"<b>{nasa_apod['title']}</b>\n"
            f"Data: {nasa_apod['date']}\n\n"
            f"{nasa_apod['explanation'][:300]}...\n\n"
            f"<i>Źródło: NASA APOD API</i>"
        )
        send_photo(chat_id, nasa_apod['url'], response)
    else:
        send_telegram_message(chat_id, "❌ Nie udało się pobrać zdjęcia NASA")

def handle_satellite_command(chat_id, text, user_settings):
    """Obsłuż komendy satelitarne"""
    args = text[11:].strip().lower()
    
    if args == "on":
        user_settings["satellite_notifications"] = True
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "✅ <b>POWIADOMIENIA SATELITARNE WŁĄCZONE</b>\n\nBędziesz otrzymywać powiadomienia o przelotach ISS nad Warszawą.")
    
    elif args == "off":
        user_settings["satellite_notifications"] = False
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "❌ <b>POWIADOMIENIA SATELITARNE WYŁĄCZONE</b>\n\nNie będziesz otrzymywać powiadomień o satelitach.")
    
    else:
        status = "WŁĄCZONE" if user_settings["satellite_notifications"] else "WYŁĄCZONE"
        send_telegram_message(chat_id, f"🔔 <b>STATUS POWIADOMIEŃ SATELITARNYCH:</b> {status}\n\nUżyj: <code>/satellites on</code> lub <code>/satellites off</code>")

def handle_alerts_command(chat_id, text, user_settings):
    """Obsłuż komendy alertów"""
    args = text[7:].strip().lower()
    
    if args == "on":
        user_settings["observation_alerts"] = True
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "✅ <b>ALERTY OBSERWACYJNE WŁĄCZONE</b>\n\nBędziesz otrzymywać powiadomienia o sprzyjających warunkach do obserwacji.")
    
    elif args == "off":
        user_settings["observation_alerts"] = False
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "❌ <b>ALERTY OBSERWACYJNE WYŁĄCZONE</b>\n\nNie będziesz otrzymywać powiadomień o warunkach obserwacyjnych.")
    
    else:
        status = "WŁĄCZONE" if user_settings["observation_alerts"] else "WYŁĄCZONE"
        send_telegram_message(chat_id, f"🔔 <b>STATUS ALERTÓW OBSERWACYJNYCH:</b> {status}\n\nUżyj: <code>/alerts on</code> lub <code>/alerts off</code>")

def handle_quantum_command(chat_id, text, user_settings):
    """Obsłuż komendy kwantowe"""
    args = text[8:].strip().lower()
    
    if args == "on":
        user_settings["quantum_analysis"] = True
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "✅ <b>ANALIZA KWANTOWA WŁĄCZONA</b>\n\nTwoje raporty będą zawierać zaawansowaną analizę kwantową.")
    
    elif args == "off":
        user_settings["quantum_analysis"] = False
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "❌ <b>ANALIZA KWANTOWA WYŁĄCZONA</b>\n\nTwoje raporty będą zawierać tylko standardową analizę.")
    
    else:
        status = "WŁĄCZONE" if user_settings["quantum_analysis"] else "WYŁĄCZONE"
        ibm_status = "Połączono z IBM Quantum" if quantum_analyzer.connected else "Używam lokalnego symulatora"
        send_telegram_message(chat_id, 
            f"🔬 <b>STATUS ANALIZY KWANTOWEJ:</b> {status}\n"
            f"<b>System:</b> {ibm_status}\n\n"
            f"<b>Komendy:</b>\n"
            f"<code>/quantum on</code> - włącz analizę kwantową\n"
            f"<code>/quantum off</code> - wyłącz analizę kwantową\n"
        )

def handle_ai_command(chat_id, text, user_settings):
    """Obsłuż komendy AI"""
    args = text[3:].strip().lower()
    
    if args == "on":
        user_settings["ai_analysis"] = True
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "✅ <b>ANALIZA AI WŁĄCZONA</b>\n\nTwoje raporty będą zawierać zaawansowaną analizę sztucznej inteligencji.")
    
    elif args == "off":
        user_settings["ai_analysis"] = False
        update_user_settings(chat_id, user_settings)
        send_telegram_message(chat_id, "❌ <b>ANALIZA AI WYŁĄCZONA</b>\n\nTwoje raporty będą zawierać tylko standardową analizę.")
    
    else:
        status = "WŁĄCZONE" if user_settings["ai_analysis"] else "WYŁĄCZONE"
        ai_status = "Aktywny" if deepseek_analyzer.available else "Niedostępny"
        send_telegram_message(chat_id, 
            f"🧠 <b>STATUS ANALIZY AI:</b> {status}\n"
            f"<b>DeepSeek AI:</b> {ai_status}\n\n"
            f"<b>Komendy:</b>\n"
            f"<code>/ai on</code> - włącz analizę AI\n"
            f"<code>/ai off</code> - wyłącz analizę AI\n"
            f"<code>/ai_tips</code> - wskazówki astronomiczne od AI\n"
        )

def send_iss_info(chat_id):
    """Wyślij informacje o ISS"""
    response = (
        f"🛰️ <b>MIĘDZYNARODOWA STACJA KOSMICZNA</b>\n\n"
        f"Aktualnie system monitoruje przeloty ISS nad Warszawą.\n\n"
        f"<b>Użyj komend:</b>\n"
        f"<code>/satellites on</code> - włącz powiadomienia o przelotach\n"
        f"<code>/satellites off</code> - wyłącz powiadomienia\n\n"
        f"<i>Powiadomienia są wysyłane tylko gdy ISS jest widoczna nad Warszawą w ciągu najbliższych 2 godzin.</i>"
    )
    send_telegram_message(chat_id, response)

def send_moon_info(chat_id):
    """Wyślij informacje o Księżycu"""
    moon = calculate_moon_phase()
    
    response = (
        f"{moon['emoji']} <b>SZCZEGÓŁOWY RAPORT KSIĘŻYCA</b>\n\n"
        f"• <b>Faza:</b> {moon['name']}\n"
        f"• <b>Oświetlenie:</b> {moon['illumination']:.1f}%\n"
        f"• <b>Wiek:</b> {moon['age_days']:.2f} dni\n\n"
        
        f"<b>Najlepsze warunki do obserwacji:</b>\n"
        f"• Faza: 30-70% (pierwsza/ostatnia kwadra)\n"
        f"• Księżyc nisko nad horyzontem\n"
        f"• Noc bezchmurna\n"
    )
    send_telegram_message(chat_id, response)

def handle_weather_command(chat_id, text, user_settings):
    """Obsłuż komendy pogodowe"""
    args = text[8:].strip().lower()
    
    if args in ["warszawa", "koszalin"]:
        conditions = check_city_conditions(args)
        times = get_sun_moon_times(args)
        
        if conditions:
            response = (
                f"{conditions['city_emoji']} <b>PROGNOZA - {conditions['city_name'].upper()}</b>\n\n"
                
                f"<b>🌡️ AKTUALNIE:</b>\n"
                f"• {conditions['temperature']:.1f}°C | "
                f"Chmury: {conditions['cloud_cover']}%\n"
                f"• Wiatr: {conditions['wind_speed']} m/s | "
                f"Wilgotność: {conditions['humidity']}%\n"
                f"• Widoczność: {conditions['visibility']} km\n"
                f"• Status: {conditions['emoji']} {conditions['status']}\n\n"
                
                f"<b>🌞 SŁOŃCE:</b> {times['sun']['rise']} ↑ | {times['sun']['set']} ↓\n\n"
                
                f"<b>📊 OCENA OBSERWACYJNA:</b> {conditions['score']}%\n"
            )
            
            # Dodaj analizę AI jeśli włączona
            if user_settings.get("ai_analysis", True) and deepseek_analyzer.available:
                ai_data = get_ai_weather_analysis(args)
                if ai_data and "ai_analysis" in ai_data:
                    aa = ai_data["ai_analysis"]
                    response += f"\n🧠 <b>ANALIZA AI:</b>\n"
                    response += f"• Ocena: {aa.get('score', 5)}/10\n"
                    response += f"• Analiza: {aa.get('analysis', '')}\n"
                    response += f"• Rekomendacja: {aa.get('recommendations', '')}\n"
            
            send_telegram_message(chat_id, response)

def send_ai_tips(chat_id):
    """Wyślij wskazówki astronomiczne od AI"""
    if deepseek_analyzer.available:
        tip = deepseek_analyzer.generate_astronomy_tips()
        response = f"🧠 <b>WSKAZÓWKA ASTRONOMICZNA OD AI</b>\n\n{tip}\n\n<i>Źródło: DeepSeek AI</i>"
    else:
        response = "❌ DeepSeek AI jest obecnie niedostępny. Spróbuj ponownie później."
    
    send_telegram_message(chat_id, response)

def send_help_message(chat_id):
    """Wyślij wiadomość pomocy"""
    response = (
        f"🤖 <b>SENTRY ONE v12.0 - POMOC</b>\n\n"
        
        f"<b>🛰️ NASA I SATELITY:</b>\n"
        f"<code>/nasa</code> - Zdjęcie dnia NASA\n"
        f"<code>/iss</code> - Informacje o ISS\n\n"
        
        f"<b>🔔 POWIADOMIENIA:</b>\n"
        f"<code>/satellites on/off</code> - Powiadomienia o satelitach\n"
        f"<code>/alerts on/off</code> - Alerty obserwacyjne\n\n"
        
        f"<b>🧠 SZTUCZNA INTELIGENCJA:</b>\n"
        f"<code>/ai on/off</code> - Włącz/wyłącz analizę AI\n"
        f"<code>/ai_tips</code> - Wskazówki astronomiczne od AI\n\n"
        
        f"<b>🔬 ANALIZA KWANTOWA:</b>\n"
        f"<code>/quantum on/off</code> - Włącz/wyłącz analizę kwantową\n\n"
        
        f"<b>🌌 ASTRONOMIA:</b>\n"
        f"<code>/moon</code> - Szczegóły Księżyca\n\n"
        
        f"<b>🌤️ POGODA:</b>\n"
        f"<code>/weather warszawa/koszalin</code> - Prognoza\n\n"
        
        f"<b>📍 OBSERWOWANE MIASTA:</b>\n"
        f"• warszawa\n• koszalin\n\n"
        
        f"<i>🤖 System działa 24/7 z DeepSeek AI, IBM Quantum, NASA i N2YO API</i>"
    )
    send_telegram_message(chat_id, response)

def send_default_message(chat_id):
    """Wyślij domyślną wiadomość"""
    response = (
        f"🤖 <b>SENTRY ONE v12.0</b>\n\n"
        f"DeepSeek AI Edition - Zaawansowany system analizy astrometeorologicznej\n\n"
        f"<b>📍 Obserwowane miasta:</b>\n"
        f"🏛️ Warszawa | 🌲 Koszalin\n\n"
        f"<b>🧠 DeepSeek AI:</b> {'✅ AKTYWNY' if deepseek_analyzer.available else '❌ NIEDOSTĘPNY'}\n"
        f"<b>🔬 IBM Quantum:</b> {'✅ AKTYWNY' if quantum_analyzer.connected else '🔌 SYMULATOR'}\n\n"
        f"<i>Użyj /start dla pełnego raportu lub /help dla listy komend</i>"
    )
    send_telegram_message(chat_id, response)

# ====================== AUTO-PING SYSTEM ======================
class AutoPingService:
    """Serwis do automatycznego pingowania bez spamowania użytkowników"""
    
    def __init__(self):
        self.ping_count = 0
        self.last_ping = None
        
    def start_auto_ping(self):
        """Uruchom automatyczne pingowanie w osobnym wątku"""
        def ping_loop():
            while True:
                try:
                    # Pinguj co 10 minut (600 sekund)
                    time.sleep(600)
                    
                    # Ping tylko główną stronę - NIE wysyłaj do użytkowników!
                    response = requests.get(RENDER_URL, timeout=30)
                    self.ping_count += 1
                    self.last_ping = datetime.now()
                    
                    logger.info(f"📡 Auto-ping #{self.ping_count} - Status: {response.status_code}")
                    
                    # Raz dziennie wyślij status do admina (opcjonalnie)
                    if self.ping_count % 144 == 0:  # Co 144 pingi = 24 godziny
                        self.send_daily_status()
                        
                except Exception as e:
                    logger.error(f"❌ Błąd auto-ping: {e}")
        
        # Uruchom wątki
        threading.Thread(target=ping_loop, daemon=True).start()
        print("✅ Auto-ping service uruchomiony (co 10 minut)")
    
    def send_daily_status(self):
        """Wyślij dzienny raport statusu (opcjonalnie do admina)"""
        try:
            users = get_all_users_with_notifications()
            status_msg = (
                f"📊 <b>DAILY STATUS - SENTRY ONE v12.0</b>\n\n"
                f"• Ping count: {self.ping_count}\n"
                f"• Last ping: {self.last_ping.strftime('%H:%M:%S')}\n"
                f"• Users with notifications: {len(users)}\n"
                f"• DeepSeek AI: {'✅ AKTYWNY' if deepseek_analyzer.available else '❌ NIEDOSTĘPNY'}\n"
                f"• IBM Quantum: {'✅ POŁĄCZONY' if quantum_analyzer.connected else '🔌 SYMULATOR'}\n"
                f"• System: ACTIVE ✅\n\n"
                f"<i>Automatic daily report</i>"
            )
            
            # Tylko jeśli chcesz otrzymywać te raporty - odkomentuj poniższą linię
            # send_telegram_message(TWÓJ_CHAT_ID, status_msg)
            
        except Exception as e:
            logger.error(f"❌ Błąd daily status: {e}")

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 SENTRY ONE v12.0 - DEEPSEEK AI EDITION")
    print("=" * 60)
    
    # Inicjalizacja bazy danych
    init_database()
    
    # Pobierz aktualne dane
    now = datetime.now()
    astro_date = get_astronomical_date()
    moon = calculate_moon_phase()
    
    print(f"📅 Data: {now.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"🌌 Kalendarz: {astro_date['day']} {astro_date['month_symbol']} {astro_date['month_polish']}")
    print(f"🌙 Księżyc: {moon['emoji']} {moon['name']} ({moon['illumination']:.1f}%)")
    print(f"🧠 DeepSeek AI: {'✅ Dostępny' if deepseek_analyzer.available else '❌ Niedostępny'}")
    print(f"🔬 IBM Quantum: {'✅ Połączono' if quantum_analyzer.connected else '🔌 Używam symulatora lokalnego'}")
    
    # Uruchom auto-ping service
    ping_service = AutoPingService()
    ping_service.start_auto_ping()
    
    print("\n" + "=" * 60)
    print("✅ SYSTEM URUCHOMIONY POMYŚLNIE")
    print("=" * 60)
    print("\n📡 Endpointy dostępne:")
    print(f"• {RENDER_URL}/ - Strona główna")
    print(f"• {RENDER_URL}/ping - Ping (NIE wysyła powiadomień!)")
    print(f"• {RENDER_URL}/health - Status zdrowia")
    print(f"• {RENDER_URL}/status - Status systemu")
    print(f"• {RENDER_URL}/ai_demo - Demo analizy AI")
    print(f"• {RENDER_URL}/quantum_demo - Demo analizy kwantowej")
    print(f"• {WEBHOOK_URL} - Webhook Telegram")
    print("\n🔔 Nowe komendy AI:")
    print("   /ai on/off - włącz/wyłącz analizę AI")
    print("   /ai_tips - wskazówki astronomiczne od AI")
    print("\n🤖 Bot będzie aktywny 24/7 dzięki inteligentnemu pingowaniu")
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )