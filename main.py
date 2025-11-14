import json
import random
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types

# ================== TOKEN VA WEBHOOK ==================
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"
WEBHOOK_HOST = "https://muallifni-top.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

# ================== BOT VA DISPATCHER ==================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================== SAVOLLARNI YUKLASH ==================
with open("savollar.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# ================== O'YIN HOLATI ==================
games = {}

# ================== YORDAMCHI FUNKSIYA ==================
async def send_text(chat_type, chat_id, message_obj, text, **kwargs):
    if chat_type == "private":
        await message_obj.reply(text, **kwargs)
    else:
        await bot.send_message(chat_id, text, **kwargs)

# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    Bot.set_current(bot)
    chat_id = message.chat.id
    chat_type = message.chat.type

    # Guruhda — bot admin bo'lishi shart
    if chat_type in ["group", "supergroup"]:
        me = await bot.get_chat_member(chat_id, bot.id)
        if me.status not in ["administrator", "creator"]:
            await send_text(chat_type, chat_id, message, "❌ Bot guruhda *admin* bo‘lishi kerak!", parse_mode="Markdown")
            return

    # O‘yinning holatini yaratish
    games[chat_id] = {
        "players": {},
        "current_question": None,
        "asked_questions": []
    }

    await send_text(chat_type, chat_id, message, "🎉 *Muallifni top* o‘yini boshlandi!\nSavollar yuborilmoqda...", parse_mode="Markdown")
    await send_question(chat_id)

# ================== SAVOL YUBORISH ==================
async def send_question(chat_id):
    game = games.get(chat_id)
    if not game:
        return

    # Avvalgi savollarni kitob nomi orqali tekshirish
    available = [q for q in questions if q['kitob'] not in game["asked_questions"]]
    if not available:
        await finish_game(chat_id)
        return

    q = random.choice(available)
    game["current_question"] = q
    game["asked_questions"].append(q['kitob'])  # faqat kitob nomini saqlaymiz

    await bot.send_message(
        chat_id,
        f"📘 *{q['kitob']}*\nBu kitobni kim yozgan?",
        parse_mode="Markdown"
    )

# ================== JAVOB TEKSHIRISH ==================
@dp.message_handler()
async def answer(message: types.Message):
    chat_id = message.chat.id
    chat_type = message.chat.type

    if chat_id not in games:
        return

    game = games[chat_id]
    question = game.get("current_question")
    if not question:
        return

    user = message.from_user.username or message.from_user.full_name

    if message.text.strip().lower() == question["muallif"].lower():
        game["players"][user] = game["players"].get(user, 0) + 1

        # Javob xabari
        await send_text(chat_type, chat_id, message, f"✅ To‘g‘ri javob! {user} +1 ball")

        # Reytingni ko‘rsatish
        await show_rating(chat_id)

        # Keyingi savol
        await send_question(chat_id)

# ================== REYTING CHIQARISH ==================
async def show_rating(chat_id):
    game = games.get(chat_id)
    if not game:
        return

    players = game["players"]
    if not players:
        return

    ranking = sorted(players.items(), key=lambda x: x[1], reverse=True)
    text = "📊 *Joriy reyting:*\n\n"
    for i, (p, b) in enumerate(ranking, start=1):
        text += f"{i}. {p} — {b} ball\n"

    await bot.send_message(chat_id, text, parse_mode="Markdown")

# ================== STOP — O‘YINNI YAKUNLASH ==================
@dp.message_handler(commands=["stop"])
async def stop(message: types.Message):
    chat_id = message.chat.id
    await finish_game(chat_id)

async def finish_game(chat_id):
    if chat_id not in games:
        return

    players = games[chat_id]["players"]
    text = "🏆 *O‘yin tugadi!*\n\n"

    if not players:
        text += "❗ Hech kim javob bera olmadi."
        await bot.send_message(chat_id, text, parse_mode="Markdown")
        del games[chat_id]
        return

    ranking = sorted(players.items(), key=lambda x: x[1], reverse=True)

    # Reyting
    for i, (p, b) in enumerate(ranking, start=1):
        text += f"{i}. {p} — {b} ball\n"

    winner, points = ranking[0]
    text += f"\n🎉 *G‘olib: {winner}!* ({points} ball)"

    await bot.send_message(chat_id, text, parse_mode="Markdown")
    del games[chat_id]

# ================== WEBHOOK ==================
async def handle(request):
    Bot.set_current(bot)
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()

async def on_startup(app):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook ishga tushdi!")

async def on_shutdown(app):
    print("Bot sessiyasi yopilmoqda...")
    await bot.delete_webhook()
    await bot.close()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=10000)
