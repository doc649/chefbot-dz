import requests
from flask import jsonify
from app.openai_services import process_text, process_image
from app.config import TELEGRAM_TOKEN, ADMIN_ID

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def handle_update(update):
    if "message" not in update:
        return jsonify({"status": "no message"})

    message = update["message"]
    chat_id = message["chat"]["id"]

    if "text" in message:
        response = process_text(message["text"])
        send_message(chat_id, response)

    elif "photo" in message:
        file_id = message["photo"][-1]["file_id"]  # get highest quality image
        response = process_image(file_id)
        send_message(chat_id, response)

    return jsonify({"status": "ok"})


def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })
