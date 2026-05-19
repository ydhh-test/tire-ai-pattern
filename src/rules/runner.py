from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import BaseRuleConfig, BaseRuleFeature, BaseRuleScore
from src.rules.registry import get_rule_executor


class RuleRunner:
    """Dispatch rule execution by ``config.name``."""

    @staticmethod
    def exec_feature(
        image: BaseImage,
        config: BaseRuleConfig,
        is_debug: bool = False,
    ) -> BaseRuleFeature:
        executor = get_rule_executor(config.name)
        return executor.exec_feature(image, config, is_debug=is_debug)

    @staticmethod
    def exec_score(
        config: BaseRuleConfig,
        feature: BaseRuleFeature,
    ) -> BaseRuleScore:
        executor = get_rule_executor(config.name)
        return executor.exec_score(config, feature)
