"""DeepSeek 引擎 — 对话专用，不支持向量化"""
import logging
import httpx
from .engine import AIEngine, register, _load_engine_config, _env_or_cfg

logger = logging.getLogger("deepseek_engine")


@register("deepseek")
class DeepSeekEngine(AIEngine):
    def __init__(self):
        cfg = _load_engine_config("deepseek")
        self._base = _env_or_cfg("AI_DEEPSEEK_BASE", cfg, "base_url", "https://api.deepseek.com/v1").rstrip("/")
        self._key = _env_or_cfg("AI_DEEPSEEK_KEY", cfg, "api_key", "")
        self._model_name = _env_or_cfg("AI_DEEPSEEK_MODEL", cfg, "model", "deepseek-chat")

    @property
    def engine_name(self) -> str:
        return "deepseek"

    @property
    def supports_embedding(self) -> bool:
        return False

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def _is_reasoning_model(self) -> bool:
        return any(tag in self._model_name.lower() for tag in ("reasoner", "v4-pro", "r1-", "-r1"))

    async def chat(self, prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 512) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self._model_name,
            "messages": messages,
        }
        if self._is_reasoning_model:
            # 推理模型：不支持 temperature，给足 token 让思考能收敛
            body["max_tokens"] = max(max_tokens, 10000)
        else:
            body["temperature"] = temperature
            body["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self._base}/chat/completions",
                headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
            choice = resp.json()["choices"][0]["message"]
            content = (choice.get("content") or "").strip()

        # 推理模型：如果 content 空但用完了 tokens，可能是 token 不够，
        # 打印警告方便排查
        if self._is_reasoning_model and not content:
            logger.warning(
                "推理模型 content 为空（model=%s tokens_left=%s），raw=%s",
                self._model_name,
                choice.get("finish_reason", "?"),
                (choice.get("reasoning_content") or "")[:200],
            )

        return content

    def health_check(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self._base}/models")
            req.add_header("Authorization", f"Bearer {self._key}")
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False
