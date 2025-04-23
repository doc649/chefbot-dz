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
            # correction auto basique : si une lettre est enlevée ou mal tapée
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

        # Remplacement des formes posologiques abrégées
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
    send_message(update["message"]["chat"]["id"], "📥 Ordonnance reçue. Traitement en cours...")
    return "ok"
