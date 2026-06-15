"""
AI暴露度评估器测试
"""
import pytest
from skills.ai_exposure_checker import assess_ai_exposure, get_major_exposure_summary, batch_assess


class TestAIExposureChecker:
    """测试AI暴露度评估器"""
    
    def test_high_risk_major(self):
        """测试高风险专业（会计）"""
        result = assess_ai_exposure("会计学")
        
        assert result["major"] == "会计学"
        assert result["risk_level"] in ["medium", "high"]
        assert len(result["high_risk_tasks"]) > 0
        assert "传统财会" in result["high_risk_tasks"]
        assert result["ai_exposure_risk"] > 0.3
    
    def test_low_risk_major(self):
        """测试低风险专业（临床医学）"""
        result = assess_ai_exposure("临床医学")
        
        assert result["major"] == "临床医学"
        assert result["risk_level"] in ["low", "medium"]
        assert len(result["high_barrier_tasks"]) > 0
        assert "手术操作" in result["high_barrier_tasks"]
        assert result["ai_exposure_risk"] < 0.5
    
    def test_medium_risk_major(self):
        """测试中等风险专业（计算机）"""
        result = assess_ai_exposure("计算机科学与技术")
        
        assert result["major"] == "计算机科学与技术"
        assert result["risk_level"] in ["medium", "high"]
        assert result["ai_exposure_risk"] > 0.2
        assert result["ai_exposure_risk"] < 0.8
    
    def test_unknown_major(self):
        """测试未知专业"""
        result = assess_ai_exposure("未知专业")
        
        assert result["major"] == "未知专业"
        assert result["risk_level"] == "medium"  # 默认中等风险
        assert result["ai_exposure_risk"] == 0.5
    
    def test_custom_tasks(self):
        """测试自定义任务"""
        custom_tasks = ["基础翻译", "手术操作", "心理咨询"]
        result = assess_ai_exposure("英语", custom_tasks)
        
        assert "基础翻译" in result["high_risk_tasks"]
        assert "手术操作" in result["high_barrier_tasks"]
        assert "心理咨询" in result["high_barrier_tasks"]
    
    def test_exposure_summary(self):
        """测试暴露度摘要生成"""
        summary = get_major_exposure_summary("计算机科学与技术")
        
        assert "计算机科学与技术" in summary
        assert "AI暴露度" in summary
        assert "%" in summary
    
    def test_batch_assess(self):
        """测试批量评估"""
        majors = ["计算机科学与技术", "会计学", "临床医学"]
        results = batch_assess(majors)
        
        assert len(results) == 3
        for major in majors:
            assert major in results
            assert "risk_level" in results[major]
            assert "ai_exposure_risk" in results[major]
    
    def test_career_advice_generation(self):
        """测试职业建议生成"""
        result = assess_ai_exposure("会计学")
        
        assert result["career_advice"] != ""
        assert len(result["career_advice"]) > 50
    
    def test_enhancement_suggestions(self):
        """测试增强建议"""
        result = assess_ai_exposure("计算机科学与技术")
        
        assert len(result["enhancement_suggestions"]) > 0


class TestAIExposureEdgeCases:
    """测试AI暴露度边缘情况"""
    
    def test_empty_string_major(self):
        """测试空字符串专业"""
        result = assess_ai_exposure("")
        assert result["major"] == ""
        assert result["risk_level"] == "medium"
    
    def test_special_characters(self):
        """测试特殊字符专业名"""
        result = assess_ai_exposure("计算机@#$")
        assert result["major"] == "计算机@#$"
    
    def test_long_major_name(self):
        """测试超长专业名"""
        long_name = "计算机科学与技术" * 10
        result = assess_ai_exposure(long_name)
        assert result["major"] == long_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
