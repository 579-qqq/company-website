"""
管理员设置脚本
用法: python database/set_admin.py <手机号>
示例: python database/set_admin.py 18316989790
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'company.db')


def set_admin(phone):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 确保 is_admin 列存在
    cursor.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'is_admin' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        print("[OK] 已添加 is_admin 列")

    # 查找用户
    cursor.execute("SELECT id, username, phone, is_admin FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    if not user:
        print(f"[ERROR] 未找到手机号 {phone} 的用户，请先注册")
        conn.close()
        return

    if user['is_admin']:
        print(f"[SKIP] 用户 {user['username']} (ID={user['id']}) 已是管理员")
    else:
        cursor.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user['id'],))
        conn.commit()
        print(f"[OK] 已将 {user['username']} (ID={user['id']}) 设为管理员")

    conn.close()


def list_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, phone, is_admin FROM users ORDER BY id")
    users = cursor.fetchall()
    print(f"\n当前用户 ({len(users)} 个):")
    print("-" * 50)
    for u in users:
        role = "管理员" if u['is_admin'] else "普通用户"
        print(f"  ID={u['id']:3d}  {u['username']:10s}  {u['phone']}  [{role}]")
    conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python database/set_admin.py <手机号>")
        print("      python database/set_admin.py --list  (查看所有用户)")
        if os.path.exists(DB_PATH):
            list_users()
        sys.exit(1)

    if sys.argv[1] == '--list':
        list_users()
    else:
        set_admin(sys.argv[1])
        list_users()
