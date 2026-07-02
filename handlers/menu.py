from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import config
from loader import bot, MEMORY_DB

router = Router()

class AdminStates(StatesGroup):
    editing_buttons = State()
    adding_button = State()

async def is_subscribed(user_id: int) -> bool:
    if not config.PUBLIC_CHANNEL: return True
    try:
        member = await bot.get_chat_member(chat_id=config.PUBLIC_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

def get_user_reply_menu(user_id: int):
    lang = MEMORY_DB["users"].get(user_id, {}).get("lang", "uz")
    builder = ReplyKeyboardBuilder()
    buttons = MEMORY_DB["buttons"].get(lang, MEMORY_DB["buttons"]["en"])
    for btn in buttons:
        builder.button(text=btn)
    if user_id == config.ADMIN_ID:
        builder.button(text="⚙️ Tugmalar muharriri")
        builder.button(text="🛑 Muharrirni to'xtatish")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))  # loader'dan dp emas, to'g'ridan-to'g'ri router ishlatiladi
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in MEMORY_DB["users"]:
        MEMORY_DB["users"][user_id] = {"lang": "uz"}
    if not await is_subscribed(user_id):
        kb = InlineKeyboardBuilder()
        channel_url = f"https://t.me/{str(config.PUBLIC_CHANNEL).replace('@', '')}"
        kb.button(text="Kanalga a'zo bo'lish 🔐", url=channel_url)
        kb.adjust(1)
        await message.answer("👋 Botdan foydalanish uchun kanalga a'zo bo'ling.", reply_markup=kb.as_markup())
        return
    
    kb = InlineKeyboardBuilder()
    for code, name in config.ALL_LANGUAGES.items():
        kb.button(text=name, callback_data=f"set_lang_{code}")
    kb.adjust(2)
    await message.answer("🌐 Tilingizni tanlang / Select your language:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[2]
    user_id = callback.from_user.id
    MEMORY_DB["users"][user_id] = {"lang": lang}
    await callback.answer(f"✓ {config.ALL_LANGUAGES.get(lang)}", show_alert=False)
    await callback.message.answer(f"🤖 Menyu:", reply_markup=get_user_reply_menu(user_id))

# Admin rejimlari handlerlari shu yerda davom etadi...

