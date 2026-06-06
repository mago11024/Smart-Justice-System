"""AI 能力路由：类案推送、引擎状态"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.ai.similar_cases import search_similar_cases
from app.services.ai.engine import get_chat_engine, get_embed_engine, list_engines, flush_caches

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/similar-cases")
async def similar_cases(
    q: str = Query(..., description="搜索关键词（案由/事实描述）"),
    top_k: int = Query(5, ge=1, le=20),
    min_score: float = Query(0.15, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """类案推送：输入案由或案情描述，返回最相似的历史案件"""
    results = await search_similar_cases(
        query=q, db=db, top_k=top_k, min_score=min_score, use_embedding=True,
    )
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.get("/engines")
def list_ai_engines():
    """列出所有已注册引擎 + 当前 chat/embed 引擎状态"""
    engine_names = list_engines()

    # 对话引擎
    try:
        chat = get_chat_engine()
        chat_name = chat.engine_name
        chat_model = chat.model_name
        chat_healthy = chat.health_check()
        chat_has_embed = chat.supports_embedding
    except Exception:
        chat_name = "unknown"
        chat_model = "unknown"
        chat_healthy = False
        chat_has_embed = False

    # 向量引擎
    try:
        embed = get_embed_engine()
        embed_name = embed.engine_name
        embed_model = embed.model_name
        embed_healthy = embed.health_check() if embed.supports_embedding else False
        embed_available = embed.supports_embedding
    except Exception:
        embed_name = "unknown"
        embed_model = "unknown"
        embed_healthy = False
        embed_available = False

    return {
        "engines": engine_names,
        "current": chat_name,
        "model": chat_model,
        "healthy": chat_healthy,
        "has_embed": chat_has_embed,
        "embed_engine": embed_name,
        "embed_model": embed_model,
        "embed_healthy": embed_healthy,
        "embed_available": embed_available,
    }


@router.post("/engines/switch")
def switch_engine(data: dict):
    """运行时切换 AI 引擎"""
    name = data.get("engine", "ollama")
    import os
    os.environ["AI_ENGINE"] = name
    os.environ["AI_CHAT_ENGINE"] = name
    flush_caches()

    try:
        chat = get_chat_engine()
        embed = get_embed_engine()
        return {
            "ok": True,
            "engine": chat.engine_name,
            "model": chat.model_name,
            "healthy": chat.health_check(),
            "embed_engine": embed.engine_name,
            "embed_available": embed.supports_embedding,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
