"""小模型检测：源语言识别 + 翻译语境分析"""

from .config import _load_contents

_PROMPTS = _load_contents("prompts.json")


def detect_source_language(text: str, client, model: str) -> str:
    prompt = _PROMPTS["detect_lang"].format(text=text)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=32,
        )
        result = response.choices[0].message.content.strip()
        return result
    except Exception:
        return "Unknown"


def detect_context(text: str, client, model: str) -> str:
    prompt = _PROMPTS["detect_context"].format(text=text)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=32,
        )
        result = response.choices[0].message.content.strip()
        return result
    except Exception:
        return "general"
