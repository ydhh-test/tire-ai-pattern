from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule1Config, Rule1Feature, Rule1Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule1Executor(RuleExecutor):
    rule_cls = Rule1Config

    def exec_feature(self, image: BaseImage, config: Rule1Config, is_debug: bool = False,) -> Rule1Feature:
        """根据血缘中的 StitchingSchemeName 判断是否匹配无对称方案"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule1Feature(is_active=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_active = scheme_name in (
            StitchingSchemeName.SYMMETRY_0,   # 5-rib 无对称
            StitchingSchemeName.SYMMETRY_4,   # 4-rib 无对称
        )
        return Rule1Feature(is_active=is_active)

    def exec_score(self, config: Rule1Config, feature: Rule1Feature) -> Rule1Score:
        score = config.max_score if feature.is_active else 0
        return Rule1Score(score=score)
