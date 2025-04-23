from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "chefbotsecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"
openai.api_key = os.getenv("OPENAI_API_KEY")

def send_message(chat_id, text):
    print(f"[DEBUG] Envoi message → {chat_id}")
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    print(f"[DEBUG] get_file_path → {file_id}")
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("[DEBUG] Message Telegram reçu :", update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # ✅ Message de démarrage
        if "text" in update["message"]:
            user_text = update["message"]["text"]

            if user_text.lower() in ["/start", "start", "/hello"]:
                welcome = (
                    "👋 Bienvenue sur *ChefBot DZ* 🇩🇿 !\n\n"
                    "📸 Envoie une *photo de ton frigo* ou 💬 *écris les ingrédients* que tu as,\n"
                    "et je te propose un plat DZ facile + estimation des calories 🍽️🔥"
                )
                send_message(chat_id, welcome)
                return "ok"

            # ✅ Texte (liste ingrédients)
            try:
                gpt_reply = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un chef algérien. Tu reçois une liste d'ingrédients et tu proposes 1 ou 2 plats DZ simples, "
                                "pas chers et adaptés à la réalité algérienne. Ajoute une estimation calorique globale."
                            )
                        },
                        {"role": "user", "content": user_text}
                    ]
                )
                result_text = gpt_reply.choices[0].message.content
            except Exception as e:
                print(f"[GPT Texte Error] {e}")
                result_text = "❌ GPT n'a pas pu répondre. Réessaie plus tard."

            send_message(chat_id, result_text)
            return "ok"

        # ✅ Photo (image du frigo)
        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            send_message(chat_id, "📥 Photo reçue. Analyse en cours…")

            try:
                vision_reply = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un chef algérien. Tu vois l'image du frigo de l'utilisateur. Déduis les ingrédients visibles, "
                                "puis propose un ou deux plats traditionnels DZ faciles à préparer. Ajoute une estimation calorique globale."
                            )
                        },
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_reply.choices[0].message.content
            except Exception as e:
                print(f"[GPT Vision Error] {e}")
                result_text = "❌ L’image n’a pas pu être analysée."

            send_message(chat_id, result_text)
            return "ok"

    return "ok"
