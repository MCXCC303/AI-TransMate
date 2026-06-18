"""终端渲染：LaTeX 转换 + Rich 渲染"""

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

def _parse_usage(u) -> dict:
	"""Extract token usage across multiple API response formats."""
	details = getattr(u, "prompt_tokens_details", None)
	hit = getattr(u, "prompt_cache_hit_tokens",
	              getattr(details, "cached_tokens", 0) or 0)
	return {
		"input": getattr(u, "prompt_tokens", 0),
		"output": getattr(u, "completion_tokens", 0),
		"total": getattr(u, "total_tokens", 0),
		"cache_hit": hit,
		"cache_miss": getattr(u, "prompt_cache_miss_tokens",
		                      getattr(u, "prompt_tokens", 0) - hit),
	}

def stream_output(console: Console,
                  response,
                  reasoning_file,
                  output_file,
                  *,
                  rich_render: bool = True,
                  target_lang: str = "Chinese"):
	"""
	流式遍历 API 响应，输出结束后可选 Rich 渲染。

	返回 (full_response_list, reasoning_parts_list, usage_dict)。
	"""
	from .config import I18n

	reasoning_parts = []
	full_response = []
	reasoning_active = False
	content_started = False
	usage = {}
	thinking_text = I18n(target_lang)("thinking")
	generating_text = I18n(target_lang)("generating")

	for chunk in response:
		try:
			if chunk.choices[0].delta.reasoning_content is not None:
				rc = chunk.choices[0].delta.reasoning_content
				reasoning_parts.append(rc)
				reasoning_active = True
				dots = "." * (len(reasoning_parts) % 6 + 1)
				sys.stdout.write(f"\r\x1b[90m{thinking_text}{dots}\x1b[0m")
				sys.stdout.flush()
				with open(reasoning_file, "a") as f:
					f.write(rc)
		except AttributeError:
			pass

		if chunk.choices[0].delta.content is not None:
			content = chunk.choices[0].delta.content
			full_response.append(content)
			if reasoning_active:
				sys.stdout.write("\r\x1b[2K\r")
				reasoning_active = False
			if not content_started:
				content_started = True
			if rich_render:
				dots = "." * (len(full_response) % 6 + 1)
				sys.stdout.write(f"\r\x1b[90m{generating_text}{dots}\x1b[0m")
				sys.stdout.flush()
			else:
				sys.stdout.write(content)
				sys.stdout.flush()
			with open(output_file, "a") as f:
				f.write(content)

		if hasattr(chunk, "usage") and chunk.usage:
			usage = _parse_usage(chunk.usage)

	if content_started:
		if rich_render:
			sys.stdout.write("\r\x1b[2K\r")
		else:
			sys.stdout.write("\n")
		sys.stdout.flush()
		if rich_render:
			rendered = render_math("".join(full_response))
			console.print(Markdown(rendered))

	return full_response, reasoning_parts, usage
