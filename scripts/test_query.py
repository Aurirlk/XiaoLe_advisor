"""
测试查询脚本
"""
import sqlite3
from pathlib import Path

db_path = Path('data/zx_advisor.db')
conn = sqlite3.connect(str(db_path))

# 查询广东的录取数据
cursor = conn.execute(
    "SELECT u.name, s.year, s.min_score, s.lowest_rank "
    "FROM admission_scores s "
    "JOIN universities u ON u.id = s.university_id "
    "WHERE s.province = '广东' AND s.year = 2020 "
    "ORDER BY s.min_score DESC "
    "LIMIT 10"
)

print('广东省2020年录取数据（前10）:')
print('-' * 60)
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}分, 位次{row[2]}')

# 统计总数
cursor = conn.execute('SELECT COUNT(*) FROM admission_scores')
total = cursor.fetchone()[0]
print(f'\n总记录数: {total}')

# 统计大学数量
cursor = conn.execute('SELECT COUNT(*) FROM universities')
uni_count = cursor.fetchone()[0]
print(f'大学数量: {uni_count}')

# 按省份统计
print('\n按省份统计（前10）:')
cursor = conn.execute(
    "SELECT province, COUNT(*) as count "
    "FROM admission_scores "
    "GROUP BY province "
    "ORDER BY count DESC "
    "LIMIT 10"
)
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}条')

conn.close()
