"""
Mavzuga mos sticker tanlash. Ixtiyoriy funksiya — default holatda O'CHIRILGAN
(config.ENABLE_STICKERS = False), hech narsani buzmaydi.

Yoqish uchun .env fayliga qo'shing:
    ENABLE_STICKERS=true

Va pastdagi STICKERS lug'atiga haqiqiy sticker file_id'laringizni joylang.
file_id olish uchun o'zingizga sticker yuboring va vaqtincha shu handlerni
qo'shib ko'ring:

    @client.on(events.NewMessage(incoming=True))
    async def _debug(event):
        if event.sticker:
            print("file_id:", event.file.id)
"""

import random

from config import ENABLE_STICKERS

# --- PLACEHOLDER: o'zingizning sticker file_id'laringiz bilan almashtiring ---
STICKERS = {
    "salom": [],
    "kulgi": [],
    "rahmat": [],
    "xafa": [],
}
# -----------------------------------------------------------------------

KEYWORDS = {
    "salom": ["salom", "assalomu", "hi", "hello", "hey"],
    "kulgi": ["😂", "🤣", "kulgi", "hazil", "lol", "😄"],
    "rahmat": ["rahmat", "tashakkur", "thanks", "rahmatlar"],
    "xafa": ["xafa", "yomon", "afsus", "😢", "😔", "qiyin"],
}

# Sticker yuborish ehtimoli — har xabarga yubormaslik uchun
STICKER_PROBABILITY = 0.35


def pick_sticker_key(user_message: str, ai_reply: str):
    """Xabar matniga qarab mos sticker kategoriyasini topadi (yoki None)."""
    if not ENABLE_STICKERS:
        return None
    text = f"{user_message} {ai_reply}".lower()
    for key, words in KEYWORDS.items():
        for w in words:
            if w in text:
                return key
    return None


def pick_sticker_id(key: str, last_key: str = None):
    """
    Tanlangan kategoriya bo'yicha sticker ID qaytaradi.
    - Bir xil kategoriyani ketma-ket ikki marta yubormaydi.
    - Har doim emas, tasodifiy ehtimol bilan yuboradi.
    - ENABLE_STICKERS=false yoki ID kiritilmagan bo'lsa hech narsa yubormaydi.
    """
    if not ENABLE_STICKERS or not key or key not in STICKERS or not STICKERS[key]:
        return None, None
    if key == last_key:
        return None, None
    if random.random() > STICKER_PROBABILITY:
        return None, None

    sticker_id = random.choice(STICKERS[key])
    return sticker_id, key
