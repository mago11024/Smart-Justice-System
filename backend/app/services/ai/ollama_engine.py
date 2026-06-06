"""Ollama 引擎 — 本地部署，免 API Key，支持 chat+embed"""
import httpx
from .engine import AIEngine, register, _load_engine_config, _env_or_cfg


@register("ollama")
class OllamaEngine(AIEngine):
    def __init__(self):
        cfg = _load_engine_config("ollama")
        self._base = _env_or_cfg("AI_OLLAMA_BASE", cfg, "base_url", "http://localhost:11434").rstrip("/")
        self._model_name = _env_or_cfg("AI_OLLAMA_MODEL", cfg, "model", "qwen2.5:7b")
        self._embed_model = _env_or_cfg("AI_OLLAMA_EMBED_MODEL", cfg, "embed_model", "nomic-embed-text")
        self._timeout = float(_env_or_cfg("AI_OLLAMA_TIMEOUT", cfg, "timeout", "120"))

    @property
    def engine_name(self) -> str:
        return "ollama"

    @property
    def supports_embedding(self) -> bool:
        return True

    @property
    def model_name(self) -> str:
        return self._model_name

    async def chat(self, prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 512) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/api/generate",
                json={"model": self._model_name, "prompt": full_prompt, "stream": False,
                      "options": {"temperature": temperature, "num_predict": max_tokens}},
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for text in texts:
                resp = await client.post(
                    f"{self._base}/api/embeddings",
                    json={"model": self._embed_model, "prompt": text},
                )
                resp.raise_for_status()
                vectors.append(resp.json().get("embedding", []))
        return vectors

    def health_check(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(f"{self._base}/api/tags", timeout=3)
            return True
        except Exception:
            return False
