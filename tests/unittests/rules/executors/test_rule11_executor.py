from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.common.exceptions import InputDataError, InputTypeError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import Rule6Feature, Rule11Config, Rule11Feature, Rule11Score
from src.rules.executors.rule11 import Rule11Executor
from src.utils.image_utils import load_image_to_base64


IMAGE_SIZE = 128
DATASET_ROOT = Path("tests/datasets/task_rule11_vis")
BASELINE_PATH = DATASET_ROOT / "baseline.json"


def load_rule11_baseline_cases() -> list[dict]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["cases"]


def make_rule11_config(
    *,
    groove_width: float = 4.0,
    min_width_offset_px: int = 1,
    edge_margin_ratio: float = 0.1,
    min_segment_length_ratio: float = 0.125,
    max_angle_from_vertical: float = 30.0,
    max_count_center: int = 3,
    max_count_side: int = 2,
) -> Rule11Config:
    return Rule11Config(
        groove_width=groove_width,
        min_width_offset_px=min_width_offset_px,
        edge_margin_ratio=edge_margin_ratio,
        min_segment_length_ratio=min_segment_length_ratio,
        max_angle_from_vertical=max_angle_from_vertical,
        max_count_center=max_count_center,
        max_count_side=max_count_side,
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
    """Rule11 特征提取应只转换算法返回值，不依赖真实算法行为。"""
    decoded_image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 255, dtype=np.uint8)
    calls = {"base64": [], "detector": []}

    def fake_base64_to_ndarray(image_base64: str) -> np.ndarray:
        calls["base64"].append(image_base64)
        return decoded_image

    def fake_detect_longitudinal_grooves(image_array: np.ndarray, **kwargs):
        calls["detector"].append({"received_decoded_image": image_array is decoded_image, **kwargs})
        return 2, [39.5, 85.5], [4.0, 4.0], None, None

    monkeypatch.setattr("src.rules.executors.rule11.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule11.detect_longitudinal_grooves", fake_detect_longitudinal_grooves)
    small_image = make_small_image(RegionEnum.CENTER)

    feature = Rule11Executor().exec_feature(small_image, make_rule11_config())

    rst = {
        "feature": feature,
        "calls": calls,
    }
    expect_rst = {
        "feature": Rule11Feature(
            num_longitudinal_grooves=2,
            region=RegionEnum.CENTER,
        ),
        "calls": {
            "base64": ["data:image/png;base64,small"],
            "detector": [
                {
                    "received_decoded_image": True,
                    "is_debug": False,
                }
            ],
        },
    }
    assert rst == expect_rst


def test_exec_feature_uses_detector_defaults(monkeypatch):
    """Rule11 不再从配置派生 core 检测阈值，检测细节由算法默认值负责。"""
    decoded_image = np.full((40, 80, 3), 255, dtype=np.uint8)
    calls = {"base64": [], "detector": []}

    def fake_base64_to_ndarray(image_base64: str) -> np.ndarray:
        calls["base64"].append(image_base64)
        return decoded_image

    def fake_detect_longitudinal_grooves(image_array, **kwargs):
        calls["detector"].append({"shape": image_array.shape, **kwargs})
        return 7, [], [], None, None

    monkeypatch.setattr("src.rules.executors.rule11.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule11.detect_longitudinal_grooves", fake_detect_longitudinal_grooves)
    small_image = make_small_image(RegionEnum.SIDE)
    config = make_rule11_config(
        groove_width=5.0,
        min_width_offset_px=1,
        edge_margin_ratio=0.1,
        min_segment_length_ratio=0.25,
        max_angle_from_vertical=15.0,
    )

    feature = Rule11Executor().exec_feature(small_image, config)

    rst = {
        "feature": feature,
        "calls": calls,
    }
    expect_rst = {
        "feature": Rule11Feature(
            num_longitudinal_grooves=7,
            region=RegionEnum.SIDE,
        ),
        "calls": {
            "base64": ["data:image/png;base64,small"],
            "detector": [
                {
                    "shape": (40, 80, 3),
                    "is_debug": False,
                }
            ],
        },
    }
    assert rst == expect_rst


def test_exec_feature_passes_debug_and_returns_visualization(monkeypatch):
    """Rule11 应透传 is_debug，并只在 debug 模式下填充可视化结果。"""
    decoded_image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 255, dtype=np.uint8)
    debug_image = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    calls = {"detector": []}

    def fake_base64_to_ndarray(_image_base64: str) -> np.ndarray:
        return decoded_image

    def fake_detect_longitudinal_grooves(image_array, **kwargs):
        calls["detector"].append({"received_decoded_image": image_array is decoded_image, **kwargs})
        return 1, [64.0], [4.0], None, debug_image

    monkeypatch.setattr("src.rules.executors.rule11.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule11.detect_longitudinal_grooves", fake_detect_longitudinal_grooves)

    feature = Rule11Executor().exec_feature(make_small_image(RegionEnum.CENTER), make_rule11_config(), is_debug=True)

    rst = {
        "feature_fields": {
            "num_longitudinal_grooves": feature.num_longitudinal_grooves,
            "region": feature.region,
            "vis_names": feature.vis_names,
            "vis_image_prefix": feature.vis_images[0].split(",", 1)[0] if feature.vis_images else None,
        },
        "calls": calls,
    }
    expect_rst = {
        "feature_fields": {
            "num_longitudinal_grooves": 1,
            "region": RegionEnum.CENTER,
            "vis_names": ["rule11_longitudinal_grooves.png"],
            "vis_image_prefix": "data:image/png;base64",
        },
        "calls": {
            "detector": [
                {
                    "received_decoded_image": True,
                    "is_debug": True,
                }
            ],
        },
    }
    assert rst == expect_rst


@pytest.mark.parametrize("baseline_case", load_rule11_baseline_cases(), ids=lambda case: case["image_path"])
def test_exec_feature_and_score_match_real_image_baseline(baseline_case: dict):
    """真实图片应输出已固化的 Rule11 特征和评分 baseline。"""
    executor = Rule11Executor()
    config = make_rule11_config()
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
    ("region", "count", "expected_score"),
    [
        (RegionEnum.CENTER, 3, 4),
        (RegionEnum.CENTER, 4, 0),
        (RegionEnum.SIDE, 2, 4),
        (RegionEnum.SIDE, 3, 0),
    ],
)
def test_exec_score_uses_region_specific_count_limit(region: RegionEnum, count: int, expected_score: int):
    """Rule11 评分应按小图区域选择 center/side 数量上限。"""
    score = Rule11Executor().exec_score(
        make_rule11_config(max_count_center=3, max_count_side=2),
        Rule11Feature(num_longitudinal_grooves=count, region=region),
    )

    rst = score
    expect_rst = Rule11Score(score=expected_score)
    assert rst == expect_rst


def test_exec_feature_rejects_non_small_image():
    """Rule11 是小图规则，不能直接接收 BigImage。"""
    with pytest.raises(InputTypeError, match="SmallImage"):
        Rule11Executor().exec_feature(make_big_image(), make_rule11_config())


def test_exec_feature_rejects_missing_region():
    """Rule11 评分需要 center/side 区域信息。"""
    with pytest.raises(InputDataError, match="image.biz.region"):
        Rule11Executor().exec_feature(make_small_image(None), make_rule11_config())


def test_exec_feature_rejects_invalid_debug_flag():
    """Rule11 debug 开关必须是 bool。"""
    with pytest.raises(InputTypeError, match="is_debug"):
        Rule11Executor().exec_feature(make_small_image(), make_rule11_config(), is_debug=1)  # type: ignore[arg-type]


def test_exec_score_rejects_wrong_feature_type():
    """Rule11 打分只接受 Rule11Feature。"""
    with pytest.raises(InputTypeError, match="Rule11Feature"):
        Rule11Executor().exec_score(make_rule11_config(), Rule6Feature(is_continuous=True))


def test_exec_score_rejects_invalid_feature_region():
    """绕过模型校验构造的非法 region 应在评分入口被拒绝。"""
    feature = Rule11Feature.model_construct(num_longitudinal_grooves=1, region=None)

    with pytest.raises(InputDataError, match="feature.region"):
        Rule11Executor().exec_score(make_rule11_config(), feature)
