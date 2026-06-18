"""翻译编排：会话管理 → 检测 → 提示词 → 流式 → 历史存储"""

import datetime
import hashlib
import os
import signal
import sys
import threading

import openai
from rich.console import Console

from .ansi_chars import TerminalColor
from .config import get_history_dir, I18n
from .detect import detect_source_language, detect_context
from .output import stream_output
from .prompt_builder import build_system_message
from .providers import get_provider

_context_cache: dict[str, str] = {}
_MAX_CACHE_SIZE = 256

def _cached_detect_context(text: str, client, provider, model: str) -> str:
	cache_key = hashlib.md5(text.encode("utf-8")).hexdigest()
	if cache_key in _context_cache:
		return _context_cache[cache_key]

	result = detect_context(text, client, provider, model)

	if len(_context_cache) >= _MAX_CACHE_SIZE:
		_context_cache.clear()
	_context_cache[cache_key] = result
	return result

class TranslationSession:
	"""多轮翻译会话，累积对话历史以最大化 LLM 前缀缓存命中率。"""

	MAX_TURNS = 20

	def __init__(self, config: dict, history_id: str):
		# 拍配置快照（会话期间不变）
		self.target_lang = config.get("target_lang", "Chinese")
		self.source_lang_specified = config.get("source_lang_specified", False)
		self.source_lang = config.get("source_lang") if self.source_lang_specified else None
		self.main_model = config.get("main_model", "deepseek-chat")
		self.fast_model = config.get("fast_model", self.main_model)

		self._history_id = history_id
		self._messages: list[dict] = []
		self._turn_count = 0
		self._detected_lang: str = ""
		self._detected_context: str = ""
		self._last_input: str = ""
		self._context_timer: threading.Timer | None = None
		self.context_stale: bool = False

	@property
	def is_active(self) -> bool:
		return self._turn_count > 0

	@property
	def turn_count(self) -> int:
		return self._turn_count

	@property
	def detected_lang(self) -> str:
		return self._detected_lang

	@property
	def detected_context(self) -> str:
		return self._detected_context

	def _cancel_context_timer(self):
		if self._context_timer is not None:
			self._context_timer.cancel()
			self._context_timer = None

	def _start_context_timer(self, config: dict):
		if not self.is_active or not config.get("context_review", True):
			return
		self._cancel_context_timer()
		text = self._last_input
		original_ctx = self._detected_context
		api_key = config.get("api_key", "")
		base_url = config.get("base_url", "https://api.deepseek.com/v1")
		provider_name = config.get("provider", "DEEPSEEK")
		fast_model = self.fast_model
		session = self

		def _check():
			if not session.is_active:
				return
			try:
				client = openai.OpenAI(api_key=api_key, base_url=base_url)
				p = get_provider(provider_name)
				new_ctx = detect_context(text, client, p, fast_model)
				if new_ctx != original_ctx:
					session.context_stale = True
					os.kill(os.getpid(), signal.SIGWINCH)
			except Exception:
				pass

		delay = max(5.0, min(60, len(text) / 40))
		self._context_timer = threading.Timer(delay, _check)
		self._context_timer.daemon = True
		self._context_timer.start()

	def translate(self, text: str, config: dict):
		"""执行一次翻译，追加到会话历史。返回 (detected_lang, detected_context, usage)。"""
		api_key = config.get("api_key", "")
		base_url = config.get("base_url", "https://api.deepseek.com/v1")

		client = openai.OpenAI(api_key=api_key, base_url=base_url)
		provider = get_provider(config.get("provider", "DEEPSEEK"))
		i18n = I18n(self.target_lang)
		self._cancel_context_timer()

		if self._turn_count == 0:
			if not self.source_lang_specified:
				sys.stdout.write(
					f"{TerminalColor.GRAY.value}{i18n('detecting_lang')}{TerminalColor.RESET.value}\r"
				)
				sys.stdout.flush()
				self._detected_lang = detect_source_language(text,
				                                             client,
				                                             provider,
				                                             self.fast_model)
				sys.stdout.write(f"{TerminalColor.CLEAR_LINE.value}\r")
				sys.stdout.flush()
			else:
				self._detected_lang = self.source_lang or ""

			sys.stdout.write(
				f"{TerminalColor.GRAY.value}{i18n('analyzing_context')}{TerminalColor.RESET.value}\r"
			)
			sys.stdout.flush()
			self._detected_context = _cached_detect_context(text, client, provider, self.fast_model)
			sys.stdout.write(f"{TerminalColor.CLEAR_LINE.value}\r")
			sys.stdout.flush()

			source_for_prompt = self._detected_lang if self._detected_lang and self._detected_lang != "Unknown" else ""
			system_msg = build_system_message(
				target_lang=self.target_lang,
				source_lang=source_for_prompt,
				context=self._detected_context,
			)
			self._messages = [{"role": "system", "content": system_msg}]

		if self._turn_count > 0:
			text = f"Translate the following text to {self.target_lang}. Output only the translation, nothing else.\n\n{text}"
		self._messages.append({"role": "user", "content": text})
		self._turn_count += 1

		if self._turn_count > self.MAX_TURNS:
			self._messages = [self._messages[0]] + self._messages[-(self.MAX_TURNS * 2):]

		history_dir = get_history_dir()
		history_dir.mkdir(parents=True, exist_ok=True)
		output_file = history_dir / f"{self._history_id}_output.md"
		reasoning_file = history_dir / f"{self._history_id}_reasoning.md"
		timestamp = datetime.datetime.now().strftime("%Y.%m.%d, %H:%M")

		with open(output_file, "a") as f:
			f.write(f"\n\n---\n\n`{timestamp}`\n> Input:\n\n{text}\n\n> Output:\n\n")
		with open(reasoning_file, "a") as f:
			f.write(f"\n\n---\n\n`{timestamp}`\n> Input:\n\n{text}\n\n> Reasoning:\n\n")

		chat_kwargs = provider.get_chat_kwargs(
			self._messages, self.main_model, stream=True,
			enable_thinking=config.get("enable_thinking", False),
		)
		response = client.chat.completions.create(**chat_kwargs)

		console = Console()
		full_response, reasoning_parts, usage = stream_output(
			console, response, reasoning_file, output_file,
			rich_render=config.get("rich_render", True),
			target_lang=self.target_lang,
		)

		if full_response:
			content_str = "".join(full_response)
			reasoning_str = "".join(reasoning_parts) if reasoning_parts else None
			self._messages.append(
				provider.build_assistant_message(content_str, reasoning_str)
			)
		else:
			# 模型未返回内容，移除本次 user 消息避免污染历史
			self._messages.pop()
			self._turn_count -= 1
			sys.stdout.write(
				f"{TerminalColor.GRAY_ITALIC.value}{i18n('service_busy')}{TerminalColor.RESET.value}\n"
			)
			with open(output_file, "a") as f:
				f.write(f"{i18n('service_busy')}\n")

		if not reasoning_parts and full_response:
			with open(reasoning_file, "a") as f:
				f.write(f"{i18n('no_reasoning')}\n")

		self._last_input = text
		if full_response and self._turn_count > 1:
			self._start_context_timer(config)

		return self._detected_lang, self._detected_context, usage
