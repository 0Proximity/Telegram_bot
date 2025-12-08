#!/usr/bin/env python3
"""
🤖 SENTRY ONE - Universal AI Ecosystem Controller
Version: 1.0.0 - Fixed Webhook Edition
Bot Token: 8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic
"""

import os
import json
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify

# Telegram imports
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------------------------------------------------------------
# CONFIGURATION - HARDCODED FOR STABILITY
# ----------------------------------------------------------------------

TELEGRAM_TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
WEBHOOK_URL = "https://telegram-bot-1-7l4g.onrender.com"
PORT = int(os.environ.get('PORT', 8080))

# ----------------------------------------------------------------------
# FLASK APP
# ----------------------------------------------------------------------

app = Flask(__name__)

# Simple agent storage
agents = {
    "echo": {"id": "echo", "name": "Echo", "type": "phone", "status": "offline", "capabilities": [], "last_seen": None},
    "vector": {"id": "vector", "name": "Vector", "type": "tablet", "status": "offline", "capabilities": [], "last_seen": None},
    "visor": {"id": "visor", "name": "Visor", "type": "oculus", "status": "offline", "capabilities": [], "last_seen": None},
    "synergic": {"id": "synergic", "name": "Synergic", "type": "computer", "status": "offline", "capabilities": [], "last_seen": None}
}

commands = {}
application = None

# ----------------------------------------------------------------------
# TELEGRAM BOT HANDLERS
# ----------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *SENTRY ONE - Universal AI Ecosystem*\n\n"
        "*Agents:*\n• 📱 Echo - Phone Observer\n• 📟 Vector - Tablet Creator\n"
        "• 🕶️ Visor - Oculus Immersor\n• 💻 Synergic - Computer Processor\n\n"
        "*Commands:*\n/start - Welcome\n/agents - Agent status\n"
        "/echo [command] - Command Echo\n/test - Connection test",
        parse_mode='Markdown'
    )

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = "🔄 *AGENT STATUS*\n\n"
    for agent_id, agent in agents.items():
        icon = "🟢" if agent["status"] == "online" else "🔴"
        status_msg += f"{icon} *{agent['name']}* ({agent['type']})\n"
        status_msg += f"  Status: {agent['status']}\n\n"
    
    await update.message.reply_text(status_msg, parse_mode='Markdown')

async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = " ".join(context.args) if context.args else "status"
    
    if agents["echo"]["status"] == "online":
        response = f"🔄 Command sent to Echo: '{command}'"
    else:
        response = "🔴 Echo is offline. Use /agents to check status."
    
    await update.message.reply_text(response)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Sentry One is operational! All systems nominal.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    if "echo" in text:
        await update.message.reply_text("📱 Echo: Ready for observation!")
    elif "vector" in text:
        await update.message.reply_text("📟 Vector: Ready for creation!")
    elif "visor" in text:
        await update.message.reply_text("🕶️ Visor: Ready for immersion!")
    elif "synergic" in text:
        await update.message.reply_text("💻 Synergic: Ready for processing!")
    else:
        await update.message.reply_text("🤖 Sentry One: Specify an agent (Echo, Vector, Visor, Synergic)")

# ----------------------------------------------------------------------
# TELEGRAM BOT SETUP
# ----------------------------------------------------------------------

async def setup_bot():
    """Initialize Telegram bot with webhook"""
    global application
    
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("agents", agents_command))
        application.add_handler(CommandHandler("echo", echo_command))
        application.add_handler(CommandHandler("test", test_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Initialize
        await application.initialize()
        
        # Set webhook
        await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
        
        bot_info = await application.bot.get_me()
        print(f"✅ Telegram bot initialized: @{bot_info.username}")
        print(f"🌐 Webhook set: {WEBHOOK_URL}/webhook")
        
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")

def start_bot_thread():
    """Start bot in background thread"""
    import asyncio
    asyncio.run(setup_bot())

# ----------------------------------------------------------------------
# FLASK ROUTES
# ----------------------------------------------------------------------

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Sentry One - Fixed",
        "webhook_url": f"{WEBHOOK_URL}/webhook",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/": "This page",
            "/dashboard": "Agent dashboard",
            "/health": "Health check",
            "/test": "Test bot connection",
            "/webhook": "Telegram webhook (POST)",
            "/register": "Register agent (POST)",
            "/status/<agent_id>": "Agent status"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "telegram_bot": "initialized" if application else "not_initialized"
    })

@app.route('/dashboard')
def dashboard():
    online_count = sum(1 for agent in agents.values() if agent["status"] == "online")
    
    return jsonify({
        "agents": list(agents.values()),
        "total_agents": len(agents),
        "online_agents": online_count,
        "offline_agents": len(agents) - online_count,
        "system": {
            "telegram_bot": "initialized" if application else "not_initialized",
            "server_time": datetime.now().isoformat(),
            "webhook_url": WEBHOOK_URL
        }
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    if application is None:
        return jsonify({"error": "Bot not initialized"}), 503
    
    try:
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put(update)
        return 'ok'
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'ok', 200  # Always return 200 to Telegram

@app.route('/register', methods=['POST'])
def register_agent():
    """Register agent connection"""
    try:
        data = request.json
        agent_id = data.get("agent_id", "").lower()
        
        if agent_id in agents:
            agents[agent_id]["status"] = "online"
            agents[agent_id]["last_seen"] = datetime.now().isoformat()
            agents[agent_id]["capabilities"] = data.get("capabilities", [])
            
            return jsonify({
                "status": "registered",
                "agent": agents[agent_id]
            })
        else:
            return jsonify({"error": "Agent not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status/<agent_id>')
def agent_status(agent_id):
    """Get agent status"""
    if agent_id in agents:
        return jsonify(agents[agent_id])
    else:
        return jsonify({"error": "Agent not found"}), 404

@app.route('/test')
def test_connection():
    """Test Telegram connection"""
    import requests
    
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
            timeout=5
        )
        
        if response.status_code == 200:
            bot_info = response.json()["result"]
            return jsonify({
                "status": "connected",
                "bot": {
                    "name": bot_info["first_name"],
                    "username": bot_info["username"],
                    "id": bot_info["id"]
                }
            })
        else:
            return jsonify({"error": "Telegram API error"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------------------
# STARTUP
# ----------------------------------------------------------------------

if __name__ == '__main__':
    print("🤖 SENTRY ONE ECOSYSTEM - Starting...")
    print(f"🔗 Webhook URL: {WEBHOOK_URL}/webhook")
    print(f"🤖 Telegram Token: {TELEGRAM_TOKEN[:10]}...")
    
    # Start Telegram bot in background thread
    bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
    bot_thread.start()
    
    # Start Flask server
    print(f"🌐 Starting Flask on port {PORT}...")
    print("📊 Dashboard:", f"{WEBHOOK_URL}/dashboard")
    print("🩺 Health:", f"{WEBHOOK_URL}/health")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)