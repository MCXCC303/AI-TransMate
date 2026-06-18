"""CLI 主循环：命令路由 + 状态栏 + 自动补全"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import openai
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from .ansi_chars import TerminalColor
from .config import (
	DEFAULT_CONFIG, I18n, PROVIDER_URLS, LANG_MAP,
	load_config, save_config, get_config_dir, get_config_path,
	_collect_model, estimate_cost, validate_config,
)
from .generate_hash import by_timestamp
from .history_viewer import show_history
from .translator import TranslationSession

_LANG_LOWER: dict[str, str] = {k.lower(): k for k in LANG_MAP}

def _find_language(name: str) -> str | None:
	"""大小写不敏感匹配语言名，支持英文名和中文名。"""
	key = name.strip().lower()
	if key in _LANG_LOWER:
		return _LANG_LOWER[key]
	for k, v in LANG_MAP.items():
		if v == name.strip():
			return k
		if v.lower() == key:
			return k
	return None

class TransMateCLI:
	COMPLETER = NestedCompleter.from_nested_dict({
		"lang": None, "source": None, "model": None, "fast": None,
		"prov": None, "show": None, "switch": None, "bye": None,
		"help": None, "?": None, "clear": None, "usage": None,
		"config": {"edit": None, "show": None},
		"history": {"clear": None},
	})

	def __init__(self):
		self.config, self._is_new = load_config()
		self.session_id = ""
		self.detected_lang = ""
		self.detected_context = ""
		self.usage = {}
		self.session: TranslationSession | None = None

	def run(self):
		if self._is_new:
			time.sleep(0.5)
			print(f"{TerminalColor.GREEN.value}{self._t('welcome')}{TerminalColor.RESET.value}")
			sys.stdout.flush()
			time.sleep(0.5)
			sys.stdout.write("\033[2J\033[H")
			sys.stdout.flush()

		self._connect()
		self.session_id = by_timestamp()
		history_path = get_config_dir() / ".input_history"

		session = PromptSession(
			history=FileHistory(str(history_path)),
			bottom_toolbar=self._render_toolbar,
			completer=self.COMPLETER,
			complete_while_typing=False,
			prompt_continuation=lambda w, ln, wc: "... " if ln > 0 else "",
			wrap_lines=True,
		)

		multiline = False
		buffer = []

		while True:
			try:
				if not multiline:
					text = session.prompt(
						HTML("<ansiyellow><b>>>> </b></ansiyellow>"), multiline=False
					)
					if "\n" in text:
						self._handle_message("\n".join(text.split("\n")))
						continue

					stripped = text.strip()
					if stripped.startswith('"""') and len(stripped) > 3:
						self._handle_message(stripped[3:])
						continue
					if stripped == '"""':
						multiline = True
						buffer = []
						continue
					if not stripped:
						continue
					if stripped.startswith("/"):
						self._dispatch(stripped[1:])
						continue
					self._handle_message(text)
				else:
					text = session.prompt("... ")
					if text.strip() == '"""':
						multiline = False
						self._handle_message("\n".join(buffer))
						buffer = []
					else:
						buffer.append(text)

			except EOFError:
				self._show_exit_usage()
				print(self._t("exiting"))
				break
			except KeyboardInterrupt:
				if multiline:
					multiline = False
					buffer = []
				print()
				continue

	def _save_config(self, config=None):
		"""保存配置；验证失败时自动回退到磁盘版本。"""
		if config is None:
			config = self.config
		if not save_config(config):
			self.config, _ = load_config()
			print(f"{TerminalColor.YELLOW.value}{self._t('config_reverted')}{TerminalColor.RESET.value}")

	def _handle_message(self, text: str):
		sys.stdout.flush()
		sys.stdout.write(f"{TerminalColor.GREEN.value}==> {TerminalColor.RESET.value}\n")
		sys.stdout.flush()

		if not self.config.get("multi_turn", True):
			self.session = None

		if self.session is None:
			self.session = TranslationSession(self.config, self.session_id)

		self.detected_lang, self.detected_context, self.usage = self.session.translate(
			text, self.config
		)

		if not self.config.get("multi_turn", True):
			self.session = None

	@staticmethod
	def _prompt(message: str) -> str:
		from prompt_toolkit.shortcuts import prompt as pt_prompt
		from prompt_toolkit.formatted_text import HTML
		try:
			return pt_prompt(HTML(f"<ansigreen><b>{message}</b></ansigreen>"))
		except (EOFError, KeyboardInterrupt):
			return ""

	@property
	def i18n(self) -> I18n:
		return I18n(self.config.get("target_lang", "Chinese"))

	def _t(self, key: str) -> str:
		return self.i18n(key)

	def _maybe_warn_session(self):
		"""若会话活跃则提示更改将在新会话中生效。"""
		if self.session and self.session.is_active:
			print(f"{TerminalColor.YELLOW.value}{self._t('config_pending')}{TerminalColor.RESET.value}")

	def _show_exit_usage(self):
		if not self.config.get("show_usage_on_exit", False):
			return
		if self.session:
			self.session._cancel_context_timer()
		u = self.usage
		if not u or u.get("total", 0) == 0:
			return
		model = self.config.get("main_model", "-")
		cost = estimate_cost(model, u)
		ml = self._t("model_label");
		il = self._t("input_label")
		ol = self._t("output_label");
		cl = self._t("cache_label")
		tl = self._t("total_label");
		cl2 = self._t("cost_label")
		hi = self._t("hit");
		mi = self._t("miss")
		print(f"\n{TerminalColor.GRAY.value}{self._t('session_usage')}{TerminalColor.RESET.value}")
		print(f"  {ml}:    {model}")
		print(f"  {il}:    {u.get('input', 0):,}")
		print(f"  {ol}:   {u.get('output', 0):,}")
		if u.get("cache_hit", 0) > 0:
			print(f"  {cl}:    {hi} {u['cache_hit']:,} / {mi} {u.get('cache_miss', 0):,}")
		print(f"  {tl}:    {u.get('total', 0):,}")
		print(f"  {cl2}:     {cost}")

	def _cmd_clear(self, args):
		if self.session is None or not self.session.is_active:
			print(f"{TerminalColor.GRAY.value}{self._t('session_inactive')}{TerminalColor.RESET.value}")
			return
		self.session = None
		self.detected_lang = ""
		self.detected_context = ""
		self.usage = {}
		self.session_id = by_timestamp()
		print(f"{TerminalColor.GREEN.value}{self._t('session_reset')}{TerminalColor.RESET.value}")

	def _cmd_usage(self, args):
		u = self.usage
		if not u or u.get("total", 0) == 0:
			print(f"{TerminalColor.GRAY.value}{self._t('no_usage')}{TerminalColor.RESET.value}")
			return
		model = self.config.get("main_model", "-")
		cost = estimate_cost(model, u)
		print(f"Model:    {model}")
		print(f"Input:    {u.get('input', 0):,}")
		print(f"Output:   {u.get('output', 0):,}")
		if u.get("cache_hit", 0) > 0:
			print(f"Cache:    hit {u['cache_hit']:,} / miss {u.get('cache_miss', 0):,}")
		if u.get("reasoning", 0) > 0:
			print(f"Reasoning:{u['reasoning']:,}")
		print(f"Total:    {u.get('total', 0):,}")
		print(f"Cost:     {cost}")

	def _connect(self):
		provider = self.config.get("provider", "DEEPSEEK")
		model = self.config.get("main_model", "deepseek-chat")

		while True:
			try:
				client = openai.OpenAI(
					api_key=self.config.get("api_key"),
					base_url=self.config.get("base_url"),
				)
				try:
					client.models.list()
				except openai.NotFoundError:
					pass
				print(
					f"Connected to {TerminalColor.CYAN.value}{provider}{TerminalColor.RESET.value}. "
					f"Model: {TerminalColor.GREEN.value}{model}{TerminalColor.RESET.value}."
				)
				print(f"Target: {TerminalColor.BLUE.value}{self.config.get('target_lang', 'Chinese')}{TerminalColor.RESET.value}. "
				      f"{TerminalColor.GRAY.value}(/? for help){TerminalColor.RESET.value}\n")
				time.sleep(0.5)
				break
			except KeyboardInterrupt:
				print(self._t("exiting"))
				sys.exit(0)
			except Exception:
				print(f"Failed to connect to {provider}. Retrying...")
				time.sleep(1)

	def _render_toolbar(self):
		sid_short = self.session_id[-12:] if self.session_id else "---"
		active = self.session and self.session.is_active

		# 会话活跃时用快照值 + 绿色标记，否则用 config 当前值
		if active:
			target = self.session.target_lang
			model = self.session.main_model
			if self.session.source_lang_specified:
				src_display = self.session.source_lang or "-"
			else:
				dl = self.session.detected_lang or "?"
				if dl == "Unknown":
					dl = "?"
				src_display = f"auto({dl})"
			ctx = self.session.detected_context or "-"
		else:
			target = self.config.get("target_lang", "Chinese")
			model = self.config.get("main_model", "-")
			if self.config.get("source_lang_specified"):
				src_display = self.config.get("source_lang", "-")
			else:
				dl = self.detected_lang or "?"
				if dl == "Unknown":
					dl = "?"
				src_display = f"auto({dl})"
			ctx = self.detected_context or "-"

		lock_color = "ansigreen" if active else ""

		# Context 颜色：活跃但语境过期时用橙色，否则用绿色
		ctx_color = "ansiyellow" if (active and self.session.context_stale) else lock_color

		S = self._t("tb_session")
		T = self._t("tb_target")
		So = self._t("tb_source")
		C = self._t("tb_context")
		M = self._t("tb_model")
		Tu = self._t("tb_turns")

		parts = [
			f"<b> {S}:</b> {sid_short}",
			f"<b>| {T}:</b> <{lock_color}>{target}</{lock_color}>" if active else f"<b>| {T}:</b> {target}",
			f"<b>| {So}:</b> <{lock_color}>{src_display}</{lock_color}>" if active else f"<b>| {So}:</b> {src_display}",
			f"<b>| {C}:</b> <{ctx_color}>{ctx}</{ctx_color}>" if active else f"<b>| {C}:</b> {ctx}",
			f"<b>| {M}:</b> {model}",
		]

		if active:
			parts.append(f"<b>| {Tu}:</b> {self.session.turn_count}")

		u = self.usage
		if self.config.get("show_tokens", True) and u and u.get("output", 0) > 0:
			parts.append(f"<b>| {self._t('tb_output')}:</b> {u['output']}")

		return HTML(" ".join(parts))

	def _dispatch(self, raw: str):
		parts = raw.strip().split(maxsplit=1)
		cmd = parts[0].lower()
		args = parts[1] if len(parts) > 1 else ""

		handlers = {
			"bye": self._cmd_bye, "quit": self._cmd_bye, "exit": self._cmd_bye, "q": self._cmd_bye,
			"help": self._cmd_help, "?": self._cmd_help,
			"show": self._cmd_show, "model": self._cmd_model, "fast": self._cmd_fast,
			"prov": self._cmd_prov, "lang": self._cmd_lang, "source": self._cmd_source,
			"switch": self._cmd_switch, "history": self._cmd_history,
			"config": self._cmd_config, "clear": self._cmd_clear,
			"usage": self._cmd_usage,
		}

		if args.strip() == "?":
			self._cmd_help_for(cmd)
			return

		handler = handlers.get(cmd)
		if handler:
			handler(args)
		else:
			print(self._t("unknown_command").format(cmd=cmd))

	def _cmd_bye(self, args):
		raise EOFError

	def _cmd_help_for(self, cmd: str):
		key = f"help_{cmd}"
		text = self._t(key)
		if text == key:  # no translation found
			print(self._t("help_not_found").format(cmd=cmd))
			return
		print(text)

	def _cmd_config(self, args):
		parts = args.strip().split(maxsplit=1)
		sub = parts[0].lower() if parts and parts[0] else ""

		if sub == "show":
			config_path = str(get_config_dir() / "config.json")
			try:
				subprocess.call(["less", config_path])
			except FileNotFoundError:
				with open(config_path, "r") as f:
					print(f.read())

		elif sub == "edit":
			config_path = get_config_path()
			with open(config_path, "r", encoding="utf-8") as src:
				original = src.read()
			original_parsed = json.loads(original)

			tmp_fd, tmp_name = tempfile.mkstemp(suffix=".json", prefix="transmate_", text=True)
			try:
				with os.fdopen(tmp_fd, "w") as dst:
					dst.write(original)
				os.chmod(tmp_name, 0o600)
				editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
				subprocess.call([editor, tmp_name])

				with open(tmp_name, "r", encoding="utf-8") as src:
					edited = src.read()

				if edited.strip() == original.strip():
					print(f"{TerminalColor.GRAY.value}{self._t('config_unchanged')}{TerminalColor.RESET.value}")
					return

				new_config = json.loads(edited)

				for key in list(new_config.keys()):
					if key not in DEFAULT_CONFIG:
						del new_config[key]

				valid, errors = validate_config(new_config)
				if not valid:
					print(f"{TerminalColor.RED.value}{self._t('validation_failed')}{TerminalColor.RESET.value}")
					for e in errors:
						print(f"  - {e}")
					print(self._t("config_not_saved"))
					return

				self._save_config(new_config)
				self.config = new_config
				print(f"{TerminalColor.GREEN.value}{self._t('config_saved_success')}{TerminalColor.RESET.value}")
			except json.JSONDecodeError as e:
				print(f"{TerminalColor.RED.value}{self._t('invalid_json')} {e}{TerminalColor.RESET.value}")
				print(self._t("config_not_saved"))
			except Exception as e:
				print(f"{TerminalColor.RED.value}Error: {e}{TerminalColor.RESET.value}")
			finally:
				os.unlink(tmp_name)

		elif sub:
			val = parts[1] if len(parts) > 1 else ""
			if sub not in DEFAULT_CONFIG:
				print(f"{self._t('unknown_config_key')} '{sub}'.\n")
				print(f"{self._t('valid_keys')} {', '.join(DEFAULT_CONFIG.keys())}")
				return
			if not val:
				print(f"{sub} = {TerminalColor.GREEN.value}{self.config.get(sub)}{TerminalColor.RESET.value}")
				return
			if isinstance(DEFAULT_CONFIG.get(sub), bool):
				if val.lower() in ("true", "yes", "1"):
					self.config[sub] = True
				elif val.lower() in ("false", "no", "0"):
					self.config[sub] = False
				else:
					print(f"'{val}' {self._t('not_valid_bool')}")
					return
			elif sub == "source_lang" and val.lower() == "null":
				self.config[sub] = None
			else:
				self.config[sub] = val
			self._save_config()
			print(f"{sub} = {TerminalColor.GREEN.value}{self.config[sub]}{TerminalColor.RESET.value}")

		else:
			print(self._t("config_usage"))
			print()
			print(f"{self._t('valid_keys')} {', '.join(DEFAULT_CONFIG.keys())}")

	def _cmd_help(self, args):
		print(f"{self._t('cmd_help')}:\n")
		print(self._t("cmd_help_text"))

	def _cmd_show(self, args):
		print(f"Provider:      {self.config.get('provider')}")
		print(f"Base URL:      {self.config.get('base_url')}")
		print(f"Main Model:    {self.config.get('main_model')}")
		print(f"Fast Model:    {self.config.get('fast_model')}")
		print(f"Target Lang:   {self.config.get('target_lang')}")
		src = self.config.get('source_lang', 'auto')
		if not self.config.get('source_lang_specified'):
			src = f"auto (detected: {self.detected_lang or 'N/A'})"
		print(f"Source Lang:   {src}")
		print(f"Cache Optim:   {self.config.get('context_optimization')}")
		print(f"Config Dir:    {get_config_dir()}")

	def _cmd_model(self, args):
		self._change_model("main_model")

	def _cmd_fast(self, args):
		self._change_model("fast_model")

	def _change_model(self, key):
		client = openai.OpenAI(
			api_key=self.config.get("api_key"),
			base_url=self.config.get("base_url"),
		)
		models = []
		try:
			models = [m.id for m in client.models.list()]
			models.sort()
			print("Available models:")
			for i, m in enumerate(models[:20]):
				print(f"  {i:2d}) {m}")
			if len(models) > 20:
				print(f"  ... and {len(models) - 20} more")
		except Exception:
			print("Could not fetch model list. Enter model name directly.")

		choice = self._prompt("Model name or number: ").strip()
		try:
			idx = int(choice)
			if models and 0 <= idx < len(models):
				self.config[key] = models[idx]
		except ValueError:
			if choice:
				self.config[key] = choice
		self._save_config()
		print(f"{key} set to {TerminalColor.GREEN.value}{self.config[key]}{TerminalColor.RESET.value}.")

		if self.session and self.session.is_active:
			if key == "main_model":
				self.session.main_model = self.config[key]
			elif key == "fast_model":
				self.session.fast_model = self.config[key]

	def _cmd_prov(self, args):
		print("Available providers:")
		providers = list(PROVIDER_URLS.keys())
		for i, p in enumerate(providers):
			print(f"  {i}) {p}")
		choice = self._prompt(">>> ").strip()
		try:
			self.config["provider"] = providers[int(choice)]
		except (ValueError, IndexError):
			if choice.upper() in providers:
				self.config["provider"] = choice.upper()
			else:
				print("Invalid provider.")
				return
		self.config["base_url"] = PROVIDER_URLS[self.config["provider"]]

		import getpass
		self.config["api_key"] = getpass.getpass(f"API key for {self.config['provider']}: ")
		client = openai.OpenAI(api_key=self.config["api_key"], base_url=self.config["base_url"])
		try:
			client.models.list()
		except openai.NotFoundError:
			pass
		except openai.AuthenticationError:
			print("Invalid API key.")
			return

		_collect_model(self.config)
		self._save_config()
		print(f"Provider: {TerminalColor.GREEN.value}{self.config['provider']}{TerminalColor.RESET.value}, "
		      f"Model: {TerminalColor.GREEN.value}{self.config['main_model']}{TerminalColor.RESET.value}.")
		self._maybe_warn_session()

	def _cmd_lang(self, args):
		print("Available languages:")
		langs = list(LANG_MAP.keys())
		for i, lang in enumerate(langs):
			cn = LANG_MAP.get(lang, "")
			print(f"  {i:2d}) {lang} ({cn})")
		choice = self._prompt("Target language: ").strip()
		try:
			self.config["target_lang"] = langs[int(choice)]
		except (ValueError, IndexError):
			match = _find_language(choice)
			if match:
				self.config["target_lang"] = match
			else:
				print("Invalid language.")
				return
		self._save_config()
		print(f"Target language: {TerminalColor.BLUE.value}{self.config['target_lang']}{TerminalColor.RESET.value}.")
		self._maybe_warn_session()

	def _cmd_source(self, args):
		if args.strip().lower() == "auto":
			self.config["source_lang_specified"] = False
			self.config["source_lang"] = None
			self._save_config()
			print(f"Source language: {TerminalColor.GREEN.value}auto (detection enabled){TerminalColor.RESET.value}.")
			self._maybe_warn_session()
			return

		print("Available languages:")
		langs = list(LANG_MAP.keys())
		for i, lang in enumerate(langs):
			cn = LANG_MAP.get(lang, "")
			print(f"  {i:2d}) {lang} ({cn})")
		print(f"\n\n...Or type 'auto' for automatic detection.")
		choice = self._prompt("Source language: ").strip()
		if choice.lower() == "auto":
			self.config["source_lang_specified"] = False
			self.config["source_lang"] = None
		else:
			try:
				self.config["source_lang"] = langs[int(choice)]
			except (ValueError, IndexError):
				match = _find_language(choice)
				if match:
					self.config["source_lang"] = match
				else:
					print("Invalid language.")
					return
			self.config["source_lang_specified"] = True
		self._save_config()
		src = self.config.get("source_lang", "auto")
		print(f"Source language: {TerminalColor.BLUE.value}{src}{TerminalColor.RESET.value}.")
		self._maybe_warn_session()

	def _cmd_switch(self, args):
		if not self.config.get("source_lang_specified") or not self.config.get("source_lang"):
			print("Set a source language first with /source.")
			return
		self.config["source_lang"], self.config["target_lang"] = (
			self.config["target_lang"], self.config["source_lang"]
		)
		self._save_config()
		print(f"Swapped: {TerminalColor.BLUE.value}{self.config['source_lang']}{TerminalColor.RESET.value} "
		      f"→ {TerminalColor.RED.value}{self.config['target_lang']}{TerminalColor.RESET.value}.")
		self._maybe_warn_session()

	def _cmd_history(self, args):
		from .config import get_history_dir
		if args.strip().lower() == "clear":
			hd = get_history_dir()
			if hd.exists():
				shutil.rmtree(hd)
				hd.mkdir(parents=True, exist_ok=True)
			print("History cleared.")
			return
		show_history(self.config.get("target_lang", "Chinese"))
