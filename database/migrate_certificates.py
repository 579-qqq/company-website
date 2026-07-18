"""
数据库迁移脚本：给 certificates 表新增 photo_path 和 qualification_type 列
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'company.db')


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查列是否已存在
    cursor.execute("PRAGMA table_info(certificates)")
    columns = [col[1] for col in cursor.fetchall()]

    added = []

    if 'photo_path' not in columns:
        cursor.execute("ALTER TABLE certificates ADD COLUMN photo_path TEXT")
        added.append('photo_path')
        print("[OK] 已添加列: photo_path")
    else:
        print("[SKIP] photo_path 列已存在")

    if 'qualification_type' not in columns:
        cursor.execute("ALTER TABLE certificates ADD COLUMN qualification_type TEXT")
        added.append('qualification_type')
        print("[OK] 已添加列: qualification_type")
    else:
        print("[SKIP] qualification_type 列已存在")

    conn.commit()
    conn.close()

    if added:
        print(f"[DONE] 迁移完成，新增 {len(added)} 列: {', '.join(added)}")
    else:
        print("[DONE] 无需迁移，所有列已存在")


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] 数据库不存在: {DB_PATH}")
    else:
        migrate()
