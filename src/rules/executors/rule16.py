from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule16Config, Rule16Feature, Rule16Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule16Executor(RuleExecutor):
    rule_cls = Rule16Config

    def exec_feature(self, image: BaseImage, config: Rule16Config) -> Rule16Feature:
        """判断血缘中的 StitchingSchemeName 是否为 CONTINUITY_1/2/3"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule16Feature(is_continuous=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_continuous = scheme_name in (
            StitchingSchemeName.CONTINUITY_1,
            StitchingSchemeName.CONTINUITY_2,
            StitchingSchemeName.CONTINUITY_3,
        )
        return Rule16Feature(is_continuous=is_continuous)

    def exec_score(self, config: Rule16Config, feature: Rule16Feature) -> Rule16Score:
        score = config.max_score if feature.is_continuous else 0
        return Rule16Score(score=score)
