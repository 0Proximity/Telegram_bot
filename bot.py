#!/usr/bin/env python3
"""
🤖 SENTRY ONE v14.0 - TOAST EDITION
DeepSeek AI + IBM Quantum + NASA + Mapbox + SATELLITE TOAST!
"""

import os
import json
import time
import logging
import threading
import requests
import math
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
import sqlite3
from typing import Dict, List, Optional

# ====================== KONFIGURACJA ======================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL","https://telegram-bot-szxa.onrender.com")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"{RENDER_URL}/webhook")  # Używamy z env lub domyślnego

# API klucze - UŻYJ SWOICH KLUCZY LUB ZMIENNYCH ŚRODOWISKOWYCH
NASA_API_KEY = os.getenv("NASA_API_KEY")
N2YO_API_KEY = os.getenv("N2YO_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
IBM_QUANTUM_TOKEN = os.getenv("IBM_QUANTUM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# MAPBOX API - TWÓJ TOKEN
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")

# API endpoints
N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MAPBOX_STATIC_URL = "https://api.mapbox.com/styles/v1/mapbox"

# Baza danych użytkowników
DB_FILE = "sentry_one.db"

# Miasta do obserwacji z miejscami do toastu
OBSERVATION_CITIES = {
    "warszawa": {
        "name": "Warszawa", 
        "lat": 52.2297, 
        "lon": 21.0122,
        "timezone": "Europe/Warsaw",
        "country": "Poland",
        "emoji": "🏛️",
        "toast_spots": [
            {"name": "Park Skaryszewski", "lat": 52.2381, "lon": 21.0485, "desc": "Otwarta przestrzeń nad Jeziorem Kamionkowskim", "type": "park"},
            {"name": "Dach Biblioteki UW", "lat": 52.2318, "lon": 21.0127, "desc": "Widok na całe miasto", "type": "viewpoint"},
            {"name": "Kopiec Powstania Warszawskiego", "lat": 52.2044, "lon": 21.0532, "desc": "Najwyższy punkt w Warszawie", "type": "hill"},
            {"name": "Bulwary Wiślane", "lat": 52.2400, "lon": 21.0300, "desc": "Otwarta przestrzeń nad Wisłą", "type": "river"},
            {"name": "Łazienki Królewskie", "lat": 52.2155, "lon": 21.0355, "desc": "Park z otwartym niebem", "type": "park"}
        ]
    },
    "koszalin": {
        "name": "Koszalin", 
        "lat": 54.1943, 
        "lon": 16.1712,
        "timezone": "Europe/Warsaw",
        "country": "Poland",
        "emoji": "🌲",
        "toast_spots": [
            {"name": "Wzgórze Chełmskie", "lat": 54.1955, "lon": 16.1839, "desc": "Najwyższy punkt z widokiem na miasto", "type": "hill"},
            {"name": "Jezioro Jamno", "lat": 54.2300, "lon": 16.1500, "desc": "Otwarta przestrzeń nad jeziorem", "type": "lake"},
            {"name": "Park nad Dzierżęcinką", "lat": 54.1900, "lon": 16.1700, "desc": "Cichy park w centrum miasta", "type": "park"},
            {"name": "Wieża Katedralna", "lat": 54.1903, "lon": 16.1824, "desc": "Widok z wieży katedry", "type": "viewpoint"}
        ]
    },
    "krakow": {
        "name": "Kraków", 
        "lat": 50.0647, 
        "lon": 19.9450,
        "timezone": "Europe/Warsaw",
        "country": "Poland",
        "emoji": "🐉",
        "toast_spots": [
            {"name": "Kopiec Kościuszki", "lat": 50.0550, "lon": 19.8936, "desc": "Panoramiczny widok na miasto", "type": "hill"},
            {"name": "Błonia Krakowskie", "lat": 50.0589, "lon": 19.9022, "desc": "Ogromna otwarta przestrzeń", "type": "park"},
            {"name": "Wawel", "lat": 50.0541, "lon": 19.9354, "desc": "Wzgórze wawelskie nad Wisłą", "type": "historic"}
        ]
    }
}

# Satelity do obserwacji
SATELLITES = {
    "iss": {"name": "Międzynarodowa Stacja Kosmiczna (ISS)", "id": 25544, "emoji": "🛰️", "type": "stacja"},
    "hubble": {"name": "Teleskop Hubble'a", "id": 20580, "emoji": "🔭", "type": "teleskop"},
    "terra": {"name": "Satelita Terra (NASA)", "id": 25994, "emoji": "🌍", "type": "obserwacja"},
    "noaa20": {"name": "NOAA-20 (pogoda)", "id": 43013, "emoji": "🌤️", "type": "meteo"}
}

print("=" * 70)
print("🤖 SENTRY ONE v14.0 - TOAST EDITION")
print("🍻 WYJDŹ Z PIWEM, TOAST DO SATELITY! 🛰️")
print("=" * 70)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== MAPBOX MODULE ======================
class MapboxProvider:
    """Dostawca map i zdjęć satelitarnych Mapbox"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.available = bool(api_key and len(api_key) > 10)
    
    def get_satellite_image(self, lat, lon, zoom=15, width=600, height=400):
        """Pobierz zdjęcie satelitarne z Mapbox"""
        if not self.available:
            return self._get_fallback_image()
        
        try:
            # Styl satellite-v9 dla zdjęć satelitarnych
            url = f"{MAPBOX_STATIC_URL}/satellite-v9/static/{lon},{lat},{zoom}/{width}x{height}"
            url += f"?access_token={self.api_key}&attribution=false&logo=false"
            
            # Sprawdź czy URL jest dostępny
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                return url
            else:
                return self._get_fallback_image()
                
        except Exception as e:
            logger.error(f"Mapbox error: {e}")
            return self._get_fallback_image()
    
    def get_street_map(self, lat, lon, zoom=15, width=600, height=400):
        """Pobierz mapę uliczną"""
        if not self.available:
            return None
        
        try:
            # Styl streets-v11 dla mapy ulic
            url = f"{MAPBOX_STATIC_URL}/streets-v11/static/{lon},{lat},{zoom}/{width}x{height}"
            url += f"?access_token={self.api_key}&attribution=false&logo=false"
            return url
        except:
            return None
    
    def get_terrain_map(self, lat, lon, zoom=15, width=600, height=400):
        """Pobierz mapę terenu"""
        if not self.available:
            return None
        
        try:
            # Styl outdoors-v11 dla terenu
            url = f"{MAPBOX_STATIC_URL}/outdoors-v11/static/{lon},{lat},{zoom}/{width}x{height}"
            url += f"?access_token={self.api_key}&attribution=false&logo=false"
            return url
        except:
            return None
    
    def _get_fallback_image(self):
        """Fallback - zdjęcie kosmosu z Unsplash"""
        space_images = [
            "https://images.unsplash.com/photo-1446776653964-20c1d3a81b06?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1502134249126-9f3755a50d78?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1465101162946-4377e57745c3?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1516339901601-2e1b62dc0c45?w=600&h=400&fit=crop",
        ]
        return random.choice(space_images)
    
    def get_directions_url(self, start_lat, start_lon, end_lat, end_lon):
        """URL do nawigacji Mapbox"""
        if not self.available:
            return None
        return f"https://api.mapbox.com/directions/v5/mapbox/walking/{start_lon},{start_lat};{end_lon},{end_lat}?access_token={self.api_key}&geometries=geojson"

# ====================== TOAST MODULE ======================
class SatelliteToast:
    """Moduł Toast do Satelity"""
    
    def __init__(self, mapbox_provider):
        self.api_key = N2YO_API_KEY
        self.mapbox = mapbox_provider
        
    def get_next_satellite_pass(self, city_key, satellite_id=25544, days=1, min_visibility=30):
        """Pobierz następny przelot satelity nad miastem"""
        city = OBSERVATION_CITIES.get(city_key)
        if not city:
            return None
        
        try:
            url = f"{N2YO_BASE_URL}/visualpasses/{satellite_id}/{city['lat']}/{city['lon']}/0/{days}/{min_visibility}"
            params = {"apiKey": self.api_key}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("info", {}).get("passescount", 0) > 0:
                pass_data = data["passes"][0]
                satellite = SATELLITES.get("iss", {})
                
                # Konwersja czasów
                start_utc = pass_data["startUTC"]
                max_utc = pass_data["maxUTC"]
                end_utc = pass_data["endUTC"]
                
                # UTC+1 dla Polski (można dodać logikę czasu letniego)
                start_local = datetime.fromtimestamp(start_utc) + timedelta(hours=1)
                max_local = datetime.fromtimestamp(max_utc) + timedelta(hours=1)
                end_local = datetime.fromtimestamp(end_utc) + timedelta(hours=1)
                
                return {
                    "satellite": satellite.get("name", "ISS"),
                    "satellite_emoji": satellite.get("emoji", "🛰️"),
                    "start_time": start_local.strftime("%H:%M"),
                    "max_time": max_local.strftime("%H:%M"),
                    "end_time": end_local.strftime("%H:%M"),
                    "date": start_local.strftime("%Y-%m-%d"),
                    "duration": int((end_utc - start_utc) / 60),  # w minutach
                    "max_elevation": round(pass_data["maxEl"], 1),
                    "start_azimuth": round(pass_data["startAz"], 1),
                    "start_compass": self.degrees_to_compass(pass_data["startAz"]),
                    "max_compass": self.degrees_to_compass(pass_data["maxAz"]),
                    "success": True
                }
            else:
                # Symuluj przelot jeśli API nie odpowiada
                return self._simulate_pass(city)
                
        except Exception as e:
            logger.error(f"Satellite API error: {e}")
            return self._simulate_pass(city)
    
    def _simulate_pass(self, city):
        """Symuluj przelot satelity (gdy API niedostępne)"""
        now = datetime.now()
        future = now + timedelta(hours=random.randint(1, 4))
        
        return {
            "satellite": "Międzynarodowa Stacja Kosmiczna (ISS)",
            "satellite_emoji": "🛰️",
            "start_time": (future - timedelta(minutes=5)).strftime("%H:%M"),
            "max_time": future.strftime("%H:%M"),
            "end_time": (future + timedelta(minutes=5)).strftime("%H:%M"),
            "date": future.strftime("%Y-%m-%d"),
            "duration": 10,
            "max_elevation": random.randint(30, 80),
            "start_azimuth": random.randint(0, 360),
            "start_compass": random.choice(["Północ", "Południe", "Wschód", "Zachód"]),
            "max_compass": random.choice(["Północ", "Południe", "Wschód", "Zachód"]),
            "success": True,
            "simulated": True
        }
    
    def degrees_to_compass(self, degrees):
        """Konwertuj stopnie na kierunek kompasu"""
        directions = [
            "Północ", "Północny-Wschód", "Wschód", "Południowy-Wschód",
            "Południe", "Południowy-Zachód", "Zachód", "Północny-Zachód"
        ]
        index = round(degrees / 45) % 8
        return directions[index]
    
    def generate_toast_spot(self, city_key, spot_type=None):
        """Wygeneruj miejsce do toastu"""
        city = OBSERVATION_CITIES.get(city_key)
        if not city or not city.get("toast_spots"):
            # Fallback na losowe współrzędne
            lat = city["lat"] + random.uniform(-0.02, 0.02)
            lon = city["lon"] + random.uniform(-0.02, 0.02)
            return {
                "name": "Sekretne miejsce obserwacyjne",
                "lat": lat,
                "lon": lon,
                "desc": "Wyjątkowe miejsce wybrane przez system",
                "type": "secret",
                "emoji": "🗺️"
            }
        
        # Filtruj po typie jeśli podany
        if spot_type:
            filtered_spots = [s for s in city["toast_spots"] if s.get("type") == spot_type]
            spots = filtered_spots if filtered_spots else city["toast_spots"]
        else:
            spots = city["toast_spots"]
        
        spot = random.choice(spots)
        
        # Dodaj emoji wg typu
        type_emojis = {
            "park": "🌳", "viewpoint": "👁️", "hill": "⛰️", 
            "river": "🌊", "lake": "💧", "historic": "🏰"
        }
        spot["emoji"] = type_emojis.get(spot.get("type", ""), "📍")
        
        return spot
    
    def get_toast_instructions(self, city_key, satellite_pass, spot, weather=None):
        """Wygeneruj instrukcje toastu"""
        city = OBSERVATION_CITIES[city_key]
        
        # Wybierz satelitę
        satellite = next((s for s in SATELLITES.values() if s["name"] == satellite_pass["satellite"]), SATELLITES["iss"])
        
        instructions = f"""
{satellite['emoji']} <b>PLAN TOASTU DO SATELITY!</b>

📍 <b>MIASTO:</b> {city['name']} {city['emoji']}

🛰️ <b>SATELITA:</b> {satellite_pass['satellite']}
📅 <b>DATA:</b> {satellite_pass['date']}
⏰ <b>GODZINY:</b> {satellite_pass['start_time']} - {satellite_pass['end_time']}
🎯 <b>NAJLEPSZY MOMENT:</b> {satellite_pass['max_time']}
🧭 <b>KIERUNEK:</b> {satellite_pass['start_compass']} → {satellite_pass['max_compass']}
📐 <b>WYSOKOŚĆ:</b> {satellite_pass['max_elevation']}°
⏱️ <b>CZAS TRWANIA:</b> {satellite_pass['duration']} minut

{spot['emoji']} <b>MIEJSCE SPOTKANIA:</b>
<b>{spot['name']}</b>
{spot['desc']}

📱 <b>INSTRUKCJA KROK PO KROKU:</b>
1. 🍺 Zaopatrz się w ulubione piwo
2. 🚶‍♂️ Udaj się na wskazane miejsce przed {satellite_pass['start_time']}
3. 🧭 Ustaw się twarzą w kierunku {satellite_pass['start_compass']}
4. ⏰ O {satellite_pass['max_time']} wznieś toast do nieba
5. 📸 Satelita zrobi Ci zdjęcie z orbity!
6. 🤳 Zrób selfie z toastem i oznacz #SatelliteToast

🌌 <b>WSKAZÓWKI:</b>
• Spójrz pod kątem {satellite_pass['max_elevation']}° nad horyzont
• Satelita będzie wyglądać jak szybko poruszająca się gwiazda
• Nie używaj latarki - pozwól oczom przyzwyczaić się do ciemności
        """
        
        # Dodaj informacje pogodowe jeśli dostępne
        if weather:
            instructions += f"\n🌤️ <b>PROGNOZA NA {satellite_pass['max_time']}:</b>"
            instructions += f"\n• Temperatura: {weather['temp']}°C"
            instructions += f"\n• Zachmurzenie: {weather['clouds']}%"
            instructions += f"\n• Wiatr: {weather['wind_speed']} m/s"
            
            if weather['clouds'] > 70:
                instructions += "\n⚠️ <i>Wysokie zachmurzenie - satelita może być niewidoczna</i>"
            elif weather['clouds'] < 30:
                instructions += "\n✅ <i>Doskonałe warunki do obserwacji!</i>"
        
        # Dodaj informację jeśli to symulacja
        if satellite_pass.get("simulated"):
            instructions += "\n\n⚠️ <i>Uwaga: Używamy symulowanych danych satelitarnych</i>"
        
        return instructions
    
    def get_toast_quote(self):
        """Losowy cytat na toast"""
        quotes = [
            "Do gwiazd i dalej! Za eksplorację kosmosu! 🚀",
            "Piwem w satelitę! Niech grawitacja zawsze będzie z Tobą! 🍻🛰️",
            "Za tych, co patrzą w gwiazdy i marzą o nieosiągalnym! ✨",
            "Toast za niewidzialne wiązania między nami a kosmosem! 🔭",
            "Niech Twoje marzenia będą tak wielkie jak wszechświat! 💫",
            "Za noc pełną cudów i gwiazd spadających! 🌠",
            "Wypijmy za tych, którzy odważyli się spojrzeć w niebo! 👨‍🚀",
            "Za kosmiczną przygodę bez wychodzenia z domu! 🏠🚀"
        ]
        return random.choice(quotes)
    
    def generate_satellite_photo_caption(self, spot, satellite_pass):
        """Wygeneruj podpis do zdjęcia satelitarnego"""
        return f"""
🛰️ <b>ZDJĘCIE SATELITARNE Z TOASTU!</b>

{satellite_pass['satellite_emoji']} <b>Satelita:</b> {satellite_pass['satellite']}
📍 <b>Lokalizacja:</b> {spot['name']}
🕐 <b>Czas:</b> {satellite_pass['max_time']}
📅 <b>Data:</b> {satellite_pass['date']}

🍻 <b>TOAST ODEBRANY NA ORBICIE!</b>
Satelita zarejestrowała Twój kosmiczny gest.
Dziękujemy za udział w eksperymencie #SatelliteToast!

💫 Następny toast już wkrótce!
        """

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
    
    def analyze_toast_conditions(self, city_name, weather_data, satellite_pass):
        """Analizuj warunki toastu przez AI"""
        try:
            prompt = f"""
            Jesteś kosmicznym sommelierem. Oceniasz warunki do "toastu do satelity".
            
            MIASTO: {city_name}
            DATA: {datetime.now().strftime('%Y-%m-%d')}
            GODZINA: {satellite_pass.get('max_time', '21:00')}
            SATELITA: {satellite_pass.get('satellite', 'ISS')}
            
            DANE POGODOWE:
            - Temperatura: {weather_data.get('temp', 0)}°C
            - Zachmurzenie: {weather_data.get('clouds', 0)}%
            - Wiatr: {weather_data.get('wind_speed', 0)} m/s
            - Wilgotność: {weather_data.get('humidity', 0)}%
            
            Oceń toast w skali 1-10 i podaj:
            1. Idealny rodzaj piwa dla tych warunków
            2. Styl toastu (np. "dostojny", "entuzjastyczny")
            3. Krótką wiadomość do satelity (max 10 słów)
            
            Odpowiedz WYŁĄCZNIE w formacie:
            OCENA: X/10 | PIWO: [rodzaj] | STYL: [styl] | WIADOMOŚĆ: [tekst]
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
                
                # Parsuj odpowiedź AI
                analysis = {
                    "score": 7,
                    "beer": "Lager",
                    "style": "Entuzjastyczny",
                    "message": "Za eksplorację kosmosu!",
                    "full_response": ai_text,
                    "source": "DeepSeek AI"
                }
                
                # Parsowanie odpowiedzi
                if "OCENA:" in ai_text:
                    try:
                        score_part = ai_text.split("OCENA:")[1].split("|")[0].strip()
                        analysis["score"] = int(score_part.split("/")[0])
                    except:
                        pass
                
                if "PIWO:" in ai_text:
                    try:
                        beer_part = ai_text.split("PIWO:")[1].split("|")[0].strip()
                        analysis["beer"] = beer_part
                    except:
                        pass
                
                if "STYL:" in ai_text:
                    try:
                        style_part = ai_text.split("STYL:")[1].split("|")[0].strip()
                        analysis["style"] = style_part
                    except:
                        pass
                
                if "WIADOMOŚĆ:" in ai_text:
                    try:
                        msg_part = ai_text.split("WIADOMOŚĆ:")[1].strip()
                        analysis["message"] = msg_part
                    except:
                        pass
                
                return analysis
            else:
                return self._get_fallback_analysis(weather_data)
                
        except Exception as e:
            logger.error(f"❌ Błąd DeepSeek AI: {e}")
            return self._get_fallback_analysis(weather_data)
    
    def _get_fallback_analysis(self, weather_data):
        """Fallback analizy toastu"""
        temp = weather_data.get('temp', 20)
        
        if temp > 25:
            beer = "Chłodny Lager lub Pszeniczne"
            style = "Orzeźwiający"
        elif temp > 15:
            beer = "Amber Ale lub IPA"
            style = "Klimatyczny"
        elif temp > 5:
            beer = "Ciemny Porter lub Stout"
            style = "Dostojny"
        else:
            beer = "Ciepłe Piwo Korzenne"
            style = "Rozgrzewający"
        
        return {
            "score": 8,
            "beer": beer,
            "style": style,
            "message": "Do gwiazd i dalej!",
            "source": "System Fallback"
        }
    
    def get_astronomy_tip(self):
        """Pobierz losową wskazówkę astronomiczną"""
        tips = [
            "Użyj aplikacji SkyView lub Stellarium do identyfikacji obiektów.",
            "Zacznij obserwacje od Księżyca i jasnych planet jak Wenus czy Jowisz.",
            "Unikaj obserwacji przy pełni Księżyca - rozjaśnia niebo.",
            "Poczekaj 20-30 minut po wyjściu, aby oczy przyzwyczaiły się do ciemności.",
            "Użyj czerwonej latarki - nie niszczy noktowizji.",
            "Sprawdź fazę księżyca przed planowaniem obserwacji.",
            "Szukaj miejsc z dala od świateł miejskich.",
            "Zaplanuj obserwacje na bezchmurną noc po północy."
        ]
        return tips[datetime.now().second % len(tips)]

# ====================== INICJALIZACJA MODUŁÓW ======================
mapbox_provider = MapboxProvider(MAPBOX_API_KEY)
toast_module = SatelliteToast(mapbox_provider)
deepseek_ai = DeepSeekAI()

# ====================== BAZA DANYCH ======================
def init_database():
    """Inicjalizacja bazy danych"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabela użytkowników
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            toasts_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela toastów
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS toasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            city TEXT,
            satellite TEXT,
            toast_time TEXT,
            spot_name TEXT,
            success BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def log_toast(chat_id, city, satellite, toast_time, spot_name, success=True):
    """Zapisz toast do bazy danych"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO toasts (chat_id, city, satellite, toast_time, spot_name, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (chat_id, city, satellite, toast_time, spot_name, success))
        
        # Zaktualizuj licznik toastów użytkownika
        cursor.execute('''
            UPDATE users SET toasts_count = toasts_count + 1 WHERE chat_id = ?
        ''', (chat_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Błąd zapisu toastu: {e}")
        return False

def get_user_toasts(chat_id):
    """Pobierz historię toastów użytkownika"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT city, satellite, toast_time, spot_name, created_at 
            FROM toasts 
            WHERE chat_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (chat_id,))
        
        toasts = cursor.fetchall()
        conn.close()
        
        return toasts
    except:
        return []

# ====================== FUNKCJE POMOCNICZE ======================
def get_weather_data(city_key):
    """Pobierz dane pogodowe dla miasta"""
    city = OBSERVATION_CITIES.get(city_key)
    if not city:
        return None
    
    try:
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
            "temp": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": round(data["wind"]["speed"], 1),
            "description": data["weather"][0]["description"],
            "clouds": data["clouds"]["all"],
            "visibility": round(data.get("visibility", 10000) / 1000, 1),
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
        }
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return None

def calculate_moon_phase():
    """Oblicz fazę księżyca"""
    now = datetime.now()
    # Proste obliczenia fazy księżyca
    days_since_new = (now - datetime(2024, 1, 11)).days % 29.53
    
    if days_since_new < 1:
        return {"name": "Nów", "emoji": "🌑", "illumination": 0}
    elif days_since_new < 7.4:
        illum = (days_since_new / 7.4) * 50
        return {"name": "Rosnący sierp", "emoji": "🌒", "illumination": round(illum, 1)}
    elif days_since_new < 14.8:
        return {"name": "Pełnia", "emoji": "🌕", "illumination": 100}
    else:
        illum = 100 - ((days_since_new - 14.8) / 14.73) * 50
        return {"name": "Malejący sierp", "emoji": "🌘", "illumination": round(illum, 1)}

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
    except Exception as e:
        logger.error(f"Telegram photo error: {e}")
        return None

def send_location(chat_id, lat, lon):
    """Wyślij lokalizację"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendLocation"
    payload = {
        "chat_id": chat_id,
        "latitude": lat,
        "longitude": lon
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
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE v14.0 - TOAST EDITION</title>
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
                max-width: 900px;
                margin: 0 auto;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 40px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }
            .toast-animation {
                font-size: 4em;
                margin: 30px 0;
                animation: float 3s ease-in-out infinite;
            }
            @keyframes float {
                0%, 100% { transform: translateY(0) rotate(0deg); }
                33% { transform: translateY(-20px) rotate(5deg); }
                66% { transform: translateY(-10px) rotate(-5deg); }
            }
            .btn {
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(to right, #FFD700, #FFA500);
                color: #000;
                text-decoration: none;
                border-radius: 15px;
                font-weight: bold;
                margin: 15px;
                transition: all 0.3s;
                border: 2px solid rgba(255,255,255,0.3);
                font-size: 16px;
            }
            .btn:hover { 
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(255, 215, 0, 0.4);
            }
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 40px 0;
            }
            .status-card {
                background: rgba(0,0,0,0.3);
                padding: 20px;
                border-radius: 15px;
                text-align: center;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .city-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 30px 0;
            }
            .city-card {
                background: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 10px;
                font-size: 1.2em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="toast-animation">🍻🛰️✨</div>
            <h1>🤖 SENTRY ONE v14.0</h1>
            <h2>TOAST EDITION 🍻🚀</h2>
            <h3>Wyjdź z piwem, znajdź miejsce, wznieś toast do satelity!</h3>
            
            <div class="status-grid">
                <div class="status-card">
                    <h4>🗺️ Mapbox</h4>
                    <p>''' + ('✅ Aktywny' if mapbox_provider.available else '❌ Brak klucza') + '''</p>
                </div>
                <div class="status-card">
                    <h4>🧠 DeepSeek AI</h4>
                    <p>''' + ('✅ Online' if deepseek_ai.available else '❌ Offline') + '''</p>
                </div>
                <div class="status-card">
                    <h4>🛰️ Satelity</h4>
                    <p>''' + str(len(SATELLITES)) + ''' dostępnych</p>
                </div>
                <div class="status-card">
                    <h4>📍 Miasta</h4>
                    <p>''' + str(len(OBSERVATION_CITIES)) + ''' dostępne</p>
                </div>
            </div>
            
            <div style="margin: 40px 0;">
                <h3>🍻 Jak działa Toast do Satelity?</h3>
                <p>1. Użyj komendy <code>/toast [miasto]</code></p>
                <p>2. Bot znajdzie przelot satelity nad Twoim miastem</p>
                <p>3. Wskaże Ci idealne miejsce i godzinę</p>
                <p>4. Wyjdź z piwem i wznieś toast do satelity!</p>
                <p>5. Otrzymasz "zdjęcie satelitarne" z toastu! 🛰️📸</p>
            </div>
            
            <div class="city-grid">
                <div class="city-card">🏛️ Warszawa</div>
                <div class="city-card">🌲 Koszalin</div>
                <div class="city-card">🐉 Kraków</div>
            </div>
            
            <div style="margin: 40px 0;">
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
            
            <div style="background: rgba(255,215,0,0.1); padding: 25px; border-radius: 15px; margin: 30px 0;">
                <h4>🚀 System aktywny!</h4>
                <p>Ping count: ''' + str(ping_count) + ''' | Ostatni ping: ''' + last_ping_time.strftime('%H:%M:%S') + '''</p>
                <p>Gotowość toastowa: <span style="color: #FFD700;">100%</span></p>
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
        "version": "14.0 Toast Edition",
        "services": {
            "mapbox": mapbox_provider.available,
            "deepseek_ai": deepseek_ai.available,
            "nasa_api": bool(NASA_API_KEY),
            "telegram_bot": True
        },
        "statistics": {
            "cities": len(OBSERVATION_CITIES),
            "satellites": len(SATELLITES),
            "ping_count": ping_count,
            "mapbox_status": "active" if mapbox_provider.available else "inactive"
        }
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
        "message": "Toast system ready! 🍻🛰️"
    })

# ====================== WEBHOOK I KOMENDY ======================
@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook Telegram - główny endpoint"""
    global last_ping_time, ping_count
    
    try:
        data = request.get_json()
        logger.info(f"📩 Webhook odebrany od Telegrama")
        
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()
            
            # Obsługa komend
            if text.startswith("/"):
                handle_command(chat_id, text.lower())
            else:
                # Obsługa wiadomości tekstowych
                handle_text_message(chat_id, text)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"🔥 Błąd webhook: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def handle_command(chat_id, command):
    """Obsłuż komendę od użytkownika"""
    
    if command == "/start":
        welcome = f"""
🤖 <b>SENTRY ONE v14.0 - TOAST EDITION</b>

🍻 <b>NOWOŚĆ: TOAST DO SATELITY!</b>
Wyjdź z piwem, znajdź miejsce, wznieś toast do satelity na orbicie!

<b>🌍 DOSTĘPNE MIASTA:</b>
🏛️ Warszawa - <code>/toast warszawa</code>
🌲 Koszalin - <code>/toast koszalin</code>
🐉 Kraków - <code>/toast krakow</code>

<b>📋 GŁÓWNE KOMENDY:</b>
<code>/toast [miasto]</code> - Zaplanuj toast do satelity
<code>/weather [miasto]</code> - Sprawdź pogodę
<code>/moon</code> - Faza księżyca
<code>/nasa</code> - Zdjęcie dnia NASA
<code>/help</code> - Wszystkie komendy

<b>🎯 TYDZIEŃ PRÓBNY:</b>
• Mapbox: {'✅ Aktywny' if mapbox_provider.available else '❌ Brak'}
• DeepSeek AI: {'✅ Online' if deepseek_ai.available else '❌ Offline'}

🚀 <b>Gotów na kosmiczny toast?</b>
        """
        send_telegram_message(chat_id, welcome)
    
    elif command == "/help":
        help_text = """
🍻 <b>SENTRY ONE - TOAST EDITION - WSZYSTKIE KOMENDY</b>

<b>🛰️ KOMENDY TOASTU:</b>
<code>/toast warszawa</code> - Zaplanuj toast w Warszawie
<code>/toast koszalin</code> - Zaplanuj toast w Koszalinie
<code>/toast krakow</code> - Zaplanuj toast w Krakowie
<code>/toast_quote</code> - Losowy cytat na toast
<code>/my_toasts</code> - Twoja historia toastów

<b>🌤️ POGODA I ASTRONOMIA:</b>
<code>/weather warszawa</code> - Pogoda dla Warszawy
<code>/weather koszalin</code> - Pogoda dla Koszalina
<code>/weather krakow</code> - Pogoda dla Krakowa
<code>/moon</code> - Aktualna faza księżyca
<code>/nasa</code> - Astronomy Picture of the Day

<b>🗺️ MAPY I LOKALIZACJA:</b>
<code>/map warszawa</code> - Mapa Warszawy (zdjęcie satelitarne)
<code>/map koszalin</code> - Mapa Koszalina
<code>/map krakow</code> - Mapa Krakowa

<b>🧠 AI I SYSTEM:</b>
<code>/ai_tip</code> - Wskazówka od AI
<code>/status</code> - Status systemu
<code>/ping</code> - Test połączenia
<code>/satellites</code> - Lista śledzonych satelit

<b>📍 PRZYKŁAD:</b> <code>/toast warszawa</code>
        """
        send_telegram_message(chat_id, help_text)
    
    elif command.startswith("/toast "):
        parts = command.split()
        if len(parts) == 2 and parts[1] in OBSERVATION_CITIES:
            city_key = parts[1]
            city = OBSERVATION_CITIES[city_key]
            
            # Pobierz przelot satelity
            satellite_pass = toast_module.get_next_satellite_pass(city_key)
            
            if satellite_pass and satellite_pass.get("success"):
                # Wybierz miejsce
                spot = toast_module.generate_toast_spot(city_key)
                
                # Pobierz pogodę
                weather = get_weather_data(city_key)
                
                # Generuj instrukcje
                instructions = toast_module.get_toast_instructions(
                    city_key, satellite_pass, spot, weather
                )
                
                # Dodaj analizę AI jeśli dostępna
                if deepseek_ai.available and weather:
                    ai_analysis = deepseek_ai.analyze_toast_conditions(
                        city["name"], weather, satellite_pass
                    )
                    
                    instructions += f"\n🧠 <b>ANALIZA DEEPSEEK AI:</b>\n"
                    instructions += f"• Ocena toastu: {ai_analysis['score']}/10\n"
                    instructions += f"• Idealne piwo: {ai_analysis['beer']}\n"
                    instructions += f"• Styl: {ai_analysis['style']}\n"
                    instructions += f"• Wiadomość do satelity: \"{ai_analysis['message']}\"\n"
                
                # Dodaj cytat
                instructions += f"\n💫 <b>CYTAT NA TOAST:</b>\n{toast_module.get_toast_quote()}"
                
                # Wyślij główną wiadomość
                send_telegram_message(chat_id, instructions)
                
                # Wyślij lokalizację miejsca
                send_location(chat_id, spot["lat"], spot["lon"])
                
                # Zapisz toast w bazie
                log_toast(chat_id, city["name"], satellite_pass["satellite"], 
                         satellite_pass["max_time"], spot["name"])
                
                # Zaplanuj wysłanie "zdjęcia satelitarnego" (po 8 sekundach)
                threading.Timer(8.0, send_satellite_photo, args=[chat_id, spot, satellite_pass]).start()
                
            else:
                error_msg = f"""
❌ <b>BRAK SATELITY W ZASIĘGU!</b>

W {city['name']} nie ma widocznych przelotów satelitów w ciągu najbliższych 24h.

🍻 <b>Alternatywny plan:</b>
1. Weź piwo i wyjdź na zewnątrz o 21:00
2. Znajdź miejsce z widokiem na niebo
3. Wznieś toast do gwiazd
4. Satelity i tak Cię widzą! 🛰️

💫 Spróbuj ponownie jutro lub użyj <code>/weather {city_key}</code>.
                """
                send_telegram_message(chat_id, error_msg)
        else:
            cities = ", ".join([f"<code>/toast {k}</code>" for k in OBSERVATION_CITIES.keys()])
            send_telegram_message(chat_id, f"❌ Dostępne miasta: {cities}")
    
    elif command == "/toast_quote":
        quote = toast_module.get_toast_quote()
        send_telegram_message(chat_id, f"💫 <b>CYTAT NA TOAST:</b>\n\n{quote}")
    
    elif command == "/my_toasts":
        toasts = get_user_toasts(chat_id)
        if toasts:
            response = "📜 <b>TWOJA HISTORIA TOASTÓW:</b>\n\n"
            for i, (city, satellite, toast_time, spot_name, created_at) in enumerate(toasts, 1):
                date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d.%m %H:%M")
                response += f"{i}. {date} - {city}\n"
                response += f"   🛰️ {satellite}\n"
                response += f"   📍 {spot_name}\n"
                response += f"   ⏰ {toast_time}\n\n"
            
            response += f"🍻 Łączna liczba toastów: {len(toasts)}"
        else:
            response = "📜 <b>Jeszcze nie wzniósłeś żadnego toastu!</b>\n\nUżyj <code>/toast [miasto]</code> aby rozpocząć!"
        
        send_telegram_message(chat_id, response)
    
    elif command.startswith("/weather"):
        parts = command.split()
        if len(parts) == 2 and parts[1] in OBSERVATION_CITIES:
            city_key = parts[1]
            city = OBSERVATION_CITIES[city_key]
            weather = get_weather_data(city_key)
            
            if weather:
                # Pobierz fazę księżyca
                moon = calculate_moon_phase()
                
                response = f"""
{city['emoji']} <b>POGODA - {city['name'].upper()}</b>

🌡️ Temperatura: {weather['temp']}°C
🌡️ Odczuwalna: {weather['feels_like']}°C
💨 Wiatr: {weather['wind_speed']} m/s
💧 Wilgotność: {weather['humidity']}%
☁️ Zachmurzenie: {weather['clouds']}%
👁️ Widoczność: {weather['visibility']} km
🌅 Wschód: {weather['sunrise']} | 🌇 Zachód: {weather['sunset']}

{moon['emoji']} <b>Księżyc:</b> {moon['name']} ({moon['illumination']}%)

📱 <b>OCENA WARUNKÓW DO TOASTU:</b>
• Zachmurzenie: {'✅ Niskie' if weather['clouds'] < 30 else '⚠️ Umiarkowane' if weather['clouds'] < 70 else '❌ Wysokie'}
• Temperatura: {'✅ Idealna na piwo!' if 10 <= weather['temp'] <= 25 else '🧥 Weź kurtkę!' if weather['temp'] < 10 else '🥶 Zimne piwo!'}
• Wiatr: {'✅ Łagodny' if weather['wind_speed'] < 5 else '⚠️ Umiarkowany' if weather['wind_speed'] < 10 else '❌ Silny'}

🍻 <b>NAJLEPSZY CZAS NA TOAST:</b> 1-2 godziny po zachodzie słońca

Użyj <code>/toast {city_key}</code> aby zaplanować toast!
                """
                send_telegram_message(chat_id, response)
            else:
                send_telegram_message(chat_id, f"❌ Nie udało się pobrać pogody dla {city['name']}")
        else:
            cities = ", ".join([f"<code>/weather {k}</code>" for k in OBSERVATION_CITIES.keys()])
            send_telegram_message(chat_id, f"❌ Dostępne miasta: {cities}")
    
    elif command.startswith("/map"):
        parts = command.split()
        if len(parts) == 2 and parts[1] in OBSERVATION_CITIES:
            city_key = parts[1]
            city = OBSERVATION_CITIES[city_key]
            
            # Pobierz zdjęcie satelitarne miasta
            image_url = mapbox_provider.get_satellite_image(city["lat"], city["lon"], zoom=12)
            
            caption = f"""
🗺️ <b>MAPA SATELITARNA - {city['name'].upper()}</b>

📍 Lokalizacja: {city['name']}, {city['country']}
🌐 Współrzędne: {city['lat']:.4f}°, {city['lon']:.4f}°
🛰️ Źródło: Mapbox Satellite

🍻 <b>Miejsca do toastu w {city['name']}:</b>
"""
            # Dodaj miejsca do toastu
            for i, spot in enumerate(city.get("toast_spots", [])[:3], 1):
                caption += f"\n{i}. {spot.get('emoji', '📍')} <b>{spot['name']}</b>"
                caption += f"\n   {spot['desc']}"
            
            caption += f"\n\nUżyj <code>/toast {city_key}</code> aby zaplanować toast w tym mieście!"
            
            send_photo(chat_id, image_url, caption)
        else:
            cities = ", ".join([f"<code>/map {k}</code>" for k in OBSERVATION_CITIES.keys()])
            send_telegram_message(chat_id, f"❌ Dostępne miasta: {cities}")
    
    elif command == "/moon":
        moon = calculate_moon_phase()
        response = f"""
{moon['emoji']} <b>FAZA KSIĘŻYCA</b>

• Nazwa: {moon['name']}
• Oświetlenie: {moon['illumination']}%

<b>WPŁYW NA OBSERWACJE:</b>
• {moon['name']} {'❌ utrudnia obserwacje' if moon['illumination'] > 70 else '✅ sprzyja obserwacjom' if moon['illumination'] < 30 else '⚠️ częściowo utrudnia'}
• Najlepszy czas: 3 dni przed i po nowiu
• Unikaj pełni dla obserwacji gwiazd

<b>DOBRZE NA TOAST GDY:</b>
• Księżyc nie jest w pełni
• Bezchmurne niebo
• Po zachodzie słońca

🌌 <b>Sprawdź warunki:</b> <code>/weather [miasto]</code>
        """
        send_telegram_message(chat_id, response)
    
    elif command == "/nasa":
        apod = get_nasa_apod()
        if apod and apod.get("url"):
            caption = f"""
🛰️ <b>NASA ASTRONOMY PICTURE OF THE DAY</b>

<b>{apod['title']}</b>
📅 {apod['date']}

{apod['explanation'][:300]}...
            """
            send_photo(chat_id, apod['url'], caption)
        else:
            # Fallback na losowe zdjęcie kosmosu
            space_images = [
                "https://images.unsplash.com/photo-1446776653964-20c1d3a81b06?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1465101162946-4377e57745c3?w=800&h=600&fit=crop"
            ]
            send_photo(chat_id, random.choice(space_images), "🛰️ <b>NASA INSPIRACJA</b>\n\nDzisiejsze zdjęcie kosmosu dla Ciebie!")
    
    elif command == "/ai_tip":
        tip = deepseek_ai.get_astronomy_tip()
        send_telegram_message(chat_id, f"🧠 <b>WSKAZÓWKA ASTRONOMICZNA OD AI:</b>\n\n{tip}")
    
    elif command == "/satellites":
        response = "🛰️ <b>SATELITY ŚLEDZONE PRZEZ SYSTEM:</b>\n\n"
        for key, sat in SATELLITES.items():
            response += f"{sat['emoji']} <b>{sat['name']}</b>\n"
            response += f"   Typ: {sat['type']}\n"
            response += f"   ID: {sat['id']}\n\n"
        
        response += "ℹ️ System automatycznie wybiera satelitę nadlatującą nad Twoje miasto."
        send_telegram_message(chat_id, response)
    
    elif command == "/status":
        response = f"""
📊 <b>STATUS SYSTEMU SENTRY ONE v14.0</b>

🤖 Telegram Bot: ✅ AKTYWNY
🗺️ Mapbox API: {'✅ AKTYWNY' if mapbox_provider.available else '❌ BRAK KLUCZA'}
🧠 DeepSeek AI: {'✅ ONLINE' if deepseek_ai.available else '❌ OFFLINE'}
🛰️ Satelity: {len(SATELLITES)} śledzonych
📍 Miasta: {len(OBSERVATION_CITIES)} dostępne

📡 <b>STATYSTYKI:</b>
• Ping count: {ping_count}
• Ostatni ping: {last_ping_time.strftime('%H:%M:%S')}
• Wersja: Toast Edition v14.0

🍻 <b>GOTOWOŚĆ TOASTOWA:</b> 100%
🚀 <b>Użyj:</b> <code>/toast [miasto]</code>
        """
        send_telegram_message(chat_id, response)
    
    elif command == "/ping":
        send_telegram_message(chat_id, f"🏓 <b>PONG!</b> System toastowy aktywny! Ping #{ping_count}")
    
    else:
        send_telegram_message(chat_id, "❌ Nieznana komenda. Użyj /help aby zobaczyć dostępne komendy.")

def handle_text_message(chat_id, text):
    """Obsłuż wiadomość tekstową"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["piwo", "beer", "toast", "satelita", "kosmos"]):
        response = random.choice([
            "Mówisz o piwie? 🍻 Użyj /toast [miasto] aby zaplanować toast do satelity!",
            "Chcesz wznieść toast? 🚀 Sprawdź najpierw /weather [miasto]!",
            "Rozmawiamy o kosmosie? 🛰️ Spróbuj /nasa dla dzisiejszego zdjęcia NASA!",
            "Toast do satelity? To mój ulubiony temat! 🍻🛰️"
        ])
        send_telegram_message(chat_id, response)
    
    elif "dziękuję" in text_lower or "thanks" in text_lower:
        send_telegram_message(chat_id, "🤖 Nie ma za co! Miłego toastu! 🍻")
    
    elif "pogoda" in text_lower:
        send_telegram_message(chat_id, "🌤️ Sprawdź pogodę komendą: /weather [miasto]")
    
    else:
        # Domyślna odpowiedź
        send_telegram_message(chat_id, "🤖 Użyj /help aby zobaczyć dostępne komendy. 🍻🚀")

def send_satellite_photo(chat_id, spot, satellite_pass):
    """Wyślij symulowane zdjęcie satelitarne"""
    try:
        # Spróbuj pobrać prawdziwe zdjęcie satelitarne z Mapbox
        image_url = mapbox_provider.get_satellite_image(spot["lat"], spot["lon"])
        
        # Generuj podpis
        caption = toast_module.generate_satellite_photo_caption(spot, satellite_pass)
        
        # Wyślij zdjęcie
        result = send_photo(chat_id, image_url, caption)
        
        # Jeśli nie udało się wysłać, wyślij wiadomość tekstową
        if not result or result.get("ok") != True:
            send_telegram_message(chat_id, "🛰️📸 <b>Satelita zrobiła Ci zdjęcie!</b>\n\nNiestety nie mogę wysłać zdjęcia teraz, ale Twój toast został odebrany na orbicie! 🍻")
            
    except Exception as e:
        logger.error(f"Błąd wysyłania zdjęcia: {e}")
        send_telegram_message(chat_id, "🛰️ <b>TOAST ODEBRANY NA ORBICIE!</b>\n\nSatelita zarejestrowała Twój kosmiczny gest! Dziękujemy! 🍻🚀")

# ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 URUCHAMIANIE SENTRY ONE v14.0 - TOAST EDITION")
    print("=" * 70)
    print(f"🗺️  Mapbox: {'✅ Aktywny' if mapbox_provider.available else '❌ Brak klucza'}")
    print(f"🧠 DeepSeek AI: {'✅ Dostępny' if deepseek_ai.available else '❌ Niedostępny'}")
    print(f"🛰️ Satelity: {len(SATELLITES)} dostępnych")
    print(f"📍 Miasta: {len(OBSERVATION_CITIES)} dostępne")
    print(f"🌐 Webhook URL: {WEBHOOK_URL}")
    print(f"🔧 Port: {PORT}")
    print("=" * 70)
    print("🍻 System gotowy na kosmiczne toasty! 🚀")
    print("=" * 70)
    
    # Uruchom Flask
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )