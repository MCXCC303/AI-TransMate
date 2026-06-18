"""提示词构建：构建首条 system 消息"""

from .config import _load_prompts

_PROMPTS = _load_prompts()
TRANSLATION_ROLE = _PROMPTS["translator_role"]

_INSTRUCTION_TEMPLATE = "Translate the following text to {target_lang}."
_DOMAIN_TEMPLATE = "Domain: {context}."
_LANGUAGE_TEMPLATE = "Source language: {source_lang}."

def build_system_message(
		target_lang: str,
		source_lang: str = "",
		context: str = "",
) -> str:
	"""构建首条 system 消息，会话后续轮次复用此消息作为缓存前缀锚点。"""
	parts = [TRANSLATION_ROLE, _INSTRUCTION_TEMPLATE.format(target_lang=target_lang)]
	if context and context != "general":
		parts.append(_DOMAIN_TEMPLATE.format(context=context))
	if source_lang:
		parts.append(_LANGUAGE_TEMPLATE.format(source_lang=source_lang))
	return "\n\n".join(parts)
