from flask import Flask, request
import os
import requests
import openai

app = Flask(__name__)

# Configuration des variables d'environnement
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "chefbotsecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"
openai.api_key = os.getenv("OPENAI_API_KEY")

# Envoi d'un message Telegram
def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

# Récupération de l'image Telegram
def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

# Webhook principal
@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("[ChefBot DZ] Reçu:", update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # Message d'accueil
        if "text" in update["message"]:
            user_text = update["message"]["text"].strip()
            if user_text.lower() in ["/start", "start"]:
                accueil = (
                    "\ud83c\udf1f *Marhba bik f ChefBot DZ !* \ud83c\udf1f\n\n"
                    "\ud83d\udcf8 Sowerli thalajtek, wela \ud83d\udcac ktibli chno kayen 3andek, w n9olak wach t9dar tdiro lyoma.\n\n"
                    "\ud83c\udf5c N3tik wa7ed lwasfa DZ + estmation dyal calories."
                )
                send_message(chat_id, accueil)
                return "ok"

            # Traitement texte (ingrédients)
            try:
                gpt_reply = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": (
                            "Rak chef DZ. L'utilisateur yktblk les ingrédients li 3ando, nti tqtrah 3lih wa7ed lwasfa DZ s7ila, ma tkhltech. Ajout estimation calories.")},
                        {"role": "user", "content": user_text}
                    ]
                )
                result_text = gpt_reply.choices[0].message.content
            except Exception as e:
                print(f"[GPT Text Error] {e}")
                result_text = "❌ Ma9dartch nrd, jarrab 3awd tani."

            send_message(chat_id, result_text)
            return "ok"

        # Traitement photo (vision GPT-4)
        if "photo" in update["message"]:
            try:
                file_id = update["message"]["photo"][-1]["file_id"]
                file_path = get_file_path(file_id)
                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
                send_message(chat_id, "\ud83d\udcf8 Soura t9blat ! N7awel nfham chno kayen...")

                vision_response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {"role": "system", "content": (
                            "Rak chef DZ. L'utilisateur sowlak wa7ed soura dyal thalajtk. 7awel t3raf chno fih, w tqtrah wa7ed lwasfa DZ + calories")},
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_response.choices[0].message.content
            except Exception as e:
                print(f"[GPT Vision Error] {e}")
                result_text = "❌ Ma9dartch nqra had soura. Jarrab wa7da waD7a."

            send_message(chat_id, result_text)
            return "ok"

    return "ok"
