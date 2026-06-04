# Golden Dataset 评测说明

## 文件说明
- `golden_dataset.json`: 黄金测试集样例。
- `golden_eval_report.json`: 脚本输出的评测报告。

## 如何运行
在项目根目录执行：

```bash
python scripts/evaluate_golden.py
```

## 当前评测维度（规则版）
- Faithfulness（基础版）：
  - 检查回答是否命中 `expected_keywords`。
- Persona Alignment（基础版）：
  - 检查回答是否命中 `persona_keywords`。

## 注意
- 当前是轻量脚手架，目标是上线前快速回归。
- 后续可接入 Ragas，将规则评测替换为更完整的语义评估。
