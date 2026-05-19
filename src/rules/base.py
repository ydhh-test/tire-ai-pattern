from __future__ import annotations

from abc import ABC
from typing import ClassVar

from src.models.image_models import BaseImage
from src.models.rule_models import BaseRuleConfig, BaseRuleFeature, BaseRuleScore


class RuleExecutor(ABC):
    """所有规则执行器的基类。

    子类必须通过 ``rule_cls`` 绑定对应的规则配置类。
    注册器会从该配置类推导对外规则名，推导规则与
    ``BaseRuleConfig.name`` 保持一致。
    """

    rule_cls: ClassVar[type[BaseRuleConfig]]

    def exec_feature(
        self,
        image: BaseImage,
        config: BaseRuleConfig,
        is_debug: bool = False,
    ) -> BaseRuleFeature:
        raise NotImplementedError(f"{config.name}.exec_feature is not implemented")

    def exec_score(
        self,
        config: BaseRuleConfig,
        feature: BaseRuleFeature,
    ) -> BaseRuleScore:
        raise NotImplementedError(f"{config.name}.exec_score is not implemented")
