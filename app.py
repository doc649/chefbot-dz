from flask import Flask, request
import requests
import os
import openai
import json
import difflib

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "ordonnasecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

# 🌐 Stockage temporaire des langues utilisateur
user_langs = {}

# 📂 Charger base de médicaments DZ
with open("medicament.json", "r", encoding="utf-8") as f:
    medicaments_db = json.load(f)

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

def corriger_nom_medicament(mot, dosage=None):
    candidats = []
    for med in medicaments_db:
        nom = med.get("nom", "").lower()
        if difflib.SequenceMatcher(None, mot.lower(), nom).ratio() >= 0.75:
            if dosage:
                if dosage.lower() in med.get("dosage", "").lower():
                    return med["nom"]
            else:
                return med["nom"]
    return None

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # 📸 Traitement des images (GPT-4 Vision)
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
                                {"type": "text", "text": (
                                    "Lis cette ordonnance médicale manuscrite et résume uniquement les médicaments, doses et fréquence en 3 lignes maximum. "
                                    "Ensuite, ajoute une seule phrase finale courte avec un conseil ou alerte si possible (effet secondaire, interaction ou mise en garde). "
                                    "Ne répète pas d'informations inutiles. Sois rapide, clair et orienté patient."
                                )},
                                {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
                            ]
                        }
                    ],
                    max_tokens=750
                )
                result_text = vision_response.choices[0].message["content"]

                # 🔎 Correction auto sur base DZ
                mots = result_text.split()
                mots_corriges = []
                for mot in mots:
                    correction = corriger_nom_medicament(mot)
                    if correction:
                        mots_corriges.append(correction.upper())
                    else:
                        mots_corriges.append(mot)

                result_text = " ".join(mots_corriges)

            except Exception as e:
                print(f"Erreur GPT-Vision: {e}")
                result_text = "❌ Une erreur est survenue pendant l'analyse de l'image."

            send_message(chat_id, result_text)
            return "ok"

        # 📟 Texte normal (non image)
        user_text = update["message"].get("text", "")
        if user_text:
            message_clean = user_text.lower().strip()

            if message_clean == "/start":
                welcome_message = (
                    "👋 Marhba bik sur OrdonnaBot DZ 🇩🇿\n\n"
                    "📷 Envoie une ordonnance en texte ou en photo.\n\n"
                    "🗣️ Choisis ta langue : /langue_fr, /langue_dz, /langue_ar"
                )
                send_message(chat_id, welcome_message)
                return "ok"

            if message_clean == "/langue_fr": user_langs[chat_id] = "fr"; send_message(chat_id, "✅ Français activé")
            elif message_clean == "/langue_dz": user_langs[chat_id] = "dz"; send_message(chat_id, "✅ Darija activé")
            elif message_clean == "/langue_ar": user_langs[chat_id] = "ar"; send_message(chat_id, "✅ تم تغيير اللغة")

            # 🔠 GPT classique pour le texte
            langue = user_langs.get(chat_id, "fr")
            if langue == "dz":
                prompt = "Réponds en darija DZ claire et courte."
            elif langue == "ar":
                prompt = "اشرح وصفة طبية بلغة عربية فصحى مبسطة."
            else:
                prompt = "Tu es OrdonnaBot DZ. Réponds en français clair, utile, et rapide."

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
                gpt_reply = "❌ Erreur pendant l'analyse."

            send_message(chat_id, gpt_reply)
    return "ok"
