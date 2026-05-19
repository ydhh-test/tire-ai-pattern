from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import (
    BaseRuleFeature, BaseRuleScore,
    Rule101Config, Rule101Feature, Rule101Score,
)
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule101Executor(RuleExecutor):
    rule_cls = Rule101Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule101Config,
    ) -> BaseRuleFeature:
        return Rule101Feature()

    def exec_score(
        self,
        config: Rule101Config,
        feature: Rule101Feature,
    ) -> BaseRuleScore:
        return Rule101Score(score=None)
