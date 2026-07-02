from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from google import genai
import config

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = genai.Client(api_key=config.GEMINI_KEY) if config.GEMINI_KEY else None

# Dinamik xotira bazasi
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
MEMORY_DB = {"temp_music": {}}

