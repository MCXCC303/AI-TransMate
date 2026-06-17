import json
import os
import shutil
import sys
from pathlib import Path

import openai
import yaml

from .ansi_chars import TerminalColor

PROVIDER_URLS = {
    "ALIYUN": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "DEEPSEEK": "https://api.deepseek.com/v1",
    "SILICONFLOW": "https://api.siliconflow.cn/v1",
    "OPENAI": "https://api.openai.com/v1",
    "TENCENT": "https://api.lkeap.cloud.tencent.com/v1",
    "VOLCE": "https://ark.cn-beijing.volces.com/api/v3",
}

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.deepseek.com/v1",
    "provider": "DEEPSEEK",
    "main_model": "deepseek-chat",
    "fast_model": "deepseek-chat",
    "target_lang": "Chinese",
    "source_lang_specified": False,
    "source_lang": None,
    "vi_mode": True,
    "context_optimization": True,
}

LANG_MAP = {
    "Afrikaans": "南非荷兰语", "Arabic": "阿拉伯语", "Bengali": "孟加拉语",
    "Bulgarian": "保加利亚语", "Catalan": "加泰罗尼亚语", "Chinese": "中文",
    "Croatian": "克罗地亚语", "Czech": "捷克语", "Danish": "丹麦语",
    "Dutch": "荷兰语", "English": "英语", "Estonian": "爱沙尼亚语",
    "Finnish": "芬兰语", "French": "法语", "German": "德语",
    "Greek": "希腊语", "Hebrew": "希伯来语", "Hindi": "印地语",
    "Hungarian": "匈牙利语", "Icelandic": "冰岛语", "Indonesian": "印度尼西亚语",
    "Italian": "意大利语", "Japanese": "日语", "Korean": "韩语",
    "Latvian": "拉脱维亚语", "Lithuanian": "立陶宛语", "Malay": "马来语",
    "Norwegian": "挪威语", "Persian": "波斯语", "Polish": "波兰语",
    "Portuguese": "葡萄牙语", "Punjabi": "旁遮普语", "Romanian": "罗马尼亚语",
    "Russian": "俄语", "Serbian": "塞尔维亚语", "Slovak": "斯洛伐克语",
    "Slovenian": "斯洛文尼亚语", "Spanish": "西班牙语", "Swahili": "斯瓦希里语",
    "Swedish": "瑞典语", "Tamil": "泰米尔语", "Telugu": "泰卢固语",
    "Thai": "泰语", "Turkish": "土耳其语", "Ukrainian": "乌克兰语",
    "Urdu": "乌尔都语", "Vietnamese": "越南语", "Welsh": "威尔士语",
    "Zulu": "祖鲁语",
}


def get_config_dir():
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(xdg) / "transmate"


def get_config_path():
    return get_config_dir() / "config.json"


def get_history_dir():
    return get_config_dir() / "history"


def load_config():
    config_dir = get_config_dir()
    config_path = get_config_path()

    if not config_path.exists():
        return _init_config(config_dir, config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value

    return config


def _init_config(config_dir, config_path):
    old_yaml = Path("config.yaml")
    if old_yaml.exists():
        print(f"{TerminalColor.YELLOW.value}Migrating old config.yaml to {config_path}{TerminalColor.RESET.value}")
        return _migrate_from_yaml(config_dir, config_path, old_yaml)

    config_dir.mkdir(parents=True, exist_ok=True)
    get_history_dir().mkdir(parents=True, exist_ok=True)

    config = dict(DEFAULT_CONFIG)
    _interactive_setup(config)
    save_config(config)
    return config


def _migrate_from_yaml(config_dir, config_path, old_yaml):
    with open(old_yaml, "r", encoding="utf-8") as f:
        old = yaml.safe_load(f)

    config_dir.mkdir(parents=True, exist_ok=True)
    get_history_dir().mkdir(parents=True, exist_ok=True)

    config = dict(DEFAULT_CONFIG)
    if "api_key" in old:
        config["api_key"] = old["api_key"]
    if "base_url" in old:
        config["base_url"] = old["base_url"]
    if "provider" in old:
        config["provider"] = old["provider"]
    if "model" in old:
        config["main_model"] = old["model"]
        config["fast_model"] = old["model"]
    if "target_lang" in old:
        config["target_lang"] = LANG_MAP.get(old["target_lang"], old["target_lang"])
    if "source_lang" in old:
        config["source_lang"] = LANG_MAP.get(old["source_lang"], old["source_lang"])
        config["source_lang_specified"] = True

    save_config(config)
    print(f"{TerminalColor.GREEN.value}Config migrated to {config_path}{TerminalColor.RESET.value}")
    return config


def _interactive_setup(config):
    print("Welcome to AI TransMate! Let's set up your configuration.\n")

    import getpass

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

    while True:
        try:
            config["api_key"] = getpass.getpass(f"Enter your API key for {config['provider']}: ")
            sys.stdout.write("\033[1A\033[2K\nVerifying API key...\n")
            client = openai.OpenAI(api_key=config["api_key"], base_url=config["base_url"])
            try:
                client.models.list()
            except openai.NotFoundError:
                pass
            break
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            raise
        except openai.AuthenticationError:
            print("Invalid API key. Try again.")

    print(f"{TerminalColor.GREEN.value}Authentication succeeded.{TerminalColor.RESET.value}\n")

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

    _collect_model(config)

    print(f"\n{TerminalColor.GREEN.value}Setup complete! Configuration saved.{TerminalColor.RESET.value}")


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
        print(f"\n  Or type any model name directly.")
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


def migrate_history():
    old_history = Path("history")
    new_history = get_history_dir()
    if old_history.exists() and old_history.is_dir():
        for f in old_history.iterdir():
            if f.is_file():
                shutil.copy2(f, new_history / f.name)
        print(f"{TerminalColor.GREEN.value}History migrated to {new_history}{TerminalColor.RESET.value}")
