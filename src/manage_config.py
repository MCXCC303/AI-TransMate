import os

import yaml

class ConfigManager:
    def __init__(self, command: str, args: list[str], config_file='./config.yaml'):
        if not os.path.exists(config_file):
            return
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.config = config
        self.role = config['role']
        self.provider = config['provider']
        if self.provider == 'LOCAL':
            self.base_url = config['base_url']
            self.api_key = config['api_key']
        self.model = config['model']
