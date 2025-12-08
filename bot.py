#!/usr/bin/env python3
"""
🤖 SENTRY ONE - Render.com Compatible Version
"""

import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable (safer!)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic")

# Simple agents data
AGENTS = {
    "echo": {"name": "Echo", "status": "online", "type": "phone"},
    "vector": {"name": "Vector", "status": "offline", "type": "tablet"},
    "visor": {"name": "Visor", "status": "offline", "type": "oculus"},
    "synergic": {"name": "Synergic", "status": "offline", "type": "computer"}
}

# ====================== TELEGRAM HANDLERS ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *SENTRY ONE - AI Ecosystem*\n\n"
        "📡 *Mode:* Polling (Render.com)\n"
        "✅ *Status:* Operational\n\n"
        "*Commands:*\n"
        "/start - This message\n"
        "/agents - Agent status\n"
        "/test - Connection test\n"
        "/status - System info\n\n"
        "_Bot running on Render.com_",
        parse_mode='Markdown'
    )

async def agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔭 *AGENT STATUS*\n\n"
    for agent in AGENTS.values():
        status_icon = "🟢" if agent["status"] == "online" else "🔴"
        text += f"{status_icon} *{agent['name']}*\n"
        text += f"Type: {agent['type']}\n"
        text += f"Status: {agent['status']}\n\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Connection successful! Bot is alive.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    online = sum(1 for a in AGENTS.values() if a["status"] == "online")
    await update.message.reply_text(
        f"📊 *SYSTEM STATUS*\n"
        f"• Platform: Render.com\n"
        f"• Mode: Polling\n"
        f"• Agents: {online}/{len(AGENTS)} online\n"
        f"• Uptime: Active",
        parse_mode='Markdown'
    )

# ====================== BOT SETUP ======================
def setup_bot():
    """Setup and run the bot in background"""
    async def bot_main():
        print("🤖 Initializing Telegram bot...")
        
        # Create application with specific settings for Render
        application = Application.builder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("agents", agents))
        application.add_handler(CommandHandler("test", test))
        application.add_handler(CommandHandler("status", status))
        
        print("🔄 Starting polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Keep running
        print("✅ Bot is running on Render!")
        
        # Create a never-ending task to keep the bot alive
        await asyncio.Event().wait()
    
    # Run bot in background
    asyncio.create_task(bot_main())

# ====================== FLASK APP (for Render health checks) ======================
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# HTML template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🤖 SENTRY ONE - Render</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .online { background: #d4edda; color: #155724; }
        .offline { background: #f8d7da; color: #721c24; }
        .agent { padding: 15px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 SENTRY ONE</h1>
        <p>Telegram Bot running on Render.com</p>
        
        <div class="status online">
            <h3>🟢 Bot Status: ONLINE</h3>
            <p>Mode: Polling | Platform: Render</p>
        </div>
        
        <h2>Agents Status</h2>
        {% for agent in agents %}
        <div class="agent">
            <h3>{{ agent.name }} ({{ agent.type }})</h3>
            <p>Status: <strong>{{ agent.status }}</strong></p>
        </div>
        {% endfor %}
        
        <h2>API Endpoints</h2>
        <ul>
            <li><a href="/health">/health</a> - Health check</li>
            <li><a href="/dashboard">/dashboard</a> - JSON dashboard</li>
            <li><a href="https://t.me/PcSentintel_Bot" target="_blank">Telegram Bot</a></li>
        </ul>
        
        <p><em>Bot Token: {{ token_display }}</em></p>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    agents_list = list(AGENTS.values())
    token_display = f"{TOKEN[:10]}..." if TOKEN else "Not set"
    return render_template_string(HTML_TEMPLATE, 
                                 agents=agents_list, 
                                 token_display=token_display)

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "sentry-one-bot",
        "platform": "render",
        "bot": "active"
    })

@app.route('/dashboard')
def dashboard():
    online = sum(1 for a in AGENTS.values() if a["status"] == "online")
    return jsonify({
        "platform": "Render.com",
        "bot_mode": "polling",
        "agents": AGENTS,
        "stats": {
            "total_agents": len(AGENTS),
            "online_agents": online,
            "offline_agents": len(AGENTS) - online
        }
    })

# ====================== MAIN ENTRY POINT ======================
if __name__ == "__main__":
    print("🚀 Starting SENTRY ONE on Render.com")
    print(f"🤖 Bot token: {TOKEN[:10]}...")
    
    # Setup and run bot
    import threading
    
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def start_bot():
            application = Application.builder().token(TOKEN).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("agents", agents))
            application.add_handler(CommandHandler("test", test))
            application.add_handler(CommandHandler("status", status))
            
            print("🔄 Bot: Starting polling...")
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            # Keep alive
            await asyncio.Event().wait()
        
        try:
            loop.run_until_complete(start_bot())
        except KeyboardInterrupt:
            print("Bot stopped")
    
    # Start bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Bot thread started")
    
    # Start Flask app
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Web server starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)