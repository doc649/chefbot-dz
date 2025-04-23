from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = "ordonnasecret"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

@app.route("/ordonnasecret", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            send_message(chat_id, "📥 Ordonnance reçue. Lecture en cours...")

            try:
                vision_response = openai.ChatCompletion.create(
                    model="gpt-4-turbo",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Lis cette ordonnance manuscrite. Tu es un pharmacien algérien. "
                                        "Ne donne que les lignes de médicaments. Ignore les dates, noms, signatures. "
                                        "Donne un résumé clair ligne par ligne."
                                    )
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url, "detail": "high"}
                                }
                            ]
                        }
                    ],
                    max_tokens=1000
                )
                result_text = vision_response.choices[0].message["content"]
            except Exception as e:
                print(f"Erreur GPT-Vision: {e}")
                result_text = "❌ Erreur lors de la lecture de l'image."

            send_message(chat_id, result_text)
            return "ok"

        user_text = update["message"].get("text", "")
        if user_text:
            send_message(chat_id, "📥 Texte reçu. Analyse...")
            prompt = "Tu es un pharmacien algérien. Donne une explication claire et concise du médicament mentionné."
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_text}
                    ]
                )
                gpt_reply = response.choices[0].message["content"]
            except Exception as e:
                print(f"Erreur GPT Texte: {e}")
                gpt_reply = "❌ Erreur lors du traitement du texte."
            send_message(chat_id, gpt_reply)

    return "ok"
