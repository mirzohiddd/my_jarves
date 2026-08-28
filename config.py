import os
from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, required: bool = True, default=None):
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"'{name}' aniqlanmagan. .env faylini tekshiring.")
    return value


# --- Telegram ---
TELEGRAM_API_ID = int(_get_env("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = _get_env("TELEGRAM_API_HASH")
TELEGRAM_PHONE = _get_env("TELEGRAM_PHONE")
TELEGRAM_SESSION_NAME = _get_env(
    "TELEGRAM_SESSION_NAME", required=False, default="assistant_session"
)

# --- AI provayder tanlovi: "groq" yoki "openai" ---
AI_PROVIDER = _get_env("AI_PROVIDER", required=False, default="groq").strip().lower()

# --- Groq (faqat AI_PROVIDER=groq bo'lsa majburiy) ---
GROQ_API_KEY = _get_env("GROQ_API_KEY", required=(AI_PROVIDER == "groq"))
GROQ_MODEL = _get_env("GROQ_MODEL", required=False, default="openai/gpt-oss-120b")

# --- OpenAI (faqat AI_PROVIDER=openai bo'lsa majburiy) ---
OPENAI_API_KEY = _get_env("OPENAI_API_KEY", required=(AI_PROVIDER == "openai"))
OPENAI_MODEL = _get_env("OPENAI_MODEL", required=(AI_PROVIDER == "openai"), default=None)

# --- Yordamchi sozlamalari ---
OWNER_NAME = _get_env("OWNER_NAME", required=False, default="egasi")
TIMEZONE = _get_env("TIMEZONE", required=False, default="Asia/Tashkent")

# --- Ma'lumotlar ---
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
CONVERSATIONS_FILE = os.path.join(DATA_DIR, "conversations.json")

# --- Suhbat konteksti chuqurligi ---
MAX_HISTORY_MESSAGES = int(_get_env("MAX_HISTORY_MESSAGES", required=False, default="10"))

# --- Ketma-ket kelayotgan xabarlarni yig'ib, bittalab javob berish uchun kutish vaqti (sekund) ---
MESSAGE_DEBOUNCE_SECONDS = float(
    _get_env("MESSAGE_DEBOUNCE_SECONDS", required=False, default="3")
)

# --- Sticker yuborishni yoqish/o'chirish (default: o'chirilgan) ---
ENABLE_STICKERS = (
    _get_env("ENABLE_STICKERS", required=False, default="false").strip().lower() == "true"
)