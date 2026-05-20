from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule17Config, Rule17Feature, Rule17Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule17Executor(RuleExecutor):
    rule_cls = Rule17Config

    def exec_feature(self, image: BaseImage, config: Rule17Config) -> Rule17Feature:
        """
        TODO: 判断血缘中的 StitchingSchemeName 是否在边缘RIB连续性列表中。
        目前还没有对应的 CONTINUITY_N 被定义，该列表为空。
        后续定义了 CONTINUITY_N 枚举值之后，填充到 _EDGE_CONTINUITY_LIST 中。
        """
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule17Feature(is_continuous=False)

        # TODO: 等待 CONTINUITY_N 枚举定义后更新此列表
        _EDGE_CONTINUITY_LIST: tuple = ()

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_continuous = scheme_name in _EDGE_CONTINUITY_LIST
        return Rule17Feature(is_continuous=is_continuous)

    def exec_score(self, config: Rule17Config, feature: Rule17Feature) -> Rule17Score:
        score = config.max_score if feature.is_continuous else 0
        return Rule17Score(score=score)
