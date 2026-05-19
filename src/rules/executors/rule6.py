from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import Rule6Config, Rule6Feature, Rule6Score
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule6Executor(RuleExecutor):
    rule_cls = Rule6Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule6Config,
    ) -> Rule6Feature:
        import cv2
        from src.core.detection.pattern_continuity import detect_pattern_continuity
        from src.utils.image_utils import base64_to_ndarray

        bgr = base64_to_ndarray(image.image_base64)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        is_continuous, _, _ = detect_pattern_continuity(gray)

        return Rule6Feature(is_continuous=is_continuous)

    def exec_score(
        self,
        config: Rule6Config,
        feature: Rule6Feature,
    ) -> Rule6Score:
        score = config.max_score if feature.is_continuous else 0
        return Rule6Score(score=score)
