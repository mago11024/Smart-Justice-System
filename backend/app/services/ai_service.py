"""AI 文档分析服务 — 通过引擎工厂调用 AI 后端"""
import json, logging
from app.services.ai.engine import get_engine
from app.services.desensitizer import fast_desensitize

logger = logging.getLogger("ai_service")

SYSTEM_PROMPT = """你是资深法律案件分析师。阅读以下法律文档，提取可识别信息并以严格JSON返回。

## 输出字段

{
  "document_type": "起诉状|答辩状|判决书|裁定书|调解书|开庭传票|证据清单|代理词|上诉状|申请书|告知书|合同|其他",
  "plaintiff": "原告/申请人/公诉机关，多个用、分隔，无则null",
  "defendant": "被告/被申请人，多个用、分隔，无则null",
  "third_party": "第三人，无则null",
  "plaintiff_agent": "原告代理律师/律所，无则null",
  "defendant_agent": "被告代理律师/律所，无则null",
  "cause_of_action": "案由如民间借贷纠纷，无则null",
  "court": "受理法院全称，无则null",
  "judge": "审判员/审判长姓名，无则null",
  "case_number": "案号如(2025)沪0105民初1234号，无则null",
  "amount_in_dispute": "标的金额元纯数字如500000，无则null",
  "stage": "consultation|document_prep|court_appearance|awaiting_result|closed",
  "deadline": "举证/答辩/上诉截止日YYYY-MM-DD，无则null",
  "court_date": "开庭日期YYYY-MM-DDTHH:MM，无则null",
  "courtroom": "法庭编号如第三法庭，无则null",
  "key_facts": "案情摘要3-5句话，无则null",
  "next_action": "下一步应做事项建议，无则null",
  "urgency": "high|medium|low",
  "confidence": 0.0-1.0
}

## 规则

1. 起诉状/立案通知书→consultation；证据清单/答辩状→document_prep；开庭传票/出庭通知→court_appearance；庭审后至宣判→awaiting_result；生效判决/裁定/调解书→closed
2. 标的金额统一为元。只提取明确标注的日期(非落款日期)
3. 信息缺失填null，不要编造
4. 只返回JSON，不要```json```包裹，不要解释"""

MATCH_PROMPT = """你是律师事务所的案件匹配系统。一份新文档刚刚被扫描上传，AI 已提取了结构化信息。现在需要判断这份文档归属于系统中哪个已有案件。

## 新文档信息

{extracted}

## 系统中已有案件（候选池）

{cases}

## 匹配规则（按优先级）

1. **案号精确匹配** — 如果文档的 case_number 与某个案件完全一致 → matched_id = 该案件ID, confidence ≥ 0.98
2. **当事人高度重合** — 原告和被告名称与某个案件一致或近似（允许简称/全称差异，如"某科技公司" vs"某科技有限公司"）→ confidence ≥ 0.85
3. **当事人部分重合 + 案由一致** — 仅一方当事人匹配，但案由相同 → confidence 0.5~0.8
4. **仅案由或事实描述相似** — 没有当事人匹配，但案由/关键事实与某个案件高度相关 → confidence 0.3~0.5
5. **完全无匹配** — 以上都不满足 → matched_id = null, confidence = 0

## 返回格式

{{
  "matched_id": 案件ID（整数）或 null,
  "confidence": 0.0-1.0,
  "reason": "匹配理由，说明判断依据（当事人重合/案由一致/案号匹配等）",
  "suggestion": "如果 confidence < 0.5，给出一句话建议，如'建议创建新案件，案由为民间借贷纠纷'"
}}

## 重要

- 只返回 JSON，不要 Markdown 代码块。
- 宁可保守（null），不要强行匹配错误案件。"""


async def analyze_document(text_content: str) -> dict:
    """调用 AI 引擎分析文档，返回结构化提取结果"""
    # 快速脱敏：仅正则匹配（< 0.1s），跳过 jieba 分词
    text_content = fast_desensitize(text_content)
    # 截取前 15K 字符，足够覆盖法律文档核心内容
    prompt = f"## 待分析的法律文档\n\n{text_content[:15000]}"

    try:
        engine = get_engine()
        parsed = await engine.chat_json(prompt, SYSTEM_PROMPT, temperature=0.05, max_tokens=2000)
        if not parsed:
            return {"success": False, "raw": "", "error": "AI 返回为空或解析失败"}

        return {
            "success": True,
            "document_type": parsed.get("document_type"),
            "stage": parsed.get("stage"),
            "plaintiff": parsed.get("plaintiff"),
            "defendant": parsed.get("defendant"),
            "third_party": parsed.get("third_party"),
            "plaintiff_agent": parsed.get("plaintiff_agent"),
            "defendant_agent": parsed.get("defendant_agent"),
            "cause_of_action": parsed.get("cause_of_action"),
            "court": parsed.get("court"),
            "judge": parsed.get("judge"),
            "case_number": parsed.get("case_number"),
            "amount_in_dispute": parsed.get("amount_in_dispute"),
            "deadline": parsed.get("deadline"),
            "court_date": parsed.get("court_date"),
            "courtroom": parsed.get("courtroom"),
            "key_facts": parsed.get("key_facts"),
            "next_action": parsed.get("next_action"),
            "urgency": parsed.get("urgency"),
            "confidence": parsed.get("confidence", 0.0),
            "raw": json.dumps(parsed, ensure_ascii=False),
        }
    except Exception as e:
        logger.exception("analyze_document 失败")
        return {"success": False, "raw": "", "error": f"AI 引擎调用失败: {str(e)}"}


async def match_to_case(extracted: dict, cases: list[dict]) -> dict:
    """将文档提取信息与已有案件匹配"""
    # 构造更丰富的候选描述：加上案号和阶段
    cases_lines = []
    for c in cases[:40]:
        parts = [
            f"ID:{c['id']}",
            f"案件:{c['case_name']}",
            f"原告:{c.get('plaintiff', '')}",
            f"被告:{c.get('defendant', '')}",
            f"案由:{c.get('cause_of_action', '')}",
        ]
        if c.get("case_number"):
            parts.append(f"案号:{c['case_number']}")
        if c.get("stage"):
            parts.append(f"阶段:{c.get('stage', '')}")
        cases_lines.append(" | ".join(parts))

    cases_text = "\n".join(cases_lines)
    # 快速脱敏：仅正则匹配
    cases_text = fast_desensitize(cases_text)
    extracted_text = json.dumps(extracted, ensure_ascii=False)
    prompt = MATCH_PROMPT.format(extracted=extracted_text, cases=cases_text)

    try:
        engine = get_engine()
        parsed = await engine.chat_json(prompt, temperature=0.05, max_tokens=512)
        if not parsed:
            return {"matched_id": None, "confidence": 0.0, "reason": "AI 返回解析失败"}
        return parsed
    except Exception as e:
        logger.exception("match_to_case 失败")
        return {"matched_id": None, "confidence": 0.0, "reason": str(e)}


def extract_text(file_path: str, ext: str) -> str:
    """从 PDF/DOCX/TXT/图片 提取文本

    PDF 优先用 PyPDF2 读文字层，空则回退 PaddleOCR。
    """
    ext = ext.lower().lstrip(".")
    if ext == "txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == "pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        if len(text) < 20:
            logger.info("PDF 文字层为空，启用 PaddleOCR: %s", file_path)
            from app.services.ocr_service import ocr_pdf
            ocr_text = ocr_pdf(file_path)
            if ocr_text.strip():
                text = ocr_text
        return text
    elif ext in ("docx", "doc"):
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    elif ext in ("png", "jpg", "jpeg", "tiff", "bmp", "webp"):
        from app.services.ocr_service import ocr_pdf
        return ocr_pdf(file_path)
    else:
        return ""
