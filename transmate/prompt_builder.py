"""提示词构建：按缓存优化顺序构建 messages 列表"""

from .config import _load_contents

_PROMPTS = _load_contents("prompts.json")
TRANSLATION_ROLE = _PROMPTS["translator_role"]


def build_messages(
    target_lang: str,
    source_lang: str = "",
    context: str = "",
    user_text: str = "",
    context_optimization: bool = True,
):
    """构建按缓存优化顺序排列的消息列表。

    顺序: 1) 翻译角色+目标语言(静态) → 2) 语境风格(半静态) → 3) 源语言(动态) → 4) 用户文本
    在目标语言不变时，消息1完全可被缓存。
    """
    messages = []

    if context_optimization:
        # Message 1: 角色 + 目标语言（最静态，缓存命中率最高）
        role_msg = TRANSLATION_ROLE + f"\n\nTranslate the following text to {target_lang}."
        messages.append({"role": "system", "content": role_msg})

        # Message 2: 语境/风格信息（半静态）
        context_parts = ["Translation context:"]
        if context and context != "general":
            context_parts.append(f"The source text belongs to the domain of: {context}.")
        if source_lang:
            context_parts.append(f"The source language is: {source_lang}.")
        if len(context_parts) > 1:
            messages.append({"role": "system", "content": " ".join(context_parts)})

        # Message 3: 用户文本
        messages.append({"role": "user", "content": user_text})
    else:
        # 非优化模式：所有信息合并到一条 system message
        parts = [TRANSLATION_ROLE, f"Translate the following text to {target_lang}."]
        if source_lang:
            parts.append(f"The source language is: {source_lang}.")
        if context and context != "general":
            parts.append(f"The source text domain is: {context}.")
        system_content = "\n\n".join(parts)
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_text},
        ]

    return messages
