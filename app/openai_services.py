import openai
import requests
from app.config import OPENAI_API_KEY, TELEGRAM_TOKEN
from app.recipe_generator import generate_recipes
from app.meal_planner import generate_meal_plan, estimate_calories, generate_shopping_list

openai.api_key = OPENAI_API_KEY

def process_text(text):
    if "plan repas" in text.lower():
        return generate_meal_plan()
    elif "courses" in text.lower():
        return generate_shopping_list(text)
    elif "calorie" in text.lower():
        return estimate_calories(text)
    else:
        return generate_recipes(text)

def process_image(file_id):
    # Get Telegram file URL
    file_path = get_file_path(file_id)
    if not file_path:
        return "Impossible de récupérer l'image."
    image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

    # GPT-4 Vision API call
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "Quels ingrédients reconnais-tu dans cette image ? Donne-moi uniquement les noms d'ingrédients, séparés par des virgules."},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ],
            max_tokens=300
        )
        ingredients = response.choices[0].message.content.strip()
        return generate_recipes(ingredients)
    except Exception as e:
        return f"Erreur lors de l'analyse de l'image : {str(e)}"

def get_file_path(file_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
    try:
        r = requests.get(url)
        file_path = r.json()["result"]["file_path"]
        return file_path
    except:
        return None
