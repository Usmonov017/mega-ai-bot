import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from google import genai

logging.basicConfig(level=logging.INFO)

# Muhit o'zgaruvchilari
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL", "@MoviTimeUz")
SERVER_CHANNEL = os.getenv("SERVER_CHANNEL", "@MoviTimeUz")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # O'zingizning ID raqamingizni yozing

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Gemini AI Klienti
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

ALL_LANGUAGES = {
    "en": "🇬🇧 English", "ru": "🇷🇺 Русский", "uz": "🇺🇿 O'zbekcha",
    "az": "🇦🇿 Azərbaycan", "tr": "⭐️ Türkçe", "kk": "🇰🇿 Қазақша",
    "tg": "🇹🇯 Тоҷикӣ", "ky": "🇰🇬 Кыргызча", "tk": "🇹🇲 Türkmençe"
}

MEMORY_DB = {
    "users": {},
    "buttons": {
        "en": ["🎬 Search Movie", "🤖 Gemini AI Chat", "🎵 Music Center"],
        "ru": ["🎬 Поиск Кино", "🤖 Gemini AI Chat", "🎵 Музыкальный Центр"],
        "uz": ["🎬 Kino Qidirish", "🤖 Gemini AI Chat", "🎵 Musiqa Markazi"],
        "az": ["🎬 Kino Axtarış", "🤖 Gemini AI Chat", "🎵 Musiqi Mərkəzi"],
        "tr": ["🎬 Film Ara", "🤖 Gemini AI Chat", "🎵 Müzik Merkezi"],
        "kk": ["🎬 Кино Іздеу", "🤖 Gemini AI Chat", "🎵 Музыка Орталығы"],
        "tg": ["🎬 Ҷустуҷӯи Кино", "🤖 Gemini AI Chat", "🎵 Маркази Мусиқӣ"],
        "ky": ["🎬 Кино Издөө", "🤖 Gemini AI Chat", "🎵 Музыка Борбору"],
        "tk": ["🎬 Kino Gözleg", "🤖 Gemini AI Chat", "🎵 Saz Merkezi"]
    }
}

class AdminStates(StatesGroup):
    editing_buttons = State()
    adding_button = State()

async def is_subscribed(user_id: int) -> bool:
    if not PUBLIC_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(chat_id=PUBLIC_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def get_user_lang(user_id: int) -> str:
    return MEMORY_DB["users"].get(user_id, {}).get("lang", "uz")

def get_user_reply_menu(user_id: int):
    lang = get_user_lang(user_id)
    builder = ReplyKeyboardBuilder()
    buttons = MEMORY_DB["buttons"].get(lang, MEMORY_DB["buttons"]["en"])
    for btn in buttons:
        builder.button(text=btn)
    if user_id == ADMIN_ID:
        builder.button(text="⚙️ Tugmalar muharriri")
        builder.button(text="🛑 Muharrirni to'xtatish")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_lang_keyboard():
    kb = InlineKeyboardBuilder()
    for code, name in ALL_LANGUAGES.items():
        kb.button(text=name, callback_data=f"set_lang_{code}")
    kb.adjust(2)
    return kb.as_markup()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in MEMORY_DB["users"]:
        MEMORY_DB["users"][user_id] = {"lang": "uz"}
    if not await is_subscribed(user_id):
        kb = InlineKeyboardBuilder()
        channel_url = f"https://t.me/{str(PUBLIC_CHANNEL).replace('@', '')}"
        kb.button(text="Kanalga a'zo bo'lish 🔐", url=channel_url)
        kb.button(text="Tekshirish ✅", callback_data="check_subscription")
        kb.adjust(1)
        await message.answer("👋 Botdan foydalanish uchun kanalga a'zo bo'ling.", reply_markup=kb.as_markup())
        return
    await message.answer("🌐 Tilingizni tanlang / Select your language:", reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[2]
    user_id = callback.from_user.id
    MEMORY_DB["users"][user_id] = {"lang": lang}
    await callback.answer(f"✓ {ALL_LANGUAGES.get(lang)}", show_alert=False)
    await callback.message.answer(f"🤖 Menyu:", reply_markup=get_user_reply_menu(user_id))

@dp.message(F.text == "⚙️ Tugmalar muharriri", F.from_user.id == ADMIN_ID)
async def admin_mode_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.editing_buttons)
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Tugma Qo'shish")
    kb.button(text="🛑 Muharrirni to'xtatish")
    kb.adjust(1)
    await message.answer("🔧 **Tugmalarni tahrirlash rejimi faollashdi.**", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "➕ Tugma Qo'shish", AdminStates.editing_buttons)
async def add_button_prompt(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.adding_button)
    await message.answer("📝 Yangi tugma nomini yuboring:")

@dp.message(AdminStates.adding_button)
async def add_button_save(message: types.Message, state: FSMContext):
    btn_name = message.text
    lang = get_user_lang(message.from_user.id)
    if btn_name not in MEMORY_DB["buttons"][lang]:
        MEMORY_DB["buttons"][lang].append(btn_name)
    await state.set_state(AdminStates.editing_buttons)
    await message.answer(f"✅ Qo'shildi!", reply_markup=get_user_reply_menu(message.from_user.id))

@dp.message(F.text == "🛑 Muharrirni to'xtatish")
async def stop_constructor(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔄 Oddiy rejim faol.", reply_markup=get_user_reply_menu(message.from_user.id))

# --- 🔥 ASOSIY MATN PROSESSORI TIZIMI ---

@dp.message()
async def main_bot_processor(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    if not await is_subscribed(user_id):
        await message.answer("Iltimos, avval kanalga a'zo bo'ling! /start")
        return

    all_movie_buttons = ["🎬 Kino Qidirish", "🎬 Search Movie", "🎬 Поиск Кино", "🎬 Kino Axtarış", "🎬 Film Ara", "🎬 Кино Іздеу", "🎬 Ҷустуҷӯи Кино", "🎬 Кино Издөө", "🎬 Kino Gözleg"]
    all_ai_buttons = ["🤖 Gemini AI Chat"]
    all_music_buttons = ["🎵 Musiqa Markazi", "🎵 Music Center", "🎵 Музыкальный Центр", "🎵 Musiqi Mərkəzi", "🎵 Müzik Merkezi", "🎵 Музыка Орталығы", "🎵 Маркази Мусиқӣ", "🎵 Музыка Борбору", "🎵 Saz Merkezi"]

    if text in all_movie_buttons:
        await message.answer("🎬 **Kino Tizimi**\n\nKino olish uchun uning kodini (faqat raqam o'zini) yuboring.")
        return
    elif text in all_ai_buttons:
        await message.answer("🤖 **Gemini AI**\n\nMenga savol yo'llang yoki rasm chizish uchun `rasm: xohlagan tasviringiz` ko'rinishida yozing.")
        return
    elif text in all_music_buttons:
        await message.answer("🎵 **Musiqa Markazi**\n\nQo'shiq qidirish uchun `musiqa: qo'shiq nomi` shaklida yozing.")
        return

    # A. KINO KODINI TEKSHIRISH (Faqat raqam bo'lsa)
    if text.isdigit():
        try:
            await bot.forward_message(chat_id=message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=int(text))
        except Exception:
            await message.answer("ℹ️ Bunday kodli film topilmadi.")
        return

    # B. 🎨 RASM CHIZISH PROMPT'I (Gemini matn modelidan tepada turishi shart!)
    if text.lower().startswith("rasm:"):
        prompt = text[5:].strip()
        if not ai_client:
            await message.answer("❌ Gemini API kaliti sozlanmagan.")
            return
        
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        try:
            result = ai_client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=dict(number_of_images=1)
            )
            for gen_img in result.generated_images:
                file_input = types.BufferedInputFile(gen_img.image.image_bytes, filename="ai_image.jpg")
                await bot.send_photo(chat_id=message.chat.id, photo=file_input, caption=f"🎨 **Siz so'ragan tasvir:**\n`{prompt}`")
            return
        except Exception as e:
            logging.error(f"Rasm chizishda xato: {e}")
            await message.answer("❌ Tasvirni chizishda xatolik yuz berdi. Promptni boshqacharoq yozib ko'ring.")
            return

    # C. 🎵 MUSIQA QIDIRISH SIMULATSIYASI
    if text.lower().startswith("musiqa:"):
        query = text[8:].strip()
        kb = InlineKeyboardBuilder()
        # Namuna uchun tugmalar (buni kengaytirish mumkin)
        kb.button(text="🎵 1-Variant", callback_data="vkm_play_1")
        kb.button(text="🎵 2-Variant", callback_data="vkm_play_2")
        kb.adjust(2)
        await message.answer(f"🔍 **'{query}' bo'yicha topilgan musiqalar:**", reply_markup=kb.as_markup())
        return

    # D. 💬 ODDIY CHAT BOT (GEMINI AI MATN MODELI)
    if ai_client:
        try:
            await bot.send_chat_action(chat_id=message.chat.id, action="typing")
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=text)
            await message.answer(response.text)
        except Exception:
            await message.answer("💬 ...")

@dp.callback_query(F.data.startswith("vkm_play_"))
async def play_music(callback: types.CallbackQuery):
    await callback.answer("🎵 Musiqa yuklanmoqda...", show_alert=False)
    await callback.message.answer("ℹ️ Musiqa server bazasidan qidirilmoqda. To'liq integratsiya uchun musiqa bazasi ulanishi kerak.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
