"""
重新导入用户提供的题库
用法: python database/reimport_questions.py
"""
import sys
import os
import re
import json
import subprocess
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'company.db')

# 用户提供的题库文件
FILES = [
    (r'C:\Users\36465\Desktop\单选.doc', 'ISO9001质量管理体系'),
    (r'C:\Users\36465\Desktop\单选 新增.doc', 'ISO9001质量管理体系'),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def extract_text_from_doc(filepath):
    """利用 PowerShell + Word COM 从 .doc 提取纯文本"""
    ps_script = f'''
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    try {{
        $doc = $word.Documents.Open("{filepath}")
        $text = $doc.Content.Text
        $doc.Close()
        $text = $text -replace "\\r\\n", "`n" -replace "\\r", "`n"
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Write-Output $text
    }} finally {{
        $word.Quit()
    }}
    '''
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', ps_script],
        capture_output=True, text=True, encoding='utf-8', timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"PowerShell 提取失败: {result.stderr}")
    return result.stdout


def parse_questions(text, category):
    """解析题目文本，支持多种格式"""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    option_letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    questions = []
    current = None

    def start_new_question(content):
        nonlocal current
        current = {
            'category': category,
            'content': content,
            'options': [],
            'answer': '',
            'score': 2
        }

    def save_current():
        nonlocal current
        if current and current.get('options') and current.get('answer'):
            questions.append(current)
            current = None
            return True
        return False

    def looks_complete(text):
        if len(text) < 10:
            return False
        if re.search(r'[（(][\s]*[）)]$', text):
            return True
        if re.search(r'[？?。：:]$', text):
            return True
        if re.search(r'(什么|哪些|哪个|如何|哪个|是否|可否|为什么|怎样)', text):
            return True
        if len(text) > 60:
            return True
        return False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 跳过纯标签行
        if re.match(r'^[单选多选判]+\s*题\s*$', line):
            continue

        is_numbered = bool(re.match(r'^[\(（]?\d+[\)）、.．]', line))
        is_answer = bool(re.match(r'^(?:正确)?答案[：:]\s*([A-Fa-f])', line))
        has_letter_prefix = bool(re.match(r'^[A-Fa-f][.、．\s]', line))

        if is_answer:
            if current and not current['answer']:
                m = re.match(r'^(?:正确)?答案[：:]\s*([A-Fa-f])', line)
                current['answer'] = m.group(1).upper()
                save_current()
            continue

        if is_numbered:
            save_current()
            content = re.sub(r'^[\(（]?\d+[\)）、.．\s]+', '', line, count=1).strip()
            start_new_question(content)
            continue

        if has_letter_prefix:
            if current and not current['answer']:
                m = re.match(r'^([A-Fa-f])[.、．\s]+(.*)', line)
                if m:
                    letter = m.group(1).upper()
                    opt_text = m.group(2).strip()
                    current['options'].append(f"{letter}. {opt_text}")
                continue

        if current and current['answer']:
            save_current()

        if current is None:
            start_new_question(line)
        elif not current['answer']:
            if current['options']:
                idx = len(current['options'])
                letter = option_letters[idx] if idx < len(option_letters) else '?'
                current['options'].append(f"{letter}. {line}")
            else:
                if looks_complete(current['content']):
                    idx = len(current['options'])
                    letter = option_letters[idx]
                    current['options'].append(f"{letter}. {line}")
                else:
                    current['content'] += line

    save_current()
    return questions


def main():
    # 先提取和解析所有题目
    all_questions = []
    for filepath, category in FILES:
        if not os.path.exists(filepath):
            print(f"[WARN] 文件不存在，跳过: {filepath}")
            continue

        print(f"[INFO] 读取: {filepath}")
        text = extract_text_from_doc(filepath)
        questions = parse_questions(text, category)
        print(f"  -> 解析到 {len(questions)} 题")
        all_questions.extend(questions)

    if not all_questions:
        print("[ERROR] 没有解析到任何题目")
        return

    print(f"\n[INFO] 共解析到 {len(all_questions)} 道题目")

    # 显示统计
    from collections import Counter
    cats = Counter(q['category'] for q in all_questions)
    for cat, count in cats.items():
        print(f"  {cat}: {count} 题")

    # 预览前5题
    print(f"\n{'='*50}")
    print("预览（前5题）:")
    for i, q in enumerate(all_questions[:5], 1):
        print(f"\n  {i}. {q['content'][:60]}")
        for opt in q['options'][:4]:
            print(f"     {opt}")
        if len(q['options']) > 4:
            print(f"     ... 共 {len(q['options'])} 个选项")
        print(f"     答案: {q['answer']}")

    # 确认（--yes 跳过交互）
    if '--yes' in sys.argv:
        print(f"\n[INFO] --yes 模式，直接导入")
    else:
        confirm = input(f"\n确认清空现有题库并导入这 {len(all_questions)} 题？(y/n): ").strip().lower()
        if confirm != 'y':
            print("[INFO] 已取消")
            return

    # 导入
    conn = get_connection()
    cursor = conn.cursor()

    # 清空
    cursor.execute('DELETE FROM questions')
    print("[OK] 已清空原有题库")

    imported = 0
    skipped = 0
    for q in all_questions:
        if len(q['options']) < 2:
            print(f"  [WARN] 跳过（选项不足）: {q['content'][:40]}")
            skipped += 1
            continue
        if not q['answer']:
            print(f"  [WARN] 跳过（无答案）: {q['content'][:40]}")
            skipped += 1
            continue
        try:
            cursor.execute('''
                INSERT INTO questions (category, question_type, content, options, answer, score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                q['category'],
                '单选题',
                q['content'],
                json.dumps(q['options'], ensure_ascii=False),
                q['answer'],
                q['score']
            ))
            imported += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"[OK] 导入完成！成功 {imported} 题，跳过 {skipped} 题")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
