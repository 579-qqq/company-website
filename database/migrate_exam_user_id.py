"""迁移脚本：为 exam_records 表添加 user_id 列"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'company.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查 user_id 列是否已存在
    cursor.execute("PRAGMA table_info(exam_records)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'user_id' not in columns:
        print(">>> 添加 exam_records.user_id 列...")
        cursor.execute("ALTER TABLE exam_records ADD COLUMN user_id INTEGER REFERENCES users(id)")
        conn.commit()
        print("[OK] 迁移完成")
    else:
        print("[OK] user_id 列已存在，跳过迁移")

    conn.close()

if __name__ == '__main__':
    migrate()
