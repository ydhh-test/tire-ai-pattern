import pytest

from src.models.rule_models import BaseRuleConfig
from src.rules.base import RuleExecutor
from src.rules.registry import (
    RuleExecutorRegistry,
    get_rule_executor,
    register_rule_executor,
)


class RulexConfig(BaseRuleConfig):
    description: str = "dummy"
    max_score: int = 0


class DummyExecutor(RuleExecutor):
    rule_cls = RulexConfig

    def exec_feature(self, image, config, is_debug=False):
        raise AssertionError("not called")

    def exec_score(self, config, feature):
        raise AssertionError("not called")


def test_registry_registers_and_gets_executor_by_rule_name():
    """验证独立注册表可以按 rule_name 注册并取回同一个 executor 实例。"""
    registry = RuleExecutorRegistry()
    executor = DummyExecutor()

    registry.register("rulex", executor)

    assert registry.get("rulex") is executor


def test_registry_rejects_duplicate_rule_name():
    """验证同一个 rule_name 重复注册 executor 时会抛出 ValueError。"""
    registry = RuleExecutorRegistry()
    registry.register("rulex", DummyExecutor())

    with pytest.raises(ValueError, match="duplicate rule executor"):
        registry.register("rulex", DummyExecutor())


def test_registry_rejects_missing_rule_name():
    """验证读取不存在的 rule_name 时注册表会抛出 ValueError。"""
    registry = RuleExecutorRegistry()

    with pytest.raises(ValueError, match="rule executor is not registered"):
        registry.get("missing")


def test_global_registry_helpers_use_same_registry():
    """验证全局注册装饰器和 get_rule_executor 使用同一个全局注册表。"""
    decorated_cls = register_rule_executor(DummyExecutor)

    assert decorated_cls is DummyExecutor
    assert isinstance(get_rule_executor("rulex"), DummyExecutor)


def test_register_rule_executor_requires_rule_executor_subclass():
    """验证注册装饰器拒绝未继承 RuleExecutor 的类。"""
    class NotExecutor:
        rule_cls = RulexConfig

    with pytest.raises(TypeError, match="RuleExecutor"):
        register_rule_executor(NotExecutor)


def test_register_rule_executor_requires_rule_cls():
    """验证注册装饰器拒绝缺少 rule_cls 声明的 executor 类。"""
    class MissingRuleClsExecutor(RuleExecutor):
        def exec_feature(self, image, config, is_debug=False):
            raise AssertionError("not called")

        def exec_score(self, config, feature):
            raise AssertionError("not called")

    with pytest.raises(ValueError, match="rule_cls"):
        register_rule_executor(MissingRuleClsExecutor)
