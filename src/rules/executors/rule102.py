from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import (
    BaseRuleFeature, BaseRuleScore,
    Rule102Config, Rule102Feature, Rule102Score,
)
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule102Executor(RuleExecutor):
    rule_cls = Rule102Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule102Config,
    ) -> BaseRuleFeature:
        return Rule102Feature()

    def exec_score(
        self,
        config: Rule102Config,
        feature: Rule102Feature,
    ) -> BaseRuleScore:
        return Rule102Score(score=None)
