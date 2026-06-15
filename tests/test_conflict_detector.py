"""
家庭冲突检测器测试
"""
import pytest
from skills.conflict_detector import detect_family_conflict, get_conflict_summary


class TestConflictDetector:
    """测试冲突检测器"""
    
    def test_no_conflict(self):
        """测试无冲突情况"""
        parent_constraints = {
            "budget_ceiling": 50000,
            "must_public": False,
            "health_restrictions": [],
            "blacklist_majors": [],
        }
        student_preferences = {
            "preferred_cities": ["广州"],
            "preferred_majors": ["计算机"],
        }
        score = 600
        rank = 20000
        
        result = detect_family_conflict(parent_constraints, student_preferences, score, rank)
        
        assert result["has_conflict"] is False
        assert result["requires_arbitration"] is False
        assert len(result["conflicts"]) == 0
    
    def test_budget_vs_public_conflict(self):
        """测试预算vs公办冲突"""
        parent_constraints = {
            "budget_ceiling": 15000,
            "must_public": True,
            "health_restrictions": [],
        }
        student_preferences = {
            "preferred_cities": ["广州"],
            "preferred_majors": ["计算机"],
        }
        score = 450  # 低分段
        rank = 80000
        
        result = detect_family_conflict(parent_constraints, student_preferences, score, rank)
        
        assert result["has_conflict"] is True
        assert any(c["type"] == "budget_vs_public" for c in result["conflicts"])
        assert result["requires_arbitration"] is True
    
    def test_city_vs_reality_conflict(self):
        """测试城市偏好vs分数现实冲突"""
        parent_constraints = {
            "budget_ceiling": 50000,
            "must_public": False,
        }
        student_preferences = {
            "preferred_cities": ["北京", "上海"],
            "preferred_majors": ["计算机"],
        }
        score = 550
        rank = 60000  # 位次较低
        
        result = detect_family_conflict(parent_constraints, student_preferences, score, rank)
        
        assert result["has_conflict"] is True
        assert any(c["type"] == "ambition_vs_reality" for c in result["conflicts"])
    
    def test_major_blacklist_conflict(self):
        """测试专业黑名单冲突"""
        parent_constraints = {
            "budget_ceiling": 50000,
            "must_public": False,
            "blacklist_majors": ["土木工程", "化学"],
        }
        student_preferences = {
            "preferred_cities": ["广州"],
            "preferred_majors": ["土木工程", "计算机"],
        }
        score = 600
        rank = 30000
        
        result = detect_family_conflict(parent_constraints, student_preferences, score, rank)
        
        assert result["has_conflict"] is True
        assert any(c["type"] == "preference_conflict" for c in result["conflicts"])
        assert result["requires_arbitration"] is True
    
    def test_health_vs_major_conflict(self):
        """测试体检限制vs专业冲突"""
        parent_constraints = {
            "budget_ceiling": 50000,
            "must_public": False,
            "health_restrictions": ["色弱"],
        }
        student_preferences = {
            "preferred_cities": ["广州"],
            "preferred_majors": ["化学工程", "计算机"],
        }
        score = 600
        rank = 30000
        
        result = detect_family_conflict(parent_constraints, student_preferences, score, rank)
        
        assert result["has_conflict"] is True
        assert any(c["type"] == "health_vs_major" for c in result["conflicts"])
        assert result["requires_arbitration"] is True
    
    def test_multiple_conflicts(self):
        """测试多个冲突"""
        parent_constraints = {
            "budget_ceiling": 15000,
            "must_public": True,
            "health_restrictions": ["色弱"],
            "blacklist_majors": ["土木工程"],
        }
        student_preferences = {
            "preferred_cities": ["北京"],
            "preferred_majors": ["土木工程", "化学"],
        }
        score = 450
        rank = 80000
        
        result = detect_family_conflict(parent_constraints, student_preferences, score, rank)
        
        assert result["has_conflict"] is True
        assert len(result["conflicts"]) >= 3
        assert result["requires_arbitration"] is True
    
    def test_resolution_prompt_generation(self):
        """测试冲突解决提示词生成"""
        parent_constraints = {
            "budget_ceiling": 15000,
            "must_public": True,
        }
        student_preferences = {
            "preferred_cities": ["北京"],
            "preferred_majors": ["计算机"],
        }
        score = 450
        rank = 80000
        
        result = detect_family_conflict(parent_constraints, student_preferences, score, rank)
        
        assert result["resolution_prompt"] != ""
        assert "家庭冲突检测报告" in result["resolution_prompt"]
        assert "强制输出要求" in result["resolution_prompt"]


class TestConflictSummary:
    """测试冲突摘要"""
    
    def test_no_conflict_summary(self):
        """测试无冲突摘要"""
        summary = get_conflict_summary([])
        assert summary == "无冲突检测"
    
    def test_conflict_summary(self):
        """测试有冲突摘要"""
        conflicts = [
            {"severity": "critical", "message": "严重冲突"},
            {"severity": "high", "message": "重要冲突"},
            {"severity": "warning", "message": "警告"},
        ]
        summary = get_conflict_summary(conflicts)
        assert "1个严重冲突" in summary
        assert "1个重要冲突" in summary
        assert "1个警告" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
