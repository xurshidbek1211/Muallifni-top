import json
import random
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode

# ================== TOKEN VA WEBHOOK ==================
API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"
WEBHOOK_HOST = "https://muallifni-top.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================== SAVOLLARNI YUKLASH ==================
with open("savollar.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# ================== O'YIN HOLATI ==================
games = {}

# ================== START KOMANDASI ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    Bot.set_current(bot)
    chat_id = message.chat.id
    chat_type = message.chat.type

    # Guruhda adminlikni tekshirish
    if chat_type in ["group", "supergroup"]:
        me = await bot.get_me()
        chat_member = await bot.get_chat_member(chat_id, me.id)
        if chat_member.status not in ["administrator", "creator"]:
            await message.reply("❌ Bot guruhda *admin* bo‘lishi shart!")
            return

    # O‘yin holatini yaratish
    games[chat_id] = {
        "players": {},
        "current_question": None,
        "asked_questions": []
    }

    await message.reply("🎉 *Muallifni top* o‘yini boshlandi!\nSavollar ketma-ket beriladi.", parse_mode=ParseMode.MARKDOWN)
    await send_question(chat_id)

# ================== /STOP KOMANDASI ==================
@dp.message_handler(commands=["stop"])
async def stop_game(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in games:
        await message.reply("❌ Hozir o‘yin yo‘q.")
        return

    await finish_game(chat_id)

# ================== SAVOL YUBORISH ==================
async def send_question(chat_id):
    game = games[chat_id]

    # Agar savollar tugasa qayta boshlanadi
    available = [q for q in questions if q not in game["asked_questions"]]
    if not available:
        game["asked_questions"] = []
        available = questions.copy()

    q = random.choice(available)
    game["current_question"] = q
    game["asked_questions"].append(q)

    await bot.send_message(
        chat_id,
        f"📗 *{q['kitob']}*\nBu kitobni kim yozgan?",
        parse_mode=ParseMode.MARKDOWN
    )

# ================== JAVOB TEKSHIRISH ==================
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

    # To'g'ri javob berilgan bo'lsa
    if message.text.strip().lower() == question["muallif"].lower():
        game["players"][user] = game["players"].get(user, 0) + 1
        await message.reply(f"✅ To‘g‘ri! {user} +1 ball")

        # Reyting chiqarish
        ranking = sorted(game["players"].items(), key=lambda x: x[1], reverse=True)
        text = "📊 *Joriy reyting:*\n"
        for i, (p, b) in enumerate(ranking, start=1):
            text += f"{i}. {p} — {b} ball\n"

        await message.reply(text, parse_mode=ParseMode.MARKDOWN)

        # Yangi savol berish
        game["current_question"] = None
        await send_question(chat_id)

# ================== O‘YIN TUGASHI VA TABRIK ==================
async def finish_game(chat_id):
    game = games.get(chat_id)
    if not game:
        return

    if not game["players"]:
        await bot.send_message(chat_id, "❗ Hech kim javob bermadi. O‘yin tugadi.")
        del games[chat_id]
        return

    ranking = sorted(game["players"].items(), key=lambda x: x[1], reverse=True)
    winner, points = ranking[0]

    text = "🏆 *O‘yin tugadi!*\n\n🏅 Reyting:\n"
    for i, (p, b) in enumerate(ranking, start=1):
        text += f"{i}. {p} — {b} ball\n"

    text += f"\n🎉 *TABRIKLAYMIZ, {winner}!* Eng ko‘p ball to‘pladingiz!"

    await bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)
    del games[chat_id]

# ================== WEBHOOK HANDLER ==================
async def handle(request):
    Bot.set_current(bot)
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()

async def on_startup(app):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(ping())

# ================== BOTNI UXLAMASLIGI ==================
async def ping():
    while True:
        try:
            await bot.get_me()
        except:
            pass
        await asyncio.sleep(480)

# ================== APP ==================
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=10000)
