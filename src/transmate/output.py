"""终端渲染：LaTeX 转换 + Rich Markdown 输出"""

import re
import sys

from pylatexenc.latex2text import LatexNodes2Text
from rich.console import Console
from rich.markdown import Markdown


def render_math(text: str) -> str:
    """将 Markdown 中的 LaTeX 公式转为终端可读纯文本。"""
    patterns = [
        (r'(?<!\\)\$\$((?:\\\$|[^$])+?)(?<!\\)\$\$', True),
        (r'(?<!\\)\$((?:\\\$|[^$])+?)(?<!\\)\$', False),
        (r'\\\[(.+?)\\\]', True),
        (r'\\\((.+?)\\\)', False),
    ]

    def convert(match):
        return LatexNodes2Text().latex_to_text(match.group(1))

    for pattern, is_display in patterns:
        flags = re.DOTALL if is_display else 0
        if is_display:
            text = re.sub(pattern, lambda m: "\n" + convert(m) + "\n", text, flags=flags)
        else:
            text = re.sub(pattern, convert, text, flags=flags)

    return text


def print_output(text: str):
    """用 Rich Markdown 渲染并输出翻译结果。"""
    console = Console()
    console.print(Markdown(render_math(text)))


def write_reasoning_chunk(text: str):
    """写入推理块（显示 Thinking 动画）。"""
    dots = "." * (len(text) % 6 + 1)
    sys.stdout.write(f"\r\x1b[90mThinking{dots}\x1b[0m")
    sys.stdout.flush()


def finish_thinking():
    """清除 Thinking 行。"""
    sys.stdout.write("\r\x1b[2K\r")
    sys.stdout.flush()
