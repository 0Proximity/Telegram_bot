#!/usr/bin/env python3
"""
🤖 SENTRY ONE - Fixed Polling Version
python-telegram-bot >= 20.0
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"

# Agents data
agents = {
    "echo": {"name": "Echo", "status": "online", "type": "phone"},
    "vector": {"name": "Vector", "status": "offline", "type": "tablet"},
    "visor": {"name": "Visor", "status": "offline", "type": "oculus"},
    "synergic": {"name": "Synergic", "status": "offline", "type": "computer"}
}

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "🤖 *SENTRY ONE - Universal AI Ecosystem*\n\n"
        "Commands:\n"
        "/start - Welcome message\n"
        "/agents - Check agent status\n"
        "/test - Connection test\n"
        "/status - System status\n"
        "/set <agent> <online/offline> - Change agent status",
        parse_mode='Markdown'
    )

async def agents_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show agent status"""
    response = "🔄 *AGENT STATUS*\n\n"
    for agent_id, agent in agents.items():
        status_icon = "🟢" if agent["status"] == "online" else "🔴"
        response += f"{status_icon} *{agent['name']}* ({agent['type']})\n"
        response += f"  Status: {agent['status']}\n\n"
    await update.message.reply_text(response, parse_mode='Markdown')

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test connection"""
    await update.message.reply_text("✅ Sentry One operational! Polling mode active.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """System status"""
    online = sum(1 for a in agents.values() if a["status"] == "online")
    await update.message.reply_text(
        f"📊 *SYSTEM STATUS*\n"
        f"• Bot: ✅ Online\n"
        f"• Agents: {online}/{len(agents)} online\n"
        f"• Mode: 🔄 Polling",
        parse_mode='Markdown'
    )

async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set agent status"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /set <agent> <online|offline>")
        return
    
    agent_name = context.args[0].lower()
    new_status = context.args[1].lower()
    
    if agent_name not in agents:
        await update.message.reply_text(f"❌ Agent '{agent_name}' not found")
        return
    
    if new_status not in ["online", "offline"]:
        await update.message.reply_text("❌ Status must be 'online' or 'offline'")
        return
    
    agents[agent_name]["status"] = new_status
    await update.message.reply_text(
        f"✅ {agents[agent_name]['name']} set to {new_status}"
    )

# Main function
async def main():
    """Start the bot"""
    print("🤖 Starting SENTRY ONE...")
    print(f"📝 Token: {TOKEN[:10]}...")
    
    # Create Application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("agents", agents_cmd))
    application.add_handler(CommandHandler("test", test))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("set", set_status))
    
    # Start polling
    print("🔄 Starting polling...")
    print("✅ Bot is running! Press Ctrl+C to stop.\n")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")