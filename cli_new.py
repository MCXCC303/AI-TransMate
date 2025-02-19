import os
import yaml
from pathlib import Path
import tempfile
import shutil
import subprocess

from numpy.lib.utils import source

from create_config import collect_lang

# 常量定义
CONFIG_FILE = "config.yaml"
PROMPT_DIR = "./prompt"

def display_config(file_path=CONFIG_FILE):
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".swp", text=True)
    try:
        with open(file_path, "r") as src, os.fdopen(tmp_fd, "w") as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(tmp_name, 0o444)
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
        subprocess.call([editor, tmp_name])
    finally:
        os.unlink(tmp_name)

class CommandProcessor:
    def __init__(self):
        self.config = self.load_config()
        self.command_map = {
            "bye": self.command_bye,
            "help": self.command_help,
            "?": self.command_help,
            "show": self.command_show,
            "model": self.command_model,
            "prov": self.command_prov,
            "role": self.command_role,
            "lang": self.command_lang,
            "switch": self.command_switch,
        }
        self.role_commands = {
            None: ["bye", "help", "?", "show", "model", "prov", "role"],
            "translate": ["lang", "switch"],
            "interface": ["lang"],
        }

    @staticmethod
    def load_config():
        """加载配置文件"""
        if not Path(CONFIG_FILE).exists():
            return {
                "api_key": "",
                "base_url": "",
                "model": "",
                "provider": "",
                "role": None,
            }
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f)

    def save_config(self):
        """保存配置到文件"""
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(self.config, f)

    def get_available_commands(self):
        """获取当前角色可用的命令列表"""
        base = self.role_commands[None]
        role = self.config.get("role")
        return base + self.role_commands.get(role, [])

    def parse_command(self, input_str):
        """解析并执行命令"""
        parts = input_str.strip().split(maxsplit=1)
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        if cmd not in self.command_map:
            print(f"Unknown Command {cmd}")
            return

        handler = self.command_map[cmd]

        # 参数数量验证
        if cmd in ["bye", "model", "prov", "role", "lang", "switch"]:
            if len(args) > 0:
                print(f"Command {cmd} doesn't accept arguments")
                return
        elif cmd == "show":
            if len(args) == 0:
                display_config()
                return
            required_args = 1
            if len(args) != required_args:
                print(f"Command {cmd} requires {required_args} argument")
                return
            if args[0] not in self.config:
                print(f"Invalid config parameter: {args[0]}")
                return

        handler(args)

    # 通用命令实现
    def command_bye(self, args):
        """退出命令"""
        print("Goodbye!")
        exit()

    def command_help(self, args):
        """帮助命令"""
        available_commands = self.get_available_commands()
        print("Available commands:")
        for cmd in available_commands:
            print(f"  {cmd}")

    def command_show(self, args):
        """显示配置参数"""
        param = args[0]
        print(f"Current {param}: {self.config.get(param, '')}")

    def command_role(self, args):
        """处理角色选择"""
        prompt_files = list(Path(PROMPT_DIR).glob("*.json"))
        options = [f.stem for f in prompt_files] + ["talk"]

        print("Available roles:")
        for i, opt in enumerate(options):
            print(f"{i}): {opt}")

        selection = input(">>> ").strip()

        try:
            # 尝试转换为数字选择
            index = int(selection)
            if 0 <= index < len(options):
                selected_role = options[index]
            else:
                raise ValueError
        except ValueError:
            # 按名称选择
            selected_role = selection if selection in options else None

        if not selected_role:
            print("Invalid selection")
            return

        if selected_role == "talk":
            self.config["role"] = None
        else:
            self.config["role"] = selected_role
            self.handle_role_specific_config(selected_role)

        self.save_config()

    def handle_role_specific_config(self, role):
        """处理角色特定的配置"""
        if role == "translate":
            source_lang, target_lang = collect_lang()
            self.config = {**self.config, 'source_lang': source_lang, 'target_lang': target_lang}
            self.save_config()
        elif role == "interface":
            self.command_lang_prog()

    # 角色特定命令
    def command_lang(self, args):
        """设置翻译语言"""
        # 实现具体的语言设置逻辑
        lang_support_list = []
        self.config.update({"source_lang": "en", "target_lang": "zh"})
        pass

    def command_lang_prog(self, args):
        """设置编程语言"""
        self.config["lang"] = "python"
        pass

    def command_switch(self, args):
        """切换翻译方向"""
        pass

    # 其他命令占位
    def command_model(self, args):
        pass

    def command_prov(self, args):
        pass

    def command_switch(self, args):
        pass


# 使用示例
if __name__ == "__main__":
    processor = CommandProcessor()
    while True:
        user_input=input('> ')
        processor.parse_command(user_input)
