from __future__ import annotations

from src.common.exceptions import InputDataError, InputTypeError
from src.core.detection.groove_intersection import detect_transverse_grooves
from src.models.enums import RegionEnum
from src.models.image_models import BaseImage, SmallImage
from src.models.rule_models import BaseRuleFeature, BaseRuleScore, Rule14Config, Rule14Feature, Rule14Score
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor
from src.utils.image_utils import base64_to_ndarray, ndarray_to_base64


FEATURE_FUNCTION = "Rule14Executor.exec_feature"
SCORE_FUNCTION = "Rule14Executor.exec_score"
CENTER_GROOVE_WIDTH_PX = 25
SIDE_GROOVE_WIDTH_PX = 13


@register_rule_executor
class Rule14Executor(RuleExecutor):
    rule_cls = Rule14Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule14Config,
        is_debug: bool = False,
    ) -> BaseRuleFeature:
        if not isinstance(image, SmallImage):
            raise InputTypeError(FEATURE_FUNCTION, "image", "SmallImage", type(image).__name__)
        if not isinstance(config, Rule14Config):
            raise InputTypeError(FEATURE_FUNCTION, "config", "Rule14Config", type(config).__name__)
        if not isinstance(is_debug, bool):
            raise InputTypeError(FEATURE_FUNCTION, "is_debug", "bool", type(is_debug).__name__)

        region = image.biz.region
        if region not in (RegionEnum.CENTER, RegionEnum.SIDE):
            raise InputDataError(FEATURE_FUNCTION, "image.biz.region", "must be center or side", region)

        image_array = base64_to_ndarray(image.image_base64)
        groove_width_px = CENTER_GROOVE_WIDTH_PX if region == RegionEnum.CENTER else SIDE_GROOVE_WIDTH_PX

        _groove_count, intersection_count, vis_name, vis_image = detect_transverse_grooves(
            image_array,
            groove_width_px=groove_width_px,
            is_debug=is_debug,
        )

        feature_data = {"num_intersections": intersection_count}
        if is_debug and vis_image is not None:
            debug_name = f"{vis_name}.png" if vis_name else "groove_intersections.png"
            feature_data["vis_names"] = [debug_name]
            feature_data["vis_images"] = [ndarray_to_base64(vis_image)]

        return Rule14Feature(**feature_data)

    def exec_score(
        self,
        config: Rule14Config,
        feature: Rule14Feature,
    ) -> BaseRuleScore:
        if not isinstance(config, Rule14Config):
            raise InputTypeError(SCORE_FUNCTION, "config", "Rule14Config", type(config).__name__)
        if not isinstance(feature, Rule14Feature):
            raise InputTypeError(SCORE_FUNCTION, "feature", "Rule14Feature", type(feature).__name__)

        if feature.num_intersections < 0:
            raise InputDataError(
                SCORE_FUNCTION,
                "feature.num_intersections",
                "must be >= 0",
                feature.num_intersections,
            )
        if config.max_intersections < 0:
            raise InputDataError(
                SCORE_FUNCTION,
                "config.max_intersections",
                "must be >= 0",
                config.max_intersections,
            )

        score = config.max_score if feature.num_intersections <= config.max_intersections else 0
        return Rule14Score(score=score)
