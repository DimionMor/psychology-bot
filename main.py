import os
import requests
import random
from openai import OpenAI
from flask import Flask, request
import threading
import time

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_KEY")

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_KEY)

# Хранилище данных пользователей
user_data = {}
USERS_FILE = '/tmp/users.txt'

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return set(int(x.strip()) for x in f.readlines() if x.strip())
    except:
        return set()

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            for uid in users:
                f.write(str(uid) + '
')
    except:
        pass

all_users = load_users()

# Карточки психологов (заглушка)
PSYCHOLOGISTS = [
    {
        "name": "Яна, 37 лет",
        "description": "В своей работе с клиентами я не навязываю решения, а создаю условия, в которых клиент сам учится находить собственные пути к изменениям. Опыт работы с паническими атаками, депрессией, переживанием потерь.",
        "compatibility": 80,
        "contact": "Запись временно недоступна. Скоро здесь появится возможность записаться! 🔜"
    },
    {
        "name": "Алексей, 42 года",
        "description": "Специализируюсь на когнитивно-поведенческой терапии. Работаю с тревожностью, отношениями, кризисами идентичности. 15 лет практики.",
        "compatibility": 75,
        "contact": "Запись временно недоступна. Скоро здесь появится возможность записаться! 🔜"
    },
    {
        "name": "Марина, 35 лет",
        "description": "Гештальт-терапевт. Помогаю разобраться в отношениях, найти себя, справиться со стрессом и тревогой. Работаю онлайн.",
        "compatibility": 70,
        "contact": "Запись временно недоступна. Скоро здесь появится возможность записаться! 🔜"
    },
]

# Темы и вопросы
TOPICS = {
    "💔 Отношения": "Расскажи, что происходит в твоих отношениях?",
    "😰 Тревога": "Расскажи, что тебя тревожит?",
    "🏠 Семья": "Что происходит в твоей семье?",
    "👥 Друзья": "Что происходит в твоих отношениях с друзьями?",
    "💼 Работа": "Что происходит на работе?",
    "🌱 Саморазвитие": "Расскажи, над чем ты хочешь работать в себе?",
    "🤔 Другое": "Расскажи, что тебя беспокоит?"
}

# Советы
DAILY_TIPS = [
    "Посмотри старые фото, где ты счастлив. Это «якорь» ресурсного состояния. Есть такие в телефоне? 📸",
    "Попробуй сегодня выключить уведомления в чатах. Проверяй их по расписанию. Тишина лечит. 🔕",
    "Попробуй говорить тише. Это заставляет прислушиваться и успокаивает собеседника. 🤫",
    "Правило 20 секунд: сделай полезную привычку на 20 секунд доступнее, а вредную — на 20 секунд сложнее. ⏱",
    "Сегодня скажи кому-то близкому что-то хорошее. Это укрепляет отношения и поднимает настроение. 💛",
    "Сделай 5 глубоких вдохов прямо сейчас. Это активирует парасимпатическую нервную систему. 🌬",
    "Запиши три вещи, за которые ты благодарен сегодня. Это меняет фокус внимания. 📝",
]

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload, timeout=10)

def get_main_menu():
    return {
        "keyboard": [[{"text": "📋 Меню"}]],
        "resize_keyboard": True,
        "persistent": True
    }

def get_gender_keyboard():
    return {
        "inline_keyboard": [[
            {"text": "😊 Я Парень", "callback_data": "gender_male"},
            {"text": "👩 Я Девушка", "callback_data": "gender_female"}
        ]]
    }

def get_topics_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "💔 Отношения", "callback_data": "topic_отношения"},
                {"text": "😰 Тревога", "callback_data": "topic_тревога"}
            ],
            [
                {"text": "🏠 Семья", "callback_data": "topic_семья"},
                {"text": "👥 Друзья", "callback_data": "topic_друзья"}
            ],
            [
                {"text": "💼 Работа", "callback_data": "topic_работа"},
                {"text": "🌱 Саморазвитие", "callback_data": "topic_саморазвитие"}
            ],
            [{"text": "🤔 Другое", "callback_data": "topic_другое"}]
        ]
    }

def get_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "👥 Подобрать живого психолога", "callback_data": "menu_psychologists"}],
            [{"text": "🔄 Сменить тему", "callback_data": "menu_change_topic"}],
            [{"text": "🔄 Начать заново", "callback_data": "menu_restart"}]
        ]
    }

def get_psychologist_keyboard(index):
    nav = []
    if index > 0:
        nav.append({"text": "◀️", "callback_data": f"psych_{index-1}"})
    nav.append({"text": f"{index+1}/{len(PSYCHOLOGISTS)}", "callback_data": "psych_none"})
    if index < len(PSYCHOLOGISTS) - 1:
        nav.append({"text": "▶️", "callback_data": f"psych_{index+1}"})
    return {
        "inline_keyboard": [
            nav,
            [{"text": "📋 Подробнее о психологе", "callback_data": f"psych_detail_{index}"}],
            [{"text": "📅 Записаться на сессию", "callback_data": f"psych_book_{index}"}]
        ]
    }

def ask_gpt(chat_id, user_text):
    try:
        user = user_data.get(chat_id, {})
        gender = user.get("gender", "не указан")
        topic = user.get("topic", "общее")
        history = user.get("history", [])
        gender_context = "парень" if gender == "male" else "девушка"

        system_prompt = (
            f"Ты — Мария Иевлева, профессиональный психолог с глубоким уровнем эмпатии. "
            f"Ты общаешься с {gender_context} на тему: {topic}. "
            f"Твоя цель: поддерживать, слушать и помогать. "
            f"Говори тепло, искренне, без официоза. "
            f"Задавай уточняющие вопросы. Не давай советов сразу — сначала выслушай. "
            f"Отвечай на русском языке."
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages += history
        messages.append({"role": "user", "content": user_text})

        if len(messages) > 22:
            messages = [messages[0]] + messages[-20:]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1024
        )

        response_text = response.choices[0].message.content

        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": response_text})
        if len(history) > 20:
            history = history[-20:]

        if chat_id not in user_data:
            user_data[chat_id] = {}
        user_data[chat_id]["history"] = history

        return response_text

    except Exception as e:
        return f"Мария временно недоступна... (Ошибка: {str(e)})"

def send_daily_tips():
    first_delay = random.randint(12 * 3600, 48 * 3600)
    time.sleep(first_delay)
    while True:
        tip = random.choice(DAILY_TIPS)
        for chat_id in list(all_users):
            try:
                send_message(chat_id, f"💡 <b>Совет от Марии:</b>\n\n{tip}")
            except:
                pass
        delay = random.randint(36 * 3600, 60 * 3600)
        time.sleep(delay)

def handle_start(chat_id):
    all_users.add(chat_id)
    save_users(all_users)
    user_data[chat_id] = {"history": []}
    welcome_text = (
        "Привет 💜\n\n"
        "Здесь можно быть собой. Без масок, без «я в порядке», без страха осуждения.\n\n"
        "Я — Мария Иевлева, твой личный психолог. Пиши мне в любое время дня и ночи. "
        "Я не устаю, не осуждаю и не делюсь твоими секретами.\n\n"
        "✨ <b>Что я умею:</b>\n"
        "• Выслушать, когда больше некому\n"
        "• Разобрать переписку — перешли мне сообщения\n"
        "• Помочь разобраться в себе и своих чувствах\n\n"
        "Чем больше мы общаемся, тем лучше я тебя понимаю!\n\n"
        "Укажи свой пол, чтобы мои советы были максимально точными 🎯"
    )
    send_message(chat_id, welcome_text, reply_markup=get_gender_keyboard())

def handle_gender(chat_id, gender, message_id):
    user_data[chat_id] = {"gender": gender, "history": []}
    all_users.add(chat_id)
    save_users(all_users)
    gender_text = "Парень" if gender == "male" else "Девушка"
    emoji = "😊" if gender == "male" else "👩"

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup",
        json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
        timeout=10
    )

    send_message(chat_id, f"✅ Отлично! Ты выбрал: {emoji} {gender_text}")
    send_message(chat_id, "👇 Используй кнопки или напиши сообщение:\n\nИли выбери тему:", reply_markup=get_topics_keyboard())

def handle_topic(chat_id, topic_key):
    topic_map = {
        "отношения": "💔 Отношения",
        "тревога": "😰 Тревога",
        "семья": "🏠 Семья",
        "друзья": "👥 Друзья",
        "работа": "💼 Работа",
        "саморазвитие": "🌱 Саморазвитие",
        "другое": "🤔 Другое"
    }
    topic = topic_map.get(topic_key, "🤔 Другое")
    question = TOPICS.get(topic, "Расскажи, что тебя беспокоит?")

    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]["topic"] = topic
    user_data[chat_id]["history"] = []

    send_message(chat_id, f"Тема: {topic}\n\n{question}", reply_markup=get_main_menu())

def handle_psychologists(chat_id, index=0):
    psych = PSYCHOLOGISTS[index]
    text = (
        f"👤 <b>{psych['name']}</b>\n\n"
        f"ℹ️ {psych['description']}\n\n"
        f"🔥 <b>Совместимость: {psych['compatibility']}%</b>"
    )
    send_message(chat_id, text, reply_markup=get_psychologist_keyboard(index))

@app.route("/send_tips", methods=["GET", "POST"])
def send_tips_endpoint():
    if not all_users:
        return "No users", 200
    tip = random.choice(DAILY_TIPS)
    count = 0
    for chat_id in list(all_users):
        try:
            send_message(chat_id, f"💡 <b>Совет от Марии:</b>\n\n{tip}")
            count += 1
        except:
            pass
    return f"Sent to {count} users", 200

@app.route("/ping", methods=["GET"])
def ping():
    return "OK", 200

@app.route("/", methods=["POST"])
def index():
    data = request.get_json(silent=True)
    if not data:
        return "OK", 200

    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        callback_data = callback["data"]

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]},
            timeout=10
        )

        if callback_data == "gender_male":
            handle_gender(chat_id, "male", message_id)
        elif callback_data == "gender_female":
            handle_gender(chat_id, "female", message_id)
        elif callback_data.startswith("topic_"):
            handle_topic(chat_id, callback_data.replace("topic_", ""))
        elif callback_data == "menu_psychologists":
            handle_psychologists(chat_id, 0)
        elif callback_data == "menu_change_topic":
            send_message(chat_id, "Выбери новую тему:", reply_markup=get_topics_keyboard())
        elif callback_data == "menu_restart":
            handle_start(chat_id)
        elif callback_data.startswith("psych_") and "detail" not in callback_data and "book" not in callback_data and "none" not in callback_data:
            try:
                handle_psychologists(chat_id, int(callback_data.replace("psych_", "")))
            except:
                pass
        elif callback_data.startswith("psych_book_"):
            try:
                idx = int(callback_data.replace("psych_book_", ""))
                send_message(chat_id, PSYCHOLOGISTS[idx]["contact"])
            except:
                pass
        elif callback_data.startswith("psych_detail_"):
            try:
                idx = int(callback_data.replace("psych_detail_", ""))
                psych = PSYCHOLOGISTS[idx]
                send_message(chat_id, f"👤 <b>{psych['name']}</b>\n\n{psych['description']}")
            except:
                pass

        return "OK", 200

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")
        all_users.add(chat_id)
    save_users(all_users)

        if not user_text:
            return "OK", 200

        if user_text == "/start":
            handle_start(chat_id)
        elif user_text in ["📋 Меню", "/menu"]:
            send_message(chat_id, "Выбери действие:", reply_markup=get_menu_keyboard())
        elif user_text == "/psychologists":
            handle_psychologists(chat_id, 0)
        else:
            if chat_id not in user_data:
                handle_start(chat_id)
                return "OK", 200
            if not user_data[chat_id].get("topic"):
                send_message(chat_id, "Выбери тему для разговора:", reply_markup=get_topics_keyboard())
                return "OK", 200
            answer = ask_gpt(chat_id, user_text)
            send_message(chat_id, answer)

    return "OK", 200

if __name__ == "__main__":
    tip_thread = threading.Thread(target=send_daily_tips, daemon=True)
    tip_thread.start()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
