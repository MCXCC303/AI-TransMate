"""DeepSeek 提供商：thinking 模式、reasoning_content 处理。"""

from .base import BaseProvider

class DeepSeekProvider(BaseProvider):
	"""DeepSeek 特有行为：思考模式显式控制、reasoning_content 保留。"""

	name = "deepseek"

	def get_chat_kwargs(self, messages: list, model: str, *,
	                    stream: bool = True,
	                    enable_thinking: bool = False) -> dict:
		thinking_type = "enabled" if enable_thinking else "disabled"
		return {
			"model": model,
			"stream": stream,
			"messages": messages,
			"extra_body": {"thinking": {"type": thinking_type}},
		}

	def get_detect_kwargs(self, prompt: str, model: str) -> dict:
		"""检测调用必须禁用 thinking，否则 content 可能为 None。"""
		return {
			"model": model,
			"messages": [{"role": "system", "content": prompt}],
			"temperature": 0.1,
			"max_tokens": 32,
			"extra_body": {"thinking": {"type": "disabled"}},
		}

	def build_assistant_message(self, content: str, reasoning: str | None = None) -> dict:
		"""DeepSeek 多轮对话需要保留 reasoning_content。"""
		msg: dict = {"role": "assistant", "content": content}
		if reasoning:
			msg["reasoning_content"] = reasoning
		return msg
