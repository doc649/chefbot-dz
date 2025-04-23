from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = "chefbotsecret"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

# Fonction d'envoi de message Telegram
def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

# Obtenir le chemin du fichier image sur Telegram
def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

# Webhook pour gérer les messages reçus
@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # Si l'utilisateur envoie une photo d'ingrédients ou de frigo
        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            send_message(chat_id, "📸 Image reçue ! Analyse des ingrédients en cours...")

            try:
                vision_response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un chef cuisinier algérien et nutritionniste. "
                                "Regarde l'image envoyée par l'utilisateur. Identifie les ingrédients visibles "
                                "et propose un ou plusieurs plats algériens traditionnels faciles à préparer avec ce que tu vois. "
                                "Utilise des mots simples, un ton chaleureux, et fais attention à la réalité économique en Algérie. "
                                "Ajoute pour chaque plat une estimation approximative des calories totales."
                            )
                        },
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_response.choices[0].message.content
            except Exception as e:
                print(f"Erreur GPT Vision: {e}")
                result_text = "❌ Impossible d'analyser l'image. Essaie une photo plus nette."

            send_message(chat_id, result_text)
            return "ok"

        # Si l'utilisateur envoie un texte (liste d'ingrédients)
        user_text = update["message"].get("text", "")
        if user_text:
            try:
                gpt_reply = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Tu es un chef cuisinier algérien et nutritionniste. "
                                "Tu connais les ingrédients locaux, les plats traditionnels DZ, les habitudes alimentaires algériennes "
                                "et les contraintes économiques. Quand l'utilisateur t'envoie une liste d'ingrédients ou ce qu'il a dans son frigo, "
                                "propose-lui des plats algériens simples, pas chers, faciles à préparer, et utilise un langage chaleureux et familier. "
                                "Ajoute pour chaque plat une estimation approximative des calories totales."
                            )
                        },
                        {"role": "user", "content": user_text}
                    ]
                )
                result_text = gpt_reply.choices[0].message.content
            except Exception as e:
                print(f"Erreur GPT Texte: {e}")
                result_text = "❌ Une erreur est survenue. Réessaie plus tard."

            send_message(chat_id, result_text)

    return "ok"
