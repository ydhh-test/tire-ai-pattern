# -*- coding: utf-8 -*-
"""
Rule8 executor unit tests.

These tests mirror the Rule6 migration style: the rule layer decodes the image,
selects explicit algorithm parameters from rule config + image metadata, maps the
algorithm output into Rule8Feature, and computes score from config + feature only.
"""

from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

import numpy as np

from src.models.enums import (
    ImageFormatEnum,
    ImageModeEnum,
    LevelEnum,
    RegionEnum,
    RuleTypeEnum,
)
from src.models.image_models import ImageBiz, ImageMeta, BigImage
from src.models.rule_models import Rule8Config, Rule8Feature, Rule8Score
from src.rules.executors.rule8 import Rule8Executor
from src.rules.registry import get_rule_executor
from src.utils.image_utils import load_image_to_base64, ndarray_to_base64


_DATASET_GROOVE = Path("tests/datasets/test_groove_intersection")


def _make_big_image(
    region: RegionEnum = RegionEnum.CENTER,
    height: int = 16,
    width: int = 16,
) -> BigImage:
    bgr = np.tile(
        np.arange(width, dtype=np.uint8)[None, :, None],
        (height, 1, 3),
    )
    return BigImage(
        image_base64=ndarray_to_base64(bgr, image_type="png"),
        meta=ImageMeta(
            width=width,
            height=height,
            channels=3,
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=0,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, region=region),
    )


def _make_big_image_from_file(
    image_path: Path,
    region: RegionEnum,
    width: int,
    height: int,
) -> BigImage:
    return BigImage(
        image_base64=load_image_to_base64(image_path),
        meta=ImageMeta(
            width=width,
            height=height,
            channels=3,
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=image_path.stat().st_size,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, region=region),
    )


def _make_config(
    max_score: int = 4,
    groove_width_center: float = 25.0,
    groove_width_side: float = 13.0,
) -> Rule8Config:
    return Rule8Config(
        max_score=max_score,
        rule_type=RuleTypeEnum.BIG_IMAGE,
        groove_width_center=groove_width_center,
        groove_width_side=groove_width_side,
    )


class TestRule8ExecutorRegistration(unittest.TestCase):
    def test_rule8_executor_is_registered_by_config_name(self):
        config = _make_config()

        executor = get_rule_executor(config.name)

        self.assertIsInstance(executor, Rule8Executor)


class TestRule8ExecFeature(unittest.TestCase):
    def _patch_algorithm(self, return_value):
        return mock.patch(
            "src.core.detection.groove_intersection.detect_transverse_grooves",
            return_value=return_value,
        )

    def test_exec_feature_calls_algorithm_with_bgr_image(self):
        image = _make_big_image(height=16, width=16)
        config = _make_config()
        executor = Rule8Executor()

        with self._patch_algorithm((2, 1, "", None)) as fake_algo:
            executor.exec_feature(image, config)

        self.assertEqual(fake_algo.call_count, 1)
        args, kwargs = fake_algo.call_args
        bgr_arg = args[0]
        self.assertIsInstance(bgr_arg, np.ndarray)
        self.assertEqual(bgr_arg.shape, (16, 16, 3))
        self.assertEqual(bgr_arg.dtype, np.uint8)
        self.assertEqual(kwargs["groove_width_px"], 25)

    def test_exec_feature_uses_side_groove_width_for_side_image(self):
        image = _make_big_image(region=RegionEnum.SIDE)
        config = _make_config(groove_width_center=25.0, groove_width_side=13.0)
        executor = Rule8Executor()

        with self._patch_algorithm((1, 0, "", None)) as fake_algo:
            executor.exec_feature(image, config)

        _, kwargs = fake_algo.call_args
        rst = kwargs["groove_width_px"]
        expected = 13
        self.assertEqual(rst, expected)

    def test_exec_feature_maps_groove_count(self):
        image = _make_big_image()
        config = _make_config()
        executor = Rule8Executor()

        with self._patch_algorithm((3, 2, "groove_intersections", np.zeros((4, 4, 3), dtype=np.uint8))):
            rst = executor.exec_feature(image, config)

        expected = {
            "num_transverse_grooves": 3,
            "vis_names": None,
            "vis_images": None,
        }
        self.assertIsInstance(rst, Rule8Feature)
        self.assertEqual(rst.num_transverse_grooves, expected["num_transverse_grooves"])
        self.assertEqual(rst.vis_names, expected["vis_names"])
        self.assertEqual(rst.vis_images, expected["vis_images"])

    def test_exec_feature_rounds_config_width_and_keeps_minimum_one(self):
        image = _make_big_image()
        config = _make_config(groove_width_center=0.6, groove_width_side=13.0)
        executor = Rule8Executor()

        with self._patch_algorithm((0, 0, "", None)) as fake_algo:
            executor.exec_feature(image, config)

        _, kwargs = fake_algo.call_args
        rst = kwargs["groove_width_px"]
        expected = 1
        self.assertEqual(rst, expected)

    def test_exec_feature_integration_calls_real_algorithm_with_center_image(self):
        image_path = _DATASET_GROOVE / "center_inf" / "0.png"
        image = _make_big_image_from_file(
            image_path,
            region=RegionEnum.CENTER,
            width=80,
            height=80,
        )
        config = _make_config(groove_width_center=25.0)
        executor = Rule8Executor()

        rst = executor.exec_feature(image, config)

        self.assertIsInstance(rst, Rule8Feature)
        self.assertEqual(rst.num_transverse_grooves, 2)

    def test_exec_feature_integration_calls_real_algorithm_with_side_image(self):
        image_path = _DATASET_GROOVE / "side_inf" / "0.png"
        image = _make_big_image_from_file(
            image_path,
            region=RegionEnum.SIDE,
            width=80,
            height=80,
        )
        config = _make_config(groove_width_side=13.0)
        executor = Rule8Executor()

        rst = executor.exec_feature(image, config)

        self.assertIsInstance(rst, Rule8Feature)
        self.assertEqual(rst.num_transverse_grooves, 2)


class TestRule8ExecScore(unittest.TestCase):
    def test_exec_score_with_grooves_returns_max_score(self):
        executor = Rule8Executor()
        config = _make_config(max_score=4)
        feature = Rule8Feature(num_transverse_grooves=2)

        rst = executor.exec_score(config, feature)

        expected = 4
        self.assertEqual(rst.score, expected)

    def test_exec_score_without_grooves_returns_zero(self):
        executor = Rule8Executor()
        config = _make_config(max_score=4)
        feature = Rule8Feature(num_transverse_grooves=0)

        rst = executor.exec_score(config, feature)

        expected = 0
        self.assertEqual(rst.score, expected)

    def test_exec_score_respects_custom_max_score(self):
        executor = Rule8Executor()
        config = _make_config(max_score=2)
        feature = Rule8Feature(num_transverse_grooves=1)

        rst = executor.exec_score(config, feature)

        expected = 2
        self.assertEqual(rst.score, expected)

    def test_exec_score_returns_rule8score_type(self):
        executor = Rule8Executor()
        config = _make_config()
        feature = Rule8Feature(num_transverse_grooves=1)

        rst = executor.exec_score(config, feature)

        self.assertIsInstance(rst, Rule8Score)

if __name__ == "__main__":
    unittest.main()
