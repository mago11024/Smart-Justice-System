"""PaddleOCR 云端服务 — 处理扫描件 PDF / 图片 OCR"""
import os, json, time, logging
import httpx
from app.config_env import load_env_file

logger = logging.getLogger("paddle_ocr")
load_env_file()

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"


def _get_config() -> dict:
    """从 config.json 读取 PaddleOCR 非敏感配置"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("paddleocr", {})
    except Exception:
        return {}


def ocr_pdf(file_path: str, timeout: int = 120) -> str:
    """对 PDF 文件执行 OCR，返回识别文本。

    流程：提交任务 → 轮询 → 下载 JSONL → 解析文本
    """
    load_env_file()
    cfg = _get_config()
    token = os.getenv("PADDLEOCR_TOKEN", "")
    model = os.getenv("PADDLEOCR_MODEL", "") or cfg.get("model", "PP-OCRv5")

    if not token:
        logger.warning("PaddleOCR token 未配置，跳过 OCR")
        return ""

    if not os.path.exists(file_path):
        logger.error("文件不存在: %s", file_path)
        return ""

    headers = {"Authorization": f"bearer {token}"}

    # 1. 提交任务
    try:
        with open(file_path, "rb") as f:
            data = {
                "model": model,
                "optionalPayload": json.dumps({
                    "useDocOrientationClassify": False,
                    "useDocUnwarping": False,
                    "useTextlineOrientation": False,
                }),
            }
            files = {"file": f}
            resp = httpx.post(JOB_URL, headers=headers, data=data, files=files, timeout=30)
            resp.raise_for_status()
    except Exception as e:
        logger.exception("PaddleOCR 提交任务失败")
        return ""

    job_data = resp.json()
    job_id = job_data.get("data", {}).get("jobId", "")
    if not job_id:
        logger.error("PaddleOCR 未返回 jobId: %s", resp.text[:300])
        return ""

    logger.info("PaddleOCR job submitted: %s", job_id)

    # 2. 轮询等待（1.5s 间隔，比 3s 快一倍）
    start = time.time()
    jsonl_url = ""
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            logger.warning("PaddleOCR job %s 超时 (%ds)", job_id, timeout)
            return ""

        try:
            resp = httpx.get(f"{JOB_URL}/{job_id}", headers=headers, timeout=10)
            resp.raise_for_status()
            state_data = resp.json().get("data", {})
            state = state_data.get("state", "pending")
        except Exception as e:
            logger.warning("PaddleOCR 轮询异常: %s", e)
            time.sleep(1.5)
            continue

        if state == "done":
            jsonl_url = state_data.get("resultUrl", {}).get("jsonUrl", "")
            break
        elif state == "failed":
            err = state_data.get("errorMsg", "未知错误")
            logger.error("PaddleOCR job %s 失败: %s", job_id, err)
            return ""
        else:
            progress = state_data.get("extractProgress", {})
            total = progress.get("totalPages", "?")
            done = progress.get("extractedPages", 0)
            if state == "running":
                logger.debug("PaddleOCR %s: %s/%s 页", job_id, done, total)
            time.sleep(1.5)

    if not jsonl_url:
        return ""

    # 3. 下载并解析 JSONL
    try:
        resp = httpx.get(jsonl_url, timeout=60)
        resp.raise_for_status()
        text_parts = []
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                result = json.loads(line).get("result", {})
                for ocr_result in result.get("ocrResults", []):
                    pruned = ocr_result.get("prunedResult", {})
                    raw_text = pruned_result_to_text(pruned)
                    if raw_text:
                        text_parts.append(raw_text)
            except json.JSONDecodeError:
                continue
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.exception("PaddleOCR 下载/解析结果失败")
        return ""


def pruned_result_to_text(pruned: dict) -> str:
    """将 PaddleOCR prunedResult 转为纯文本。

    结构: {"rec_texts": [...], "rec_boxes": [...], "rec_polys": [...]}
    """
    texts = pruned.get("rec_texts", [])
    return "\n".join(texts).strip() if texts else ""
