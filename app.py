from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "chefbotsecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def send_message(chat_id, text):
    print(f"[DEBUG] Envoi message à {chat_id} : {text[:60]}...")
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    print(f"[DEBUG] Récupération file_id: {file_id}")
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("[DEBUG] Update reçu :", update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # 📸 Partie PHOTO
        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            send_message(chat_id, "📸 Image reçue ! Lecture des ingrédients...")

            try:
                vision_response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {"role": "system", "content": "Tu es un chef algérien..."},
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_response.choices[0].message.content
            except Exception as e:
                print(f"[ERREUR GPT Vision] {e}")
                result_text = "❌ Impossible de lire l'image."

            send_message(chat_id, result_text)
            return "ok"

        # 💬 Partie TEXTE
        user_text = update["message"].get("text", "")
        if user_text:
            print(f"[DEBUG] Message texte reçu : {user_text}")
            try:
                gpt_reply = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un chef algérien..."},
                        {"role": "user", "content": user_text}
                    ]
                )
                result_text = gpt_reply.choices[0].message.content
            except Exception as e:
                print(f"[ERREUR GPT Texte] {e}")
                result_text = "❌ GPT n’a pas pu générer de réponse."

            send_message(chat_id, result_text)

    return "ok"
