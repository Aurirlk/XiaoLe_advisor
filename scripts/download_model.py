"""
下载 SentenceTransformer 模型到本地
"""
from sentence_transformers import SentenceTransformer
from pathlib import Path

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
LOCAL_DIR = Path(__file__).resolve().parent.parent / "data" / "models" / MODEL_NAME

print(f"下载模型: {MODEL_NAME}")
print(f"保存到: {LOCAL_DIR}")

# 下载并保存到本地
model = SentenceTransformer(MODEL_NAME)
model.save(str(LOCAL_DIR))

print(f"下载完成！模型已保存到: {LOCAL_DIR}")
print(f"文件大小: {sum(f.stat().st_size for f in LOCAL_DIR.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")
