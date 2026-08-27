import asyncio
import logging

from telethon import TelegramClient, events
from telethon.tl.types import User

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SESSION_NAME,
    MAX_HISTORY_MESSAGES,
    AI_PROVIDER,
)
from storage import (
    upsert_user,
    append_message,
    get_recent_history,
    is_introduced,
    mark_introduced,
)
from ai.manager import get_ai_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ai_assistant")

# Yangi odam bilan birinchi suhbatda JARVIS o'zini shu xabar bilan tanishtiradi.
# Bu matn AI orqali emas, to'g'ridan-to'g'ri yuboriladi — shu bilan har doim bir xil
# va barqaror bo'lishi kafolatlanadi.
INTRO_MESSAGE = (
    "Assalomu alaykum 👋\n"
    "Men Mirzohid tomonidan yaratilgan JARVIS AI Agentman 🤖\n"
    "Hozir Mirzohid Telegramda emaslar, shuning uchun siz bilan vaqtincha men suhbatlashaman."
)

# Python 3.14'da faol event loop bo'lmasa asyncio.get_event_loop() xato beradi
# (eski Python'larda avtomatik loop yaratardi). Telethon klienti yaratilishidan
# oldin loop'ni qo'lda yaratib, joriy loop sifatida belgilab qo'yamiz.
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

client = TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH, loop=loop)


@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):
    # Faqat shaxsiy (1:1) xabarlar bilan ishlaymiz — guruh/kanal e'tiborsiz qoldiriladi
    if not event.is_private:
        return

    sender = await event.get_sender()

    # Botlardan kelgan xabarlarni e'tiborsiz qoldiramiz
    if not isinstance(sender, User) or sender.bot:
        return

    if not event.raw_text or not event.raw_text.strip():
        return

    chat_id = str(event.chat_id)
    user_message = event.raw_text.strip()

    logger.info(f"Yangi xabar: chat_id={chat_id} matn={user_message!r}")

    # 1) Foydalanuvchi va xabar ma'lumotlarini saqlash
    await upsert_user(chat_id, sender)
    await append_message(chat_id, "user", user_message)

    # 1.1) Bu odam bilan JARVIS ilk marta gaplashayotgan bo'lsa — avval tanishtiruv
    # xabarini yuboradi va introduced=true qilib belgilaydi. Bu faqat BIR MARTA sodir
    # bo'ladi; keyingi barcha xabarlarda to'g'ridan-to'g'ri AI javobi yuboriladi.
    if not is_introduced(chat_id):
        await event.reply(INTRO_MESSAGE)
        await append_message(chat_id, "assistant", INTRO_MESSAGE)
        await mark_introduced(chat_id)
        logger.info(f"Tanishtiruv xabari yuborildi: chat_id={chat_id}")
        return

    # 2) Kontekst uchun so'nggi xabarlarni olish
    history = get_recent_history(chat_id, MAX_HISTORY_MESSAGES)

    # 3) Tanlangan AI provayderdan (Groq yoki OpenAI) javob olish
    try:
        async with client.action(event.chat_id, "typing"):
            ai_reply = await asyncio.to_thread(get_ai_response, history, user_message)
    except Exception:
        logger.exception(f"AI provayder ({AI_PROVIDER}) xatosi")
        ai_reply = (
            "Hozir javob berishda texnik muammo yuz berdi. "
            "Iltimos, birozdan so'ng qayta yozing."
        )

    # 4) Javobni Telegramga yuborish
    await event.reply(ai_reply)
    await append_message(chat_id, "assistant", ai_reply)

    logger.info(f"Javob yuborildi: chat_id={chat_id}")


async def main():
    await client.start(phone=TELEGRAM_PHONE)
    me = await client.get_me()
    logger.info(f"Ulandi: {me.first_name} (@{me.username})")
    logger.info(f"AI provayder: {AI_PROVIDER}")
    logger.info("AI Assistant ishga tushdi. Xabarlar kutilmoqda...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    loop.run_until_complete(main())
