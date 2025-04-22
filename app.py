from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ordonnasecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

# 🌐 Stockage temporaire des langues utilisateur (session uniquement)
user_langs = {}

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"].get("text", "")

        if user_text:
            message_clean = user_text.lower().strip()

            # 🎬 Message d'accueil /start
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
                requests.post(f"{BOT_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": welcome_message
                })
                return "ok"

            # 🔁 Commandes de changement de langue
            if message_clean == "/langue_fr":
                user_langs[chat_id] = "fr"
                requests.post(f"{BOT_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "✅ Langue changée en français."
                })
                return "ok"

            if message_clean == "/langue_dz":
                user_langs[chat_id] = "dz"
                requests.post(f"{BOT_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "✅ Langue changée en darija DZ (lettres latines)."
                })
                return "ok"

            if message_clean == "/langue_ar":
                user_langs[chat_id] = "ar"
                requests.post(f"{BOT_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "✅ تم تغيير اللغة إلى العربية."
                })
                return "ok"

            # 🧼 Blocage des messages inutiles
            interdits = ["bonjour", "salut", "cc", "slt", "merci", "ok", "hello", "test", "wesh"]
            if message_clean in interdits:
                print("💥 INTERCEPTION ACTIVE BY HAMZA : message bloqué ->", message_clean)
                requests.post(
                    f"{BOT_URL}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "🧾 Envoie une ordonnance pour que je puisse t'aider. Tu peux choisir la langue avec /langue_fr ou /langue_dz ou /langue_ar."
                    }
                )
                return "ok"

            # 🧠 Choix du prompt GPT selon la langue
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

            # 🤖 Appel GPT
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

            requests.post(
                f"{BOT_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": gpt_reply
                }
            )
    return "ok"
