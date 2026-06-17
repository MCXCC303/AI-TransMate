"""翻译编排：检测 → 提示词 → 流式 → 历史存储"""

import datetime
import sys

import openai
from rich.console import Console

from .ansi_chars import TerminalColor
from .config import get_history_dir
from .detect import detect_source_language, detect_context
from .output import stream_output
from .prompt_builder import build_messages


def translate(text: str, config: dict, history_id: str):
    """执行翻译，返回 (detected_source_lang, detected_context)。"""
    api_key = config.get("api_key")
    base_url = config.get("base_url", "https://api.deepseek.com/v1")
    main_model = config.get("main_model", "deepseek-chat")
    fast_model = config.get("fast_model", main_model)
    target_lang = config.get("target_lang", "Chinese")
    source_lang_specified = config.get("source_lang_specified", False)
    source_lang = config.get("source_lang") if source_lang_specified else None
    context_optimization = config.get("context_optimization", True)

    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    # ── 小模型检测 ──
    detected_lang = source_lang
    detected_context = "general"

    if not source_lang_specified:
        sys.stdout.write(
            f"{TerminalColor.GRAY.value}Detecting source language...{TerminalColor.RESET.value}\r"
        )
        sys.stdout.flush()
        detected_lang = detect_source_language(text, client, fast_model)
        sys.stdout.write(f"{TerminalColor.CLEAR_LINE.value}\r")
        sys.stdout.flush()

    sys.stdout.write(
        f"{TerminalColor.GRAY.value}Analyzing context...{TerminalColor.RESET.value}\r"
    )
    sys.stdout.flush()
    detected_context = detect_context(text, client, fast_model)
    sys.stdout.write(f"{TerminalColor.CLEAR_LINE.value}\r")
    sys.stdout.flush()

    # ── 构建提示词 ──
    messages = build_messages(
        target_lang=target_lang,
        source_lang=detected_lang or "",
        context=detected_context,
        user_text=text,
        context_optimization=context_optimization,
    )

    # ── 历史文件 ──
    history_dir = get_history_dir()
    history_dir.mkdir(parents=True, exist_ok=True)
    output_file = history_dir / f"{history_id}_output.md"
    reasoning_file = history_dir / f"{history_id}_reasoning.md"
    timestamp = datetime.datetime.now().strftime("%Y.%m.%d, %H:%M")

    with open(output_file, "a") as f:
        f.write(f"\n\n---\n\n`{timestamp}`\n> Input:\n\n{text}\n\n> Output:\n\n")
    with open(reasoning_file, "a") as f:
        f.write(f"\n\n---\n\n`{timestamp}`\n> Input:\n\n{text}\n\n> Reasoning:\n\n")

    # ── 流式调用 ──
    response = client.chat.completions.create(
        model=main_model, stream=True, messages=messages
    )

    console = Console()
    full_response, reasoning_parts = stream_output(
        console, response, reasoning_file, output_file
    )

    # ── 完成 ──
    if not full_response:
        sys.stdout.write(
            f"{TerminalColor.GRAY_ITALIC.value}Service busy. Try again later.{TerminalColor.RESET.value}\n"
        )
        with open(output_file, "a") as f:
            f.write("Service busy. Try again later.\n")

    if not reasoning_parts and full_response:
        with open(reasoning_file, "a") as f:
            f.write("(Model does not support reasoning or thinking is off.)\n")

    return detected_lang, detected_context
