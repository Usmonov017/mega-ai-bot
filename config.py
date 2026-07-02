import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL", "@MoviTimeUz")
SERVER_CHANNEL = os.getenv("SERVER_CHANNEL", "@MoviTimeUz")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

ALL_LANGUAGES = {
    "en": "🇬🇧 English", "ru": "🇷🇺 Русский", "uz": "🇺🇿 O'zbekcha",
    "az": "🇦🇿 Azərbaycan", "tr": "⭐️ Türkçe", "kk": "🇰🇿 Қазақша",
    "tg": "🇹🇯 Тоҷикӣ", "ky": "🇰🇬 Кыргызча", "tk": "🇹🇲 Türkmençe"
}

