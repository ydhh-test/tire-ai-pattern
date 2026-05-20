from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule2Config, Rule2Feature, Rule2Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule2Executor(RuleExecutor):
    rule_cls = Rule2Config

    def exec_feature(self, image: BaseImage, config: Rule2Config) -> Rule2Feature:
        """根据血缘中的 StitchingSchemeName 判断是否匹配中心对称方案"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule2Feature(is_active=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_active = scheme_name in (
            StitchingSchemeName.SYMMETRY_1,   # 5-rib 中心旋转180°对称
            StitchingSchemeName.SYMMETRY_5,   # 4-rib 中心旋转180°对称
        )
        return Rule2Feature(is_active=is_active)

    def exec_score(self, config: Rule2Config, feature: Rule2Feature) -> Rule2Score:
        score = config.max_score if feature.is_active else 0
        return Rule2Score(score=score)
