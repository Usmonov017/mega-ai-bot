import os  # Kichik harf bilan to'g'rilandi
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google import genai

# Loglarni yoqamiz
logging.basicConfig(level=logging.INFO)

# Muhit o'zgaruvchilarini olish (Render Envs)
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL")  # Ommaviy kanal (Majburiy obuna uchun)
SERVER_CHANNEL = os.getenv("SERVER_CHANNEL")  # Yopiq kanal (Kinolar saqlanadigan bepul xotira)
GEMINI_KEY = os.getenv("GEMINI_API_KEY")       # Google AI API kaliti

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Gemini AI Klientini ishga tushiramiz
ai_client = None
if GEMINI_KEY:
    ai_client = genai.Client(api_key=GEMINI_KEY)

# Foydalanuvchining Ommaviy kanalga obunasini tekshirish funksiyasi
async def is_subscribed(user_id: int) -> bool:
    if not PUBLIC_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(chat_id=PUBLIC_CHANNEL, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception as e:
        logging.error(f"Ommaviy kanalga obunani tekshirishda xato: {e}")
        return False

# /start komandasi va bosh menyu yuklanishi
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    
    # Birinchi navbatda Ommaviy kanalga obunani tekshiramiz
    if not await is_subscribed(user_id):
        kb = InlineKeyboardBuilder()
        if str(PUBLIC_CHANNEL).startswith("-100"):
            clean_channel = str(PUBLIC_CHANNEL).replace('-100', '')
            channel_url = f"https://t.me/c/{clean_channel}"
        else:
            channel_url = f"https://t.me/{str(PUBLIC_CHANNEL).replace('@', '')}"
            
        kb.button(text="Kanalga a'zo bo'lish 🔐", url=channel_url)
        kb.button(text="Tekshirish ✅", callback_data="check_subscription")
        kb.adjust(1)
        
        await message.answer(
            "👋 Salom! Bot xizmatlaridan foydalanish uchun avval rasmiy ommaviy kanalimizga a'zo bo'ling.",
            reply_markup=kb.as_markup()
        )
        return

    # Asosiy Menyu Interfeysi
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Kino Qidirish", callback_data="nav_cinema")
    kb.button(text="🤖 Gemini AI Chat", callback_data="nav_ai")
    kb.button(text="🎵 Musiqa Markazi", callback_data="nav_music")
    kb.adjust(1)
    
    await message.answer(
        f"✨ Xush kelibsiz, {message.from_user.full_name}!\n"
        f"Kerakli bo'limni tanlang:",
        reply_markup=kb.as_markup()
    )

# Obunani tekshirish tugmasi bosilganda
@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.answer("Rahmat! Obuna tasdiqlandi. /start buyrug'ini bosing.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
    else:
        await callback.answer("Siz hali ommaviy kanalimizga a'zo bo'lmadingiz! ❌", show_alert=True)

# Bo'limlar navigatsiyasi
@dp.callback_query(F.data.startswith("nav_"))
async def navigation_callback(callback: types.CallbackQuery):
    section = callback.data.split("_")[1]
    
    if section == "cinema":
        await callback.message.answer("🎬 **MoviTime Tizimi**\n\nKino topish uchun o'sha kinoning kodini (raqamini) to'g'ridan-to'g'ri xabar qilib yuboring.")
    elif section == "ai":
        await callback.message.answer("🤖 **Gemini AI Chat**\n\nMenga xohlagan matnli savolingizni yozing yoki rasm chizdirish uchun matn boshiga `rasm:` so'zini qo'shib yozing.")
    elif section == "music":
        await callback.message.answer("🎵 **Musiqa Bo'limi**\n\nIzlayotgan qo'shig'ingiz yoki ijrochi nomini yozib yuboring (masalan, `musiqa: Janob Rasul`).")
    
    await callback.answer()

# Kelayotgan xabarlarni qayta ishlash
@dp.message()
async def main_message_processor(message: types.Message):
    user_id = message.from_user.id
    
    # Har qanday amal oldidan majburiy obunani tekshirish
    if not await is_subscribed(user_id):
        await message.answer("Iltimos, botdan foydalanish uchun avval ommaviy kanalga a'zo bo'ling! Yangilash uchun /start bosing.")
        return

    text = message.text

    # 1. KINO QIDIRISH (Faqat raqam yozilganda - Yopiq "Server" kanaldan qidiradi)
    if text.isdigit():
        msg = await message.answer("🔍 Kino serverdan qidirilmoqda...")
        try:
            await bot.forward_message(chat_id=message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=int(text))
            await msg.delete()
        except Exception as e:
            await msg.edit_text("ℹ️ Ushbu kod ostida kino topilmadi. Bot yopiq (server) kanalda admin ekanligini tekshiring!")
            logging.error(f"Server kanaldan kino uzatishda xato: {e}")
        return

    # 2. AI RASM CHIZISH (`rasm:` bilan boshlansa)
    if text.lower().startswith("rasm:"):
        prompt = text[5:].strip()
        if not prompt:
            await message.answer("Rasm chizish uchun tasvirni yozing. Masalan: `rasm: Kiborg o'zbek jangchisi`")
            return
            
        msg = await message.answer("🎨 Gemini AI tasvirni chizmoqda, kuting...")
        if ai_client:
            try:
                result = ai_client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt,
                    config=dict(number_of_images=1)
                )
                for generated_image in result.generated_images:
                    image_bytes = generated_image.image.image_bytes
                    input_file = types.BufferedInputFile(image_bytes, filename="ai_artwork.jpg")
                    await bot.send_photo(chat_id=message.chat.id, photo=input_file, caption=f"🎨 Sizning so'rovingiz: {prompt}")
                await msg.delete()
            except Exception as e:
                await msg.edit_text("❌ Rasm chizish jarayonida xatolik yuz berdi.")
                logging.error(f"Imagen error: {e}")
        else:
            await msg.edit_text("🤖 AI tizimi ulanmagan. GEMINI_API_KEY sozlamalarini tekshiring.")
        return

    # 3. MUSIQA QIDIRISH (Agar xabar 'musiqa:' bilan boshlansa)
    if text.lower().startswith("musiqa:"):
        search_query = text[8:].strip()
        if not search_query:
            await message.answer("Musiqa izlash uchun nomini yozing. Masalan: `musiqa: Sherali Jo'rayev`")
            return

        kb = InlineKeyboardBuilder()
        for i in range(1, 9):
            kb.button(text=str(i), callback_data=f"play_track_{i}")
        kb.button(text="⬅️", callback_data="music_prev")
        kb.button(text="❌", callback_data="music_close")
        kb.button(text="➡️", callback_data="music_next")
        kb.adjust(4, 4, 3)
        
        await message.answer(
            f"🔍 **Qidiruv natijalari: {search_query}**\n\n"
            f"1. {search_query} - Original Mix [03:45]\n"
            f"2. {search_query} - Slowed Reverb [04:12]\n"
            f"3. {search_query} - Remix Version [02:50]\n"
            f"4. {search_query} - TikTok Trend [03:10]\n\n"
            f"Natijalar 1-4. Eshitish uchun quyidagi raqamlarni bosing:",
            reply_markup=kb.as_markup()
        )
        return

    # 4. GEMINI AI MATNLI CHAT (Boshqa barcha holatlarda)
    if ai_client:
        msg = await message.answer("🤔 O'ylayapman...")
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=text,
            )
            await msg.edit_text(response.text)
        except Exception as e:
            await msg.edit_text("❌ Tizim javob berishda xatoga duch keldi.")
            logging.error(f"Gemini Text error: {e}")
    else:
        await message.answer("🤖 Sun'iy intellekt moduli faollashtirilmagan.")

@dp.callback_query(F.data.startswith("play_track_"))
async def play_track_callback(callback: types.CallbackQuery):
    track_num = callback.data.split("_")[2]
    await callback.answer(f"🎵 {track_num}-raqamli qo'shiq yuklanmoqda...", show_alert=False)

@dp.callback_query(F.data == "music_close")
async def close_music_callback(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

async def main():
    logging.info("Mega Portal Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
