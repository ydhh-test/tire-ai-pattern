from __future__ import annotations

from src.common.exceptions import InputDataError, InputTypeError
from src.core.detection.land_sea_ratio import compute_land_sea_ratio
from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import BaseRuleFeature, BaseRuleScore, Rule13Config, Rule13Feature, Rule13Score
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor
from src.utils.image_utils import base64_to_ndarray, ndarray_to_base64


FEATURE_FUNCTION = "Rule13Executor.exec_feature"
SCORE_FUNCTION = "Rule13Executor.exec_score"


@register_rule_executor
class Rule13Executor(RuleExecutor):
    rule_cls = Rule13Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule13Config,
        is_debug: bool = False,
    ) -> BaseRuleFeature:
        if not isinstance(image, BigImage):
            raise InputTypeError(FEATURE_FUNCTION, "image", "BigImage", type(image).__name__)
        if not isinstance(config, Rule13Config):
            raise InputTypeError(FEATURE_FUNCTION, "config", "Rule13Config", type(config).__name__)
        if not isinstance(is_debug, bool):
            raise InputTypeError(FEATURE_FUNCTION, "is_debug", "bool", type(is_debug).__name__)

        image_array = base64_to_ndarray(image.image_base64)
        ratio_percent, vis_name, vis_image = compute_land_sea_ratio(
            image_array,
            is_debug=is_debug,
        )

        feature_data = {"land_ratio": ratio_percent}
        if is_debug and vis_image is not None:
            debug_name = f"{vis_name}.png" if vis_name else "land_sea_ratio.png"
            feature_data["vis_names"] = [debug_name]
            feature_data["vis_images"] = [ndarray_to_base64(vis_image)]

        return Rule13Feature(**feature_data)

    def exec_score(
        self,
        config: Rule13Config,
        feature: Rule13Feature,
    ) -> BaseRuleScore:
        if not isinstance(config, Rule13Config):
            raise InputTypeError(SCORE_FUNCTION, "config", "Rule13Config", type(config).__name__)
        if not isinstance(feature, Rule13Feature):
            raise InputTypeError(SCORE_FUNCTION, "feature", "Rule13Feature", type(feature).__name__)

        if not 0 <= feature.land_ratio <= 100:
            raise InputDataError(SCORE_FUNCTION, "feature.land_ratio", "must be in [0, 100]", feature.land_ratio)
        if config.land_ratio_min > config.land_ratio_max:
            raise InputDataError(
                SCORE_FUNCTION,
                "config.land_ratio_min",
                "must be <= config.land_ratio_max",
                config.land_ratio_min,
            )

        score = config.max_score if config.land_ratio_min <= feature.land_ratio <= config.land_ratio_max else 0
        return Rule13Score(score=score)