#!/usr/bin/env python3
"""
🤖 SENTRY ONE v4.0 - z funkcją pogodową
Render.com Telegram Bot z obserwacją astronomiczną
"""

import os
import json
import time
import logging
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"
PING_INTERVAL = 300  # 5 minut (300 sekund)

# Konfiguracja Open-Meteo (BEZPŁATNE API)
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Miasta do obserwacji astronomicznych
OBSERVATION_CITIES = {
    "warszawa": {
        "name": "Warszawa",
        "lat": 52.2297,
        "lon": 21.0122,
        "timezone": "Europe/Warsaw"
    },
    "koszalin": {
        "name": "Koszalin",
        "lat": 54.1943,
        "lon": 16.1712,
        "timezone": "Europe/Warsaw"
    }
}

# Próg dobrej widoczności dla obserwacji astronomicznych
GOOD_CONDITIONS = {
    "max_cloud_cover": 30,      # Maksymalne zachmurzenie w %
    "min_visibility": 10,       # Minimalna widoczność w km
    "max_humidity": 80,         # Maksymalna wilgotność w %
    "max_wind_speed": 15,       # Maksymalna prędkość wiatru w m/s
    "min_temperature": -10,     # Minimalna temperatura w °C
    "max_temperature": 30       # Maksymalna temperatura w °C
}

print("=" * 60)
print("🤖 SENTRY ONE v4.0 - TELEGRAM BOT z POGODĄ")
print(f"🌐 URL: {RENDER_URL}")
print(f"🔗 Webhook: {WEBHOOK_URL}")
print(f"⏰ Ping interval: {PING_INTERVAL}s")
print(f"🌤️  API Pogodowe: Open-Meteo (bezpłatne)")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== DANE AGENTÓW ======================
AGENTS = {
    "echo": {"name": "Echo", "status": "online", "type": "phone", "icon": "📱"},
    "vector": {"name": "Vector", "status": "online", "type": "tablet", "icon": "📟"},
    "visor": {"name": "Visor", "status": "offline", "type": "oculus", "icon": "🕶️"},
    "synergic": {"name": "Synergic", "status": "online", "type": "computer", "icon": "💻"},
    "observator": {"name": "Observator", "status": "online", "type": "weather", "icon": "🌌"}
}

# ====================== PING SYSTEM ======================
class PingService:
    """Serwis do utrzymania aktywności aplikacji"""

    def __init__(self):
        self.ping_count = 0
        self.last_ping = None
        self.is_running = False
        self.scheduler = BackgroundScheduler()

    def start(self):
        """Uruchom pingowanie"""
        if not self.is_running:
            print("🔄 Uruchamianie systemu pingowania...")

            # Dodaj zadanie pingowania co 5 minut
            self.scheduler.add_job(self.ping_self, 'interval', seconds=PING_INTERVAL)
            self.scheduler.start()

            # Pierwszy ping natychmiast
            threading.Thread(target=self.ping_self, daemon=True).start()

            self.is_running = True
            print(f"✅ Pingowanie aktywne co {PING_INTERVAL/60} minut")

    def ping_self(self):
        """Wyślij ping do własnego endpointu"""
        try:
            self.ping_count += 1
            self.last_ping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Ping główny endpoint
            response = requests.get(f"{RENDER_URL}/health", timeout=10)

            # Dodatkowy ping do dashboardu
            requests.get(f"{RENDER_URL}/", timeout=5)

            logger.info(f"📡 Ping #{self.ping_count} wysłany o {self.last_ping} - Status: {response.status_code}")

            # Zapisuj logi pingów do pliku (opcjonalnie)
            with open("ping_log.txt", "a") as f:
                f.write(f"{self.last_ping} - Ping #{self.ping_count} - Status: {response.status_code}\n")

        except Exception as e:
            logger.error(f"❌ Błąd pingowania: {e}")

    def get_stats(self):
        """Zwróć statystyki pingowania"""
        return {
            "ping_count": self.ping_count,
            "last_ping": self.last_ping,
            "is_running": self.is_running,
            "interval_seconds": PING_INTERVAL,
            "next_ping_in": PING_INTERVAL - (time.time() % PING_INTERVAL) if self.is_running else None
        }

    def stop(self):
        """Zatrzymaj pingowanie"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print("⏹️  Pingowanie zatrzymane")

# Inicjalizacja serwisu pingowania
ping_service = PingService()

# ====================== FUNKCJE POGODOWE ======================
def get_weather_forecast(lat, lon):
    """Pobierz prognozę pogody z Open-Meteo"""
    try:
        url = OPENMETEO_BASE_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,wind_direction_10m,visibility,is_day",
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,visibility",
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

def check_astronomical_conditions(weather_data, city_name):
    """Sprawdź warunki do obserwacji astronomicznych"""
    if not weather_data or "current" not in weather_data:
        return None
    
    current = weather_data["current"]
    daily = weather_data.get("daily", {})
    
    # Pobierz aktualne dane
    cloud_cover = current.get("cloud_cover", 100)
    visibility = current.get("visibility", 0) / 1000  # konwertuj na km
    humidity = current.get("relative_humidity_2m", 100)
    wind_speed = current.get("wind_speed_10m", 0)
    temperature = current.get("temperature_2m", 0)
    is_day = current.get("is_day", 1)
    
    # Sprawdź warunki
    conditions_met = 0
    total_conditions = 5
    
    conditions_check = {
        "cloud_cover": cloud_cover <= GOOD_CONDITIONS["max_cloud_cover"],
        "visibility": visibility >= GOOD_CONDITIONS["min_visibility"],
        "humidity": humidity <= GOOD_CONDITIONS["max_humidity"],
        "wind_speed": wind_speed <= GOOD_CONDITIONS["max_wind_speed"],
        "temperature": GOOD_CONDITIONS["min_temperature"] <= temperature <= GOOD_CONDITIONS["max_temperature"]
    }
    
    conditions_met = sum(conditions_check.values())
    
    # Ocena ogólna
    if conditions_met >= 4:
        status = "DOSKONAŁE"
        emoji = "✨"
        description = "Idealne warunki do obserwacji!"
    elif conditions_met >= 3:
        status = "DOBRE"
        emoji = "⭐"
        description = "Dobre warunki do obserwacji"
    elif conditions_met >= 2:
        status = "ŚREDNIE"
        emoji = "⛅"
        description = "Warunki umiarkowane"
    else:
        status = "ZŁE"
        emoji = "🌧️"
        description = "Nieodpowiednie warunki"
    
    # Sprawdź najbliższe godziny (prognoza)
    hourly_forecast = []
    if "hourly" in weather_data:
        times = weather_data["hourly"].get("time", [])[:24]  # Następne 24 godziny
        clouds = weather_data["hourly"].get("cloud_cover", [])[:24]
        
        for i, (time_str, cloud) in enumerate(zip(times, clouds)):
            if cloud <= GOOD_CONDITIONS["max_cloud_cover"]:
                forecast_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                hourly_forecast.append({
                    "time": forecast_time.strftime("%H:%M"),
                    "cloud_cover": cloud,
                    "hour": i
                })
    
    return {
        "city": city_name,
        "status": status,
        "emoji": emoji,
        "description": description,
        "score": round((conditions_met / total_conditions) * 100),
        "is_night": is_day == 0,
        "conditions": {
            "cloud_cover": cloud_cover,
            "visibility_km": round(visibility, 1),
            "humidity": humidity,
            "wind_speed": wind_speed,
            "temperature": temperature,
            "details": conditions_check
        },
        "forecast": {
            "next_good_hours": hourly_forecast[:5],  # Pierwsze 5 dobrych godzin
            "total_good_hours": len(hourly_forecast)
        },
        "sun_times": {
            "sunrise": daily.get("sunrise", [""])[0] if daily.get("sunrise") else "Brak danych",
            "sunset": daily.get("sunset", [""])[0] if daily.get("sunset") else "Brak danych"
        }
    }

def format_weather_message(weather_info):
    """Sformatuj wiadomość pogodową"""
    city = weather_info["city"]
    
    message = (
        f"{weather_info['emoji']} <b>{city.upper()} - Warunki astronomiczne</b>\n"
        f"Status: <b>{weather_info['status']}</b> ({weather_info['score']}%)\n"
        f"{weather_info['description']}\n\n"
        
        f"<b>📊 Aktualne warunki:</b>\n"
        f"• Zachmurzenie: {weather_info['conditions']['cloud_cover']}% "
        f"{'✅' if weather_info['conditions']['details']['cloud_cover'] else '❌'}\n"
        f"• Widoczność: {weather_info['conditions']['visibility_km']} km "
        f"{'✅' if weather_info['conditions']['details']['visibility'] else '❌'}\n"
        f"• Wilgotność: {weather_info['conditions']['humidity']}% "
        f"{'✅' if weather_info['conditions']['details']['humidity'] else '❌'}\n"
        f"• Wiatr: {weather_info['conditions']['wind_speed']} m/s "
        f"{'✅' if weather_info['conditions']['details']['wind_speed'] else '❌'}\n"
        f"• Temperatura: {weather_info['conditions']['temperature']}°C "
        f"{'✅' if weather_info['conditions']['details']['temperature'] else '❌'}\n"
        f"• Czas: {'🌙 Noc' if weather_info['is_night'] else '☀️ Dzień'}\n\n"
    )
    
    # Dodaj informacje o wschodzie/zachodzie słońca
    if weather_info['sun_times']['sunrise'] and weather_info['sun_times']['sunset']:
        sunrise = datetime.fromisoformat(weather_info['sun_times']['sunrise'].replace('Z', '+00:00'))
        sunset = datetime.fromisoformat(weather_info['sun_times']['sunset'].replace('Z', '+00:00'))
        message += f"<b>🌅 Czas astronomiczny:</b>\n"
        message += f"• Wschód słońca: {sunrise.strftime('%H:%M')}\n"
        message += f"• Zachód słońca: {sunset.strftime('%H:%M')}\n\n"
    
    # Dodaj prognozę na najbliższe godziny
    if weather_info['forecast']['next_good_hours']:
        message += f"<b>📅 Najbliższe dobre godziny:</b>\n"
        for hour in weather_info['forecast']['next_good_hours']:
            message += f"• {hour['time']} (zachmurzenie: {hour['cloud_cover']}%)\n"
        
        if weather_info['forecast']['total_good_hours'] > 5:
            message += f"• ... i {weather_info['forecast']['total_good_hours'] - 5} więcej\n"
    else:
        message += "<b>📅 Prognoza:</b>\nBrak dobrych warunków w ciągu 24h\n"
    
    # Dodaj rekomendację
    if weather_info['status'] in ["DOSKONAŁE", "DOBRE"] and weather_info['is_night']:
        message += "\n✅ <b>Warunki odpowiednie do obserwacji!</b>"
    elif weather_info['status'] in ["DOSKONAŁE", "DOBRE"] and not weather_info['is_night']:
        message += "\n⚠️ <b>Dobre warunki, ale jest dzień. Poczekaj do zmierzchu.</b>"
    else:
        message += "\n❌ <b>Warunki nieodpowiednie do obserwacji.</b>"
    
    return message

# ====================== FUNKCJE POMOCNICZE ======================
def send_telegram_message(chat_id, text):
    """Wyślij wiadomość przez Telegram API"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return None

# ====================== FLASK APP ======================
app = Flask(__name__)

# Middleware do logowania requestów
@app.before_request
def log_request():
    if request.path not in ['/health', '/ping']:  # Nie loguj pingów
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")

# Strona główna - Dashboard
@app.route('/')
def home():
    online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
    ping_stats = ping_service.get_stats()
    
    # Pobierz aktualną pogodę dla miast
    current_weather = {}
    for city_key, city_info in OBSERVATION_CITIES.items():
        try:
            weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
            if weather_data:
                current = weather_data.get("current", {})
                current_weather[city_key] = {
                    "temp": current.get("temperature_2m", "N/A"),
                    "clouds": current.get("cloud_cover", "N/A"),
                    "humidity": current.get("relative_humidity_2m", "N/A"),
                    "wind": current.get("wind_speed_10m", "N/A"),
                    "is_day": current.get("is_day", 1)
                }
        except:
            current_weather[city_key] = None

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v4.0 - Telegram Bot z Pogodą</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
                color: #333;
                min-height: 100vh;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                margin-top: 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .status-badge {{
                display: inline-block;
                padding: 8px 16px;
                background: #4CAF50;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .weather-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .weather-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .city-name {{
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .weather-icon {{
                font-size: 50px;
                text-align: center;
                margin: 10px 0;
            }}
            .weather-details {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin-top: 15px;
            }}
            .weather-item {{
                background: rgba(255,255,255,0.2);
                padding: 10px;
                border-radius: 10px;
                text-align: center;
            }}
            .conditions-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .condition-card {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                border-left: 5px solid #667eea;
            }}
            .good {{
                border-left-color: #4CAF50;
                background: #e8f5e9;
            }}
            .bad {{
                border-left-color: #f44336;
                background: #ffebee;
            }}
            .agent-card {{
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                padding: 15px;
                margin: 15px 0;
                display: flex;
                align-items: center;
                transition: transform 0.2s;
            }}
            .agent-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .agent-icon {{
                font-size: 40px;
                margin-right: 20px;
            }}
            .agent-info {{
                flex: 1;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                border-left: 5px solid #667eea;
            }}
            .bot-link {{
                display: block;
                text-align: center;
                margin: 30px 0;
                padding: 15px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                transition: background 0.3s;
            }}
            .command {{
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 10px;
                margin: 10px 0;
                font-family: monospace;
            }}
            .timestamp {{
                color: #666;
                font-size: 12px;
                font-family: monospace;
            }}
        </style>
        <script>
            function refreshWeather() {{
                fetch('/weather?city=warszawa')
                    .then(response => response.json())
                    .then(data => {{
                        if(data.warszawa) {{
                            const w = data.warszawa;
                            document.getElementById('warszawa-temp').innerText = w.temp + '°C';
                            document.getElementById('warszawa-clouds').innerText = w.clouds + '%';
                            document.getElementById('warszawa-humidity').innerText = w.humidity + '%';
                            document.getElementById('warszawa-wind').innerText = w.wind + ' m/s';
                        }}
                    }});
                    
                fetch('/weather?city=koszalin')
                    .then(response => response.json())
                    .then(data => {{
                        if(data.koszalin) {{
                            const w = data.koszalin;
                            document.getElementById('koszalin-temp').innerText = w.temp + '°C';
                            document.getElementById('koszalin-clouds').innerText = w.clouds + '%';
                            document.getElementById('koszalin-humidity').innerText = w.humidity + '%';
                            document.getElementById('koszalin-wind').innerText = w.wind + ' m/s';
                        }}
                    }});
            }}
            
            document.addEventListener('DOMContentLoaded', function() {{
                refreshWeather();
                setInterval(refreshWeather, 60000); // Odśwież co minutę
            }});
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 42px; margin-bottom: 10px;">🤖 SENTRY ONE v4.0</h1>
                <h2 style="color: #666;">Telegram Bot z Obserwacją Astronomiczną</h2>
                <div class="status-badge">🟢 SYSTEM ONLINE</div>
                <p>Bot z bezpłatnym API Open-Meteo do obserwacji astronomicznych</p>
            </div>
            
            <a href="https://t.me/PcSentintel_Bot" class="bot-link" target="_blank">
                💬 Otwórz @PcSentintel_Bot w Telegramie
            </a>
            
            <h2>🌌 Warunki do obserwacji astronomicznych</h2>
            <div class="weather-grid">
                <div class="weather-card">
                    <div class="city-name">Warszawa</div>
                    <div class="weather-icon">🌃</div>
                    <div class="weather-details">
                        <div class="weather-item">
                            <div>Temperatura</div>
                            <div id="warszawa-temp">Ładowanie...</div>
                        </div>
                        <div class="weather-item">
                            <div>Zachmurzenie</div>
                            <div id="warszawa-clouds">Ładowanie...</div>
                        </div>
                        <div class="weather-item">
                            <div>Wilgotność</div>
                            <div id="warszawa-humidity">Ładowanie...</div>
                        </div>
                        <div class="weather-item">
                            <div>Wiatr</div>
                            <div id="warszawa-wind">Ładowanie...</div>
                        </div>
                    </div>
                </div>
                
                <div class="weather-card">
                    <div class="city-name">Koszalin</div>
                    <div class="weather-icon">🌌</div>
                    <div class="weather-details">
                        <div class="weather-item">
                            <div>Temperatura</div>
                            <div id="koszalin-temp">Ładowanie...</div>
                        </div>
                        <div class="weather-item">
                            <div>Zachmurzenie</div>
                            <div id="koszalin-clouds">Ładowanie...</div>
                        </div>
                        <div class="weather-item">
                            <div>Wilgotność</div>
                            <div id="koszalin-humidity">Ładowanie...</div>
                        </div>
                        <div class="weather-item">
                            <div>Wiatr</div>
                            <div id="koszalin-wind">Ładowanie...</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <h3>📋 Warunki dobrej widoczności:</h3>
            <div class="conditions-grid">
                <div class="condition-card good">
                    <div>Zachmurzenie ≤ {GOOD_CONDITIONS["max_cloud_cover"]}%</div>
                </div>
                <div class="condition-card good">
                    <div>Widoczność ≥ {GOOD_CONDITIONS["min_visibility"]} km</div>
                </div>
                <div class="condition-card good">
                    <div>Wilgotność ≤ {GOOD_CONDITIONS["max_humidity"]}%</div>
                </div>
                <div class="condition-card good">
                    <div>Wiatr ≤ {GOOD_CONDITIONS["max_wind_speed"]} m/s</div>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="total-agents">{len(AGENTS)}</div>
                    <div>Wszystkich agentów</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="online-agents">{online_count}</div>
                    <div>Online</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="offline-agents">{len(AGENTS) - online_count}</div>
                    <div>Offline</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="ping-count">{ping_stats['ping_count']}</div>
                    <div>Pingów wysłanych</div>
                </div>
            </div>
            
            <h2>🧭 Agenci systemu</h2>
    '''

    for agent in AGENTS.values():
        status_class = "online" if agent["status"] == "online" else "offline"
        status_text = "🟢 ONLINE" if agent["status"] == "online" else "🔴 OFFLINE"

        html += f'''
            <div class="agent-card">
                <div class="agent-icon">{agent['icon']}</div>
                <div class="agent-info">
                    <div class="agent-name">{agent['name']}</div>
                    <div>Typ: {agent['type']}</div>
                    <div class="agent-status {status_class}">
                        {status_text}
                    </div>
                </div>
            </div>
        '''

    html += f'''
            <h2>📋 Nowe komendy w Telegram</h2>
            <div class="command">/astro - Warunki dla wszystkich miast</div>
            <div class="command">/astro warszawa - Warunki tylko dla Warszawy</div>
            <div class="command">/astro koszalin - Warunki tylko dla Koszalina</div>
            <div class="command">/astro prognoza - Prognoza na najbliższe godziny</div>
            <div class="command">/astro warunki - Kryteria dobrej widoczności</div>
            
            <h2>📡 Endpointy API</h2>
            <div style="background: #f1f3f4; padding: 15px; border-radius: 12px; margin-top: 20px; font-family: monospace;">
                <div><strong>GET</strong> <a href="/weather">/weather</a> - Dane pogodowe JSON</div>
                <div><strong>GET</strong> <a href="/weather?city=warszawa">/weather?city=warszawa</a> - Pogoda dla Warszawy</div>
                <div><strong>GET</strong> <a href="/check_conditions">/check_conditions</a> - Sprawdź warunki</div>
                <div><strong>GET</strong> <a href="/health">/health</a> - Status zdrowia</div>
                <div><strong>GET</strong> <a href="/pingstats">/pingstats</a> - Statystyki pingów</div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; color: #666; padding-top: 20px; border-top: 1px solid #eee;">
                <p>🤖 SENTRY ONE v4.0 | Open-Meteo API | Obserwacja astronomiczna</p>
                <p>🌌 Sprawdza warunki w Warszawie i Koszalinie</p>
                <p class="timestamp">Ostatnia aktualizacja: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# Endpoint zdrowia dla Render
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "sentry-one-telegram-bot-v4",
        "platform": "render.com",
        "version": "4.0",
        "weather_api": "Open-Meteo (free)",
        "bot": "online",
        "webhook": WEBHOOK_URL,
        "timestamp": datetime.now().isoformat(),
        "ping_count": ping_service.ping_count
    })

# Endpoint danych pogodowych
@app.route('/weather')
def weather():
    """Zwróć dane pogodowe w formacie JSON"""
    city_name = request.args.get('city', '').lower()
    
    result = {}
    
    if city_name and city_name in OBSERVATION_CITIES:
        cities_to_check = [city_name]
    else:
        cities_to_check = OBSERVATION_CITIES.keys()
    
    for city_key in cities_to_check:
        city_info = OBSERVATION_CITIES[city_key]
        weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
        
        if weather_data and "current" in weather_data:
            current = weather_data["current"]
            result[city_key] = {
                "city": city_info["name"],
                "temp": round(current.get("temperature_2m", 0), 1),
                "clouds": current.get("cloud_cover", 0),
                "humidity": current.get("relative_humidity_2m", 0),
                "wind": current.get("wind_speed_10m", 0),
                "visibility": current.get("visibility", 0) / 1000,
                "is_day": current.get("is_day", 1) == 1,
                "timestamp": datetime.now().isoformat()
            }
        else:
            result[city_key] = {"error": "Nie udało się pobrać danych"}
    
    return jsonify(result)

# Sprawdź warunki dla obserwacji
@app.route('/check_conditions')
def check_conditions():
    """Sprawdź warunki do obserwacji astronomicznej"""
    city_name = request.args.get('city', '').lower()
    
    if city_name and city_name in OBSERVATION_CITIES:
        cities_to_check = [city_name]
    else:
        cities_to_check = OBSERVATION_CITIES.keys()
    
    result = {}
    
    for city_key in cities_to_check:
        city_info = OBSERVATION_CITIES[city_key]
        weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
        
        if weather_data:
            conditions = check_astronomical_conditions(weather_data, city_info["name"])
            result[city_key] = conditions
        else:
            result[city_key] = {"error": "Nie udało się pobrać danych pogodowych"}
    
    return jsonify(result)

# Ręczne pingowanie
@app.route('/ping')
def manual_ping():
    """Ręczne wywołanie pingowania"""
    try:
        ping_service.ping_self()
        return jsonify({
            "success": True,
            "message": "Ping wykonany ręcznie",
            "ping_count": ping_service.ping_count,
            "last_ping": ping_service.last_ping,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Statystyki pingowania
@app.route('/pingstats')
def ping_stats():
    """Zwróć statystyki pingowania"""
    return jsonify(ping_service.get_stats())

# JSON dashboard
@app.route('/dashboard')
def dashboard():
    online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
    return jsonify({
        "system": {
            "name": "SENTRY ONE v4.0",
            "version": "4.0",
            "platform": "Render.com",
            "status": "online",
            "weather_api": "Open-Meteo",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "observation_cities": OBSERVATION_CITIES,
        "good_conditions": GOOD_CONDITIONS,
        "ping_system": ping_service.get_stats(),
        "agents": AGENTS,
        "statistics": {
            "total_agents": len(AGENTS),
            "online_agents": online_count,
            "offline_agents": len(AGENTS) - online_count
        }
    })

# Ustaw webhook
@app.route('/setwebhook')
def set_webhook():
    """Ustaw webhook dla Telegrama"""
    try:
        delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        requests.get(delete_url)

        set_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
        response = requests.get(set_url)

        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "success": True,
                "message": "Webhook ustawiony pomyślnie",
                "result": result
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Błąd HTTP: {response.status_code}"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Endpoint webhook dla Telegrama
@app.route('/webhook', methods=['POST'])
def webhook():
    """Główny endpoint dla webhook Telegram"""
    try:
        data = request.get_json()
        logger.info(f"📥 Otrzymano webhook od Telegram")

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            # Obsługa komend
            if text.startswith("/start"):
                response_text = (
                    "🤖 <b>SENTRY ONE v4.0 - Obserwacja astronomiczna</b>\n\n"
                    "Witaj! Oprócz standardowych funkcji, mogę sprawdzać warunki "
                    "do obserwacji astronomicznych w Warszawie i Koszalinie!\n\n"
                    "<b>Nowe komendy pogodowe:</b>\n"
                    "/astro - Warunki dla wszystkich miast\n"
                    "/astro warszawa - Warunki tylko dla Warszawy\n"
                    "/astro koszalin - Warunki tylko dla Koszalina\n"
                    "/astro prognoza - Prognoza na najbliższe godziny\n"
                    "/astro warunki - Kryteria dobrej widoczności\n\n"
                    "<b>Standardowe komendy:</b>\n"
                    "/status - Status systemu\n"
                    "/agents - Lista agentów\n"
                    "/ping - Statystyki pingowania\n"
                    "/echo [tekst] - Powtórz tekst\n\n"
                    "<i>🌌 API: Open-Meteo (bezpłatne)</i>"
                )
                send_telegram_message(chat_id, response_text)

            elif text.startswith("/astro"):
                args = text[6:].strip().lower()
                
                if args == "warunki":
                    response_text = (
                        "🌌 <b>KRYTERIA DOBREJ WIDOCZNOŚCI:</b>\n\n"
                        f"• Zachmurzenie ≤ {GOOD_CONDITIONS['max_cloud_cover']}%\n"
                        f"• Widoczność ≥ {GOOD_CONDITIONS['min_visibility']} km\n"
                        f"• Wilgotność ≤ {GOOD_CONDITIONS['max_humidity']}%\n"
                        f"• Wiatr ≤ {GOOD_CONDITIONS['max_wind_speed']} m/s\n"
                        f"• Temperatura: {GOOD_CONDITIONS['min_temperature']}°C do {GOOD_CONDITIONS['max_temperature']}°C\n\n"
                        "<i>Warunki są oceniane na podstawie powyższych kryteriów.</i>"
                    )
                    send_telegram_message(chat_id, response_text)
                    
                elif args == "prognoza":
                    # Pobierz prognozę dla obu miast
                    for city_key, city_info in OBSERVATION_CITIES.items():
                        weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
                        if weather_data and "hourly" in weather_data:
                            hourly = weather_data["hourly"]
                            clouds = hourly.get("cloud_cover", [])[:12]  # 12 godzin
                            
                            good_hours = []
                            for i, cloud in enumerate(clouds):
                                if cloud <= GOOD_CONDITIONS["max_cloud_cover"]:
                                    hour_time = datetime.now() + timedelta(hours=i)
                                    good_hours.append(f"{hour_time.strftime('%H:%M')} ({cloud}%)")
                            
                            if good_hours:
                                response_text = (
                                    f"📅 <b>Prognoza dla {city_info['name']}:</b>\n"
                                    f"Dobre godziny (zachmurzenie ≤ {GOOD_CONDITIONS['max_cloud_cover']}%):\n"
                                )
                                for hour in good_hours[:6]:  # Pierwsze 6 godzin
                                    response_text += f"• {hour}\n"
                                if len(good_hours) > 6:
                                    response_text += f"• ... i {len(good_hours)-6} więcej\n"
                            else:
                                response_text = f"📅 <b>{city_info['name']}:</b>\nBrak dobrych warunków w ciągu 12h\n"
                            
                            send_telegram_message(chat_id, response_text)
                    
                elif args in ["warszawa", "koszalin"]:
                    # Sprawdź warunki dla konkretnego miasta
                    city_info = OBSERVATION_CITIES[args]
                    weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
                    
                    if weather_data:
                        weather_info = check_astronomical_conditions(weather_data, city_info["name"])
                        if weather_info:
                            message_text = format_weather_message(weather_info)
                            send_telegram_message(chat_id, message_text)
                        else:
                            send_telegram_message(chat_id, "❌ Nie udało się ocenić warunków")
                    else:
                        send_telegram_message(chat_id, "❌ Nie udało się pobrać danych pogodowych")
                        
                else:
                    # Sprawdź warunki dla wszystkich miast
                    for city_key, city_info in OBSERVATION_CITIES.items():
                        weather_data = get_weather_forecast(city_info["lat"], city_info["lon"])
                        
                        if weather_data:
                            weather_info = check_astronomical_conditions(weather_data, city_info["name"])
                            if weather_info:
                                # Skrócona wersja dla podsumowania
                                response_text = (
                                    f"{weather_info['emoji']} <b>{city_info['name']}</b>\n"
                                    f"Status: {weather_info['status']} ({weather_info['score']}%)\n"
                                    f"Zachmurzenie: {weather_info['conditions']['cloud_cover']}%\n"
                                    f"Widoczność: {weather_info['conditions']['visibility_km']} km\n"
                                    f"Wilgotność: {weather_info['conditions']['humidity']}%\n"
                                    f"{'🌙 Noc' if weather_info['is_night'] else '☀️ Dzień'}\n"
                                )
                                
                                if weather_info['forecast']['total_good_hours'] > 0:
                                    response_text += f"Dobre godziny: {weather_info['forecast']['total_good_hours']}\n"
                                
                                send_telegram_message(chat_id, response_text)
                        time.sleep(0.5)  # Małe opóźnienie między miastami
                    
                    send_telegram_message(chat_id, "ℹ️ Użyj /astro warunki aby zobaczyć kryteria")

            elif text.startswith("/status"):
                online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
                ping_stats = ping_service.get_stats()

                response_text = (
                    f"📊 <b>STATUS SYSTEMU v4.0</b>\n\n"
                    f"• Platforma: Render.com\n"
                    f"• Bot: ✅ Działa\n"
                    f"• Tryb: Webhook\n"
                    f"• Agenty: {online_count}/{len(AGENTS)} online\n"
                    f"• API Pogodowe: Open-Meteo\n"
                    f"• Pingowanie: {'🟢 Aktywne' if ping_stats['is_running'] else '🔴 Nieaktywne'}\n"
                    f"• Pingów wysłano: {ping_stats['ping_count']}\n"
                    f"• Obserwowane miasta: {len(OBSERVATION_CITIES)}\n"
                    f"• URL: {RENDER_URL}\n\n"
                    f"<i>System obserwacji astronomicznej aktywny!</i>"
                )
                send_telegram_message(chat_id, response_text)

            elif text.startswith("/agents"):
                response_text = "👥 <b>AGENTY SYSTEMU</b>\n\n"
                for agent in AGENTS.values():
                    status_icon = "🟢" if agent["status"] == "online" else "🔴"
                    response_text += f"{status_icon} <b>{agent['name']}</b>\n"
                    response_text += f"  • Typ: {agent['type']}\n"
                    response_text += f"  • Status: {agent['status']}\n\n"
                send_telegram_message(chat_id, response_text)

            elif text.startswith("/ping"):
                ping_stats = ping_service.get_stats()
                response_text = (
                    "📡 <b>STATYSTYKI PINGOWANIA</b>\n\n"
                    f"• Status: {'🟢 AKTYWNE' if ping_stats['is_running'] else '🔴 NIEAKTYWNE'}\n"
                    f"• Pingów wysłano: {ping_stats['ping_count']}\n"
                    f"• Ostatni ping: {ping_stats['last_ping'] or 'Nigdy'}\n"
                    f"• Interwał: {ping_stats['interval_seconds']/60} minut\n\n"
                    f"<i>Pingowanie utrzymuje bot aktywnym na darmowym Render</i>"
                )
                send_telegram_message(chat_id, response_text)

            elif text.startswith("/echo"):
                echo_text = text[5:].strip()
                if echo_text:
                    response_text = f"📣 <b>ECHO:</b> {echo_text}"
                else:
                    response_text = "📣 <b>ECHO:</b> Brak tekstu do powtórzenia"
                send_telegram_message(chat_id, response_text)

            else:
                response_text = (
                    "❓ <b>Nieznana komenda</b>\n\n"
                    "<b>Komendy pogodowe:</b>\n"
                    "/astro - Warunki obserwacyjne\n"
                    "/astro warszawa - Warunki dla Warszawy\n"
                    "/astro koszalin - Warunki dla Koszalina\n\n"
                    "<b>Standardowe komendy:</b>\n"
                    "/start - Informacje\n"
                    "/status - Status systemu\n"
                    "/agents - Lista agentów\n"
                    "/ping - Statystyki pingowania\n"
                    "/echo [tekst] - Powtórz tekst"
                )
                send_telegram_message(chat_id, response_text)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Błąd przetwarzania webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print(f"🚀 Uruchamianie SENTRY ONE v4.0 na Render...")
    print(f"🌐 URL: {RENDER_URL}")
    print(f"🔗 Webhook: {WEBHOOK_URL}")
    print(f"🌤️  API Pogodowe: Open-Meteo (bezpłatne)")
    print(f"🌌 Obserwowane miasta: {', '.join([c['name'] for c in OBSERVATION_CITIES.values()])}")

    # Uruchom system pingowania
    ping_service.start()

    # Uruchom serwer
    port = PORT
    print(f"🌍 Serwer startuje na porcie {port}")

    # Uruchom Flask
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )