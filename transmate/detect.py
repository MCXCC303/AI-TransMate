"""小模型检测：源语言识别 + 翻译语境分析"""

import re

from .config import _load_prompts, LANG_MAP

_PROMPTS = _load_prompts()

# ── 语言别名映射 ──
_LANG_ALIASES = {}
for name in LANG_MAP:
    _LANG_ALIASES[name.lower()] = name

_EXTRA_ALIASES = {
    "mandarin": "Chinese", "cantonese": "Chinese",
    "zh": "Chinese", "en": "English", "ja": "Japanese",
    "fr": "French", "de": "German", "ko": "Korean",
    "es": "Spanish", "ru": "Russian", "ar": "Arabic",
    "pt": "Portuguese", "it": "Italian", "nl": "Dutch",
    "pl": "Polish", "tr": "Turkish", "vi": "Vietnamese",
    "th": "Thai", "sv": "Swedish", "da": "Danish",
    "fi": "Finnish", "cs": "Czech", "hu": "Hungarian",
    "ro": "Romanian", "uk": "Ukrainian", "el": "Greek",
    "he": "Hebrew", "iw": "Hebrew", "id": "Indonesian",
    "ms": "Malay", "no": "Norwegian", "fa": "Persian",
    "hi": "Hindi", "bn": "Bengali", "pa": "Punjabi",
    "ta": "Tamil", "te": "Telugu", "ur": "Urdu",
    "sw": "Swahili", "cy": "Welsh", "zu": "Zulu",
    "is": "Icelandic", "lv": "Latvian", "lt": "Lithuanian",
    "sr": "Serbian", "sk": "Slovak", "sl": "Slovenian",
    "ca": "Catalan", "et": "Estonian", "bg": "Bulgarian",
    "hr": "Croatian", "af": "Afrikaans",
}
_LANG_ALIASES.update(_EXTRA_ALIASES)


def _normalize_language(raw: str) -> str:
    """Normalize language detection output to match LANG_MAP keys."""
    if not raw or not raw.strip():
        return "Unknown"

    cleaned = re.sub(r"[^\w\s-]", "", raw).strip().lower()
    if not cleaned:
        return "Unknown"

    if cleaned in _LANG_ALIASES:
        return _LANG_ALIASES[cleaned]

    for alias, canonical in _LANG_ALIASES.items():
        if cleaned in alias or alias in cleaned:
            return canonical

    return "Unknown"


# ── 语境别名映射 ──
_VALID_CONTEXTS = frozenset({
    "general", "technical", "medical", "legal", "literary",
    "casual conversation", "academic", "business", "news",
    "scientific", "religious", "slang/dialect",
})

_CONTEXT_ALIASES = {
    "general": "general",
    "technical": "technical", "tech": "technical",
    "medical": "medical",
    "legal": "legal",
    "literary": "literary", "literature": "literary",
    "casual conversation": "casual conversation",
    "casual": "casual conversation",
    "conversation": "casual conversation",
    "academic": "academic",
    "business": "business",
    "news": "news",
    "scientific": "scientific", "science": "scientific",
    "religious": "religious", "religion": "religious",
    "slang/dialect": "slang/dialect",
    "slang": "slang/dialect", "dialect": "slang/dialect",
}


def _normalize_context(raw: str) -> str:
    """Normalize context detection output to a valid label."""
    if not raw or not raw.strip():
        return "general"

    cleaned = re.sub(r"[^\w\s/-]", "", raw).strip().lower()
    if not cleaned:
        return "general"

    return _CONTEXT_ALIASES.get(cleaned, "general")


def _detect_call(client, model: str, prompt: str) -> str:
    """Wrap detection API call, handling reasoning models where content may be None."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.1,
        max_tokens=32,
        extra_body={"thinking": {"type": "disabled"}},
    )
    msg = response.choices[0].message
    content = getattr(msg, "content", None)
    if content:
        return content.strip()
    # reasoning models: answer may be in reasoning_content
    reasoning = getattr(msg, "reasoning_content", None)
    return (reasoning or "").strip()


def detect_source_language(text: str, client, model: str) -> str:
    prompt = _PROMPTS["detect_lang"].format(text=text)
    try:
        result = _detect_call(client, model, prompt)
        return _normalize_language(result)
    except Exception:
        return "Unknown"


def detect_context(text: str, client, model: str) -> str:
    prompt = _PROMPTS["detect_context"].format(text=text)
    try:
        result = _detect_call(client, model, prompt)
        return _normalize_context(result)
    except Exception:
        return "general"
