from pathlib import Path
import csv
import io
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "zhangxuefeng-skill-main"
DOCUMENTS_ROOT = ROOT / "data" / "documents"


def _load_rag_config() -> dict:
    path = ROOT / "configs" / "rag_config.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("rag", {})


def _chunk_text(text: str, max_chunk: int = 1200) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= max_chunk:
            chunks.append(para)
        else:
            sentences = para.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n")
            current = ""
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(current) + len(s) <= max_chunk:
                    current += s
                else:
                    if current:
                        chunks.append(current)
                    current = s
            if current:
                chunks.append(current)
    return chunks


def _parse_pdf_text(file_path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber 未安装，请执行 pip install pdfplumber")

    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _parse_csv_text(file_path: Path) -> str:
    text_parts = []
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if headers:
            text_parts.append(" | ".join(headers))
        for row in reader:
            text_parts.append(" | ".join(row))
    return "\n".join(text_parts)


def _parse_markdown_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore").strip()


def _parse_txt_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore").strip()


FORMAT_PARSERS = {
    ".pdf": _parse_pdf_text,
    ".csv": _parse_csv_text,
    ".md": _parse_markdown_file,
    ".txt": _parse_txt_file,
}


def _push_to_elasticsearch(docs: list[dict], cfg: dict) -> None:
    endpoint = cfg.get("endpoint", "").rstrip("/")
    index_name = cfg.get("index", "")
    if not endpoint or not index_name:
        return

    for i, doc in enumerate(docs):
        payload = {"index": {"_index": index_name, "_id": i + 1}}
        bulk_body = f"{json.dumps(payload, ensure_ascii=False)}\n{json.dumps(doc, ensure_ascii=False)}\n"
        request = Request(
            url=f"{endpoint}/_bulk",
            data=bulk_body.encode("utf-8"),
            headers={"Content-Type": "application/x-ndjson"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=float(cfg.get("timeout_seconds", 2.0))) as response:
                _ = response.read()
        except (URLError, TimeoutError, ValueError) as exc:
            print(f"[WARN] ES 写入失败（已跳过）：{exc}")
            return


def _push_to_milvus(docs: list[dict], cfg: dict) -> None:
    host = cfg.get("host", "")
    port = cfg.get("port", 19530)
    collection_name = cfg.get("collection", "")
    if not host or not collection_name:
        return

    try:
        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
    except Exception as exc:
        print(f"[WARN] pymilvus 不可用（已跳过）：{exc}")
        return

    alias = "zx_ai_advisor_build"
    try:
        connections.connect(alias=alias, host=host, port=port)
        try:
            if not utility.has_collection(collection_name, using=alias):
                schema = CollectionSchema(
                    fields=[
                        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=200),
                        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4000),
                    ],
                    description="ZX experience text collection",
                )
                collection = Collection(name=collection_name, schema=schema, using=alias)
            else:
                collection = Collection(name=collection_name, using=alias)
            collection.insert([[doc.get("source", "") for doc in docs], [doc.get("text", "") for doc in docs]])
            collection.flush()
        finally:
            connections.disconnect(alias=alias)
    except Exception as exc:
        print(f"[WARN] Milvus 写入失败（已跳过）：{exc}")


def _scan_user_documents() -> list[dict]:
    docs = []
    if not DOCUMENTS_ROOT.exists():
        return docs

    for file_path in sorted(DOCUMENTS_ROOT.rglob("*")):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        if suffix not in FORMAT_PARSERS:
            continue

        rel_path = file_path.relative_to(DOCUMENTS_ROOT).as_posix()
        print(f"[INFO] 解析文档: {rel_path} ({suffix})")

        try:
            parser = FORMAT_PARSERS[suffix]
            text = parser(file_path)
        except Exception as exc:
            print(f"[WARN] 解析失败 {rel_path}: {exc}")
            continue

        if not text:
            continue

        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks[:500]):
            docs.append({
                "source": f"user:{rel_path}#{i + 1}",
                "text": chunk[:1200],
            })

    return docs


def main() -> None:
    docs: list[dict] = []

    # 1) 优先用 skill 资产生成语料
    if SKILL_ROOT.exists():
        candidates = [
            SKILL_ROOT / "SKILL.md",
            SKILL_ROOT / "examples" / "demo-conversation.md",
            *sorted((SKILL_ROOT / "references" / "research").glob("*.md")),
        ]
        for path in candidates:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue
            chunks = _chunk_text(text)
            for i, chunk in enumerate(chunks[:200]):
                docs.append({
                    "source": f"{path.relative_to(ROOT).as_posix()}#{i + 1}",
                    "text": chunk[:1200],
                })

    # 2) 扫描用户上传的文档 (md/csv/pdf/txt)
    user_docs = _scan_user_documents()
    if user_docs:
        docs.extend(user_docs)
        print(f"[INFO] 用户文档已加入索引: {len(user_docs)} 条")

    # 3) 若没有任何文档，写入最小可用默认语料
    if not docs:
        docs = [
            {"source": "seed:live", "text": "医学周期长、成本高，家庭预算必须先算清楚。"},
            {"source": "seed:case", "text": "冲稳保必须按位次，不按情绪。"},
            {"source": "seed:quote", "text": "报志愿是策略问题，不是情绪问题。"},
        ]

    target = ROOT / "data" / "vector_store" / "zx_experience.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] 本地索引已写入: {target} ({len(docs)} 条)")

    rag_cfg = _load_rag_config()
    if rag_cfg.get("write_remote", True):
        _push_to_milvus(docs, rag_cfg.get("milvus", {}))
        _push_to_elasticsearch(docs, rag_cfg.get("elasticsearch", {}))
        print("[INFO] RAG 双写流程完成（远端失败不阻断）。")
    else:
        print("write_remote=false，已跳过 Milvus/ES 写入。")


if __name__ == "__main__":
    main()
