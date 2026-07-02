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

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# Muhit o'zgaruvchilari (Render yoki .env uchun)
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL")
SERVER_CHANNEL = os.getenv("SERVER_CHANNEL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # O'zingizning Telegram ID'ingizni kiriting

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Gemini AI Klienti
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- DINAMIK BAZA (Xotirada saqlash uchun sodda DB model) ---
MEMORY_DB = {
    "users": {},          # {user_id: {"lang": "uz"}}
    "buttons": {          # Dinamik tugmalar ro'yxati
        "uz": ["🎬 Kino Qidirish", "🤖 Gemini AI Chat", "🎵 Musiqa Markazi"],
        "en": ["🎬 Search Movie", "🤖 Gemini AI Chat", "🎵 Music Center"],
        "ru": ["🎬 Поиск Кино", "🤖 Gemini AI Chat", "🎵 Музыкальный Центр"]
    },
    "custom_responses": {} # {button_name: "Xabar matni"}
}

# FSM Davlatlari (Admin rejimlari uchun)
class AdminStates(StatesGroup):
    editing_buttons = State()
    adding_button = State()
    editing_button_props = State()
    editing_messages = State()
    adding_message_text = State()

# --- YORDAMChI FUNKSIYALAR ---
async def is_subscribed(user_id: int) -> bool:
    if not PUBLIC_CHANNEL: @MoviTimeUz
        return True
    try:
        member = await bot.get_chat_member(chat_id=PUBLIC_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Obunani tekshirishda xato: {e}")
        return False

def get_user_lang(user_id: int) -> str:
    return MEMORY_DB["users"].get(user_id, {}).get("lang", "uz")

# 📱 USER MENYUSI (Dinamik tillar va tugmalar asosida shakllanadi)
def get_user_reply_menu(user_id: int):
    lang = get_user_lang(user_id)
    builder = ReplyKeyboardBuilder()
    buttons = MEMORY_DB["buttons"].get(lang, MEMORY_DB["buttons"]["uz"])
    
    for btn in buttons:
        builder.button(text=btn)
    
    # Agar admin bo'lsa, pastdan boshqaruv tugmasini ko'rsatish
    if user_id == ADMIN_ID:
        builder.button(text="⚙️ Tugmalar muharriri")
        builder.button(text="📝 Xabar tahrirlash")
        
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# 🌐 MULTILANGUAGE KLAVIATURA (`6679.jpg` dagi kabi)
def get_lang_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇬🇧 English", callback_data="set_lang_en")
    kb.button(text="🇷🇺 Русский", callback_data="set_lang_ru")
    kb.button(text="🇺🇿 O'zbek", callback_data="set_lang_uz")
    kb.adjust(1)
    return kb.as_markup()

# 🛠️ ADMIN VISUAL CONSTRUCTOR TUGMALARI (`6681.jpg` va `6682.jpg` dagi kabi)
def get_admin_constructor_kb():
    kb = InlineKeyboardBuilder()
    # Navigatsiya o'qlari
    kb.button(text="⬅️", callback_data="btn_left")
    kb.button(text="🔼", callback_data="btn_up")
    kb.button(text="🔽", callback_data="btn_down")
    kb.button(text="➡️", callback_data="btn_right")
    kb.button(text="*️⃣", callback_data="btn_star")
    # Amal tugmalari
    kb.button(text="➕ Tahrirlash", callback_data="btn_edit_prop")
    kb.button(text="❌ O'chirish", callback_data="btn_delete")
    kb.button(text="📋 Ko'chirish", callback_data="btn_copy")
    kb.adjust(5, 3)
    return kb.as_markup()

def get_admin_reply_constructor():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Tugma Qo'shish")
    builder.button(text="🛑 Muharrirni to'xtatish")
    builder.button(text="📝 Xabar muharriri")
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

# --- BUYRUQLAR VA KOD TIZIMI ---

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

    # Til tanlash xabarini chiqarish (`6679.jpg` dagi kabi tekst va admin menyusi)
    lang_text = (
        "👋 **Welcome to the Menu Builder.**\n\n"
        "You can change your language:\n"
        "🇬🇧 English . . . . . . /langen\n"
        "🇷🇺 Русский . . . . . . /langru\n"
        "🇺🇿 O'zbek . . . . . . /languz\n\n"
        "_(This message helps you build and control everything!)_"
    )
    await message.answer(lang_text, reply_markup=get_lang_keyboard())

# Tilni o'zgartirish callback'lari
@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[2]
    user_id = callback.from_user.id
    MEMORY_DB["users"][user_id] = {"lang": lang}
    
    lang_names = {"uz": "O'zbek", "en": "English", "ru": "Русский"}
    await callback.answer(f"✓ Til {lang_names[lang]} tiliga o'girildi !", show_alert=False)
    await callback.message.answer(f"🤖 Asosiy Menyu ({lang_names[lang]}):", reply_markup=get_user_reply_menu(user_id))

# --- ⚙️ ADMIN TUGMALAR MUHARRIRI (VISUAL CONSTRUCTOR) ---

@dp.message(F.text == "⚙️ Tugmalar muharriri", F.from_user.id == ADMIN_ID)
async def admin_mode_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.editing_buttons)
    await message.answer("🔧 **Siz Tugmalarni Tahrirlash rejimidasisiz.**", reply_markup=get_admin_reply_constructor())
    
    # `6681.jpg` dagi kabi sozlamalar oynasi matni
    settings_text = (
        "🔧 **Tugmani tahrirlash:**\n\n"
        "■ Tasodifiy xabar: 🟦 O'chiq\n"
        "■ Faqat admin: 🟦 O'chiq\n"
        "■ Yashirin: 🟦 O'chiq\n"
        "■ Captcha: 🟦 O'chiq\n"
        "■ Obuna (join): 🟦 O'chiq\n"
        "■ Buyruq: ---\n"
        "■ Shart: ---\n"
        "■ Navigatsiya: 🟦 O'chiq\n"
        "■ Shop: ---"
    )
    await message.answer(settings_text, reply_markup=get_admin_constructor_kb())

@dp.message(F.text == "➕ Tugma Qo'shish", AdminStates.editing_buttons)
async def add_button_prompt(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.adding_button)
    await message.answer("📝 Yangi tugma nomini kiriting:")

@dp.message(AdminStates.adding_button)
async def add_button_save(message: types.Message, state: FSMContext):
    btn_name = message.text
    lang = get_user_lang(message.from_user.id)
    
    if btn_name not in MEMORY_DB["buttons"][lang]:
        MEMORY_DB["buttons"][lang].append(btn_name)
        
    await state.set_state(AdminStates.editing_buttons)
    await message.answer(f"✅ '{btn_name}' tugmasi muvaffaqiyatli qo'shildi!", reply_markup=get_user_reply_menu(message.from_user.id))

@dp.message(F.text == "🛑 Muharrirni to'xtatish")
async def stop_constructor(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔄 Muharrir to'xtatildi. Oddiy rejim faol.", reply_markup=get_user_reply_menu(message.from_user.id))

# --- 📝 XABARLAR MUHARRIRI (`6684.jpg` dagi kabi) ---

@dp.message(F.text == "📝 Xabar tahrirlash", F.from_user.id == ADMIN_ID)
@dp.message(F.text == "📝 Xabar muharriri", F.from_user.id == ADMIN_ID)
async def messages_edit_mode(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.editing_messages)
    
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Xabar Qo'shish")
    kb.button(text="🔄 Muharrirda sahifalash (10)")
    kb.button(text="⚙️ Tugmalar muharriri")
    kb.button(text="🛑 Muharrirni to'xtatish")
    kb.adjust(1, 1, 2)
    
    await message.answer("🔧 **You are in Messages Editing mode.**", reply_markup=kb.as_markup(resize_keyboard=True))

# --- FOYDALANUVChI SO'ROVLARI VA ASOSIY FUNKSIYALAR ---

@dp.message()
async def main_bot_processor(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text

    # Obunani majburiy tekshirish
    if not await is_subscribed(user_id):
        await message.answer("Iltimos, avval ommaviy kanalga a'zo bo'ling! /start tugmasini bosing.")
        return

    # Sobiq koddagi funksiyalar (Tugmalar bosilganda ishlaydi)
    if text in ["🎬 Kino Qidirish", "🎬 Search Movie", "🎬 Поиск Кино"]:
        await message.answer("🎬 **MoviTime Tizimi**\n\nKino topish uchun o'sha kinoning kodini (faqat raqam o'zini) yozib yuboring.")
        return
        
    elif text in ["🤖 Gemini AI Chat"]:
        await message.answer("🤖 **Gemini AI Chat**\n\nMenga xohlagan matnli savolingizni kiriting yoki rasm chizish uchun `rasm: ko'rinish tavsifi` ko'rinishida yozing.")
        return
        
    elif text in ["🎵 Musiqa Markazi", "🎵 Music Center", "🎵 Музыкальный Центр"]:
        await message.answer("🎵 **Musiqa Markazi**\n\nQo'shiq nomini `musiqa: qo'shiq nomi` shaklida yozib yuboring.")
        return

    # 1. KINO QIDIRISH TIZIMI (Faqat raqamlar yuborilganda)
    if text.isdigit():
        msg = await message.answer("🔍 Serverdan qidirilmoqda...")
        try:
            await bot.forward_message(chat_id=message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=int(text))
            await msg.delete()
        except Exception:
            await msg.edit_text("ℹ️ Ushbu kod ostida hech narsa topilmadi.")
        return

    # 2. AI RASM CHIZISH PROMPT'I
    if text.lower().startswith("rasm:"):
        prompt = text[5:].strip()
        msg = await message.answer("🎨 Tasvir yaratilmoqda...")
        if ai_client:
            try:
                result = ai_client.models.generate_images(model='imagen-3.0-generate-002', prompt=prompt, config=dict(number_of_images=1))
                for gen_img in result.generated_images:
                    file_input = types.BufferedInputFile(gen_img.image.image_bytes, filename="ai.jpg")
                    await bot.send_photo(chat_id=message.chat.id, photo=file_input, caption=f"🎨 Tavsif: {prompt}")
                await msg.delete()
            except Exception:
                await msg.edit_text("❌ Rasm yaratishda xatolik.")
        return

    # 3. MUSIQA INTERFEYSI (`musiqa:`)
    if text.lower().startswith("musiqa:"):
        query = text[8:].strip()
        kb = InlineKeyboardBuilder()
        for i in range(1, 5):
            kb.button(text=f"🎵 {i}-Musiqa", callback_data=f"vkm_play_{100+i}")
        kb.adjust(2)
        await message.answer(f"🔍 **Qidiruv natijalari: {query}**\n\nKerakli raqamni tanlang:", reply_markup=kb.as_markup())
        return

    # 4. CHAT BOT (GEMINI AI SAVOL-JAVOB)
    if ai_client:
        try:
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=text)
            await message.answer(response.text)
        except Exception:
            await message.answer("🤖 Hozircha javob berishda muammo yuzaga keldi.")

# Musiqani yuborish handler'i
@dp.callback_query(F.data.startswith("vkm_play_"))
async def play_music(callback: types.CallbackQuery):
    msg_id = int(callback.data.split("_")[2])
    try:
        await bot.forward_message(chat_id=callback.message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=msg_id)
    except Exception:
        await callback.answer("❌ Fayl topilmadi.", show_alert=True)

# Botni ishga tushirish
async def main():
    logging.info("Visual Constructor va barcha funksiyalar yuklandi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
