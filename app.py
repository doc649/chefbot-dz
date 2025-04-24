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


@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    print("[ChefBot DZ] Reçu:", update)

    if "message" in update:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"].get("text", "").strip()

        if text:
            try:
                suggestion_prompt = f"راك شاف جزايري. المستخدم عطاك هذه القائمة: {text}. عطي غير 3 اقتراحات متنوعة ومختلفة لوجبات DZ الممكنة فعليًا، بلا تكرار ولا شرح، فقط الاسماء."
                suggestion_reply = openai.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": suggestion_prompt},
                        {"role": "user", "content": text}
                    ]
                )
                plats = suggestion_reply.choices[0].message.content.strip()
                plats_list = list(dict.fromkeys([p.strip() for p in plats.split("\n") if p.strip()]))[:3]
                keyboard = {
                    "inline_keyboard": [[{"text": f"🍽️ {p}", "callback_data": p}] for p in plats_list] + [[{"text": "🔁 اقتراحات أخرى", "callback_data": "autres"}]]
                }
                user_state[chat_id] = plats_list
                send_message(chat_id, f"👨‍🍳 🇩🇿 *اقتراحاتي حسب المكونات المكتوبة:*
" + "\n".join(plats_list) + "\n\n✅ اضغط على اسم الطبق باش نبعثلك الطريقة.", reply_markup=keyboard)
            except Exception as e:
                print(f"Erreur GPT Texte: {e}")
                send_message(chat_id, "❌ ماقدرتش نقترح عليك وصفات.")
            return "ok"

        if "photo" in update["message"]:
            file_id = update["message"]["photo"][-1]["file_id"]
            file_path = get_file_path(file_id)
            image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

            try:
                vision_response = openai.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un expert en cuisine DZ. Donne uniquement la liste des ingrédients visibles dans cette image, en arabe algérien, sans explication."},
                        {"role": "user", "content": [
                            {"type": "text", "text": "Voici l'image de mon frigo ou des ingrédients."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]}
                    ]
                )
                ingredients_detected = vision_response.choices[0].message.content.strip()
                send_message(chat_id, f"📸 *المكونات المستخرجة من الصورة:*\n{ingredients_detected}")

                suggestion_prompt = f"راك شاف جزايري. المستعمل عطاك هذه المكونات: {ingredients_detected}. عطي غير 3 اقتراحات متنوعة ومختلفة لوجبات DZ الممكنة فعليًا، بلا تكرار ولا شرح، فقط الاسماء."
                suggestion_reply = openai.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": suggestion_prompt},
                        {"role": "user", "content": ingredients_detected}
                    ]
                )
                plats = suggestion_reply.choices[0].message.content.strip()
                plats_list = list(dict.fromkeys([p.strip() for p in plats.split("\n") if p.strip()]))[:3]
                keyboard = {
                    "inline_keyboard": [[{"text": f"🍽️ {p}", "callback_data": p}] for p in plats_list] + [[{"text": "🔁 اقتراحات أخرى", "callback_data": "autres"}]]
                }
                user_state[chat_id] = plats_list
                send_message(chat_id, f"👨‍🍳 🇩🇿 *اقتراحاتي حسب الصورة:*\n" + "\n".join(plats_list) + "\n\n✅ اضغط على اسم الطبق باش نبعثلك الطريقة.", reply_markup=keyboard)

            except Exception as e:
                print(f"Erreur GPT-Vision: {e}")
                send_message(chat_id, "❌ ماقدرتش نقرأ الصورة.")
            return "ok"

    if "callback_query" in update:
        query = update["callback_query"]
        chat_id = str(query["message"]["chat"]["id"])
        plat_choisi = query["data"]

        if plat_choisi == "autres":
            send_message(chat_id, "🔁 عاود كتبلي واش كاين عندك فالثلاجة من جديد.")
            return "ok"

        if last_response_sent.get(chat_id) == plat_choisi:
            return "ok"

        try:
            prompt = f"راك شاف جزايري. المستخدم اختار {plat_choisi}. اشرح الطريقة المبسطة لتحضيرها من دون هدرة زايدة. ثم أعط تقدير تقريبي للسعرات الحرارية الكاملة لهذا الطبق."
            gpt_reply = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": plat_choisi}
                ]
            )
            result_text = gpt_reply.choices[0].message.content.strip()
            send_message(chat_id, result_text)
            last_response_sent[chat_id] = plat_choisi
        except Exception as e:
            print(f"[GPT Inline Error] {e}")
            send_message(chat_id, "❌ ماقدرتش نشرح الطريقة.")

    return "ok"
