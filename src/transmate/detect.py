"""小模型检测：源语言识别 + 翻译语境分析"""


def detect_source_language(text: str, client, model: str) -> str:
    prompt = (
        "Identify the language of the following text. "
        "Reply with ONLY the language name in English (e.g., 'Chinese', 'English', 'Japanese', 'French', 'German', 'Korean', 'Spanish', 'Russian', 'Arabic', etc.). "
        "Nothing else.\n\n"
        f"Text: {text}"
    )
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
    prompt = (
        "Analyze the domain, register, and context of the following text. "
        "Reply with ONLY a short descriptive label (choose one: 'general', 'technical', 'medical', 'legal', 'literary', 'casual conversation', 'academic', 'business', 'news', 'scientific', 'religious', 'slang/dialect'). "
        "Nothing else.\n\n"
        f"Text: {text}"
    )
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
