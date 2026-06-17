"""CLI 主循环：命令路由 + 状态栏 + vi 模式 + 自动补全"""

import json
import os
import subprocess
import sys
import tempfile

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from .ansi_chars import TerminalColor
from .generate_hash import by_timestamp
from .config import (
    DEFAULT_CONFIG, PROVIDER_URLS, LANG_MAP,
    load_config, save_config, get_config_dir,
    migrate_history, _collect_model,
)
from .history_viewer import show_history
from .translator import translate


class TransMateCLI:
    COMMAND_HELP = {
        "lang": (
            "Set the target language for translation.\n\n"
            "  /lang          Open interactive language selector"
        ),
        "source": (
            "Set or auto-detect the source language.\n\n"
            "  /source        Open interactive selector\n"
            "  /source auto   Enable automatic detection"
        ),
        "model": (
            "Change the main translation model.\n\n"
            "  /model         List available models and select"
        ),
        "fast": (
            "Change the fast model used for language/context detection.\n\n"
            "  /fast          List available models and select"
        ),
        "prov": (
            "Change the API provider and authenticate.\n\n"
            "  /prov          Open provider selector and API key prompt"
        ),
        "config": (
            "Manage configuration.\n\n"
            "  /config show           View config via less\n"
            "  /config edit           Edit config in $EDITOR\n"
            "  /config <key> <value>  Set a config option directly"
        ),
        "history": (
            "View or clear translation history.\n\n"
            "  /history       Browse past sessions\n"
            "  /history clear Clear all history"
        ),
        "show":    "Display current configuration and status.",
        "switch":  "Swap source and target languages. Requires manually specified source language.",
        "bye":     "Exit TransMate.",
        "help":    "List all available commands. Use /<cmd> ? for detailed help on a specific command.",
    }

    COMPLETER = NestedCompleter.from_nested_dict({
        "lang": None, "source": None, "model": None, "fast": None,
        "prov": None, "show": None, "switch": None, "bye": None,
        "help": None, "?": None,
        "config": {"edit": None, "show": None},
        "history": {"clear": None},
    })

    def __init__(self):
        self.config = load_config()
        migrate_history()
        self.session_id = ""
        self.detected_lang = ""
        self.detected_context = ""

    def run(self):
        self._connect()
        self.session_id = by_timestamp()
        vi = self.config.get("vi_mode", True)
        history_path = get_config_dir() / ".input_history"

        session = PromptSession(
            history=FileHistory(str(history_path)),
            bottom_toolbar=self._render_toolbar,
            vi_mode=vi,
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
                        HTML("<ansiyellow><b>>>></b></ansiyellow> "), multiline=False
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
                print("Exiting...")
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
            self.config = load_config()
            print(f"{TerminalColor.YELLOW.value}Config reverted to last valid version.{TerminalColor.RESET.value}")

    def _handle_message(self, text: str):
        sys.stdout.flush()
        self.detected_lang, self.detected_context = translate(
            text, self.config, self.session_id
        )

    def _connect(self):
        import openai
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
                break
            except KeyboardInterrupt:
                print("Exiting...")
                sys.exit(0)
            except Exception:
                print(f"Failed to connect to {provider}. Retrying...")
                import time
                time.sleep(1)

    def _render_toolbar(self):
        sid_short = self.session_id[-12:] if self.session_id else "---"
        target = self.config.get("target_lang", "Chinese")

        if self.config.get("source_lang_specified"):
            src_display = self.config.get("source_lang", "-")
        else:
            dl = self.detected_lang or "?"
            src_display = f"auto({dl})"

        ctx = self.detected_context or "-"
        model = self.config.get("main_model", "-")

        return HTML(
            f"<b> Session:</b> {sid_short} "
            f"<b>| Target:</b> {target} "
            f"<b>| Source:</b> {src_display} "
            f"<b>| Context:</b> {ctx} "
            f"<b>| Model:</b> {model} "
        )

    # ── 命令路由 ──

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
            "config": self._cmd_config,
        }

        if args.strip() == "?":
            self._cmd_help_for(cmd)
            return

        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            print(f"Unknown command '/{cmd}'. Type /? for help.")

    def _cmd_bye(self, args):
        raise EOFError

    def _cmd_help_for(self, cmd: str):
        if cmd not in self.COMMAND_HELP:
            print(f"No help available for '/{cmd}'.")
            return

        print(self.COMMAND_HELP[cmd])

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
            from .config import get_config_path, validate_config
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
                    print(f"{TerminalColor.GRAY.value}Config unchanged.{TerminalColor.RESET.value}")
                    return

                new_config = json.loads(edited)

                for key in list(new_config.keys()):
                    if key not in DEFAULT_CONFIG:
                        del new_config[key]
                        print(f"Ignored unknown key: {key}")

                valid, errors = validate_config(new_config)
                if not valid:
                    print(f"{TerminalColor.RED.value}Validation failed:{TerminalColor.RESET.value}")
                    for e in errors:
                        print(f"  - {e}")
                    print("Config NOT saved.")
                    return

                self._save_config(new_config)
                self.config = new_config
                print(f"{TerminalColor.GREEN.value}Config updated.{TerminalColor.RESET.value}")
            except json.JSONDecodeError as e:
                print(f"{TerminalColor.RED.value}Invalid JSON: {e}{TerminalColor.RESET.value}")
                print("Config NOT saved.")
            except Exception as e:
                print(f"{TerminalColor.RED.value}Error: {e}{TerminalColor.RESET.value}")
            finally:
                os.unlink(tmp_name)

        elif sub:
            val = parts[1] if len(parts) > 1 else ""
            if sub not in DEFAULT_CONFIG:
                print(f"Unknown config key: '{sub}'.")
                print(f"Valid keys: {', '.join(DEFAULT_CONFIG.keys())}")
                return
            if sub in ("source_lang_specified", "vi_mode", "context_optimization"):
                if val.lower() in ("true", "yes", "1"):
                    self.config[sub] = True
                elif val.lower() in ("false", "no", "0"):
                    self.config[sub] = False
                else:
                    self.config[sub] = bool(val)
            elif sub == "source_lang" and val.lower() == "null":
                self.config[sub] = None
            else:
                self.config[sub] = val
            self._save_config()
            print(f"{sub} = {TerminalColor.GREEN.value}{self.config[sub]}{TerminalColor.RESET.value}")

        else:
            print("Usage:\n  /config show           View config via less\n  /config edit           Edit config in $EDITOR\n  /config <key> <value>  Set a config option directly")
            print(f"Valid keys: {', '.join(DEFAULT_CONFIG.keys())}")

    def _cmd_help(self, args):
        print(
            "Available commands:\n"
            "  /lang          Set target language\n"
            "  /source        Set source language (or 'auto' for detection)\n"
            "  /model         Change main translation model\n"
            "  /fast          Change fast model (for language/context detection)\n"
            "  /prov          Change API provider\n"
            "  /show          Show current configuration\n"
            "  /switch        Swap source and target languages\n"
            "  /history       View translation history\n"
            "  /history clear Clear translation history\n"
            "  /bye           Exit\n"
            "  /?, /help      Show this help\n"
            "\n  Use \"\"\" to begin a multi-line message.\n"
        )

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
        print(f"VI Mode:       {self.config.get('vi_mode')}")
        print(f"Cache Optim:   {self.config.get('context_optimization')}")
        print(f"Config Dir:    {get_config_dir()}")

    def _cmd_model(self, args):
        self._change_model("main_model")

    def _cmd_fast(self, args):
        self._change_model("fast_model")

    def _change_model(self, key):
        import openai
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

        choice = input(f"{TerminalColor.GREEN_BOLD.value}Model name or number: {TerminalColor.RESET.value}").strip()
        try:
            idx = int(choice)
            if models and 0 <= idx < len(models):
                self.config[key] = models[idx]
        except ValueError:
            if choice:
                self.config[key] = choice
        self._save_config()
        print(f"{key} set to {TerminalColor.GREEN.value}{self.config[key]}{TerminalColor.RESET.value}.")

    def _cmd_prov(self, args):
        print("Available providers:")
        providers = list(PROVIDER_URLS.keys())
        for i, p in enumerate(providers):
            print(f"  {i}) {p}")
        choice = input(f"{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ").strip()
        try:
            self.config["provider"] = providers[int(choice)]
        except (ValueError, IndexError):
            if choice.upper() in providers:
                self.config["provider"] = choice.upper()
            else:
                print("Invalid provider.")
                return
        self.config["base_url"] = PROVIDER_URLS[self.config["provider"]]

        import openai
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

    def _cmd_lang(self, args):
        print("Available languages:")
        langs = list(LANG_MAP.keys())
        for i, lang in enumerate(langs):
            cn = LANG_MAP.get(lang, "")
            print(f"  {i:2d}) {lang} ({cn})")
        choice = input(f"{TerminalColor.GREEN_BOLD.value}Target language: {TerminalColor.RESET.value}").strip()
        try:
            self.config["target_lang"] = langs[int(choice)]
        except (ValueError, IndexError):
            if choice in langs:
                self.config["target_lang"] = choice
            elif choice in LANG_MAP.values():
                for k, v in LANG_MAP.items():
                    if v == choice:
                        self.config["target_lang"] = k
                        break
            else:
                print("Invalid language.")
                return
        self._save_config()
        print(f"Target language: {TerminalColor.BLUE.value}{self.config['target_lang']}{TerminalColor.RESET.value}.")

    def _cmd_source(self, args):
        if args.strip().lower() == "auto":
            self.config["source_lang_specified"] = False
            self.config["source_lang"] = None
            self._save_config()
            print(f"Source language: {TerminalColor.GREEN.value}auto (detection enabled){TerminalColor.RESET.value}.")
            return

        print("Available languages:")
        langs = list(LANG_MAP.keys())
        for i, lang in enumerate(langs):
            cn = LANG_MAP.get(lang, "")
            print(f"  {i:2d}) {lang} ({cn})")
        print(f"  Or type 'auto' for automatic detection.")
        choice = input(f"{TerminalColor.GREEN_BOLD.value}Source language: {TerminalColor.RESET.value}").strip()
        if choice.lower() == "auto":
            self.config["source_lang_specified"] = False
            self.config["source_lang"] = None
        else:
            try:
                self.config["source_lang"] = langs[int(choice)]
            except (ValueError, IndexError):
                if choice in langs:
                    self.config["source_lang"] = choice
                else:
                    print("Invalid language.")
                    return
            self.config["source_lang_specified"] = True
        self._save_config()
        src = self.config.get("source_lang", "auto")
        print(f"Source language: {TerminalColor.BLUE.value}{src}{TerminalColor.RESET.value}.")

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

    def _cmd_history(self, args):
        import shutil
        from .config import get_history_dir
        if args.strip().lower() == "clear":
            hd = get_history_dir()
            if hd.exists():
                shutil.rmtree(hd)
                hd.mkdir(parents=True, exist_ok=True)
            print("History cleared.")
            return
        show_history()
