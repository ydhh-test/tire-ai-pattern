# -*- coding: utf-8 -*-
"""
Rule6 执行器单元测试

测试目标：src.rules.executors.rule6.Rule6Executor

最重要的测试验证逻辑（按 .results/rule层重构与迁移需求.md 第 10 节验收标准）：
1. 注册：Rule6Executor 可通过 Rule6Config.name 从注册表读取。
2. 算法对接（不真正调用算法）：使用 monkeypatch 替换 detect_pattern_continuity，
   验证 Rule6Executor.exec_feature：
   - 解码 image.image_base64 为 BGR ndarray，转灰度后传给算法。
   - 把算法返回的 is_continuous 正确写入 Rule6Feature.is_continuous。
   - Rule6Feature.vis_names / vis_images 始终为 None（规则层不处理 debug 可视化）。
   - exec_feature 返回 Rule6Feature 类型。
3. 打分逻辑：exec_score 在连续时返回 max_score，不连续时返回 0；
   严格按 config.max_score，不硬编码默认值；返回 Rule6Score 类型。

人工设计的覆盖性测试逻辑：
- 算法函数仅被调用 1 次（防止重复调用）。
- 入参精确匹配：image_base64 解码后的灰度形状。
- 打分分支覆盖：is_continuous=True / False 两路 + max_score 自定义值。
- 类型契约：exec_feature 返回 Rule6Feature；exec_score 返回 Rule6Score。
"""

from __future__ import annotations

import unittest
from unittest import mock

import numpy as np

from src.models.enums import (
    ImageFormatEnum,
    ImageModeEnum,
    LevelEnum,
    RegionEnum,
)
from src.models.image_models import ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import Rule6Config, Rule6Feature, Rule6Score
from src.rules.executors.rule6 import Rule6Executor
from src.rules.registry import get_rule_executor
from src.utils.image_utils import ndarray_to_base64


def _make_small_image(height: int = 16, width: int = 16) -> SmallImage:
    """构造一张可控的小图，BGR 三通道，像素为单调递增灰度。"""
    bgr = np.tile(
        np.arange(width, dtype=np.uint8)[None, :, None],
        (height, 1, 3),
    )
    return SmallImage(
        image_base64=ndarray_to_base64(bgr, image_type="png"),
        meta=ImageMeta(
            width=width,
            height=height,
            channels=3,
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=0,
        ),
        biz=ImageBiz(level=LevelEnum.SMALL, region=RegionEnum.CENTER),
    )


def _make_config(max_score: int = 10) -> Rule6Config:
    return Rule6Config(max_score=max_score)


# ============================================================
# 注册验收
# ============================================================

class TestRule6ExecutorRegistration(unittest.TestCase):
    """验收 Rule6Executor 通过 Rule6Config.name 注册到全局注册表。"""

    def test_rule6_executor_is_registered_by_config_name(self):
        config = _make_config()

        executor = get_rule_executor(config.name)

        self.assertIsInstance(executor, Rule6Executor)


# ============================================================
# exec_feature 算法对接（mock 算法函数，不实际调用算法）
# ============================================================

class TestRule6ExecFeature(unittest.TestCase):
    """验收 exec_feature 与算法层的对接契约：入参正确、出参映射正确。"""

    def _patch_algorithm(self, return_value):
        """替换 Rule6Executor 内部 import 的 detect_pattern_continuity。"""
        return mock.patch(
            "src.core.detection.pattern_continuity.detect_pattern_continuity",
            return_value=return_value,
        )

    def test_exec_feature_calls_algorithm_with_gray(self):
        """exec_feature 应将灰度图传给算法层，且仅调用一次。"""
        image = _make_small_image(height=16, width=16)
        config = _make_config()
        executor = Rule6Executor()

        with self._patch_algorithm((True, "", None)) as fake_algo:
            executor.exec_feature(image, config)

        expected_call_count = 1
        self.assertEqual(fake_algo.call_count, expected_call_count)

        args, _ = fake_algo.call_args
        gray_arg = args[0]
        self.assertIsInstance(gray_arg, np.ndarray)
        expected_gray_shape = (16, 16)
        self.assertEqual(gray_arg.shape, expected_gray_shape)
        self.assertEqual(gray_arg.dtype, np.uint8)

    def test_exec_feature_maps_is_continuous_true(self):
        """算法返回 is_continuous=True 时应写入 Rule6Feature.is_continuous。"""
        image = _make_small_image()
        config = _make_config()
        executor = Rule6Executor()

        with self._patch_algorithm((True, "", None)):
            rst = executor.exec_feature(image, config)

        expected_is_continuous = True
        self.assertEqual(rst.is_continuous, expected_is_continuous)

    def test_exec_feature_maps_is_continuous_false(self):
        """算法返回 is_continuous=False 时应写入 Rule6Feature.is_continuous。"""
        image = _make_small_image()
        config = _make_config()
        executor = Rule6Executor()

        with self._patch_algorithm((False, "", None)):
            rst = executor.exec_feature(image, config)

        expected_is_continuous = False
        self.assertEqual(rst.is_continuous, expected_is_continuous)

    def test_exec_feature_returns_rule6feature_type(self):
        """exec_feature 应返回 Rule6Feature 实例。"""
        image = _make_small_image()
        config = _make_config()
        executor = Rule6Executor()

        with self._patch_algorithm((True, "", None)):
            rst = executor.exec_feature(image, config)

        self.assertIsInstance(rst, Rule6Feature)

    def test_exec_feature_vis_fields_are_always_none(self):
        """规则层不处理 debug 可视化，vis_names/vis_images 始终为 None。"""
        image = _make_small_image()
        config = _make_config()
        executor = Rule6Executor()

        with self._patch_algorithm(
            (True, "pattern_continuity.png", np.zeros((4, 4, 3), dtype=np.uint8))
        ):
            rst = executor.exec_feature(image, config)

        self.assertIsNone(rst.vis_names)
        self.assertIsNone(rst.vis_images)


# ============================================================
# exec_score 纯逻辑测试
# ============================================================

class TestRule6ExecScore(unittest.TestCase):
    """验收 exec_score 的打分逻辑与类型契约。"""

    def test_exec_score_continuous_returns_max_score(self):
        executor = Rule6Executor()
        config = _make_config(max_score=10)
        feature = Rule6Feature(is_continuous=True)

        rst = executor.exec_score(config, feature)

        expected = 10
        self.assertEqual(rst.score, expected)

    def test_exec_score_discontinuous_returns_zero(self):
        executor = Rule6Executor()
        config = _make_config(max_score=10)
        feature = Rule6Feature(is_continuous=False)

        rst = executor.exec_score(config, feature)

        expected = 0
        self.assertEqual(rst.score, expected)

    def test_exec_score_respects_custom_max_score(self):
        executor = Rule6Executor()
        config = _make_config(max_score=5)
        feature = Rule6Feature(is_continuous=True)

        rst = executor.exec_score(config, feature)

        expected = 5
        self.assertEqual(rst.score, expected)

    def test_exec_score_returns_rule6score_type(self):
        executor = Rule6Executor()
        config = _make_config()
        feature = Rule6Feature(is_continuous=True)

        rst = executor.exec_score(config, feature)

        self.assertIsInstance(rst, Rule6Score)


# ============================================================
# exec_feature 真实算法调用（不 mock，直接调用 detect_pattern_continuity）
# ============================================================

class TestRule6ExecFeatureRealAlgorithm(unittest.TestCase):
    """验收 exec_feature 在不 mock 算法的情况下能正确完成端到端调用。"""

    def _make_all_white_image(self, height: int = 16, width: int = 16) -> SmallImage:
        """全白 BGR 图：灰度后所有像素为 255，上下边缘无暗线，算法应判定连续。"""
        bgr = np.full((height, width, 3), 255, dtype=np.uint8)
        return SmallImage(
            image_base64=ndarray_to_base64(bgr, image_type="png"),
            meta=ImageMeta(
                width=width,
                height=height,
                channels=3,
                mode=ImageModeEnum.RGB,
                format=ImageFormatEnum.PNG,
                size=0,
            ),
            biz=ImageBiz(level=LevelEnum.SMALL, region=RegionEnum.CENTER),
        )

    def test_exec_feature_real_call_on_continuous_image(self):
        """全白图上下边缘无暗线，真实算法应返回 is_continuous=True。"""
        image = self._make_all_white_image(height=16, width=16)
        config = _make_config()
        executor = Rule6Executor()

        rst = executor.exec_feature(image, config)

        self.assertIsInstance(rst, Rule6Feature)
        self.assertTrue(rst.is_continuous)
        self.assertIsNone(rst.vis_names)
        self.assertIsNone(rst.vis_images)


if __name__ == "__main__":
    unittest.main()
