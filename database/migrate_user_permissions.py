"""
迁移脚本：创建 user_permissions 表，替代 orders 支付流程
权限类型：course（课程）、exam（考试）
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'company.db')


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建权限表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            resource_type TEXT NOT NULL,
            resource_value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            granted_by INTEGER REFERENCES users(id),
            UNIQUE(user_id, resource_type, resource_value)
        )
    ''')

    # 从现有 orders 表迁移已付费用户 → course 权限
    cursor.execute('''
        INSERT OR IGNORE INTO user_permissions (user_id, resource_type, resource_value, created_at)
        SELECT user_id, 'course', CAST(course_id AS TEXT), paid_at
        FROM orders
        WHERE status = 'paid'
    ''')

    count = cursor.rowcount if cursor.rowcount > 0 else 0

    conn.commit()
    conn.close()

    print(f'[OK] user_permissions 表已创建，迁移了 {count} 条已有订单记录')


if __name__ == '__main__':
    migrate()
