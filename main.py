```python
import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from google import genai

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# Muhit o'zgaruvchilari (Config)
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL", "@MoviTimeUz")
SERVER_CHANNEL = os.getenv("SERVER_CHANNEL", "@MoviTimeUz")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

# Bot obyektlarini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Tillar va xotira (Database o'rnida)
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
        "az": ["🎬 Kino Axtarış", "🎵 Musiqi Mərkəzi"],
        "tr": ["🎬 Film Ara", "🎵 Müzik Merkezi"],
        "kk": ["🎬 Кино Іздеу", "🎵 Musyqa Ortalyǵy"],
        "tg": ["🎬 Ҷустуҷӯи Кино", "🎵 Маркази Мусиқӣ"],
        "ky": ["🎬 Кино Издөө", "🎵 Музыка Борбору"],
        "tk": ["🎬 Kino Gözleg", "🎵 Saz Merkezi"]
    },
    "temp_music": {}
}

# FSM holatlari
class UserStates(StatesGroup):
    searching_music = State()

class AdminStates(StatesGroup):
    editing_buttons = State()

# --- YORDAMCHI FUNKSIYALAR ---

async def is_subscribed(user_id: int) -> bool:
    if not PUBLIC_CHANNEL: return True
    try:
        member = await bot.get_chat_member(chat_id=PUBLIC_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def get_user_reply_menu(user_id: int):
    lang = MEMORY_DB.get("users", {}).get(user_id, {}).get("lang", "uz")
    builder = ReplyKeyboardBuilder()
    buttons = MEMORY_DB.get("buttons", {}).get(lang, MEMORY_DB["buttons"]["en"])
    for btn in buttons:
        builder.button(text=btn)
    if user_id == ADMIN_ID:
        builder.button(text="⚙️ Tugmalar muharriri")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- MENU VA TILLAR (START) ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in MEMORY_DB["users"]:
        MEMORY_DB["users"][user_id] = {"lang": "uz"}
    
    if not await is_subscribed(user_id):
        kb = InlineKeyboardBuilder()
        channel_url = f"https://t.me/{str(PUBLIC_CHANNEL).replace('@', '')}"
        kb.button(text="Kanalga a'zo bo'lish 🔐", url=channel_url)
        await message.answer("👋 Botdan foydalanish uchun kanalga a'zo bo'ling.", reply_markup=kb.as_markup())
        return

    kb = InlineKeyboardBuilder()
    for code, name in ALL_LANGUAGES.items():
        kb.button(text=name, callback_data=f"set_lang_{code}")
    kb.adjust(2)
    await message.answer("🌐 Tilingizni tanlang / Select your language:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[2]
    user_id = callback.from_user.id
    MEMORY_DB["users"][user_id] = {"lang": lang}
    await callback.answer(f"{ALL_LANGUAGES.get(lang)} tanlandi", show_alert=False)
    await callback.message.answer("🏠 Menyu:", reply_markup=get_user_reply_menu(user_id))

# --- MUSIQA MARKAZI (VK MUSIC API) ---

async def search_vk_style_music(query: str):
    url = f"https://api.deezer.com/search?q={query}&limit=6"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    for track in data.get('data', []):
                        results.append({
                            'title': f"{track['artist']['name']} - {track['title']}",
                            'url': track['preview'],
                            'duration': track['duration']
                        })
                    return results
    except Exception as e:
        print(f"Musiqa topishda xato: {e}")
    return []

@dp.message(F.text.in_(["🎵 Musiqa Markazi", "🎵 Music Center", "🎵 Музыкальный Центр", "🎵 Musiqi Mərkəzi", "🎵 Müzik Merkezi", "🎵 Musyqa Ortalyǵy", "🎵 Маркази Мусиқӣ", "🎵 Музыка Борбору", "🎵 Saz Merkezi"]))
async def music_mode_activate(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.searching_music)
    await message.answer("🎵 **Musiqa qidiruv tizimi faol!**\n\nQo'shiq nomi yoki ijrochini yozing (Masalan: *Konsta*):")

@dp.message(UserStates.searching_music)
async def process_music_search(message: types.Message, state: FSMContext):
    query = message.text
    status_msg = await message.answer("🔍 Qo'shiqlar qidirilmoqda...")
    
    songs = await search_vk_style_music(query)
    
    if not songs:
        await status_msg.edit_text("ℹ️ Hech narsa topilmadi. Qo'shiq nomini to'g'rilab yozing.")
        await state.clear()
        return

    user_id = message.from_user.id
    MEMORY_DB["temp_music"][user_id] = songs
    
    response_text = f"🔍 **Natijalar:**\n\n"
    kb = InlineKeyboardBuilder()
    
    for idx, song in enumerate(songs, start=1):
        minut = song['duration'] // 60
        sekund = song['duration'] % 60
        response_text += f"{idx}. 🎵 {song['title']} [{minut}:{sekund:02d}]\n"
        kb.button(text=str(idx), callback_data=f"vkm_download_{idx}")
        
    kb.button(text="❌ Yopish", callback_data="vkm_close")
    kb.adjust(3, 3, 1)
    
    await status_msg.delete()
    await message.answer(response_text, reply_markup=kb.as_markup())
    await state.clear()

@dp.callback_query(F.data.startswith("vkm_download_"))
async def download_music(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[2]) - 1
    user_id = callback.from_user.id
    
    songs = MEMORY_DB["temp_music"].get(user_id)
    if not songs or idx >= len(songs):
        await callback.answer("❌ Seans muddati tugagan.", show_alert=True)
        return
        
    selected_song = songs[idx]
    await callback.message.answer(f"📥 **{selected_song['title']}** yuborilmoqda...")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_voice")
    
    try:
        audio_file = types.URLInputFile(selected_song['url'], filename=f"{selected_song['title']}.mp3")
        await bot.send_audio(
            chat_id=callback.message.chat.id, 
            audio=audio_file, 
            title=selected_song['title'],
            performer="Mega Bot Music"
        )
    except Exception:
        await callback.message.answer("❌ Kechirasiz, musiqani yuborib bo'lmadi.")

@dp.callback_query(F.data == "vkm_close")
async def close_music_menu(callback: types.CallbackQuery):
    await callback.message.delete()

# --- ASOSIY PROSESSOR (KINO VA AI) ---

@dp.message()
async def main_bot_processor(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    if not await is_subscribed(user_id):
        await message.answer("Iltimos, avval kanalga a'zo bo'ling! /start")
        return

    # 1. Rasm chizish (Gemini AI)
    if text.lower().startswith("rasm:"):
        prompt = text[5:].strip()
        if not ai_client:
            await message.answer("🤖 AI kaliti ulanmagan.")
            return
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        try:
            result = ai_client.models.generate_images(model='imagen-3.0-generate-002', prompt=prompt, config=dict(number_of_images=1))
            for gen_img in result.generated_images:
                file_input = types.BufferedInputFile(gen_img.image.image_bytes, filename="ai.jpg")
                await bot.send_photo(chat_id=message.chat.id, photo=file_input, caption=f"🎨 `{prompt}`")
        except Exception:
            await message.answer("❌ Rasm chizishda xatolik yuz berdi.")
        return

    # 2. Kino qidirish (Forward)
    if text.isdigit():
        try:
            await bot.forward_message(chat_id=message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=int(text))
        except Exception:
            await message.answer("ℹ️ Bunday kodli film topilmadi.")
        return

    # 3. Kino menyusi bosilganda
    movie_buttons = ["🎬 Kino Qidirish", "🎬 Search Movie", "🎬 Поиск Кино", "🎬 Kino Axtarış", "🎬 Film Ara", "🎬 Кино Іздеу", "🎬 Ҷустуҷӯи Кино", "🎬 Кино Издөө", "🎬 Kino Gözleg"]
    if text in movie_buttons:
        await message.answer("🎬 **Kino qidirish**\nKino kodini (raqamini) yozib yuboring:")
        return

    # 4. Oddiy AI Chat (Gemini)
    if ai_client and text not in ["🤖 Gemini AI Chat"]:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        try:
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=text)
            await message.answer(response.text)
        except Exception:
            pass
    elif text == "🤖 Gemini AI Chat":
        await message.answer("🤖 Menga xohlagan savolingizni yozing yoki rasm chizish uchun `rasm: ` deb yozing.")
# --- BOTNI ISHGA TUSHIRISH ---

async def handle(request):
    return aiohttp.web.Response(text="Bot is running successfully!")

async def main():
    # Render port tekshiruvidan o'tish uchun kichik veb-server
    app = aiohttp.web.Application()
    app.router.add_get('/', handle)
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = aiohttp.web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    print("🚀 Mega Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
