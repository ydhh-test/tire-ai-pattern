from __future__ import annotations

from typing import TypeVar

from src.rules.base import RuleExecutor, BaseRuleConfig

ExecutorT = TypeVar("ExecutorT", bound=type[RuleExecutor])


class RuleExecutorRegistry:
    """规则执行器运行时注册表，使用规则名作为索引。"""

    def __init__(self) -> None:
        self._executors: dict[str, RuleExecutor] = {}

    def register(self, rule_name: str, executor: RuleExecutor) -> RuleExecutor:
        if rule_name in self._executors:
            raise ValueError(f"duplicate rule executor: {rule_name}")
        self._executors[rule_name] = executor
        return executor

    def get(self, rule_name: str) -> RuleExecutor:
        try:
            return self._executors[rule_name]
        except KeyError:
            raise ValueError(f"rule executor is not registered: {rule_name}") from None


_GLOBAL_REGISTRY = RuleExecutorRegistry()


def register_rule_executor(cls: ExecutorT) -> ExecutorT:
    """注册规则执行器类的装饰器。

    被装饰的执行器类必须继承 ``RuleExecutor``，并定义 ``rule_cls``。
    注册名从 ``rule_cls`` 推导，避免每个 executor 重复定义
    单独的 ``rule_name`` 字段。
    """

    if not issubclass(cls, RuleExecutor):
        raise TypeError("rule executor must inherit RuleExecutor")
    rule_cls = getattr(cls, "rule_cls", None)
    if rule_cls is None:
        raise ValueError("rule executor must define rule_cls")
    rule_name = rule_cls.__name__.lower().replace("config", "")
    _GLOBAL_REGISTRY.register(rule_name, cls())
    return cls


def get_rule_executor(rule_name: str) -> RuleExecutor:
    return _GLOBAL_REGISTRY.get(rule_name)


def get_rule(rule_name: str) -> BaseRuleConfig:
    return _GLOBAL_REGISTRY.get(rule_name).rule_cls