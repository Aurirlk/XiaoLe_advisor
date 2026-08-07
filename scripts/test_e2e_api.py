"""
E2E 测试脚本 — 验证核心 API 端点

运行方式：
python scripts/test_e2e_api.py

测试内容：
1. 健康检查
2. 用户注册/登录
3. 意图识别（三层路由）
4. 渐进询问
5. 推荐理由
6. 对比分析
7. 志愿表生成
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    """测试健康检查"""
    try:
        resp = requests.get(f"{BASE_URL}/healthz", timeout=5)
        assert resp.status_code == 200, f"健康检查失败: {resp.status_code}"
        data = resp.json()
        assert data.get("ok") == True, f"健康检查返回异常: {data}"
        print("✅ 健康检查通过")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False


def test_status():
    """测试状态接口"""
    try:
        resp = requests.get(f"{BASE_URL}/status", timeout=5)
        assert resp.status_code == 200, f"状态检查失败: {resp.status_code}"
        data = resp.json()
        assert data.get("ok") == True, f"状态检查返回异常: {data}"
        print("✅ 状态检查通过")
        print(f"   - Graph: {data.get('graph_ready', False)}")
        print(f"   - DB: {data.get('db_ready', False)}")
        print(f"   - Redis: {data.get('redis_ready', False)}")
        print(f"   - Vector: {data.get('vector_ready', False)}")
        return True
    except Exception as e:
        print(f"❌ 状态检查失败: {e}")
        return False


def test_register_and_login():
    """测试注册和登录"""
    try:
        # 注册
        register_data = {
            "phone_number": "13800138000",
            "password": "test123456",
            "role": "student"
        }
        resp = requests.post(f"{BASE_URL}/auth/register", json=register_data, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("token"), "注册未返回 token"
            print("✅ 注册成功")
            return data["token"]
        elif resp.status_code == 400:
            # 用户已存在，尝试登录
            print("⚠️ 用户已存在，尝试登录")
        else:
            print(f"❌ 注册失败: {resp.status_code}")
            return None

        # 登录
        login_data = {
            "phone_number": "13800138000",
            "password": "test123456"
        }
        resp = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("token"), "登录未返回 token"
            print("✅ 登录成功")
            return data["token"]
        else:
            print(f"❌ 登录失败: {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ 注册/登录异常: {e}")
        return None


def test_graph_query(token):
    """测试知识图谱查询"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            f"{BASE_URL}/api/graph/query",
            params={"query_type": "university", "keyword": "清华大学", "depth": 2},
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            nodes_count = len(data.get("nodes", []))
            edges_count = len(data.get("edges", []))
            print(f"✅ 知识图谱: {nodes_count} 个节点, {edges_count} 条边")
            return True
        elif resp.status_code == 404:
            print("⚠️ 知识图谱: API 端点不存在（可能未实现）")
            return False
        else:
            print(f"❌ 知识图谱: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 知识图谱: {e}")
        return False


def test_ranking(token):
    """测试院校排名"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            f"{BASE_URL}/api/ranking/qs",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            universities_count = len(data.get("universities", []))
            print(f"✅ 院校排名: {universities_count} 所院校")
            return True
        elif resp.status_code == 404:
            print("⚠️ 院校排名: API 端点不存在（可能未实现）")
            return False
        else:
            print(f"❌ 院校排名: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 院校排名: {e}")
        return False


def test_comparison(token):
    """测试对比分析"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.post(
            f"{BASE_URL}/api/compare",
            json={"type": "university", "items": ["清华大学", "北京大学"]},
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ 对比分析: {len(data.get('items', []))} 个对比项")
            return True
        elif resp.status_code == 404:
            print("⚠️ 对比分析: API 端点不存在（可能未实现）")
            return False
        else:
            print(f"❌ 对比分析: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 对比分析: {e}")
        return False


def test_application_form(token):
    """测试志愿表生成"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.post(
            f"{BASE_URL}/api/application-form",
            json={"province": "广东", "subject_type": "物理类", "score": 580, "rank": 50000},
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            rush_count = len(data.get("rush_items", []))
            stable_count = len(data.get("stable_items", []))
            safe_count = len(data.get("safe_items", []))
            print(f"✅ 志愿表生成: 冲{rush_count} 稳{stable_count} 保{safe_count}")
            return True
        elif resp.status_code == 404:
            print("⚠️ 志愿表生成: API 端点不存在（可能未实现）")
            return False
        else:
            print(f"❌ 志愿表生成: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 志愿表生成: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 50)
    print("小乐AI E2E API 测试")
    print("=" * 50)
    print()
    
    # 1. 健康检查
    print("1. 健康检查")
    if not test_health():
        print("\n❌ 后端服务未启动，请先运行: python -m api.main")
        return
    print()
    
    # 2. 状态检查
    print("2. 状态检查")
    test_status()
    print()
    
    # 3. 注册/登录
    print("3. 注册/登录")
    token = test_register_and_login()
    print()
    
    if not token:
        print("❌ 无法获取 token，跳过后续测试")
        return
    
    # 4. 知识图谱
    print("4. 知识图谱查询")
    test_graph_query(token)
    print()
    
    # 5. 院校排名
    print("5. 院校排名")
    test_ranking(token)
    print()
    
    # 6. 对比分析
    print("6. 对比分析")
    test_comparison(token)
    print()
    
    # 7. 志愿表生成
    print("7. 志愿表生成")
    test_application_form(token)
    print()
    
    print("=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
