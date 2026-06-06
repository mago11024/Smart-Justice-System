"""类案推送服务 — 基于关键词 + 语义向量相似度匹配"""
import math, re, logging
from typing import Optional
from sqlalchemy.orm import Session

from app import models
from app.services.ai.engine import get_embed_engine, AIEngine

logger = logging.getLogger("similar_cases")

# ── 中文分词（轻量级：基于字符 bigram + 关键词提取） ──

# 法律领域关键词权重表
LEGAL_KEYWORDS = {
    "借贷": 3.0, "借款": 3.0, "合同": 2.0, "纠纷": 1.0,
    "离婚": 3.0, "婚姻": 3.0, "继承": 3.0, "抚养": 3.0,
    "劳动": 3.0, "工伤": 3.0, "赔偿": 3.0, "人身损害": 3.0,
    "交通": 3.0, "事故": 3.0, "股权": 3.0, "转让": 2.5,
    "侵权": 3.0, "知识产权": 3.0, "商标": 3.0, "专利": 3.0,
    "金融": 3.0, "银行": 3.0, "保险": 3.0, "票据": 3.0,
    "房地产": 3.0, "租赁": 3.0, "物业": 3.0, "建筑": 3.0,
    "工程款": 3.0, "运输": 3.0, "物流": 3.0, "货运": 3.0,
    "债务": 3.0, "货款": 3.0, "追偿": 3.0, "担保": 3.0,
    "不正当竞争": 3.0, "垄断": 3.0, "消费者": 3.0,
    "土地": 3.0, "承包": 3.0, "村民": 3.0, "村委会": 3.0,
    "刑事": 3.0, "行政": 3.0, "民事": 1.0,
}


def _tokenize(text: str) -> dict[str, float]:
    """中文轻量分词 → {token: weight}"""
    text = text.lower().strip()
    tokens: dict[str, float] = {}

    # 1. 关键词加权匹配
    for kw, w in LEGAL_KEYWORDS.items():
        if kw in text:
            tokens[kw] = tokens.get(kw, 0) + w

    # 2. 单字权重 0.5（过滤标点/数字）
    for ch in text:
        if '一' <= ch <= '鿿':  # CJK 汉字
            tokens[ch] = tokens.get(ch, 0) + 0.5

    # 3. Bigram 权重 1.5
    chars = [c for c in text if '一' <= c <= '鿿']
    for i in range(len(chars) - 1):
        bigram = chars[i] + chars[i + 1]
        tokens[bigram] = tokens.get(bigram, 0) + 1.5

    return tokens


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _keyword_score(query_tokens: dict[str, float], doc_tokens: dict[str, float]) -> float:
    """关键词匹配得分 (0~1)"""
    if not query_tokens:
        return 0.0
    score = 0.0
    for token, qw in query_tokens.items():
        dw = doc_tokens.get(token, 0)
        if dw > 0:
            score += math.sqrt(qw * dw)
    # 归一化
    max_score = math.sqrt(sum(w * w for w in query_tokens.values()))
    if max_score == 0:
        return 0.0
    return min(score / max_score, 1.0)


# ── 主服务 ──

def _case_to_text(c: models.Case) -> str:
    """将案件转为搜索文本"""
    parts = [c.case_name]
    if c.plaintiff:
        parts.append(c.plaintiff)
    if c.defendant:
        parts.append(c.defendant)
    if c.cause_of_action:
        parts.append(c.cause_of_action)
    # 案由加权 — 重复添加以提升匹配权重
    if c.cause_of_action:
        parts.append(c.cause_of_action)
    return " ".join(parts)


async def search_similar_cases(
    query: str,
    db: Session,
    top_k: int = 5,
    min_score: float = 0.15,
    use_embedding: bool = True,
) -> list[dict]:
    """在已结/活跃案件中搜索与 query 最相似的案件。

    返回: [{case_id, case_name, plaintiff, defendant, cause_of_action,
             stage, stage_label, lawyer_name, score, match_type}, ...]
    按 score 降序排列。
    """
    # 1. 获取候选池：已结案件 + 活跃案件
    candidates = db.query(models.Case).filter(
        models.Case.is_archived == False
    ).all()

    if not candidates:
        return []

    # 2. 关键词评分（始终执行，作为基础分）
    query_tokens = _tokenize(query)
    doc_tokens_list = [_tokenize(_case_to_text(c)) for c in candidates]
    kw_scores = [_keyword_score(query_tokens, dt) for dt in doc_tokens_list]

    # 3. 如果有向量引擎，计算语义相似度
    embedding_scores = [0.0] * len(candidates)
    engine: Optional[AIEngine] = None

    if use_embedding:
        try:
            engine = get_embed_engine()
            if engine.supports_embedding:
                candidate_texts = [_case_to_text(c) for c in candidates]
                all_texts = [query] + candidate_texts
                embeddings = await engine.embed(all_texts)
                query_vec = embeddings[0]
                for i, vec in enumerate(embeddings[1:]):
                    embedding_scores[i] = _cosine_similarity(query_vec, vec)
        except NotImplementedError:
            logger.info("向量引擎不支持 embedding，使用纯关键词匹配")
        except Exception as e:
            logger.warning("向量检索失败，回退到关键词匹配: %s", e)

    # 4. 融合得分：向量分 × 0.6 + 关键词分 × 0.4
    has_embeddings = any(s > 0 for s in embedding_scores)
    scores = []
    for i, c in enumerate(candidates):
        if has_embeddings:
            final = embedding_scores[i] * 0.6 + kw_scores[i] * 0.4
            match_type = "semantic"
        else:
            final = kw_scores[i]
            match_type = "keyword"

        if final >= min_score:
            scores.append((i, final, match_type))

    scores.sort(key=lambda x: x[1], reverse=True)

    # 5. 组装结果
    results = []
    from app.services.case_service import case_to_dict

    for idx, score, match_type in scores[:top_k]:
        c = candidates[idx]
        results.append({
            **case_to_dict(c),
            "score": round(score, 4),
            "score_pct": round(score * 100),
            "match_type": match_type,
        })

    return results
