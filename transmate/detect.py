"""小模型检测：源语言识别 + 翻译语境分析"""

import re

from .config import _load_prompts, LANG_MAP
from .providers.base import BaseProvider

_PROMPTS = _load_prompts()

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

_TERM_TYPE_ALIASES = {
	"sentence": "sentence", "sent": "sentence", "text": "sentence",
	"phrase": "phrase", "expression": "phrase", "collocation": "phrase",
	"abbreviation": "abbreviation", "abbr": "abbreviation", "acronym": "abbreviation",
	"initialism": "abbreviation",
	"technical_term": "technical_term", "technical term": "technical_term",
	"tech_term": "technical_term", "scientific_term": "technical_term",
	"chemical": "technical_term",
}

def _normalize_term_type(raw: str) -> str:
	"""Normalize term type detection output to a valid label."""
	if not raw or not raw.strip():
		return "sentence"

	cleaned = re.sub(r"[^\w\s/-]", "", raw).strip().lower()
	if not cleaned:
		return "sentence"

	return _TERM_TYPE_ALIASES.get(cleaned, "sentence")

def _detect_call(client, provider: BaseProvider, model: str, prompt: str) -> str:
	"""通过 provider 封装检测调用，自动处理各提供商的格式差异。"""
	kwargs = provider.get_detect_kwargs(prompt, model)
	kwargs.pop("messages")  # 由 builder 传入
	response = client.chat.completions.create(
		model=model,
		messages=[{"role": "system", "content": prompt}],
		**{k: v for k, v in kwargs.items() if k not in ("model", "messages")},
	)
	content, reasoning = provider.parse_response(response)
	if content:
		return content.strip()
	return (reasoning or "").strip()

def detect_source_language(text: str, client, provider: BaseProvider, model: str) -> str:
	prompt = _PROMPTS["detect_lang"].format(text=text)
	try:
		result = _detect_call(client, provider, model, prompt)
		return _normalize_language(result)
	except Exception:
		return "Unknown"

def detect_context(text: str, client, provider: BaseProvider, model: str) -> tuple[str, str]:
	"""检测文本领域和输入类型。返回 (context, term_type)。"""
	prompt = _PROMPTS["detect_context"].format(text=text)
	try:
		result = _detect_call(client, provider, model, prompt)
		lines = [ln.strip() for ln in result.strip().split("\n") if ln.strip()]
		if len(lines) >= 2:
			return _normalize_context(lines[0]), _normalize_term_type(lines[1])
		if lines:
			return _normalize_context(lines[0]), "sentence"
		return "general", "sentence"
	except Exception:
		return "general", "sentence"
