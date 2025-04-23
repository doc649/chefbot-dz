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

        # Détection de la langue choisie (default : darija)
        langue = user_languages.get(chat_id, "darija")

        # Traitement texte (ingrédients)
        try:
            if langue == "arabe":
                system_prompt = (
                    "أنت ChefBot DZ، شيف جزائري تقترح وصفات تقليدية بناءً على ما يرسله المستخدم من مكونات.\n"
                    "اقترح وصفة أساسية + وصفات بديلة إن أمكن، مع تقدير السعرات الحرارية، وطريقة التحضير باختصار."
                )
            elif langue == "fr":
                system_prompt = (
                    "Tu es ChefBot DZ, un chef algérien. Tu proposes des recettes DZ selon les ingrédients fournis.\n"
                    "Propose une recette principale + alternatives, estimation des calories, et brève préparation."
                )
            else:
                system_prompt = (
                    "راك شاف جزايري. المستعمل يكتبلك واش كاين عندو. انت تقترح عليه أكلة جزائرية مناسبة،\nمع 2 اختيارات بديلة، والسعرات الحرارية، وطريقة التحضير فـ3 سطور."
                )

            gpt_reply = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ]
            )
            result_text = gpt_reply.choices[0].message.content
        except Exception as e:
            print(f"[GPT Text Error] {e}")
            result_text = "❌ ماقدرتش نجاوب، جرب تعاود."

        send_message(chat_id, result_text)
        if langue in ["arabe", "darija"]:
            send_voice(chat_id, result_text, lang_code="ar")
        return "ok"

        # Traitement photo (vision GPT-4)
        if "photo" in update["message"]:
            try:
                file_id = update["message"]["photo"][-1]["file_id"]
                file_path = get_file_path(file_id)
                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
                send_message(chat_id, "📸 تم استلام الصورة! نحاول نفهم واش كاين...")

                vision_response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_response.choices[0].message.content
            except Exception as e:
                print(f"[GPT Vision Error] {e}")
                result_text = "❌ ماقدرتش نقرا الصورة. جرب وحدة أوضح."

            send_message(chat_id, result_text)
            if langue in ["arabe", "darija"]:
                send_voice(chat_id, result_text, lang_code="ar")
            return "ok"

    return "ok"
