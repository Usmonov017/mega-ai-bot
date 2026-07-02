import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
import config

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Bot va Dispatcher
bot = Bot(
    token=config.BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# /start buyrug'i
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        f"<b>Salom, {message.from_user.full_name}!</b>\n\n"
        f"🤖 <b>Mega AI & Media Portal</b> botiga xush kelibsiz!\n"
        f"Hozirda botning poydevori muvaffaqiyatli qurilmoqda. "
        f"Tez orada barcha daxshatli funksiyalar ishga tushadi! 🚀"
    )

# Render tekin tarifda o'chib qolmasligi uchun soxta Web Sahifa ochamiz
async def handle_root(request):
    return web.Response(text="Bot is running smoothly 24/7!")

async def main():
    logger.info("Bot ishga tushmoqda...")
    
    # Render portini aniqlash (Render avtomatik PORT beradi)
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_root)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    # Web serverni orqa fonda ishga tushirish
    asyncio.create_task(site.start())
    logger.info(f"Web server {port}-portda ishga tushdi.")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot to'xtatildi!")
