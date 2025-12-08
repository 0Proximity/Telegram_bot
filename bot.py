#!/usr/bin/env python3
"""
🤖 SENTRY ONE - Telegram Bot dla Render.com
Webhook Mode - Stabilny i niezawodny
"""

import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request, jsonify, render_template_string

# ====================== KONFIGURACJA ======================
TOKEN = os.getenv("TELEGRAM_TOKEN", "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-bot-szxa.onrender.com")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"

print("=" * 50)
print(f"🚀 STARTUJE SENTRY ONE NA RENDER")
print(f"📱 Bot: @PcSentintel_Bot")
print(f"🌐 URL: {RENDER_URL}")
print(f"🔗 Webhook: {WEBHOOK_URL}")
print("=" * 50)

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

# ====================== TELEGRAM BOT ======================
application = Application.builder().token(TOKEN).build()

# Handler dla /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"🤖 <b>SENTRY ONE v2.0</b>\n\n"
        f"Witaj, {user.first_name}!\n\n"
        f"<b>Platforma:</b> Render.com\n"
        f"<b>Tryb:</b> Webhook\n"
        f"<b>Status:</b> ✅ Działa\n\n"
        f"<b>Dostępne komendy:</b>\n"
        f"/start - Informacje\n"
        f"/help - Pomoc\n"
        f"/status - Status systemu\n"
        f"/agents - Lista agentów\n"
        f"/test - Test połączenia\n"
        f"/webhook - Info o webhook\n\n"
        f"<i>Bot URL: {RENDER_URL}</i>"
    )

# Handler dla /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 <b>POMOC - SENTRY ONE</b>\n\n"
        "<b>Komendy:</b>\n"
        "• /start - Informacje startowe\n"
        "• /help - Ta wiadomość\n"
        "• /status - Status systemu\n"
        "• /agents - Lista agentów\n"
        "• /test - Test działania\n"
        "• /webhook - Informacje o webhook\n\n"
        "<b>Agenty:</b>\n"
        "• 📱 Echo - Telefon\n"
        "• 📟 Vector - Tablet\n"
        "• 🕶️ Visor - Oculus\n"
        "• 💻 Synergic - Komputer\n\n"
        "<i>Bot hostowany na Render.com</i>",
        parse_mode='HTML'
    )

# Handler dla /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
    
    status_text = (
        "📊 <b>STATUS SYSTEMU</b>\n\n"
        f"<b>Platforma:</b> Render.com\n"
        f"<b>Bot:</b> @PcSentintel_Bot\n"
        f"<b>Tryb:</b> Webhook\n"
        f"<b>URL:</b> {RENDER_URL}\n\n"
        f"<b>Agenty ({online_count}/{len(AGENTS)} online):</b>\n"
    )
    
    for agent_id, agent in AGENTS.items():
        status_emoji = "🟢" if agent["status"] == "online" else "🔴"
        status_text += f"{status_emoji} {agent['icon']} <b>{agent['name']}</b> - {agent['type']}\n"
    
    status_text += f"\n<i>Uptime: Render.com gwarantuje 99%</i>"
    
    await update.message.reply_html(status_text)

# Handler dla /agents
async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agents_text = "👥 <b>LISTA AGENTÓW</b>\n\n"
    
    for agent_id, agent in AGENTS.items():
        status_color = "🟢 ONLINE" if agent["status"] == "online" else "🔴 OFFLINE"
        agents_text += (
            f"{agent['icon']} <b>{agent['name']}</b>\n"
            f"  • Typ: {agent['type']}\n"
            f"  • Status: {status_color}\n"
            f"  • ID: {agent_id}\n\n"
        )
    
    agents_text += "<i>Użyj /status dla podsumowania</i>"
    
    await update.message.reply_html(agents_text)

# Handler dla /test
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ <b>TEST POŁĄCZENIA</b>\n\n"
        "Wszystkie systemy sprawne!\n"
        f"• Bot: Działa\n• Webhook: Aktywny\n• Platforma: Render.com\n• URL: {RENDER_URL}",
        parse_mode='HTML'
    )

# Handler dla /webhook
async def webhook_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    webhook_info = await application.bot.get_webhook_info()
    
    info_text = (
        "🔗 <b>INFORMACJE O WEBHOOK</b>\n\n"
        f"<b>URL:</b> {webhook_info.url or 'Nie ustawiony'}\n"
        f"<b>Status:</b> {'Aktywny ✅' if webhook_info.url else 'Nieaktywny ❌'}\n"
        f"<b>Oczekujące:</b> {webhook_info.pending_update_count}\n"
        f"<b>Ostatni błąd:</b> {webhook_info.last_error_message or 'Brak'}\n\n"
        f"<i>Twój webhook URL: {WEBHOOK_URL}</i>"
    )
    
    await update.message.reply_html(info_text)

# Handler dla /echo
async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args) if context.args else "Brak wiadomości"
    await update.message.reply_text(f"📣 Echo: {text}")

# Handler dla /set
async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Użycie: /set <agent> <online/offline>")
        return
    
    agent_id = context.args[0].lower()
    status = context.args[1].lower()
    
    if agent_id not in AGENTS:
        await update.message.reply_text(f"❌ Nieznany agent: {agent_id}")
        return
    
    if status not in ["online", "offline"]:
        await update.message.reply_text("❌ Status musi być 'online' lub 'offline'")
        return
    
    AGENTS[agent_id]["status"] = status
    await update.message.reply_text(f"✅ {AGENTS[agent_id]['name']} ustawiony na {status}")

# Dodaj wszystkie handlery
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("status", status_command))
application.add_handler(CommandHandler("agents", agents_command))
application.add_handler(CommandHandler("test", test_command))
application.add_handler(CommandHandler("webhook", webhook_command))
application.add_handler(CommandHandler("echo", echo_command))
application.add_handler(CommandHandler("set", set_command))

# ====================== FLASK APP ======================
app = Flask(__name__)

# Strona główna - Dashboard
@app.route('/')
def home():
    online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
    
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
                max-width: 1000px;
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
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 36px;
                font-weight: bold;
                color: #667eea;
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="font-size: 42px; margin-bottom: 10px;">🤖 SENTRY ONE</h1>
                <h2 style="color: #666;">Universal AI Ecosystem</h2>
                <div class="status-badge">🟢 SYSTEM ONLINE</div>
                <p>Telegram Bot hostowany na <strong>Render.com</strong></p>
            </div>
            
            <a href="https://t.me/PcSentintel_Bot" class="bot-link" target="_blank">
                💬 Otwórz bota w Telegramie
            </a>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{len(AGENTS)}</div>
                    <div>Wszystkich agentów</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{online_count}</div>
                    <div>Online</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(AGENTS) - online_count}</div>
                    <div>Offline</div>
                </div>
            </div>
            
            <h2>🧭 Agenci systemu</h2>
            {"".join([
                f'''
                <div class="agent-card">
                    <div class="agent-icon">{agent["icon"]}</div>
                    <div class="agent-info">
                        <div class="agent-name">{agent["name"]}</div>
                        <div>Typ: {agent["type"]}</div>
                        <div class="agent-status {'online' if agent['status'] == 'online' else 'offline'}">
                            {'🟢 ONLINE' if agent['status'] == 'online' else '🔴 OFFLINE'}
                        </div>
                    </div>
                </div>
                ''' for agent in AGENTS.values()
            ])}
            
            <h2>🔧 Informacje techniczne</h2>
            <div class="endpoints">
                <div><strong>Bot Token:</strong> {TOKEN[:10]}...</div>
                <div><strong>Webhook URL:</strong> {WEBHOOK_URL}</div>
                <div><strong>Render URL:</strong> {RENDER_URL}</div>
                <div><strong>Port:</strong> {PORT}</div>
            </div>
            
            <h2>📡 Endpointy API</h2>
            <div class="endpoints">
                <div><strong>GET</strong> <a href="/">/</a> - Ten dashboard</div>
                <div><strong>GET</strong> <a href="/health">/health</a> - Status zdrowia</div>
                <div><strong>GET</strong> <a href="/dashboard">/dashboard</a> - Dashboard JSON</div>
                <div><strong>GET</strong> <a href="/set_webhook">/set_webhook</a> - Ustaw webhook</div>
                <div><strong>GET</strong> <a href="/delete_webhook">/delete_webhook</a> - Usuń webhook</div>
                <div><strong>POST</strong> /webhook - Endpoint dla Telegrama</div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; color: #666; padding-top: 20px; border-top: 1px solid #eee;">
                <p>🤖 SENTRY ONE v2.0 | Render.com | Webhook Mode</p>
                <p>🔗 <a href="{RENDER_URL}">{RENDER_URL}</a></p>
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
        "agents": len(AGENTS),
        "webhook": WEBHOOK_URL
    })

# JSON dashboard
@app.route('/dashboard')
def dashboard():
    online_count = sum(1 for agent in AGENTS.values() if agent["status"] == "online")
    return jsonify({
        "system": {
            "name": "SENTRY ONE",
            "version": "2.0",
            "platform": "Render.com",
            "status": "online"
        },
        "bot": {
            "username": "PcSentintel_Bot",
            "mode": "webhook",
            "webhook_url": WEBHOOK_URL,
            "token_masked": f"{TOKEN[:10]}..."
        },
        "agents": AGENTS,
        "statistics": {
            "total_agents": len(AGENTS),
            "online_agents": online_count,
            "offline_agents": len(AGENTS) - online_count,
            "online_percentage": round((online_count / len(AGENTS)) * 100, 1)
        }
    })

# Endpoint do ustawienia webhooka
@app.route('/set_webhook')
async def set_webhook_route():
    try:
        # Ustaw webhook
        await application.bot.set_webhook(WEBHOOK_URL)
        
        # Sprawdź info
        webhook_info = await application.bot.get_webhook_info()
        
        return jsonify({
            "success": True,
            "message": "Webhook ustawiony pomyślnie",
            "webhook_url": webhook_info.url,
            "pending_updates": webhook_info.pending_update_count,
            "last_error": webhook_info.last_error_message
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Endpoint do usunięcia webhooka
@app.route('/delete_webhook')
async def delete_webhook_route():
    try:
        await application.bot.delete_webhook()
        return jsonify({
            "success": True,
            "message": "Webhook usunięty"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Endpoint webhook dla Telegrama
@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        # Pobierz dane z requesta
        data = await request.get_json()
        
        # Utwórz obiekt Update
        update = Update.de_json(data, application.bot)
        
        # Przekaż do dispatchera
        await application.process_update(update)
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ====================== INICJALIZACJA ======================
async def initialize():
    """Inicjalizacja bota"""
    print("\n" + "="*50)
    print("🤖 INICJALIZACJA SENTRY ONE")
    print("="*50)
    
    # Inicjalizuj aplikację
    await application.initialize()
    await application.start()
    
    # Ustaw webhook
    print(f"🔗 Ustawiam webhook: {WEBHOOK_URL}")
    
    try:
        await application.bot.set_webhook(
            url=WEBHOOK_URL,
            max_connections=40,
            allowed_updates=["message", "callback_query"]
        )
        
        # Sprawdź webhook
        webhook_info = await application.bot.get_webhook_info()
        print(f"✅ Webhook ustawiony pomyślnie!")
        print(f"📊 Pending updates: {webhook_info.pending_update_count}")
        print(f"🌐 Webhook URL: {webhook_info.url}")
    except Exception as e:
        print(f"❌ Błąd ustawiania webhook: {e}")
    
    print(f"🚀 Bot gotowy do działania!")
    print(f"🌍 URL: {RENDER_URL}")
    print("="*50 + "\n")

# ====================== START APLIKACJI ======================
if __name__ == "__main__":
    # Uruchom inicjalizację asynchronicznie
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Wykonaj inicjalizację
    loop.run_until_complete(initialize())
    
    # Uruchom serwer Flask
    print(f"🌐 Uruchamiam serwer HTTP na porcie {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )