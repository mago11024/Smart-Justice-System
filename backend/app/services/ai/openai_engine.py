"""OpenAI 兼容引擎 — 对接 OpenAI / 兼容 API"""
import httpx
from .engine import AIEngine, register, _load_engine_config, _env_or_cfg


@register("openai")
class OpenAIEngine(AIEngine):
    def __init__(self):
        cfg = _load_engine_config("openai")
        self._base = _env_or_cfg("AI_OPENAI_BASE", cfg, "base_url", "https://api.openai.com/v1").rstrip("/")
        self._key = _env_or_cfg("AI_OPENAI_KEY", cfg, "api_key", "")
        self._model_name = _env_or_cfg("AI_OPENAI_MODEL", cfg, "model", "gpt-4o-mini")
        self._embed_model = _env_or_cfg("AI_OPENAI_EMBED_MODEL", cfg, "embed_model", "text-embedding-3-small")
        self._timeout = float(_env_or_cfg("AI_OPENAI_TIMEOUT", cfg, "timeout", "60"))

    @property
    def engine_name(self) -> str:
        return "openai"

    @property
    def supports_embedding(self) -> bool:
        return True

    @property
    def model_name(self) -> str:
        return self._model_name

    def _headers(self):
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    async def chat(self, prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 512) -> str:
        messages = []
        if system: messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/chat/completions", headers=self._headers(),
                json={"model": self._model_name, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/embeddings", headers=self._headers(),
                json={"model": self._embed_model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            data.sort(key=lambda x: x["index"])
            return [d["embedding"] for d in data]

    def health_check(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self._base}/models")
            req.add_header("Authorization", f"Bearer {self._key}")
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False
