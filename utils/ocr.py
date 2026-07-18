"""
证书照片 OCR 识别模块
使用 Tesseract OCR + 中文语言包提取证书信息
"""
import re
import os
from datetime import datetime

# Tesseract 路径（Windows 下需手动指定，Linux 下通常自动检测）
TESSERACT_CMD = None
if os.name == 'nt':
    # Windows 常见安装路径
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for p in possible_paths:
        if os.path.exists(p):
            TESSERACT_CMD = p
            break


def extract_text(image_path):
    """
    从图片中提取文字

    Args:
        image_path: 图片文件路径

    Returns:
        str: OCR 识别出的原始文本
    """
    try:
        from PIL import Image
        import pytesseract

        if TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

        img = Image.open(image_path)
        # 使用中文 + 英文语言包
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text.strip()

    except ImportError as e:
        raise ImportError(
            f"OCR 依赖未安装：{e}。请运行: pip install pytesseract Pillow\n"
            "并安装 Tesseract 系统包: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except Exception as e:
        raise RuntimeError(f"OCR 识别失败: {e}")


def _normalize_text(text):
    """预处理 OCR 文本：去掉中文字间空格、统一标点"""
    import unicodedata
    # 全角数字/字母 → 半角
    text = unicodedata.normalize('NFKC', text)
    # 中文冒号统一
    text = text.replace('：', ':').replace('∶', ':').replace('︰', ':')
    # ★ 去掉中文字之间的空格（Tesseract 中文常见问题）
    # 匹配 CJK 字符之间的空格并移除
    text = re.sub(r'([一-鿿㐀-䶿])\s+([一-鿿㐀-䶿])', r'\1\2', text)
    # 去掉中文与数字/字母之间多余的空格（但保留英文单词间的空格）
    text = re.sub(r'([一-鿿㐀-䶿])\s+([A-Za-z0-9])', r'\1\2', text)
    text = re.sub(r'([A-Za-z0-9])\s+([一-鿿㐀-䶿])', r'\1\2', text)
    # 普通多余空白合并（英文单词之间保留一个空格）
    text = re.sub(r'[ \t]+', ' ', text)
    # 行首行尾空白
    text = '\n'.join(line.strip() for line in text.splitlines())
    return text


def _find_date_after_label(text, labels):
    """在标签后面找日期，返回 (date_str, match_end_pos) 或 None"""
    for label in labels:
        # 标签后面紧跟日期（可能跨行、有空格、有标点）
        m = re.search(
            label + r'\s*[：:]*\s*' +
            r'(\d{4})\s*[年/\-.年]\s*(\d{1,2})\s*[月/\-.]?\s*(\d{1,2})?\s*[日]?',
            text
        )
        if m:
            y, mo, d = m.group(1), m.group(2), (m.group(3) or '01')
            return (f'{y}-{int(mo):02d}-{int(d):02d}', m.end())
    return None


def _find_all_dates(text):
    """从文本中提取所有日期（YYYY-MM-DD 格式），返回按日期排序的列表"""
    dates = []
    # 匹配各种日期格式
    patterns = [
        # 2026年3月15日 / 2026年03月15日
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
        # 2026-03-15 / 2026/03/15 / 2026.03.15
        r'(\d{4})\s*[\/\-.]\s*(\d{1,2})\s*[\/\-.]\s*(\d{1,2})',
        # 2026年3月 (没有日，默认1号)
        r'(\d{4})\s*年\s*(\d{1,2})\s*月(?!\s*\d)',
        # 2026-03 (没有日)
        r'(\d{4})\s*[\/\-.]\s*(\d{1,2})(?![/\-.]\s*\d)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            try:
                y, mo = int(m.group(1)), int(m.group(2))
                d = int(m.group(3)) if m.lastindex >= 3 else 1
                if 2020 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                    dates.append(f'{y}-{mo:02d}-{d:02d}')
            except (ValueError, IndexError):
                pass

    # 去重排序
    dates = sorted(set(dates))
    return dates


def parse_certificate_info(text):
    """
    从 OCR 文本中解析证书信息（增强版）

    Returns:
        dict: 提取到的字段，未识别则为 None
    """
    result = {
        'name': None,
        'id_number': None,
        'cert_number': None,
        'qualification_type': None,
        'issue_date': None,
        'expire_date': None,
    }

    text = _normalize_text(text)

    # ====== 1. 身份证号 ======
    # 18位身份证号（放宽到在整段文本中找）
    id_m = re.search(r'[^0-9]?([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])[^0-9]?', text)
    if not id_m:
        # 更宽松：直接找 18 位数字+X
        id_m = re.search(r'(\d{17}[\dXx])', text)
    if id_m:
        result['id_number'] = id_m.group(1).upper()

    # ====== 2. 证书编号 ======
    # 按优先级匹配
    cert_patterns = [
        # 标签 + 编号：证书编号 / 编号 / 证书号 / NO / No.
        r'(?:证书编号|证书号|编号|NO|No\.?)[\s:：]*([A-Za-z0-9\-\/]{4,30})',
        # CERT 开头
        r'\b(CERT[\-\s]*\d{4}[\-\s]*\d+)\b',
        # 大写字母 + 数字组合（至少 6 位）
        r'\b([A-Z]{2,6}[\-\s]*\d{4}[\-\s]*\d{2,6})\b',
        # 纯数字编号（8-20位数字）
        r'(?:证书编号|编号|证书号|NO|No\.?)[\s:：]*(\d{6,20})',
    ]
    for pat in cert_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            num = m.group(1).strip()
            # 清理空格和多余字符
            num = re.sub(r'\s+', '', num)
            if len(num) >= 4:
                result['cert_number'] = num
                break

    # ====== 3. 资质类型（大幅增强） ======
    qual_parts = []

    # 3a. ISO 系列（容错匹配：ISO 9001 / ISO9001 / iso9001 / 1SO9001 等）
    iso_m = re.search(r'[I1l|]\s*[S5]\s*[O0]\s*(\d{4,5})', text, re.IGNORECASE)
    if iso_m:
        iso_num = iso_m.group(1)
        qual_parts.append(f'ISO{iso_num}')

    # 3b. IATF 系列
    iatf_m = re.search(r'IATF\s*(\d{4,5})', text, re.IGNORECASE)
    if iatf_m:
        qual_parts.append(f'IATF{iatf_m.group(1)}')

    # 3c. 关键词匹配（分类组织，取最具体者）
    keyword_groups = {
        '质量管理体系内部审核员': ['质量管理体系', '内部审核', '质量体系', '质量管理'],
        '环境管理体系内部审核员': ['环境管理体系', '环境管理'],
        '职业健康安全管理体系内部审核员': ['职业健康安全', '安全管理体系'],
        '食品安全管理体系内部审核员': ['食品安全管理', '食品安全'],
        '信息安全管理体系内部审核员': ['信息安全管理', '信息安全'],
        '内审员': ['内审员', '内部审核员', '内审'],
        '外审员': ['外审员', '主任审核员', '外部审核员'],
        '质量工程师': ['质量工程师'],
        '安全工程师': ['安全工程师'],
        '环境工程师': ['环境工程师'],
        '软件工程师': ['软件工程师'],
        '网络工程师': ['网络工程师'],
        '项目管理师': ['项目管理师', '项目管理'],
        '六西格玛黑带': ['六西格玛黑带', '黑带'],
        '六西格玛绿带': ['六西格玛绿带', '绿带'],
        '精益生产管理师': ['精益生产', '精益管理'],
        '企业管理咨询师': ['企业管理咨询师'],
        '人力资源管[理理]师': ['人力资源'],
        '供应链管理师': ['供应链'],
        '班组长管理': ['班组长'],
        '中层管理': ['中层管理', '领导力'],
    }
    for cert_name, keywords in keyword_groups.items():
        for kw in keywords:
            if kw in text:
                qual_parts.append(cert_name)
                break

    if qual_parts:
        # 去重：去除被其他项包含的子串（如"内审员"已被"质量管理体系内部审核员"包含）
        unique = []
        for p in qual_parts:
            is_sub = False
            for other in qual_parts:
                if p != other and p in other:
                    is_sub = True
                    break
            if not is_sub:
                unique.append(p)
        # 二次去重
        seen = set()
        final = []
        for p in unique:
            if p not in seen:
                seen.add(p)
                final.append(p)
        result['qualification_type'] = ' '.join(final)
    else:
        # 最后兜底：找"资质类型"/"课程名称"/"培训课程"后面的文字
        for label in ['资质类型', '课程名称', '培训课程', '认证类型', '证书类型']:
            m = re.search(label + r'[\s:：]*([^\n]{2,30})', text)
            if m:
                result['qualification_type'] = m.group(1).strip()
                break

    # ====== 4. 姓名（多种标签格式） ======
    name_patterns = [
        # 标准标签
        r'姓\s*名[\s:：]*([一-鿿·]{2,4})',
        r'学\s*员[\s:：]*([一-鿿·]{2,4})',
        r'持证人[\s:：]*([一-鿿·]{2,4})',
        r'兹证明\s*([一-鿿·]{2,4})',
        # 证书常用格式
        r'兹\s*有\s*([一-鿿·]{2,4})',
        r'同\s*志\s*([一-鿿·]{2,4})',
        r'先\s*生\s*([一-鿿·]{2,4})',
        r'女\s*士\s*([一-鿿·]{2,4})',
    ]
    for pat in name_patterns:
        m = re.search(pat, text)
        if m:
            result['name'] = m.group(1)
            break

    # 兜底：身份证号前面找姓名
    if not result['name'] and result['id_number']:
        idx = text.find(result['id_number'])
        if idx >= 5:
            before = text[max(0, idx-20):idx]
            # 多种策略找姓名
            # 策略1: 从后往前找 CJK 字符序列（2-4字）
            cjk_seq = re.findall(r'[一-鿿·]{2,4}', before)
            if cjk_seq:
                result['name'] = cjk_seq[-1]  # 取最靠近身份证号的中文序列
            # 策略2: 找逗号/空格后面的中文名
            if not result['name']:
                name_m = re.search(r'[,，\s]\s*([一-鿿·]{2,4})\s*[,，\s]*$', before)
                if name_m:
                    result['name'] = name_m.group(1)

    # ====== 5. 日期 ======
    # 先用标签定位
    issue = _find_date_after_label(text, ['发证日期', '签发日期', '颁发日期', '批准日期', 'issue', 'Issue'])
    expire = _find_date_after_label(text, ['有效期至', '有效期到', '截止日期', '到期日期', '有效期', 'expire', 'Expire'])

    if issue:
        result['issue_date'] = issue[0]
    if expire:
        result['expire_date'] = expire[0]

    # 如果标签没找到，用全部日期推断
    all_dates = _find_all_dates(text)
    if all_dates:
        if not result['issue_date'] and not result['expire_date']:
            if len(all_dates) >= 2:
                result['issue_date'] = all_dates[0]
                result['expire_date'] = all_dates[-1]
            else:
                result['issue_date'] = all_dates[0]
        elif not result['expire_date'] and len(all_dates) >= 2:
            result['expire_date'] = all_dates[-1]
        elif not result['issue_date']:
            result['issue_date'] = all_dates[0]

    # ====== 5b. 有效期推算（如果没有明确到期日但有"有效期X年"） ======
    if not result['expire_date'] and result['issue_date']:
        # 中文数字映射
        cn_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6,
                   '七': 7, '八': 8, '九': 9, '十': 10}
        # 匹配"有效期X年" / "有效期为三年" 等
        validity_m = re.search(
            r'有效期(?:为|是|：|:)?\s*(\d+|[一二三四五六七八九十]+)\s*年',
            text
        )
        if validity_m:
            years_str = validity_m.group(1)
            if years_str.isdigit():
                years = int(years_str)
            else:
                years = cn_nums.get(years_str, 0) if len(years_str) == 1 else 3
            if 1 <= years <= 20:
                try:
                    issue_dt = datetime.strptime(result['issue_date'], '%Y-%m-%d')
                    exp_dt = issue_dt.replace(year=issue_dt.year + years)
                    result['expire_date'] = exp_dt.strftime('%Y-%m-%d')
                except (ValueError, OverflowError):
                    pass

    # ====== 6. 自动判断有效期状态 ======
    if result['expire_date']:
        try:
            exp_dt = datetime.strptime(result['expire_date'], '%Y-%m-%d')
            if exp_dt < datetime.now():
                result['status'] = '过期'
            else:
                result['status'] = '有效'
        except ValueError:
            result['status'] = '有效'
    else:
        result['status'] = '有效'

    return result


def normalize_date(date_str):
    """将各种日期格式统一为 YYYY-MM-DD"""
    date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '').replace('/', '-')
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        pass
    try:
        dt = datetime.strptime(date_str, '%Y-%m')
        return dt.strftime('%Y-%m')
    except ValueError:
        return None


# ==========================================
# 测试入口
# ==========================================
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python utils/ocr.py <图片路径>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"[ERROR] 文件不存在: {image_path}")
        sys.exit(1)

    print(f"[INFO] 正在识别: {image_path}")
    print("-" * 50)

    try:
        raw_text = extract_text(image_path)
        print("【原始 OCR 文本】")
        print(raw_text)
        print("-" * 50)

        info = parse_certificate_info(raw_text)
        print("【解析结果】")
        for key, value in info.items():
            print(f"  {key}: {value or '(未识别)'}")

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
