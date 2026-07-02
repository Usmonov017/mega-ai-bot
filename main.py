import os, asyncio
from loader import dp, bot
from handlers import get_handlers_router

async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    # Routerlarni ulash
    dp.include_router(get_handlers_router())
    
    print("🚀 Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
