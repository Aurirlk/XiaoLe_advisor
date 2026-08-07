"""
Harness 机制 - 数据引导与知识注入

当系统数据不足时，引导用户上传数据，解析后自动入库

场景定义已拆分到 harness_scenarios.py
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.harness_scenarios import MISSING_DATA_SCENARIOS, match_scenario

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]


class DataHarness:
    """数据引导与注入引擎"""

    def __init__(self, neo4j_client=None, sqlite_db_path: str = None):
        self.neo4j = neo4j_client
        self.sqlite_db = sqlite_db_path or str(ROOT / "data" / "zx_advisor.db")

    def detect_missing_data(self, query: str, tool_result: str = None) -> Optional[Dict]:
        """检测用户查询是否涉及缺失数据"""
        if tool_result:
            missing_indicators = [
                "未找到", "不存在", "暂无数据", "查询失败",
                "没有找到", "无数据", "未收录"
            ]
            if any(indicator in tool_result for indicator in missing_indicators):
                return match_scenario(query)
        return None

    def _match_scenario(self, query: str) -> Optional[Dict]:
        """根据查询内容匹配数据缺失场景（委托给 harness_scenarios 模块级实现）"""
        return match_scenario(query)

    # 兼容旧调用方：场景常量已迁至 harness_scenarios，此处保留只读引用
    MISSING_DATA_SCENARIOS = MISSING_DATA_SCENARIOS

    def generate_upload_prompt(self, scenario: Dict) -> str:
        """生成引导用户上传数据的话术"""
        return scenario.get("prompt", "请上传相关数据文件，我会帮你解析分析。")

    def parse_uploaded_file(
        self, file_content: bytes, filename: str, content_type: str, scenario: Dict
    ) -> Tuple[bool, str, List[Dict]]:
        """
        解析上传的文件

        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            content_type: MIME类型
            scenario: 数据场景配置

        Returns:
            (成功与否, 消息, 解析出的结构化数据)
        """
        parse_strategy = scenario.get("parse_strategy", "generic")
        ext = Path(filename).suffix.lower()

        try:
            # 图片文件 - 需要调用视觉模型解析
            if content_type and content_type.startswith("image/"):
                return self._parse_image(file_content, parse_strategy)

            # CSV 文件
            if ext == ".csv":
                return self._parse_csv(file_content, parse_strategy)

            # Excel 文件
            if ext in (".xlsx", ".xls"):
                return self._parse_excel(file_content, parse_strategy)

            # PDF 文件
            if ext == ".pdf":
                return self._parse_pdf(file_content, parse_strategy)

            return False, f"不支持的文件格式: {ext}", []

        except Exception as e:
            logger.exception(f"解析文件失败: {filename}")
            return False, f"解析失败: {str(e)}", []

    def _parse_image(self, image_bytes: bytes, strategy: str) -> Tuple[bool, str, List[Dict]]:
        """
        解析图片 - 需要调用视觉模型

        返回原始图片字节和解析策略，由调用方调用视觉模型
        """
        # 图片解析需要调用视觉模型，这里返回策略信息
        return True, "image_ready_for_vision", [{"type": "image", "strategy": strategy, "bytes": image_bytes}]

    def _parse_csv(self, file_content: bytes, strategy: str) -> Tuple[bool, str, List[Dict]]:
        """解析 CSV 文件"""
        try:
            text = file_content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)

            if not rows:
                return False, "CSV文件为空", []

            # 根据策略解析
            if strategy == "score_segment":
                return self._parse_score_segment_csv(rows)
            elif strategy == "batch_cutoff":
                return self._parse_batch_cutoff_csv(rows)
            elif strategy == "admission_data":
                return self._parse_admission_csv(rows)
            else:
                return True, f"解析成功，共{len(rows)}行数据", rows

        except Exception as e:
            return False, f"CSV解析失败: {str(e)}", []

    def _parse_score_segment_csv(self, rows: List[Dict]) -> Tuple[bool, str, List[Dict]]:
        """解析一分一段表 CSV"""
        # 尝试识别列名
        if not rows:
            return False, "数据为空", []

        sample = rows[0]
        keys = list(sample.keys())

        # 尝试映射列名
        score_col = next((k for k in keys if "分" in k or "score" in k.lower()), None)
        rank_col = next((k for k in keys if "名" in k or "rank" in k.lower() or "累计" in k), None)
        count_col = next((k for k in keys if "人数" in k or "count" in k.lower() or "本段" in k), None)

        if not score_col:
            return False, "无法识别分数列，请确认CSV包含'分数'列", []

        parsed = []
        for row in rows:
            try:
                entry = {
                    "score": int(row.get(score_col, 0)),
                    "segment_count": int(row.get(count_col, 0)) if count_col else 0,
                    "cumulative_count": int(row.get(rank_col, 0)) if rank_col else 0,
                }
                parsed.append(entry)
            except (ValueError, TypeError):
                continue

        return True, f"解析成功，共{len(parsed)}条一分一段数据", parsed

    def _parse_batch_cutoff_csv(self, rows: List[Dict]) -> Tuple[bool, str, List[Dict]]:
        """解析批次线 CSV"""
        if not rows:
            return False, "数据为空", []

        parsed = []
        for row in rows:
            entry = {}
            for k, v in row.items():
                if "批次" in k or "batch" in k.lower():
                    entry["batch_name"] = v
                elif "分" in k or "score" in k.lower():
                    try:
                        entry["score"] = int(v)
                    except ValueError:
                        pass
            if entry.get("batch_name") and entry.get("score"):
                parsed.append(entry)

        return True, f"解析成功，共{len(parsed)}条批次线数据", parsed

    def _parse_admission_csv(self, rows: List[Dict]) -> Tuple[bool, str, List[Dict]]:
        """解析录取数据 CSV"""
        if not rows:
            return False, "数据为空", []

        parsed = []
        for row in rows:
            entry = {}
            for k, v in row.items():
                k_lower = k.lower()
                if "院校" in k or "学校" in k or "university" in k_lower:
                    entry["university"] = v
                elif "专业" in k or "major" in k_lower:
                    entry["major"] = v
                elif "最低分" in k or "min_score" in k_lower:
                    try:
                        entry["min_score"] = int(v)
                    except ValueError:
                        pass
                elif "位次" in k or "rank" in k_lower:
                    try:
                        entry["rank"] = int(v)
                    except ValueError:
                        pass
            if entry.get("university"):
                parsed.append(entry)

        return True, f"解析成功，共{len(parsed)}条录取数据", parsed

    def _parse_excel(self, file_content: bytes, strategy: str) -> Tuple[bool, str, List[Dict]]:
        """解析 Excel 文件"""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)
            ws = wb.active

            rows = []
            headers = None
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 0:
                    headers = [str(h) if h else f"col_{j}" for j, h in enumerate(row)]
                else:
                    rows.append(dict(zip(headers, row)))

            wb.close()

            if not rows:
                return False, "Excel文件为空", []

            # 复用 CSV 解析逻辑
            return self._parse_csv_rows(rows, strategy)

        except ImportError:
            return False, "未安装openpyxl库，无法解析Excel文件", []
        except Exception as e:
            return False, f"Excel解析失败: {str(e)}", []

    def _parse_csv_rows(self, rows: List[Dict], strategy: str) -> Tuple[bool, str, List[Dict]]:
        """通用 CSV 行解析"""
        if strategy == "score_segment":
            return self._parse_score_segment_csv(rows)
        elif strategy == "batch_cutoff":
            return self._parse_batch_cutoff_csv(rows)
        elif strategy == "admission_data":
            return self._parse_admission_csv(rows)
        else:
            return True, f"解析成功，共{len(rows)}行数据", rows

    def _parse_pdf(self, file_content: bytes, strategy: str) -> Tuple[bool, str, List[Dict]]:
        """解析 PDF 文件"""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                all_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)

                if not all_text:
                    return False, "PDF无法提取文本（可能是扫描件），请上传图片版本", []

                full_text = "\n".join(all_text)
                return True, f"PDF解析成功，共{len(all_text)}页", [{"type": "pdf_text", "content": full_text, "strategy": strategy}]

        except ImportError:
            return False, "未安装pdfplumber库，无法解析PDF", []
        except Exception as e:
            return False, f"PDF解析失败: {str(e)}", []

    def save_to_database(self, data: List[Dict], strategy: str, metadata: Dict = None) -> Tuple[bool, str]:
        """
        将解析后的数据保存到数据库

        Args:
            data: 结构化数据
            strategy: 解析策略（决定存入哪个表）
            metadata: 元数据（省份、年份等）

        Returns:
            (成功与否, 消息)
        """
        import sqlite3

        try:
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()

            if strategy == "score_segment":
                return self._save_score_segment(cursor, conn, data, metadata)
            elif strategy == "batch_cutoff":
                return self._save_batch_cutoff(cursor, conn, data, metadata)
            elif strategy == "admission_data":
                return self._save_admission_data(cursor, conn, data, metadata)
            else:
                # 通用保存到 RAG
                return self._save_to_rag(data, strategy, metadata)

        except Exception as e:
            logger.exception("保存数据失败")
            return False, f"保存失败: {str(e)}"

    def _save_score_segment(self, cursor, conn, data: List[Dict], metadata: Dict) -> Tuple[bool, str]:
        """保存一分一段数据"""
        # 创建表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS score_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                province TEXT NOT NULL,
                year INTEGER NOT NULL,
                subject_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                segment_count INTEGER,
                cumulative_count INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(province, year, subject_type, score)
            )
        """)

        province = metadata.get("province", "")
        year = metadata.get("year", 2025)
        subject_type = metadata.get("subject_type", "")

        inserted = 0
        for row in data:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO score_segments
                    (province, year, subject_type, score, segment_count, cumulative_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (province, year, subject_type, row["score"], row.get("segment_count", 0), row.get("cumulative_count", 0)))
                inserted += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return True, f"成功保存{inserted}条一分一段数据"

    def _save_batch_cutoff(self, cursor, conn, data: List[Dict], metadata: Dict) -> Tuple[bool, str]:
        """保存批次线数据"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS province_cutoffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                province TEXT NOT NULL,
                year INTEGER NOT NULL,
                subject_type TEXT NOT NULL,
                batch_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(province, year, subject_type, batch_name)
            )
        """)

        province = metadata.get("province", "")
        year = metadata.get("year", 2025)
        subject_type = metadata.get("subject_type", "")

        inserted = 0
        for row in data:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO province_cutoffs
                    (province, year, subject_type, batch_name, score)
                    VALUES (?, ?, ?, ?, ?)
                """, (province, year, subject_type, row["batch_name"], row["score"]))
                inserted += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return True, f"成功保存{inserted}条批次线数据"

    def _save_admission_data(self, cursor, conn, data: List[Dict], metadata: Dict) -> Tuple[bool, str]:
        """保存录取数据"""
        # 复用现有 admission_scores 表
        province = metadata.get("province", "")
        year = metadata.get("year", 2025)
        subject_type = metadata.get("subject_type", "")

        inserted = 0
        for row in data:
            try:
                # 查找或创建院校
                uni_name = row.get("university", "")
                if not uni_name:
                    continue

                cursor.execute("SELECT id FROM universities WHERE name = ?", (uni_name,))
                uni_row = cursor.fetchone()
                if not uni_row:
                    cursor.execute("INSERT INTO universities (name, tier, city, tags) VALUES (?, '', '', '')", (uni_name,))
                    uni_id = cursor.lastrowid
                else:
                    uni_id = uni_row[0]

                cursor.execute("""
                    INSERT INTO admission_scores
                    (university_id, province, subject_type, year, major_name, min_score, lowest_rank)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (uni_id, province, subject_type, year, row.get("major", ""), row.get("min_score", 0), row.get("rank", 0)))
                inserted += 1
            except Exception:
                continue

        conn.commit()
        conn.close()
        return True, f"成功保存{inserted}条录取数据"

    def _save_to_rag(self, data: List[Dict], strategy: str, metadata: Dict) -> Tuple[bool, str]:
        """保存到 RAG 向量数据库"""
        # 将数据转为文本存入 RAG
        texts = []
        for item in data:
            if isinstance(item, dict):
                if item.get("type") == "pdf_text":
                    texts.append(item.get("content", ""))
                else:
                    texts.append(json.dumps(item, ensure_ascii=False))
            else:
                texts.append(str(item))

        # 这里需要调用 RAG 工具保存
        # 暂时返回成功提示
        return True, f"数据已准备就绪，共{len(texts)}条记录"


# 全局实例
harness = DataHarness()
