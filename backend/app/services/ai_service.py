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


EVIDENCE_CATALOG_PROMPT = """你是资深法律案件分析师。基于给定的案件基本信息以及已上传证据材料的AI提取/原始文本，为提交人整理一份可直接提交法院的证据目录，以严格JSON返回。

## 案件基本信息
{case_info}

## 已上传文档详情
{doc_summaries}

## 输出字段

{{
  "submitter_role": "提交人的诉讼地位，如原告、被告、第三人、申请执行人等",
  "evidence_list": [
    {{
      "index": 1,
      "name": "证据名称。要具体，包含文书编号/日期/签署方等关键标识。例如：'编号GF-2000-0171《商品房买卖合同》（2013年2月签订）'",
      "proof_content": "证明内容：用一句话说明该份证据用来证明什么事实。例如：'证明原被告之间存在商品房买卖合同关系'",
      "type": "书证|物证|证人证言|视听资料|电子数据|鉴定意见|勘验笔录|当事人陈述"
    }},
    ...
  ]
}}

## 规则

1. submitter_role 从案件材料中判断提交方诉讼地位。
2. evidence_list 按证明逻辑排序，每组证据（如合同类、付款类、判决类、程序类）放在一起。通常5-15条。
3. 证据名称必须从文档材料中提取，不可凭空编造。若有合同编号、签订日期、当事人姓名等细节，务必写进名称中。
4. proof_content 必须指向具体的待证事实，每条证明内容是一个完整陈述句。
5. type 根据证据形式判断，默认为'书证'。
6. 如果文档材料不足，基于已有信息尽力填充，但不要编造不存在的证据。
7. 只返回JSON，不要```json```包裹，不要解释。"""

EVIDENCE_CATALOG_PROMPT_NO_DOCS = """你是资深法律案件分析师。基于给定的案件基本信息，为该案件整理一份证据清单框架，以严格JSON返回。

## 案件基本信息
{case_info}

## 输出字段

{{
  "submitter_role": "提交人的诉讼地位",
  "evidence_list": [
    {{
      "index": 1,
      "name": "证据名称",
      "proof_content": "证明内容",
      "type": "书证"
    }}
  ]
}}

## 规则

1. 基于案由和当事人信息，推测该类型案件通常需要哪些关键证据。
2. 证据名称先给通用描述（如'《xx合同》'），留待律师补充细节。
3. 证明内容指向该类案件的要件事实。
4. 每类证据一条，控制在5-8条，不要过度推测。
5. 只返回JSON，不要```json```包裹，不要解释。"""


async def generate_core_summary(case_data: dict, doc_summaries: list[dict]) -> dict:
    """调用AI引擎，综合案件信息与文档分析结果，生成证据目录"""
    case_info = json.dumps({
        "案件名称": case_data.get("case_name", ""),
        "案号": case_data.get("case_number", ""),
        "原告": case_data.get("plaintiff", ""),
        "被告": case_data.get("defendant", ""),
        "案由": case_data.get("cause_of_action", ""),
        "当前阶段": case_data.get("stage_label", case_data.get("stage", "")),
        "备注": case_data.get("notes", ""),
    }, ensure_ascii=False, indent=2)

    docs_text = ""
    for i, d in enumerate(doc_summaries[:15], 1):
        parts = [f"文档{i}: {d.get('filename', '')}"]
        if d.get("ai_extracted_stage"):
            parts.append(f"  阶段: {d['ai_extracted_stage']}")
        if d.get("ai_extracted_cause"):
            parts.append(f"  案由: {d['ai_extracted_cause']}")
        try:
            parties = json.loads(d.get("ai_extracted_parties", "{}"))
            if parties.get("plaintiff"):
                parts.append(f"  原告: {parties['plaintiff']}")
            if parties.get("defendant"):
                parts.append(f"  被告: {parties['defendant']}")
        except Exception:
            pass
        if d.get("ai_raw_response"):
            try:
                raw = json.loads(d["ai_raw_response"])
                if raw.get("key_facts"):
                    parts.append(f"  关键事实: {raw['key_facts']}")
                if raw.get("document_type"):
                    parts.append(f"  文书类型: {raw['document_type']}")
                if raw.get("next_action"):
                    parts.append(f"  建议: {raw['next_action']}")
            except Exception:
                pass
        docs_text += "\n".join(parts) + "\n\n"

    if docs_text.strip():
        prompt = EVIDENCE_CATALOG_PROMPT.format(case_info=case_info, doc_summaries=docs_text)
    else:
        prompt = EVIDENCE_CATALOG_PROMPT_NO_DOCS.format(case_info=case_info)

    try:
        engine = get_engine()
        result = await engine.chat_json(prompt, temperature=0.1, max_tokens=2000)
        if not result:
            return {"success": False, "error": "AI 返回为空或解析失败"}
        # 确保每条有 index
        if result.get("evidence_list"):
            for idx, item in enumerate(result["evidence_list"], 1):
                if "index" not in item or item["index"] is None:
                    item["index"] = idx
                if "type" not in item or not item["type"]:
                    item["type"] = "书证"
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("generate_core_summary 失败")
        return {"success": False, "error": str(e)}


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
