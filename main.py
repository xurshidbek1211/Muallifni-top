import os
import json
import random
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.session.aiohttp import AiohttpSession

# ================== TOKEN VA WEBHOOK ==================
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"
WEBHOOK_HOST = "https://muallifni-top.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

# ================== BOT VA DISPATCHER ==================
session = AiohttpSession()
bot = Bot(token=API_TOKEN, session=session)
types.Bot.set_current(bot)  # aiogram 3+ uchun

dp = Dispatcher()

# ================== SAVOLLARNI YUKLASH ==================
with open("savollar.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# ================== O'YIN HOLATI ==================
games = {}

question_limit_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("5 ta"), KeyboardButton("10 ta")],
        [KeyboardButton("15 ta"), KeyboardButton("20 ta")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ================== START KOMANDASI ==================
@dp.message()
async def start(message: types.Message):
    if message.text != "/start":
        return

    chat_id = message.chat.id
    chat_type = message.chat.type

    # Guruhda bot adminligini tekshirish
    if chat_type in ["group", "supergroup"]:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ["administrator", "creator"]:
            await bot.send_message(chat_id, "❌ Guruhda botni admin qilib tayinlang!")
            return

    games[chat_id] = {
        "players": {},
        "limit": None,
        "count": 0,
        "current_question": None,
        "asked_questions": []
    }

    await bot.send_message(
        chat_id,
        "🎉 *Muallifni top* o‘yiniga xush kelibsiz!\n\n✳ O‘yin necha savoldan iborat bo‘lsin?",
        reply_markup=question_limit_kb,
        parse_mode=ParseMode.MARKDOWN
    )

# ================== SAVOL LIMITINI TANLASH ==================
@dp.message()
async def set_limit(message: types.Message):
    if message.text not in ["5 ta", "10 ta", "15 ta", "20 ta"]:
        return
    chat_id = message.chat.id
    if chat_id not in games:
        return

    limit = int(message.text.split()[0])
    games[chat_id]["limit"] = limit
    await bot.send_message(chat_id, f"✅ O‘yin {limit} ta savoldan iborat.\n⏳ Birinchi savol yuborilyapti...")
    await send_question(chat_id)

# ================== SAVOL YUBORISH ==================
async def send_question(chat_id):
    game = games[chat_id]

    if game["count"] >= game["limit"]:
        await finish_game(chat_id)
        return

    available = [q for q in questions if q not in game["asked_questions"]]
    if not available:
        await finish_game(chat_id)
        return

    q = random.choice(available)
    game["current_question"] = q
    game["asked_questions"].append(q)
    game["count"] += 1

    await bot.send_message(chat_id, f"📗 *{q['kitob']}*\nBu kitobni kim yozgan?", parse_mode=ParseMode.MARKDOWN)

# ================== JAVOB TEKSHIRISH ==================
@dp.message()
async def check_answer(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return
    game = games[chat_id]
    question = game["current_question"]
    if not question:
        return

    user = message.from_user.username or message.from_user.full_name

    if message.text.strip().lower() == question["muallif"].lower():
        game["players"][user] = game["players"].get(user, 0) + 1
        await bot.send_message(chat_id, f"✅ To‘g‘ri! {user} +1 ball")
        await send_question(chat_id)

# ================== O‘YIN TUGASHI VA TABRIK ==================
async def finish_game(chat_id):
    game = games[chat_id]

    if not game["players"]:
        await bot.send_message(chat_id, "❗ Hech kim javob bera olmadi. O‘yin tugadi.")
        del games[chat_id]
        return

    ranking = sorted(game["players"].items(), key=lambda x: x[1], reverse=True)
    winner, points = ranking[0]

    text = "🏆 *O‘yin yakunlandi!*\n\n🏅 Reyting:\n"
    for i, (p, b) in enumerate(ranking, start=1):
        text += f"{i}. {p} — {b} ball\n"

    text += f"\n🎉 *TABRIKLAYMIZ, {winner}!* 🎉\nSiz o‘yin davomida eng ko‘p to‘g‘ri javob berdingiz!"

    await bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)
    del games[chat_id]

# ================== WEBHOOK SERVER ==================
async def handle(request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook ishga tushdi!")

# ================== BOT UXLAMASLIGI ==================
async def ping():
    while True:
        try:
            await bot.get_me()
        except:
            pass
        await asyncio.sleep(480)

def start_background_tasks(app):
    app.loop.create_task(ping())

# ================== APP ==================
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_startup.append(start_background_tasks)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))  # Render port
    web.run_app(app, port=PORT)
