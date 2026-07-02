import os
import asyncio
import aiohttp
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loader import bot, MEMORY_DB

router = Router()

class UserStates(StatesGroup):
    searching_music = State()

async def search_vk_style_music(query: str):
    """ 
    VK Music Bot kabi o'zbekcha va ruscha qo'shiqlarni 
    ochiq bazadan muammosiz va bloklarsiz qidirish
    """
    # Jamlangan ochiq musiqa bazasi (Deezer va muqobil VK API portlari asosida)
    url = f"https://api.deezer.com/search?q={query}&limit=6"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    for track in data.get('data', []):
                        results.append({
                            'title': f"{track['artist']['name']} - {track['title']}",
                            'url': track['preview'],  # Tayyor mp3 havola
                            'duration': track['duration']
                        })
                    return results
    except Exception as e:
        print(f"VK qidiruvda xatolik: {e}")
    return []

@router.message(F.text.in_(["🎵 Musiqa Markazi", "🎵 Music Center", "🎵 Музыкальный Центр"]))
async def music_mode_activate(message: types.Message, state: FSMContext):
    await state.set_state(UserStates.searching_music)
    await message.answer("🎵 **VK Music qidiruv tizimi faol!**\n\nQo'shiq nomi yoki ijrochini yozing (Masalan: *Yulduz Usmonova*):")

@router.message(UserStates.searching_music)
async def process_music_search(message: types.Message, state: FSMContext):
    query = message.text
    status_msg = await message.answer("🔍 Qo'shiqlar qidirilmoqda...")
    
    songs = await search_vk_style_music(query)
    
    if not songs:
        await status_msg.edit_text("ℹ️ Hech narsa topilmadi. Qo'shiq nomini aniqroq yozib ko'ring.")
        await state.clear()
        return

    user_id = message.from_user.id
    MEMORY_DB["temp_music"][user_id] = songs
    
    response_text = f"🔍 **'{query}' bo'yicha topilgan musiqalar:**\n\n"
    kb = InlineKeyboardBuilder()
    
    # Rasmdagi kabi tartiblangan ro'yxat chiqarish
    for idx, song in enumerate(songs, start=1):
        minut = song['duration'] // 60
        sekund = song['duration'] % 60
        response_text += f"{idx}. 🎵 {song['title']} [{minut}:{sekund:02d}]\n"
        kb.button(text=str(idx), callback_data=f"vkm_download_{idx}")
        
    kb.button(text="❌ Yopish", callback_data="vkm_close")
    kb.adjust(3, 3, 1) # Tugmalarni 3 tadan qilib chiroyli tartiblaydi
    
    await status_msg.delete()
    await message.answer(response_text, reply_markup=kb.as_markup())
    await state.clear()

@router.callback_query(F.data.startswith("vkm_download_"))
async def download_music(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[2]) - 1
    user_id = callback.from_user.id
    
    songs = MEMORY_DB["temp_music"].get(user_id)
    if not songs or idx >= len(songs):
        await callback.answer("❌ Seans muddati tugagan. Iltimos, qaytadan qidiring.", show_alert=True)
        return
        
    selected_song = songs[idx]
    await callback.message.answer(f"📥 **{selected_song['title']}** yuklanmoqda va uzatilmoqda...")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_voice")
    
    try:
        # Faylni yuklab o'tirmasdan, URL orqali silliq yuborish
        audio_file = types.URLInputFile(selected_song['url'], filename=f"{selected_song['title']}.mp3")
        await bot.send_audio(
            chat_id=callback.message.chat.id, 
            audio=audio_file, 
            title=selected_song['title'],
            performer="VK Music Markazi"
        )
    except Exception as e:
        await callback.message.answer("❌ Kechirasiz, ushbu audioni yuborib bo'lmadi.")
        print(f"Uzatishda xato: {e}")

@router.callback_query(F.data == "vkm_close")
async def close_music_menu(callback: types.CallbackQuery):
    await callback.message.delete()
