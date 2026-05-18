from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import BaseRuleFeature, BaseRuleScore, Rule19Config, Rule19Feature, Rule19Score
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule19Executor(RuleExecutor):
    rule_cls = Rule19Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule19Config,
        is_debug: bool = False,
    ) -> BaseRuleFeature:
        return Rule19Feature()

    def exec_score(
        self,
        config: Rule19Config,
        feature: Rule19Feature,
    ) -> BaseRuleScore:
        return Rule19Score(score=0)
