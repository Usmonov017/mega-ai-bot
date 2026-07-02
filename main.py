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
import yt_dlp

logging.basicConfig(level=logging.INFO)

# Muhit o'zgaruvchilari
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL", "@MoviTimeUz")
SERVER_CHANNEL = os.getenv("SERVER_CHANNEL", "@MoviTimeUz")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

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
    },
    "temp_music": {} # Qidiruv natijalarini vaqtincha saqlash uchun
}

class AdminStates(StatesGroup):
    editing_buttons = State()
    adding_button = State()

class UserStates(StatesGroup):
    searching_music = State()

# --- INTERNETDAN QIDIRISH (TEKIN API) ---
def search_youtube_music(query: str):
    """ Kalitsiz ochiq API: Internetdan musiqalarni qidirish """
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch3', # 3 ta eng mos musiqani topadi
    }
    results = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    results.append({
                        'title': entry.get('title'),
                        'url': entry.get('webpage_url'),
                        'duration': entry.get('duration')
                    })
        except Exception as e:
            logging.error(f"Musiqa qidirishda xato: {e}")
    return results

async def is_subscribed(user_id: int) -> bool:
    if not PUBLIC_CHANNEL: return True
    try:
        member = await bot.get_chat_member(chat_id=PUBLIC_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

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

# --- MUSIQA APISINI IShLATISh TIZIMI ---

@dp.message(F.text.in_(["🎵 Musiqa Markazi", "🎵 Music Center", "🎵 Музыкальный Центр", "🎵 Musiqi Mərkəzi", "🎵 Müzik Merkezi", "🎵 Музыка Орталығы", "🎵 Маркази Мусиқӣ", "🎵 Музыка Борбору", "🎵 Saz Merkezi"]))
async def music_mode_activate(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.searching_music)
    await message.answer("🎵 **Musiqa qidirish tizimi ishga tushdi.**\n\nQo'shiq nomi yoki ijrochini yozing:")

@dp.message(UserStates.searching_music)
async def process_music_search(message: types.Message, state: FSMContext):
    query = message.text
    status_msg = await message.answer("🔍 Internet bazasidan qidirilmoqda...")
    
    # API orqali qidirish funksiyasini chaqiramiz
    loop = asyncio.get_event_loop()
    songs = await loop.run_in_executor(None, search_youtube_music, query)
    
    if not songs:
        await status_msg.edit_text("ℹ️ Hech qanday musiqa topilmadi. Boshqa nom yozib ko'ring.")
        return

    # Vaqtincha xotiraga saqlab turamiz (foydalanuvchi tugmani bosganda yuklash uchun)
    user_id = message.from_user.id
    MEMORY_DB["temp_music"][user_id] = songs

    response_text = f"🔍 **'{query}' bo'yicha topilgan musiqalar:**\n\n"
    kb = InlineKeyboardBuilder()
    
    for idx, song in enumerate(songs, start=1):
        minut = song['duration'] // 60
        sekund = song['duration'] % 60
        response_text += f"{idx}. 🎵 {song['title']} [{minut}:{sekund:02d}]\n"
        kb.button(text=str(idx), callback_data=f"vkm_download_{idx}")
        
    kb.button(text="❌ Yopish", callback_data="vkm_close")
    kb.adjust(3, 1)
    
    await status_msg.delete()
    await message.answer(response_text, reply_markup=kb.as_markup())
    await state.clear()

# Musiqani (.mp3) yuklab yuborish handler'i
@dp.callback_query(F.data.startswith("vkm_download_"))
async def download_and_send_music(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[2]) - 1
    user_id = callback.from_user.id
    
    songs = MEMORY_DB["temp_music"].get(user_id)
    if not songs or idx >= len(songs):
        await callback.answer("❌ Seans muddati tugagan. Qaytadan qidiring.", show_alert=True)
        return
        
    selected_song = songs[idx]
    await callback.message.answer(f"📥 **{selected_song['title']}** yuklab olinmoqda, iltimos kuting...")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_voice")

    # Audio faylni vaqtincha yuklash sozlamalari
    outtmpl = f"downloads/{user_id}_%(id)s.%(ext)s"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Faylni internetdan yuklab olamiz
            info = await loop.run_in_executor(None, ydl.extract_info, selected_song['url'], True)
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            
            # Telegramga audio fayl qilib yuboramiz
            audio_file = types.FSInputFile(filename)
            await bot.send_audio(
                chat_id=callback.message.chat.id, 
                audio=audio_file, 
                title=selected_song['title'],
                performer="Musiqa Markazi Bot"
            )
            # Server xotirasini to'ldirmaslik uchun faylni darrov o'chiramiz
            if os.path.exists(filename):
                os.remove(filename)
    except Exception as e:
        logging.error(f"Yuklashda xato: {e}")
        await callback.message.answer("❌ Kechirasiz, ushbu audioni yuklash imkoni bo'lmadi.")

@dp.callback_query(F.data == "vkm_close")
async def close_music_menu(callback: types.CallbackQuery):
    await callback.message.delete()

# --- QOLGAN ASOSIY PROSESSORLAR (Kino va Rasm) ---
@dp.message()
async def main_bot_processor(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    if text.lower().startswith("rasm:"):
        prompt = text[5:].strip()
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        try:
            result = ai_client.models.generate_images(model='imagen-3.0-generate-002', prompt=prompt, config=dict(number_of_images=1))
            for gen_img in result.generated_images:
                file_input = types.BufferedInputFile(gen_img.image.image_bytes, filename="ai_image.jpg")
                await bot.send_photo(chat_id=message.chat.id, photo=file_input, caption=f"🎨 **Tasvir:** `{prompt}`")
        except Exception:
            await message.answer("❌ Rasm chizishda xatolik.")
        return

    if text.isdigit():
        try:
            await bot.forward_message(chat_id=message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=int(text))
        except:
            await message.answer("ℹ️ Film topilmadi.")
        return

    if ai_client:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        try:
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=text)
            await message.answer(response.text)
        except:
            await message.answer("💬 ...")

async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
