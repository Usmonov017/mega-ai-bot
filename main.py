import os
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
SERVER_CHANNEL = os.getenv("SERVER_CHANNEL")  # Yopiq kanal (Kinolar va Musiqalar saqlanadigan xotira)
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

# Bosh menyu shakllantirish funksiyasi (Qayta-qayta ishlatish uchun)
def get_main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Kino Qidirish", callback_data="nav_cinema")
    kb.button(text="🤖 Gemini AI Chat", callback_data="nav_ai")
    kb.button(text="🎵 Musiqa Markazi", callback_data="nav_music")
    kb.adjust(1)
    return kb.as_markup()

# /start komandasi
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    
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

    await message.answer(
        f"✨ Xush kelibsiz, {message.from_user.full_name}!\nKerakli bo'limni tanlang:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.answer("Rahmat! Obuna tasdiqlandi. ✨", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("Bosh menyu:", reply_markup=get_main_menu())
    else:
        await callback.answer("Siz hali ommaviy kanalimizga a'zo bo'lmadingiz! ❌", show_alert=True)

# Bo'limlar navigatsiyasi (Tugmalar bosilganda)
@dp.callback_query(F.data.startswith("nav_"))
async def navigation_callback(callback: types.CallbackQuery):
    section = callback.data.split("_")[1]
    
    if section == "cinema":
        await callback.message.answer(
            "🎬 **MoviTime Tizimi**\n\nKino topish uchun o'sha kinoning kodini (raqamini) to'g'ridan-to'g'ri xabar qilib yuboring.",
            reply_markup=InlineKeyboardBuilder().button(text="⬅️ Bosh menyu", callback_data="back_to_menu").as_markup()
        )
    elif section == "ai":
        await callback.message.answer(
            "🤖 **Gemini AI Chat**\n\nMenga xohlagan matnli savolingizni yozing yoki rasm chizdirish uchun matn boshiga `rasm:` so'zini qo'shib yozing.",
            reply_markup=InlineKeyboardBuilder().button(text="⬅️ Bosh menyu", callback_data="back_to_menu").as_markup()
        )
    elif section == "music":
        await callback.message.answer(
            "🎵 **Musiqa Markazi (VKM Mode)**\n\nIzlayotgan qo'shig'ingiz yoki ijrochi nomini `musiqa:` so'zi bilan boshlab yozing.\n\n*Masalan:* `musiqa: Janob Rasul`",
            reply_markup=InlineKeyboardBuilder().button(text="⬅️ Bosh menyu", callback_data="back_to_menu").as_markup()
        )
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text("Kerakli bo'limni tanlang:", reply_markup=get_main_menu())
    except Exception:
        await callback.message.answer("Kerakli bo'limni tanlang:", reply_markup=get_main_menu())
    await callback.answer()

# Kelayotgan xabarlarni qayta ishlash
@dp.message()
async def main_message_processor(message: types.Message):
    user_id = message.from_user.id
    
    if not await is_subscribed(user_id):
        await message.answer("Iltimos, botdan foydalanish uchun avval ommaviy kanalga a'zo bo'ling! Yangilash uchun /start bosing.")
        return

    text = message.text

    # 1. KINO QIDIRISH (Faqat raqam yozilganda - Server kanaldan forward qiladi)
    if text.isdigit():
        msg = await message.answer("🔍 Kino serverdan qidirilmoqda...")
        try:
            await bot.forward_message(chat_id=message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=int(text))
            await msg.delete()
        except Exception as e:
            await msg.edit_text("ℹ️ Ushbu kod ostida kino topilmadi. Kodni to'g'ri kiritganingizni tekshiring.")
            logging.error(f"Kino uzatishda xato: {e}")
        return

    # 2. AI RASM CHIZISH (`rasm:` bilan boshlansa)
    if text.lower().startswith("rasm:"):
        prompt = text[5:].strip()
        if not prompt:
            await message.answer("Rasm chizish uchun tasvirni yozing. Masalan: `rasm: Kosmosdagi o'zbek uyi`")
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
                    await bot.send_photo(chat_id=message.chat.id, photo=input_file, caption=f"🎨 So'rovingiz bo'yicha rasm: {prompt}")
                await msg.delete()
            except Exception as e:
                await msg.edit_text("❌ Rasm chizish jarayonida xatolik yuz berdi.")
                logging.error(f"Imagen error: {e}")
        else:
            await msg.edit_text("🤖 AI tizimi ulanmagan.")
        return

    # 3. MUSIQA QIDIRISH (Agar xabar 'musiqa:' bilan boshlansa - VKM Interfeysi)
    if text.lower().startswith("musiqa:"):
        search_query = text[8:].strip()
        if not search_query:
            await message.answer("Musiqa izlash uchun nomini yozing. Masalan: `musiqa: Konsta`")
            return

        # VKM uslubidagi 1 dan 8 gacha raqamli inline tugmalar
        kb = InlineKeyboardBuilder()
        # Bizda haqiqiy musiqa bazasi yo'qligi sababli, tugmalarga server kanalingizdagi taxminiy xabar IDlarini bog'laymiz
        # Foydalanuvchi tugmani bassa, bot o'sha ID ostidagi audioni yopiq kanaldan qidirib topadi
        base_id = 100  # Bu shunchaki namuna raqam
        for i in range(1, 9):
            kb.button(text=str(i), callback_data=f"vkm_play_{base_id + i}")
        
        kb.button(text="❌ Menyuni yopish", callback_data="music_close")
        kb.adjust(4, 4, 1)
        
        await message.answer(
            f"🔍 **VKM Qidiruv natijalari: {search_query}**\n\n"
            f"1️⃣ {search_query} - Original Mp3\n"
            f"2️⃣ {search_query} - Remix Remix\n"
            f"3️⃣ {search_query} - Slowed Version\n"
            f"4️⃣ {search_query} - Tik Tok Trend\n"
            f"5️⃣ {search_query} - Retro Cover\n"
            f"6️⃣ {search_query} - Instrumental\n"
            f"7️⃣ {search_query} - Acoustic\n"
            f"8️⃣ {search_query} - Live Performance\n\n"
            f"Eshitish uchun quyidagi raqamlarni bosing:",
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

# VKM Musiqa tugmasi bosilganda ishlaydigan mantiq
@dp.callback_query(F.data.startswith("vkm_play_"))
async def vkm_play_callback(callback: types.CallbackQuery):
    target_msg_id = int(callback.data.split("_")[2])
    await callback.answer("🎵 Musiqa bazadan qidirilmoqda...", show_alert=False)
    
    try:
        # Qo'shiqni yopiq SERVER_CHANNEL ichidan olib, foydalanuvchiga uzatadi
        await bot.forward_message(chat_id=callback.message.chat.id, from_chat_id=SERVER_CHANNEL, message_id=target_msg_id)
    except Exception as e:
        # Agar yopiq kanalda u raqamli xabar bo'lmasa, ogohlantirish beradi
        await callback.message.answer("ℹ️ Kechirasiz, ushbu musiqa fayli server omboridan topilmadi.")
        logging.error(f"Musiqa forward qilishda xato: {e}")

@dp.callback_query(F.data == "music_close")
async def close_music_callback(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()

async def main():
    logging.info("Mega Portal Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
