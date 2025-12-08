# app.py z pollingiem zamiast webhooka
import os
from flask import Flask, jsonify
from telegram.ext import Application, CommandHandler
import threading

app = Flask(__name__)
TELEGRAM_TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"

async def start(update, context):
    await update.message.reply_text("🤖 Sentry One działa! Test OK.")

async def setup_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("✅ Bot działa z pollingiem")

# Uruchom bota w tle
import asyncio
thread = threading.Thread(target=lambda: asyncio.run(setup_bot()), daemon=True)
thread.start()

@app.route('/')
def home():
    return jsonify({"status": "online", "bot": "polling mode"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))