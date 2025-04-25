from flask import Flask, request, jsonify
from app.telegram_handler import handle_update
from app.config import TELEGRAM_TOKEN

app = Flask(__name__)

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    return handle_update(update)

if __name__ == "__main__":
    app.run(debug=True)
