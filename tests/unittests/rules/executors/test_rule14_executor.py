from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.common.exceptions import InputDataError, InputTypeError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import Rule6Feature, Rule14Config, Rule14Feature, Rule14Score
from src.rules.executors.rule14 import Rule14Executor
from src.utils.image_utils import load_image_to_base64


IMAGE_SIZE = 128
DATASET_ROOT = Path("tests/datasets/task_rule14_vis")
BASELINE_PATH = DATASET_ROOT / "baseline.json"


def load_rule14_baseline_cases() -> list[dict]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["cases"]


def make_rule14_config(
    *,
    max_intersections: int = 2,
    max_score: int = 2,
) -> Rule14Config:
    return Rule14Config(
        max_intersections=max_intersections,
        max_score=max_score,
    )


def make_meta(width: int = IMAGE_SIZE, height: int = IMAGE_SIZE, size: int = 1) -> ImageMeta:
    return ImageMeta(
        width=width,
        height=height,
        channels=3,
        mode=ImageModeEnum.RGB,
        format=ImageFormatEnum.PNG,
        size=size,
    )


def make_small_image(
    region: RegionEnum | None = RegionEnum.CENTER,
    image_base64: str = "data:image/png;base64,small",
    meta: ImageMeta | None = None,
) -> SmallImage:
    source_type = SourceTypeEnum.ORIGINAL if region is not None else SourceTypeEnum.CONCAT
    return SmallImage(
        image_base64=image_base64,
        meta=meta or make_meta(),
        biz=ImageBiz(level=LevelEnum.SMALL, region=region, source_type=source_type),
    )


def make_big_image() -> BigImage:
    return BigImage(
        image_base64="data:image/png;base64,big",
        meta=make_meta(),
        biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
    )


def make_baseline_small_image(baseline_case: dict) -> SmallImage:
    image_path = DATASET_ROOT / baseline_case["image_path"]
    return make_small_image(
        region=RegionEnum(baseline_case["region"]),
        image_base64=load_image_to_base64(image_path),
        meta=make_meta(size=image_path.stat().st_size),
    )


def test_exec_feature_converts_detector_result_to_feature(monkeypatch):
    """Rule14 特征提取应只转换算法返回值，不依赖真实算法行为。"""
    decoded_image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 255, dtype=np.uint8)
    calls = {"base64": [], "detector": []}

    def fake_base64_to_ndarray(image_base64: str) -> np.ndarray:
        calls["base64"].append(image_base64)
        return decoded_image

    def fake_detect_transverse_grooves(image_array: np.ndarray, **kwargs):
        calls["detector"].append({"received_decoded_image": image_array is decoded_image, **kwargs})
        return 2, 1, "", None

    monkeypatch.setattr("src.rules.executors.rule14.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule14.detect_transverse_grooves", fake_detect_transverse_grooves)
    small_image = make_small_image(RegionEnum.CENTER)

    feature = Rule14Executor().exec_feature(small_image, make_rule14_config())

    rst = {
        "feature": feature,
        "calls": calls,
    }
    expect_rst = {
        "feature": Rule14Feature(num_intersections=1),
        "calls": {
            "base64": ["data:image/png;base64,small"],
            "detector": [
                {
                    "received_decoded_image": True,
                    "groove_width_px": 25,
                    "is_debug": False,
                }
            ],
        },
    }
    assert rst == expect_rst


def test_exec_feature_uses_side_detector_width(monkeypatch):
    """Rule14 应按小图区域选择 core 检测所需的横沟宽度。"""
    decoded_image = np.full((40, 80, 3), 255, dtype=np.uint8)
    calls = {"base64": [], "detector": []}

    def fake_base64_to_ndarray(image_base64: str) -> np.ndarray:
        calls["base64"].append(image_base64)
        return decoded_image

    def fake_detect_transverse_grooves(image_array: np.ndarray, **kwargs):
        calls["detector"].append({"shape": image_array.shape, **kwargs})
        return 3, 2, "", None

    monkeypatch.setattr("src.rules.executors.rule14.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule14.detect_transverse_grooves", fake_detect_transverse_grooves)
    small_image = make_small_image(RegionEnum.SIDE)

    feature = Rule14Executor().exec_feature(small_image, make_rule14_config())

    rst = {
        "feature": feature,
        "calls": calls,
    }
    expect_rst = {
        "feature": Rule14Feature(num_intersections=2),
        "calls": {
            "base64": ["data:image/png;base64,small"],
            "detector": [
                {
                    "shape": (40, 80, 3),
                    "groove_width_px": 13,
                    "is_debug": False,
                }
            ],
        },
    }
    assert rst == expect_rst


def test_exec_feature_passes_debug_and_returns_visualization(monkeypatch):
    """Rule14 应透传 is_debug，并只在 debug 模式下填充可视化结果。"""
    decoded_image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 255, dtype=np.uint8)
    debug_image = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    calls = {"detector": []}

    def fake_base64_to_ndarray(_image_base64: str) -> np.ndarray:
        return decoded_image

    def fake_detect_transverse_grooves(image_array: np.ndarray, **kwargs):
        calls["detector"].append({"received_decoded_image": image_array is decoded_image, **kwargs})
        return 1, 1, "groove_intersections", debug_image

    monkeypatch.setattr("src.rules.executors.rule14.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule14.detect_transverse_grooves", fake_detect_transverse_grooves)

    feature = Rule14Executor().exec_feature(make_small_image(RegionEnum.CENTER), make_rule14_config(), is_debug=True)

    rst = {
        "feature_fields": {
            "num_intersections": feature.num_intersections,
            "vis_names": feature.vis_names,
            "vis_image_prefix": feature.vis_images[0].split(",", 1)[0] if feature.vis_images else None,
        },
        "calls": calls,
    }
    expect_rst = {
        "feature_fields": {
            "num_intersections": 1,
            "vis_names": ["groove_intersections.png"],
            "vis_image_prefix": "data:image/png;base64",
        },
        "calls": {
            "detector": [
                {
                    "received_decoded_image": True,
                    "groove_width_px": 25,
                    "is_debug": True,
                }
            ],
        },
    }
    assert rst == expect_rst


@pytest.mark.parametrize("baseline_case", load_rule14_baseline_cases(), ids=lambda case: case["image_path"])
def test_exec_feature_and_score_match_real_image_baseline(baseline_case: dict):
    """真实图片应输出已固化的 Rule14 特征和评分 baseline。"""
    executor = Rule14Executor()
    config = make_rule14_config()
    small_image = make_baseline_small_image(baseline_case)

    feature = executor.exec_feature(small_image, config)
    score = executor.exec_score(config, feature)

    rst = {
        "feature": feature.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
    }
    expect_rst = {
        "feature": baseline_case["feature"],
        "score": baseline_case["score"],
    }
    assert rst == expect_rst


@pytest.mark.parametrize(
    ("count", "expected_score"),
    [
        (0, 2),
        (2, 2),
        (3, 0),
    ],
)
def test_exec_score_uses_intersection_count_limit(count: int, expected_score: int):
    """Rule14 评分应按交点数量上限计算。"""
    score = Rule14Executor().exec_score(
        make_rule14_config(max_intersections=2),
        Rule14Feature(num_intersections=count),
    )

    rst = score
    expect_rst = Rule14Score(score=expected_score)
    assert rst == expect_rst


def test_exec_feature_rejects_non_small_image():
    """Rule14 是小图规则，不能直接接收 BigImage。"""
    with pytest.raises(InputTypeError, match="SmallImage"):
        Rule14Executor().exec_feature(make_big_image(), make_rule14_config())


def test_exec_feature_rejects_missing_region():
    """Rule14 选择检测参数需要 center/side 区域信息。"""
    with pytest.raises(InputDataError, match="image.biz.region"):
        Rule14Executor().exec_feature(make_small_image(None), make_rule14_config())


def test_exec_feature_rejects_invalid_debug_flag():
    """Rule14 debug 开关必须是 bool。"""
    with pytest.raises(InputTypeError, match="is_debug"):
        Rule14Executor().exec_feature(make_small_image(), make_rule14_config(), is_debug=1)  # type: ignore[arg-type]


def test_exec_score_rejects_wrong_feature_type():
    """Rule14 打分只接受 Rule14Feature。"""
    with pytest.raises(InputTypeError, match="Rule14Feature"):
        Rule14Executor().exec_score(make_rule14_config(), Rule6Feature(is_continuous=True))


def test_exec_score_rejects_invalid_feature_count():
    """绕过模型校验构造的非法交点数应在评分入口被拒绝。"""
    feature = Rule14Feature.model_construct(num_intersections=-1)

    with pytest.raises(InputDataError, match="feature.num_intersections"):
        Rule14Executor().exec_score(make_rule14_config(), feature)


def test_exec_score_rejects_invalid_config_limit():
    """Rule14 交点数量上限不能为负数。"""
    config = make_rule14_config(max_intersections=-1)

    with pytest.raises(InputDataError, match="config.max_intersections"):
        Rule14Executor().exec_score(config, Rule14Feature(num_intersections=0))