import os, asyncio
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import yt_dlp
from loader import bot, MEMORY_DB

router = Router()

class UserStates(StatesGroup):
    searching_music = State()

def search_youtube_music(query: str):
    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'ytsearch3'}
    results = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    results.append({'title': entry.get('title'), 'url': entry.get('webpage_url'), 'duration': entry.get('duration')})
        except: pass
    return results

@router.message(F.text.in_(["🎵 Musiqa Markazi", "🎵 Music Center", "🎵 Музыкальный Центр"]))
async def music_mode_activate(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.searching_music)
    await message.answer("🎵 **Qo'shiq nomi yoki ijrochini yozing:**")

@router.message(UserStates.searching_music)
async def process_music_search(message: types.Message, state: FSMContext):
    query = message.text
    status_msg = await message.answer("🔍 Qidirilmoqda...")
    
    loop = asyncio.get_event_loop()
    songs = await loop.run_in_executor(None, search_youtube_music, query)
    
    if not songs:
        await status_msg.edit_text("ℹ️ Musiqa topilmadi.")
        return

    user_id = message.from_user.id
    MEMORY_DB["temp_music"][user_id] = songs
    
    response_text = f"🔍 **Natijalar:**\n\n"
    kb = InlineKeyboardBuilder()
    for idx, song in enumerate(songs, start=1):
        response_text += f"{idx}. 🎵 {song['title']}\n"
        kb.button(text=str(idx), callback_data=f"vkm_download_{idx}")
    kb.adjust(3)
    
    await status_msg.delete()
    await message.answer(response_text, reply_markup=kb.as_markup())
    await state.clear()

@router.callback_query(F.data.startswith("vkm_download_"))
async def download_music(callback: types.CallbackQuery):
    # Musiqa yuklash kodi (Yugoridagi variant bilan bir xil) shu yerda bo'ladi...
    pass

