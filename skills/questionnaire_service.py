"""
调查问卷服务 (Questionnaire Service)

设计理念：
- 在用户与AI对话前，通过问卷快速完成画像
- 支持多种题型：选择题、填空题、论述题、矩阵题
- 问卷结果自动填充到 user_profile / parent_constraints / student_preferences
- 减少用户与系统的对话轮次，提升效率
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "questionnaire_config.yaml"


class QuestionnaireService:
    """问卷服务"""
    
    def __init__(self):
        self.config = self._load_config()
        self.questionnaires = self.config.get("questionnaires", {})
        self.mbti_mapping = self.config.get("mbti_major_mapping", {})
    
    def _load_config(self) -> dict:
        """加载问卷配置"""
        if not CONFIG_PATH.exists():
            return {"questionnaires": {}, "mbti_major_mapping": {}}
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def get_questionnaire_types(self) -> List[Dict[str, Any]]:
        """获取所有问卷类型列表"""
        types = self.config.get("questionnaire_types", {})
        result = []
        for key, info in types.items():
            result.append({
                "id": key,
                "name": info.get("name", ""),
                "description": info.get("description", ""),
                "estimated_time": info.get("estimated_time", ""),
                "required": info.get("required", False),
                "question_count": len(self.questionnaires.get(key, [])),
            })
        return result
    
    def get_questionnaire(self, questionnaire_type: str) -> Optional[Dict[str, Any]]:
        """获取指定类型的问卷详情"""
        questions = self.questionnaires.get(questionnaire_type)
        if not questions:
            return None
        
        type_info = self.config.get("questionnaire_types", {}).get(questionnaire_type, {})
        
        return {
            "id": questionnaire_type,
            "name": type_info.get("name", ""),
            "description": type_info.get("description", ""),
            "estimated_time": type_info.get("estimated_time", ""),
            "questions": questions,
        }
    
    def validate_answers(
        self, 
        questionnaire_type: str, 
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证问卷答案
        
        Returns:
            valid: 是否有效
            errors: 错误信息列表
            cleaned_answers: 清洗后的答案
        """
        questions = self.questionnaires.get(questionnaire_type, [])
        errors = []
        cleaned = {}
        
        for q in questions:
            q_id = q["id"]
            q_type = q.get("type", "")
            is_required = q.get("required", False)
            
            answer = answers.get(q_id)
            
            # 必填校验
            if is_required and (answer is None or answer == "" or answer == []):
                errors.append(f"题目 '{q['question']}' 为必填项")
                continue
            
            # 跳过非必填且为空的
            if answer is None or answer == "" or answer == []:
                continue
            
            # 类型校验
            if q_type == "single_choice":
                valid_options = q.get("options", [])
                if answer not in valid_options:
                    errors.append(f"题目 '{q['question']}' 的选项无效: {answer}")
                else:
                    cleaned[q_id] = answer
                    
            elif q_type == "multiple_choice":
                valid_options = q.get("options", [])
                max_select = q.get("max_select", len(valid_options))
                if not isinstance(answer, list):
                    errors.append(f"题目 '{q['question']}' 需要多选格式")
                elif len(answer) > max_select:
                    errors.append(f"题目 '{q['question']}' 最多选择{max_select}项")
                else:
                    cleaned[q_id] = answer
                    
            elif q_type == "fill_blank":
                input_type = q.get("input_type", "text")
                if input_type == "number":
                    try:
                        num_val = int(answer)
                        min_val = q.get("min", 0)
                        max_val = q.get("max", 999999)
                        if num_val < min_val or num_val > max_val:
                            errors.append(f"题目 '{q['question']}' 的数值需在 {min_val}-{max_val} 之间")
                        else:
                            cleaned[q_id] = num_val
                    except ValueError:
                        errors.append(f"题目 '{q['question']}' 需要填写数字")
                else:
                    cleaned[q_id] = str(answer).strip()
                    
            elif q_type == "textarea":
                cleaned[q_id] = str(answer).strip()
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "cleaned_answers": cleaned,
        }
    
    def convert_to_profile(
        self, 
        questionnaire_type: str, 
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将问卷答案转换为用户画像格式
        
        Returns:
            profile: 用户画像
            parent_constraints: 家长约束（如有）
            student_preferences: 学生偏好（如有）
        """
        questions = self.questionnaires.get(questionnaire_type, [])
        
        profile = {}
        parent_constraints = {}
        student_preferences = {}
        
        for q in questions:
            q_id = q["id"]
            answer = answers.get(q_id)
            if answer is None:
                continue
            
            # 获取目标字段
            profile_field = q.get("profile_field")
            constraint_field = q.get("constraint_field")
            
            # 值映射
            value_mapping = q.get("value_mapping", {})
            mapped_value = value_mapping.get(answer, answer) if value_mapping else answer
            
            # 填充到对应结构
            if profile_field:
                profile[profile_field] = mapped_value
            elif constraint_field:
                parent_constraints[constraint_field] = mapped_value
        
        # 处理MBTI特殊逻辑
        if questionnaire_type == "mbti_personality":
            mbti_type = self._calculate_mbti(answers)
            profile["mbti_type"] = mbti_type
            profile["mbti_recommendations"] = self.mbti_mapping.get(mbti_type, [])
        
        # 构建student_preferences
        if questionnaire_type in ["student_basic", "major_preference"]:
            student_preferences = {
                "preferred_cities": profile.get("preferred_cities", []),
                "preferred_majors": profile.get("preferred_majors", []),
                "risk_tolerance": profile.get("risk_tolerance", "medium"),
                "postgraduate_plan": profile.get("postgraduate_plan", ""),
            }
        
        return {
            "profile": profile,
            "parent_constraints": parent_constraints,
            "student_preferences": student_preferences,
        }
    
    def _calculate_mbti(self, answers: Dict[str, Any]) -> str:
        """根据答案计算MBTI类型"""
        dimension_counts = {"E": 0, "I": 0, "S": 0, "N": 0, "T": 0, "F": 0, "J": 0, "P": 0}
        
        for q in self.questionnaires.get("mbti_personality", []):
            q_id = q["id"]
            answer = answers.get(q_id)
            if answer is None:
                continue
            
            # 获取该选项对应的维度值
            options = q.get("options", [])
            values = q.get("values", [])
            dimension = q.get("dimension", "")
            
            if answer in options:
                idx = options.index(answer)
                if idx < len(values):
                    dim_value = values[idx]
                    if dim_value in dimension_counts:
                        dimension_counts[dim_value] += 1
        
        # 计算MBTI类型
        mbti = ""
        mbti += "E" if dimension_counts["E"] >= dimension_counts["I"] else "I"
        mbti += "S" if dimension_counts["S"] >= dimension_counts["N"] else "N"
        mbti += "T" if dimension_counts["T"] >= dimension_counts["F"] else "F"
        mbti += "J" if dimension_counts["J"] >= dimension_counts["P"] else "P"
        
        return mbti
    
    def get_completion_stats(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """获取问卷完成度统计"""
        total = 0
        answered = 0
        
        for q in self.questionnaires.get("student_basic", []):
            total += 1
            if q["id"] in answers and answers[q["id"]]:
                answered += 1
        
        return {
            "total_questions": total,
            "answered": answered,
            "completion_rate": answered / total if total > 0 else 0,
        }


# 单例实例
_questionnaire_service: Optional[QuestionnaireService] = None


def get_questionnaire_service() -> QuestionnaireService:
    """获取问卷服务单例"""
    global _questionnaire_service
    if _questionnaire_service is None:
        _questionnaire_service = QuestionnaireService()
    return _questionnaire_service
