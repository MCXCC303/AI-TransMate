"""终端渲染：LaTeX 转换 + Rich Live 流式渲染"""

import re
import sys

from pylatexenc.latex2text import LatexNodes2Text
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text


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


def stream_output(console: Console, response, reasoning_file, output_file):
    """流式遍历 API 响应，实时渲染 LaTeX/Markdown。

    返回 (full_response_list, reasoning_parts_list)。
    所有终端输出通过 Rich Live 管理，不直接写 stdout。
    """
    reasoning_parts = []
    full_response = []
    reasoning_active = False
    content_started = False

    with Live(console=console, auto_refresh=False, vertical_overflow="visible", transient=True) as live:
        for chunk in response:
            try:
                if chunk.choices[0].delta.reasoning_content is not None:
                    rc = chunk.choices[0].delta.reasoning_content
                    reasoning_parts.append(rc)
                    reasoning_active = True
                    dots = "." * (len(reasoning_parts) % 6 + 1)
                    live.update(Text(f"Thinking{dots}", style="dim"))
                    live.refresh()
                    with open(reasoning_file, "a") as f:
                        f.write(rc)
            except AttributeError:
                pass

            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response.append(content)
                reasoning_active = False
                content_started = True
                rendered = render_math("".join(full_response))
                live.update(Markdown(rendered))
                live.refresh()
                with open(output_file, "a") as f:
                    f.write(content)

    if content_started:
        console.print(Markdown(render_math("".join(full_response))))

    return full_response, reasoning_parts
