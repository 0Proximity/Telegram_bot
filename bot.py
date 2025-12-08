#!/usr/bin/env python3
"""
🤖 SENTRY ONE - FINAL VERSION with Auto-Ping
Render.com Telegram Bot with Keep-Alive
"""

import os
import json
import time
import logging
import threading
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler

# ====================== KONFIGURACJA ======================
TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
RENDER_URL = "https://telegram-bot-szxa.onrender.com"
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"
PING_INTERVAL = 300  # 5 minut (300 sekund)

print("=" * 60)
print("🤖 SENTRY ONE - TELEGRAM BOT")
print(f"🌐 URL: {RENDER_URL}")
print(f"🔗 Webhook: {WEBHOOK_URL}")
print(f"⏰ Ping interval: {PING_INTERVAL}s")
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
    "synergic": {"name": "Synergic", "status": "online", "type": "computer", "icon": "💻"}
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
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 SENTRY ONE - Telegram Bot</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
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
            .agent-name {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .agent-status {{
                padding: 3px 10px;
                border-radius: 15px;
                font-size: 14px;
                display: inline-block;
            }}
            .online {{
                background: #d4edda;
                color: #155724;
            }}
            .offline {{
                background: #f8d7da;
                color: #721c24;
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
            .stat-value {{
                font-size: 36px;
                font-weight: bold;
                color: #667eea;
            }}
            .ping-card {{
                background: #e3f2fd;
                border-left: 5px solid #2196F3;
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
            .bot-link:hover {{
                background: #764ba2;
            }}
            .endpoints {{
                background: #f1f3f4;
                padding: 15px;
                border-radius: 12px;
                margin-top: 20px;
                font-family: monospace;
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
            .ping-active {{
                color: #4CAF50;
                font-weight: bold;
            }}
            .ping-inactive {{
                color: #f44336;
            }}
            .progress-bar {{
                height: 10px;
                background: #e0e0e0;
                border-radius: 5px;
                margin: 10px 0;
                overflow: hidden;
            }}
            .progress-fill {{
                height: 100%;
                background: #4CAF50;
                width: 0%;
                transition: width 0.5s;
            }}
        </style>
        <script>
            function updatePingProgress() {{
                const interval = {PING_INTERVAL};
                const startTime = Date.now();
                
                function update() {{
                    const elapsed = (Date.now() - startTime) % interval;
                    const percentage = (elapsed / interval) * 100;
                    document.getElementById('progress-fill').style.width = percentage + '%';
                    
                    const remaining = Math.max(0, Math.floor((interval - elapsed) / 1000));
                    document.getElementById('next-ping').innerText = remaining + 's';
                }}
                
                setInterval(update, 1000);
                update();
            }}
            
            function refreshPingStats() {{
                fetch('/pingstats')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('ping-count').innerText = data.ping_count;
                        document.getElementById('last-ping').innerText = data.last_ping || 'Nigdy';
                        document.getElementById('ping-status').innerText = 
                            data.is_running ? '🟢 AKTYWNE' : '🔴 NIEAKTYWNE';
                        document.getElementById('ping-status').className = 
                            data.is_running ? 'ping-active' : 'ping-inactive';
                    }});
            }}
            
            // Automatyczne odświeżanie co 30 sekund
            document.addEventListener('DOMContentLoaded', function() {{
                updatePingProgress();
                refreshPingStats();
                setInterval(refreshPingStats, 30000);
                setInterval(updatePingProgress, 30000);
            }});
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 42px; margin-bottom: 10px;">🤖 SENTRY ONE</h1>
                <h2 style="color: #666;">Universal AI Ecosystem with Auto-Ping</h2>
                <div class="status-badge">🟢 SYSTEM ONLINE</div>
                <p>Telegram Bot hostowany na <strong>Render.com</strong> z auto-pingowaniem</p>
            </div>
            
            <a href="https://t.me/PcSentintel_Bot" class="bot-link" target="_blank">
                💬 Otwórz @PcSentintel_Bot w Telegramie
            </a>
            
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
                <div class="stat-card ping-card">
                    <div class="stat-value" id="ping-count">0</div>
                    <div>Pingów wysłanych</div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>📡 System Pingowania</h3>
                <p>Status: <span id="ping-status" class="ping-active">🟢 AKTYWNE</span></p>
                <p>Ostatni ping: <span id="last-ping" class="timestamp">Ładowanie...</span></p>
                <p>Następny ping za: <span id="next-ping">--</span> sekund</p>
                <p>Interwał: {PING_INTERVAL/60} minut</p>
                
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                
                <p><small>Pingowanie utrzymuje aplikację aktywną na darmowym planie Render</small></p>
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
            <h2>📋 Dostępne komendy w Telegram</h2>
            <div class="command">/start - Informacje o bocie</div>
            <div class="command">/status - Status systemu</div>
            <div class="command">/agents - Lista agentów</div>
            <div class="command">/test - Test połączenia</div>
            <div class="command">/ping - Statystyki pingowania</div>
            <div class="command">/echo [wiadomość] - Powtórz wiadomość</div>
            
            <h2>🔧 Informacje techniczne</h2>
            <div class="endpoints">
                <div><strong>Bot Token:</strong> {TOKEN[:10]}...</div>
                <div><strong>Webhook URL:</strong> {WEBHOOK_URL}</div>
                <div><strong>Render URL:</strong> {RENDER_URL}</div>
                <div><strong>Port:</strong> {PORT}</div>
                <div><strong>Start Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
            </div>
            
            <h2>📡 Endpointy API</h2>
            <div class="endpoints">
                <div><strong>GET</strong> <a href="/">/</a> - Ten dashboard</div>
                <div><strong>GET</strong> <a href="/health">/health</a> - Status zdrowia</div>
                <div><strong>GET</strong> <a href="/ping">/ping</a> - Ręczne pingowanie</div>
                <div><strong>GET</strong> <a href="/pingstats">/pingstats</a> - Statystyki pingów</div>
                <div><strong>GET</strong> <a href="/dashboard">/dashboard</a> - Dashboard JSON</div>
                <div><strong>GET</strong> <a href="/setwebhook">/setwebhook</a> - Ustaw webhook</div>
                <div><strong>POST</strong> /webhook - Endpoint dla Telegrama</div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; color: #666; padding-top: 20px; border-top: 1px solid #eee;">
                <p>🤖 SENTRY ONE v3.0 | Render.com | Auto-Ping System</p>
                <p>🔗 <a href="{RENDER_URL}">{RENDER_URL}</a> | ⏰ Uptime: <span id="uptime">0s</span></p>
                <script>
                    // Uptime counter
                    const startTime = Date.now();
                    setInterval(() => {{
                        const uptime = Math.floor((Date.now() - startTime) / 1000);
                        document.getElementById('uptime').innerText = 
                            Math.floor(uptime / 3600) + 'h ' + 
                            Math.floor((uptime % 3600) / 60) + 'm ' + 
                            (uptime % 60) + 's';
                    }}, 1000);
                </script>
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
        "service": "sentry-one-telegram-bot",
        "platform": "render.com",
        "bot": "online",
        "webhook": WEBHOOK_URL,
        "timestamp": datetime.now().isoformat(),
        "ping_count": ping_service.ping_count
    })

# Ręczne pingowanie
@app.route('/ping')
def manual_ping():
    """Ręczne wywołanie pingowania"""
    try:
        # Wykonaj ping
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
            "name": "SENTRY ONE",
            "version": "3.0",
            "platform": "Render.com",
            "status": "online",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "bot": {
            "username": "PcSentintel_Bot",
            "mode": "webhook",
            "webhook_url": WEBHOOK_URL
        },
        "ping_system": ping_service.get_stats(),
        "agents": AGENTS,
        "statistics": {
            "total_agents": len(AGENTS),
            "online_agents": online_count,
            "offline_agents": len(AGENTS) - online_count,
            "online_percentage": round((online_count / len(AGENTS)) * 100, 1)
        }
    })

# Ustaw webhook
@app.route('/setwebhook')
def set_webhook():
    """Ustaw webhook dla Telegrama"""
    try:
        # Usuń istniejący webhook
        delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        requests.get(delete_url)
        
        # Ustaw nowy webhook
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

# Sprawdź webhook
@app.route('/getwebhook')
def get_webhook():
    """Sprawdź status webhooka"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
        response = requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint webhook dla Telegrama
@app.route('/webhook', methods=['POST'])
def webhook():
    """Główny endpoint dla webhook Telegram"""
    try:
        # Pobierz dane z requesta
        data = request.get_json()
        
        # Loguj otrzymane dane (opcjonalnie)
        logger.info(f"📥 Otrzymano webhook od Telegram")
        
        # Sprawdź czy to wiadomość
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            # Obsługa komend
            if text.startswith("/start"):
                response_text = (
                    "🤖 <b>SENTRY ONE v3.0</b>\n\n"
                    "Witaj! Jestem botem SENTRY ONE z systemem auto-pingowania!\n\n"
                    "<b>Dostępne komendy:</b>\n"
                    "/start - Informacje\n"
                    "/status - Status systemu\n"
                    "/agents - Lista agentów\n"
                    "/test - Test połączenia\n"
                    "/ping - Statystyki pingowania\n"
                    "/echo [tekst] - Powtórz tekst\n\n"
                    "<i>🌐 Platforma: Render.com</i>\n"
                    "<i>⏰ Auto-ping: Aktywny co 5 minut</i>"
                )
                send_telegram_message(chat_id, response_text)
                
            elif text.startswith("/status"):
                online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
                ping_stats = ping_service.get_stats()
                
                response_text = (
                    f"📊 <b>STATUS SYSTEMU</b>\n\n"
                    f"• Platforma: Render.com\n"
                    f"• Bot: ✅ Działa\n"
                    f"• Tryb: Webhook\n"
                    f"• Agenty: {online_count}/{len(AGENTS)} online\n"
                    f"• Pingowanie: {'🟢 Aktywne' if ping_stats['is_running'] else '🔴 Nieaktywne'}\n"
                    f"• Pingów wysłano: {ping_stats['ping_count']}\n"
                    f"• URL: {RENDER_URL}\n\n"
                    f"<i>Wszystkie systemy sprawne!</i>"
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
                
            elif text.startswith("/test"):
                response_text = (
                    "✅ <b>TEST POŁĄCZENIA</b>\n\n"
                    "Wszystkie systemy sprawne!\n"
                    f"• Bot: Działa\n• Webhook: Aktywny\n• Platforma: Render.com\n• URL: {RENDER_URL}"
                )
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
                # Domyślna odpowiedź na nieznane komendy
                response_text = (
                    "❓ <b>Nieznana komenda</b>\n\n"
                    "Użyj jednej z dostępnych komend:\n"
                    "/start - Informacje\n"
                    "/status - Status systemu\n"
                    "/agents - Lista agentów\n"
                    "/test - Test połączenia\n"
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
    print(f"🚀 Uruchamianie SENTRY ONE v3.0 na Render...")
    print(f"🌐 URL: {RENDER_URL}")
    print(f"🔗 Webhook: {WEBHOOK_URL}")
    print(f"🔑 Token: {TOKEN[:10]}...")
    
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