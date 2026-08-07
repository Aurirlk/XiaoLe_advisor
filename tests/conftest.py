"""pytest 全局配置

zxf conda 环境存在原生库（sentence_transformers/onnxruntime）加载顺序敏感问题：
后加载 `api.dependencies`（→ tools.vector_store → sentence_transformers）时可能 segfault。
对策：在收集阶段最早加载整条依赖链，先加载者建立稳定的原生库初始化顺序。
"""
from __future__ import annotations

import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

# 关键：让 sentence_transformers 链最早加载（先 import 者先初始化原生库）
import api.dependencies  # noqa: F401,E402
