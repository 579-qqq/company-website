"""数据库初始化脚本 - 创建公司官网所需的表结构和示例数据"""
import sqlite3
import os

# 数据库文件路径（在项目根目录）
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'company.db')


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库：创建表并插入示例数据"""
    conn = get_connection()
    cursor = conn.cursor()

    # ==========================================
    # 1. 证书查询相关表
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,              -- 姓名
            id_number TEXT NOT NULL,         -- 身份证号码
            cert_name TEXT NOT NULL,         -- 证书名称
            cert_number TEXT NOT NULL UNIQUE, -- 证书编号
            issue_date TEXT NOT NULL,        -- 发证日期
            expire_date TEXT,                -- 有效期至
            status TEXT DEFAULT '有效',       -- 状态：有效/过期/吊销
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==========================================
    # 2. 题库相关表
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,           -- 分类（如：基础知识、专业技能）
            question_type TEXT DEFAULT '单选题', -- 题目类型
            content TEXT NOT NULL,            -- 题目内容
            options TEXT NOT NULL,            -- 选项（JSON格式）
            answer TEXT NOT NULL,             -- 正确答案
            score INTEGER DEFAULT 1,          -- 分值
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==========================================
    # 3. 考试记录表
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_taker TEXT NOT NULL,         -- 考生姓名
            score INTEGER NOT NULL,           -- 得分
            total_questions INTEGER NOT NULL, -- 总题数
            correct_count INTEGER NOT NULL,   -- 正确数
            answers TEXT,                     -- 答题详情（JSON格式）
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')

    # ==========================================
    # 插入示例证书数据
    # ==========================================
    sample_certificates = [
        ('张三', '110101199001011234', '软件工程师（高级）', 'CERT-2024-0001', '2024-01-15', '2027-01-15', '有效'),
        ('李四', '110101198505202356', '网络工程师（中级）', 'CERT-2024-0002', '2024-03-20', '2027-03-20', '有效'),
        ('王五', '110101199512033478', '数据分析师', 'CERT-2024-0003', '2024-06-10', '2026-06-10', '有效'),
        ('赵六', '110101198807154567', '信息安全工程师', 'CERT-2023-0004', '2023-09-01', '2026-09-01', '过期'),
        ('张三', '110101199001011234', '项目管理师', 'CERT-2024-0005', '2024-11-01', '2027-11-01', '有效'),
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO certificates (name, id_number, cert_name, cert_number, issue_date, expire_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sample_certificates)

    # ==========================================
    # 插入示例题库数据
    # ==========================================
    sample_questions = [
        # 基础知识类
        ('基础知识', '单选题',
         'Python 中，以下哪个关键字用于定义函数？',
         '["A. define", "B. function", "C. def", "D. func"]',
         'C', 2),
        ('基础知识', '单选题',
         '在 HTTP 协议中，状态码 404 表示什么？',
         '["A. 服务器内部错误", "B. 页面未找到", "C. 请求成功", "D. 重定向"]',
         'B', 2),
        ('基础知识', '单选题',
         'SQL 中用于查询数据的关键字是？',
         '["A. INSERT", "B. UPDATE", "C. SELECT", "D. DELETE"]',
         'C', 2),
        ('基础知识', '单选题',
         '以下哪个不是面向对象编程的特性？',
         '["A. 封装", "B. 继承", "C. 多态", "D. 递归"]',
         'D', 2),
        ('基础知识', '单选题',
         '在 HTML 中，哪个标签用于创建超链接？',
         '["A. <link>", "B. <a>", "C. <href>", "D. <url>"]',
         'B', 2),
        # 专业技能类
        ('专业技能', '单选题',
         'Flask 框架中，用于处理 URL 路由的装饰器是？',
         '["A. @app.route()", "B. @app.url()", "C. @app.path()", "D. @app.endpoint()"]',
         'A', 3),
        ('专业技能', '单选题',
         '在 Git 中，将暂存区的修改提交到本地仓库使用什么命令？',
         '["A. git push", "B. git commit", "C. git add", "D. git merge"]',
         'B', 3),
        ('专业技能', '单选题',
         '以下哪种数据库是关系型数据库？',
         '["A. MongoDB", "B. Redis", "C. SQLite", "D. Elasticsearch"]',
         'C', 3),
        ('专业技能', '单选题',
         'CSS 中，让元素水平居中的正确方式是？',
         '["A. text-align: center", "B. align: center", "C. horizontal-align: center", "D. position: center"]',
         'A', 3),
        ('专业技能', '单选题',
         'RESTful API 中，用于更新资源的 HTTP 方法是？',
         '["A. GET", "B. POST", "C. PUT", "D. DELETE"]',
         'C', 3),
    ]

    cursor.executemany('''
        INSERT INTO questions (category, question_type, content, options, answer, score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_questions)

    conn.commit()
    conn.close()
    print(f"[OK] 数据库初始化成功！文件位置: {DB_PATH}")
    print(f"   - 已插入 {len(sample_certificates)} 条证书数据")
    print(f"   - 已插入 {len(sample_questions)} 道题目")


if __name__ == '__main__':
    # 如果数据库已存在，询问是否覆盖
    if os.path.exists(DB_PATH):
        choice = input("数据库已存在，是否重建？(y/n): ").strip().lower()
        if choice == 'y':
            os.remove(DB_PATH)
            print("已删除旧数据库")
            init_database()
        else:
            print("保持现有数据库不变")
    else:
        init_database()
