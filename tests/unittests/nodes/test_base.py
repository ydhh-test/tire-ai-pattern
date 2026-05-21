from __future__ import annotations

import pytest

from src.common.exceptions import InputDataError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum, RuleTypeEnum
from src.models.image_models import ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import (
    Rule1Config,
    Rule13Config,
    Rule20Config,
    Rule22Config,
    Rule6Config,
    Rule6Feature,
    Rule6Score,
    Rule8Config,
    Rule11Config,
    Rule11Feature,
    Rule11Score,
)
from src.nodes.base import (
    BIG_IMAGE_EVALUATOR_CONFIGS,
    DEFAULT_RULE_CONFIGS,
    SMALL_IMAGE_EVALUATOR_CONFIGS,
    evaluate_image_with_configs,
    get_rule_config_types_by_rule_type,
    select_node_configs,
    validate_no_duplicate_config_types,
)


def make_meta() -> ImageMeta:
    return ImageMeta(
        width=10,
        height=20,
        channels=3,
        mode=ImageModeEnum.RGB,
        format=ImageFormatEnum.PNG,
        size=5,
    )


def make_small_image() -> SmallImage:
    return SmallImage(
        image_base64="data:image/png;base64,small",
        meta=make_meta(),
        biz=ImageBiz(level=LevelEnum.SMALL, region=RegionEnum.CENTER),
    )


def make_rule8_config() -> Rule8Config:
    return Rule8Config(groove_width_center=1, groove_width_side=1)


def make_rule11_config() -> Rule11Config:
    return Rule11Config(
        groove_width=1,
        min_width_offset_px=1,
        edge_margin_ratio=0.1,
        min_segment_length_ratio=0.5,
        max_angle_from_vertical=10,
        max_count_center=3,
        max_count_side=2,
    )


class FakeRuleRunner:
    calls = []

    @classmethod
    def reset(cls) -> None:
        cls.calls = []

    @staticmethod
    def exec_feature(image, config, is_debug=False):
        FakeRuleRunner.calls.append(("feature", image.image_base64, config.name, is_debug))
        if config.name == "rule6":
            return Rule6Feature(is_continuous=True)
        if config.name == "rule11":
            return Rule11Feature(num_longitudinal_grooves=2, region=RegionEnum.CENTER)
        raise AssertionError(f"unexpected feature config {config.name}")

    @staticmethod
    def exec_score(config, feature):
        FakeRuleRunner.calls.append(("score", config.name, feature.name))
        if config.name == "rule6":
            return Rule6Score(score=6)
        if config.name == "rule11":
            return Rule11Score(score=4)
        raise AssertionError(f"unexpected score config {config.name}")


def test_select_node_configs_filters_and_uses_node_order():
    """验证节点配置选择会忽略未声明配置，并按节点常量顺序返回 RuleConfig。"""
    configs = [make_rule11_config(), make_rule8_config(), Rule6Config()]

    selected = select_node_configs(configs, SMALL_IMAGE_EVALUATOR_CONFIGS)

    assert [config.name for config in selected] == ["rule6", "rule8", "rule11"]


def test_select_node_configs_does_not_validate_duplicate_config_types():
    """Verify selection only filters and sorts; duplicate validation is a separate step."""
    configs = [Rule6Config(max_score=1), Rule6Config(max_score=2)]

    selected = select_node_configs(configs, SMALL_IMAGE_EVALUATOR_CONFIGS)

    assert [config.max_score for config in selected] == [2]


def test_rule_type_config_lists_are_generated_from_rule_type():
    """Verify evaluator config lists are derived from RuleTypeEnum, not hand-picked."""
    expected_small = get_rule_config_types_by_rule_type(RuleTypeEnum.SMALL_IMAGE)
    expected_big = get_rule_config_types_by_rule_type(RuleTypeEnum.BIG_IMAGE)
    expected_default = get_rule_config_types_by_rule_type(RuleTypeEnum.DEFAULT)

    assert SMALL_IMAGE_EVALUATOR_CONFIGS == expected_small
    assert BIG_IMAGE_EVALUATOR_CONFIGS == expected_big
    assert DEFAULT_RULE_CONFIGS == expected_default


def test_rule_type_config_generation_classifies_known_rules():
    """Verify common rules land in the evaluator list matching their rule_type."""
    assert Rule6Config in SMALL_IMAGE_EVALUATOR_CONFIGS
    assert Rule1Config in BIG_IMAGE_EVALUATOR_CONFIGS
    assert Rule13Config in BIG_IMAGE_EVALUATOR_CONFIGS
    assert Rule20Config in DEFAULT_RULE_CONFIGS
    assert Rule22Config in DEFAULT_RULE_CONFIGS


def test_validate_no_duplicate_config_types_rejects_duplicate_type():
    """验证同一种 RuleConfig 重复出现时会抛出 InputDataError。"""
    configs = [Rule6Config(), Rule6Config()]

    with pytest.raises(InputDataError, match="duplicate rule config"):
        validate_no_duplicate_config_types(configs)


def test_evaluate_image_with_configs_builds_rule_evaluations(monkeypatch):
    """验证通用图片评估 helper 会依次调用 RuleRunner 并汇总 current_score。"""
    FakeRuleRunner.reset()
    monkeypatch.setattr("src.nodes.base.RuleRunner", FakeRuleRunner)

    evaluation = evaluate_image_with_configs(
        make_small_image(),
        [Rule6Config(), make_rule11_config()],
    )

    assert [rule.name for rule in evaluation.rules] == ["rule6", "rule11"]
    assert evaluation.current_score == 10
    assert [call[0] for call in FakeRuleRunner.calls] == ["feature", "score", "feature", "score"]


def test_evaluate_image_with_configs_passes_debug_flag(monkeypatch):
    """验证通用图片评估 helper 会把 debug 开关传给 RuleRunner。"""
    FakeRuleRunner.reset()
    monkeypatch.setattr("src.nodes.base.RuleRunner", FakeRuleRunner)

    evaluate_image_with_configs(
        make_small_image(),
        [Rule6Config()],
        is_debug=True,
    )

    assert FakeRuleRunner.calls[0] == ("feature", "data:image/png;base64,small", "rule6", True)
