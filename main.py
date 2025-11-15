import logging
import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from fastapi import FastAPI, Request
from aiogram.utils.markdown import escape_md

# --- Atrof-muhit sozlamalari ---
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"  # O'zing tokenni qo'y
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

ADMIN_ID = 1899194677  # Shaxsiy ID
RUXSAT_ETILGANLAR = [8460056817]

bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot, storage=MemoryStorage())

Bot.set_current(bot)
Dispatcher.set_current(dp)

app = FastAPI()
logging.basicConfig(level=logging.INFO)

SAVOLLAR_FILE = "savollar.json"
SCORE_FILE = "user_scores.json"
STATE_FILE = "user_states.json"

# --- JSON fayllarni yuklash/saqlash ---
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Javoblarni normallashtirish ---
def normalize_answer(text):
    return text.lower().strip()

# --- Bot adminligini tekshirish (faqat guruhda) ---
async def check_bot_admin(message: types.Message) -> bool:
    if message.chat.type == "private":
        return True
    try:
        bot_member = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
        return bot_member.is_chat_admin()
    except Exception as e:
        logging.error(f"Bot adminligini tekshirishda xato: {e}")
        return False

# --- Yangi savol yuborish ---
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
    await bot.send_message(chat_id, escape_md(f"📘 {question['kitob']}\nBu kitobni kim yozgan?"))

# --- /goo --- start game
@dp.message_handler(commands=["goo"])
async def start_game(message: types.Message):
    if not await check_bot_admin(message):
        await message.answer("❌ Botni admin qiling!")
        return

    chat_id = message.chat.id
    await send_new_question(chat_id)

# --- Javoblarni tekshirish ---
@dp.message_handler()
async def check_answer(message: types.Message):
    if not await check_bot_admin(message):
        return

    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    states = load_json(STATE_FILE)

    if chat_id not in states:
        return
    state = states[chat_id]
    if "current" not in state or state.get("answered_by") is not None:
        return

    user_answer = normalize_answer(message.text)
    correct_answer = normalize_answer(state["current"]["muallif"])

    if user_answer == correct_answer:
        state["answered_by"] = user_id
        states[chat_id] = state
        save_json(STATE_FILE, states)

        scores = load_json(SCORE_FILE)
        if chat_id not in scores:
            scores[chat_id] = {}
        scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + 1
        save_json(SCORE_FILE, scores)

        # Top 10 reyting
        top = sorted(scores[chat_id].items(), key=lambda x: x[1], reverse=True)[:10]
        reyting = ""
        for i, (uid, ball) in enumerate(top):
            try:
                user = await bot.get_chat(int(uid))
                name = user.first_name
            except:
                name = "👤 Nomaʼlum"
            reyting += f"{i+1}. {name} - {ball} ball\n"

        await message.answer(
            f"🎯 To‘g‘ri javob: {state['current']['muallif']}\n"
            f"🎉 {message.from_user.full_name} +1 ball oldi!\n\n"
            f"🏆 Guruhdagi eng yaxshi 10 ta foydalanuvchi:\n{reyting}"
        )

        await send_new_question(message.chat.id)

# --- /ball ---
@dp.message_handler(commands=["ball"])
async def show_score(message: types.Message):
    scores = load_json(SCORE_FILE)
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    chat_scores = scores.get(chat_id, {})
    user_score = chat_scores.get(user_id, 0)
    await message.answer(f"📊 Sizning guruhdagi umumiy balingiz: {user_score}")

# --- Webhook sozlash ---
@app.on_event("startup")
async def on_startup():
    logging.info("Bot ishga tushmoqda...")
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook o‘rnatildi: {WEBHOOK_URL}")

# --- Webhookni qabul qilish ---
@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    data = await request.body()
    update = types.Update(**json.loads(data))
    await dp.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "Bot tirik va ishlayapti ✅"}
