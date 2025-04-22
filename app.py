from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ordonnasecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

# 🌐 Stockage temporaire des langues utilisateur
user_langs = {}

# 📩 Envoi d’un message texte
def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# 📷 Récupération du chemin d’une image Telegram
def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # 📸 Si l'utilisateur envoie une photo
        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

            send_message(chat_id, "📸 Image reçue. Traitement IA en cours...")

            try:
                vision_response = openai.ChatCompletion.create(
                    model="gpt-4-turbo",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Lis et décris cette ordonnance médicale comme si tu étais un pharmacien algérien. Résume les médicaments, doses, et posologie de manière claire."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": image_url,
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000
                )

                result_text = vision_response.choices[0].message["content"]

            except Exception as e:
                print(f"Erreur GPT-Vision: {e}")
                result_text = "❌ Une erreur est survenue pendant l'analyse de l'image."

            send_message(chat_id, result_text)
            return "ok"

        # 🧾 Traitement texte normal
        user_text = update["message"].get("text", "")
        if user_text:
            message_clean = user_text.lower().strip()

            # 🎬 /start
            if message_clean == "/start":
                welcome_message = (
                    "👋 Marhba bik sur OrdonnaBot DZ 🇩🇿\n\n"
                    "📷 Envoie une ordonnance en texte ou en photo.\n\n"
                    "🗣️ Choisis ta langue de réponse :\n"
                    "/langue_fr → Français\n"
                    "/langue_dz → Darija DZ (lettres latines)\n"
                    "/langue_ar → العربية\n\n"
                    "🧾 Je vais t'expliquer ton ordonnance de manière claire et simple."
                )
                send_message(chat_id, welcome_message)
                return "ok"

            # 🔁 Langue
            if message_clean == "/langue_fr":
                user_langs[chat_id] = "fr"
                send_message(chat_id, "✅ Langue changée en français.")
                return "ok"

            if message_clean == "/langue_dz":
                user_langs[chat_id] = "dz"
                send_message(chat_id, "✅ Langue changée en darija DZ (lettres latines).")
                return "ok"

            if message_clean == "/langue_ar":
                user_langs[chat_id] = "ar"
                send_message(chat_id, "✅ تم تغيير اللغة إلى العربية.")
                return "ok"

            # 🧼 Filtrage
            interdits = ["bonjour", "salut", "cc", "slt", "merci", "ok", "hello", "test", "wesh"]
            if message_clean in interdits:
                print("💥 INTERCEPTION ACTIVE BY HAMZA : message bloqué ->", message_clean)
                send_message(chat_id, "🧾 Envoie une ordonnance pour que je puisse t'aider. Tu peux choisir la langue avec /langue_fr ou /langue_dz ou /langue_ar.")
                return "ok"

            # 🔠 Prompt selon langue
            langue = user_langs.get(chat_id, "fr")
            if langue == "dz":
                prompt = (
                    "Réponds en darija algérienne (lettres latines). "
                    "Sois court, clair, sans bavardage. Décris les médicaments et comment les prendre."
                )
            elif langue == "ar":
                prompt = (
                    "أنت مساعد طبي اسمه OrdonnaBot. تشرح وصفات الأدوية بلغة عربية فصحى مبسطة ومباشرة. "
                    "يجب أن تكون الردود قصيرة، واضحة، ومناسبة للمرضى لفهم العلاج."
                )
            else:
                prompt = (
                    "Tu es OrdonnaBot, un assistant médical algérien. "
                    "Tu aides les gens à comprendre leurs ordonnances et les traitements prescrits. "
                    "Réponds toujours de manière claire, bienveillante, et en français. "
                    "Ne dis jamais 'bonjour', ni 'comment puis-je vous aider'."
                )

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
                print(f"Erreur GPT: {e}")
                gpt_reply = "❌ Une erreur est survenue. Veuillez réessayer plus tard."

            send_message(chat_id, gpt_reply)
    return "ok"
