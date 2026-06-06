"""设置路由：读取/写入 JSON 配置文件"""
import json, os, logging
from copy import deepcopy
from fastapi import APIRouter

logger = logging.getLogger("settings")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")

# 需要脱敏的字段路径 (JSON key path)
SENSITIVE_KEYS = {
    ("ai", "openai", "api_key"),
    ("ai", "deepseek", "api_key"),
    ("paddleocr", "token"),
}
MASK = "***"

DEFAULT_CONFIG = {
    "ai": {
        "engine": "ollama",
        "embed_engine": "ollama",
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "qwen2.5:7b",
            "embed_model": "nomic-embed-text",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-4o-mini",
            "embed_model": "text-embedding-3-small",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat",
        },
        "llamacpp": {
            "base_url": "http://localhost:8080/v1",
            "model": "qwen2.5-7b",
        },
        "timeout": 120,
    },
    "display": {
        "theme": "auto",
        "sidebar_default": "expanded",
        "language": "zh-CN",
    },
    "notification": {
        "enabled": True,
        "overdue_alert": True,
        "due_soon_alert": True,
        "court_reminder": True,
        "auto_refresh_minutes": 30,
    },
    "paddleocr": {
        "token": "",
        "model": "PP-OCRv5",
    },
}

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        _save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except Exception:
        logger.warning("配置文件损坏，使用默认配置")
        return deepcopy(DEFAULT_CONFIG)

    merged = deepcopy(DEFAULT_CONFIG)
    _deep_merge(merged, saved)
    return merged


def _save_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _deep_merge(base: dict, override: dict):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _mask_secrets(config: dict) -> dict:
    """返回脱敏后的配置副本，密钥字段替换为 ***"""
    masked = deepcopy(config)
    for path in SENSITIVE_KEYS:
        d = masked
        for key in path[:-1]:
            d = d.setdefault(key, {})
        if d.get(path[-1], ""):
            d[path[-1]] = MASK
    return masked


def _filter_empty_keys(data: dict, disk_config: dict):
    """移除 data 中值为 '' 的敏感字段，防止空值覆盖已有密钥"""
    for path in SENSITIVE_KEYS:
        d = data
        disk_d = disk_config
        try:
            for key in path[:-1]:
                d = d[key]
                disk_d = disk_d.get(key, {})
            if d.get(path[-1], "") == "" or d.get(path[-1], None) == MASK:
                # 恢复为磁盘上的值
                d[path[-1]] = disk_d.get(path[-1], "")
        except (KeyError, TypeError):
            pass


def _sync_env(config: dict):
    """将配置文件同步到环境变量，使引擎工厂生效"""
    ai = config.get("ai", {})

    chat_name = ai.get("engine", "ollama")
    os.environ["AI_CHAT_ENGINE"] = chat_name
    os.environ["AI_ENGINE"] = chat_name

    embed_name = ai.get("embed_engine", "ollama")
    os.environ["AI_EMBED_ENGINE"] = embed_name

    for eng_name in ("ollama", "openai", "deepseek", "llamacpp"):
        cfg = ai.get(eng_name, {})
        if eng_name == "ollama":
            os.environ["AI_OLLAMA_BASE"] = cfg.get("base_url", "http://localhost:11434")
            os.environ["AI_OLLAMA_MODEL"] = cfg.get("model", "qwen2.5:7b")
            os.environ["AI_OLLAMA_EMBED_MODEL"] = cfg.get("embed_model", "nomic-embed-text")
        elif eng_name == "openai":
            os.environ["AI_OPENAI_BASE"] = cfg.get("base_url", "")
            os.environ["AI_OPENAI_KEY"] = cfg.get("api_key", "")
            os.environ["AI_OPENAI_MODEL"] = cfg.get("model", "gpt-4o-mini")
            os.environ["AI_OPENAI_EMBED_MODEL"] = cfg.get("embed_model", "text-embedding-3-small")
        elif eng_name == "deepseek":
            os.environ["AI_DEEPSEEK_BASE"] = cfg.get("base_url", "https://api.deepseek.com/v1")
            os.environ["AI_DEEPSEEK_KEY"] = cfg.get("api_key", "")
            os.environ["AI_DEEPSEEK_MODEL"] = cfg.get("model", "deepseek-chat")
        elif eng_name == "llamacpp":
            os.environ["AI_LLAMACPP_BASE"] = cfg.get("base_url", "http://localhost:8080/v1")
            os.environ["AI_LLAMACPP_MODEL"] = cfg.get("model", "qwen2.5-7b")

    os.environ["AI_OLLAMA_TIMEOUT"] = str(ai.get("timeout", 120))
    os.environ["AI_OPENAI_TIMEOUT"] = str(ai.get("timeout", 120))
    os.environ["AI_DEEPSEEK_TIMEOUT"] = str(ai.get("timeout", 120))
    os.environ["AI_LLAMACPP_TIMEOUT"] = str(ai.get("timeout", 120))

    # PaddleOCR
    po = config.get("paddleocr", {})
    os.environ["PADDLEOCR_TOKEN"] = po.get("token", "")


@router.get("")
def get_settings():
    """返回脱敏后的配置"""
    config = _load_config()
    return _mask_secrets(config)


@router.put("")
def update_settings(data: dict):
    """更新配置。空密钥不覆盖已有值。返回脱敏后的配置。"""
    current = _load_config()

    # 空值/MASK 不覆盖已有密钥
    _filter_empty_keys(data, current)

    _deep_merge(current, data)
    _save_config(current)
    _sync_env(current)

    from app.services.ai import flush_caches
    flush_caches()

    return {"ok": True, "config": _mask_secrets(current)}


@router.post("/reset")
def reset_settings():
    _save_config(DEFAULT_CONFIG)
    _sync_env(DEFAULT_CONFIG)
    from app.services.ai import flush_caches
    flush_caches()
    return {"ok": True, "config": _mask_secrets(DEFAULT_CONFIG)}
