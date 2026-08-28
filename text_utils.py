"""
Telegram xabarlarini formatlash va limitiga qarab bo'laklarga bo'lish.
"""

TELEGRAM_MAX_LEN = 4096


def format_for_telegram(text: str) -> str:
    """
    - ortiqcha bo'sh qatorlarni tozalaydi (2 tadan ortiq bo'sh qator bo'lmaydi)
    - qator oxiridagi keraksiz bo'shliqlarni olib tashlaydi
    - matn boshi/oxiridagi bo'shliqni tozalaydi
    Telegram Markdown/HTML teglariga tegmaydi — faqat bo'sh qatorlarni tartiblaydi.
    """
    if not text:
        return text

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]

    cleaned = []
    empty_streak = 0
    for line in lines:
        if line.strip() == "":
            empty_streak += 1
            if empty_streak > 1:
                continue
        else:
            empty_streak = 0
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def split_long_message(text: str, limit: int = TELEGRAM_MAX_LEN) -> list:
    """
    Xabarni Telegram limitiga (default 4096) qarab bo'laklarga bo'ladi.
    Kesish nuqtasini tanlashda ustuvorlik: paragraf -> gap -> bo'shliq.
    Shu bilan so'z yoki gap o'rtasidan kesilmasligiga harakat qilinadi.
    """
    if not text:
        return [text] if text else []

    if len(text) <= limit:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > limit:
        window = remaining[:limit]
        split_at = _find_safe_split(window)
        if split_at <= 0:
            split_at = limit

        chunk = remaining[:split_at].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].lstrip("\n")

    if remaining:
        chunks.append(remaining)

    return chunks


def _find_safe_split(window: str) -> int:
    for sep in ("\n\n", "\n", ". ", "! ", "? ", " "):
        idx = window.rfind(sep)
        if idx > 0:
            return idx + len(sep)
    return len(window)
