"""
填充示例课程数据
运行: python database/seed_courses.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'company.db')

COURSES = [
    {
        'title': 'ISO9001质量管理体系内审员培训',
        'cover_image': '',
        'description': '全面掌握ISO9001:2015标准要求，学会内部审核的方法与技巧，能够独立组织企业内部审核工作。适合质量管理人员、内审员、体系工程师。',
        'price': 29900,        # ¥299
        'original_price': 59900,
        'status': 'published',
        'sort_order': 1,
        'chapters': [
            {'title': '第1章：ISO9001标准概述与发展历程', 'duration': 1800, 'sort_order': 1, 'is_free': 1},
            {'title': '第2章：质量管理七大原则', 'duration': 2400, 'sort_order': 2},
            {'title': '第3章：组织环境与领导作用（第4-5章）', 'duration': 3000, 'sort_order': 3},
            {'title': '第4章：策划与风险应对（第6章）', 'duration': 2700, 'sort_order': 4},
            {'title': '第5章：支持过程（第7章）', 'duration': 2400, 'sort_order': 5},
            {'title': '第6章：运行控制（第8章）', 'duration': 3600, 'sort_order': 6},
            {'title': '第7章：绩效评价（第9章）', 'duration': 1800, 'sort_order': 7},
            {'title': '第8章：改进（第10章）', 'duration': 1800, 'sort_order': 8},
            {'title': '第9章：内部审核流程与技巧', 'duration': 3000, 'sort_order': 9},
            {'title': '第10章：审核报告编写与不符合项整改', 'duration': 2400, 'sort_order': 10},
        ]
    },
    {
        'title': '精益生产与6S现场管理实战',
        'cover_image': '',
        'description': '从理论到实践，系统学习精益生产核心工具与6S管理方法。包含大量工厂实战案例，学完即可在企业推行。适合生产管理人员、班组长、IE工程师。',
        'price': 39900,        # ¥399
        'original_price': 79900,
        'status': 'published',
        'sort_order': 2,
        'chapters': [
            {'title': '第1章：精益生产理念与起源', 'duration': 1800, 'sort_order': 1, 'is_free': 1},
            {'title': '第2章：现场6S管理详解', 'duration': 3000, 'sort_order': 2},
            {'title': '第3章：目视化管理与看板系统', 'duration': 2400, 'sort_order': 3},
            {'title': '第4章：标准作业与线平衡', 'duration': 2700, 'sort_order': 4},
            {'title': '第5章：快速换模（SMED）', 'duration': 2400, 'sort_order': 5},
            {'title': '第6章：价值流图分析（VSM）', 'duration': 3000, 'sort_order': 6},
            {'title': '第7章：拉动式生产与Kanban', 'duration': 2400, 'sort_order': 7},
            {'title': '第8章：A3问题解决法', 'duration': 2700, 'sort_order': 8},
        ]
    },
    {
        'title': '绩效管理与薪酬体系设计',
        'cover_image': '',
        'description': '学会设计科学合理的绩效考核方案与薪酬激励体系，让员工从"要我做"变成"我要做"。适合HR经理、企业高管、部门负责人。',
        'price': 19900,        # ¥199
        'original_price': 39900,
        'status': 'published',
        'sort_order': 3,
        'chapters': [
            {'title': '第1章：绩效管理的基本概念与误区', 'duration': 1800, 'sort_order': 1, 'is_free': 1},
            {'title': '第2章：KPI指标体系设计方法', 'duration': 3000, 'sort_order': 2},
            {'title': '第3章：OKR目标管理法实战', 'duration': 2400, 'sort_order': 3},
            {'title': '第4章：360度评估与行为锚定法', 'duration': 2400, 'sort_order': 4},
            {'title': '第5章：薪酬结构设计与岗位评估', 'duration': 3000, 'sort_order': 5},
            {'title': '第6章：奖金与股权激励机制', 'duration': 2700, 'sort_order': 6},
        ]
    },
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查是否已有课程数据
    cursor.execute('SELECT COUNT(*) FROM courses')
    if cursor.fetchone()[0] > 0:
        print('[SKIP] 课程数据已存在，跳过填充')
        conn.close()
        return

    for course in COURSES:
        chapters = course.pop('chapters')
        cursor.execute('''
            INSERT INTO courses (title, cover_image, description, price, original_price, status, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            course['title'], course['cover_image'], course['description'],
            course['price'], course['original_price'], course['status'], course['sort_order']
        ))
        course_id = cursor.lastrowid

        for ch in chapters:
            cursor.execute('''
                INSERT INTO chapters (course_id, title, duration, sort_order, is_free)
                VALUES (?, ?, ?, ?, ?)
            ''', (course_id, ch['title'], ch['duration'], ch['sort_order'], ch.get('is_free', 0)))

        print(f'[OK] 课程已添加: {course["title"]} ({len(chapters)}章)')

    conn.commit()
    conn.close()
    print(f'[OK] 共填充 {len(COURSES)} 门课程')

if __name__ == '__main__':
    seed()
