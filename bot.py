import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# Konfiguracja logowania
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class SentryOneSystem:
    def __init__(self):
        self.agents = {
            "echo": {"name": "Echo", "type": "phone", "status": "offline", "capabilities": []},
            "vector": {"name": "Vector", "type": "tablet", "status": "offline", "capabilities": []},
            "visor": {"name": "Visor", "type": "oculus", "status": "offline", "capabilities": []},
            "synergic": {"name": "Synergic", "type": "computer", "status": "offline", "capabilities": []}
        }
    
    def start_command(self, update, context):
        """Komenda /start - inicjalizacja systemu"""
        welcome_text = """
🤖 **SENTRY ONE SYSTEM AKTYWOWANY**

Zarejestrowani agenci:
- 📱 Echo (Telefon) - *offline*
- 📟 Vector (Tablet) - *offline*  
- 🕶️ Visor (Oculus) - *offline*
- 💻 Synergic (Komputer) - *offline*

Użyj /register aby aktywować urządzenia!
        """
        update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    def register_command(self, update, context):
        """Komenda /register - rejestracja urządzenia"""
        keyboard = [
            [InlineKeyboardButton("📱 Echo", callback_data="register_echo")],
            [InlineKeyboardButton("📟 Vector", callback_data="register_vector")],
            [InlineKeyboardButton("🕶️ Visor", callback_data="register_visor")],
            [InlineKeyboardButton("💻 Synergic", callback_data="register_synergic")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "Wybierz urządzenie do rejestracji:",
            reply_markup=reply_markup
        )
    
    def button_handler(self, update, context):
        """Obsługa przycisków inline"""
        query = update.callback_query
        query.answer()
        
        agent_id = query.data.replace("register_", "")
        
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "online"
            self.agents[agent_id]["capabilities"] = ["monitoring", "communication", "data_analysis"]
            
            query.edit_message_text(
                f"✅ **{self.agents[agent_id]['name']}** został aktywowany!\n"
                f"Typ: {self.agents[agent_id]['type']}\n"
                f"Status: {self.agents[agent_id]['status']}\n"
                f"Możliwości: {', '.join(self.agents[agent_id]['capabilities'])}",
                parse_mode='Markdown'
            )
    
    def agents_command(self, update, context):
        """Komenda /agents - lista agentów"""
        status_text = "🤖 **AKTYWNI AGENCI:**\n\n"
        
        for agent_id, agent in self.agents.items():
            status_icon = "🟢" if agent["status"] == "online" else "🔴"
            status_text += f"{status_icon} **{agent['name']}** ({agent['type']})\n"
            status_text += f"   Status: {agent['status']}\n"
            if agent['capabilities']:
                status_text += f"   Możliwości: {', '.join(agent['capabilities'])}\n"
            status_text += "\n"
        
        update.message.reply_text(status_text, parse_mode='Markdown')
    
    def handle_agent_message(self, update, context):
        """Obsługa wiadomości do agentów"""
        message_text = update.message.text.lower()
        
        # Rozpoznawanie którego agenta wywołano
        if message_text.startswith('echo'):
            response = self.handle_echo_command(message_text)
        elif message_text.startswith('vector'):
            response = self.handle_vector_command(message_text)
        elif message_text.startswith('visor'):
            response = self.handle_visor_command(message_text)
        elif message_text.startswith('synergic'):
            response = self.handle_synergic_command(message_text)
        else:
            response = "🤖 Sentry One: Nie rozpoznano agenta. Użyj: Echo, Vector, Visor lub Synergic"
        
        update.message.reply_text(response)
    
    def handle_echo_command(self, command):
        """Obsługa komend dla Echo (telefon)"""
        if "status" in command:
            return "📱 Echo: Jestem w trakcie konfiguracji. DeepSeek 7B ładuje się na Manjaro ARM..."
        elif "test" in command:
            return "📱 Echo: Testuję system głosowy... Mikrofon aktywny!"
        else:
            return "📱 Echo: Słucham! Przygotowuję się do obserwacji astronomicznych."
    
    def handle_vector_command(self, command):
        """Obsługa komend dla Vector (tablet)"""
        return "📟 Vector: Gotowy do działań kreatywnych! Czekam na konfigurację."
    
    def handle_visor_command(self, command):
        """Obsługa komend dla Visor (oculus)"""
        return "🕶️ Visor: System VR inicjalizowany. Przygotowuję immersyjne doświadczenia!"
    
    def handle_synergic_command(self, command):
        """Obsługa komend dla Synergic (komputer)"""
        return "💻 Synergic: Gotowy do ciężkich obliczeń. DeepSeek 34B oczekuje na wdrożenie."

# Inicjalizacja systemu
sentry_system = SentryOneSystem()

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """Główna funkcja uruchamiająca bot"""
    # Pobierz token z zmiennej środowiskowej
    token = os.environ.get('BOT_TOKEN')
    if not token:
        print("❌ Błąd: Nie ustawiono BOT_TOKEN!")
        return

    # Utwórz Updater i przekaż token
    updater = Updater(token, use_context=True)
    
    # Pobierz dyspozytora do rejestracji handlerów
    dp = updater.dispatcher

    # Dodaj handlery komend
    dp.add_handler(CommandHandler("start", sentry_system.start_command))
    dp.add_handler(CommandHandler("register", sentry_system.register_command))
    dp.add_handler(CommandHandler("agents", sentry_system.agents_command))
    dp.add_handler(CommandHandler("status", sentry_system.agents_command))
    
    # Handler dla przycisków inline
    dp.add_handler(CallbackQueryHandler(sentry_system.button_handler))
    
    # Handler dla wiadomości tekstowych
    dp.add_handler(MessageHandler(Filters.text, sentry_system.handle_agent_message))
    
    # Handler błędów
    dp.add_error_handler(error)

    # Uruchom bota
    print("🟢 Sentry One System starting...")
    updater.start_polling()
    print("✅ Bot is running and polling...")
    updater.idle()

if __name__ == '__main__':
    main()
