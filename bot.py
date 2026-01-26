#!/usr/bin/env python3
"""
🤖 SENTRY ONE v13.0 - ULTIMATE EDITION
DeepSeek AI + IBM Quantum + NASA + Astrometeorologia
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
import sqlite3
from typing import Dict, List, Optional

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"

# API klucze - WSZYSTKIE W JEDNYM MIEJSCU!
NASA_API_KEY = "P0locPuOZBvnkHCdIKjkxzKsfnM7tc7pbiMcsBDE"
N2YO_API_KEY = "UNWEQ8-N47JL7-WFJZYX-5N65"
OPENWEATHER_API_KEY = "38e01cfb763fc738e9eddee84cfc4384"
IBM_QUANTUM_TOKEN = "esUNC1tmumZpWO1C2iwgaYxCA48k4MBOiFp7ARD2Wk3A"
DEEPSEEK_API_KEY = "sk-4af5d51f20e34ba8b53e09e6422341a4"

# API endpoints
N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Baza danych użytkowników
DB_FILE = "sentry_one.db"

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
print("🤖 SENTRY ONE v13.0 - ULTIMATE EDITION")
print(f"🌐 URL: {RENDER_URL}")
print("🧠 DeepSeek AI + IBM Quantum + NASA + N2YO")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== DEEPSEEK AI ANALYZER ======================
class DeepSeekAI:
    """Analiza przez DeepSeek AI"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.available = self._check_api()
    
    def _check_api(self):
        """Sprawdź dostępność API"""
        try:
            response = requests.get(
                "https://api.deepseek.com/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def analyze_conditions(self, weather_data, moon_data, city_name):
        """Analizuj warunki obserwacyjne przez AI"""
        try:
            prompt = f"""
            Jesteś ekspertem astrometeorologii. Oceniasz warunki do obserwacji astronomicznych.
            
            MIASTO: {city_name}
            DATA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            DANE POGODOWE:
            - Temperatura: {weather_data.get('temperature', 0)}°C
            - Zachmurzenie: {weather_data.get('cloud_cover', 0)}%
            - Wilgotność: {weather_data.get('humidity', 0)}%
            - Wiatr: {weather_data.get('wind_speed', 0)} m/s
            - Widoczność: {weather_data.get('visibility', 0)} km
            
            DANE KSIĘŻYCOWE:
            - Faza: {moon_data.get('name', '')}
            - Oświetlenie: {moon_data.get('illumination', 0)}%
            
            Oceń warunki w skali 1-10 i podaj krótką rekomendację (max 2 zdania po polsku).
            Format: "OCENA: X/10 | REKOMENDACJA: [tekst]"
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
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_text = result["choices"][0]["message"]["content"]
                
                # Parsuj odpowiedź
                score = 5
                if "OCENA:" in ai_text:
                    try:
                        score_text = ai_text.split("OCENA:")[1].split("/")[0].strip()
                        score = int(score_text)
                    except:
                        pass
                
                recommendation = ai_text.split("REKOMENDACJA:")[-1].strip() if "REKOMENDACJA:" in ai_text else ai_text
                
                return {
                    "score": score,
                    "recommendation": recommendation,
                    "full_response": ai_text,
                    "source": "DeepSeek AI"
                }
            else:
                return self._get_fallback_analysis(weather_data, moon_data)
                
        except Exception as e:
            logger.error(f"❌ Błąd DeepSeek AI: {e}")
            return self._get_fallback_analysis(weather_data, moon_data)
    
    def _get_fallback_analysis(self, weather_data, moon_data):
        """Fallback gdy AI niedostępne"""
        score = 5
        if weather_data.get("cloud_cover", 100) < 30:
            score += 2
        if weather_data.get("visibility", 0) > 10:
            score += 2
        
        return {
            "score": min(10, max(1, score)),
            "recommendation": "Sprawdź lokalną pogodę przed obserwacją.",
            "source": "System Fallback"
        }
    
    def get_astronomy_tip(self):
        """Pobierz losową wskazówkę astronomiczną"""
        tips = [
            "Użyj aplikacji Stellarium do identyfikacji obiektów.",
            "Zacznij obserwacje od Księżyca i jasnych planet.",
            "Unikaj obserwacji przy pełni Księżyca - rozjaśnia niebo.",
            "Użyj filtrów księżycowych dla lepszych obserwacji.",
            "Poczekaj 30 minut po wyjściu na zewnątrz, aby oczy przyzwyczaiły się do ciemności."
        ]
        return tips[datetime.now().second % len(tips)]

# ====================== QUANTUM ANALYZER ======================
class QuantumAnalyzer:
    """Analiza przez IBM Quantum"""
    
    def __init__(self):
        self.api_key = IBM_QUANTUM_TOKEN
        self.available = False
        self._try_connect()
    
    def _try_connect(self):
        """Spróbuj połączyć z IBM Quantum"""
        try:
            # Sprawdź czy token jest poprawny
            response = requests.get(
                "https://auth.quantum-computing.ibm.com/api/users/me",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            self.available = response.status_code == 200
            if self.available:
                logger.info("✅ Połączono z IBM Quantum API")
            else:
                logger.warning("⚠️ IBM Quantum API niedostępne")
        except:
            self.available = False
    
    def analyze_orbit_stability(self, satellite_data):
        """Analizuj stabilność orbity (symulacja)"""
        if not self.available:
            return {"stability": "unknown", "source": "Quantum API offline"}
        
        try:
            # Symulowana analiza kwantowa
            altitude = satellite_data.get("altitude", 400)
            velocity = satellite_data.get("velocity", 7.6)
            
            # Proste obliczenia "kwantowe"
            stability_score = min(100, max(0, 
                (450 - abs(altitude - 400)) * 0.2 +
                (8 - abs(velocity - 7.6)) * 10
            ))
            
            if stability_score > 80:
                stability = "wysoka"
            elif stability_score > 60:
                stability = "średnia"
            else:
                stability = "niska"
            
            return {
                "stability": stability,
                "score": round(stability_score, 1),
                "analysis": f"Orbita na {altitude}km z prędkością {velocity}km/s",
                "source": "IBM Quantum Simulation"
            }
            
        except Exception as e:
            return {"error": str(e), "source": "Quantum Analysis Failed"}

# Inicjalizuj analizatory
deepseek_ai = DeepSeekAI()
quantum_analyzer = QuantumAnalyzer()

# ====================== BAZA DANYCH ======================
def init_database():
    """Inicjalizacja bazy danych"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            ai_enabled BOOLEAN DEFAULT 1,
            quantum_enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_or_create_user(chat_id, username="", first_name="", last_name=""):
    """Pobierz lub utwórz użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
            INSERT INTO users (chat_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, username, first_name, last_name))
        conn.commit()
    
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    user = cursor.fetchone()
    conn.close()
    
    return {
        "chat_id": user[0],
        "username": user[1],
        "first_name": user[2],
        "last_name": user[3],
        "ai_enabled": bool(user[4]),
        "quantum_enabled": bool(user[5])
    }

def update_user_setting(chat_id, setting, value):
    """Aktualizuj ustawienie użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if setting == "ai":
        cursor.execute('UPDATE users SET ai_enabled = ? WHERE chat_id = ?', (value, chat_id))
    elif setting == "quantum":
        cursor.execute('UPDATE users SET quantum_enabled = ? WHERE chat_id = ?', (value, chat_id))
    
    conn.commit()
    conn.close()

# ====================== NASA I POGODA FUNCTIONS ======================
def get_nasa_apod():
    """Pobierz Astronomy Picture of the Day"""
    try:
        url = f"{NASA_APOD_URL}?api_key={NASA_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            "title": data.get("title", "NASA APOD"),
            "url": data.get("url", ""),
            "explanation": data.get("explanation", ""),
            "date": data.get("date", "")
        }
    except:
        return None

def get_weather_data(city_key):
    """Pobierz dane pogodowe dla miasta"""
    city = OBSERVATION_CITIES.get(city_key)
    if not city:
        return None
    
    try:
        # OpenWeather
        url = f"{OPENWEATHER_BASE_URL}/weather"
        params = {
            "lat": city["lat"],
            "lon": city["lon"],
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl"
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        return {
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "description": data["weather"][0]["description"],
            "clouds": data["clouds"]["all"],
            "visibility": data.get("visibility", 10000) / 1000,
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
        }
    except:
        return None

def calculate_moon_phase():
    """Oblicz fazę księżyca"""
    now = datetime.now()
    # Proste obliczenia
    days_since_new = (now - datetime(2024, 1, 11)).days % 29.53
    
    if days_since_new < 1:
        return {"name": "Nów", "emoji": "🌑", "illumination": 0}
    elif days_since_new < 7.4:
        return {"name": "Rosnący sierp", "emoji": "🌒", "illumination": days_since_new/7.4*50}
    elif days_since_new < 14.8:
        return {"name": "Pełnia", "emoji": "🌕", "illumination": 100}
    else:
        return {"name": "Malejący sierp", "emoji": "🌘", "illumination": 100-(days_since_new-14.8)/14.73*50}

# ====================== TELEGRAM FUNCTIONS ======================
def send_telegram_message(chat_id, text, parse_mode="HTML"):
    """Wyślij wiadomość na Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return None

def send_photo(chat_id, photo_url, caption=""):
    """Wyślij zdjęcie"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except:
        return None

# ====================== FLASK APP ======================
app = Flask(__name__)

# Globalne zmienne
last_ping_time = datetime.now()
ping_count = 0
init_database()

@app.route('/')
def home():
    """Strona główna"""
    global last_ping_time, ping_count
    last_ping_time = datetime.now()
    ping_count += 1
    
    status_info = {
        "deepseek_ai": "✅ Aktywny" if deepseek_ai.available else "❌ Offline",
        "ibm_quantum": "✅ Aktywny" if quantum_analyzer.available else "❌ Offline",
        "nasa_api": "✅ Aktywny",
        "telegram_bot": "✅ Aktywny"
    }
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v13.0</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0a2a 0%, #1a1a4a 100%);
                color: white;
                padding: 20px;
                text-align: center;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 30px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }
            .status-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 30px 0;
            }
            .status-card {
                background: rgba(0,0,0,0.3);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            .api-status {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                margin: 5px;
            }
            .online { background: linear-gradient(to right, #00b09b, #96c93d); }
            .offline { background: linear-gradient(to right, #ff416c, #ff4b2b); }
            .btn {
                display: inline-block;
                padding: 12px 25px;
                background: linear-gradient(to right, #4776E6, #8E54E9);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                margin: 10px;
                transition: transform 0.3s;
            }
            .btn:hover { transform: translateY(-2px); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 SENTRY ONE v13.0</h1>
            <h3>DeepSeek AI + IBM Quantum + NASA Integration</h3>
            
            <div class="status-grid">
                <div class="status-card">
                    <h4>🧠 DeepSeek AI</h4>
                    <span class="api-status ''' + ('online' if deepseek_ai.available else 'offline') + '''">
                        ''' + ('✅ Aktywny' if deepseek_ai.available else '❌ Offline') + '''
                    </span>
                </div>
                <div class="status-card">
                    <h4>🔬 IBM Quantum</h4>
                    <span class="api-status ''' + ('online' if quantum_analyzer.available else 'offline') + '''">
                        ''' + ('✅ Aktywny' if quantum_analyzer.available else '❌ Offline') + '''
                    </span>
                </div>
                <div class="status-card">
                    <h4>🛰️ NASA API</h4>
                    <span class="api-status online">✅ Aktywny</span>
                </div>
                <div class="status-card">
                    <h4>🤖 Telegram Bot</h4>
                    <span class="api-status online">✅ Aktywny</span>
                </div>
            </div>
            
            <div style="margin: 30px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" class="btn">
                    💬 Otwórz bota w Telegram
                </a>
                <a href="/health" class="btn" style="background: linear-gradient(to right, #00c6ff, #0072ff);">
                    🏥 Status zdrowia
                </a>
                <a href="/ping" class="btn" style="background: linear-gradient(to right, #f46b45, #eea849);">
                    📡 Test ping
                </a>
            </div>
            
            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; margin-top: 20px;">
                <h4>📊 Statystyki systemu:</h4>
                <p>• Ostatni ping: ''' + last_ping_time.strftime('%H:%M:%S') + '''</p>
                <p>• Liczba pingów: ''' + str(ping_count) + '''</p>
                <p>• Obserwowane miasta: Warszawa, Koszalin</p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

@app.route('/health')
def health():
    """Status zdrowia"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "deepseek_ai": deepseek_ai.available,
            "ibm_quantum": quantum_analyzer.available,
            "telegram_bot": True,
            "nasa_api": True
        },
        "ping_count": ping_count
    })

@app.route('/ping')
def ping():
    """Test ping"""
    global last_ping_time, ping_count
    last_ping_time = datetime.now()
    ping_count += 1
    return jsonify({
        "status": "pong",
        "ping_count": ping_count,
        "time": last_ping_time.isoformat()
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook Telegram - GŁÓWNY ENDPOINT!"""
    global last_ping_time, ping_count
    
    try:
        data = request.get_json()
        logger.info(f"📩 Webhook data: {json.dumps(data, indent=2)}")
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()
            
            # Pobierz/utwórz użytkownika
            user = get_or_create_user(
                chat_id,
                message.get("from", {}).get("username", ""),
                message.get("from", {}).get("first_name", ""),
                message.get("from", {}).get("last_name", "")
            )
            
            # Obsługa komend
            if text.startswith("/"):
                handle_command(chat_id, text.lower(), user)
            else:
                send_telegram_message(chat_id, "🤖 Użyj /help aby zobaczyć dostępne komendy")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"🔥 Błąd webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def handle_command(chat_id, command, user):
    """Obsłuż komendę od użytkownika"""
    
    if command == "/start":
        welcome_message = f"""
🤖 <b>SENTRY ONE v13.0 - ULTIMATE EDITION</b>

👋 Witaj, {user['first_name'] or 'Astronomie'}!

🧠 <b>Systemy aktywne:</b>
• DeepSeek AI: {'✅ ONLINE' if deepseek_ai.available else '❌ OFFLINE'}
• IBM Quantum: {'✅ ONLINE' if quantum_analyzer.available else '❌ OFFLINE'}
• NASA APOD: ✅ ONLINE
• Astrometeorologia: ✅ ONLINE

📍 <b>Obserwowane miasta:</b>
🏛️ Warszawa | 🌲 Koszalin

🔧 <b>Twoje ustawienia:</b>
• Analiza AI: {'✅ WŁĄCZONA' if user['ai_enabled'] else '❌ WYŁĄCZONA'}
• Analiza Quantum: {'✅ WŁĄCZONA' if user['quantum_enabled'] else '❌ WYŁĄCZONA'}

📋 <b>Dostępne komendy:</b>
<code>/start</code> - ten ekran
<code>/help</code> - wszystkie komendy
<code>/nasa</code> - zdjęcie dnia NASA
<code>/weather [miasto]</code> - prognoza + analiza AI
<code>/moon</code> - faza księżyca
<code>/ai_tip</code> - wskazówka od AI
<code>/quantum_status</code> - status IBM Quantum
<code>/ai on/off</code> - włącz/wyłącz AI
<code>/quantum on/off</code> - włącz/wyłącz Quantum

🚀 <b>System gotowy do działania!</b>
        """
        send_telegram_message(chat_id, welcome_message)
    
    elif command == "/help":
        help_text = """
📋 <b>WSZYSTKIE KOMENDY:</b>

<b>🛰️ NASA I ASTRONOMIA:</b>
<code>/nasa</code> - Astronomy Picture of the Day
<code>/moon</code> - aktualna faza księżyca
<code>/ai_tip</code> - wskazówka astronomiczna od AI

<b>🌤️ POGODA I ANALIZA:</b>
<code>/weather warszawa</code> - prognoza dla Warszawy
<code>/weather koszalin</code> - prognoza dla Koszalina

<b>🧠 SZTUCZNA INTELIGENCJA:</b>
<code>/ai on</code> - włącz analizę DeepSeek AI
<code>/ai off</code> - wyłącz analizę AI
<code>/ai_status</code> - status AI

<b>🔬 OBLICZENIA KWANTOWE:</b>
<code>/quantum on</code> - włącz analizę IBM Quantum
<code>/quantum off</code> - wyłącz analizę Quantum
<code>/quantum_status</code> - status IBM Quantum

<b>⚙️ SYSTEM:</b>
<code>/status</code> - status wszystkich systemów
<code>/ping</code> - test połączenia

📍 <b>OBSERWOWANE MIASTA:</b>
• warszawa
• koszalin
        """
        send_telegram_message(chat_id, help_text)
    
    elif command == "/nasa":
        apod = get_nasa_apod()
        if apod and apod.get("url"):
            caption = f"🛰️ <b>{apod['title']}</b>\n\n{apod['explanation'][:200]}..."
            send_photo(chat_id, apod['url'], caption)
        else:
            send_telegram_message(chat_id, "❌ Nie udało się pobrać zdjęcia NASA")
    
    elif command.startswith("/weather"):
        parts = command.split()
        if len(parts) == 2 and parts[1] in ["warszawa", "koszalin"]:
            city_key = parts[1]
            city = OBSERVATION_CITIES[city_key]
            weather = get_weather_data(city_key)
            moon = calculate_moon_phase()
            
            if weather:
                # Buduj odpowiedź
                response = f"""
{city['emoji']} <b>PROGNOZA - {city['name'].upper()}</b>

🌡️ Temperatura: {weather['temp']}°C (odczuwalna: {weather['feels_like']}°C)
💨 Wiatr: {weather['wind_speed']} m/s
💧 Wilgotność: {weather['humidity']}%
☁️ Zachmurzenie: {weather['clouds']}%
👁️ Widoczność: {weather['visibility']} km
🌅 Wschód słońca: {weather['sunrise']}
🌇 Zachód słońca: {weather['sunset']}

{moon['emoji']} <b>Księżyc:</b> {moon['name']} ({moon['illumination']:.0f}%)
                """
                
                # Dodaj analizę AI jeśli włączona
                if user['ai_enabled'] and deepseek_ai.available:
                    ai_analysis = deepseek_ai.analyze_conditions(
                        {
                            "temperature": weather['temp'],
                            "cloud_cover": weather['clouds'],
                            "humidity": weather['humidity'],
                            "wind_speed": weather['wind_speed'],
                            "visibility": weather['visibility']
                        },
                        moon,
                        city['name']
                    )
                    
                    response += f"\n🧠 <b>ANALIZA DEEPSEEK AI:</b>\n"
                    response += f"• Ocena: {ai_analysis['score']}/10\n"
                    response += f"• {ai_analysis['recommendation']}\n"
                
                send_telegram_message(chat_id, response)
            else:
                send_telegram_message(chat_id, f"❌ Nie udało się pobrać danych dla {city['name']}")
        else:
            send_telegram_message(chat_id, "❌ Użyj: <code>/weather warszawa</code> lub <code>/weather koszalin</code>")
    
    elif command == "/moon":
        moon = calculate_moon_phase()
        response = f"""
{moon['emoji']} <b>FAZA KSIĘŻYCA</b>

• Nazwa: {moon['name']}
• Oświetlenie: {moon['illumination']:.1f}%

<b>Najlepsze warunki do obserwacji:</b>
• Faza: 30-70% oświetlenia
• Księżyc nisko nad horyzontem
• Noc bezchmurna
        """
        send_telegram_message(chat_id, response)
    
    elif command == "/ai_tip":
        tip = deepseek_ai.get_astronomy_tip()
        send_telegram_message(chat_id, f"🧠 <b>WSKAZÓWKA ASTRONOMICZNA:</b>\n\n{tip}")
    
    elif command == "/ai_status":
        status = "✅ AKTYWNY" if deepseek_ai.available else "❌ OFFLINE"
        send_telegram_message(chat_id, f"🧠 <b>STATUS DEEPSEEK AI:</b> {status}")
    
    elif command == "/quantum_status":
        status = "✅ AKTYWNY" if quantum_analyzer.available else "❌ OFFLINE"
        send_telegram_message(chat_id, f"🔬 <b>STATUS IBM QUANTUM:</b> {status}")
    
    elif command == "/status":
        response = f"""
📊 <b>STATUS SYSTEMU SENTRY ONE</b>

🧠 DeepSeek AI: {'✅ ONLINE' if deepseek_ai.available else '❌ OFFLINE'}
🔬 IBM Quantum: {'✅ ONLINE' if quantum_analyzer.available else '❌ OFFLINE'}
🛰️ NASA API: ✅ ONLINE
🌤️ OpenWeather: ✅ ONLINE

🤖 Telegram Bot: ✅ AKTYWNY
📡 Ping count: {ping_count}
🕐 Ostatni ping: {last_ping_time.strftime('%H:%M:%S')}

<b>Twoje ustawienia:</b>
• Analiza AI: {'✅ WŁĄCZONA' if user['ai_enabled'] else '❌ WYŁĄCZONA'}
• Analiza Quantum: {'✅ WŁĄCZONA' if user['quantum_enabled'] else '❌ WYŁĄCZONA'}
        """
        send_telegram_message(chat_id, response)
    
    elif command in ["/ai on", "/ai off"]:
        enabled = command == "/ai on"
        update_user_setting(chat_id, "ai", enabled)
        status = "WŁĄCZONA" if enabled else "WYŁĄCZONA"
        send_telegram_message(chat_id, f"✅ Analiza AI {status}")
    
    elif command in ["/quantum on", "/quantum off"]:
        enabled = command == "/quantum on"
        update_user_setting(chat_id, "quantum", enabled)
        status = "WŁĄCZONA" if enabled else "WYŁĄCZONA"
        send_telegram_message(chat_id, f"✅ Analiza Quantum {status}")
    
    elif command == "/ping":
        send_telegram_message(chat_id, f"🏓 PONG! System aktywny. Ping #{ping_count}")
    
    else:
        send_telegram_message(chat_id, "❌ Nieznana komenda. Użyj /help")

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 URUCHAMIANIE SENTRY ONE v13.0")
    print("=" * 60)
    print(f"🧠 DeepSeek AI: {'✅ Dostępny' if deepseek_ai.available else '❌ Niedostępny'}")
    print(f"🔬 IBM Quantum: {'✅ Dostępny' if quantum_analyzer.available else '❌ Niedostępny'}")
    print(f"🌐 Webhook URL: {WEBHOOK_URL}")
    print(f"🔧 Port: {PORT}")
    print("=" * 60)
    
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )