# 用户文档目录

将以下格式的文档放入此目录，系统会自动解析并加入 RAG 知识库：

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| Markdown | `.md` | 文本内容原样提取，按段落分块 |
| CSV | `.csv` | 表格数据按行列拼接为文本 |
| PDF | `.pdf` | 需要 `pdfplumber` 库（`pip install pdfplumber`） |
| 纯文本 | `.txt` | 文本内容原样提取 |

放入文档后，运行以下命令重建 RAG 索引：

```bash
python -m scripts.build_rag_index
```

然后通过 API 同步到向量库：

```bash
curl -X POST http://127.0.0.1:8000/rag/sync-from-json
```
