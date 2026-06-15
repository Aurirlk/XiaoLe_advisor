"""
问卷API路由 (Questionnaire Router)

端点：
- GET /questionnaire/types - 获取所有问卷类型
- GET /questionnaire/{type} - 获取指定问卷详情
- POST /questionnaire/validate - 验证问卷答案
- POST /questionnaire/submit - 提交问卷并转换为画像
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from skills.questionnaire_service import get_questionnaire_service

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


class QuestionnaireType(BaseModel):
    id: str
    name: str
    description: str
    estimated_time: str
    required: bool
    question_count: int


class ValidateRequest(BaseModel):
    questionnaire_type: str
    answers: Dict[str, Any]


class SubmitRequest(BaseModel):
    questionnaire_type: str
    answers: Dict[str, Any]
    phone_number: Optional[str] = None


class ValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    cleaned_answers: Dict[str, Any] = {}


class SubmitResponse(BaseModel):
    ok: bool
    profile: Dict[str, Any] = {}
    parent_constraints: Dict[str, Any] = {}
    student_preferences: Dict[str, Any] = {}
    message: str = ""


@router.get("/types", response_model=List[QuestionnaireType])
async def get_questionnaire_types():
    """获取所有问卷类型"""
    service = get_questionnaire_service()
    types = service.get_questionnaire_types()
    return types


@router.get("/{questionnaire_type}")
async def get_questionnaire(questionnaire_type: str):
    """获取指定类型的问卷详情"""
    service = get_questionnaire_service()
    questionnaire = service.get_questionnaire(questionnaire_type)
    
    if not questionnaire:
        raise HTTPException(status_code=404, detail=f"问卷类型 '{questionnaire_type}' 不存在")
    
    return questionnaire


@router.post("/validate", response_model=ValidateResponse)
async def validate_answers(req: ValidateRequest):
    """验证问卷答案"""
    service = get_questionnaire_service()
    
    # 检查问卷类型是否存在
    questionnaire = service.get_questionnaire(req.questionnaire_type)
    if not questionnaire:
        raise HTTPException(status_code=404, detail=f"问卷类型 '{req.questionnaire_type}' 不存在")
    
    result = service.validate_answers(req.questionnaire_type, req.answers)
    return result


@router.post("/submit", response_model=SubmitResponse)
async def submit_questionnaire(req: SubmitRequest):
    """提交问卷并转换为用户画像"""
    service = get_questionnaire_service()
    
    # 检查问卷类型是否存在
    questionnaire = service.get_questionnaire(req.questionnaire_type)
    if not questionnaire:
        raise HTTPException(status_code=404, detail=f"问卷类型 '{req.questionnaire_type}' 不存在")
    
    # 验证答案
    validation = service.validate_answers(req.questionnaire_type, req.answers)
    if not validation["valid"]:
        return SubmitResponse(
            ok=False,
            message=f"问卷验证失败: {'; '.join(validation['errors'])}"
        )
    
    # 转换为画像
    converted = service.convert_to_profile(req.questionnaire_type, validation["cleaned_answers"])
    
    # 如果有手机号，保存到CRM
    if req.phone_number:
        try:
            from api.dependencies import get_crm_manager
            crm = get_crm_manager()
            
            # 加载现有画像
            existing_profile = await crm.load_profile(req.phone_number)
            
            # 合并新画像
            merged_profile = {**existing_profile, **converted["profile"]}
            
            # 保存
            await crm.save_profile(req.phone_number, merged_profile, "问卷填写", req.questionnaire_type)
        except Exception:
            pass  # 静默失败，不影响返回
    
    return SubmitResponse(
        ok=True,
        profile=converted["profile"],
        parent_constraints=converted["parent_constraints"],
        student_preferences=converted["student_preferences"],
        message="问卷提交成功",
    )


@router.get("/stats/completion")
async def get_completion_stats(phone_number: Optional[str] = None):
    """获取问卷完成度统计"""
    service = get_questionnaire_service()
    
    # 获取基础问卷统计
    stats = {
        "student_basic": service.get_completion_stats({}),
        "available_types": [t["id"] for t in service.get_questionnaire_types()],
    }
    
    return stats
