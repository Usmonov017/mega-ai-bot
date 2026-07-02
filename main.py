import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import config

# Loglarni sozlash (Serverda bot qanday ishlayotganini kuzatish uchun)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(
    token=config.BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Ilk sinov handler: /start buyrug'i uchun
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        f"<b>Salom, {message.from_user.full_name}!</b>\n\n"
        f"🤖 <b>Mega AI & Media Portal</b> botiga xush kelibsiz!\n"
        f"Hozirda botning poydevori muvaffaqiyatli qurilmoqda. "
        f"Tez orada barcha daxshatli funksiyalar ishga tushadi! 🚀"
    )

# Botni ishga tushirish asinxron funksiyasi
async def main():
    logger.info("Bot muvaffaqiyatli ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot to'xtatildi!")

