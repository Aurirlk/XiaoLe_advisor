"""创建默认管理员账号"""
import sqlite3
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.auth import hash_password

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "zx_advisor.db"

def create_default_admin():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 检查是否已有管理员
    cursor.execute("SELECT id FROM user_profiles WHERE role = 'admin'")
    if cursor.fetchone():
        print("管理员账号已存在")
        conn.close()
        return
    
    # 创建默认管理员
    phone = "13800000000"
    password = "admin123"
    username = "管理员"
    password_hash = hash_password(password)
    
    cursor.execute(
        "INSERT INTO user_profiles (phone_number, username, password_hash, role) VALUES (?, ?, ?, 'admin')",
        (phone, username, password_hash)
    )
    
    conn.commit()
    conn.close()
    
    print("默认管理员账号已创建:")
    print(f"  手机号: {phone}")
    print(f"  密码: {password}")
    print(f"  角色: admin")

if __name__ == "__main__":
    create_default_admin()
