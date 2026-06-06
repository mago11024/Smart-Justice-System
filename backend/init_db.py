"""数据库初始化：建表 + 种子数据"""
from datetime import date, datetime, timedelta
from app.database import engine, SessionLocal, Base
from app import models

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 清理旧数据
db.query(models.Notification).delete()
db.query(models.CaseLog).delete()
db.query(models.CaseDocument).delete()
db.query(models.Case).delete()
db.query(models.Lawyer).delete()
db.commit()

# 律师种子数据
lawyers_data = [
    {"name": "王浩", "initials": "王", "role": "合伙人", "email": "wanghao@law.com"},
    {"name": "赵敏", "initials": "赵", "role": "律师", "email": "zhaomin@law.com"},
    {"name": "李芳", "initials": "李", "role": "律师", "email": "lifang@law.com"},
    {"name": "陈思远", "initials": "陈", "role": "律师", "email": "chensy@law.com"},
]
lawyers = {}
for ld in lawyers_data:
    l = models.Lawyer(**ld)
    db.add(l)
    db.flush()
    lawyers[ld["name"]] = l.id

# 案件种子数据（对齐 HTML 原型）
today = date.today()

cases_data = [
    # 超期
    {"case_number": "(2025)沪0105民初1234号", "case_name": "张三诉李四借款纠纷",
     "plaintiff": "张三", "defendant": "李四", "cause_of_action": "民间借贷",
     "stage": "awaiting_result", "deadline": today - timedelta(days=3),
     "stage_entered_at": datetime.utcnow() - timedelta(days=5),
     "lawyer_id": lawyers["王浩"]},
    {"case_number": "(2025)沪0115民初5678号", "case_name": "某科技公司合同纠纷",
     "plaintiff": "某科技有限公司", "defendant": "某信息公司", "cause_of_action": "合同纠纷",
     "stage": "document_prep", "deadline": today - timedelta(days=1),
     "stage_entered_at": datetime.utcnow() - timedelta(days=8),
     "lawyer_id": lawyers["赵敏"]},
    # 即将到期
    {"case_number": "(2025)沪0101民初9012号", "case_name": "某银行金融借款纠纷",
     "plaintiff": "某银行", "defendant": "某贸易公司", "cause_of_action": "金融借款",
     "stage": "document_prep", "deadline": today + timedelta(days=3),
     "stage_entered_at": datetime.utcnow() - timedelta(days=12),
     "lawyer_id": lawyers["李芳"]},
    {"case_number": "(2025)沪0105民初3456号", "case_name": "王某人身损害赔偿",
     "plaintiff": "王某", "defendant": "某物业公司", "cause_of_action": "人身损害赔偿",
     "stage": "document_prep", "deadline": today + timedelta(days=5),
     "stage_entered_at": datetime.utcnow() - timedelta(days=6),
     "lawyer_id": lawyers["王浩"]},
    # 正常文书
    {"case_number": "(2025)沪0115民初7890号", "case_name": "某房地产公司合同纠纷",
     "plaintiff": "某房地产公司", "defendant": "某建筑公司", "cause_of_action": "合同纠纷",
     "stage": "document_prep", "deadline": today + timedelta(days=16),
     "stage_entered_at": datetime.utcnow() - timedelta(days=4),
     "lawyer_id": lawyers["陈思远"]},
    # 出庭
    {"case_number": "(2025)沪0105民初1111号", "case_name": "某物流公司运输合同纠纷",
     "plaintiff": "某物流公司", "defendant": "某货运公司", "cause_of_action": "运输合同",
     "stage": "court_appearance", "court_date": today + timedelta(days=1),
     "stage_entered_at": datetime.utcnow() - timedelta(days=15),
     "lawyer_id": lawyers["赵敏"]},
    {"case_number": "(2025)沪0105民初2222号", "case_name": "刘某劳动争议",
     "plaintiff": "刘某", "defendant": "某科技公司", "cause_of_action": "劳动争议",
     "stage": "court_appearance", "court_date": today + timedelta(days=8),
     "stage_entered_at": datetime.utcnow() - timedelta(days=10),
     "lawyer_id": lawyers["李芳"]},
    # 咨询
    {"case_number": "", "case_name": "某公司股权转让咨询",
     "plaintiff": "", "defendant": "", "cause_of_action": "股权转让",
     "stage": "consultation", "stage_entered_at": datetime.utcnow() - timedelta(days=1),
     "lawyer_id": lawyers["陈思远"]},
    # 等候
    {"case_number": "(2025)沪0105民初3333号", "case_name": "某建筑公司工程款纠纷",
     "plaintiff": "某建筑公司", "defendant": "某开发公司", "cause_of_action": "工程款纠纷",
     "stage": "awaiting_result", "stage_entered_at": datetime.utcnow() - timedelta(days=7),
     "court_date": datetime.utcnow() - timedelta(days=10),
     "lawyer_id": lawyers["王浩"]},
    # 已结
    {"case_number": "(2025)沪0105民初4444号", "case_name": "某服装公司货款纠纷",
     "plaintiff": "某服装公司", "defendant": "某商场", "cause_of_action": "货款纠纷",
     "stage": "closed", "outcome": "won", "outcome_note": "胜诉，判赔 50 万",
     "stage_entered_at": datetime.utcnow() - timedelta(days=30),
     "lawyer_id": lawyers["王浩"]},
    {"case_number": "(2025)沪0105民初5555号", "case_name": "某餐饮公司租赁纠纷",
     "plaintiff": "某餐饮公司", "defendant": "某商场", "cause_of_action": "租赁纠纷",
     "stage": "closed", "outcome": "mediated", "outcome_note": "调解结案",
     "stage_entered_at": datetime.utcnow() - timedelta(days=45),
     "lawyer_id": lawyers["王浩"]},
    {"case_number": "(2025)沪0115民初6666号", "case_name": "某网络公司侵权纠纷",
     "plaintiff": "某个人", "defendant": "某网络公司", "cause_of_action": "侵权纠纷",
     "stage": "closed", "outcome": "won", "outcome_note": "胜诉",
     "stage_entered_at": datetime.utcnow() - timedelta(days=60),
     "lawyer_id": lawyers["赵敏"]},
    {"case_number": "(2025)沪0115民初7777号", "case_name": "某公司债务追偿",
     "plaintiff": "某投资公司", "defendant": "某个体户", "cause_of_action": "债务追偿",
     "stage": "closed", "outcome": "dismissed", "outcome_note": "撤诉",
     "stage_entered_at": datetime.utcnow() - timedelta(days=90),
     "lawyer_id": lawyers["赵敏"]},
    {"case_number": "(2025)沪0101民初8888号", "case_name": "某村民土地承包纠纷",
     "plaintiff": "某村民", "defendant": "某村委会", "cause_of_action": "土地承包",
     "stage": "closed", "outcome": "won", "outcome_note": "胜诉",
     "stage_entered_at": datetime.utcnow() - timedelta(days=120),
     "lawyer_id": lawyers["李芳"]},
    {"case_number": "(2025)沪0101民初9999号", "case_name": "某公司不正当竞争",
     "plaintiff": "某品牌公司", "defendant": "某竞争对手", "cause_of_action": "不正当竞争",
     "stage": "closed", "outcome": "won", "outcome_note": "胜诉，判赔 200 万",
     "stage_entered_at": datetime.utcnow() - timedelta(days=150),
     "lawyer_id": lawyers["陈思远"]},
]

case_objects = []
for cd in cases_data:
    c = models.Case(**cd)
    db.add(c)
    db.flush()
    case_objects.append((c, cd.get("stage", "")))

# 额外补几条，凑到 20 件活跃（咨询阶段增加）
extra_consult = [
    {"case_number": "", "case_name": "张某婚姻财产分割咨询",
     "plaintiff": "张某", "defendant": "", "cause_of_action": "婚姻财产",
     "stage": "consultation", "stage_entered_at": datetime.utcnow() - timedelta(days=2),
     "lawyer_id": lawyers["李芳"]},
]
for cd in extra_consult:
    c = models.Case(**cd)
    db.add(c)
    db.flush()
    case_objects.append((c, cd["stage"]))

# 操作日志
for c, stage in case_objects:
    db.add(models.CaseLog(case_id=c.id, action="created", new_value=stage, note="初始创建"))

db.commit()
print(f"初始化完成：{len(lawyers)} 位律师，{len(case_objects)} 件案件")

# 生成初始通知
from app.services.notification_service import generate_notifications
n = generate_notifications(db)
print(f"生成 {n} 条提醒")

db.close()
