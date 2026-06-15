from __future__ import annotations

import importlib.util
import io

import pytest

REDIS_INSTALLED = importlib.util.find_spec("redis") is not None

if REDIS_INSTALLED:
    from fastapi.testclient import TestClient
    from api.main import app


@pytest.fixture
def client():
    if not REDIS_INSTALLED:
        pytest.skip("redis not installed")
    return TestClient(app)


def test_admin_data_stats(client, monkeypatch):
    if not REDIS_INSTALLED:
        return
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    resp = client.get("/admin/data/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "provinces" in body


def test_admin_import_csv(client, monkeypatch, tmp_path):
    if not REDIS_INSTALLED:
        return
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    csv_content = (
        "university_name,province,subject_type,year,major_name,min_score,lowest_rank,data_source\n"
        "测试大学A,浙江省,物理类,2024,软件工程,610,15000,test_import\n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/admin/import?dry_run=true", files=files)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
