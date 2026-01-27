#!/usr/bin/env python3
"""
🤖 SENTRY ONE v14.0 - SATELITA + PIWO EDYCJA
System: Satelity w czasie rzeczywistym + NASA + DeepSeek AI + Piwo 🍻
"""

import os
import json
import time
import logging
import threading
import requests
import math
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import uuid

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"

# API klucze
NASA_API_KEY = "P0locPuOZBvnkHCdIKjkxzKsfnM7tc7pbiMcsBDE"
N2YO_API_KEY = "UNWEQ8-N47JL7-WFJZYX-5N65"
OPENWEATHER_API_KEY = "38e01cfb763fc738e9eddee84cfc4384"
DEEPSEEK_API_KEY = "sk-4af5d51f20e34ba8b53e09e6422341a4"

# API endpoints
N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
NASA_EARTH_URL = "https://api.nasa.gov/planetary/earth/imagery"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"

# Baza danych
DB_FILE = "sentry_one.db"

# Ciekawe satelity do obserwacji
INTERESTING_SATELLITES = {
    25544: {"name": "ISS", "type": "stacja", "emoji": "🛰️", "brightness": -3.9, "description": "Międzynarodowa Stacja Kosmiczna"},
    20580: {"name": "Hubble", "type": "teleskop", "emoji": "🔭", "brightness": 2.0, "description": "Teleskop Hubble'a"},
    27607: {"name": "Starlink", "type": "konstelacja", "emoji": "✨", "brightness": 3.0, "description": "Pociąg Starlink"},
    25994: {"name": "NOAA 19", "type": "pogoda", "emoji": "🌤️", "brightness": 2.5, "description": "Satelita pogodowy"},
    25338: {"name": "Landsat 8", "type": "obrazowanie", "emoji": "🛰️", "brightness": 4.0, "description": "Zdjęcia Ziemi"},
    28654: {"name": "Sentinel-2A", "type": "obrazowanie", "emoji": "📡", "brightness": 4.5, "description": "Obrazowanie wysokiej rozdzielczości"},
    43013: {"name": "CAPSTONE", "type": "księżyc", "emoji": "🌙", "brightness": 5.0, "description": "Misja księżycowa NASA"},
}

# Piwa do wyboru 🍻
BEER_SELECTION = {
    "jasne": ["🍺 Żywiec", "🍺 Tyskie", "🍺 Lech", "🍺 Okocim"],
    "ciemne": ["🍺 Porter", "🍺 Książęce Ciemne", "🍺 Komes Ciemne"],
    "pszeniczne": ["🍺 Żywiec Białe", "🍺 Hoegaarden", "🍺 Franziskaner"],
    "craft": ["🍺 APA", "🍺 IPA", "🍺 Stout", "🍺 Lager"],
    "bezalkoholowe": ["🍺 Heineken 0.0", "🍺 Lech Free", "🍺 Tyskie 0.0"]
}

print("=" * 60)
print("🤖 SENTRY ONE v14.0 - SATELITA + PIWO EDYCJA 🍻")
print(f"🌐 URL: {RENDER_URL}")
print("🛰️ N2YO Satelity + NASA Earth + DeepSeek AI")
print("🔔 System: SATELITA nad głową + ZDJĘCIE + PIWO")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== BAZA DANYCH ======================
def init_database():
    """Inicjalizacja bazy danych"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Użytkownicy
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            latitude REAL,
            longitude REAL,
            location_name TEXT,
            beer_preference TEXT DEFAULT 'jasne',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Zaplanowane sesje satelitarne
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS satellite_sessions (
            session_id TEXT PRIMARY KEY,
            chat_id INTEGER,
            satellite_id INTEGER,
            satellite_name TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            location_lat REAL,
            location_lon REAL,
            location_name TEXT,
            beer_type TEXT,
            status TEXT DEFAULT 'scheduled',
            notifications_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES users (chat_id)
        )
    ''')
    
    # Powiadomienia
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id TEXT PRIMARY KEY,
            session_id TEXT,
            chat_id INTEGER,
            scheduled_time TIMESTAMP,
            message TEXT,
            sent BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (session_id) REFERENCES satellite_sessions (session_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Baza danych zainicjalizowana")

# ====================== FUNKCJE BAZY DANYCH ======================
def get_user(chat_id):
    """Pobierz użytkownika z bazy"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "chat_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "location_name": row[6],
            "beer_preference": row[7] or "jasne",
            "created_at": row[8],
            "last_active": row[9]
        }
    return None

def save_user(chat_id, username="", first_name="", last_name=""):
    """Zapisz/aktualizuj użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (chat_id, username, first_name, last_name, last_active)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (chat_id, username, first_name, last_name))
    
    conn.commit()
    conn.close()

def update_user_location(chat_id, lat, lon, location_name):
    """Zaktualizuj lokalizację użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET latitude = ?, longitude = ?, location_name = ?
        WHERE chat_id = ?
    ''', (lat, lon, location_name, chat_id))
    
    conn.commit()
    conn.close()

def update_beer_preference(chat_id, beer_type):
    """Zaktualizuj preferencje piwne"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET beer_preference = ?
        WHERE chat_id = ?
    ''', (beer_type, chat_id))
    
    conn.commit()
    conn.close()

def save_satellite_session(session_data):
    """Zapisz sesję satelitarną"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO satellite_sessions 
        (session_id, chat_id, satellite_id, satellite_name, 
         start_time, end_time, location_lat, location_lon, 
         location_name, beer_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_data["session_id"],
        session_data["chat_id"],
        session_data["satellite_id"],
        session_data["satellite_name"],
        session_data["start_time"],
        session_data["end_time"],
        session_data["location_lat"],
        session_data["location_lon"],
        session_data["location_name"],
        session_data["beer_type"],
        session_data["status"]
    ))
    
    conn.commit()
    conn.close()

def save_notification(notification_data):
    """Zapisz powiadomienie"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO notifications 
        (notification_id, session_id, chat_id, scheduled_time, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        notification_data["notification_id"],
        notification_data["session_id"],
        notification_data["chat_id"],
        notification_data["scheduled_time"],
        notification_data["message"]
    ))
    
    conn.commit()
    conn.close()

def get_user_sessions(chat_id, limit=5):
    """Pobierz sesje użytkownika"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM satellite_sessions 
        WHERE chat_id = ? 
        ORDER BY start_time DESC 
        LIMIT ?
    ''', (chat_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    sessions = []
    for row in rows:
        sessions.append({
            "session_id": row[0],
            "satellite_name": row[3],
            "start_time": row[4],
            "location_name": row[8],
            "beer_type": row[9],
            "status": row[10]
        })
    
    return sessions

def cancel_session(session_id):
    """Anuluj sesję"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE satellite_sessions 
        SET status = 'cancelled'
        WHERE session_id = ?
    ''', (session_id,))
    
    # Usuń zaplanowane powiadomienia
    cursor.execute('''
        DELETE FROM notifications 
        WHERE session_id = ? AND sent = FALSE
    ''', (session_id,))
    
    conn.commit()
    conn.close()

# ====================== GEOKODOWANIE ======================
def geocode_address(address: str) -> Optional[Tuple[float, float, str]]:
    """Konwertuj adres na współrzędne GPS"""
    try:
        url = f"{NOMINATIM_URL}/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": "pl",  # Priorytet dla Polski
            "accept-language": "pl"
        }
        
        headers = {
            "User-Agent": "SentryOneBot/1.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                display_name = data[0].get("display_name", address)
                
                # Pobierz dokładniejszy adres
                reverse_url = f"{NOMINATIM_URL}/reverse"
                reverse_params = {
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "zoom": 18
                }
                
                reverse_response = requests.get(reverse_url, params=reverse_params, headers=headers, timeout=5)
                if reverse_response.status_code == 200:
                    reverse_data = reverse_response.json()
                    if reverse_data.get("address"):
                        address_parts = []
                        if "road" in reverse_data["address"]:
                            address_parts.append(reverse_data["address"]["road"])
                        if "house_number" in reverse_data["address"]:
                            address_parts.append(reverse_data["address"]["house_number"])
                        if address_parts:
                            street_address = " ".join(address_parts)
                            display_name = f"{street_address}, {display_name.split(',')[-1]}"
                
                return lat, lon, display_name
        
        return None
    except Exception as e:
        logger.error(f"❌ Błąd geokodowania: {e}")
        return None

def reverse_geocode(lat: float, lon: float) -> str:
    """Konwertuj współrzędne na adres"""
    try:
        url = f"{NOMINATIM_URL}/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 18,
            "accept-language": "pl"
        }
        
        headers = {
            "User-Agent": "SentryOneBot/1.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("address"):
                address = data["address"]
                parts = []
                
                if "road" in address:
                    parts.append(address["road"])
                    if "house_number" in address:
                        parts.append(address["house_number"])
                
                if "city" in address:
                    parts.append(address["city"])
                elif "town" in address:
                    parts.append(address["town"])
                elif "village" in address:
                    parts.append(address["village"])
                
                if "country" in address:
                    parts.append(address["country"])
                
                return ", ".join(parts) if parts else data.get("display_name", f"{lat}, {lon}")
        
        return f"{lat:.4f}, {lon:.4f}"
    except Exception as e:
        logger.error(f"❌ Błąd reverse geokodowania: {e}")
        return f"{lat:.4f}, {lon:.4f}"

# ====================== N2YO SATELITY ======================
def get_satellites_above(lat: float, lon: float, alt: float = 0, radius: int = 90, days: int = 2):
    """Pobierz satelity nad daną lokalizacją"""
    try:
        url = f"{N2YO_BASE_URL}/above/{lat}/{lon}/{alt}/{radius}/{days}"
        params = {"apiKey": N2YO_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            interesting_sats = []
            
            for sat in data.get("above", []):
                sat_id = sat["satid"]
                if sat_id in INTERESTING_SATELLITES:
                    sat_info = INTERESTING_SATELLITES[sat_id]
                    
                    # Pobierz przeloty dla tego satelity
                    passes = get_satellite_passes(sat_id, lat, lon, days=2)
                    
                    if passes:
                        interesting_sats.append({
                            "id": sat_id,
                            "name": sat["satname"],
                            "type": sat_info["type"],
                            "emoji": sat_info["emoji"],
                            "description": sat_info["description"],
                            "altitude": sat["satalt"],
                            "passes": passes[:3],  # 3 najbliższe przeloty
                            "brightness": sat_info.get("brightness", 0)
                        })
            
            return interesting_sats
        else:
            logger.error(f"❌ Błąd N2YO API: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Błąd pobierania satelitów: {e}")
        return []

def get_satellite_passes(sat_id: int, lat: float, lon: float, alt: float = 0, days: int = 2, min_visibility: int = 60):
    """Pobierz przeloty satelity"""
    try:
        url = f"{N2YO_BASE_URL}/radiopasses/{sat_id}/{lat}/{lon}/{alt}/{days}/{min_visibility}"
        params = {"apiKey": N2YO_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            passes = []
            
            for pass_data in data.get("passes", []):
                start_utc = datetime.utcfromtimestamp(pass_data["startUTC"])
                end_utc = datetime.utcfromtimestamp(pass_data["endUTC"])
                
                passes.append({
                    "start_utc": start_utc,
                    "end_utc": end_utc,
                    "duration": pass_data["endUTC"] - pass_data["startUTC"],
                    "max_elevation": pass_data["maxEl"],
                    "start_azimuth": pass_data["startAz"],
                    "end_azimuth": pass_data["endAz"],
                    "start_azimuth_compass": get_compass_direction(pass_data["startAz"]),
                    "end_azimuth_compass": get_compass_direction(pass_data["endAz"]),
                    "magnitude": pass_data.get("mag", 0)
                })
            
            return passes
        else:
            return []
    except Exception as e:
        logger.error(f"❌ Błąd pobierania przelotów: {e}")
        return []

def get_compass_direction(azimuth: float) -> str:
    """Konwertuj azymut na kierunek kompasu"""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(azimuth / 45) % 8
    return directions[index]

# ====================== NASA EARTH IMAGERY ======================
def get_satellite_image(lat: float, lon: float, date=None, dim: float = 0.025):
    """Pobierz zdjęcie satelitarne z NASA Earth API"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        url = "https://api.nasa.gov/planetary/earth/assets"
        
        params = {
            "lat": lat,
            "lon": lon,
            "date": date,
            "dim": dim,
            "api_key": NASA_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("url"):
                return data["url"]
        
        # Fallback - zdjęcie z Landsat Look API
        return get_landsat_image(lat, lon, date)
        
    except Exception as e:
        logger.error(f"❌ Błąd NASA Earth API: {e}")
        return get_static_map_image(lat, lon)

def get_landsat_image(lat: float, lon: float, date=None):
    """Pobierz zdjęcie z Landsat"""
    try:
        if not date:
            # Szukaj najnowszego dostępnego zdjęcia
            date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Proste API Landsat Look (darmowe)
        url = f"https://landsatlook.usgs.gov/sat-api/stac"
        params = {
            "bbox": f"{lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}",
            "datetime": f"{date}/2025-12-31",
            "collections": ["landsat-c2l2-sr"],
            "limit": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("features"):
                # Pobierz thumbnail
                thumb_url = data["features"][0].get("assets", {}).get("thumbnail", {}).get("href")
                if thumb_url:
                    return thumb_url
        
        return None
    except:
        return None

def get_static_map_image(lat: float, lon: float, zoom: int = 15):
    """Fallback - statyczna mapa satelitarna"""
    # OpenStreetMap static
    return f"https://static-maps.yandex.ru/1.x/?ll={lon},{lat}&z={zoom}&l=sat&size=600,400"

# ====================== DEEPSEEK AI ======================
class DeepSeekAI:
    """Integracja z DeepSeek AI"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
    
    def ask(self, prompt: str, max_tokens: int = 500) -> str:
        """Zapytaj DeepSeek AI"""
        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return "🤖 AI tymczasowo niedostępny. Spróbuj później!"
                
        except Exception as e:
            logger.error(f"❌ Błąd DeepSeek AI: {e}")
            return "🤖 Przykro mi, AI ma awarię. Spróbuj później!"
    
    def generate_satellite_tips(self, satellite_name: str, pass_data: dict) -> str:
        """Wygeneruj wskazówki do obserwacji satelity"""
        prompt = f"""
        Jesteś asystentem astronomicznym. Podaj praktyczne wskazówki do obserwacji satelity {satellite_name}.
        
        Dane przelotu:
        - Czas: {pass_data['start_utc'].strftime('%H:%M')}
        - Długość: {pass_data['duration']} sekund
        - Maksymalna wysokość: {pass_data['max_elevation']:.0f}°
        - Kierunek startu: {pass_data['start_azimuth_compass']} ({pass_data['start_azimuth']:.0f}°)
        - Kierunek końca: {pass_data['end_azimuth_compass']} ({pass_data['end_azimuth']:.0f}°)
        
        Podaj:
        1. Jak znaleźć satelitę na niebie (krok po kroku)
        2. Na co zwrócić uwagę podczas obserwacji
        3. Ciekawostkę o tym satelicie
        4. Czy warto użyć lornetki/teleskopu
        
        Odpowiedz po polsku, zwięźle i konkretnie.
        """
        
        return self.ask(prompt)

deepseek_ai = DeepSeekAI()

# ====================== SYSTEM SATELITA + PIWO ======================
def setup_satellite_beer_session(chat_id: int, address: str, beer_type: str = None):
    """Główna funkcja - zaplanuj sesję satelitarną z piwem"""
    
    # 1. Geokoduj adres
    logger.info(f"🌍 Geokodowanie adresu: {address}")
    geocode_result = geocode_address(address)
    
    if not geocode_result:
        return "❌ Nie mogę znaleźć tego adresu! Spróbuj podać dokładniejszy adres lub współrzędne."
    
    lat, lon, location_name = geocode_result
    
    # 2. Pobierz satelity
    logger.info(f"🛰️ Szukam satelitów nad {lat},{lon}")
    satellites = get_satellites_above(lat, lon)
    
    if not satellites:
        return "😔 Niestety, żadne ciekawe satelity nie przelatują nad tym miejscem w najbliższych dniach."
    
    # 3. Znajdź najlepszy przelot
    best_pass = None
    best_satellite = None
    
    for sat in satellites:
        for sat_pass in sat.get("passes", []):
            # Filtruj tylko dobre przeloty (wysokie, długie)
            if sat_pass["max_elevation"] > 20 and sat_pass["duration"] > 60:
                if not best_pass or sat_pass["max_elevation"] > best_pass["max_elevation"]:
                    best_pass = sat_pass
                    best_satellite = sat
    
    if not best_pass:
        return "📡 Znaleziono tylko niskie przeloty. Spróbuj jutro lub podaj inne miejsce!"
    
    # 4. Ustal piwo
    user = get_user(chat_id)
    if not beer_type:
        beer_type = user["beer_preference"] if user else "jasne"
    
    beer_options = BEER_SELECTION.get(beer_type, BEER_SELECTION["jasne"])
    selected_beer = random.choice(beer_options)
    
    # 5. Przygotuj dane sesji
    session_id = str(uuid.uuid4())[:8]
    session_data = {
        "session_id": session_id,
        "chat_id": chat_id,
        "satellite_id": best_satellite["id"],
        "satellite_name": best_satellite["name"],
        "start_time": best_pass["start_utc"],
        "end_time": best_pass["end_utc"],
        "location_lat": lat,
        "location_lon": lon,
        "location_name": location_name,
        "beer_type": beer_type,
        "status": "scheduled"
    }
    
    # 6. Zapisz sesję
    save_satellite_session(session_data)
    
    # 7. Zaplanuj powiadomienia
    schedule_session_notifications(session_data, best_pass, selected_beer)
    
    # 8. Zwróć plan
    return create_session_plan(session_data, best_pass, selected_beer)

def schedule_session_notifications(session_data: dict, pass_data: dict, selected_beer: str):
    """Zaplanuj powiadomienia dla sesji"""
    session_id = session_data["session_id"]
    chat_id = session_data["chat_id"]
    start_time = pass_data["start_utc"]
    
    notifications = [
        {
            "time": start_time - timedelta(hours=24),
            "message": f"⏰ <b>PRZYPOMNIENIE - JUTRO O {start_time.strftime('%H:%M')}</b>\n\n"
                      f"🛰️ Satelita: {session_data['satellite_name']}\n"
                      f"📍 Miejsce: {session_data['location_name'][:50]}...\n"
                      f"🍺 Piwo: {selected_beer}\n\n"
                      f"Przygotuj się na obserwację! 🔭"
        },
        {
            "time": start_time - timedelta(hours=1),
            "message": f"🔭 <b>ZA GODZINĘ - PRZYGOTUJ SIĘ!</b>\n\n"
                      f"🛰️ {session_data['satellite_name']} startuje o {start_time.strftime('%H:%M')}\n"
                      f"📍 Wyjdź na: {session_data['location_name'][:40]}...\n"
                      f"🍺 {selected_beer} - czas na schłodzenie!\n"
                      f"🧭 Startuj z kierunku: {pass_data['start_azimuth_compass']}"
        },
        {
            "time": start_time - timedelta(minutes=10),
            "message": f"🚀 <b>ZA 10 MINUT - NA MIEJSCU!</b>\n\n"
                      f"🛰️ {session_data['satellite_name']} startuje o {start_time.strftime('%H:%M')}\n"
                      f"👆 Patrz na: {pass_data['start_azimuth_compass']} ({pass_data['start_azimuth']:.0f}°)\n"
                      f"📈 Maks. wysokość: {pass_data['max_elevation']:.0f}°\n"
                      f"🍻 Otwórz {selected_beer} i patrz w niebo!"
        },
        {
            "time": start_time,
            "message": f"🛰️ <b>TERAZ! SATELITA NAD TOBĄ!</b>\n\n"
                      f"👀 {session_data['satellite_name']} właśnie startuje!\n"
                      f"⏱️ Czas obserwacji: {pass_data['duration']} sekund\n"
                      f"✨ Śledź go wzrokiem z {pass_data['start_azimuth_compass']} do {pass_data['end_azimuth_compass']}\n"
                      f"🍺 {selected_beer} - na zdrowie! 🥂"
        },
        {
            "time": start_time + timedelta(minutes=2),
            "message": f"📸 <b>ROBIĘ ZDJĘCIE TWOJEJ LOKALIZACJI!</b>\n\n"
                      f"🛰️ Satelita właśnie nad: {session_data['location_name'][:40]}...\n"
                      f"⏳ Pobieram zdjęcie satelitarne...\n"
                      f"🍻 Ciesz się obserwacją i {selected_beer}!"
        }
    ]
    
    for notif in notifications:
        notification_id = str(uuid.uuid4())[:8]
        notification_data = {
            "notification_id": notification_id,
            "session_id": session_id,
            "chat_id": chat_id,
            "scheduled_time": notif["time"],
            "message": notif["message"]
        }
        save_notification(notification_data)
        
        # Zaplanuj wysłanie (w prawdziwej implementacji użyj APScheduler)
        schedule_notification(notification_data)

def create_session_plan(session_data: dict, pass_data: dict, selected_beer: str) -> str:
    """Stwórz czytelny plan sesji"""
    
    # Generuj wskazówki od AI
    ai_tips = deepseek_ai.generate_satellite_tips(
        session_data["satellite_name"],
        pass_data
    )
    
    plan = f"""
🛰️ <b>SATELITA + PIWO - PLAN OBSERWACJI 🍻</b>

<b>📡 SATELITA:</b> {session_data['satellite_name']}
{INTERESTING_SATELLITES.get(session_data['satellite_id'], {}).get('emoji', '🛰️')} {INTERESTING_SATELLITES.get(session_data['satellite_id'], {}).get('description', '')}

<b>⏰ CZAS STARTU:</b> {pass_data['start_utc'].strftime('%Y-%m-%d %H:%M:%S')}
<b>⌛ CZAS TRWANIA:</b> {pass_data['duration']} sekund
<b>📈 MAKS. WYSOKOŚĆ:</b> {pass_data['max_elevation']:.0f}°
<b>🧭 KIERUNEK STARTU:</b> {pass_data['start_azimuth_compass']} ({pass_data['start_azimuth']:.0f}°)
<b>🧭 KIERUNEK KOŃCA:</b> {pass_data['end_azimuth_compass']} ({pass_data['end_azimuth']:.0f}°)

<b>📍 MIEJSCE:</b> {session_data['location_name']}
<b>📍 WSPÓŁRZĘDNE:</b> {session_data['location_lat']:.4f}, {session_data['location_lon']:.4f}

<b>🍺 PIWO:</b> {selected_beer}
<b>🎯 SESJA ID:</b> {session_data['session_id']}

<b>🔔 POWIADOMIENIA:</b>
1. 24h przed - przypomnienie
2. 1h przed - przygotowanie
3. 10min przed - na miejscu
4. 0min - start obserwacji
5. +2min - zdjęcie satelitarne

<b>🧠 WSKAZÓWKI OD AI:</b>
{ai_tips}

<b>❌ ANULUJ SESJĘ:</b>
/cancel_satellite {session_data['session_id']}

<b>🎯 NAJWAŻNIEJSZE:</b>
• Bądź na miejscu 10 minut wcześniej
• Sprawdź pogodę przed wyjściem
• Zabierz ciepłe ubranie
• Nie zapomnij {selected_beer}! 🍻

<b>🚀 POWODZENIA!</b>
"""
    
    return plan

# ====================== SYSTEM POWIADOMIEŃ ======================
scheduler = BackgroundScheduler()

def schedule_notification(notification_data: dict):
    """Zaplanuj wysłanie powiadomienia"""
    try:
        trigger = DateTrigger(run_date=notification_data["scheduled_time"])
        
        scheduler.add_job(
            send_scheduled_notification,
            trigger,
            args=[notification_data],
            id=notification_data["notification_id"]
        )
        
        logger.info(f"✅ Zaplanowano powiadomienie {notification_data['notification_id']} na {notification_data['scheduled_time']}")
    except Exception as e:
        logger.error(f"❌ Błąd planowania powiadomienia: {e}")

def send_scheduled_notification(notification_data: dict):
    """Wyślij zaplanowane powiadomienie"""
    try:
        chat_id = notification_data["chat_id"]
        message = notification_data["message"]
        
        # Jeśli to powiadomienie o zdjęciu
        if "ROBIĘ ZDJĘCIE" in message:
            # Pobierz sesję
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT location_lat, location_lon FROM satellite_sessions WHERE session_id = ?', 
                         (notification_data["session_id"],))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                lat, lon = row
                # Pobierz zdjęcie satelitarne
                image_url = get_satellite_image(lat, lon)
                
                if image_url:
                    send_photo_message(
                        chat_id,
                        image_url,
                        caption=f"📸 <b>ZDJĘCIE SATELITARNE TWOJEJ LOKALIZACJI</b>\n\n"
                               f"📍 {reverse_geocode(lat, lon)}\n"
                               f"🛰️ Zdjęcie wykonane przez satelitę obserwacyjnego\n"
                               f"🍻 Na zdrowie! Kolejna sesja za 90 minut!"
                    )
                else:
                    send_telegram_message(chat_id, 
                        "❌ Nie udało się pobrać zdjęcia satelitarnego.\n"
                        "Spróbuję ponownie przy następnym przelocie!"
                    )
        else:
            send_telegram_message(chat_id, message)
        
        # Oznacz jako wysłane
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE notifications SET sent = TRUE WHERE notification_id = ?', 
                     (notification_data["notification_id"],))
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania powiadomienia: {e}")

# ====================== TELEGRAM FUNCTIONS ======================
def send_telegram_message(chat_id: int, text: str, parse_mode: str = "HTML", reply_markup=None):
    """Wyślij wiadomość na Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania wiadomości: {e}")
        return None

def send_photo_message(chat_id: int, photo_url: str, caption: str = ""):
    """Wyślij zdjęcie na Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Błąd wysyłania zdjęcia: {e}")
        # Fallback - wyślij link
        send_telegram_message(chat_id, f"📸 {caption}\n\n🔗 Link do zdjęcia: {photo_url}")
        return None

# ====================== FLASK APP ======================
app = Flask(__name__)

# Globalne zmienne
last_ping_time = datetime.now()
ping_count = 0

@app.route('/')
def home():
    """Strona główna"""
    global last_ping_time, ping_count
    last_ping_time = datetime.now()
    ping_count += 1
    
    now = datetime.now()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v14.0 - Satelita + Piwo 🍻</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0a2a 0%, #1a1a4a 100%);
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 30px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }}
            .beer-emoji {{
                font-size: 60px;
                animation: float 3s infinite;
            }}
            @keyframes float {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-10px); }}
            }}
            .satellite-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 30px 0;
            }}
            .satellite-card {{
                background: rgba(0,0,0,0.3);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 25px;
                background: linear-gradient(to right, #4776E6, #8E54E9);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                margin: 10px;
                transition: transform 0.3s;
            }}
            .btn:hover {{ transform: translateY(-2px); }}
            .btn-beer {{
                background: linear-gradient(to right, #f46b45, #eea849);
            }}
            .status-info {{
                background: rgba(0,0,0,0.3);
                padding: 15px;
                border-radius: 10px;
                margin-top: 20px;
                font-family: monospace;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 SENTRY ONE v14.0</h1>
            <h2>Satelita + Piwo Edition 🍻</h2>
            
            <div class="beer-emoji">🍺</div>
            
            <div style="margin: 30px 0;">
                <a href="https://t.me/PcSentintel_Bot" target="_blank" class="btn">
                    💬 Otwórz bota w Telegram
                </a>
                <a href="/satellite_demo" class="btn btn-beer">
                    🛰️ Demo satelity
                </a>
                <a href="/health" class="btn" style="background: linear-gradient(to right, #00c6ff, #0072ff);">
                    🏥 Status zdrowia
                </a>
            </div>
            
            <div class="satellite-grid">
                <div class="satellite-card">
                    <h3>🛰️ ISS</h3>
                    <p>Stacja kosmiczna</p>
                    <p>Jasność: -3.9 mag</p>
                </div>
                <div class="satellite-card">
                    <h3>🔭 Hubble</h3>
                    <p>Teleskop kosmiczny</p>
                    <p>Jasność: 2.0 mag</p>
                </div>
                <div class="satellite-card">
                    <h3>✨ Starlink</h3>
                    <p>Pociąg satelitów</p>
                    <p>Widoczny gołym okiem</p>
                </div>
                <div class="satellite-card">
                    <h3>🌤️ NOAA 19</h3>
                    <p>Satelita pogodowy</p>
                    <p>Codzienne obrazy Ziemi</p>
                </div>
            </div>
            
            <div class="status-info">
                <h4>📊 Statystyki systemu:</h4>
                <p>• Ostatni ping: {last_ping_time.strftime('%H:%M:%S')}</p>
                <p>• Liczba pingów: {ping_count}</p>
                <p>• Aktywne sesje: {get_active_sessions_count()}</p>
                <p>• Obserwowane satelity: {len(INTERESTING_SATELLITES)}</p>
            </div>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                <p>🤖 SENTRY ONE v14.0 | System: Satelita + Piwo + Zdjęcie</p>
                <p style="font-family: monospace; font-size: 12px; opacity: 0.8;">
                    {now.strftime("%Y-%m-%d %H:%M:%S")} | Ping #{ping_count} | 🍻 Na zdrowie!
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

def get_active_sessions_count():
    """Pobierz liczbę aktywnych sesji"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM satellite_sessions WHERE status = 'scheduled'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

@app.route('/satellite_demo')
def satellite_demo():
    """Demo systemu satelitarnego"""
    # Przykładowa sesja
    demo_data = {
        "satellite": "ISS",
        "time": (datetime.now() + timedelta(hours=2)).strftime("%H:%M"),
        "location": "Warszawa, Polska",
        "beer": "🍺 Żywiec",
        "image_url": get_static_map_image(52.2297, 21.0122)
    }
    
    return jsonify({
        "demo": True,
        "system": "Satelita + Piwo",
        "data": demo_data,
        "instructions": "Użyj w Telegramie: /satellite_beer [twój adres]"
    })

@app.route('/health')
def health():
    """Status zdrowia"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "telegram_bot": True,
            "n2yo_satellites": True,
            "nasa_earth": True,
            "deepseek_ai": True,
            "scheduler": scheduler.running if hasattr(scheduler, 'running') else False
        },
        "ping_count": ping_count,
        "active_sessions": get_active_sessions_count()
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
        "time": last_ping_time.isoformat(),
        "message": "🍻 System gotowy na satelity i piwo!"
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook Telegram - GŁÓWNY ENDPOINT"""
    global last_ping_time, ping_count
    
    try:
        data = request.get_json()
        logger.info(f"📩 Webhook odebrany")
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()
            
            # Zaktualizuj czas aktywności
            last_ping_time = datetime.now()
            ping_count += 1
            
            # Zapisz użytkownika
            from_user = message.get("from", {})
            save_user(
                chat_id,
                from_user.get("username", ""),
                from_user.get("first_name", ""),
                from_user.get("last_name", "")
            )
            
            # Obsługa komend
            if text.startswith("/"):
                handle_command(chat_id, text.lower(), from_user)
            else:
                send_telegram_message(chat_id, 
                    "🤖 Użyj /help aby zobaczyć wszystkie komendy\n"
                    "lub /satellite_beer [adres] aby zacząć przygodę z satelitami! 🍻"
                )
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"🔥 Błąd webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def handle_command(chat_id: int, command: str, user_data: dict):
    """Obsłuż komendę od użytkownika"""
    
    # Komenda główna - SATELITA + PIWO
    if command.startswith("/satellite_beer"):
        parts = command.split()
        if len(parts) > 1:
            address = " ".join(parts[1:])
            
            # Opcjonalny typ piwa
            beer_type = None
            if len(parts) > 2 and parts[-1] in BEER_SELECTION:
                beer_type = parts[-1]
                address = " ".join(parts[1:-1])
            
            send_telegram_message(chat_id, "🔍 Szukam satelitów i dobieram piwo... 🍻")
            
            plan = setup_satellite_beer_session(chat_id, address, beer_type)
            send_telegram_message(chat_id, plan)
        else:
            send_telegram_message(chat_id,
                "❌ Podaj adres!\n\n"
                "Przykłady:\n"
                "<code>/satellite_beer Warszawa</code>\n"
                "<code>/satellite_beer Marszałkowska 1, Warszawa</code>\n"
                "<code>/satellite_beer 52.2297,21.0122</code>\n"
                "<code>/satellite_beer Kraków jasne</code>\n"
                "<code>/satellite_beer Gdańsk ciemne</code>\n\n"
                f"Dostępne piwa: {', '.join(BEER_SELECTION.keys())}"
            )
    
    # Ustaw lokalizację
    elif command.startswith("/set_location"):
        parts = command.split()
        if len(parts) > 1:
            location = " ".join(parts[1:])
            
            # Sprawdź czy to współrzędne
            if "," in location:
                try:
                    lat, lon = map(float, location.split(",")[:2])
                    location_name = reverse_geocode(lat, lon)
                    update_user_location(chat_id, lat, lon, location_name)
                    send_telegram_message(chat_id, f"✅ Lokalizacja zapisana: {location_name}")
                except:
                    send_telegram_message(chat_id, "❌ Nieprawidłowe współrzędne!")
            else:
                # Geokoduj adres
                result = geocode_address(location)
                if result:
                    lat, lon, location_name = result
                    update_user_location(chat_id, lat, lon, location_name)
                    send_telegram_message(chat_id, f"✅ Lokalizacja zapisana: {location_name}")
                else:
                    send_telegram_message(chat_id, "❌ Nie znaleziono adresu!")
        else:
            send_telegram_message(chat_id,
                "📍 Ustaw swoją domyślną lokalizację:\n\n"
                "<code>/set_location [adres]</code>\n"
                "<code>/set_location [szerokość],[długość]</code>\n\n"
                "Przykłady:\n"
                "<code>/set_location Warszawa</code>\n"
                "<code>/set_location 52.2297,21.0122</code>"
            )
    
    # Nadchodzące satelity
    elif command == "/next_satellites":
        user = get_user(chat_id)
        if user and user.get("latitude"):
            satellites = get_satellites_above(user["latitude"], user["longitude"])
            
            if satellites:
                response = "🛰️ <b>NADCHODZĄCE SATELITY NAD TOBĄ</b>\n\n"
                
                for sat in satellites[:3]:  # 3 najbliższe
                    if sat.get("passes"):
                        next_pass = sat["passes"][0]
                        time_str = next_pass["start_utc"].strftime("%H:%M")
                        
                        response += f"{sat['emoji']} <b>{sat['name']}</b>\n"
                        response += f"  ⏰ {time_str} | 📈 {next_pass['max_elevation']:.0f}°\n"
                        response += f"  🕐 {next_pass['duration']}s | 🧭 {next_pass['start_azimuth_compass']}\n"
                        response += f"  📍 {sat['description']}\n\n"
                
                response += "🎯 <b>Zaplanuj obserwację:</b>\n"
                response += "<code>/satellite_beer [adres] [piwo]</code>"
                
                send_telegram_message(chat_id, response)
            else:
                send_telegram_message(chat_id, 
                    "😔 Brak satelitów w najbliższych godzinach.\n"
                    "Spróbuj później lub ustaw inną lokalizację!"
                )
        else:
            send_telegram_message(chat_id,
                "❌ Najpierw ustaw swoją lokalizację!\n"
                "<code>/set_location [adres]</code>"
            )
    
    # Moje sesje
    elif command == "/my_sessions":
        sessions = get_user_sessions(chat_id, limit=5)
        
        if sessions:
            response = "📋 <b>MOJE SESJE SATELITARNE</b>\n\n"
            
            for session in sessions:
                time_str = datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S").strftime("%d.%m %H:%M")
                status_emoji = "🟢" if session["status"] == "scheduled" else "🔴"
                
                response += f"{status_emoji} <b>{session['satellite_name']}</b>\n"
                response += f"  ⏰ {time_str} | 📍 {session['location_name'][:30]}...\n"
                response += f"  🍺 {session['beer_type']} | 🆔 {session['session_id']}\n\n"
            
            response += "❌ <b>Anuluj sesję:</b>\n"
            response += "<code>/cancel_satellite [session_id]</code>"
            
            send_telegram_message(chat_id, response)
        else:
            send_telegram_message(chat_id,
                "📭 Nie masz zaplanowanych sesji.\n\n"
                "🎯 Zaplanuj pierwszą:\n"
                "<code>/satellite_beer [twój adres]</code>"
            )
    
    # Anuluj sesję
    elif command.startswith("/cancel_satellite"):
        parts = command.split()
        if len(parts) == 2:
            session_id = parts[1]
            cancel_session(session_id)
            send_telegram_message(chat_id, f"✅ Sesja {session_id} anulowana.")
        else:
            send_telegram_message(chat_id,
                "❌ Podaj ID sesji!\n\n"
                "<code>/cancel_satellite [session_id]</code>\n\n"
                "ID znajdziesz w: /my_sessions"
            )
    
    # Ustaw piwo
    elif command.startswith("/set_beer"):
        parts = command.split()
        if len(parts) == 2 and parts[1] in BEER_SELECTION:
            beer_type = parts[1]
            update_beer_preference(chat_id, beer_type)
            
            beer_options = BEER_SELECTION[beer_type]
            response = f"✅ Domyślne piwo ustawione na: <b>{beer_type}</b>\n\n"
            response += f"🍺 Dostępne opcje:\n"
            for beer in beer_options:
                response += f"• {beer}\n"
            
            send_telegram_message(chat_id, response)
        else:
            send_telegram_message(chat_id,
                "❌ Wybierz rodzaj piwa:\n\n" +
                "\n".join([f"<code>/set_beer {beer_type}</code>" for beer_type in BEER_SELECTION.keys()])
            )
    
    # Start
    elif command == "/start":
        welcome = f"""
🤖 <b>SENTRY ONE v14.0 - SATELITA + PIWO 🍻</b>

👋 Witaj, {user_data.get('first_name', 'Astronomie')}!

<b>🚀 NOWOŚĆ:</b> System <b>SATELITA + PIWO + ZDJĘCIE</b>
1. Znajdź satelitę nad twoją głową
2. Zaplanuj obserwację z piwem
3. Otrzymaj powiadomienia
4. Oglądaj satelitę na żywo
5. Dostaniesz zdjęcie satelitarne twojej lokalizacji!

<b>🛰️ OBSERWUJ SATELITY:</b>
• ISS - stacja kosmiczna
• Hubble - teleskop kosmiczny  
• Starlink - pociąg satelitów
• NOAA 19 - satelita pogodowy
• i wiele innych!

<b>🍺 DOSTĘPNE PIWA:</b>
{', '.join(BEER_SELECTION.keys())}

<b>🎮 KOMENDY:</b>
<code>/satellite_beer [adres]</code> - zaplanuj sesję
<code>/set_location [adres]</code> - ustaw lokalizację
<code>/next_satellites</code> - nadchodzące satelity
<code>/my_sessions</code> - moje sesje
<code>/set_beer [typ]</code> - ustaw piwo
<code>/help</code> - wszystkie komendy

<b>📍 PRZYKŁAD:</b>
<code>/satellite_beer Warszawa jasne</code>
<code>/satellite_beer 52.2297,21.0122 craft</code>

<b>🚀 ZACZNIJMY PRZYGODĘ!</b>
        """
        send_telegram_message(chat_id, welcome)
    
    # Help
    elif command == "/help":
        help_text = """
📋 <b>WSZYSTKIE KOMENDY</b>

<b>🛰️ SYSTEM SATELITA + PIWO:</b>
<code>/satellite_beer [adres] [piwo]</code> - zaplanuj sesję
<code>/next_satellites</code> - satelity nad tobą
<code>/my_sessions</code> - twoje sesje
<code>/cancel_satellite [id]</code> - anuluj sesję

<b>📍 LOKALIZACJA:</b>
<code>/set_location [adres]</code> - ustaw domyślną
<code>/set_location [lat],[lon]</code> - przez współrzędne

<b>🍺 PIWO:</b>
<code>/set_beer [typ]</code> - ustaw domyślne
Dostępne: jasne, ciemne, pszeniczne, craft, bezalkoholowe

<b>🛰️ SATELITY:</b>
• ISS 🛰️ - Międzynarodowa Stacja Kosmiczna
• Hubble 🔭 - Teleskop kosmiczny
• Starlink ✨ - Pociąg satelitów
• NOAA 19 🌤️ - Satelita pogodowy
• Landsat 8 🛰️ - Zdjęcia Ziemi

<b>🎯 PRZYKŁADY:</b>
<code>/satellite_beer Warszawa</code>
<code>/satellite_beer Kraków jasne</code>
<code>/satellite_beer 52.2297,21.0122 craft</code>
<code>/set_location Gdańsk</code>
<code>/set_beer ciemne</code>

<b>🚀 POWODZENIA W OBSERWACJACH!</b> 🍻
        """
        send_telegram_message(chat_id, help_text)
    
    # Inne komendy (możesz dodać stare funkcje tutaj)
    else:
        send_telegram_message(chat_id,
            "🤖 Nieznana komenda!\n\n"
            "🎯 Użyj <code>/satellite_beer [adres]</code> aby zacząć!\n"
            "lub <code>/help</code> aby zobaczyć wszystkie komendy."
        )

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 URUCHAMIANIE SENTRY ONE v14.0")
    print("🍻 SATELITA + PIWO EDYCJA")
    print("=" * 60)
    
    # Inicjalizuj bazę danych
    init_database()
    
    # Uruchom scheduler
    try:
        scheduler.start()
        print("✅ Scheduler uruchomiony")
    except:
        print("⚠️ Scheduler już działa")
    
    print(f"🌐 Webhook URL: {WEBHOOK_URL}")
    print(f"🔧 Port: {PORT}")
    print(f"🍻 Piwa dostępne: {len(BEER_SELECTION)} rodzajów")
    print(f"🛰️ Satelity: {len(INTERESTING_SATELLITES)} do obserwacji")
    print("=" * 60)
    print("🚀 SYSTEM GOTOWY DO DZIAŁANIA!")
    print("🍻 UŻYJ: /satellite_beer [twój adres]")
    print("=" * 60)
    
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )