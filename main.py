import logging
import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

# ===== TOKEN VA WEBHOOK =====
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")  # Render avtomatik beradi

WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# ===== BOT =====
bot = Bot(token=API_TOKEN, parse_mode="MarkdownV2")
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ===== JSON FAYLLAR =====
SAVOLLAR_FILE = "savollar.json"
SCORE_FILE = "user_scores.json"
STATE_FILE = "user_states.json"

# ===== JSON YUKLASH / SAQLASH =====
def load_json(filename):
    return json.load(open(filename, "r", encoding="utf-8")) if os.path.exists(filename) else {}

def save_json(filename, data):
    json.dump(data, open(filename, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ===== MarkdownV2 escapelash =====
def escape_md(text):
    esc = r"\_*[]()~`>#+-=|{}.!"
    for ch in esc:
        text = text.replace(ch, f"\\{ch}")
    return text

# ===== Javobni tozalash =====
def normalize(text):
    return text.lower().strip()

# ===== Savol yuborish =====
async def send_new_question(chat_id):
    questions = load_json(SAVOLLAR_FILE)
    if not questions:
        await bot.send_message(chat_id, "❌ Savollar yuklanmagan.")
        return

    question = random.choice(questions)

    state = load_json(STATE_FILE)
    state[str(chat_id)] = {
        "kitob": question["kitob"],
        "muallif": question["muallif"],
        "answered_by": None
    }
    save_json(STATE_FILE, state)

    text = escape_md(f"📘 *{question['kitob']}*\nBu kitobni kim yozgan?")
    await bot.send_message(chat_id, text)

# ===== /goo buyrug‘i =====
@dp.message_handler(commands=["goo"])
async def start_game(message: types.Message):
    await send_new_question(message.chat.id)

# ===== Javob tekshirish =====
@dp.message_handler()
async def check_answer(message: types.Message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)

    state = load_json(STATE_FILE)

    # Hali savol berilmagan
    if chat_id not in state:
        return

    # Savolga allaqachon javob berilgan
    if state[chat_id].get("answered_by") is not None:
        return

    correct = normalize(state[chat_id]["muallif"])
    user_answer = normalize(message.text)

    if user_answer == correct:

        # Kim javob berganini belgilash
        state[chat_id]["answered_by"] = user_id
        save_json(STATE_FILE, state)

        # Ball berish
        scores = load_json(SCORE_FILE)
        scores.setdefault(chat_id, {})
        scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + 1
        save_json(SCORE_FILE, scores)

        # Reyting tayyorlash
        top = sorted(scores[chat_id].items(), key=lambda x: x[1], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        reyting = ""

        for i, (uid, ball) in enumerate(top[:10]):
            try:
                user = await bot.get_chat(int(uid))
                name = escape_md(user.first_name)
            except:
                name = "Noma'lum"
            medal = medals[i] if i < 3 else f"{i+1}."
            reyting += f"{medal} {name} — {ball} ball\n"

        msg = escape_md(
            f"🎉 {message.from_user.full_name} to‘g‘ri javob berdi!\n"
            f"🎯 To‘g‘ri javob: {state[chat_id]['muallif']}\n\n"
            f"🏆 TOP 10:\n{reyting}"
        )

        await message.answer(msg)
        await send_new_question(message.chat.id)

# ===== /ball =====
@dp.message_handler(commands=["ball"])
async def show_score(message: types.Message):
    scores = load_json(SCORE_FILE)
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)

    ball = scores.get(chat_id, {}).get(user_id, 0)
    await message.answer(f"📊 Sizning balingiz: {ball}")

# ===== FastAPI + Webhook =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook o‘rnatildi:", WEBHOOK_URL)
    yield
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return {"ok": True}

@app.get("/")
async def home():
    return {"status": "running", "webhook_url": WEBHOOK_URL}
