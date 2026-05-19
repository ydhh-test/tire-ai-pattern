from __future__ import annotations

import pytest

from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import Rule6Config, Rule6Feature, Rule6Score, Rule8Config, Rule11Config, Rule11Feature, Rule11Score
from src.nodes.small_image_evaluator import evaluate_small_images


def make_meta(width: int = 10, height: int = 20) -> ImageMeta:
    return ImageMeta(
        width=width,
        height=height,
        channels=3,
        mode=ImageModeEnum.RGB,
        format=ImageFormatEnum.PNG,
        size=5,
    )


def make_small_image(region: RegionEnum = RegionEnum.CENTER) -> SmallImage:
    return SmallImage(
        image_base64="data:image/png;base64,small",
        meta=make_meta(),
        biz=ImageBiz(level=LevelEnum.SMALL, region=region),
    )


def make_big_image() -> BigImage:
    return BigImage(
        image_base64="data:image/png;base64,big",
        meta=make_meta(width=40),
        biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
    )


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
            return Rule11Feature(num_longitudinal_grooves=2, region=image.biz.region)
        raise AssertionError(f"unexpected feature config {config.name}")

    @staticmethod
    def exec_score(config, feature):
        FakeRuleRunner.calls.append(("score", config.name, feature.name))
        if config.name == "rule6":
            return Rule6Score(score=6)
        if config.name == "rule11":
            return Rule11Score(score=4)
        raise AssertionError(f"unexpected score config {config.name}")


class FailingRuleRunner(FakeRuleRunner):
    @staticmethod
    def exec_feature(image, config, is_debug=False):
        raise RuntimeError("boom")


def test_evaluate_small_images_writes_independent_evaluations_in_node_order(monkeypatch):
    """验证小图节点接收小图列表并返回已写入独立评估的小图列表。"""
    FakeRuleRunner.reset()
    monkeypatch.setattr("src.nodes.base.RuleRunner", FakeRuleRunner)
    small_images = [make_small_image(), make_small_image(RegionEnum.SIDE)]
    rules_config = [make_rule11_config(), Rule8Config(groove_width_center=1, groove_width_side=1), Rule6Config()]

    result = evaluate_small_images(small_images, rules_config)

    assert result is small_images
    assert [rule.name for rule in result[0].evaluation.rules] == ["rule6", "rule11"]
    assert [rule.name for rule in result[1].evaluation.rules] == ["rule6", "rule11"]
    assert result[0].evaluation is not result[1].evaluation
    assert result[0].evaluation.current_score == 10
    assert [call[0] for call in FakeRuleRunner.calls] == ["feature", "score", "feature", "score", "feature", "score", "feature", "score"]


def test_evaluate_small_images_does_not_handle_runner_exception(monkeypatch):
    """验证小图节点不捕获 RuleRunner 异常，底层异常会直接向上抛出。"""
    FailingRuleRunner.reset()
    monkeypatch.setattr("src.nodes.base.RuleRunner", FailingRuleRunner)

    with pytest.raises(RuntimeError, match="boom"):
        evaluate_small_images([make_small_image()], [Rule6Config()])
