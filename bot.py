#!/usr/bin/env python3
"""
🤖 SENTRY ONE - POLLING MODE
Simple, reliable, no webhook issues
"""

import os
import asyncio
import threading
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)
TELEGRAM_TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"

# Store for agents
agents = {
    "echo": {"name": "Echo", "status": "offline", "type": "phone"},
    "vector": {"name": "Vector", "status": "offline", "type": "tablet"},
    "visor": {"name": "Visor", "status": "offline", "type": "oculus"},
    "synergic": {"name": "Synergic", "status": "offline", "type": "computer"}
}

# Telegram bot handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *SENTRY ONE - Universal AI Ecosystem*\n\n"
        "*Agents:*\n• 📱 Echo - Phone Observer\n• 📟 Vector - Tablet Creator\n"
        "• 🕶️ Visor - Oculus Immersor\n• 💻 Synergic - Computer Processor\n\n"
        "*Commands:*\n/start - Welcome\n/agents - Agent status\n"
        "/test - Connection test\n/echo [command] - Command Echo",
        parse_mode='Markdown'
    )

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🔄 *AGENT STATUS*\n\n"
    for agent in agents.values():
        icon = "🟢" if agent["status"] == "online" else "🔴"
        msg += f"{icon} *{agent['name']}* ({agent['type']})\n"
        msg += f"  Status: {agent['status']}\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = " ".join(context.args) if context.args else "status"
    if agents["echo"]["status"] == "online":
        await update.message.reply_text(f"📱 Echo: Received '{command}'")
    else:
        await update.message.reply_text("🔴 Echo is offline. Use /agents to check.")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Sentry One operational! Polling mode active.")

# Setup and run bot
async def run_bot():
    print("🤖 Starting Telegram bot in polling mode...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("agents", agents_command))
    application.add_handler(CommandHandler("echo", echo_command))
    application.add_handler(CommandHandler("test", test_command))
    
    # Start polling
    await application.initialize()
    await application.start()
    print("✅ Bot started with polling")
    
    # Run forever
    await application.updater.start_polling()
    await application.stop()

# Start bot in background thread
def start_bot():
    asyncio.run(run_bot())

bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

# Flask routes
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "mode": "polling",
        "bot": "active",
        "agents_count": len(agents),
        "message": "Sentry One running in polling mode"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "bot": "polling"})

@app.route('/dashboard')
def dashboard():
    online = sum(1 for a in agents.values() if a["status"] == "online")
    return jsonify({
        "agents": agents,
        "online_agents": online,
        "offline_agents": len(agents) - online,
        "total_agents": len(agents)
    })

@app.route('/register', methods=['POST'])
def register_agent():
    data = request.json
    agent_id = data.get("agent_id", "").lower()
    
    if agent_id in agents:
        agents[agent_id]["status"] = "online"
        return jsonify({"status": "registered", "agent": agents[agent_id]})
    return jsonify({"error": "Agent not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Starting Sentry One on port {port}")
    print(f"🤖 Bot token: {TELEGRAM_TOKEN[:10]}...")
    print("📊 Dashboard: http://localhost:{}/dashboard".format(port))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)