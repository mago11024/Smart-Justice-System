"""工具函数：阶段枚举、合法转换、时间计算"""
from datetime import date, datetime
from typing import Optional

STAGE_ORDER = [
    "consultation",
    "document_prep",
    "court_appearance",
    "awaiting_result",
    "closed",
]

STAGE_LABELS = {
    "consultation": "咨询 / 待定",
    "document_prep": "文书准备",
    "court_appearance": "出庭应诉",
    "awaiting_result": "等候结果",
    "closed": "已结 / 归档",
}

STAGE_COLORS = {
    "consultation": "#6366F1",
    "document_prep": "#6366F1",
    "court_appearance": "#F59E0B",
    "awaiting_result": "#F59E0B",
    "closed": "#10B981",
}


def get_next_stage(current: str) -> Optional[str]:
    """合法前向转换：仅允许顺序推进，不允许跳过"""
    try:
        idx = STAGE_ORDER.index(current)
    except ValueError:
        return None
    return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None


def compute_overdue_status(deadline: Optional[date]) -> tuple:
    """
    返回 (状态, 天数)
    状态: overdue | due_soon | normal
    天数: 正数=超期天数，负数=剩余天数，0=今天截止
    """
    if deadline is None:
        return ("normal", 0)
    delta = (date.today() - deadline).days
    if delta > 0:
        return ("overdue", delta)
    elif delta >= -7:
        return ("due_soon", -delta)
    else:
        return ("normal", -delta)


def days_in_stage(stage_entered_at: datetime) -> int:
    """计算当前阶段停留天数"""
    delta = datetime.utcnow() - stage_entered_at
    return max(0, delta.days)
