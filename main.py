import asyncio
import logging
from collections import defaultdict

from telethon import TelegramClient, events
from telethon.tl.types import User

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SESSION_NAME,
    MAX_HISTORY_MESSAGES,
    AI_PROVIDER,
    MESSAGE_DEBOUNCE_SECONDS,
)
from storage import (
    upsert_user,
    append_message,
    get_recent_history,
    is_introduced,
    mark_introduced,
    get_chat_state,
    set_chat_state,
    get_last_sticker,
    set_last_sticker,
    AI_ACTIVE,
    HUMAN_ACTIVE,
)
from ai.manager import get_ai_response
from ai.base import OWNER_NAME
from text_utils import format_for_telegram, split_long_message
from stickers import pick_sticker_key, pick_sticker_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ai_assistant")

# chat_id -> hozircha yig'ilayotgan (javob berilmagan) xabarlar
_pending_messages = defaultdict(list)
# chat_id -> debounce task (kutish tugagach javob yozadigan task)
_pending_tasks = {}

# Python 3.14'da faol event loop bo'lmasa asyncio.get_event_loop() xato beradi
# (eski Python'larda avtomatik loop yaratardi). Telethon klienti yaratilishidan
# oldin loop'ni qo'lda yaratib, joriy loop sifatida belgilab qo'yamiz.
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

client = TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH, loop=loop)


def get_display_name(sender: User) -> str:
    """Telegram profilidan ism (va bo'lsa familiya) oladi."""
    name = (sender.first_name or "").strip()
    if sender.last_name:
        name = f"{name} {sender.last_name}".strip()
    return name


def build_intro_message(name: str) -> str:
    """
    Yangi odam bilan birinchi suhbatda yuboriladigan tanishtiruv xabari.
    Bu matn AI orqali emas, to'g'ridan-to'g'ri yuboriladi — shu bilan har
    doim barqaror va tabiiy bo'lishi kafolatlanadi. Faqat shu bir marta
    ishlatiladi, keyingi xabarlar AI orqali (JARVIS_SYSTEM_PROMPT qoidalariga
    mos) davom etadi va bu tanishtiruvni takrorlamaydi.
    """
    if name:
        return (
            f"Assalomu alaykum, {name}! 👋\n\n"
            f"Men {OWNER_NAME}ning JARVIS AI yordamchisiman. U hozir sizga shaxsan "
            "javob bera olmayapti, shu payt men yordam beraman 😊\n"
            "Nima kerak, bemalol yozavering!"
        )
    return (
        "Assalomu alaykum! 👋\n\n"
        f"Men {OWNER_NAME}ning JARVIS AI yordamchisiman. U hozir shaxsan javob "
        "bera olmayapti, shu payt men yordam beraman 😊"
    )


@client.on(events.NewMessage(outgoing=True))
async def handle_outgoing_message(event):
    """
    Mirzohid AYNAN shu chatga o'zi xabar yozsa — faqat shu bitta chat
    uchun JARVIS darhol to'xtaydi va HUMAN_ACTIVE holatiga o'tadi.
    Boshqa chatlarga bu hech qanday ta'sir qilmaydi (har chat mustaqil).
    Online/offline statusga bog'liq emas — faqat aynan shu chatga
    Mirzohidning o'zi yozganini tekshiradi.
    """
    if not event.is_private:
        return

    chat_id = str(event.chat_id)
    await set_chat_state(chat_id, HUMAN_ACTIVE)

    # Shu chat uchun javob kutib turgan (debounce) task bo'lsa — bekor qilamiz,
    # chunki Mirzohid o'zi javob berdi.
    task = _pending_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()
    _pending_messages.pop(chat_id, None)

    logger.info(f"Mirzohid shaxsan yozdi -> HUMAN_ACTIVE: chat_id={chat_id}")


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

    # Shu CHAT uchun holatni tekshiramiz (global online/offline emas!)
    if get_chat_state(chat_id) == HUMAN_ACTIVE:
        logger.info(f"HUMAN_ACTIVE, JARVIS javob bermaydi: chat_id={chat_id}")
        return

    logger.info(f"Yangi xabar: chat_id={chat_id} matn={user_message!r}")

    # 1) Foydalanuvchi va xabar ma'lumotlarini saqlash
    await upsert_user(chat_id, sender)
    await append_message(chat_id, "user", user_message)

    # 2) Ketma-ket kelayotgan xabarlarni yig'ib, bir necha soniya kutamiz —
    #    odam bir nechta xabar yuborsa, ularni yig'ib bitta javob beramiz.
    _pending_messages[chat_id].append(user_message)

    prev_task = _pending_tasks.get(chat_id)
    if prev_task and not prev_task.done():
        prev_task.cancel()

    _pending_tasks[chat_id] = asyncio.ensure_future(
        _process_after_debounce(event, chat_id, sender)
    )


async def _process_after_debounce(event, chat_id: str, sender: User):
    try:
        await asyncio.sleep(MESSAGE_DEBOUNCE_SECONDS)
    except asyncio.CancelledError:
        # Yangi xabar keldi yoki Mirzohid o'zi yozdi — bu task bekor qilindi
        return

    # Kutish tugagach, shu orada Mirzohid o'zi yozib qo'ymaganini tekshiramiz
    if get_chat_state(chat_id) == HUMAN_ACTIVE:
        _pending_messages.pop(chat_id, None)
        return

    messages = _pending_messages.pop(chat_id, [])
    if not messages:
        return
    combined_message = "\n".join(messages)

    # 2.1) Bu odam bilan JARVIS ilk marta gaplashayotgan bo'lsa — avval
    # tanishtiruv xabarini (ismi bilan) yuboradi va introduced=true qilib
    # belgilaydi. Bu faqat BIR MARTA sodir bo'ladi.
    if not is_introduced(chat_id):
        name = get_display_name(sender)
        intro = format_for_telegram(build_intro_message(name))
        await event.reply(intro)
        await append_message(chat_id, "assistant", intro)
        await mark_introduced(chat_id)
        logger.info(f"Tanishtiruv xabari yuborildi: chat_id={chat_id}")
        return

    # 3) Kontekst uchun so'nggi xabarlarni olish
    history = get_recent_history(chat_id, MAX_HISTORY_MESSAGES)

    # 4) Tanlangan AI provayderdan (Groq yoki OpenAI) javob olish
    try:
        async with client.action(event.chat_id, "typing"):
            ai_reply = await asyncio.to_thread(get_ai_response, history, combined_message)
    except Exception:
        logger.exception(f"AI provayder ({AI_PROVIDER}) xatosi")
        ai_reply = (
            "Hozir javob berishda texnik muammo yuz berdi. "
            "Iltimos, birozdan so'ng qayta yozing."
        )

    # 5) Javobni formatlab, kerak bo'lsa Telegram limitiga qarab bo'lib yuborish
    ai_reply = format_for_telegram(ai_reply)
    chunks = split_long_message(ai_reply)

    for chunk in chunks:
        await event.reply(chunk)

    await append_message(chat_id, "assistant", ai_reply)

    # 6) Vaziyatga mos bo'lsa, tabiiy tarzda (va kamdan-kam) sticker yuborish
    #    (default o'chirilgan — config.ENABLE_STICKERS orqali yoqiladi)
    try:
        key = pick_sticker_key(combined_message, ai_reply)
        last_key = get_last_sticker(chat_id)
        sticker_id, used_key = pick_sticker_id(key, last_key)
        if sticker_id:
            await client.send_file(event.chat_id, sticker_id)
            await set_last_sticker(chat_id, used_key)
    except Exception:
        logger.exception(f"Sticker yuborishda xato: chat_id={chat_id}")

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