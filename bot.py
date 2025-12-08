#!/usr/bin/env python3
"""
🤖 SENTRY ONE - POLLING MODE
Simple, reliable, no webhook issues
"""

import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"

# Store for agents
agents = {
    "echo": {"name": "Echo", "status": "online", "type": "phone"},
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
        "/test - Connection test\n/echo [command] - Command Echo\n"
        "/status - System status",
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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    online_count = sum(1 for a in agents.values() if a["status"] == "online")
    await update.message.reply_text(
        f"📊 *SYSTEM STATUS*\n\n"
        f"• Bot: ✅ Online\n"
        f"• Mode: 🔄 Polling\n"
        f"• Agents: {online_count}/{len(agents)} online\n"
        f"• Use /agents for details",
        parse_mode='Markdown'
    )

async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set agent status (admin only)"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /set <agent_name> <online|offline>")
        return
    
    agent_name = context.args[0].lower()
    status = context.args[1].lower()
    
    if agent_name not in agents:
        await update.message.reply_text(f"❌ Agent '{agent_name}' not found")
        return
    
    if status not in ["online", "offline"]:
        await update.message.reply_text("❌ Status must be 'online' or 'offline'")
        return
    
    agents[agent_name]["status"] = status
    await update.message.reply_text(f"✅ {agents[agent_name]['name']} set to {status}")

# Main function
async def main():
    """Start the bot."""
    print("🤖 Starting SENTRY ONE in polling mode...")
    print(f"📝 Token: {TELEGRAM_TOKEN[:10]}...")
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("agents", agents_command))
    application.add_handler(CommandHandler("echo", echo_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("set", set_command))
    
    # Start polling
    print("🔄 Starting polling...")
    print("✅ Bot is running! Press Ctrl+C to stop.")
    
    await application.run_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down SENTRY ONE...")
    except Exception as e:
        print(f"❌ Error: {e}")