from flask import Flask, request
import requests
import os
import openai
import json
import difflib

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = "ordonnasecret"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

# 🌐 Stockage temporaire des langues utilisateur
user_langs = {}

# 📂 Charger base de médicaments DZ
with open("medicament.json", "r", encoding="utf-8") as f:
    medicaments_db = json.load(f)

# 📘 Dictionnaire des abréviations médicales locales
abreviations = {
    "dolipr": "doliprane",
    "augment": "augmentin",
    "amox": "amoxicilline",
    "spasf": "spasfon",
    "relax": "relaxan",
    "valda": "valda",
    "parac": "paracetamol",
    "smect": "smecta",
    "rulid": "rulid",
    "celeb": "celebrex",
    "feld": "feldene",
    "ibup": "ibuprofene",
    "keto": "ketoprofene",
    "prof": "profenid",
    "nuro": "nurofen",
    "advil": "advil",
    "algif": "algifen",
    "bruf": "brufen"
}

# 🥄 Abréviations posologiques + unités médicales issues du PDF
abreviations_dosage = {
    "c.a.s": "cuillère à soupe",
    "cas": "cuillère à soupe",
    "c.a.c": "cuillère à café",
    "cac": "cuillère à café",
    "c.a.d": "cuillère à dessert",
    "gtt": "gouttes",
    "cp": "comprimé",
    "supp": "suppositoire",
    "inj": "injection",
    "amp": "ampoule",
    "gel": "gélule",
    "id": "intradermique",
    "im": "intramusculaire",
    "iv": "intraveineux",
    "sc": "sous-cutané",
    "po": "par voie orale",
    "ai": "anti-inflammatoire",
    "ains": "anti-inflammatoire non stéroïdien"
}

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_file_path(file_id):
    response = requests.get(f"{BOT_URL}/getFile?file_id={file_id}")
    return response.json()["result"]["file_path"]

def corriger_nom_medicament_ligne(ligne):
    # Remplacement manuel d'erreurs orthographiques fréquentes
    corrections_typiques = {
        "dolipprane": "doliprane",
        "amoxycilline": "amoxicilline",
        "bruffen": "brufen",
        "ibuprofeen": "ibuprofene",
        "paracetaml": "paracetamol",
        "algifenn": "algifen"
    }

    # Nettoyage initial : retirer les caractères parasites
    ligne = ligne.replace(':', ' ').replace('/', ' ').replace('°', '').replace('.', ' ')
    ligne = ligne.replace('-', ' ').replace(',', ' ').replace(';', ' ')

    for faute, correction in corrections_typiques.items():
        ligne = ligne.replace(faute, correction)

    mots = ligne.strip().split()
    if not mots:
        return ligne

    meilleur_match = None
    meilleur_score = 0.0

    for med in medicaments_db:
        nom_commercial = med.get("nom", "").lower()
        for mot in mots:
            mot_normalise = abreviations.get(mot.lower(), mot.lower())
            if len(mot_normalise) > 3:
                if mot_normalise in nom_commercial:
                    score = 1.0
                else:
                    score = difflib.SequenceMatcher(None, mot_normalise, nom_commercial).ratio()
            else:
                score = 0

            if score > meilleur_score:
                meilleur_score = score
                meilleur_match = med

    if meilleur_score >= 0.85 and meilleur_match:
        nom_corrige = meilleur_match["nom"].upper()
        dosage = meilleur_match.get("dosage", "")
        labo = meilleur_match.get("laboratoire", "")

        ligne_dosage = " ".join([
            abreviations_dosage.get(m.lower(), m) for m in mots if m.lower() in abreviations_dosage
        ])

        ligne_corrigee = f"💊 {nom_corrige} - {dosage} - {labo} {ligne_dosage}"
        return ligne_corrigee
    else:
        return f"❓ {ligne}  (non reconnu, vérifie l'écriture)"

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
                noms_medicaments = ", ".join([m['nom'] for m in medicaments_db if 'nom' in m][:150])
                vision_response = openai.ChatCompletion.create(
                    model="gpt-4-turbo",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Lis cette ordonnance manuscrite. Tu es un pharmacien algérien. "
                                        "Ne donne que les lignes de médicaments. Ignore les dates, noms, signatures. "
                                        "Base-toi sur cette liste : " + noms_medicaments + ". "
                                        "Donne la réponse ligne par ligne."
                                    )
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url, "detail": "high"}
                                }
                            ]
                        }
                    ],
                    max_tokens=750
                )
                result_text = vision_response.choices[0].message["content"]
                lignes = result_text.split("\n")
                lignes_corrigees = [corriger_nom_medicament_ligne(l) for l in lignes]
                result_text = "\n".join(lignes_corrigees)
            except Exception as e:
                print(f"Erreur GPT-Vision: {e}")
                result_text = "❌ Erreur lors de la lecture de l'image."

            send_message(chat_id, result_text)
            return "ok"

        user_text = update["message"].get("text", "")
        if user_text:
            send_message(chat_id, "📥 Texte reçu. Analyse...")
            prompt = "Tu es un pharmacien algérien. Donne une explication courte et claire."
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
