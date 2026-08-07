"""
一键导入脚本 - 整合所有数据导入和索引构建步骤

使用方法:
    python scripts/import_all.py          # 完整导入
    python scripts/import_all.py --skip-gaokao  # 跳过高考数据导入
    python scripts/import_all.py --skip-rag     # 跳过RAG索引构建
    python scripts/import_all.py --stats        # 仅显示统计信息
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def print_banner(text: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def step_init_sqlite() -> bool:
    """步骤1: 初始化SQLite数据库"""
    print_banner("步骤1/4: 初始化SQLite数据库")
    try:
        from scripts.init_sqlite import init_sqlite
        path = init_sqlite()
        print(f"✅ 数据库已就绪: {path}")
        return True
    except Exception as e:
        print(f"❌ SQLite初始化失败: {e}")
        return False


def step_import_gaokao() -> bool:
    """步骤2: 导入高考录取数据"""
    print_banner("步骤2/4: 导入高考录取数据")
    try:
        from scripts.import_gaokao_from_xlsx import import_all_xlsx, show_stats
        import_all_xlsx(dry_run=False)
        show_stats()
        return True
    except Exception as e:
        print(f"❌ 高考数据导入失败: {e}")
        return False


def step_build_rag_index() -> bool:
    """步骤3: 构建RAG索引"""
    print_banner("步骤3/4: 构建RAG索引")
    try:
        from scripts.build_rag_index import main as build_rag_index
        build_rag_index()
        print("✅ RAG索引构建完成")
        return True
    except Exception as e:
        print(f"❌ RAG索引构建失败: {e}")
        return False


def step_show_stats() -> None:
    """步骤4: 显示统计信息"""
    print_banner("步骤4/4: 数据统计")
    
    db_path = ROOT / "data" / "zx_advisor.db"
    if not db_path.exists():
        print("❌ 数据库不存在")
        return
    
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    
    # 院校统计
    cursor = conn.execute("SELECT COUNT(*) FROM universities")
    uni_count = cursor.fetchone()[0]
    print(f"\n📊 院校总数: {uni_count}")
    
    # 分数线统计
    cursor = conn.execute("SELECT COUNT(*) FROM admission_scores")
    score_count = cursor.fetchone()[0]
    print(f"📊 分数线记录: {score_count}")
    
    # 按省份统计
    cursor = conn.execute("""
        SELECT province, COUNT(*) as count 
        FROM admission_scores 
        GROUP BY province 
        ORDER BY count DESC 
        LIMIT 10
    """)
    print("\n📊 各省份数据量 (Top 10):")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}条")
    
    # 按年份统计
    cursor = conn.execute("""
        SELECT year, COUNT(*) as count 
        FROM admission_scores 
        GROUP BY year 
        ORDER BY year DESC
    """)
    print("\n📊 各年份数据量:")
    for row in cursor.fetchall():
        print(f"  {row[0]}年: {row[1]}条")
    
    # RAG索引统计
    rag_path = ROOT / "data" / "vector_store" / "zx_experience.json"
    if rag_path.exists():
        import json
        docs = json.loads(rag_path.read_text(encoding="utf-8"))
        print(f"\n📊 RAG文档数: {len(docs)}")
    else:
        print("\n📊 RAG索引: 未创建")
    
    # 文档目录统计
    docs_dir = ROOT / "data" / "documents"
    if docs_dir.exists():
        doc_count = sum(1 for f in docs_dir.rglob("*") if f.is_file() and f.suffix in ('.md', '.txt', '.pdf', '.csv'))
        print(f"📊 知识库文档数: {doc_count}")
    
    conn.close()


def main():
    start_time = time.time()
    
    print_banner("小乐AI - 一键数据导入")
    print(f"项目根目录: {ROOT}")
    
    # 解析参数
    args = sys.argv[1:]
    skip_gaokao = "--skip-gaokao" in args
    skip_rag = "--skip-rag" in args
    stats_only = "--stats" in args
    
    if stats_only:
        step_show_stats()
        return
    
    # 步骤1: 初始化数据库
    if not step_init_sqlite():
        print("\n❌ 数据库初始化失败，终止导入")
        return
    
    # 步骤2: 导入高考数据
    if not skip_gaokao:
        step_import_gaokao()
    else:
        print_banner("步骤2/4: 跳过高考数据导入 (--skip-gaokao)")
    
    # 步骤3: 构建RAG索引
    if not skip_rag:
        step_build_rag_index()
    else:
        print_banner("步骤3/4: 跳过RAG索引构建 (--skip-rag)")
    
    # 步骤4: 显示统计
    step_show_stats()
    
    elapsed = time.time() - start_time
    print_banner(f"导入完成! 耗时: {elapsed:.1f}秒")
    
    print("\n下一步:")
    print("  1. 启动服务: python -m api.main")
    print("  2. 访问界面: http://127.0.0.1:5000")
    print("  3. API文档: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    main()
