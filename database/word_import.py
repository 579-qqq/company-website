"""
Word 题库导入工具
支持格式：
    1. 题目内容
       A. 选项1
       B. 选项2
       C. 选项3
       D. 选项4
       答案：A

    2. 下一题...
       ...

用法：python database/word_import.py <Word文件路径>
"""
import sys
import os
import re
import sqlite3
from docx import Document

# 确保能找到项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'company.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_questions_from_docx(filepath):
    """
    从 Word 文档中解析题目，返回题目列表。
    每道题格式：字典包含 category, content, options, answer, score
    """
    if not os.path.exists(filepath):
        print(f"[ERROR] 文件不存在: {filepath}")
        return []

    doc = Document(filepath)
    questions = []
    current = None  # 正在解析的题目
    # 正则：题号开头，如 "1." "2." "(1)" "1、"
    question_pattern = re.compile(r'^[\(（]?\d+[\)）、.．]\s*(.*)')
    # 正则：选项行，如 "A." "A、" "B." "B、"
    option_pattern = re.compile(r'^([A-Da-d])[.、．\s]\s*(.*)')
    # 正则：答案行，如 "答案：A" "答案:A" "正确答案：A"
    answer_pattern = re.compile(r'^(?:正确)?答案[：:]\s*([A-Da-d])')

    category = input("请输入这批题目的分类名称（如：基础知识、专业技能）: ").strip()
    if not category:
        category = '未分类'

    default_score = input("请输入每题默认分值（直接回车默认为2分）: ").strip()
    default_score = int(default_score) if default_score.isdigit() else 2

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # 检查是否是题号开头
        q_match = question_pattern.match(text)
        if q_match:
            # 保存上一题
            if current:
                if current.get('content') and current.get('options'):
                    questions.append(current)
                else:
                    print(f"[WARN] 跳过不完整的题目: {current.get('content', '空')[:30]}")

            # 新题目
            content_text = q_match.group(1).strip()
            current = {
                'category': category,
                'content': content_text,
                'options': [],
                'answer': '',
                'score': default_score
            }
            continue

        # 检查是否是选项行
        o_match = option_pattern.match(text)
        if o_match and current:
            letter = o_match.group(1).upper()
            option_text = o_match.group(2).strip()
            current['options'].append(f"{letter}. {option_text}")
            continue

        # 检查是否是答案行
        a_match = answer_pattern.match(text)
        if a_match and current:
            current['answer'] = a_match.group(1).upper()
            continue

        # 其他文本行：如果正在解析题目，追加到题目内容（支持多行题目）
        if current:
            current['content'] += text

    # 保存最后一题
    if current:
        if current.get('content') and current.get('options') and current.get('answer'):
            questions.append(current)
        else:
            print(f"[WARN] 跳过不完整的题目: {current.get('content', '空')[:30]}")

    return questions


def import_questions(questions, clear_first=False):
    """将解析出的题目导入数据库"""
    if not questions:
        print("[ERROR] 没有读到有效题目")
        return

    conn = get_connection()
    cursor = conn.cursor()

    if clear_first:
        confirm = input("⚠️  是否清空已有题库再导入？(y/n): ").strip().lower()
        if confirm == 'y':
            cursor.execute('DELETE FROM questions')
            print("[OK] 已清空原有题库")
        else:
            print("[INFO] 保留原有题库，追加导入")

    imported = 0
    skipped = 0
    for q in questions:
        # 校验：确保有4个选项
        if len(q['options']) != 4:
            print(f"[WARN] 跳过选项数不对的题目 ({len(q['options'])}个选项): {q['content'][:30]}")
            skipped += 1
            continue
        # 校验：必须有答案
        if not q['answer']:
            print(f"[WARN] 跳过无答案的题目: {q['content'][:30]}")
            skipped += 1
            continue
        # 校验：答案必须在 A-D 范围内
        if q['answer'] not in ['A', 'B', 'C', 'D']:
            print(f"[WARN] 跳过答案格式不对的题目: 答案={q['answer']}")
            skipped += 1
            continue

        try:
            import json
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
            print(f"[ERROR] 导入失败: {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\n{'='*40}")
    print(f"[OK] 导入完成！")
    print(f"   - 成功导入: {imported} 题")
    print(f"   - 跳过: {skipped} 题")
    print(f"   - 分类: {questions[0]['category']}")
    print(f"{'='*40}")

    # 打印预览
    print(f"\n📋 导入预览（前3题）:")
    for i, q in enumerate(questions[:3], 1):
        print(f"  {i}. {q['content']}")
        for opt in q['options']:
            print(f"     {opt}")
        print(f"     答案: {q['answer']}")
        print()


def main():
    if len(sys.argv) < 2:
        print("用法: python database/word_import.py <Word文件路径>")
        print("示例: python database/word_import.py D:\\我的题库.docx")
        print()
        print("支持的 Word 文档格式：")
        print("  1. 题目内容")
        print("     A. 选项1")
        print("     B. 选项2")
        print("     C. 选项3")
        print("     D. 选项4")
        print("     答案：A")
        print()
        print("  2. 下一题...")
        sys.exit(1)

    filepath = sys.argv[1]

    print(f"[INFO] 正在解析: {filepath}")
    questions = parse_questions_from_docx(filepath)

    if not questions:
        print("[ERROR] 未能从文档中解析出任何题目，请检查格式")
        print("\n支持的格式示例：")
        print("  1. 以下哪个是 Python 的关键字？")
        print("     A. define")
        print("     B. function")
        print("     C. def")
        print("     D. func")
        print("     答案：C")
        return

    print(f"\n[INFO] 共解析出 {len(questions)} 道题目")

    # 显示解析结果预览
    print("\n📋 解析预览（前3题）:")
    for i, q in enumerate(questions[:3], 1):
        print(f"  {i}. {q['content']}")
        for opt in q['options']:
            print(f"     {opt}")
        print(f"     答案: {q['answer']}")

    confirm = input(f"\n确认导入这 {len(questions)} 道题？(y/n): ").strip().lower()
    if confirm == 'y':
        import_questions(questions)
    else:
        print("[INFO] 已取消导入")


if __name__ == '__main__':
    main()
