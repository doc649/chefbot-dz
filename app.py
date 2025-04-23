from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "chefbotsecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # 🔍 Si l'utilisateur envoie une photo (image du frigo)
        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            send_message(chat_id, "📸 Image reçue ! Lecture des ingrédients...")

            try:
                vision_response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un chef algérien. Regarde cette image du frigo, détecte les ingrédients visibles "
                                "et propose un ou deux plats traditionnels DZ simples à faire. Donne une estimation calorique approximative."
                            )
                        },
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_response.choices[0].message.content
            except Exception as e:
                print(f"Erreur GPT-Vision: {e}")
                result_text = "❌ Impossible de lire l'image. Réessaie avec une photo plus claire."

            send_message(chat_id, result_text)
            return "ok"

        # ✍️ Si l'utilisateur envoie un texte (liste d’ingrédients)
        user_text = update["message"].get("text", "")
        if user_text:
            try:
                gpt_reply = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un chef algérien. L’utilisateur t’envoie une liste d’ingrédients ou ce qu’il a dans son frigo. "
                                "Propose-lui 1 ou 2 plats DZ simples, économiques, faciles à faire. Donne une estimation des calories totales."
                            )
                        },
                        {"role": "user", "content": user_text}
                    ]
                )
                result_text = gpt_reply.choices[0].message.content
            except Exception as e:
                print(f"Erreur GPT Texte: {e}")
                result_text = "❌ GPT n’a pas pu générer de réponse. Réessaie plus tard."

            send_message(chat_id, result_text)

    return "ok"
