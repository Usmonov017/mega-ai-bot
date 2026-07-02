from aiogram import Router, types, F
import config
from loader import bot

router = Router()

@router.message(F.text.in_(["🎬 Kino Qidirish", "🎬 Search Movie", "🎬 Поиск Кино"]))
async def kino_menu(message: types.Message):
    await message.answer("🎬 **Kino kodini yuboring (faqat raqam):**")

@router.message(F.text.isdigit())
async def forward_movie(message: types.Message):
    try:
        await bot.forward_message(chat_id=message.chat.id, from_chat_id=config.SERVER_CHANNEL, message_id=int(message.text))
    except:
        await message.answer("ℹ️ Bunday kodli film topilmadi.")

