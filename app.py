from flask import Flask, request
import requests
import os
import openai
import easyocr
import tempfile

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = "ordonnasecret"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

reader = easyocr.Reader(['fr', 'en'], gpu=False)

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

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

                # Lecture avec EasyOCR
                results = reader.readtext(tmp_path, detail=0)
                ocr_text = "\n".join(results)

                # Passage à GPT-3.5 turbo pour résumé pharmacien
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
