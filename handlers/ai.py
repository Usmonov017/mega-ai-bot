from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loader import bot, ai_client
import logging

router = Router()

@router.message(F.text == "🤖 Gemini AI Chat")
async def ai_menu(message: types.Message):
    await message.answer("🤖 **Gemini AI faol.**\n\nSavol yozing yoki rasm chizish uchun `rasm: so'z` ko'rinishida yozing.")

@router.message(F.text.lower().startswith("rasm:"))
async def draw_image(message: types.Message):
    prompt = message.text[5:].strip()
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
    try:
        result = ai_client.models.generate_images(model='imagen-3.0-generate-002', prompt=prompt, config=dict(number_of_images=1))
        for gen_img in result.generated_images:
            file_input = types.BufferedInputFile(gen_img.image.image_bytes, filename="ai_image.jpg")
            await bot.send_photo(chat_id=message.chat.id, photo=file_input, caption=f"🎨 **Tasvir:** `{prompt}`")
    except Exception:
        await message.answer("❌ Rasm chizishda xatolik.")

@router.message()
async def chat_ai(message: types.Message):
    # Agar matn raqam bo'lsa yoki boshqa handlerga tegishli bo'lsa o'tkazib yuboradi
    if message.text.isdigit() or message.text.startswith("🎵"): return
    
    if ai_client:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        try:
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=message.text)
            await message.answer(response.text)
        except:
            await message.answer("💬 ...")

