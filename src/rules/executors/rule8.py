from __future__ import annotations

from src.models.enums import RegionEnum
from src.models.image_models import BaseImage
from src.models.rule_models import Rule8Config, Rule8Feature, Rule8Score
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule8Executor(RuleExecutor):
    rule_cls = Rule8Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule8Config,
        is_debug: bool = False,
    ) -> Rule8Feature:
        from src.core.detection.groove_intersection import detect_transverse_grooves
        from src.utils.image_utils import base64_to_ndarray

        bgr = base64_to_ndarray(image.image_base64)
        groove_width_px = self._select_groove_width_px(image, config)
        num_transverse_grooves, _, _, _ = detect_transverse_grooves(
            bgr,
            groove_width_px=groove_width_px,
        )

        return Rule8Feature(num_transverse_grooves=num_transverse_grooves)

    def exec_score(
        self,
        config: Rule8Config,
        feature: Rule8Feature,
    ) -> Rule8Score:
        score = config.max_score if feature.num_transverse_grooves > 0 else 0
        return Rule8Score(score=score)

    @staticmethod
    def _select_groove_width_px(
        image: BaseImage,
        config: Rule8Config,
    ) -> int:
        if image.biz.region == RegionEnum.SIDE:
            groove_width = config.groove_width_side
        else:
            groove_width = config.groove_width_center

        return max(1, int(round(groove_width)))
