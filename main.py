import logging
import os
import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import md
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager


# ===== TOKEN & WEBHOOK =====
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

# ===== BOT + DISPATCHER =====
bot = Bot(token=API_TOKEN, parse_mode="MarkdownV2")
Bot.set_current(bot)  # <<< MUHIM >>> Kontekst o‘rnatish

dp = Dispatcher(bot, storage=MemoryStorage())
Dispatcher.set_current(dp)  # <<< MUHIM >>> Kontekst o‘rnatish

logging.basicConfig(level=logging.INFO)


# ===== FILES =====
SAVOLLAR_FILE = "savollar.json"
SCORE_FILE = "user_scores.json"
STATE_FILE = "user_states.json"


# ===== JSON FUNKSIYALAR =====
def load_json(filename):
    return json.load(open(filename, "r", encoding="utf-8")) if os.path.exists(filename) else {}

def save_json(filename, data):
    json.dump(data, open(filename, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# ===== Markdown escape =====
def escape_md(text):
    chars = r"\_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text


# ===== Normalization =====
def normalize(text):
    return text.lower().strip()


# ===== Savol yuborish =====
async def send_new_question(chat_id):

    questions = load_json(SAVOLLAR_FILE)
    if not questions:
        await bot.send_message(chat_id, "❌ Savollar topilmadi.")
        return

    q = random.choice(questions)

    states = load_json(STATE_FILE)
    states[str(chat_id)] = {
        "kitob": q["kitob"],
        "muallif": q["muallif"],
        "answered_by": None
    }
    save_json(STATE_FILE, states)

    msg = escape_md(f"📘 *{q['kitob']}*\nBu kitobni kim yozgan?")
    await bot.send_message(chat_id, msg)


# ===== /goo =====
@dp.message_handler(commands=["goo"])
async def goo(message: types.Message):
    await send_new_question(message.chat.id)


# ===== Javob tekshirish =====
@dp.message_handler()
async def check_answer(message: types.Message):

    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)

    states = load_json(STATE_FILE)
    if chat_id not in states:
        return

    state = states[chat_id]

    # Allaqachon javob berilgan
    if state.get("answered_by") is not None:
        return

    # Javob tekshirish
    correct = normalize(state["muallif"])
    user_answer = normalize(message.text)

    if user_answer == correct:

        # Birinchi bo‘lib to‘g‘ri javob bergan
        state["answered_by"] = user_id
        save_json(STATE_FILE, states)

        # Ball yozish
        scores = load_json(SCORE_FILE)
        scores.setdefault(chat_id, {})
        scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + 1
        save_json(SCORE_FILE, scores)

        # Reyting
        reyting_text = ""
        medals = ["🥇", "🥈", "🥉"]

        top = sorted(scores[chat_id].items(), key=lambda x: x[1], reverse=True)

        for i, (uid, ball) in enumerate(top[:10]):
            try:
                user = await bot.get_chat(int(uid))
                name = escape_md(user.first_name)
            except:
                name = "Noma’lum"

            medal = medals[i] if i < 3 else f"{i+1}."
            reyting_text += f"{medal} {name} — {ball} ball\n"

        msg = escape_md(
            f"🎉 {message.from_user.full_name} to‘g‘ri javob berdi!\n"
            f"✔️ To‘g‘ri javob: {state['muallif']}\n\n"
            f"🏆 TOP 10:\n{reyting_text}"
        )

        # <<< MUHIM >>> message.answer o‘rniga bot.send_message ishlatamiz
        await bot.send_message(message.chat.id, msg)

        # Yangi savol
        await send_new_question(message.chat.id)


# ===== /ball =====
@dp.message_handler(commands=["ball"])
async def my_ball(message: types.Message):

    scores = load_json(SCORE_FILE)
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)

    ball = scores.get(chat_id, {}).get(user_id, 0)

    await bot.send_message(message.chat.id, f"📊 Sizning balingiz: {ball}")


# ===== FASTAPI + WEBHOOK =====
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
    Bot.set_current(bot)
    Dispatcher.set_current(dp)

    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)

    return {"ok": True}


@app.get("/")
async def home():
    return {"bot": "running", "webhook": WEBHOOK_URL}
