import pytest

from src.models.image_models import BaseImage
from src.models.rule_models import BaseRuleConfig, BaseRuleFeature, BaseRuleScore, Rule19Config
from src.nodes.base import STITCH_SCHEME_GENERATOR_CONFIGS, select_node_configs
from src.rules.base import RuleExecutor
from src.rules import registry as rule_registry
from src.rules.registry import get_rule_executor, register_rule_executor
from src.rules.executors.rule19 import Rule19Executor


def make_rule19_config() -> Rule19Config:
    """构造 Rule19 的规则配置，作为注册查找入参。"""

    return Rule19Config(
        tire_design_width=80,
        decoration_border_alpha=0.5,
        decoration_gray_color=128,
    )


@pytest.fixture
def test_rule_config():
    """注册测试专用 Rule，测试完成后从全局注册表移除。"""

    class TestRuleConfig(BaseRuleConfig):
        description: str = "测试专用规则"
        max_score: int = 0

    class TestRuleExecutor(RuleExecutor):
        rule_cls = TestRuleConfig

    register_rule_executor(TestRuleExecutor)
    config = TestRuleConfig()
    try:
        yield config
    finally:
        rule_registry._GLOBAL_REGISTRY._executors.pop(config.name, None)


def test_rule19_executor_is_registered_by_config_name():
    """验收 Rule19Executor 可以通过 Rule19Config.name 从注册表读取。"""

    config = make_rule19_config()
    expected_executor_type = Rule19Executor

    executor = get_rule_executor(config.name)

    assert isinstance(executor, expected_executor_type)


def test_rule19_config_is_selected_by_stitch_scheme_node(test_rule_config):
    """验收 Node 层规则过滤会把 Rule19 分配给拼接方案生成节点。"""

    rule19_config = make_rule19_config()
    expected_test_rule_executor_type = RuleExecutor
    expected_selected_configs = [rule19_config]

    selected_configs = select_node_configs(
        [test_rule_config, rule19_config],
        STITCH_SCHEME_GENERATOR_CONFIGS,
    )

    assert isinstance(get_rule_executor(test_rule_config.name), expected_test_rule_executor_type)
    assert selected_configs == expected_selected_configs


@pytest.mark.skip(reason="Rule19 当前未接入真实算法；接入算法后启用并补全本验收用例")
def test_rule19_exec_feature():
    """验收 exec_feature 的算法对接。

    Rule19Executor 接入真实算法后，需要验证：
    1. 使用 monkeypatch 替换 Rule19Executor 调用的算法函数，记录实际入参。
    2. 调用 executor.exec_feature(image, config)。
    3. 断言算法函数收到的参数值正确。
    4. 断言算法返回值被正确转换并写入 Rule19Feature 的字段。
    5. 断言 exec_feature 返回 Rule19Feature，且字段值符合算法返回结果。
    """

    # 示例结构：
    # calls = []
    #
    # expected_algorithm_call_count = 1
    # expected_algorithm_call = ("data:image/png;base64,original", 80, 0.5, 128)
    # expected_decoration_border_created = True
    # expected_decoration_border_width = 12
    # def fake_algorithm(image_base64: str, tire_design_width: int, alpha: float, gray_color: int):
    #     actual_algorithm_call = (image_base64, tire_design_width, alpha, gray_color)
    #     calls.append(actual_algorithm_call)
    #     return {
    #         "decoration_border_created": expected_decoration_border_created,
    #         "decoration_border_width": expected_decoration_border_width,
    #     }
    #
    # monkeypatch.setattr("src.rules.executors.rule19.algorithm_func", fake_algorithm)
    #
    # feature = Rule19Executor().exec_feature(image, config)
    #
    # assert len(calls) == expected_algorithm_call_count
    # assert calls[0] == expected_algorithm_call
    # assert isinstance(feature, Rule19Feature)
    # assert feature.decoration_border_created is expected_decoration_border_created
    # assert feature.decoration_border_width == expected_decoration_border_width


@pytest.mark.skip(reason="Rule19 当前未接入真实打分逻辑；接入后启用并补全本验收用例")
def test_rule19_exec_score():
    """验收 exec_score 的打分逻辑。

    Rule19Executor 接入真实打分逻辑后，需要验证：
    1. 构造 Rule19Config 和 Rule19Feature。
    2. 调用 executor.exec_score(config, feature)。
    3. 断言 score 计算结果符合规则预期。
    4. 断言 exec_score 返回 Rule19Score。
    """

    # 示例结构：
    # expected_score = 0
    #
    # score = Rule19Executor().exec_score(config, feature)
    #
    # assert isinstance(score, Rule19Score)
    # assert score.score == expected_score
