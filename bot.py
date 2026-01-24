#!/usr/bin/env python3
"""
🌌 COSMOS SENTRY v2.0 PRO - PROAKTYWNY SYSTEM POWIADOMIEŃ OBSERWACYJNYCH
Bot sam informuje o dobrych warunkach do obserwacji satelit i nieba
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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import random
from typing import Dict, List, Optional, Set

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"

# API klucze
OPENWEATHER_API_KEY = "38e01cfb763fc738e9eddee84cfc4384"
N2YO_API_KEY = "UNWEQ8-N47JL7-WFJZYX-5N65"
NASA_API_KEY = "P0locPuOZBvnkHCdIKjkxzKsfnM7tc7pbiMcsBDE"

# API endpoints
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5"
N2YO_URL = "https://api.n2yo.com/rest/v1/satellite"

# Twoja lokalizacja (możesz zmienić)
YOUR_LOCATION = {
    "name": "Twoja Lokalizacja",
    "lat": 52.2297,  # Warszawa - zmień na swoje współrzędne
    "lon": 21.0122,
    "emoji": "📍",
    "timezone": "Europe/Warsaw",
    "chat_id": None  # Będzie ustawione automatycznie po pierwszej komendzie /start
}

# Warunki dobrej widoczności - PROGI DLA POWIADOMIEŃ
NOTIFICATION_THRESHOLDS = {
    "excellent": {
        "min_score": 80,
        "emoji": "✨",
        "name": "DOSKONAŁE",
        "notify": True,
        "conditions": {
            "max_clouds": 20,      # Maksymalne zachmurzenie 20%
            "min_visibility": 15,  # Minimalna widoczność 15 km
            "max_humidity": 70,    # Maksymalna wilgotność 70%
            "max_wind": 5,         # Maksymalny wiatr 5 m/s
            "min_temp": -10,       # Minimalna temperatura -10°C
            "max_temp": 30         # Maksymalna temperatura 30°C
        }
    },
    "good": {
        "min_score": 60,
        "emoji": "⭐",
        "name": "DOBRE",
        "notify": True,
        "conditions": {
            "max_clouds": 40,
            "min_visibility": 10,
            "max_humidity": 80,
            "max_wind": 8,
            "min_temp": -15,
            "max_temp": 35
        }
    },
    "moderate": {
        "min_score": 40,
        "emoji": "⛅",
        "name": "ŚREDNIE",
        "notify": False,  # Nie powiadamiaj dla średnich warunków
        "conditions": {
            "max_clouds": 60,
            "min_visibility": 5,
            "max_humidity": 90,
            "max_wind": 12
        }
    }
}

# Satelity do śledzenia
SATELLITES = {
    "iss": {
        "name": "ISS",
        "id": 25544,
        "emoji": "🛰️",
        "min_elevation": 30,  # Minimalna wysokość dla powiadomienia (stopnie)
        "min_brightness": -1, # Minimalna jasność (im mniejsza liczba, tym jaśniej)
        "notify": True
    },
    "hst": {
        "name": "Hubble",
        "id": 20580,
        "emoji": "🔭",
        "min_elevation": 40,
        "min_brightness": 2,
        "notify": True
    },
    "tiangong": {
        "name": "Tiangong",
        "id": 48274,
        "emoji": "🇨🇳",
        "min_elevation": 30,
        "min_brightness": 0,
        "notify": False  # Domyślnie wyłączone
    }
}

# ====================== SYSTEM POWIADOMIEŃ ======================
class NotificationSystem:
    """System zarządzania powiadomieniami"""
    
    def __init__(self):
        self.notifications_enabled = True
        self.last_notification = {}
        self.notification_cooldown = 3600  # 1 godzina między powiadomieniami tego samego typu
        self.subscribers = set()  # chat_id użytkowników
        self.load_config()
        
    def load_config(self):
        """Załaduj konfigurację z pliku"""
        try:
            if os.path.exists("notifications_config.json"):
                with open("notifications_config.json", "r") as f:
                    data = json.load(f)
                    self.subscribers = set(data.get("subscribers", []))
                    self.notifications_enabled = data.get("enabled", True)
                    self.last_notification = data.get("last_notification", {})
        except Exception as e:
            logging.error(f"❌ Błąd ładowania konfiguracji: {e}")
    
    def save_config(self):
        """Zapisz konfigurację do pliku"""
        try:
            data = {
                "subscribers": list(self.subscribers),
                "enabled": self.notifications_enabled,
                "last_notification": self.last_notification,
                "last_update": datetime.now().isoformat()
            }
            with open("notifications_config.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"❌ Błąd zapisywania konfiguracji: {e}")
    
    def can_send_notification(self, notification_type: str) -> bool:
        """Sprawdź czy można wysłać powiadomienie danego typu"""
        if not self.notifications_enabled:
            return False
            
        if notification_type not in self.last_notification:
            return True
            
        last_time = datetime.fromisoformat(self.last_notification[notification_type])
        elapsed = (datetime.now() - last_time).total_seconds()
        
        return elapsed > self.notification_cooldown
    
    def mark_notification_sent(self, notification_type: str):
        """Oznacz powiadomienie jako wysłane"""
        self.last_notification[notification_type] = datetime.now().isoformat()
        self.save_config()
    
    def add_subscriber(self, chat_id: int):
        """Dodaj użytkownika do listy powiadomień"""
        self.subscribers.add(chat_id)
        self.save_config()
        return True
    
    def remove_subscriber(self, chat_id: int):
        """Usuń użytkownika z listy powiadomień"""
        if chat_id in self.subscribers:
            self.subscribers.remove(chat_id)
            self.save_config()
        return True
    
    def is_subscribed(self, chat_id: int) -> bool:
        """Sprawdź czy użytkownik jest zapisany na powiadomienia"""
        return chat_id in self.subscribers

# ====================== FUNKCJE POGODOWE ======================
def get_openweather_data(lat: float, lon: float) -> Optional[Dict]:
    """Pobierz aktualną pogodę z OpenWeather"""
    try:
        url = f"{OPENWEATHER_URL}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "pl"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            logging.error(f"OpenWeather error: {data}")
            return None
        
        return {
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "wind_deg": data["wind"].get("deg", 0),
            "clouds": data["clouds"]["all"],
            "visibility": data.get("visibility", 10000) / 1000,
            "description": data["weather"][0]["description"],
            "weather_main": data["weather"][0]["main"],
            "icon": data["weather"][0]["icon"],
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]),
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logging.error(f"❌ Błąd OpenWeather: {e}")
        return None

def get_satellite_passes(satellite_id: int, lat: float, lon: float) -> Optional[List]:
    """Pobierz nadchodzące przeloty satelity"""
    try:
        url = f"{N2YO_URL}/visualpasses/{satellite_id}/{lat}/{lon}/0/5/300/"
        params = {"apiKey": N2YO_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            return None
        
        if "passes" in data:
            passes = []
            now = datetime.now()
            
            for pass_data in data["passes"]:
                start_time = datetime.fromtimestamp(pass_data["startUTC"])
                end_time = datetime.fromtimestamp(pass_data["endUTC"])
                
                # Tylko przyszłe przeloty (w ciągu najbliższych 24h)
                if start_time > now and (start_time - now).total_seconds() < 86400:
                    passes.append({
                        "start": start_time,
                        "end": end_time,
                        "duration": pass_data["duration"],
                        "max_elevation": pass_data["maxEl"],
                        "brightness": pass_data.get("mag", 0),
                        "start_azimuth": pass_data.get("startAz", 0),
                        "end_azimuth": pass_data.get("endAz", 0)
                    })
            
            return sorted(passes, key=lambda x: x["start"])[:3]  # 3 najbliższe przeloty
        
        return None
        
    except Exception as e:
        logging.error(f"❌ Błąd pobierania przelotów satelity: {e}")
        return None

def calculate_observation_score(weather_data: Dict) -> Dict:
    """Oblicz wynik warunków obserwacyjnych"""
    if not weather_data:
        return {"score": 0, "category": "unknown", "reasons": ["Brak danych"]}
    
    score = 100
    reasons = []
    
    # 1. Zachmurzenie (najważniejsze!)
    clouds = weather_data["clouds"]
    cloud_deduction = min(clouds * 0.8, 60)  # Do 60 punktów
    score -= cloud_deduction
    if clouds > 30:
        reasons.append(f"☁️ Zachmurzenie: {clouds}%")
    
    # 2. Widoczność
    visibility = weather_data["visibility"]
    if visibility < 10:
        score -= 20
        reasons.append(f"🌫️ Słaba widoczność: {visibility:.1f}km")
    elif visibility > 20:
        score += 10
        reasons.append(f"👁️ Doskonała widoczność: {visibility:.1f}km")
    
    # 3. Wilgotność
    humidity = weather_data["humidity"]
    if humidity > 80:
        score -= 15
        reasons.append(f"💧 Wysoka wilgotność: {humidity}%")
    
    # 4. Wiatr
    wind = weather_data["wind_speed"]
    if wind > 8:
        score -= 20
        reasons.append(f"💨 Silny wiatr: {wind} m/s")
    elif wind < 3:
        score += 5
        reasons.append(f"🍃 Słaby wiatr: {wind} m/s")
    
    # 5. Temperatura
    temp = weather_data["temp"]
    if temp < -5:
        score -= 10
        reasons.append(f"🥶 Zimno: {temp:.1f}°C")
    elif temp > 25:
        score -= 5
        reasons.append(f"🔥 Gorąco: {temp:.1f}°C")
    
    # 6. Czy jest noc? (najważniejsze dla obserwacji)
    now = datetime.now()
    is_night = now < weather_data["sunrise"] or now > weather_data["sunset"]
    
    if not is_night:
        score -= 40  # W dzień warunki zawsze gorsze
        reasons.append("☀️ Jest dzień - poczekaj do zmierzchu")
    else:
        score += 20
        reasons.append("🌙 Jest noc - idealny czas!")
    
    # 7. Opady
    weather_main = weather_data["weather_main"].lower()
    bad_weather = ["rain", "snow", "thunderstorm", "drizzle"]
    if any(bad in weather_main for bad in bad_weather):
        score -= 50
        reasons.append(f"🌧️ Opady: {weather_data['description']}")
    
    score = max(0, min(100, score))
    
    # Określ kategorię
    category = "poor"
    for cat_name, threshold in NOTIFICATION_THRESHOLDS.items():
        if score >= threshold["min_score"]:
            category = cat_name
            break
    
    return {
        "score": round(score),
        "category": category,
        "reasons": reasons,
        "is_night": is_night
    }

# ====================== FUNKCJE POWIADOMIEŃ ======================
def check_and_notify_good_conditions():
    """Sprawdź warunki i wyślij powiadomienie jeśli są dobre"""
    notification_system = app.config['NOTIFICATION_SYSTEM']
    
    if not notification_system.subscribers:
        logging.info("⏭️ Brak subskrybentów powiadomień")
        return
    
    # Pobierz dane pogodowe
    weather_data = get_openweather_data(YOUR_LOCATION["lat"], YOUR_LOCATION["lon"])
    if not weather_data:
        return
    
    # Oblicz wynik obserwacyjny
    observation = calculate_observation_score(weather_data)
    
    # Sprawdź czy warunki są wystarczająco dobre
    if observation["category"] in ["excellent", "good"]:
        # Sprawdź czy można wysłać powiadomienie
        if notification_system.can_send_notification("good_conditions"):
            
            for chat_id in notification_system.subscribers:
                message = create_conditions_notification(weather_data, observation)
                send_telegram_message(chat_id, message)
            
            notification_system.mark_notification_sent("good_conditions")
            logging.info(f"✅ Wysłano powiadomienie o dobrych warunkach do {len(notification_system.subscribers)} osób")

def check_and_notify_satellite_passes():
    """Sprawdź nadchodzące przeloty satelit i wyślij powiadomienia"""
    notification_system = app.config['NOTIFICATION_SYSTEM']
    
    if not notification_system.subscribers:
        return
    
    now = datetime.now()
    
    for sat_key, satellite in SATELLITES.items():
        if not satellite.get("notify", False):
            continue
        
        # Sprawdź przeloty
        passes = get_satellite_passes(satellite["id"], YOUR_LOCATION["lat"], YOUR_LOCATION["lon"])
        if not passes:
            continue
        
        # Znajdź najbliższy dobry przelot
        for pass_data in passes:
            # Sprawdź czy przelot jest wystarczająco wysoki i jasny
            if (pass_data["max_elevation"] >= satellite["min_elevation"] and
                pass_data["brightness"] <= satellite["min_brightness"]):
                
                # Sprawdź czy przelot jest w ciągu najbliższych 2 godzin
                time_to_pass = (pass_data["start"] - now).total_seconds()
                if 1800 <= time_to_pass <= 7200:  # 30 min do 2 godzin
                    
                    # Sprawdź czy można wysłać powiadomienie dla tego satelity
                    notification_type = f"satellite_{sat_key}_{pass_data['start'].strftime('%Y%m%d_%H')}"
                    
                    if notification_system.can_send_notification(notification_type):
                        for chat_id in notification_system.subscribers:
                            message = create_satellite_notification(satellite, pass_data)
                            send_telegram_message(chat_id, message)
                        
                        notification_system.mark_notification_sent(notification_type)
                        logging.info(f"🛰️ Wysłano powiadomienie o przelocie {satellite['name']}")
                        break  # Tylko jeden przelot na satelitę na raz

def create_conditions_notification(weather_data: Dict, observation: Dict) -> str:
    """Utwórz wiadomość powiadomienia o warunkach"""
    border = "═" * 40
    
    message = f"{border}\n"
    message += f"✨ <b>POWIADOMIENIE O DOBRYCH WARUNKACH!</b>\n"
    message += f"{border}\n\n"
    
    message += f"🌌 <b>Warunki obserwacyjne: {observation['category'].upper()}</b>\n"
    message += f"📊 <b>Wynik:</b> {observation['score']}/100\n\n"
    
    message += f"📍 <b>Lokalizacja:</b> {YOUR_LOCATION['name']}\n"
    message += f"⏰ <b>Czas:</b> {datetime.now().strftime('%H:%M')}\n\n"
    
    message += f"🌤️ <b>Pogoda:</b>\n"
    message += f"• Temperatura: {weather_data['temp']:.1f}°C\n"
    message += f"• Zachmurzenie: {weather_data['clouds']}%\n"
    message += f"• Widoczność: {weather_data['visibility']:.1f} km\n"
    message += f"• Wiatr: {weather_data['wind_speed']} m/s\n"
    message += f"• Wilgotność: {weather_data['humidity']}%\n\n"
    
    message += f"🎯 <b>Dlaczego warto obserwować TERAZ:</b>\n"
    for reason in observation.get("reasons", [])[:5]:  # Maksymalnie 5 powodów
        message += f"• {reason}\n"
    
    message += f"\n{border}\n"
    message += f"<i>🌌 COSMOS SENTRY - System automatycznych powiadomień</i>\n"
    message += f"<i>🔔 Aby wyłączyć: /notify_off</i>"
    
    return message

def create_satellite_notification(satellite: Dict, pass_data: Dict) -> str:
    """Utwórz wiadomość powiadomienia o przelocie satelity"""
    border = "═" * 40
    time_now = datetime.now()
    time_to_start = pass_data["start"] - time_now
    minutes_to_start = int(time_to_start.total_seconds() / 60)
    
    message = f"{border}\n"
    message += f"🛰️ <b>POWIADOMIENIE O PRZELOCIE SATELITY!</b>\n"
    message += f"{border}\n\n"
    
    message += f"{satellite['emoji']} <b>{satellite['name']}</b>\n\n"
    
    message += f"⏰ <b>Zaczyna się za:</b> {minutes_to_start} minut\n"
    message += f"🕐 <b>Start:</b> {pass_data['start'].strftime('%H:%M')}\n"
    message += f"🕐 <b>Koniec:</b> {pass_data['end'].strftime('%H:%M')}\n"
    message += f"⏱️ <b>Czas trwania:</b> {pass_data['duration']} sekund\n\n"
    
    message += f"📐 <b>Parametry przelotu:</b>\n"
    message += f"• Maksymalna wysokość: {pass_data['max_elevation']:.1f}°\n"
    message += f"• Jasność: {pass_data['brightness']:.1f} mag\n"
    message += f"• Kierunek startu: {pass_data.get('start_azimuth', 0):.0f}°\n"
    message += f"• Kierunek końca: {pass_data.get('end_azimuth', 0):.0f}°\n\n"
    
    message += f"📍 <b>Lokalizacja:</b> {YOUR_LOCATION['name']}\n\n"
    
    message += f"💡 <b>Jak obserwować:</b>\n"
    message += f"1. Wyjdź na otwartą przestrzeń\n"
    message += f"2. Spójrz w kierunku {pass_data.get('start_azimuth', 0):.0f}°\n"
    message += f"3. Szukaj poruszającej się 'gwiazdy'\n"
    message += f"4. Satelita będzie najwyżej o {pass_data['start'].strftime('%H:%M')}\n"
    
    message += f"\n{border}\n"
    message += f"<i>🛰️ COSMOS SENTRY - Śledzenie satelit</i>\n"
    message += f"<i>🔔 Aby wyłączyć: /notify_sat_off</i>"
    
    return message

# ====================== FUNKCJE POMOCNICZE ======================
def send_telegram_message(chat_id: int, text: str):
    """Wyślij wiadomość przez Telegram API"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logging.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return None

def get_weather_icon(icon_code: str) -> str:
    """Mapuj kod ikony na emoji"""
    icon_map = {
        "01d": "☀️", "01n": "🌙",
        "02d": "⛅", "02n": "⛅",
        "03d": "☁️", "03n": "☁️",
        "04d": "☁️", "04n": "☁️",
        "09d": "🌧️", "09n": "🌧️",
        "10d": "🌦️", "10n": "🌦️",
        "11d": "⛈️", "11n": "⛈️",
        "13d": "❄️", "13n": "❄️",
        "50d": "🌫️", "50n": "🌫️"
    }
    return icon_map.get(icon_code, "🌤️")

# ====================== FLASK APP ======================
app = Flask(__name__)
notification_system = NotificationSystem()
app.config['NOTIFICATION_SYSTEM'] = notification_system

# Scheduler do okresowych zadań
scheduler = BackgroundScheduler()

@app.route('/')
def home():
    """Strona główna"""
    now = datetime.now()
    subscribers_count = len(notification_system.subscribers)
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🌌 COSMOS SENTRY PRO - System Powiadomień</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #0c0e2e 0%, #1a1b3e 50%, #2a2b5e 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-top: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .status-card {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                margin: 15px 0;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .badge {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                margin: 5px;
            }}
            .badge-on {{
                background: linear-gradient(45deg, #00b09b, #96c93d);
            }}
            .badge-off {{
                background: linear-gradient(45deg, #ff416c, #ff4b2b);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌌 COSMOS SENTRY PRO v2.0</h1>
            <h2>🛰️ Proaktywny System Powiadomień Obserwacyjnych</h2>
            
            <div class="status-card">
                <h3>📊 Status Systemu</h3>
                <p><strong>Czas:</strong> {now.strftime('%d.%m.%Y %H:%M:%S')}</p>
                <p><strong>Lokalizacja:</strong> {YOUR_LOCATION['name']}</p>
                <p><strong>Subskrybenci:</strong> {subscribers_count}</p>
                <p><strong>Powiadomienia:</strong> 
                    <span class="badge {'badge-on' if notification_system.notifications_enabled else 'badge-off'}">
                        {'WŁĄCZONE' if notification_system.notifications_enabled else 'WYŁĄCZONE'}
                    </span>
                </p>
            </div>
            
            <div class="status-card">
                <h3>🔔 Jak działa system?</h3>
                <p>1. Bot <strong>sam sprawdza</strong> warunki pogodowe co 30 minut</p>
                <p>2. Gdy warunki są dobre, <strong>wysyła automatyczne powiadomienie</strong></p>
                <p>3. Monitoruje <strong>przeloty satelit</strong> (ISS, Hubble)</p>
                <p>4. Informuje <strong>2 godziny przed</strong> dobrym przelotem</p>
            </div>
            
            <div class="status-card">
                <h3>🎯 Kryteria powiadomień</h3>
                <p><strong>Warunki pogodowe:</strong></p>
                <p>• Zachmurzenie: &lt; 40%</p>
                <p>• Widoczność: &gt; 10 km</p>
                <p>• Wiatr: &lt; 8 m/s</p>
                <p>• Noc (po zachodzie słońca)</p>
                <p><strong>Przeloty satelit:</strong></p>
                <p>• Wysokość: &gt; 30° nad horyzontem</p>
                <p>• Powiadomienie: 2 godziny przed</p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <p>🌌 Bot informuje Cię kiedy warto wyjść na obserwacje!</p>
                <p>🛰️ Nie przegap dobrych warunków i przelotów ISS</p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

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
            
            notification_system = app.config['NOTIFICATION_SYSTEM']
            
            # Komenda /start - zapisz użytkownika
            if text == "/start":
                # Zapisz lokalizację użytkownika
                YOUR_LOCATION["chat_id"] = chat_id
                
                # Dodaj użytkownika do powiadomień
                notification_system.add_subscriber(chat_id)
                
                welcome_msg = (
                    "═" * 40 + "\n"
                    "🌌 <b>COSMOS SENTRY PRO v2.0</b>\n"
                    "═" * 40 + "\n\n"
                    
                    "🎯 <b>PROAKTYWNY SYSTEM POWIADOMIEŃ</b>\n\n"
                    
                    "✅ <b>ZAREJESTROWANO!</b> Teraz otrzymasz powiadomienia:\n"
                    "• 🌤️ Gdy warunki do obserwacji będą DOBRE\n"
                    "• 🛰️ 2 godziny przed przelotem ISS/Hubble\n"
                    "• ✨ O innych astronomicznych okazjach\n\n"
                    
                    "📊 <b>Twoja konfiguracja:</b>\n"
                    f"• Lokalizacja: {YOUR_LOCATION['name']}\n"
                    f"• Szerokość: {YOUR_LOCATION['lat']:.4f}°\n"
                    f"• Długość: {YOUR_LOCATION['lon']:.4f}°\n\n"
                    
                    "⚙️ <b>Dostępne komendy:</b>\n"
                    "<code>/notify_status</code> - Status powiadomień\n"
                    "<code>/notify_off</code> - Wyłącz powiadomienia\n"
                    "<code>/notify_on</code> - Włącz powiadomienia\n"
                    "<code>/check_now</code> - Sprawdź teraz\n"
                    "<code>/next_passes</code> - Nadchodzące przeloty\n"
                    "<code>/help</code> - Wszystkie komendy\n\n"
                    
                    "═" * 40 + "\n"
                    "<i>🌌 Bot będzie Cię informował o dobrych warunkach!</i>"
                )
                send_telegram_message(chat_id, welcome_msg)
            
            # Sprawdź teraz
            elif text == "/check_now":
                weather_data = get_openweather_data(YOUR_LOCATION["lat"], YOUR_LOCATION["lon"])
                if weather_data:
                    observation = calculate_observation_score(weather_data)
                    
                    if observation["category"] in ["excellent", "good"]:
                        msg = "✅ <b>TERAZ SĄ DOBRE WARUNKI!</b>\n"
                        msg += f"Wynik: {observation['score']}/100\n"
                        msg += f"Kategoria: {observation['category'].upper()}\n\n"
                        msg += "🌤️ Wychodź na obserwacje!"
                    else:
                        msg = "⚠️ <b>Warunki nie są optymalne</b>\n"
                        msg += f"Wynik: {observation['score']}/100\n"
                        msg += f"Kategoria: {observation['category'].upper()}\n\n"
                        msg += "📋 Powody:\n"
                        for reason in observation.get("reasons", [])[:3]:
                            msg += f"• {reason}\n"
                    
                    send_telegram_message(chat_id, msg)
                else:
                    send_telegram_message(chat_id, "❌ Nie udało się sprawdzić warunków")
            
            # Nadchodzące przeloty
            elif text == "/next_passes":
                msg = "🛰️ <b>NADCHODZĄCE PRZELOTY:</b>\n\n"
                
                for sat_key, satellite in SATELLITES.items():
                    if satellite.get("notify", False):
                        passes = get_satellite_passes(satellite["id"], YOUR_LOCATION["lat"], YOUR_LOCATION["lon"])
                        if passes:
                            next_pass = passes[0]
                            time_to = (next_pass["start"] - datetime.now()).total_seconds() / 60
                            msg += f"{satellite['emoji']} <b>{satellite['name']}</b>\n"
                            msg += f"• Za: {int(time_to)} minut\n"
                            msg += f"• Godzina: {next_pass['start'].strftime('%H:%M')}\n"
                            msg += f"• Wysokość: {next_pass['max_elevation']:.1f}°\n\n"
                
                if msg == "🛰️ <b>NADCHODZĄCE PRZELOTY:</b>\n\n":
                    msg += "❌ Brak nadchodzących przelotów w ciągu najbliższych 24h\n"
                
                msg += "🔔 Otrzymasz powiadomienie 2h przed dobrym przelotem!"
                send_telegram_message(chat_id, msg)
            
            # Status powiadomień
            elif text == "/notify_status":
                is_subscribed = notification_system.is_subscribed(chat_id)
                status = "✅ WŁĄCZONE" if is_subscribed else "❌ WYŁĄCZONE"
                
                msg = (
                    "🔔 <b>STATUS POWIADOMIEŃ</b>\n\n"
                    f"• Subskrypcja: {status}\n"
                    f"• Lokalizacja: {YOUR_LOCATION['name']}\n"
                    f"• Ostatnie sprawdzenie: {datetime.now().strftime('%H:%M')}\n\n"
                    
                    "🎯 <b>Co monitoruję:</b>\n"
                    "• Zachmurzenie i widoczność\n"
                    "• Przeloty ISS i Hubble'a\n"
                    "• Warunki nocne\n"
                    "• Wiatr i wilgotność\n\n"
                    
                    "⚙️ <b>Komendy:</b>\n"
                    "<code>/notify_off</code> - Wyłącz\n"
                    "<code>/notify_on</code> - Włącz\n"
                    "<code>/check_now</code> - Sprawdź teraz\n"
                )
                send_telegram_message(chat_id, msg)
            
            # Wyłącz powiadomienia
            elif text == "/notify_off":
                notification_system.remove_subscriber(chat_id)
                send_telegram_message(chat_id, 
                    "🔕 <b>POWIADOMIENIA WYŁĄCZONE</b>\n\n"
                    "Nie otrzymasz więcej automatycznych powiadomień.\n"
                    "Aby włączyć ponownie: <code>/notify_on</code>"
                )
            
            # Włącz powiadomienia
            elif text == "/notify_on":
                notification_system.add_subscriber(chat_id)
                send_telegram_message(chat_id,
                    "🔔 <b>POWIADOMIENIA WŁĄCZONE</b>\n\n"
                    "Teraz otrzymasz powiadomienia gdy:\n"
                    "• 🌤️ Warunki obserwacyjne będą dobre\n"
                    "• 🛰️ ISS/Hubble będą przelatywać\n"
                    "• ✨ Będą inne okazje do obserwacji\n\n"
                    "Aby wyłączyć: <code>/notify_off</code>"
                )
            
            # Pomoc
            elif text == "/help":
                help_msg = (
                    "═" * 40 + "\n"
                    "🆘 <b>POMOC - COSMOS SENTRY PRO</b>\n"
                    "═" * 40 + "\n\n"
                    
                    "🎯 <b>GŁÓWNE KOMENDY:</b>\n"
                    "<code>/start</code> - Zarejestruj się w systemie\n"
                    "<code>/notify_on</code> - Włącz powiadomienia\n"
                    "<code>/notify_off</code> - Wyłącz powiadomienia\n"
                    "<code>/notify_status</code> - Status powiadomień\n"
                    "<code>/check_now</code> - Sprawdź warunki TERAZ\n"
                    "<code>/next_passes</code> - Nadchodzące przeloty\n\n"
                    
                    "📊 <b>INFORMACJE:</b>\n"
                    "• Bot sam sprawdza warunki co 30 minut\n"
                    "• Wysyła powiadomienia gdy są dobre warunki\n"
                    "• Informuje 2h przed przelotem satelity\n"
                    "• Działa tylko w nocy (po zachodzie słońca)\n\n"
                    
                    "🎯 <b>KRYTERIA POWIADOMIEŃ:</b>\n"
                    "• Zachmurzenie < 40%\n"
                    "• Widoczność > 10 km\n"
                    "• Wiatr < 8 m/s\n"
                    "• Jest noc\n"
                    "• Satelita wysoki > 30°\n\n"
                    
                    "═" * 40 + "\n"
                    "<i>🌌 Bot dba o Twoje obserwacje astronomiczne!</i>"
                )
                send_telegram_message(chat_id, help_msg)
            
            # Domyślna odpowiedź
            else:
                default_msg = (
                    "🌌 <b>COSMOS SENTRY PRO v2.0</b>\n\n"
                    "To jest <b>proaktywny bot obserwacyjny</b>!\n\n"
                    "🎯 <b>Nie musisz nic robić</b> - bot sam Cię poinformuje:\n"
                    "• Kiedy warunki do obserwacji są dobre\n"
                    "• Kiedy przelatuje ISS lub Hubble\n"
                    "• O innych astronomicznych okazjach\n\n"
                    "📱 <b>Rozpocznij:</b>\n"
                    "1. Wpisz <code>/start</code> aby się zarejestrować\n"
                    "2. Bot zapisze Twoją lokalizację\n"
                    "3. Otrzymasz powiadomienia gdy będzie warto obserwować!\n\n"
                    "🔔 <i>Bot działa automatycznie 24/7</i>"
                )
                send_telegram_message(chat_id, default_msg)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logging.error(f"❌ Błąd przetwarzania webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== ZADANIA OKRESOWE ======================
def setup_scheduled_tasks():
    """Skonfiguruj zaplanowane zadania"""
    # Sprawdzaj warunki pogodowe co 30 minut
    scheduler.add_job(
        check_and_notify_good_conditions,
        trigger='interval',
        minutes=30,
        id='check_conditions',
        name='Sprawdzanie warunków obserwacyjnych',
        replace_existing=True
    )
    
    # Sprawdzaj przeloty satelit co godzinę
    scheduler.add_job(
        check_and_notify_satellite_passes,
        trigger='interval',
        minutes=60,
        id='check_satellites',
        name='Sprawdzanie przelotów satelit',
        replace_existing=True
    )
    
    # Codzienne podsumowanie o 18:00
    scheduler.add_job(
        send_daily_summary,
        trigger=CronTrigger(hour=18, minute=0),
        id='daily_summary',
        name='Codzienne podsumowanie',
        replace_existing=True
    )
    
    scheduler.start()
    logging.info("✅ Zaplanowane zadania uruchomione")

def send_daily_summary():
    """Wyślij codzienne podsumowanie"""
    notification_system = app.config['NOTIFICATION_SYSTEM']
    
    if not notification_system.subscribers:
        return
    
    weather_data = get_openweather_data(YOUR_LOCATION["lat"], YOUR_LOCATION["lon"])
    if not weather_data:
        return
    
    observation = calculate_observation_score(weather_data)
    now = datetime.now()
    
    # Tylko jeśli jest wieczór (18:00-22:00)
    if 18 <= now.hour <= 22:
        for chat_id in notification_system.subscribers:
            msg = (
                "🌅 <b>WIECZORNE PODSUMOWANIE</b>\n\n"
                f"📍 {YOUR_LOCATION['name']} | {now.strftime('%d.%m %H:%M')}\n\n"
                
                f"🌤️ <b>Aktualna pogoda:</b>\n"
                f"• Temperatura: {weather_data['temp']:.1f}°C\n"
                f"• Zachmurzenie: {weather_data['clouds']}%\n"
                f"• Wiatr: {weather_data['wind_speed']} m/s\n"
                f"• Widoczność: {weather_data['visibility']:.1f} km\n\n"
                
                f"🎯 <b>Warunki obserwacyjne:</b> {observation['category'].upper()}\n"
                f"Wynik: {observation['score']}/100\n\n"
            )
            
            if observation["score"] >= 60:
                msg += "✅ <b>DOBRE WARUNKI NA OBSERWACJE!</b>\n"
                msg += "To dobry wieczór na obserwacje!\n"
            else:
                msg += "⚠️ <b>Warunki nie są optymalne</b>\n"
                msg += "Może lepiej poczekać na lepszą pogodę.\n"
            
            msg += "\n🔔 Bot powiadomi Cię jeśli warunki się poprawią!"
            send_telegram_message(chat_id, msg)

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    print("=" * 60)
    print("🌌 COSMOS SENTRY PRO v2.0 - PROAKTYWNY SYSTEM POWIADOMIEŃ")
    print("=" * 60)
    
    print(f"📍 Lokalizacja: {YOUR_LOCATION['name']}")
    print(f"📌 Współrzędne: {YOUR_LOCATION['lat']:.4f}, {YOUR_LOCATION['lon']:.4f}")
    print(f"👥 Subskrybenci: {len(notification_system.subscribers)}")
    
    # Uruchom zaplanowane zadania
    setup_scheduled_tasks()
    
    print("\n🎯 SYSTEM DZIAŁA PROAKTYWNIE:")
    print("• Sprawdzanie warunków: co 30 minut")
    print("• Sprawdzanie satelit: co godzinę")
    print("• Podsumowanie: codziennie 18:00")
    print("• Powiadomienia: automatycznie przy dobrych warunkach")
    
    print("\n🔔 Bot będzie teraz SAM informować o:")
    print("1. Dobrych warunkach do obserwacji")
    print("2. Przelotach ISS i Hubble'a (2h przed)")
    print("3. Innych astronomicznych okazjach")
    
    print("\n📱 Użytkownik musi tylko wpisać: /start")
    print("=" * 60)
    
    # Uruchom serwer
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )