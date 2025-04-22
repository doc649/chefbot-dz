from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ordonnasecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"].get("text", "")

        if user_text:
            message_clean = user_text.lower().strip()
            interdits = ["bonjour", "salut", "cc", "slt", "merci", "ok", "hello", "test", "wesh"]

            if message_clean in interdits:
                print("💥 INTERCEPTION ACTIVE BY HAMZA : message bloqué ->", message_clean)
                requests.post(
                    f"{BOT_URL}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "🧾 Envoie une ordonnance pour que je puisse t'aider. Tu peux choisir la langue avec /langue_fr ou /langue_dz."
                    }
                )
                return "ok"

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es OrdonnaBot, un assistant médical algérien. "
                                "Tu aides les gens à comprendre leurs ordonnances et les traitements prescrits. "
                                "Réponds toujours de manière claire, bienveillante, et en français. "
                                "Ne dis jamais 'bonjour', ni 'comment puis-je vous aider'."
                            )
                        },
                        {"role": "user", "content": user_text}
                    ]
                )

                gpt_reply = response.choices[0].message["content"]

            except Exception as e:
                print(f"Erreur GPT: {e}")
                gpt_reply = "❌ Une erreur est survenue. Veuillez réessayer plus tard."

            requests.post(
                f"{BOT_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": gpt_reply
                }
            )
    return "ok"
