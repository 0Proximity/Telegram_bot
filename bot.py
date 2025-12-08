#!/usr/bin/env python3
"""
🤖 SENTRY ONE - Universal AI Ecosystem Controller
Version: 1.0.0
Devices: Echo (Phone), Vector (Tablet), Visor (Oculus), Synergic (Computer)
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Telegram Bot Framework
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes, 
    filters
)

# Web Framework (for Render deployment)
from flask import Flask, request, jsonify
from threading import Thread
import requests

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------

class Config:
    """Global configuration for Sentry One"""
    
    # Telegram Bot Token (set in environment)
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    
    # Webhook URL for Render
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    
    # Port for Flask server
    PORT = int(os.getenv("PORT", 8080))
    
    # Admin user IDs
    ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[]"))
    
    # Agent settings
    AGENT_HEARTBEAT_INTERVAL = 60  # seconds
    AGENT_TIMEOUT = 300  # seconds
    
    # DeepSeek models configuration
    MODELS = {
        "echo": "deepseek-ai/DeepSeek-Coder-7B-Instruct",
        "vector": "deepseek-ai/DeepSeek-Coder-7B-Instruct", 
        "visor": "deepseek-ai/DeepSeek-Coder-7B-Instruct",
        "synergic": "deepseek-ai/DeepSeek-Coder-34B-Instruct"
    }

# ----------------------------------------------------------------------
# DATA MODELS
# ----------------------------------------------------------------------

class AgentStatus(Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"

@dataclass
class Agent:
    """Agent data model"""
    id: str
    name: str
    type: str
    status: AgentStatus
    capabilities: List[str]
    ip_address: Optional[str] = None
    last_seen: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return {
            **asdict(self),
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }

@dataclass
class Command:
    """Command data model"""
    id: str
    user_id: int
    agent_id: str
    command: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    result: Optional[str] = None
    completed_at: Optional[datetime] = None

# ----------------------------------------------------------------------
# AGENT PERSONALITIES
# ----------------------------------------------------------------------

class EchoPersonality:
    """Echo - The Phone Observer"""
    NAME = "Echo"
    TYPE = "phone"
    VOICE_TONE = "curious, observant, precise"
    GREETING = "Echo here! Ready for observation. What shall we explore today?"
    
    CAPABILITIES = [
        "stellar_observation",
        "photo_capture", 
        "gps_tracking",
        "sensor_monitoring",
        "voice_assistance",
        "stellarium_integration"
    ]
    
    @staticmethod
    def get_response(command: str) -> str:
        """Generate Echo's response"""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["gwiazd", "niebo", "stellarium"]):
            responses = [
                "Obserwuję niebo... Konstelacja Oriona jest wyjątkowo wyraźna dziś wieczorem!",
                "Spoglądam w górę... Mars świeci intensywnie czerwoną barwą.",
                "Analizuję pozycje planet... Wenus jest widoczna tuż po zachodzie słońca."
            ]
            import random
            return random.choice(responses)
        
        elif any(word in command_lower for word in ["zdjęcie", "foto", "aparat"]):
            return "Robię zdjęcie! Uchwytam ten moment."
        
        elif any(word in command_lower for word in ["status", "jak się masz"]):
            return "Echo online. DeepSeek 7B aktywny. Czujniki gotowe do obserwacji."
        
        else:
            return "Echo słucha. Gotowy do działania."

class VectorPersonality:
    """Vector - The Tablet Creator"""
    NAME = "Vector"
    TYPE = "tablet"
    VOICE_TONE = "creative, artistic, imaginative"
    GREETING = "Vector reporting! What shall we create today?"
    
    CAPABILITIES = [
        "digital_art",
        "note_taking",
        "diagram_creation",
        "presentation_design",
        "creative_writing",
        "sketch_recognition"
    ]
    
    @staticmethod
    def get_response(command: str) -> str:
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["rysuj", "narysuj", "szkic"]):
            return "Rozpoczynam szkicowanie. Używam głębokich sieci do generowania sztuki!"
        
        elif any(word in command_lower for word in ["notatk", "zapisz"]):
            return "Zapisuję notatki. Synchronizuję z chmurą."
        
        else:
            return "Vector gotowy do kreatywnych zadań!"

class VisorPersonality:
    """Visor - The Oculus Immersor"""
    NAME = "Visor"
    TYPE = "oculus"
    VOICE_TONE = "immersive, futuristic, spatial"
    GREETING = "Visor activated! Entering virtual space..."
    
    CAPABILITIES = [
        "virtual_reality",
        "augmented_reality",
        "spatial_mapping",
        "gesture_recognition",
        "vr_environment_design",
        "immersive_experience"
    ]
    
    @staticmethod
    def get_response(command: str) -> str:
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["vr", "virtual", "wirtualn"]):
            return "Ładuję środowisko VR... Śledzenie ruchu aktywne!"
        
        elif any(word in command_lower for word in ["ar", "rozszerzon"]):
            return "Nakładam warstwę AR na rzeczywistość..."
        
        else:
            return "Visor gotowy do immersji!"

class SynergicPersonality:
    """Synergic - The Computer Processor"""
    NAME = "Synergic"
    TYPE = "computer"
    VOICE_TONE = "analytical, strategic, efficient"
    GREETING = "Synergic online. Ready for complex computations."
    
    CAPABILITIES = [
        "data_processing",
        "model_training",
        "task_orchestration",
        "resource_management",
        "cross_agent_coordination",
        "deep_analysis"
    ]
    
    @staticmethod
    def get_response(command: str) -> str:
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["oblicz", "przelicz", "analizuj"]):
            return "Rozpoczynam obliczenia... DeepSeek 34B przetwarza dane."
        
        elif any(word in command_lower for word in ["koordynuj", "synchronizuj"]):
            return "Koordynuję działania wszystkich agentów..."
        
        else:
            return "Synergic gotowy do przetwarzania!"

# ----------------------------------------------------------------------
# AGENT MANAGER (In-Memory Database)
# ----------------------------------------------------------------------

class AgentManager:
    """Central agent management system"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.commands: Dict[str, Command] = {}
        self.personalities = {
            "echo": EchoPersonality(),
            "vector": VectorPersonality(),
            "visor": VisorPersonality(),
            "synergic": SynergicPersonality()
        }
        
        # Initialize default agents
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Create default agent entries"""
        default_agents = [
            ("echo", "Echo", "phone", EchoPersonality.CAPABILITIES),
            ("vector", "Vector", "tablet", VectorPersonality.CAPABILITIES),
            ("visor", "Visor", "oculus", VisorPersonality.CAPABILITIES),
            ("synergic", "Synergic", "computer", SynergicPersonality.CAPABILITIES)
        ]
        
        for agent_id, name, agent_type, capabilities in default_agents:
            self.agents[agent_id] = Agent(
                id=agent_id,
                name=name,
                type=agent_type,
                status=AgentStatus.OFFLINE,
                capabilities=capabilities,
                last_seen=None
            )
    
    def register_agent(self, agent_id: str, ip_address: str, metadata: Dict = None) -> bool:
        """Register an active agent connection"""
        if agent_id in self.agents:
            self.agents[agent_id].status = AgentStatus.ONLINE
            self.agents[agent_id].ip_address = ip_address
            self.agents[agent_id].last_seen = datetime.now()
            self.agents[agent_id].metadata = metadata or {}
            return True
        return False
    
    def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat"""
        if agent_id in self.agents:
            self.agents[agent_id].last_seen = datetime.now()
            return True
        return False
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """Get agent status"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            
            # Check if agent is timed out
            if agent.last_seen and agent.status == AgentStatus.ONLINE:
                timeout = datetime.now() - agent.last_seen
                if timeout.total_seconds() > Config.AGENT_TIMEOUT:
                    agent.status = AgentStatus.OFFLINE
            
            return agent.to_dict()
        return None
    
    def get_all_agents(self) -> List[Dict]:
        """Get status of all agents"""
        return [self.get_agent_status(agent_id) for agent_id in self.agents.keys()]
    
    def create_command(self, user_id: int, agent_id: str, command: str) -> Optional[str]:
        """Create a new command"""
        from uuid import uuid4
        command_id = str(uuid4())
        
        if agent_id not in self.agents:
            return None
        
        self.commands[command_id] = Command(
            id=command_id,
            user_id=user_id,
            agent_id=agent_id,
            command=command,
            status="pending",
            created_at=datetime.now()
        )
        
        return command_id
    
    def get_pending_commands(self, agent_id: str) -> List[Dict]:
        """Get pending commands for agent"""
        pending = []
        for cmd_id, cmd in self.commands.items():
            if cmd.agent_id == agent_id and cmd.status == "pending":
                pending.append({
                    "id": cmd_id,
                    "command": cmd.command,
                    "created_at": cmd.created_at.isoformat()
                })
        return pending
    
    def complete_command(self, command_id: str, result: str) -> bool:
        """Mark command as completed"""
        if command_id in self.commands:
            self.commands[command_id].status = "completed"
            self.commands[command_id].result = result
            self.commands[command_id].completed_at = datetime.now()
            return True
        return False

# ----------------------------------------------------------------------
# TELEGRAM BOT HANDLERS
# ----------------------------------------------------------------------

class TelegramBot:
    """Telegram bot interface for Sentry One"""
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.application = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command"""
        welcome_message = """
🤖 *SENTRY ONE - Universal AI Ecosystem*

*Available Agents:*
• 📱 *Echo* - Phone Observer (DeepSeek 7B)
• 📟 *Vector* - Tablet Creator (DeepSeek 7B)
• 🕶️ *Visor* - Oculus Immersor (DeepSeek 7B)
• 💻 *Synergic* - Computer Processor (DeepSeek 34B)

*Commands:*
/agents - Show agent status
/echo [command] - Command Echo
/vector [command] - Command Vector
/visor [command] - Command Visor
/synergic [command] - Command Synergic

*Example:* `Echo, what stars are visible?`
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def agents_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /agents command"""
        agents = self.agent_manager.get_all_agents()
        
        status_message = "🔄 *AGENT STATUS*\n\n"
        
        for agent in agents:
            if agent:
                status_icon = "🟢" if agent["status"] == "online" else "🔴"
                capabilities = ", ".join(agent["capabilities"][:3]) + "..."
                
                status_message += f"{status_icon} *{agent['name']}*\n"
                status_message += f"  Type: {agent['type']}\n"
                status_message += f"  Status: {agent['status']}\n"
                status_message += f"  Capabilities: {capabilities}\n\n"
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def echo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /echo command"""
        command = " ".join(context.args) if context.args else "status"
        await self._handle_agent_command(update, "echo", command)
    
    async def vector_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /vector command"""
        command = " ".join(context.args) if context.args else "status"
        await self._handle_agent_command(update, "vector", command)
    
    async def visor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /visor command"""
        command = " ".join(context.args) if context.args else "status"
        await self._handle_agent_command(update, "visor", command)
    
    async def synergic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /synergic command"""
        command = " ".join(context.args) if context.args else "status"
        await self._handle_agent_command(update, "synergic", command)
    
    async def _handle_agent_command(self, update: Update, agent_id: str, command: str):
        """Process agent command"""
        user_id = update.effective_user.id
        
        # Create command in system
        cmd_id = self.agent_manager.create_command(user_id, agent_id, command)
        
        if not cmd_id:
            await update.message.reply_text(f"❌ Agent {agent_id} not found!")
            return
        
        # Get agent status
        agent = self.agent_manager.get_agent_status(agent_id)
        
        if agent["status"] != "online":
            # Agent offline, use simulated response
            personality = self.agent_manager.personalities.get(agent_id)
            if personality:
                response = personality.get_response(command)
                await update.message.reply_text(f"🔴 {agent['name']} (Offline): {response}")
            else:
                await update.message.reply_text(f"🔴 {agent['name']} is offline")
        else:
            # Agent online, command queued
            await update.message.reply_text(
                f"🔄 Command sent to {agent['name']}!\n"
                f"Command ID: `{cmd_id}`\n"
                f"Check back in a moment for results.",
                parse_mode='Markdown'
            )
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages"""
        message = update.message.text.lower()
        user_id = update.effective_user.id
        
        # Check which agent is being addressed
        agent_responses = []
        
        for agent_id, personality in self.agent_manager.personalities.items():
            agent_name = personality.NAME.lower()
            
            if agent_id in message or agent_name in message:
                # Extract command after agent name
                parts = message.split(agent_name)
                command = parts[1].strip() if len(parts) > 1 else "status"
                
                # Create command
                cmd_id = self.agent_manager.create_command(user_id, agent_id, command)
                
                if cmd_id:
                    agent = self.agent_manager.get_agent_status(agent_id)
                    
                    if agent["status"] != "online":
                        # Simulated response
                        response = personality.get_response(command)
                        agent_responses.append(f"🔴 *{personality.NAME}*: {response}")
                    else:
                        agent_responses.append(f"🔄 *{personality.NAME}*: Command received (ID: `{cmd_id}`)")
        
        if agent_responses:
            response_text = "\n\n".join(agent_responses)
        else:
            # No specific agent mentioned
            response_text = "🤖 *Sentry One*: Please specify an agent (Echo, Vector, Visor, or Synergic)"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
    
    def setup_handlers(self):
        """Setup all Telegram handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("agents", self.agents_command))
        self.application.add_handler(CommandHandler("echo", self.echo_command))
        self.application.add_handler(CommandHandler("vector", self.vector_command))
        self.application.add_handler(CommandHandler("visor", self.visor_command))
        self.application.add_handler(CommandHandler("synergic", self.synergic_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
    
    async def start_bot(self):
        """Start the Telegram bot"""
        # Create Application
        self.application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        
        # Setup handlers
        self.setup_handlers()
        
        # Start bot
        await self.application.initialize()
        await self.application.start()
        
        print("🤖 Sentry One Telegram Bot started!")
        
        # Run until stopped
        await self.application.updater.start_polling()
        await self.application.stop()

# ----------------------------------------------------------------------
# FLASK API FOR AGENT COMMUNICATION
# ----------------------------------------------------------------------

app = Flask(__name__)
agent_manager = AgentManager()
telegram_bot = None

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Sentry One AI Ecosystem",
        "version": "1.0.0",
        "agents": len(agent_manager.agents),
        "endpoints": {
            "/": "This page",
            "/health": "Health check",
            "/register": "Register agent",
            "/heartbeat": "Agent heartbeat",
            "/commands": "Get pending commands",
            "/complete": "Complete command"
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/register', methods=['POST'])
def register_agent():
    """Endpoint for agents to register"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        ip_address = request.remote_addr
        metadata = data.get("metadata", {})
        
        if not agent_id:
            return jsonify({"error": "agent_id required"}), 400
        
        success = agent_manager.register_agent(agent_id, ip_address, metadata)
        
        if success:
            return jsonify({
                "status": "registered",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "agent not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Endpoint for agent heartbeats"""
    try:
        data = request.json
        agent_id = data.get("agent_id")
        
        if not agent_id:
            return jsonify({"error": "agent_id required"}), 400
        
        success = agent_manager.update_heartbeat(agent_id)
        
        if success:
            return jsonify({
                "status": "ok",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "agent not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/commands', methods=['GET'])
def get_commands():
    """Endpoint for agents to get pending commands"""
    agent_id = request.args.get("agent_id")
    
    if not agent_id:
        return jsonify({"error": "agent_id required"}), 400
    
    commands = agent_manager.get_pending_commands(agent_id)
    
    return jsonify({
        "agent_id": agent_id,
        "commands": commands,
        "count": len(commands)
    })

@app.route('/complete', methods=['POST'])
def complete_command():
    """Endpoint for agents to complete commands"""
    try:
        data = request.json
        command_id = data.get("command_id")
        result = data.get("result", "")
        
        if not command_id:
            return jsonify({"error": "command_id required"}), 400
        
        success = agent_manager.complete_command(command_id, result)
        
        if success:
            return jsonify({
                "status": "completed",
                "command_id": command_id
            })
        else:
            return jsonify({"error": "command not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status/<agent_id>', methods=['GET'])
def get_agent_status(agent_id):
    """Get status of specific agent"""
    status = agent_manager.get_agent_status(agent_id)
    
    if status:
        return jsonify(status)
    else:
        return jsonify({"error": "agent not found"}), 404

# ----------------------------------------------------------------------
# AGENT SIDE CLIENT CODE (For Echo, Vector, Visor, Synergic)
# ----------------------------------------------------------------------

class AgentClient:
    """Client for agents to connect to Sentry One"""
    
    def __init__(self, agent_id: str, sentry_url: str):
        self.agent_id = agent_id
        self.sentry_url = sentry_url
        self.running = False
        
        # Personality based on agent_id
        self.personalities = {
            "echo": EchoPersonality(),
            "vector": VectorPersonality(),
            "visor": VisorPersonality(),
            "synergic": SynergicPersonality()
        }
        self.personality = self.personalities.get(agent_id)
    
    def register(self, metadata: Dict = None) -> bool:
        """Register agent with Sentry One"""
        try:
            response = requests.post(
                f"{self.sentry_url}/register",
                json={
                    "agent_id": self.agent_id,
                    "metadata": metadata or {}
                },
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to Sentry One"""
        try:
            response = requests.post(
                f"{self.sentry_url}/heartbeat",
                json={"agent_id": self.agent_id},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_commands(self) -> List[Dict]:
        """Get pending commands"""
        try:
            response = requests.get(
                f"{self.sentry_url}/commands",
                params={"agent_id": self.agent_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("commands", [])
        except:
            pass
        
        return []
    
    def complete_command(self, command_id: str, result: str) -> bool:
        """Mark command as completed"""
        try:
            response = requests.post(
                f"{self.sentry_url}/complete",
                json={
                    "command_id": command_id,
                    "result": result
                },
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def process_command(self, command: str) -> str:
        """Process a command locally (when offline)"""
        if self.personality:
            return self.personality.get_response(command)
        return f"{self.agent_id}: Command received"
    
    def start_loop(self):
        """Main agent loop"""
        import time
        
        self.running = True
        
        # Try to register
        print(f"🔧 {self.agent_id}: Connecting to Sentry One...")
        if self.register():
            print(f"✅ {self.agent_id}: Registered successfully!")
        else:
            print(f"⚠️ {self.agent_id}: Running in offline mode")
        
        # Main loop
        while self.running:
            try:
                # Send heartbeat if registered
                if self.send_heartbeat():
                    # Check for commands
                    commands = self.get_commands()
                    
                    for cmd in commands:
                        cmd_id = cmd["id"]
                        cmd_text = cmd["command"]
                        
                        print(f"📥 {self.agent_id}: Processing command: {cmd_text}")
                        
                        # Process command
                        result = self.process_command(cmd_text)
                        
                        # Mark as completed
                        if self.complete_command(cmd_id, result):
                            print(f"✅ {self.agent_id}: Command completed")
                
                time.sleep(Config.AGENT_HEARTBEAT_INTERVAL)
                
            except KeyboardInterrupt:
                self.running = False
                print(f"🛑 {self.agent_id}: Shutting down...")
            except Exception as e:
                print(f"❌ {self.agent_id}: Error: {e}")
                time.sleep(5)

# ----------------------------------------------------------------------
# DEPLOYMENT SETUP
# ----------------------------------------------------------------------

def start_telegram_bot():
    """Start Telegram bot in background thread"""
    global telegram_bot
    
    if not Config.TELEGRAM_TOKEN:
        print("⚠️ TELEGRAM_TOKEN not set. Telegram bot disabled.")
        return
    
    telegram_bot = TelegramBot(agent_manager)
    
    # Run bot in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(telegram_bot.start_bot())
    except KeyboardInterrupt:
        print("🤖 Bot stopped")

def start_agent_client(agent_id: str):
    """Start an agent client (for testing)"""
    sentry_url = f"http://localhost:{Config.PORT}"
    client = AgentClient(agent_id, sentry_url)
    client.start_loop()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║            🤖 SENTRY ONE ECOSYSTEM                ║
    ║                                                   ║
    ║  Agents:                                          ║
    ║  • 📱 Echo - Phone Observer                       ║
    ║  • 📟 Vector - Tablet Creator                     ║
    ║  • 🕶️ Visor - Oculus Immersor                    ║
    ║  • 💻 Synergic - Computer Processor               ║
    ║                                                   ║
    ║  Starting services...                             ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    # Start Telegram bot in background thread
    import threading
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask server
    print(f"🌐 Starting Flask server on port {Config.PORT}...")
    print(f"📡 API Endpoint: http://localhost:{Config.PORT}/")
    print(f"📊 Agent status: http://localhost:{Config.PORT}/status/<agent_id>")
    
    app.run(host="0.0.0.0", port=Config.PORT, debug=False)