import os
import requests
import anthropic
from flask import Flask, request

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_KEY = os.environ.get("CLAUDE_KEY")

app = Flask(__name__)
client = anthropic.Anthropic(
    api_key=CLAUDE_KEY,
    timeout=60.0
)

# История диалогов
conversation_history = {}

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)

def ask_claude(chat_id, user_text):
    try:
        if chat_id not in conversation_history:
            conversation_history[chat_id] = []

        conversation_history[chat_id].append({
            "role": "user",
            "content": user_text
        })

        if len(conversation_history[chat_id]) > 20:
            conversation_history[chat_id] = conversation_history[chat_id][-20:]

        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=(
                "Ты — Мария, профессиональный психолог с глубоким уровнем эмпатии. "
                "Твоя цель: поддерживать, слушать и помогать. "
                "Говори тепло, искренне, без лишнего официоза."
            ),
            messages=conversation_history[chat_id]
        )

        response_text = message.content[0].text

        conversation_history[chat_id].append({
            "role": "assistant",
            "content": response_text
        })

        return response_text

    except Exception as e:
        return f"Мария временно недоступна... (Ошибка: {str(e)})"

@app.route("/", methods=["POST"])
def index():
    data = request.get_json(silent=True)
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        if user_text:
            answer = ask_claude(chat_id, user_text)
            send_message(chat_id, answer)

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
