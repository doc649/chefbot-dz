from flask import Flask, request
import os
import requests
import openai

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


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
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
        user_text = update["message"].get("text", "").strip()

        if user_text.lower() == "/stop" and chat_id == ADMIN_ID:
            stop_flags.add(chat_id)
            send_message(chat_id, "✅ Réponses automatiques désactivées.")
            return "ok"

        if user_text.lower() == "/resume" and chat_id == ADMIN_ID:
            stop_flags.discard(chat_id)
            send_message(chat_id, "🔄 Réponses automatiques réactivées.")
            return "ok"

        if chat_id in stop_flags:
            return "ok"

        if recent_users.get(chat_id) == user_text:
            return "ok"
        recent_users[chat_id] = user_text

        if user_text.lower() in ["/lang_dz", "darija"]:
            user_languages[chat_id] = "darija"
            send_message(chat_id, "✅ تم تغيير اللغة إلى الدارجة الجزائرية 🇩🇿")
            return "ok"
        elif user_text.lower() in ["/lang_ar", "arabe"]:
            user_languages[chat_id] = "arabe"
            send_message(chat_id, "✅ تم تغيير اللغة إلى العربية 🇩🇿")
            return "ok"
        elif user_text.lower() in ["/lang_fr", "français"]:
            user_languages[chat_id] = "fr"
            send_message(chat_id, "✅ Langue changée : Français 🇩🇿")
            return "ok"

        if user_text.lower() in ["/start", "start"]:
            accueil = (
                "🇩🇿 *مرحبا بك في ChefBot DZ !* 🇩🇿\n\n"
                "📸 صورلي الثلاجة تاعك، ولا 🗣️ كتبلي واش كاين عندك فالدار،\nباش نقترح عليك أكلة جزائرية مناسبة.\n\n"
                "🍽️ نعطيك 3 اقتراحات لأكلات DZ، واختر واحدة باش نرسللك طريقتها.\n"
                "🌐 اللغات المتاحة: /lang_dz (الدارجة), /lang_ar (العربية), /lang_fr (فرançaise)"
            )
            send_message(chat_id, accueil)
            return "ok"

        langue = user_languages.get(chat_id, "darija")

        if chat_id in user_state:
            plat_choisi = user_text.strip()
            selected = user_state.pop(chat_id)
            try:
                prompt = (
                    f"راك شاف جزايري. المستخدم اختار {plat_choisi} من بين {selected}."
                    f"اشرح كيفاش يحضرها بطريقة مبسطة ومباشرة، بلا هدرة زايدة."
                )
                gpt_reply = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": plat_choisi}
                    ]
                )
                result_text = gpt_reply.choices[0].message.content.strip()
                send_message(chat_id, result_text)
                if langue in ["arabe", "darija"]:
                    send_voice(chat_id, result_text, lang_code="ar")
                return "ok"
            except Exception as e:
                print(f"[GPT Recipe Error] {e}")
                send_message(chat_id, "❌ ماقدرتش نشرح الطريقة.")
                return "ok"

        try:
            if langue == "arabe":
                prompt = (
                    "أنت ChefBot DZ، شيف جزائري. أعط فقط 3 اقتراحات لأكلات جزائرية مشهورة حسب مكونات المستخدم،"
                    "بدون شرح أو تفاصيل. فقط الأسماء مفصولة بسطر جديد."
                )
            elif langue == "fr":
                prompt = (
                    "Tu es ChefBot DZ. Propose 3 plats DZ en fonction des ingrédients, sans explication, juste les noms."
                )
            else:
                prompt = (
                    "راك شاف جزايري. عطي فقط 3 أسماء تاع وجبات DZ لي تصلح حسب المكونات. بلا شرح ولا هدرة زايدة."
                )

            gpt_reply = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_text}
                ]
            )
            plats = gpt_reply.choices[0].message.content.strip()
            user_state[chat_id] = plats
            keyboard = {
                "keyboard": [[{"text": f"🍽️ {p.strip()}"}] for p in plats.split("\n") if p.strip()],
                "resize_keyboard": True,
                "one_time_keyboard": True
            }
            send_message(
                chat_id,
                f"👨‍🍳 🇩🇿 *اقتراحاتي:*\n{plats}\n\n✅ اضغط على اسم الطبق باش نبعثلك الطريقة.",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"[GPT Suggestion Error] {e}")
            send_message(chat_id, "❌ ماقدرتش نجاوب، جرب تعاود.")

    return "ok"
