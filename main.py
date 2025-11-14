import json
import random
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton

# BOT TOKENINI shuyerga yozing
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"

# Webhook sozlamalari
WEBHOOK_HOST = "https://muallifni-top.onrender.com"  # Render URL
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Savollarni yuklash
with open("savollar.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# O'yin holati
games = {}

# Savol sonini tanlash klaviaturasi
game_setup_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("5 ta"), KeyboardButton("10 ta")],
        [KeyboardButton("15 ta"), KeyboardButton("20 ta")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# --- START --- #
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    chat_id = message.chat.id
    chat_type = message.chat.type

    # Guruhda bot admin ekanligini tekshirish
    if chat_type in ["group", "supergroup"]:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.reply("❌ Iltimos, o‘yinni ishlatish uchun botni guruhda admin qilib tayinlang.")
            return

    # O‘yin holatini yaratish
    games[chat_id] = {
        "players": {},
        "limit": None,
        "count": 0,
        "current_question": None,
        "asked_questions": [],
    }

    await message.reply(
        "🎉 *Muallifni top* o‘yiniga xush kelibsiz!\n\n"
        "✳ O‘yin necha savoldan iborat bo‘lsin?",
        reply_markup=game_setup_kb,
        parse_mode=ParseMode.MARKDOWN
    )

# --- SAVOL LIMITINI TANLASH --- #
@dp.message_handler(lambda msg: msg.text in ["5 ta", "10 ta", "15 ta", "20 ta"])
async def set_limit(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return
    limit = int(message.text.split()[0])
    games[chat_id]["limit"] = limit
    await message.reply(f"✅ O‘yin {limit} ta savoldan iborat. Savol yuborilyapti...")
    await send_question(chat_id)

# --- SAVOL YUBORISH --- #
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

    await bot.send_message(
        chat_id,
        f"📗 *{q['kitob']}*\nBu kitobni kim yozgan?",
        parse_mode=ParseMode.MARKDOWN
    )

# --- JAVOB TEKSHIRISH --- #
@dp.message_handler()
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
        await message.reply(f"✅ To‘g‘ri! {user} +1 ball")
        await send_question(chat_id)

# --- O‘YIN YAKUNI --- #
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

    text += (
        f"\n🎉 *TABRIKLAYMIZ, {winner}!* 🎉\n"
        "Siz o‘yin davomida eng ko‘p to‘g‘ri javob berdingiz va g‘olib bo‘ldingiz!\n"
        "👏 Zo‘r bilim, tezkor javob va e’tibor uchun rahmat!"
    )

    await bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)
    del games[chat_id]

# --- WEBHOOK SERVER --- #
async def handle(request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()

async def on_startup(app):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook ishga tushdi!")

# BOT UXLAMASLIGI — har 8 daqiqa ping
async def ping():
    while True:
        try:
            await bot.get_me()
        except:
            pass
        await asyncio.sleep(480)  # 8 daqiqa

def start_background_tasks(app):
    app.loop.create_task(ping())

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_startup.append(start_background_tasks)

if __name__ == "__main__":
    web.run_app(app, port=10000)
