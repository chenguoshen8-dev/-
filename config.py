import json, os

CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'claude_pet_cfg.json')

DEFAULT_CFG = {
    "active_api": 0,
    "apis": [
        {"name": "API 1", "url": "", "key": "", "model": ""},
        {"name": "API 2", "url": "", "key": "", "model": ""},
        {"name": "API 3", "url": "", "key": "", "model": ""},
    ],
    "pet_size": 3,
    "topmost": True,
}


def load_cfg():
    try:
        with open(CFG_FILE, encoding='utf-8') as f:
            d = json.load(f)
            return {**DEFAULT_CFG, **d}
    except Exception:
        return dict(DEFAULT_CFG)


def save_cfg(cfg):
    with open(CFG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
