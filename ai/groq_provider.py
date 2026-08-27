from typing import List, Dict

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL
from ai.base import AIProvider


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self) -> None:
        self._client = Groq(api_key=GROQ_API_KEY)

    def get_response(self, history: List[Dict[str, str]], user_message: str) -> str:
        messages = self._build_messages(history, user_message)
        completion = self._client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=400,
        )
        return completion.choices[0].message.content.strip()
