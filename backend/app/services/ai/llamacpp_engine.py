"""llama.cpp Server 引擎 — 本地 OpenAI 兼容服务"""
import httpx
from .engine import AIEngine, register, _load_engine_config, _env_or_cfg


@register("llamacpp")
class LlamaCppEngine(AIEngine):
    def __init__(self):
        cfg = _load_engine_config("llamacpp")
        self._base = _env_or_cfg("AI_LLAMACPP_BASE", cfg, "base_url", "http://localhost:8080/v1").rstrip("/")
        self._model_name = _env_or_cfg("AI_LLAMACPP_MODEL", cfg, "model", "qwen2.5-7b")
        self._timeout = float(_env_or_cfg("AI_LLAMACPP_TIMEOUT", cfg, "timeout", "120"))

    @property
    def engine_name(self) -> str:
        return "llamacpp"

    @property
    def supports_embedding(self) -> bool:
        return False

    @property
    def model_name(self) -> str:
        return self._model_name

    async def chat(self, prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 512) -> str:
        messages = []
        if system: messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={"model": self._model_name, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    def health_check(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(f"{self._base}/models", timeout=3)
            return True
        except Exception:
            return False
