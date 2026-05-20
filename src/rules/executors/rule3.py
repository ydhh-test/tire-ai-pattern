from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule3Config, Rule3Feature, Rule3Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule3Executor(RuleExecutor):
    rule_cls = Rule3Config

    def exec_feature(self, image: BaseImage, config: Rule3Config) -> Rule3Feature:
        """根据血缘中的 StitchingSchemeName 判断是否匹配左右对称方案"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule3Feature(is_active=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_active = scheme_name in (
            StitchingSchemeName.SYMMETRY_2,   # 5-rib 左右镜像对称
            StitchingSchemeName.SYMMETRY_6,   # 4-rib 左右镜像对称
        )
        return Rule3Feature(is_active=is_active)

    def exec_score(self, config: Rule3Config, feature: Rule3Feature) -> Rule3Score:
        score = config.max_score if feature.is_active else 0
        return Rule3Score(score=score)
