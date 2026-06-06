"""AI 引擎工厂 — 可插拔的 AI 后端

使用方式:
    from app.services.ai import get_chat_engine, get_embed_engine

    chat = get_chat_engine()          # 对话引擎（默认 ollama）
    embed = get_embed_engine()        # 向量引擎（默认 ollama）

    # DeepSeek + Ollama 混合
    # 设置环境变量: AI_CHAT_ENGINE=deepseek  AI_EMBED_ENGINE=ollama

配置 (环境变量):
    AI_CHAT_ENGINE=ollama|openai|deepseek
    AI_EMBED_ENGINE=ollama|openai       # 向量引擎独立设置

    # Ollama
    AI_OLLAMA_BASE=http://localhost:11434
    AI_OLLAMA_MODEL=qwen2.5:7b
    AI_OLLAMA_EMBED_MODEL=nomic-embed-text

    # OpenAI
    AI_OPENAI_KEY=sk-...
    AI_OPENAI_MODEL=gpt-4o-mini

    # DeepSeek (仅对话，无 embedding)
    AI_DEEPSEEK_KEY=sk-...
    AI_DEEPSEEK_MODEL=deepseek-chat
"""
from .engine import AIEngine, get_engine, get_chat_engine, get_embed_engine, list_engines, flush_caches

__all__ = [
    "AIEngine",
    "get_engine",        # 兼容旧代码
    "get_chat_engine",
    "get_embed_engine",
    "list_engines",
    "flush_caches",
]
