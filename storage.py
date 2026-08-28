import json
import os
import asyncio
from datetime import datetime
from typing import Any, Dict, List

from config import DATA_DIR, USERS_FILE, CONVERSATIONS_FILE

# Bir vaqtda bir nechta yozuv operatsiyasi fayllarni buzib qo'ymasligi uchun lock
_write_lock = asyncio.Lock()

# --- Per-chat holat qiymatlari ---
# AI_ACTIVE  -> JARVIS shu chatda javob berishda davom etadi
# HUMAN_ACTIVE -> Mirzohid shu chatga o'zi yozgan, JARVIS aralashmaydi
AI_ACTIVE = "AI_ACTIVE"
HUMAN_ACTIVE = "HUMAN_ACTIVE"


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path: str, default: Any) -> Any:
    _ensure_data_dir()
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: str, data: Any) -> None:
    _ensure_data_dir()
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def load_users() -> Dict[str, Any]:
    return _load_json(USERS_FILE, {})


def load_conversations() -> Dict[str, Any]:
    return _load_json(CONVERSATIONS_FILE, {})


async def upsert_user(chat_id: str, sender) -> None:
    """Foydalanuvchi ma'lumotini users.json ga yozadi/yangilaydi."""
    async with _write_lock:
        users = load_users()
        now = datetime.now().isoformat()
        user = users.get(chat_id, {})
        user.update(
            {
                "chat_id": chat_id,
                "username": getattr(sender, "username", None),
                "first_name": getattr(sender, "first_name", None),
                "last_name": getattr(sender, "last_name", None),
                "last_message_at": now,
            }
        )
        user.setdefault("first_seen_at", now)
        # JARVIS bu foydalanuvchi bilan avval tanishtirilganmi — yo'q bo'lsa False
        user.setdefault("introduced", False)
        # Shu chat uchun holat: AI_ACTIVE yoki HUMAN_ACTIVE — yo'q bo'lsa default AI_ACTIVE
        user.setdefault("state", AI_ACTIVE)
        users[chat_id] = user
        _save_json(USERS_FILE, users)


def is_introduced(chat_id: str) -> bool:
    """JARVIS shu foydalanuvchi bilan avval o'zini tanishtirganmi, shuni tekshiradi."""
    users = load_users()
    return bool(users.get(chat_id, {}).get("introduced", False))


async def mark_introduced(chat_id: str) -> None:
    """Foydalanuvchini 'introduced=true' deb belgilaydi (qayta tanishtirmaslik uchun)."""
    async with _write_lock:
        users = load_users()
        user = users.get(chat_id, {})
        user["introduced"] = True
        users[chat_id] = user
        _save_json(USERS_FILE, users)


def get_chat_state(chat_id: str) -> str:
    """
    Shu CHAT uchun joriy holatni qaytaradi (AI_ACTIVE yoki HUMAN_ACTIVE).
    Default: AI_ACTIVE. Bu Telegram online/offline statusiga bog'liq emas —
    faqat Mirzohidning aynan shu chatga o'zi yozgan-yozmaganini bildiradi.
    """
    users = load_users()
    return users.get(chat_id, {}).get("state", AI_ACTIVE)


async def set_chat_state(chat_id: str, state: str) -> None:
    """Shu chat uchun holatni yozadi: AI_ACTIVE yoki HUMAN_ACTIVE."""
    async with _write_lock:
        users = load_users()
        user = users.get(chat_id, {})
        user["state"] = state
        user["state_updated_at"] = datetime.now().isoformat()
        users[chat_id] = user
        _save_json(USERS_FILE, users)


def get_last_sticker(chat_id: str):
    """Shu chatda oxirgi yuborilgan sticker kategoriyasini qaytaradi (takrorlamaslik uchun)."""
    users = load_users()
    return users.get(chat_id, {}).get("last_sticker")


async def set_last_sticker(chat_id: str, sticker_key: str) -> None:
    async with _write_lock:
        users = load_users()
        user = users.get(chat_id, {})
        user["last_sticker"] = sticker_key
        users[chat_id] = user
        _save_json(USERS_FILE, users)


async def append_message(chat_id: str, role: str, text: str) -> None:
    """Xabarni conversations.json ga qo'shadi (role: 'user' yoki 'assistant')."""
    async with _write_lock:
        conversations = load_conversations()
        history: List[Dict[str, str]] = conversations.get(chat_id, [])
        history.append(
            {
                "role": role,
                "text": text,
                "timestamp": datetime.now().isoformat(),
            }
        )
        conversations[chat_id] = history
        _save_json(CONVERSATIONS_FILE, conversations)


def get_recent_history(chat_id: str, limit: int) -> List[Dict[str, str]]:
    """So'nggi `limit` ta xabarni qaytaradi (AI kontekst uchun)."""
    conversations = load_conversations()
    history = conversations.get(chat_id, [])
    return history[-limit:]