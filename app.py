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

# Mémoire simple des langues par session (en RAM, pas persisté)
user_languages = {}

# Envoi d'un message Telegram

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

# Envoi d'un message vocal Telegram (via gtts)
def send_voice(chat_id, text, lang_code="ar"):
    from gtts import gTTS
    from io import BytesIO
    text = text.replace("\n", ". ")[:400]  # Limiter les répétitions et la longueur
    audio = gTTS(text=text, lang=lang_code)
    mp3_fp = BytesIO()
    audio.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    files = {"voice": ("voice.ogg", mp3_fp, "audio/ogg")}
    requests.post(f"{BOT_URL}/sendVoice", data={"chat_id": chat_id}, files=files)

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
        user_text = update["message"].get("text", "").strip()

        # Commande de langue
        if user_text.lower() in ["/lang_dz", "darija"]:
            user_languages[chat_id] = "darija"
            send_message(chat_id, "✅ تم تغيير اللغة إلى الدارجة الجزائرية")
            return "ok"
        elif user_text.lower() in ["/lang_ar", "arabe"]:
            user_languages[chat_id] = "arabe"
            send_message(chat_id, "✅ تم تغيير اللغة إلى العربية")
            return "ok"
        elif user_text.lower() in ["/lang_fr", "français"]:
            user_languages[chat_id] = "fr"
            send_message(chat_id, "✅ Langue changée : Français")
            return "ok"

        # Message d'accueil
        if user_text.lower() in ["/start", "start"]:
            accueil = (
                "🌟 *مرحبا بك في ChefBot DZ !* 🌟\n\n"
                "📸 صورلي الثلاجة تاعك، ولا 🗣️ كتبلي واش كاين عندك فالدار،\nباش نقترح عليك أكلة جزائرية مناسبة.\n\n"
                "🍽️ نعطيك وصفة رئيسية + بدائل + السعرات + طريقة التحضير مبسطة.\n"
                "🌐 اللغات المتاحة: /lang_dz (الدارجة), /lang_ar (العربية), /lang_fr (فرنسية)"
            )
            send_message(chat_id, accueil)
            return "ok"

        langue = user_languages.get(chat_id, "darija")

        try:
            if langue == "arabe":
                system_prompt = (
                    "أنت ChefBot DZ، شيف جزائري. المستخدم يرسل المكونات، وأنت تقترح أكلة جزائرية واحدة فقط،"
                    "بدون تكرار، مع تقدير السعرات وطريقة مختصرة."
                )
            elif langue == "fr":
                system_prompt = (
                    "Tu es ChefBot DZ. Propose UNE seule recette DZ selon les ingrédients, sans te répéter."
                    "Ajoute une estimation de calories et une brève explication."
                )
            else:
                system_prompt = (
                    "راك شاف جزايري. المستخدم يكتبلك واش كاين. عطيلو غير أكلة وحدة مناسبة،"
                    "بلا تكرار ولا هدرة بزاف، زيد السعرات وطريقة مختصرة."
                )

            gpt_reply = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ]
            )
            result_text = gpt_reply.choices[0].message.content.strip()
        except Exception as e:
            print(f"[GPT Text Error] {e}")
            result_text = "❌ ماقدرتش نجاوب، جرب تعاود."

        send_message(chat_id, result_text)
        if langue in ["arabe", "darija"]:
            send_voice(chat_id, result_text, lang_code="ar")
        return "ok"

    return "ok"
