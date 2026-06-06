/* 阶段枚举、颜色映射、预警规则 */

export const STAGE_OPTIONS = [
  { value: 'consultation', label: '咨询 / 待定', color: '#6366F1' },
  { value: 'document_prep', label: '文书准备', color: '#6366F1' },
  { value: 'court_appearance', label: '出庭应诉', color: '#F59E0B' },
  { value: 'awaiting_result', label: '等候结果', color: '#F59E0B' },
  { value: 'closed', label: '已结 / 归档', color: '#10B981' },
]

export const STAGE_LABEL_MAP = Object.fromEntries(
  STAGE_OPTIONS.map((s) => [s.value, s.label])
)

export const STAGE_COLOR_MAP = Object.fromEntries(
  STAGE_OPTIONS.map((s) => [s.value, s.color])
)

export const STATUS_STYLE = {
  overdue: { color: '#EF4444', bg: 'rgba(239,68,68,0.06)', label: '超期' },
  due_soon: { color: '#F59E0B', bg: 'rgba(245,158,11,0.06)', label: '即将到期' },
  normal: { color: '#10B981', bg: 'rgba(16,185,129,0.06)', label: '正常' },
}
