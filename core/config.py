import json
import os

CONFIG_PATH = "config.json"

DEFAULT_CONFIG = {
    "allowed": "",
    "people": "",
    "areas": "",
    "lastmonth": ""
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)