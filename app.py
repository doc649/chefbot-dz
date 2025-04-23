from flask import Flask, request
import os
import requests

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "chefbotsecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("[PONG TEST] Message reçu :", update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        requests.post(f"{BOT_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": "✅ Pong reçu ! Ton webhook fonctionne parfaitement."
        })
    return "ok"
