"""
统一题库导入工具
支持：
  - .docx 文件（直接用 python-docx）
  - .doc  文件（通过 PowerShell COM 自动化调用 Word 读取）
  - 纯文本 .txt 文件

用法：
    python database/import_questions.py C:\路径\你的题库.doc
    python database/import_questions.py C:\路径\你的题库.docx
    python database/import_questions.py C:\路径\你的题库.txt
"""
import sys
import os
import re
import json
import subprocess
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'company.db')


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
        # 统一换行符为 \n
        $text = $text -replace "\\r\\n", "`n" -replace "\\r", "`n"
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Write-Output $text
    }} finally {{
        $word.Quit()
    }}
    '''
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', ps_script],
        capture_output=True, text=True, encoding='utf-8', timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"PowerShell 提取失败: {result.stderr}")
    return result.stdout


def extract_text_from_docx(filepath):
    """用 python-docx 从 .docx 提取纯文本"""
    from docx import Document
    doc = Document(filepath)
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
    return '\n'.join(lines)


def extract_text_from_txt(filepath):
    """直接读取 .txt 文件"""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        return f.read()


def read_file(filepath):
    """根据扩展名选择读取方式"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.doc':
        print("[INFO] 检测到 .doc 格式，通过 Word 转换...")
        return extract_text_from_doc(filepath)
    elif ext == '.docx':
        print("[INFO] 检测到 .docx 格式...")
        return extract_text_from_docx(filepath)
    elif ext == '.txt':
        print("[INFO] 检测到 .txt 格式...")
        return extract_text_from_txt(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def parse_questions(text, category, default_score):
    """
    智能解析题目文本，用状态机方式处理各种格式：

    格式1（编号+字母选项）：
        1、题目内容  A、选项1  B、选项2  C、选项3  D、选项4  答案：D

    格式2（无编号+无字母选项）：
        题目内容
        选项文本1
        选项文本2
        答案：A

    格式3（混合格式）
    """
    # 统一换行符（兼容 Windows/Mac/Linux 换行）
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    lines = text.split('\n')
    option_letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    questions = []

    # 状态: None=等待新题, 'question'=收集中, 'has_options'=已有选项, 'done'=已回答
    current = None

    def start_new_question(content):
        nonlocal current
        current = {
            'category': category,
            'content': content,
            'options': [],
            'answer': '',
            'score': default_score
        }

    def save_current():
        nonlocal current
        if current and current.get('options') and current.get('answer'):
            questions.append(current)
            current = None
            return True
        return False

    def looks_complete_question(text):
        """判断题目文本是否已完整（不需要续行）"""
        if len(text) < 10:
            return False  # 太短，需要续行
        # 以括号结尾，通常是完整的（如 "下列哪个正确(    )"）
        if re.search(r'[（(][\s]*[）)]$', text):
            return True
        # 以问号/句号/冒号结尾
        if re.search(r'[？?。：:]$', text):
            return True
        # 包含常见疑问词
        if re.search(r'(什么|哪些|哪个|如何|哪个|是否|可否|为什么|怎样)', text):
            return True
        # 超过60字，通常完整
        if len(text) > 60:
            return True
        return False

    def looks_like_option_text(text):
        """判断文本是否像是选项（无字母前缀时）"""
        # 常见选项关键词
        option_keywords = [
            '以上全部', '以上都是', '以上都对', '以上全对',
            '以上全不是', '以上全是', '以上都不对',
            'A+B+C', 'A+B', 'B+C', 'A+B+C+D', 'A+C', 'B+D',
            '书面定单', '电话要货', '任何方式',
        ]
        for kw in option_keywords:
            if text.startswith(kw) or text == kw:
                return True
        # 短文本通常更可能是选项（< 30字）
        if len(text) <= 30:
            return True
        return False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 跳过纯标签行（单选题、多选题 等）
        if re.match(r'^[单选多选判]+\s*题\s*$', line):
            continue

        # === 判断行类型 ===
        is_numbered = bool(re.match(r'^[\(（]?\d+[\)）、.．]', line))
        is_answer = bool(re.match(r'^(?:正确)?答案[：:]\s*([A-Fa-f])', line))
        has_letter_prefix = bool(re.match(r'^[A-Fa-f][.、．\s]', line))

        # ---- 情况1: 答案行 ----
        if is_answer:
            if current and not current['answer']:
                m = re.match(r'^(?:正确)?答案[：:]\s*([A-Fa-f])', line)
                current['answer'] = m.group(1).upper()
                save_current()
            continue

        # ---- 情况2: 编号开头 → 新题目 ----
        if is_numbered:
            save_current()
            content = re.sub(r'^[\(（]?\d+[\)）、.．\s]+', '', line, count=1).strip()
            start_new_question(content)
            continue

        # ---- 情况3: 有字母前缀的选项行 (A. xxx 或 A、xxx) ----
        if has_letter_prefix:
            if current and not current['answer']:
                m = re.match(r'^([A-Fa-f])[.、．\s]+(.*)', line)
                if m:
                    letter = m.group(1).upper()
                    opt_text = m.group(2).strip()
                    current['options'].append(f"{letter}. {opt_text}")
                continue

        # ---- 情况4: 其他内容行 ----
        if current and current['answer']:
            save_current()

        if current is None:
            # 没有活跃题目 → 这行就是题目内容
            start_new_question(line)
        elif not current['answer']:
            if current['options']:
                # 已有选项 → 这是无字母前缀的额外选项
                idx = len(current['options'])
                letter = option_letters[idx] if idx < len(option_letters) else '?'
                current['options'].append(f"{letter}. {line}")
            else:
                # 还没有选项 → 判断是否应作为选项处理
                if looks_complete_question(current['content']) or looks_like_option_text(line):
                    # 题目看起来已完整，这行是选项
                    idx = len(current['options'])
                    letter = option_letters[idx]
                    current['options'].append(f"{letter}. {line}")
                else:
                    # 追加到题目内容（多行题目）
                    current['content'] += line

    # 保存最后一题
    save_current()
    return questions


def import_questions(questions, clear_first=False):
    """导入题目到数据库"""
    if not questions:
        print("[ERROR] 没有解析到有效题目")
        return

    conn = get_connection()
    cursor = conn.cursor()

    if clear_first:
        cursor.execute('DELETE FROM questions')
        print("[OK] 已清空原有题库")

    imported = 0
    skipped = 0
    for q in questions:
        if len(q['options']) < 2:
            print(f"  [WARN] 跳过（选项数={len(q['options'])}）: {q['content'][:30]}")
            skipped += 1
            continue
        if not q['answer']:
            print(f"  [WARN] 跳过（无答案）: {q['content'][:30]}")
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
    print(f"\n{'='*40}")
    print(f"[OK] 成功导入 {imported} 题，跳过 {skipped} 题")
    print(f"{'='*40}")


def main():
    if len(sys.argv) < 2:
        print("用法: python database/import_questions.py <文件路径> [--clear]")
        print()
        print("示例:")
        print("  python database/import_questions.py C:\\Users\\36465\\Desktop\\单选.doc")
        print("  python database/import_questions.py C:\\Users\\36465\\Desktop\\单选.docx")
        print("  python database/import_questions.py C:\\Users\\36465\\Desktop\\题库.txt")
        print("  python database/import_questions.py C:\\Users\\36465\\Desktop\\单选.doc --clear")
        print()
        print("支持格式:")
        print("  1. 题目内容")
        print("     A. 选项1")
        print("     B. 选项2")
        print("     C. 选项3")
        print("     D. 选项4")
        print("     答案：D")
        sys.exit(1)

    filepath = sys.argv[1]
    clear_first = '--clear' in sys.argv

    if not os.path.exists(filepath):
        print(f"[ERROR] 文件不存在: {filepath}")
        sys.exit(1)

    # 1. 读取文本
    print(f"[INFO] 正在读取: {filepath}")
    try:
        text = read_file(filepath)
    except Exception as e:
        print(f"[ERROR] 读取失败: {e}")
        print("提示: .doc 文件需要安装 Microsoft Word")
        sys.exit(1)

    # 2. 输入分类
    category = input("请输入分类名称（如: ISO9001、基础知识）: ").strip()
    if not category:
        category = '未分类'

    score_str = input("默认分值（回车=2分）: ").strip()
    default_score = int(score_str) if score_str.isdigit() else 2

    # 3. 解析
    print("[INFO] 正在解析题目...")
    questions = parse_questions(text, category, default_score)

    if not questions:
        print("[ERROR] 未能解析出任何题目，请检查文件格式")
        return

    print(f"\n[INFO] 解析到 {len(questions)} 道题目")

    # 4. 预览
    print(f"\n{'='*40}")
    print("解析预览（前3题）:")
    for i, q in enumerate(questions[:3], 1):
        print(f"\n  {i}. {q['content']}")
        for opt in q['options']:
            print(f"     {opt}")
        print(f"     答案: {q['answer']}")

    # 5. 确认导入
    confirm = input(f"\n确认导入这 {len(questions)} 道题？(y/n): ").strip().lower()
    if confirm == 'y':
        import_questions(questions, clear_first)
    else:
        print("[INFO] 已取消")


if __name__ == '__main__':
    main()
