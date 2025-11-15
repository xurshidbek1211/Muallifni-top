import logging
import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

# ===== TOKEN VA URL =====
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# ===== BOT VA DISPATCHER =====
bot = Bot(token=API_TOKEN, parse_mode="MarkdownV2")
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ===== JSON fayllar =====
SAVOLLAR_FILE = "savollar.json"
SCORE_FILE = "user_scores.json"
STATE_FILE = "user_states.json"

# ===== JSON load/save =====
def load_json(filename):
    return json.load(open(filename, "r", encoding="utf-8")) if os.path.exists(filename) else {}

def save_json(filename, data):
    json.dump(data, open(filename, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ===== Javobni normalizatsiya =====
def normalize_answer(text):
    return text.lower().strip()

# ===== MarkdownV2 escape =====
def escape_md(text):
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    for ch in escape_chars:
        text = text.replace(ch, f"\\{ch}")
    return text

# ===== Yangi savol yuborish =====
async def send_new_question(chat_id):
    questions = load_json(SAVOLLAR_FILE)
    if not questions:
        await bot.send_message(chat_id, "❌ Savollar mavjud emas.")
        return

    question = random.choice(questions)
    states = load_json(STATE_FILE)
    states[str(chat_id)] = {
        "current": question,
        "answered_by": None
    }
    save_json(STATE_FILE, states)

    text = escape_md(f"📘 {question['kitob']}\nBu kitobni kim yozgan?")
    await bot.send_message(chat_id, text)

# ===== /goo =====
@dp.message_handler(commands=["goo"])
async def start_game(message: types.Message):
    await send_new_question(message.chat.id)

# ===== Javoblarni tekshirish =====
@dp.message_handler()
async def check_answer(message: types.Message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    states = load_json(STATE_FILE)

    if chat_id not in states:
        return
    state = states[chat_id]
    if "current" not in state or state.get("answered_by") is not None:
        return

    user_answer = normalize_answer(message.text)
    correct = normalize_answer(state["current"]["muallif"])

    if user_answer == correct:
        state["answered_by"] = user_id
        states[chat_id] = state
        save_json(STATE_FILE, states)

        scores = load_json(SCORE_FILE)
        scores.setdefault(chat_id, {})
        scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + 1
        save_json(SCORE_FILE, scores)

        # Top 10 reyting (medallar)
        top = sorted(scores[chat_id].items(), key=lambda x: x[1], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        reyting = ""
        for i, (uid, ball) in enumerate(top[:10]):
            try:
                user = await bot.get_chat(int(uid))
                name = escape_md(user.first_name)
            except:
                name = "👤 Nomaʼlum"
            if i < 3:
                reyting += f"{medals[i]} {name} - {ball} ball\n"
            else:
                reyting += f"{i+1}. {name} - {ball} ball\n"

        msg = escape_md(
            f"🎯 To‘g‘ri javob: {state['current']['muallif']}\n"
            f"🎉 {message.from_user.full_name} +1 ball oldi!\n\n"
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

# ===== 24/7 uyg‘oq saqlash =====
async def keep_alive():
    chat_id = 1899194677  # Sizning lichka chat ID
    while True:
        try:
            await bot.send_message(chat_id, "💡 Bot ishlayapti...")
        except:
            pass
        await asyncio.sleep(600)  # 10 daqiqa

# ===== FastAPI Lifespan + Webhook =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook o‘rnatildi:", WEBHOOK_URL)

    # 24/7 uyg‘oq saqlash
    asyncio.create_task(keep_alive())

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
async def root():
    return {"status": "OK", "webhook": WEBHOOK_URL}
