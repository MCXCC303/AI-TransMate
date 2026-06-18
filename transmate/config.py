import json
import os
import sys
from pathlib import Path

import openai

from .ansi_chars import TerminalColor

_CONTENTS_DIR = Path(__file__).parent / "contents"


def _load_contents(filename):
    with open(_CONTENTS_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_prompts():
    prompts_dir = _CONTENTS_DIR / "prompts"
    prompts = {}
    for md_file in sorted(prompts_dir.glob("*.md")):
        with open(md_file, "r", encoding="utf-8") as f:
            prompts[md_file.stem] = f.read().strip()
    return prompts


PROVIDER_URLS = _load_contents("providers.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.deepseek.com/v1",
    "provider": "DEEPSEEK",
    "main_model": "deepseek-chat",
    "fast_model": "deepseek-chat",
    "target_lang": "Chinese",
    "source_lang_specified": False,
    "source_lang": None,
    "context_optimization": True,
    "context_review": True,
    "show_usage_on_exit": False,
    "show_tokens": True,
    "rich_render": False,
}

LANG_MAP = _load_contents("languages.json")
PRICING = _load_contents("pricing.json")


def estimate_cost(model: str, usage: dict) -> str:
    """根据 usage 和模型定价估算费用，返回格式化字符串。"""
    price = PRICING.get(model)
    if not price:
        return "N/A"
    inp = usage.get("input", 0)
    out = usage.get("output", 0)
    cache_hit = usage.get("cache_hit", 0)
    cache_miss = usage.get("cache_miss", inp)
    reasoning = usage.get("reasoning", 0)
    cost = (
        inp * price.get("input", 0)
        + out * price.get("output", 0)
        + cache_hit * price.get("cache_read", 0)
        + (cache_miss - cache_hit) * price.get("cache_write", 0)
        + reasoning * price.get("reasoning", price.get("output", 0))
    ) / 1_000_000
    return f"${cost:.6f}"


def get_config_dir():
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(xdg) / "transmate"


def get_config_path():
    return get_config_dir() / "config.json"


def get_history_dir():
    return get_config_dir() / "history"


def load_config():
    """返回 (config, is_new) — is_new 表示是否首次创建。"""
    config_dir = get_config_dir()
    config_path = get_config_path()

    if not config_path.exists():
        return _init_config(config_dir, config_path), True

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    config = DEFAULT_CONFIG | config
    return config, False


def _init_config(config_dir, config_path):
    config_dir.mkdir(parents=True, exist_ok=True)
    get_history_dir().mkdir(parents=True, exist_ok=True)

    config = dict(DEFAULT_CONFIG)
    env = _read_env_config()

    if env:
        config.update(env)
        missing = [k for k in ("api_key", "provider", "base_url", "main_model") if k not in env]
        print(f"{TerminalColor.GREEN.value}Read from environment:{TerminalColor.RESET.value} "
              f"{', '.join(env)}")
        if missing:
            print(f"{TerminalColor.YELLOW.value}Missing: {', '.join(missing)} — completing...{TerminalColor.RESET.value}\n")
            _interactive_setup_partial(config, missing)
        else:
            _verify_api(config)
        print(f"{TerminalColor.GREEN.value}Setup complete. Config saved to {config_path}{TerminalColor.RESET.value}")
    else:
        print("Welcome to AI TransMate! Let's set up your configuration.\n")
        _interactive_setup(config)

    save_config(config)
    return config


def _read_env_config():
    """从环境变量读取配置，返回 dict 或空 dict。"""
    result = {}
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    model = os.environ.get("OPENAI_MODEL", "")

    if api_key:
        result["api_key"] = api_key
    if base_url:
        result["base_url"] = base_url
        for name, url in PROVIDER_URLS.items():
            if base_url.startswith(url):
                result["provider"] = name
                break
        if "provider" not in result:
            result["provider"] = "DEEPSEEK"
    if model:
        result["main_model"] = model
        result["fast_model"] = model

    return result


def _verify_api(config):
    """验证 API 连接，返回 True/False。"""
    try:
        client = openai.OpenAI(api_key=config.get("api_key", ""),
                               base_url=config.get("base_url", ""))
        client.models.list()
        return True
    except openai.NotFoundError:
        return True
    except Exception:
        return False


def _interactive_setup(config):
    """完整交互式设置（无环境变量时使用）。"""
    _interactive_setup_partial(config, list(REQUIRED_KEYS))
    print(f"{TerminalColor.GREEN.value}Setup complete! Configuration saved.{TerminalColor.RESET.value}")


def _interactive_setup_partial(config, missing_keys):
    """仅为缺失的 key 进行交互式补全。"""
    import getpass

    if "provider" in missing_keys or "base_url" in missing_keys:
        print("Choose an API provider:")
        providers = list(PROVIDER_URLS.keys())
        for i, p in enumerate(providers):
            print(f"  {i}) {p}")
        while True:
            choice = input(f"{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ").strip()
            try:
                config["provider"] = providers[int(choice)]
                break
            except (ValueError, IndexError):
                if choice.upper() in providers:
                    config["provider"] = choice.upper()
                    break
                print("Invalid choice. Try again.")
        config["base_url"] = PROVIDER_URLS[config["provider"]]

    if "api_key" in missing_keys:
        while True:
            try:
                config["api_key"] = getpass.getpass(
                    f"Enter your API key for {config.get('provider', 'provider')}: ")
                sys.stdout.write("\033[1A\033[2K\nVerifying API key...\n")
                if _verify_api(config):
                    break
                print("Invalid API key. Try again.")
            except KeyboardInterrupt:
                print("\nSetup cancelled.")
                raise

    if "main_model" in missing_keys:
        _collect_model(config)

    if "target_lang" in missing_keys:
        print("Choose target language for translation:")
        langs = list(LANG_MAP.keys())
        for i, lang in enumerate(langs):
            print(f"  {i:2d}) {lang}")
        while True:
            choice = input(f"{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ").strip()
            try:
                config["target_lang"] = langs[int(choice)]
                break
            except (ValueError, IndexError):
                if choice in langs:
                    config["target_lang"] = choice
                    break
                if choice in LANG_MAP.values():
                    for k, v in LANG_MAP.items():
                        if v == choice:
                            config["target_lang"] = k
                            break
                    break
                print("Invalid language. Try again.")


def _collect_model(config):
    print(f"\nAvailable models from {config['provider']}:")
    client = openai.OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    filter_keywords = ["ocr", "vl", "diff", "audio", "sovits", "video", "janus", "flux", "qvq", "mochi", "-en"]
    models = []
    try:
        for m in client.models.list():
            mid = m.id.lower()
            if not any(k in mid for k in filter_keywords):
                models.append(m.id)
        models.sort()
        for i, m in enumerate(models[:20]):
            print(f"  {i:2d}) {m}")
        if len(models) > 20:
            print(f"  ... and {len(models) - 20} more")
        print(f"\n...Or type any model name directly.")
    except Exception:
        print("  (Could not fetch model list. Type model name directly.)")

    while True:
        choice = input(f"{TerminalColor.GREEN_BOLD.value}>>>{TerminalColor.RESET.value} ").strip()
        try:
            if models and 0 <= int(choice) < len(models):
                config["main_model"] = models[int(choice)]
                config["fast_model"] = models[int(choice)]
                break
        except ValueError:
            pass
        if choice:
            config["main_model"] = choice
            config["fast_model"] = choice
            break


REQUIRED_KEYS = [
    "api_key", "base_url", "provider", "main_model",
    "target_lang", "source_lang_specified",
]


def validate_config(config):
    """验证配置，返回 (is_valid, errors)。

    规则：
    - 缺少必需 key
    - 存在 DEFAULT_CONFIG 中不存在的 key
    - 类型与 DEFAULT_CONFIG 不一致
    - provider 不在 PROVIDER_URLS 中
    - target_lang / source_lang 不在 LANG_MAP 中
    """
    errors = []

    # 检查缺少必需 key
    for key in REQUIRED_KEYS:
        if key not in config:
            errors.append(f"Missing required key: '{key}'")

    # 检查未知 key
    for key in config:
        if key not in DEFAULT_CONFIG:
            errors.append(f"Unknown key: '{key}'")

    # 检查类型和值
    for key, default in DEFAULT_CONFIG.items():
        if key not in config:
            continue
        value = config[key]
        if type(value) is not type(default) and value is not None and default is not None:
            errors.append(
                f"'{key}': expected {type(default).__name__}, got {type(value).__name__}"
            )
            continue

        if key == "provider" and value not in PROVIDER_URLS:
            errors.append(f"'{key}': '{value}' is not a valid provider")
        if key == "target_lang" and isinstance(value, str) and value and value not in LANG_MAP:
            errors.append(f"'{key}': '{value}' is not a supported language")
        if key == "source_lang" and isinstance(value, str) and value and value not in LANG_MAP:
            errors.append(f"'{key}': '{value}' is not a supported language")
        if key in ("main_model", "fast_model") and not isinstance(value, str):
            errors.append(f"'{key}': must be a string")

    return len(errors) == 0, errors


def save_config(config):
    valid, errors = validate_config(config)
    if not valid:
        print(f"{TerminalColor.RED.value}Config validation failed:{TerminalColor.RESET.value}")
        for e in errors:
            print(f"  - {e}")
        print("Config NOT saved.")
        return False

    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    get_history_dir().mkdir(parents=True, exist_ok=True)
    with open(get_config_path(), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return True
