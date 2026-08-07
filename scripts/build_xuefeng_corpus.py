"""
张雪峰对话语料入库脚本（2026-08-06）

用法：
  # 从 data/xuefeng_dialogues/ 目录读取 .txt/.md 文件入库
  python scripts/build_xuefeng_corpus.py

  # 或指定单个文件
  python scripts/build_xuefeng_corpus.py --file data/xx.md

语料格式：每个 .md/.txt 文件 = 一场对话，内部按"问/答"自然段落组织，
切块按轮次边界（见 tools/xuefeng_store._split_turns）。

内置 3 条种子示例（首次运行时写入，便于验证链路）：
  - 医学专业的选择逻辑
  - 冲稳保策略
  - 城市 vs 学校选择
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 种子语料（首次入库用，证明链路可用；后续替换为真实雪峰对话）
SEED_DIALOGUES = [
    {
        "source": "seed:2024直播-医学专业",
        "text": "家长问：孩子想学医，但学医周期长成本高，家庭预算怎么规划？\n"
                "张雪峰答：学医这事，你得先问自己三个问题：家里能不能供得起八年，"
                "孩子是不是真的能吃苦，你有没有耐心等回报。临床医学本科五年出来只能规培，"
                "规培三年工资三千，家里没底子的别硬冲。家庭预算必须先把八年成本算清楚，"
                "学医不是赌博，是长线投资。",
    },
    {
        "source": "seed:2023直播-冲稳保策略",
        "text": "学生问：600分能上什么大学？\n"
                "张雪峰答：600分这个段位，冲稳保必须按位次来，不按分数来，更不按情绪来。"
                "冲的院校往上找三千位次，稳的找同段位，保的往下找五千位次。"
                "记住报志愿是策略问题不是情绪问题，分数边缘不要硬冲热门，先保底再谈理想。",
    },
    {
        "source": "seed:2024访谈-城市还是学校",
        "text": "考生问：选城市重要还是选学校重要？\n"
                "张雪峰答：这问题得看你要干什么。要考公回老家，那城市不重要，"
                "选个录取分低的好学校拿文凭；要在外面闯，城市比学校重要，"
                "实习机会和人脉都在城市里。普通家庭的孩子，我建议学校优先于城市，"
                "因为好的学校带来的校友资源是实打实的。",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="雪峰语料入库")
    parser.add_argument("--file", type=str, default=None, help="单个语料文件（.txt/.md）")
    parser.add_argument("--force", action="store_true", help="重建语料库（覆盖去重缓存）")
    args = parser.parse_args()

    from tools.xuefeng_store import XuefengStore, _split_turns

    store = XuefengStore()
    dialogues = list(SEED_DIALOGUES)

    # 从 data/xuefeng_dialogues/ 读用户语料
    dial_dir = ROOT / "data" / "xuefeng_dialogues"
    if dial_dir.exists():
        for f in sorted(dial_dir.glob("*")):
            if f.suffix.lower() in (".txt", ".md"):
                dialogues.append({"source": f"user:{f.name}", "text": f.read_text(encoding="utf-8", errors="ignore")})
                print(f"[INFO] 读取语料: {f.name}")

    if args.file:
        f = Path(args.file)
        dialogues.append({"source": f"user:{f.name}", "text": f.read_text(encoding="utf-8", errors="ignore")})

    if not dialogues:
        print("[WARN] 无语料，使用内置种子")
        dialogues = SEED_DIALOGUES

    # 预览切块
    total_turns = sum(len(_split_turns(d["text"])) for d in dialogues)
    print(f"[INFO] 语料 {len(dialogues)} 场，预计切块 {total_turns}+")

    result = store.build_corpus(dialogues, force=args.force)
    print(f"[OK] 入库结果: {result}")

    # 验证检索
    if result.get("ok"):
        for q in ["学医要多少钱", "600分怎么报志愿", "选城市还是学校"]:
            hits = store.search(q, top_k=2)
            print(f"[TEST] query={q!r} → {len(hits)} 条")
            for h in hits[:2]:
                print(f"        [{h.get('match','?')}] {h.get('source','')[:30]} | {h.get('text','')[:36]}...")


if __name__ == "__main__":
    main()
