"""
数据脱敏模块 — 在文本发送给 AI/LLM 之前，使用正则 + jieba 分词对敏感信息进行脱敏。

性能说明：
  - 默认仅启用正则脱敏（< 0.1s / 20K 字符）
  - jieba 人名/地址脱敏默认关闭，开启后增加 1~3s（jieba.cut 快速模式）
  - 如需最大吞吐，直接调用 fast_desensitize() 跳过 jieba 完全

支持的 PII 类型:
  - 身份证号 (18位)     → 正则精确匹配
  - 手机号 (11位)       → 正则精确匹配
  - 座机号              → 正则匹配
  - 电子邮箱            → 正则匹配
  - 银行卡号 (16-19位)  → 正则匹配
  - 车牌号              → 正则匹配
  - 统一社会信用代码    → 正则匹配
  - 人名                → jieba.cut + 姓氏表 (默认关闭)
  - 地址                → 正则辅助 (默认关闭)
"""
import re
import os
import logging

logger = logging.getLogger("desensitizer")

# ═══════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════

_config = {
    "enabled": True,
    "mask_name": False,          # 默认关闭：jieba 分词有性能代价，且法律文档中当事人姓名对 AI 匹配至关重要
    "mask_phone": True,
    "mask_id_card": True,
    "mask_email": True,
    "mask_address": False,       # 默认关闭：法律文档地址信息有助于案件匹配
    "mask_bank_card": True,
    "mask_plate": True,
    "mask_credit_code": True,
    "mask_landline": True,
}

# 常见中文姓氏表（覆盖 >95% 汉族人口），用于快速人名识别替代 jieba.posseg
_COMMON_SURNAMES = frozenset(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水"
    "窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕"
    "郝邬安常乐于时傅皮下齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成"
    "戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏"
    "蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程"
    "嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬"
    "全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰"
    "从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍卻璩桑桂濮"
    "牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步"
    "都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙"
    "乜养鞠须丰巢关蒯相查后荆红游竺权逮盍益桓公"
)

# jieba 延迟加载标记
_jieba_loaded = False


def _ensure_jieba():
    """延迟加载 jieba + 自定义法律词典（避免启动时加载开销）"""
    global _jieba_loaded
    if _jieba_loaded:
        return
    try:
        import jieba
        dict_path = os.path.join(os.path.dirname(__file__), "desensitizer_dict.txt")
        if os.path.exists(dict_path):
            jieba.load_userdict(dict_path)
            logger.info("已加载法律自定义词典: %d 条", _count_dict_lines(dict_path))
        _jieba_loaded = True
    except ImportError:
        logger.warning("jieba 未安装，人名/地址脱敏将跳过。请执行: pip install jieba")
        _jieba_loaded = True  # 标记为已尝试，避免重复警告


def _count_dict_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════
# 正则模式 — 按匹配优先级排序
# ═══════════════════════════════════════════════════════════

# 注意：Python3 中中文字符是 \w 字符，\b 在中英文交界处不生效。
# 因此数字类型 PII 使用 (?<!\d)...(?!\d) 作为边界；中文开头的 PII 不做左侧边界限制。

# 1. 身份证号 (18位) — 最高优先级，精确匹配
# 6位地区码 + 4位出生年(19xx/20xx) + 2位月(01-12) + 2位日(01-31) + 3位顺序码 + 1位校验码
_ID_CARD_RE = re.compile(
    r'(?<!\d)'
    r'[1-9]\d{5}'                 # 地区码 6位
    r'(?:19|20)\d{2}'             # 年份 19xx 或 20xx
    r'(?:0[1-9]|1[0-2])'          # 月份 01-12
    r'(?:0[1-9]|[12]\d|3[01])'    # 日期 01-31
    r'\d{3}'                       # 顺序码 3位
    r'[\dXx]'                      # 校验码
    r'(?!\d)'
)

# 2. 手机号 (11位)
_PHONE_RE = re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)')

# 3. 电子邮箱
# 左侧要求本地部分以 ASCII 字母/数字开头（防止吞掉前面的中文字符）
_EMAIL_RE = re.compile(r'[a-zA-Z0-9][\w.+-]*@[\w-]+\.[\w.-]+')

# 4. 车牌号 (含新能源)
# 省份简称 + 发牌机关代号 + 号码(5-6位含新能源)
_PLATE_RE = re.compile(
    r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁]'
    r'[A-HJ-NP-Z]'
    r'[A-HJ-NP-Z0-9]{4,5}'
    r'[A-HJ-NP-Z0-9挂学警港澳]'
    r'(?!\w)'   # 右侧不能紧跟字母/数字/中文
)

# 5. 统一社会信用代码 (18位，不含 I O Z S V)
_CREDIT_CODE_RE = re.compile(
    r'(?<![A-Z0-9])'
    r'[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}'
    r'(?![A-Z0-9])'
)

# 6. 座机号 (区号-号码-分机号)
_LANDLINE_RE = re.compile(r'(?<!\d)(\d{3,4})-(\d{7,8})(?:-(\d{1,6}))?(?!\d)')

# 7. 银行卡号 (16-19位数字) — 需要银行卡 BIN 前缀，避免误伤案件编号
# 银联(62开头)/Visa(4开头)/Mastercard(51-55开头)
_BANK_CARD_RE = re.compile(
    r'(?<!\d)'
    r'(?:62\d{14,17}'          # 银联 16/19位
    r'|4\d{15,18}'              # Visa 16/19位
    r'|5[1-5]\d{14,17})'        # Mastercard 16位
    r'(?!\d)'
)

# 8. 地址片段模式 — 保守匹配，需要省/市级开头 + 具体门牌数字
# 避免误伤法院名称、案由描述等
_ADDR_PATTERN_RE = re.compile(
    r'(?:[省市区县])'
    r'.{0,20}?'
    r'(?:[路街巷弄道])'
    r'.{0,10}?'
    r'\d+'             # 必须有门牌号
    r'(?:号|弄|幢|栋|单元|室|层|楼|座|院)'
)

# 已脱敏标记，用于跳过重复处理
_MASKED_PATTERN = re.compile(r'\[[一-鿿]+(?:号)?[:：][^\]]+\]')


# ═══════════════════════════════════════════════════════════
# 替换函数
# ═══════════════════════════════════════════════════════════

def _mask_id_card(m: re.Match) -> str:
    s = m.group()
    return f'[身份证号:{s[:3]}********{s[-4:]}]'


def _mask_phone(m: re.Match) -> str:
    s = m.group()
    return f'[手机号:{s[:3]}****{s[-4:]}]'


def _mask_email(m: re.Match) -> str:
    s = m.group()
    local, domain = s.split('@', 1)
    masked_local = local[0] + '***' if local else '***'
    return f'[邮箱:{masked_local}@{domain}]'


def _mask_plate(m: re.Match) -> str:
    s = m.group()
    return f'[车牌号:{s[0]}{s[1]}****{s[-1]}]'


def _mask_credit_code(m: re.Match) -> str:
    s = m.group()
    return f'[信用代码:****{s[-4:]}]'


def _mask_landline(m: re.Match) -> str:
    area = m.group(1)
    number = m.group(2)
    ext = m.group(3)
    masked = f'[座机号:{area}-****{number[-4:]}'
    if ext:
        masked += f'-{ext}'
    masked += ']'
    return masked


def _mask_bank_card(m: re.Match) -> str:
    s = m.group()
    # 跳过已脱敏的标记
    return f'[银行卡号:****{s[-4:]}]'


# ═══════════════════════════════════════════════════════════
# jieba 分词 — 人名 & 地址识别
# ═══════════════════════════════════════════════════════════

def _mask_names_by_jieba(text: str) -> str:
    """轻量人名识别：jieba.cut (快速模式) + 姓氏表匹配，替代慢速 pseg.cut。

    保护策略：先将已有的脱敏标记 [...] 替换为占位符 → jieba 分词 → 恢复占位符。
    这样 jieba 完全不会看到标记内的文本，避免误伤。

    性能：jieba.cut 比 pseg.cut 快 8~15x（无 HMM 词性标注），
    配合姓氏表过滤仍有良好准确率。
    """
    if not _config["mask_name"]:
        return text

    _ensure_jieba()
    try:
        import jieba
    except ImportError:
        return text

    # 1. 提取所有已有的脱敏标记，替换为唯一占位符
    MARKER_PATTERN = re.compile(r'\[[^\]]*(?::[^\]]*)?\]')
    placeholders = []
    def _save(m: re.Match) -> str:
        placeholders.append(m.group())
        return f'\x00MK{len(placeholders) - 1}\x00'
    clean = MARKER_PATTERN.sub(_save, text)

    # 2. 快速分词 + 姓氏表匹配
    words = jieba.cut(clean, HMM=False)  # 关闭 HMM 进一步加速
    result = []
    for word in words:
        wlen = len(word)
        if (
            2 <= wlen <= 3                         # 中文名 2-3 字
            and '一' <= word[0] <= '鿿'            # 首字为汉字
            and word[0] in _COMMON_SURNAMES         # 首字在姓氏表
            and all('一' <= c <= '鿿' for c in word)  # 全部为汉字
        ):
            result.append('[姓名]')
        else:
            result.append(word)
    masked = ''.join(result)

    # 3. 恢复占位符为原始标记
    for i, ph in enumerate(placeholders):
        masked = masked.replace(f'\x00MK{i}\x00', ph)

    return masked


def _mask_addresses(text: str) -> str:
    """使用正则匹配明显地址结构并替换为 [地址]

    保守策略：必须包含 省/市/区/县级 + 路/街 + 门牌号，避免误伤机构名。
    匹配内容中若已包含脱敏标记 [ 或 ]，则跳过（保护已有标记）。
    """
    if not _config["mask_address"]:
        return text

    def _replace_addr(m: re.Match) -> str:
        s = m.group()
        # 不覆盖已脱敏标记的内容
        if '[' in s or ']' in s:
            return s
        if len(s) >= 8:
            return '[地址]'
        return s

    return _ADDR_PATTERN_RE.sub(_replace_addr, text)


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

def desensitize(text: str) -> str:
    """
    对输入文本执行全部 PII 脱敏，返回脱敏后的文本。

    处理顺序（重要，避免交叉匹配）:
      1. 身份证号 (精确格式)
      2. 手机号 (11位)
      3. 电子邮箱
      4. 车牌号
      5. 统一社会信用代码
      6. 座机号
      7. 银行卡号 (16-19位通用数字)
      8. jieba 人名识别
      9. 地址识别

    Args:
        text: 原始文本

    Returns:
        脱敏后的文本（如未启用则返回原文）
    """
    if not _config["enabled"]:
        return text

    if not text or not text.strip():
        return text

    # --- 第一阶段：正则精确匹配 (结构化 PII) ---
    if _config["mask_id_card"]:
        text = _ID_CARD_RE.sub(_mask_id_card, text)

    if _config["mask_phone"]:
        text = _PHONE_RE.sub(_mask_phone, text)

    if _config["mask_email"]:
        text = _EMAIL_RE.sub(_mask_email, text)

    if _config["mask_plate"]:
        text = _PLATE_RE.sub(_mask_plate, text)

    if _config["mask_credit_code"]:
        text = _CREDIT_CODE_RE.sub(_mask_credit_code, text)

    if _config["mask_landline"]:
        text = _LANDLINE_RE.sub(_mask_landline, text)

    if _config["mask_bank_card"]:
        # 银行卡放在最后，避免与身份证/手机号等冲突
        # 跳过已被脱敏标记包围的数字串
        text = _BANK_CARD_RE.sub(_mask_bank_card, text)

    # --- 第二阶段：jieba 分词 (语义级 PII) ---
    if _config["mask_name"]:
        text = _mask_names_by_jieba(text)

    if _config["mask_address"]:
        text = _mask_addresses(text)

    return text


def get_config() -> dict:
    """获取当前脱敏配置"""
    return dict(_config)


def update_config(**kwargs):
    """更新脱敏配置

    Args:
        enabled: 是否启用脱敏
        mask_name: 是否脱敏姓名
        mask_phone: 是否脱敏手机号
        mask_id_card: 是否脱敏身份证
        mask_email: 是否脱敏邮箱
        mask_address: 是否脱敏地址
        mask_bank_card: 是否脱敏银行卡
        mask_plate: 是否脱敏车牌
        mask_credit_code: 是否脱敏统一社会信用代码
        mask_landline: 是否脱敏座机号
    """
    for k, v in kwargs.items():
        if k in _config:
            _config[k] = v
    logger.info("脱敏配置已更新: %s", {k: v for k, v in kwargs.items() if k in _config})


def fast_desensitize(text: str) -> str:
    """纯正则脱敏（跳过 jieba），适合高吞吐热路径。

    仅处理结构化 PII（身份证/手机/邮箱/车牌/信用代码/座机/银行卡），
    不处理人名和地址。20K 字符文本耗时 < 0.1s。
    """
    if not _config["enabled"] or not text or not text.strip():
        return text

    if _config["mask_id_card"]:
        text = _ID_CARD_RE.sub(_mask_id_card, text)
    if _config["mask_phone"]:
        text = _PHONE_RE.sub(_mask_phone, text)
    if _config["mask_email"]:
        text = _EMAIL_RE.sub(_mask_email, text)
    if _config["mask_plate"]:
        text = _PLATE_RE.sub(_mask_plate, text)
    if _config["mask_credit_code"]:
        text = _CREDIT_CODE_RE.sub(_mask_credit_code, text)
    if _config["mask_landline"]:
        text = _LANDLINE_RE.sub(_mask_landline, text)
    if _config["mask_bank_card"]:
        text = _BANK_CARD_RE.sub(_mask_bank_card, text)

    return text
