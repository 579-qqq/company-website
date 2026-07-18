"""题库质量检查"""
import sqlite3, json, os, re

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'company.db')
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM questions ORDER BY id')
rows = c.fetchall()
print(f'题库总数: {len(rows)} 题\n')

issues = []

# ===== 1. 乱码检查 =====
garbled = 0
for r in rows:
    content = r['content']
    # 检测常见乱码特征
    garbled_patterns = [
        r'\?{4,}',           # 连续问号
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]',  # 控制字符
        r'Ã[©¢]',            # 常见UTF8错译
        r'â',    # 右单引号乱码
    ]
    for pat in garbled_patterns:
        if re.search(pat, content):
            garbled += 1
            issues.append(f'[乱码] ID={r["id"]}: {content[:50]}...')
            break

# 另外检查是否有字符显示异常（用常见中文字符范围验证）
for r in rows:
    content = r['content']
    options = r['options']
    # 检查是否有明显非中文非ASCII的异常字符
    # 正常的题库应包含中文、字母、数字、标点
    weird_chars = re.findall(r'[^一-鿿　-〿＀-￯a-zA-Z0-9\s\.\,\;\:\!\?\-\+\=\(\)\[\]\{\}\<\>\'\"\、\。\，\；\：\《\》\（\）\“\”\？\！\…\—\·\/\@\#\$\%\^\&\*\_\\\|]', content)
    if weird_chars:
        issues.append(f'[异常字符] ID={r["id"]}: {set(weird_chars)}')

print(f'乱码检查: {garbled} 题疑似乱码')
print()

# ===== 2. 重复检查 =====
seen_content = {}
duplicates = []
for r in rows:
    content = r['content'].strip()
    # 标准化：去掉多余空格和标点差异
    normalized = re.sub(r'\s+', '', content)
    normalized = re.sub(r'[（(]\s*[）)]', '()', normalized)
    if normalized in seen_content:
        duplicates.append((seen_content[normalized], r['id'], content[:60]))
    else:
        seen_content[normalized] = r['id']

print(f'重复检查: {len(duplicates)} 组重复')
for orig_id, dup_id, text in duplicates:
    issues.append(f'[重复] ID={orig_id} 与 ID={dup_id}: {text}...')
    print(f'  ID={orig_id} == ID={dup_id}: {text}...')
print()

# ===== 3. 选项检查 =====
option_issues = 0
for r in rows:
    try:
        opts = json.loads(r['options'])
    except:
        option_issues += 1
        issues.append(f'[选项JSON错误] ID={r["id"]}')
        continue

    if len(opts) < 2:
        option_issues += 1
        issues.append(f'[选项不足] ID={r["id"]}: 只有{len(opts)}个选项')

    if len(opts) > 6:
        option_issues += 1
        issues.append(f'[选项过多] ID={r["id"]}: {len(opts)}个选项')

    # 检查选项是否为空
    for i, opt in enumerate(opts):
        if not opt or not opt.strip() or len(opt.strip()) < 3:
            option_issues += 1
            issues.append(f'[空选项] ID={r["id"]}: 选项{i+1}为空或过短')
            break

    # 检查答案是否在选项范围内
    answer = r['answer'].upper()
    valid_letters = [chr(65+i) for i in range(len(opts))]
    if answer not in valid_letters:
        option_issues += 1
        issues.append(f'[答案越界] ID={r["id"]}: 答案={answer}, 有效范围={valid_letters}')

print(f'选项检查: {option_issues} 个问题')
print()

# ===== 4. 内容质量检查 =====
quality_issues = 0
for r in rows:
    content = r['content']
    # 题目过短
    if len(content) < 6:
        quality_issues += 1
        issues.append(f'[题目过短] ID={r["id"]}: {content}')
    # 题目过长
    if len(content) > 500:
        quality_issues += 1
        issues.append(f'[题目过长] ID={r["id"]}: {len(content)}字符')
    # 包含"单选题"等标签混入题目
    if re.match(r'^[单选多判断]+题$', content.strip()):
        quality_issues += 1
        issues.append(f'[标签混入题目] ID={r["id"]}: {content}')

print(f'内容质量: {quality_issues} 个问题')
print()

# ===== 5. 分类检查 =====
from collections import Counter
cats = Counter(r['category'] for r in rows)
print('分类统计:')
for cat, count in cats.items():
    print(f'  {cat}: {count}题')
print()

# ===== 6. 选项格式检查（字母前缀一致性） =====
format_issues = 0
for r in rows:
    try:
        opts = json.loads(r['options'])
    except:
        continue
    for i, opt in enumerate(opts):
        expected_letter = chr(65+i)
        if not opt.startswith(expected_letter + '.') and not opt.startswith(expected_letter + '、'):
            format_issues += 1
            issues.append(f'[选项格式] ID={r["id"]}: 选项{i+1}不以"{expected_letter}."或"{expected_letter}、"开头 -> {opt[:30]}')
            break

print(f'选项格式: {format_issues} 个问题')
print()

# ===== 汇总 =====
print('='*60)
if issues:
    print(f'共发现 {len(issues)} 个问题:')
    for issue in issues:
        print(f'  {issue}')
else:
    print('✅ 题库质量良好，未发现问题！')
print('='*60)

conn.close()
