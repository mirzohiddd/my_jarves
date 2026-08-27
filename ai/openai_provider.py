from typing import List, Dict

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from ai.base import AIProvider


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self) -> None:
        self._client = OpenAI(api_key=OPENAI_API_KEY)

    def get_response(self, history: List[Dict[str, str]], user_message: str) -> str:
        messages = self._build_messages(history, user_message)
        completion = self._client.chat.completions.create(
            model=OPENAI_MODEL,  # .env dagi OPENAI_MODEL orqali beriladi, kodga qattiq yozilmagan
            messages=messages,
            temperature=0.6,
            max_tokens=400,
        )
        return completion.choices[0].message.content.strip()
