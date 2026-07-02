from aiogram import Router
from . import menu, ai, music, kino

def get_handlers_router() -> Router:
    master_router = Router()
    master_router.include_routers(
        menu.router,
        kino.router,
        music.router,
        ai.router      # Eng oxirida turishi shart, chunki hamma matnni ushlaydi
    )
    return master_router

