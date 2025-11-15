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
bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

# ================== SAVOLLARNI YUKLASH ==================
with open("savollar.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# ================== O'YIN HOLATI ==================
games = {}

# ================== START ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    chat_id = message.chat.id
    chat_type = message.chat.type

    # ADMIN TEKSHIRISH
    warning = ""
    if chat_type in ["group", "supergroup"]:
        try:
            me = await bot.get_me()
            bot_member = await bot.get_chat_member(chat_id, me.id)
            if bot_member.status not in ["administrator", "creator"]:
                warning = "❌ Bot guruhda admin emas, ba'zi funksiyalar ishlamasligi mumkin!"
        except:
            warning = "❌ Bot guruhda admin ekanligini tekshirib bo‘lmadi!"

    # O‘yin holatini yaratish
    games[chat_id] = {
        "players": {},
        "current_question": None,
        "asked_questions": [],
        "answered": False
    }

    text = "🎉 *Muallifni top* o‘yini boshlandi!\nSavollar tez orada yuboriladi."
    if warning:
        text = warning + "\n\n" + text

    await message.reply(text)
    await send_question(chat_id)

# ================== SAVOL YUBORISH ==================
async def send_question(chat_id):
    game = games.get(chat_id)
    if not game:
        return

    available = [q for q in questions if q['kitob'] not in game["asked_questions"]]
    if not available:
        await finish_game(chat_id)
        return

    q = random.choice(available)
    game["current_question"] = q
    game["asked_questions"].append(q['kitob'])
    game["answered"] = False

    try:
        await bot.send_message(
            chat_id,
            f"📘 *{q['kitob']}*\nBu kitobni kim yozgan?"
        )
    except:
        pass

# ================== JAVOB TEKSHIRISH ==================
@dp.message_handler()
async def answer(message: types.Message):
    chat_id = message.chat.id

    if chat_id not in games:
        return

    game = games[chat_id]
    question = game.get("current_question")

    if not question or game["answered"]:
        return

    user = message.from_user.username or message.from_user.full_name
    text = message.text.strip().lower()

    if text == question["muallif"].lower():
        game["players"][user] = game["players"].get(user, 0) + 1
        game["answered"] = True

        await message.reply(f"✅ To‘g‘ri javob! *{user}* +1 ball")
        await show_rating(chat_id)

        await asyncio.sleep(2)
        await send_question(chat_id)

# ================== REYTING ==================
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

    await bot.send_message(chat_id, text)

# ================== STOP ==================
@dp.message_handler(commands=["stop"])
async def stop(message: types.Message):
    await finish_game(message.chat.id)

async def finish_game(chat_id):
    if chat_id not in games:
        return

    players = games[chat_id]["players"]
    text = "🏆 *O‘yin tugadi!*\n\n"

    if not players:
        text += "❗ Hech kim javob bera olmadi."
        await bot.send_message(chat_id, text)
        del games[chat_id]
        return

    ranking = sorted(players.items(), key=lambda x: x[1], reverse=True)

    for i, (p, b) in enumerate(ranking, start=1):
        text += f"{i}. {p} — {b} ball\n"

    winner, points = ranking[0]
    text += f"\n🎉 *G‘olib: {winner}!* ({points} ball)"

    await bot.send_message(chat_id, text)
    del games[chat_id]

# ================== WEBHOOK ==================
async def handle(request):
    Bot.set_current(bot)  # <<< MAJBURIY
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()

async def on_startup(app):
    Bot.set_current(bot)  # <<< MAJBURIY
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook READY!")

async def on_shutdown(app):
    print("Bot stopped")
    await bot.delete_webhook()
    await bot.session.close()

# ================== APP ==================
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=10000)
