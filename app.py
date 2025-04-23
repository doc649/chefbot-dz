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
# Mémoire temporaire pour éviter répétition
recent_users = {}

# Envoi d'un message Telegram

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

# Envoi d'un message vocal Telegram (via gtts)
def send_voice(chat_id, text, lang_code="ar"):
    from gtts import gTTS
    from io import BytesIO
    text = text.replace("\n", ". ")[:400]  # Limiter la longueur et répétition
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

        # Bloquer si trop de messages similaires
        if recent_users.get(chat_id) == user_text:
            return "ok"
        recent_users[chat_id] = user_text

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
                "🍽️ نعطيك وصفة رئيسية فقط + السعرات + طريقة التحضير مبسطة.\n"
                "🌐 اللغات المتاحة: /lang_dz (الدارجة), /lang_ar (العربية), /lang_fr (فرنسية)"
            )
            send_message(chat_id, accueil)
            return "ok"

        langue = user_languages.get(chat_id, "darija")

        try:
            if langue == "arabe":
                system_prompt = (
                    "أنت ChefBot DZ، شيف جزائري. أعطي للمستخدم وصفة جزائرية واحدة مناسبة لما أرسله من مكونات،"
                    "بشكل مختصر جدًا دون تكرار أو معلومات غير ضرورية."
                )
            elif langue == "fr":
                system_prompt = (
                    "Tu es ChefBot DZ. Donne une seule recette DZ courte et claire basée sur les ingrédients reçus."
                    "Pas de répétition ni blabla inutile. Ajoute juste les calories et comment faire."
                )
            else:
                system_prompt = (
                    "راك شاف جزايري. المستعمل يكتبلك واش عندو فالدار. عطيلو غير وصفة وحدة بلا هدرة بزاف،"
                    "زيد شوية سعرات وطريقة خفيفة وخلاص."
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
