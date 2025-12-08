#!/usr/bin/env python3
"""
🤖 SENTRY ONE - FIXED for Render.com
Python 3.13 + python-telegram-bot 21.7
"""

import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request, jsonify

# ====================== KONFIGURACJA ======================
TOKEN = os.getenv("TELEGRAM_TOKEN", "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-bot-szxa.onrender.com")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{RENDER_URL}/webhook"

print("=" * 60)
print("🤖 SENTRY ONE - RENDER.COM FIX")
print("📱 Bot: @PcSentintel_Bot")
print(f"🌐 URL: {RENDER_URL}")
print("=" * 60)

# ====================== LOGGING ======================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================== DANE ======================
AGENTS = {
    "echo": {"name": "Echo", "status": "online", "type": "phone", "icon": "📱"},
    "vector": {"name": "Vector", "status": "online", "type": "tablet", "icon": "📟"},
    "visor": {"name": "Visor", "status": "offline", "type": "oculus", "icon": "🕶️"},
    "synergic": {"name": "Synergic", "status": "online", "type": "computer", "icon": "💻"}
}

# ====================== TELEGRAM HANDLERS ======================
app = Flask(__name__)

# Inicjalizacja aplikacji Telegram
telegram_app = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *SENTRY ONE v2.1*\n\n"
        "✅ Bot działa na Render.com!\n"
        "🔗 Tryb: Webhook\n\n"
        "*Komendy:*\n"
        "/start - Informacje\n"
        "/help - Pomoc\n"
        "/status - Status\n"
        "/test - Test połączenia",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *POMOC*\n\n"
        "Dostępne komendy:\n"
        "• /start - Informacje\n"
        "• /help - Ta pomoc\n"
        "• /status - Status systemu\n"
        "• /test - Test działania\n"
        "• /agents - Lista agentów\n\n"
        "🧭 *Agenty:*\n"
        "• 📱 Echo - Telefon\n"
        "• 📟 Vector - Tablet\n"
        "• 🕶️ Visor - Oculus\n"
        "• 💻 Synergic - Komputer",
        parse_mode='Markdown'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    online = sum(1 for a in AGENTS.values() if a["status"] == "online")
    await update.message.reply_text(
        f"📊 *STATUS SYSTEMU*\n\n"
        f"• Platforma: Render.com\n"
        f"• Bot: Działa ✅\n"
        f"• Tryb: Webhook\n"
        f"• Agenty: {online}/{len(AGENTS)} online\n"
        f"• URL: {RENDER_URL}",
        parse_mode='Markdown'
    )

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Test zakończony pomyślnie! Bot działa.")

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👥 *AGENTY SYSTEMU*\n\n"
    for agent in AGENTS.values():
        status = "🟢 ONLINE" if agent["status"] == "online" else "🔴 OFFLINE"
        text += f"{agent['icon']} *{agent['name']}*\n"
        text += f"   Typ: {agent['type']}\n"
        text += f"   Status: {status}\n\n"
    await update.message.reply_text(text, parse_mode='Markdown')

# ====================== FLASK ROUTES ======================
@app.route('/')
def home():
    return jsonify({
        "service": "sentry-one-telegram-bot",
        "status": "running",
        "bot": "@PcSentintel_Bot",
        "mode": "webhook",
        "url": RENDER_URL,
        "webhook": WEBHOOK_URL,
        "python_version": "3.13",
        "telegram_bot_version": "21.7"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": "2024-12-08"})

@app.route('/dashboard')
def dashboard():
    online = sum(1 for a in AGENTS.values() if a["status"] == "online")
    return jsonify({
        "agents": AGENTS,
        "stats": {
            "total": len(AGENTS),
            "online": online,
            "offline": len(AGENTS) - online
        },
        "system": {
            "platform": "render",
            "url": RENDER_URL
        }
    })

@app.route('/set_webhook')
def set_webhook():
    async def _set():
        try:
            bot = telegram_app.bot
            await bot.set_webhook(WEBHOOK_URL, max_connections=40)
            info = await bot.get_webhook_info()
            return {
                "success": True,
                "url": info.url,
                "pending": info.pending_update_count
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    result = asyncio.run(_set())
    return jsonify(result)

@app.route('/webhook', methods=['POST'])
def webhook():
    async def _process():
        try:
            data = request.get_json()
            update = Update.de_json(data, telegram_app.bot)
            await telegram_app.process_update(update)
            return "ok"
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return "error"
    
    # Run async function synchronously
    asyncio.run(_process())
    return "ok", 200

# ====================== INITIALIZATION ======================
async def initialize_telegram():
    """Initialize Telegram application"""
    global telegram_app
    
    print("🤖 Initializing Telegram bot...")
    
    # Create application
    telegram_app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("status", status_command))
    telegram_app.add_handler(CommandHandler("test", test_command))
    telegram_app.add_handler(CommandHandler("agents", agents_command))
    
    # Initialize
    await telegram_app.initialize()
    await telegram_app.start()
    
    # Set webhook
    print(f"🔗 Setting webhook to: {WEBHOOK_URL}")
    try:
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        webhook_info = await telegram_app.bot.get_webhook_info()
        print(f"✅ Webhook set successfully!")
        print(f"📊 Pending updates: {webhook_info.pending_update_count}")
    except Exception as e:
        print(f"⚠️  Webhook error: {e}")
    
    print("🚀 Telegram bot ready!")

def start_flask():
    """Start Flask server"""
    print(f"🌐 Starting Flask on port {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )

async def main():
    """Main async function"""
    # Initialize Telegram bot
    await initialize_telegram()
    
    # Start Flask in background thread
    import threading
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Keep the bot running
    print("✅ All systems operational!")
    print("📡 Bot is listening for updates...")
    
    # Run forever
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")