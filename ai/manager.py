from typing import List, Dict, Optional

from config import AI_PROVIDER
from ai.base import AIProvider
from ai.groq_provider import GroqProvider
from ai.openai_provider import OpenAIProvider

# Yangi provayder qo'shish uchun: 1) ai/<nomi>_provider.py yozing (AIProvider'dan meros),
# 2) shu ro'yxatga qo'shing. Boshqa hech narsani o'zgartirish shart emas.
_PROVIDERS = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
}

_provider_instance: Optional[AIProvider] = None


def get_provider() -> AIProvider:
    """AI_PROVIDER (.env) sozlamasiga qarab tanlangan provayder instansini qaytaradi (singleton)."""
    global _provider_instance
    if _provider_instance is None:
        provider_cls = _PROVIDERS.get(AI_PROVIDER)
        if provider_cls is None:
            available = ", ".join(_PROVIDERS.keys())
            raise RuntimeError(
                f"Noto'g'ri AI_PROVIDER='{AI_PROVIDER}'. Mavjud variantlar: {available}"
            )
        _provider_instance = provider_cls()
    return _provider_instance


def get_ai_response(history: List[Dict[str, str]], user_message: str) -> str:
    """Tanlangan provayderdan (Groq yoki OpenAI) AI javobini oladi."""
    provider = get_provider()
    return provider.get_response(history, user_message)
