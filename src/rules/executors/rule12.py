from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import Rule12Config, Rule12Feature, Rule12Score
from src.models.enums import ContinuityModeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule12Executor(RuleExecutor):
    rule_cls = Rule12Config

    def exec_feature(self, image: BaseImage, config: Rule12Config) -> Rule12Feature:
        """
        计算连续性占比：
        continuity_ratio = len(非CONTINUITY_0的元素) / len(continuity_mode_list)
        """
        if not config.continuity_mode_list:
            return Rule12Feature(continuity_ratio=0.0)

        non_zero_count = sum(
            1 for mode in config.continuity_mode_list
            if mode != ContinuityModeName.CONTINUITY_0.value
        )
        ratio = non_zero_count / len(config.continuity_mode_list)
        return Rule12Feature(continuity_ratio=ratio)

    def exec_score(self, config: Rule12Config, feature: Rule12Feature) -> Rule12Score:
        """连续性占比在 [lower, upper] 范围内则得分"""
        in_range = (
            config.continuity_ratio_lower
            <= feature.continuity_ratio
            <= config.continuity_ratio_upper
        )
        score = config.max_score if in_range else 0
        return Rule12Score(score=score)
