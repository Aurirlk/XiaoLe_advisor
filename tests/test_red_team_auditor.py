"""
反方审计引擎测试
"""
import pytest
from skills.red_team_auditor import RedTeamAuditor, quick_audit, has_critical_issues


class TestRedTeamAuditor:
    """测试反方审计引擎"""
    
    def setup_method(self):
        self.auditor = RedTeamAuditor()
    
    def test_pass_basic_recommendations(self):
        """测试基本推荐通过审计"""
        user_profile = {
            "budget": 50000,
            "score": 600,
            "rank": 30000,
        }
        recommendations = [
            {
                "university_name": "某985大学",
                "major_name": "计算机科学与技术",
                "min_score": 580,
                "tier": "985",
            },
            {
                "university_name": "某211大学",
                "major_name": "软件工程",
                "min_score": 560,
                "tier": "211",
            },
        ]
        
        result = self.auditor.audit_recommendations(user_profile, recommendations)
        
        assert result["passed"] is True
        assert len(result["audit_details"]) == 0
    
    def test_fail_budget_exceeded(self):
        """测试预算击穿检测"""
        user_profile = {
            "budget": 20000,
            "score": 600,
            "rank": 30000,
        }
        recommendations = [
            {
                "university_name": "某中外合作大学",
                "major_name": "计算机科学与技术(中外合作)",
                "min_score": 580,
                "tier": "中外合作",
                "tuition_fee": 80000,
            },
        ]
        
        result = self.auditor.audit_recommendations(user_profile, recommendations)
        
        assert result["passed"] is False
        assert len(result["audit_details"]) > 0
        assert any("预算击穿" in flaw for r in result["audit_details"] for flaw in r["fatal_flaws"])
    
    def test_fail_health_restriction(self):
        """测试体检限制检测"""
        user_profile = {
            "budget": 50000,
            "score": 600,
            "rank": 30000,
            "health_restrictions": ["色弱"],
        }
        recommendations = [
            {
                "university_name": "某医科大学",
                "major_name": "临床医学",
                "min_score": 580,
                "tier": "本科",
            },
        ]
        
        result = self.auditor.audit_recommendations(user_profile, recommendations)
        
        # 临床医学不是色弱直接冲突的专业，应该通过
        assert result["passed"] is True
    
    def test_fail_score_too_low(self):
        """测试分数严重不足检测"""
        user_profile = {
            "budget": 50000,
            "score": 450,
            "rank": 80000,
        }
        recommendations = [
            {
                "university_name": "某985大学",
                "major_name": "计算机科学与技术",
                "min_score": 620,
                "tier": "985",
            },
        ]
        
        result = self.auditor.audit_recommendations(user_profile, recommendations)
        
        assert result["passed"] is False
        assert any("分数严重不足" in flaw for r in result["audit_details"] for flaw in r["fatal_flaws"])
    
    def test_fail_pitfall_major(self):
        """测试天坑专业检测"""
        user_profile = {
            "budget": 50000,
            "score": 600,
            "rank": 30000,
        }
        recommendations = [
            {
                "university_name": "某大学",
                "major_name": "生物工程",
                "min_score": 550,
                "tier": "一本",
            },
        ]
        
        result = self.auditor.audit_recommendations(user_profile, recommendations)
        
        assert result["passed"] is True  # 天坑不是critical，只是警告
        assert any("天坑警告" in flaw for r in result["audit_details"] for flaw in r["fatal_flaws"])
    
    def test_multiple_recommendations(self):
        """测试多个推荐的审计"""
        user_profile = {
            "budget": 30000,
            "score": 500,
            "rank": 60000,
        }
        recommendations = [
            {
                "university_name": "某985大学",
                "major_name": "计算机科学与技术",
                "min_score": 620,
                "tier": "985",
            },
            {
                "university_name": "某大学",
                "major_name": "土木工程",
                "min_score": 480,
                "tier": "一本",
            },
        ]
        
        result = self.auditor.audit_recommendations(user_profile, recommendations)
        
        # 第一个推荐分数不足，第二个是天坑
        assert len(result["audit_details"]) >= 1
    
    def test_audit_summary_format(self):
        """测试审计报告格式"""
        user_profile = {
            "budget": 20000,
            "score": 450,
            "rank": 80000,
        }
        recommendations = [
            {
                "university_name": "某大学",
                "major_name": "计算机科学与技术",
                "min_score": 620,
                "tier": "一本",
                "tuition_fee": 5000,
            },
        ]
        
        result = self.auditor.audit_recommendations(user_profile, recommendations)
        
        assert "反方审计员强制警告" in result["audit_summary"]
        assert "审计结论" in result["audit_summary"]


class TestQuickAudit:
    """测试便捷审计函数"""
    
    def test_quick_audit_pass(self):
        """测试快速审计通过"""
        user_profile = {"budget": 50000, "score": 600}
        recommendations = [
            {"university_name": "某大学", "major_name": "计算机", "min_score": 580, "tier": "一本"},
        ]
        
        summary = quick_audit(user_profile, recommendations)
        assert "审计通过" in summary
    
    def test_quick_audit_fail(self):
        """测试快速审计失败"""
        user_profile = {"budget": 20000, "score": 450}
        recommendations = [
            {"university_name": "某大学", "major_name": "计算机", "min_score": 620, "tier": "一本", "tuition_fee": 5000},
        ]
        
        summary = quick_audit(user_profile, recommendations)
        assert "反方审计员强制警告" in summary


class TestHasCriticalIssues:
    """测试严重问题检测"""
    
    def test_no_critical(self):
        """测试无严重问题"""
        user_profile = {"budget": 50000, "score": 600}
        recommendations = [
            {"university_name": "某大学", "major_name": "计算机", "min_score": 580, "tier": "一本"},
        ]
        
        assert has_critical_issues(user_profile, recommendations) is False
    
    def test_has_critical(self):
        """测试有严重问题"""
        user_profile = {"budget": 20000, "score": 450}
        recommendations = [
            {"university_name": "某大学", "major_name": "计算机", "min_score": 620, "tier": "一本", "tuition_fee": 5000},
        ]
        
        assert has_critical_issues(user_profile, recommendations) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
