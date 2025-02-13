import json
import os
from glob import glob


def merge_and_complement_json_files(provider_dir:str):
    file_data = []
    all_keys = set()

    for file_path in glob(os.path.join(provider_dir, "*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            file_data.append((file_path, data))
            all_keys.update(data.keys())

    for file_path, data in file_data:
        for key in all_keys:
            if key not in data:
                data[key] = None
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    merge_and_complement_json_files(provider_dir='providers')