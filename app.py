from flask import Flask, request
import os
import requests
import openai
import json

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "chefbotsecret")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"
openai.api_key = os.getenv("OPENAI_API_KEY")

ADMIN_ID = os.getenv("ADMIN_ID", "866358358")

user_languages = {}
recent_users = {}
stop_flags = set()
user_state = {}
last_response_sent = {}

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{BOT_URL}/sendMessage", json=payload)

def send_voice(chat_id, text, lang_code="ar"):
    from gtts import gTTS
    from io import BytesIO
    text = text.replace("\n", ". ")[:400]
    audio = gTTS(text=text, lang=lang_code)
    mp3_fp = BytesIO()
    audio.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    files = {"voice": ("voice.ogg", mp3_fp, "audio/ogg")}
    requests.post(f"{BOT_URL}/sendVoice", data={"chat_id": chat_id}, files=files)

def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

def download_file(file_path):
    url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    response = requests.get(url)
    return response.content

def transcribe_audio(file_bytes):
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
        temp_audio.write(file_bytes)
        temp_audio_path = temp_audio.name
    with open(temp_audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("[ChefBot DZ] Reçu:", update)

        # Exemple de réponse multilignes corrigée
        if text == "test_multiligne":
            send_message(chat_id, (
                "👨‍🍳 🇩🇿 *اقتراحاتي حسب المكونات المكتوبة:*
"
                "1. شربة فريك
"
                "2. بطاطا في الفور
"
                "3. كسكسي بالخضرة
"
                "✅ اضغط على اسم الطبق باش نبعثلك الطريقة."
            ))
            return "ok"

    if "message" in update:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"].get("text", "").strip()

        if text.startswith("/forcer_reset") and chat_id == ADMIN_ID:
            last_response_sent.pop(chat_id, None)
            send_message(chat_id, "✅ Cache utilisateur réinitialisé.")
            return "ok"

        if text.startswith("/stop") and chat_id == ADMIN_ID:
            stop_flags.add(chat_id)
            send_message(chat_id, "🛑 Réponses du bot suspendues pour cet utilisateur.")
            return "ok"

        if text.startswith("/voice"):
            # Admin or user triggers a voice reply of the last sent text
            last_text = last_response_sent.get(chat_id)
            if last_text:
                send_voice(chat_id, last_text, lang_code="ar")
                send_message(chat_id, "🔊 Voici la version vocale de la recette !")
            else:
                send_message(chat_id, "ℹ️ Aucune réponse récente à lire.")
            return "ok"

        if chat_id in stop_flags:
            return "ok"

        if "voice" in update["message"]:
            file_id = update["message"]["voice"]["file_id"]
            try:
                file_path = get_file_path(file_id)
                file_bytes = download_file(file_path)
                transcribed_text = transcribe_audio(file_bytes)
                send_message(chat_id, f"🗣️ *Texte reconnu:* {transcribed_text}")
                update["message"]["text"] = transcribed_text  # Inject the transcribed text
                update["message"].pop("voice", None)
                return webhook()  # Relancer le traitement avec le texte injecté
            except Exception as e:
                print("[Erreur transcription]", e)
                send_message(chat_id, "❌ Échec de la reconnaissance vocale.")
                return "ok"

    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = str(query["message"]["chat"]["id"])
        plat_choisi = query["data"]

        if chat_id in stop_flags:
            return "ok"

    return "ok"
