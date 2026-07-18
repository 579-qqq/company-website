"""
多种考试类型种子数据
预置 ISO 体系常见考试类型 + 示例题目
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'company.db')

EXAM_TYPES = [
    {
        'category': 'ISO9001质量管理体系内审员',
        'questions': [
            ('ISO9001标准的核心原则不包括以下哪项？', '["A. 以顾客为关注焦点","B. 领导作用","C. 利润最大化","D. 持续改进"]', 'C'),
            ('质量管理体系文件的类型包括？', '["A. 质量手册","B. 程序文件","C. 作业指导书","D. 以上都是"]', 'D'),
            ('内部审核的主要目的是？', '["A. 罚款","B. 检查体系符合性和有效性","C. 替换员工","D. 应付检查"]', 'B'),
        ]
    },
    {
        'category': 'ISO14001环境管理体系内审员',
        'questions': [
            ('ISO14001标准关注的核心是什么？', '["A. 质量管理","B. 环境管理","C. 安全管理","D. 财务管理"]', 'B'),
            ('环境因素识别应考虑哪些方面？', '["A. 废气排放","B. 废水排放","C. 噪声污染","D. 以上都是"]', 'D'),
            ('环境管理体系的PDCA中P代表什么？', '["A. 实施","B. 检查","C. 策划","D. 改进"]', 'C'),
        ]
    },
    {
        'category': 'ISO45001职业健康安全管理体系内审员',
        'questions': [
            ('ISO45001取代了哪个标准？', '["A. ISO9001","B. OHSAS18001","C. ISO14001","D. ISO22000"]', 'B'),
            ('危险源辨识应考虑以下哪些？', '["A. 常规活动","B. 非常规活动","C. 紧急情况","D. 以上都是"]', 'D'),
            ('安全管理的"三同时"不包括？', '["A. 同时设计","B. 同时施工","C. 同时验收","D. 同时投产使用"]', 'C'),
        ]
    },
    {
        'category': 'IATF16949汽车行业质量管理体系内审员',
        'questions': [
            ('IATF16949是基于哪个标准？', '["A. ISO9001","B. ISO14001","C. ISO45001","D. ISO22000"]', 'A'),
            ('汽车行业质量管理的核心工具不包括？', '["A. APQP","B. FMEA","C. SWOT","D. PPAP"]', 'C'),
            ('SPC的中文含义是？', '["A. 统计过程控制","B. 测量系统分析","C. 生产件批准程序","D. 产品质量先期策划"]', 'A'),
        ]
    },
    {
        'category': 'IATF16949 VDA6.3过程审核员',
        'questions': [
            ('VDA6.3主要关注什么审核？', '["A. 体系审核","B. 过程审核","C. 产品审核","D. 管理评审"]', 'B'),
            ('VDA6.3审核的评分等级不包括？', '["A. A级","B. B级","C. C级","D. E级"]', 'D'),
            ('过程审核中P2代表什么？', '["A. 产品和过程开发的策划","B. 产品和过程开发的实现","C. 供方管理","D. 生产过程分析"]', 'D'),
        ]
    },
    {
        'category': 'IATF16949 VDA6.5产品审核员',
        'questions': [
            ('VDA6.5主要关注什么审核？', '["A. 体系审核","B. 过程审核","C. 产品审核","D. 管理评审"]', 'C'),
            ('产品审核的主要目的是？', '["A. 验证产品符合规定要求","B. 检查生产设备","C. 审核财务报表","D. 评估员工绩效"]', 'A'),
            ('产品审核的频率应根据什么确定？', '["A. 产品重要性和质量状况","B. 天气情况","C. 节假日安排","D. 员工出勤率"]', 'A'),
        ]
    },
    {
        'category': 'ISO13485医疗器械质量管理体系内审员',
        'questions': [
            ('ISO13485主要应用于哪个行业？', '["A. 食品行业","B. 医疗器械行业","C. 汽车行业","D. 建筑行业"]', 'B'),
            ('医疗器械质量管理体系的核心要求不包括？', '["A. 风险管理","B. 可追溯性","C. 利润最大化","D. 文件控制"]', 'C'),
            ('ISO13485标准基于哪个标准框架？', '["A. ISO9001","B. ISO14001","C. ISO45001","D. ISO22000"]', 'A'),
        ]
    },
    {
        'category': 'QC080000有害物质管理体系内审员',
        'questions': [
            ('QC080000标准主要管控什么？', '["A. 质量成本","B. 有害物质","C. 生产进度","D. 人员培训"]', 'B'),
            ('RoHS指令限制的有害物质不包括？', '["A. 铅","B. 汞","C. 镉","D. 铁"]', 'D'),
            ('QC080000是基于哪个标准框架？', '["A. ISO9001","B. ISO14001","C. ISO45001","D. ISO22000"]', 'A'),
        ]
    },
    {
        'category': 'ESG环境社会治理管理体系内审员',
        'questions': [
            ('ESG中的E代表什么？', '["A. 经济","B. 环境","C. 教育","D. 能源"]', 'B'),
            ('ESG中的G代表什么？', '["A. 政府","B. 治理","C. 全球化","D. 成长"]', 'B'),
            ('ESG评价的主要维度不包括？', '["A. 环境绩效","B. 社会责任","C. 公司治理","D. 市场份额"]', 'D'),
        ]
    },
    {
        'category': '计量校准内校员',
        'questions': [
            ('计量校准的主要目的是？', '["A. 确保测量设备准确可靠","B. 增加产量","C. 减少员工","D. 降低电费"]', 'A'),
            ('校准与检定的主要区别是？', '["A. 校准是自愿的，检定是强制的","B. 没有区别","C. 校准是强制的","D. 检定是自愿的"]', 'A'),
            ('测量不确定度表示什么？', '["A. 测量结果的可靠性范围","B. 测量设备的品牌","C. 测量人员的学历","D. 测量环境温度"]', 'A'),
        ]
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = 0
    for exam in EXAM_TYPES:
        cat = exam['category']
        # 检查是否已有题目
        cursor.execute('SELECT COUNT(*) FROM questions WHERE category = ?', (cat,))
        existing = cursor.fetchone()[0]

        if existing > 0:
            print(f'[SKIP] {cat} 已有 {existing} 题')
            continue

        for content, options, answer in exam['questions']:
            cursor.execute('''
                INSERT INTO questions (category, question_type, content, options, answer, score)
                VALUES (?, '单选题', ?, ?, ?, 2)
            ''', (cat, content, options, answer))
            total += 1

        print(f'[OK] {cat} 新增 {len(exam["questions"])} 题')

    conn.commit()
    conn.close()

    if total > 0:
        print(f'\n[DONE] 共新增 {total} 道题目')
    else:
        print('\n[DONE] 所有类型已有题目，无需添加')

    # 显示统计
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT category, COUNT(*) FROM questions GROUP BY category ORDER BY COUNT(*) DESC')
    print('\n当前题库:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}题')
    conn.close()


if __name__ == '__main__':
    seed()
