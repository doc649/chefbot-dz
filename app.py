from flask import Flask, request
import requests
import os
import openai
import tempfile
import base64
import json

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = "ordonnasecret"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY")

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

def run_ocr_google_vision(image_path):
    with open(image_path, "rb") as image_file:
        content = base64.b64encode(image_file.read()).decode("utf-8")

    vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {
        "requests": [
            {
                "image": {"content": content},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }
    response = requests.post(vision_url, headers=headers, json=body)
    result = response.json()
    try:
        text = result["responses"][0]["fullTextAnnotation"]["text"]
    except:
        text = ""
    return text

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
                # Téléchargement temporaire de l'image pour OCR
                response = requests.get(image_url)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_path = tmp_file.name

                # Lecture avec Google Cloud Vision API
                ocr_text = run_ocr_google_vision(tmp_path)

                # Passage à GPT pour résumé pharmacien
                gpt_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un pharmacien algérien. Corrige et explique les lignes de prescription suivantes."},
                        {"role": "user", "content": ocr_text}
                    ]
                )
                result_text = gpt_response.choices[0].message["content"]

            except Exception as e:
                print(f"Erreur OCR ou GPT: {e}")
                result_text = "❌ Erreur lors de la lecture ou de l'analyse."

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
