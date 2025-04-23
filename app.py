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
    print(f"[DEBUG] Envoi message → {chat_id}")
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

# Récupération de l'image Telegram
def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

# Webhook principal
@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("[DEBUG] Message Telegram reçu :", update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # Message de démarrage
        if "text" in update["message"]:
            user_text = update["message"]["text"].strip()

            if user_text.lower() in ["/start", "start"]:
                accueil = (
                    "\ud83c\udf1f *مرحبا بيك في شاف بوت ديزاد !* \ud83c\udf1f\n\n"
                    "\ud83d\udcf8 صوّرلي ثلاجتك ولا \ud83d\udcac كتبلي شنو كاين عندك من مكونات،\n"
                    "ونعطيك واش تطيب اليوم + عدد تقريبي ديال الكالوري \ud83c\udf5c\ud83d\udd25"
                )
                send_message(chat_id, accueil)
                return "ok"

            # Analyse texte (liste d'ingrédients)
            try:
                gpt_reply = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "راك شاف جزائري. المستخدم كي يكتبلك شنو كاين عندو، تقترح عليه وصفة ولا جوج جزائرية تقليدية، سهلة ورخيصة. "
                                "وضح الطريقة باختصار، وكتب تقدير ديال الكالوري فالأخير."
                            )
                        },
                        {"role": "user", "content": user_text}
                    ]
                )
                result_text = gpt_reply.choices[0].message.content
            except Exception as e:
                print(f"[GPT Texte Error] {e}")
                result_text = "❌ ماقدرتش نجاوبك، جرب مرّة أخرى."

            send_message(chat_id, result_text)
            return "ok"

        # Analyse photo (contenu du frigo)
        if "photo" in update["message"]:
            try:
                file_id = update["message"]["photo"][-1]["file_id"]
                file_path = get_file_path(file_id)
                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
                send_message(chat_id, "\ud83d\udcc5 الصورة وصلات، كنحلل فيها...")

                vision_reply = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "راك شاف جزائري. شوف الصورة ديال الثلاجة، خرج منها المكونات، و اقترح أطباق DZ لي نقدر نوجدهم. "
                                "ماتنسايش تكتب عدد تقريبي ديال الكالوري."
                            )
                        },
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_reply.choices[0].message.content
            except Exception as e:
                print(f"[GPT Vision Error] {e}")
                result_text = "❌ ماقدرتش نقرا الصورة، جرب واحدة أوضح."

            send_message(chat_id, result_text)
            return "ok"

    return "ok"
