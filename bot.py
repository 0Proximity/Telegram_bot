#!/usr/bin/env python3
"""
🤖 SENTRY ONE - SIMPLE FIXED VERSION
Fixed for Render + Telegram Webhook
"""

import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# CONFIG - HARDCODED FOR NOW
TELEGRAM_TOKEN = "8490381532:AAETsrsXJzUn-gJHNGASnIqC_3hjtOwaqic"
WEBHOOK_URL = "https://telegram-bot-1-7l4g.onrender.com"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(f"🚀 Starting Sentry One with token: {TELEGRAM_TOKEN[:10]}...")

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Sentry One - Fixed",
        "webhook_url": f"{WEBHOOK_URL}/webhook",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/": "This page",
            "/health": "Health check",
            "/webhook": "Telegram webhook (POST)",
            "/test": "Test bot connection",
            "/dashboard": "Agent dashboard"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "telegram_token_set": bool(TELEGRAM_TOKEN),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint - ALWAYS returns 200 OK"""
    try:
        data = request.get_json()
        logger.info(f"📨 Webhook received: {data}")
        
        # Always return 200 OK to prevent Telegram from disabling webhook
        return 'ok', 200
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return 'ok', 200  # Still return 200!

@app.route('/test', methods=['GET'])
def test_bot():
    """Test Telegram bot connection"""
    import requests
    
    try:
        # Test getMe endpoint
        response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            bot_info = response.json()
            return jsonify({
                "status": "connected",
                "bot": bot_info['result'],
                "message": f"Bot @{bot_info['result']['username']} is connected"
            })
        else:
            return jsonify({
                "status": "error",
                "code": response.status_code,
                "message": "Cannot connect to Telegram API"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/dashboard')
def dashboard():
    """Simple dashboard"""
    return jsonify({
        "agents": {
            "echo": {"status": "offline", "type": "phone"},
            "vector": {"status": "offline", "type": "tablet"},
            "visor": {"status": "offline", "type": "oculus"},
            "synergic": {"status": "offline", "type": "computer"}
        },
        "total_agents": 4,
        "online_agents": 0
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting server on port {port}")
    logger.info(f"🔗 Webhook URL: {WEBHOOK_URL}/webhook")
    logger.info(f"🤖 Telegram Token: {TELEGRAM_TOKEN[:10]}...")
    
    # Test Telegram connection
    import requests
    try:
        test = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
            timeout=5
        )
        if test.status_code == 200:
            logger.info(f"✅ Telegram bot connected: @{test.json()['result']['username']}")
        else:
            logger.error(f"❌ Telegram connection failed: {test.status_code}")
    except Exception as e:
        logger.error(f"❌ Telegram test error: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=False)