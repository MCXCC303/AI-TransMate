import os
import glob
from enum import Enum


def load_api_keys(dir="api_keys"):
    key_data = {}
    for filepath in glob.glob(os.path.join(dir, "*.key")):
        filename = os.path.basename(filepath)
        service_name = os.path.splitext(filename)[0]
        with open(filepath, "r") as f:
            key_value = f.read().strip()
        key_data[service_name] = key_value
    return Enum("APIKeys", key_data.items())
