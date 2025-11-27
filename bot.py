import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ['BOT_TOKEN']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🎉 Bot działa! Witaj!')

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🏓 Pong! Działam!')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Komendy: /start, /help, /ping')

def main():
    print("🟢 Starting Telegram Bot...")
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("help", help))
    
    print("✅ Bot is running!")
    application.run_polling()

if __name__ == '__main__':
    main()
