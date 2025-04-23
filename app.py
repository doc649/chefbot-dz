from flask import Flask, request
import requests
import os
import openai
import tempfile

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
@app.route("/chefbotsecret", methods=["POST"])
def webhook():
    update = request.get_json()
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

        # Si l'utilisateur envoie une photo d'ingrédients ou du frigo
        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            send_message(chat_id, "📸 Image reçue ! Analyse des ingrédients en cours...")

            try:
                # Appel GPT-4 Vision (exemple simulé)
                vision_response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {"role": "system", "content": "Tu es un chef cuisinier algérien et nutritionniste. Regarde l'image, identifie les ingrédients visibles, puis propose un ou plusieurs plats algériens traditionnels que l'utilisateur peut préparer avec. Inspire-toi des plats du quotidien des familles algériennes, utilise des termes familiers et simples, et fais attention aux réalités économiques. Pour chaque plat, donne aussi une estimation approximative des calories totales (pas par ingrédient)."},
                        {"role": "user", "content": image_url}
                    ]
                )
                result_text = vision_response.choices[0].message.content
            except Exception as e:
                print(f"Erreur GPT Vision: {e}")
                result_text = "❌ Impossible d'analyser cette image. Réessaie avec une photo plus claire du frigo ou des ingrédients."

            send_message(chat_id, result_text)
            return "ok"

        # Si l'utilisateur envoie un message texte (liste d'ingrédients ou demande de recette)
        user_text = update["message"].get("text", "")
        if user_text:
            try:
                gpt_reply = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Tu es un chef cuisinier algérien et nutritionniste. Tu vis en Algérie et tu connais bien les habitudes alimentaires, les ingrédients locaux, les plats traditionnels, les contraintes économiques et les goûts des familles algériennes. L'utilisateur te donne ce qu'il a dans son frigo ou une liste d'ingrédients. Propose-lui un ou plusieurs plats traditionnels algériens simples, bon marché et adaptés à la réalité des foyers algériens. Utilise un langage familier, simple et chaleureux. Pour chaque plat, donne aussi une estimation approximative des calories totales (pas par ingrédient)."},
                    {"role": "user", "content": user_text}
                ]
            )
                result_text = gpt_reply.choices[0].message.content
            except Exception as e:
                print(f"Erreur GPT Texte: {e}")
                result_text = "❌ Erreur lors de la génération du menu."

            send_message(chat_id, result_text)

    return "ok"
