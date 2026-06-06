"""AI 引擎抽象基类 + 工厂函数 — 支持 chat/embed 独立引擎"""
import os, json, logging
from abc import ABC, abstractmethod
from typing import Optional
from app.config_env import load_env_file

logger = logging.getLogger("ai_engine")
load_env_file()

# 引擎注册表
_registry: dict[str, type] = {}


def register(name: str):
    """装饰器：将引擎类注册到工厂"""
    def dec(cls):
        _registry[name] = cls
        return cls
    return dec


class AIEngine(ABC):
    """AI 引擎抽象接口。

    一个引擎可以实现 chat + embed 两者（如 Ollama），也可以只实现其一。
    上层业务代码通过 get_chat_engine() / get_embed_engine() 获取独立实例。
    """

    @abstractmethod
    async def chat(
        self, prompt: str, system: str = "",
        temperature: float = 0.1, max_tokens: int = 512,
    ) -> str:
        """纯文本生成"""
        ...

    async def chat_json(
        self, prompt: str, system: str = "",
        temperature: float = 0.1, max_tokens: int = 512,
    ) -> dict:
        """生成并解析 JSON 响应"""
        raw = await self.chat(prompt, system, temperature, max_tokens)
        try:
            js = raw.find("{")
            je = raw.rfind("}") + 1
            return json.loads(raw[js:je]) if js >= 0 else {}
        except json.JSONDecodeError:
            logger.warning("chat_json: JSON 解析失败, raw=%s", raw[:200])
            return {}

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """文本向量化。子类可重写；默认抛出 NotImplementedError"""
        raise NotImplementedError(f"{self.engine_name} 不支持向量化")

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """引擎标识名"""
        ...

    @property
    def supports_embedding(self) -> bool:
        """是否支持向量化。默认 False，子类可覆盖"""
        return False

    @property
    def model_name(self) -> str:
        return self._model_name

    def health_check(self) -> bool:
        return True


# ═══════════════════════════════════════════════════════════
# 双引擎工厂
# ═══════════════════════════════════════════════════════════

_chat_instance: Optional[AIEngine] = None
_chat_name: str = ""

_embed_instance: Optional[AIEngine] = None
_embed_name: str = ""


def _load_config_fallback() -> dict:
    """从 config.json 读取非敏感配置（env var 未设置时的回退）"""
    try:
        import json
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_chat_engine(name: str = "") -> AIEngine:
    """获取对话引擎（单例）。

    优先顺序: 参数 name > 环境变量 AI_CHAT_ENGINE > config.json ai.engine > 默认 'ollama'
    """
    global _chat_instance, _chat_name

    if not name:
        name = os.getenv("AI_CHAT_ENGINE", "") or os.getenv("AI_ENGINE", "")
        if not name:
            cfg = _load_config_fallback()
            name = cfg.get("ai", {}).get("engine", "ollama")
    name = name.lower().strip()

    if _chat_instance is not None and _chat_name == name:
        return _chat_instance

    cls = _resolve(name)
    _chat_instance = cls()
    _chat_name = name
    logger.info("对话引擎: %s (模型: %s)", _chat_instance.engine_name, _chat_instance.model_name)
    return _chat_instance


def get_embed_engine(name: str = "") -> AIEngine:
    """获取向量引擎（单例）。

    优先顺序: 参数 name > 环境变量 AI_EMBED_ENGINE > config.json ai.embed_engine > 默认 'ollama'
    """
    global _embed_instance, _embed_name

    if not name:
        name = os.getenv("AI_EMBED_ENGINE", "")
        if not name:
            cfg = _load_config_fallback()
            name = cfg.get("ai", {}).get("embed_engine", "ollama")
    name = name.lower().strip()

    if _embed_instance is not None and _embed_name == name:
        return _embed_instance

    cls = _resolve(name)
    inst = cls()
    if not inst.supports_embedding:
        logger.warning(
            "向量引擎 '%s' 不支持 embedding，类案推送将回退到纯关键词匹配。"
            " 建议设置 AI_EMBED_ENGINE=ollama 作为向量后端。",
            inst.engine_name,
        )
    _embed_instance = inst
    _embed_name = name
    logger.info("向量引擎: %s (模型: %s)", _embed_instance.engine_name, _embed_instance.model_name)
    return _embed_instance


def _resolve(name: str) -> type:
    """解析引擎名 → 类"""
    _auto_import_engines()
    cls = _registry.get(name)
    if cls is None:
        raise ValueError(
            f"未知 AI 引擎: '{name}'。可用引擎: {sorted(_registry.keys())}。"
        )
    return cls


# 兼容旧接口
def get_engine(name: str = "") -> AIEngine:
    """获取引擎（兼容旧代码，等同于 get_chat_engine）"""
    return get_chat_engine(name)


def list_engines() -> list[str]:
    """列出所有已注册的引擎名"""
    _auto_import_engines()
    return sorted(_registry.keys())


def flush_caches():
    """清除所有引擎缓存（配置变更后调用）"""
    global _chat_instance, _chat_name, _embed_instance, _embed_name
    _chat_instance = None
    _chat_name = ""
    _embed_instance = None
    _embed_name = ""


def _load_engine_config(engine_name: str) -> dict:
    """读取指定引擎的非敏感配置。密钥只从环境变量或 .env 读取。"""
    load_env_file()
    cfg = {}
    try:
        import json
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f).get("ai", {}).get(engine_name, {})
    except Exception:
        pass
    cfg.pop("api_key", None)
    return cfg


def _env_or_cfg(env_key: str, cfg: dict, cfg_key: str, default: str) -> str:
    """env var 优先，config.json 回退，最后 default"""
    val = os.getenv(env_key, "")
    if val:
        return val
    return cfg.get(cfg_key, default)


def _auto_import_engines():
    try:
        from . import ollama_engine  # noqa: F401
    except ImportError:
        pass
    try:
        from . import openai_engine  # noqa: F401
    except ImportError:
        pass
    try:
        from . import deepseek_engine  # noqa: F401
    except ImportError:
        pass
    try:
        from . import llamacpp_engine  # noqa: F401
    except ImportError:
        pass
