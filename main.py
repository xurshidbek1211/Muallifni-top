import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

API_TOKEN = "8569524026:AAFxbE-g8T04qwHyAK2Uu2KnPR6DQvbH8gI"
CREATOR_ID = 8460056817
ALLOWED_ADMINS = [CREATOR_ID]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Savollarni yuklash
with open("savollar.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# O'yin holati guruhlar va lichkalar bo'yicha
games = {}

# Ball variantlari klaviaturasi
ball_options = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="10"), KeyboardButton(text="20"), KeyboardButton(text="30")],
        [KeyboardButton(text="40"), KeyboardButton(text="50")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# /start_game komandasi
@dp.message_handler(commands=["start_game"])
async def start_game(message: types.Message):
    chat_id = message.chat.id
    chat_type = message.chat.type

    # Guruhda bot adminligini tekshirish
    if chat_type in ["group", "supergroup"]:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ["administrator", "creator"]:
            await message.reply("❌ Iltimos, o‘yinni ishga tushirish uchun botni guruhda admin qilib tayinlang.")
            return

    # O'yinni boshlash
    games[chat_id] = {
        "players": {},
        "max_ball": None,
        "current_question": None,
        "asked_questions": []
    }
    await message.reply(
        "🎯 O‘yin oxirida necha ball bilan g‘olib aniqlansin?", 
        reply_markup=ball_options
    )

# Ball tanlash
@dp.message_handler(lambda message: message.text in ["10","20","30","40","50"])
async def set_max_ball(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return
    games[chat_id]["max_ball"] = int(message.text)
    await message.reply(f"✅ Maksimal ball {message.text} ga belgilandi!\nSavol yuboriladi...")
    await send_question(chat_id)

# Savol yuborish funksiyasi
async def send_question(chat_id):
    available_questions = [q for q in questions if q not in games[chat_id]["asked_questions"]]
    if not available_questions:
        await bot.send_message(chat_id, "🎉 Savollar tugadi!")
        return
    question = random.choice(available_questions)
    games[chat_id]["current_question"] = question
    games[chat_id]["asked_questions"].append(question)
    await bot.send_message(
        chat_id, 
        f"📕 *{question['kitob']}* 📖\nBu kitobni kim yozgan?", 
        parse_mode=ParseMode.MARKDOWN
    )

# Javoblarni tekshirish
@dp.message_handler()
async def check_answer(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in games or games[chat_id]["current_question"] is None:
        return
    question = games[chat_id]["current_question"]
    player = message.from_user.username or message.from_user.full_name

    if message.text.strip().lower() == question["muallif"].strip().lower():
        # Ball qo'shish
        games[chat_id]["players"][player] = games[chat_id]["players"].get(player, 0) + 1
        await message.reply(f"✅ To‘g‘ri! {player} +1 ball")

        # Tablo yangilanishi
        ranking = sorted(games[chat_id]["players"].items(), key=lambda x: x[1], reverse=True)
        ranking_text = "🏅 Joriy reyting:\n" + "\n".join([f"{i+1}. {p[0]} — {p[1]} ball" for i, p in enumerate(ranking)])
        await bot.send_message(chat_id, ranking_text)

        # G'olibni tekshirish
        if games[chat_id]["players"][player] >= games[chat_id]["max_ball"]:
            await bot.send_message(
                chat_id, 
                f"🏆 Tabriklaymiz, {player}! Siz g‘olib bo‘ldingiz! 🎉\n"
                "Siz ajoyib bilim va tezkor fikr bilan barcha savollarga javob berdingiz! "
                "Sizning mahoratingiz guruhdagi barcha ishtirokchilar uchun namuna bo‘ldi. "
                "Shu muvaffaqiyat sizga yangi bilimlar, quvonch va katta ilhom olib kelsin! 🌟"
            )
            del games[chat_id]
            return

        # Keyingi savol
        await send_question(chat_id)

# /skip komandasi (faqat admin/yaratuvchi)
@dp.message_handler(commands=["skip"])
async def skip_question(message: types.Message):
    if message.from_user.id not in ALLOWED_ADMINS:
        await message.reply("❌ Sizda ruxsat yo‘q.")
        return
    chat_id = message.chat.id
    if chat_id not in games:
        return
    await message.reply("⏭ Savol o‘tkazildi, yangi savol yuboriladi...")
    await send_question(chat_id)

# /top komandasi
@dp.message_handler(commands=["top"])
async def show_ranking(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in games:
        await message.reply("❌ O‘yin hali boshlanmagan.")
        return
    ranking = sorted(games[chat_id]["players"].items(), key=lambda x: x[1], reverse=True)
    ranking_text = "🏅 Joriy reyting:\n" + "\n".join([f"{i+1}. {p[0]} — {p[1]} ball" for i, p in enumerate(ranking)])
    await message.reply(ranking_text)

# /add_question komandasi (faqat admin/yaratuvchi)
@dp.message_handler(commands=["add_question"])
async def add_question(message: types.Message):
    if message.from_user.id not in ALLOWED_ADMINS:
        await message.reply("❌ Sizda ruxsat yo‘q.")
        return
    try:
        parts = message.text.split("|")
        if len(parts) != 3:
            await message.reply("❌ Format: /add_question kitob nomi | muallif | 📕 … 📖")
            return
        kitob = parts[1].strip()
        muallif = parts[2].strip()
        questions.append({"kitob": kitob, "muallif": muallif})
        with open("savollar.json", "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=4)
        await message.reply(f"✅ Savol qo‘shildi: {kitob} — {muallif}")
    except Exception as e:
        await message.reply(f"❌ Xato: {e}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
