"""
决策框架生成器 — 教用户用什么标准做决定

功能：
- 生成高考志愿决策框架
- 生成考研决策框架
- 生成就业决策框架
- 生成职业探索框架
"""
from __future__ import annotations

from typing import Dict, Any, Optional


class DecisionFramework:
    """决策框架生成器"""
    
    def generate_framework(self, scene: str, path: Optional[str], profile: Dict[str, Any]) -> str:
        """生成决策框架"""
        
        if scene == "gaokao":
            return self._gaokao_framework(profile)
        elif scene == "postgraduate":
            if path == "postgrad":
                return self._postgrad_framework(profile)
            elif path == "employment":
                return self._employment_framework(profile)
            else:
                return self._career_exploration_framework(profile)
        
        return ""
    
    def _gaokao_framework(self, profile: Dict[str, Any]) -> str:
        """高考志愿决策框架"""
        return """
🎯 **选专业的决策框架**：

选专业其实就 3 个核心问题：

**第一，你擅长什么？**
- 不是"喜欢什么"，是"做什么比别人轻松"
- 喜欢打游戏 ≠ 擅长计算机
- 喜欢看剧 ≠ 擅长编导

**第二，市场需要什么？**
- 不是现在热门什么，是 4 年后需要什么
- 现在热门 ≠ 4 年后热门
- 看就业率、薪资、稳定性

**第三，你能接受什么？**
- 能接受加班吗？能接受出差吗？能接受低薪起步吗？
- 专业选择 = 擅长 × 市场 × 接受度

**行动建议**：
1. 先排除你绝对不想做的（排雷）
2. 再看你能接受什么（底线）
3. 最后在里面选最不差的（优化）
"""
    
    def _postgrad_framework(self, profile: Dict[str, Any]) -> str:
        """考研决策框架"""
        return """
🎯 **考研的决策框架**：

考研前先问自己 3 个问题：

**第一，为什么要考研？**
- ✅ 目标职业明确要求硕士学历（如医生、研究员）
- ✅ 想深入研究某个领域
- ❌ 不知道干什么，先考个研
- ❌ 觉得硕士一定比本科好

**第二，考研的成本你能接受吗？**
- 时间成本：2-3 年
- 经济成本：学费 + 生活费 - 少赚的工资
- 机会成本：错过的工作经验

**第三，考研的成功率你了解吗？**
- 2024 年考研报名 438 万
- 录取率约 30%
- 二战三战很常见

**行动建议**：
1. 先确定目标职业是否真的需要硕士
2. 再评估自己的学习能力和毅力
3. 最后制定备考计划
"""
    
    def _employment_framework(self, profile: Dict[str, Any]) -> str:
        """就业决策框架"""
        return """
🎯 **就业的决策框架**：

就业前先问自己 3 个问题：

**第一，你想去什么行业？**
- 互联网、金融、医疗、教育、制造业...
- 每个行业的门槛、薪资、稳定性都不同

**第二，你能接受什么工作节奏？**
- 996（互联网）vs 稳定（国企/公务员）
- 高薪高压 vs 低薪稳定

**第三，你的竞争力是什么？**
- 学历、技能、实习经验、人脉
- 你比别人强在哪？

**行动建议**：
1. 先确定目标行业
2. 再了解行业门槛
3. 最后制定提升计划
"""
    
    def _career_exploration_framework(self, profile: Dict[str, Any]) -> str:
        """职业探索框架"""
        return """
🎯 **职业探索框架**：

如果你还不确定要考研还是就业，可以这样思考：

**第一步：排除法**
- 你绝对不想做什么？
- 你绝对不能接受什么？

**第二步：偏好法**
- 你更看重什么？稳定 vs 高薪
- 你更喜欢什么？自由 vs 规律

**第三步：现实法**
- 你的家庭经济条件能支持你读研吗？
- 你的学习能力能考上吗？

**行动建议**：
1. 先做排除法，缩小范围
2. 再做偏好法，明确方向
3. 最后做现实法，验证可行性
"""
