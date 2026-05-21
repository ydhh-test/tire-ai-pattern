from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.common.exceptions import InputDataError, InputTypeError
from src.models.enums import (
    ImageFormatEnum,
    ImageModeEnum,
    LevelEnum,
    RegionEnum,
    SourceTypeEnum,
    StitchingSchemeName,
)
from src.models.image_models import BigImage, ImageBiz, ImageLineage, ImageMeta, SmallImage
from src.models.rule_models import Rule8Feature, Rule13Config, Rule13Feature, Rule13Score
from src.models.scheme_models import (
    DecorationImpl,
    DecorationScheme,
    DecorationSchemeAbstract,
    MainGrooveScheme,
    StitchingScheme,
    StitchingSchemeAbstract,
)
from src.rules.executors.rule13 import Rule13Executor
from src.utils.image_utils import base64_to_ndarray, load_image_to_base64


IMAGE_SIZE = 128
DATASET_ROOT = Path("tests/datasets/task_rule13_vis")
BASELINE_PATH = DATASET_ROOT / "baseline.json"
VIS_GOLDEN_PATH = DATASET_ROOT / "vis_golden_rule13_deco300.png"


def load_rule13_baseline_cases() -> list[dict]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["cases"]


def make_rule13_config(
    *,
    land_ratio_min: float = 28.0,
    land_ratio_max: float = 35.0,
    max_score: int = 2,
) -> Rule13Config:
    return Rule13Config(
        land_ratio_min=land_ratio_min,
        land_ratio_max=land_ratio_max,
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


def make_lineage(left_width: int = 0, right_width: int = 0) -> ImageLineage:
    """Build a minimal ImageLineage carrying only the decoration widths Rule13 needs.

    Rule13 reads `decoration_implementation` in [left, right] order; other lineage
    fields are required by the model but unused by Rule13, so we keep them trivial.
    """
    return ImageLineage(
        stitching_scheme=StitchingScheme(
            stitching_scheme_abstract=StitchingSchemeAbstract(
                name=StitchingSchemeName.SYMMETRY_0,
                description="rule13 test",
                rib_number=5,
            ),
            ribs_scheme_implementation=[],
        ),
        main_groove_scheme=MainGrooveScheme(
            main_groove_scheme_abstract=None,
            main_groove_implementation=[],
        ),
        decoration_scheme=DecorationScheme(
            decoration_scheme_abstract=DecorationSchemeAbstract(
                name="rule102",
                description="rule13 test",
            ),
            decoration_implementation=[
                DecorationImpl(
                    decoration_width=left_width,
                    decoration_height=IMAGE_SIZE,
                    decoration_opacity=255,
                ),
                DecorationImpl(
                    decoration_width=right_width,
                    decoration_height=IMAGE_SIZE,
                    decoration_opacity=255,
                ),
            ],
        ),
    )


def make_big_image(
    image_base64: str = "data:image/png;base64,big",
    meta: ImageMeta | None = None,
    lineage: ImageLineage | None = None,
) -> BigImage:
    return BigImage(
        image_base64=image_base64,
        meta=meta or make_meta(),
        biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
        lineage=lineage if lineage is not None else make_lineage(),
    )


def make_baseline_big_image(baseline_case: dict) -> BigImage:
    if "image_full_path" in baseline_case:
        image_path = Path(baseline_case["image_full_path"])
    else:
        image_path = DATASET_ROOT / baseline_case["image_path"]
    return make_big_image(
        image_base64=load_image_to_base64(image_path),
        meta=make_meta(size=image_path.stat().st_size),
        lineage=make_lineage(
            left_width=baseline_case["left_decoration_px"],
            right_width=baseline_case["right_decoration_px"],
        ),
    )


def make_small_image() -> SmallImage:
    return SmallImage(
        image_base64="data:image/png;base64,small",
        meta=make_meta(),
        biz=ImageBiz(level=LevelEnum.SMALL, region=RegionEnum.CENTER),
    )


def test_exec_feature_converts_detector_result_to_feature(monkeypatch):
    """Rule13 feature extraction should only adapt the core detector result."""
    decoded_image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 255, dtype=np.uint8)
    calls = {"base64": [], "detector": []}

    def fake_base64_to_ndarray(image_base64: str) -> np.ndarray:
        calls["base64"].append(image_base64)
        return decoded_image

    def fake_compute_land_sea_ratio(image_array: np.ndarray, **kwargs):
        calls["detector"].append(
            {
                "received_shape": image_array.shape,
                "received_equals_decoded": np.array_equal(image_array, decoded_image),
                **kwargs,
            }
        )
        return 24.72, "", None

    monkeypatch.setattr("src.rules.executors.rule13.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule13.compute_land_sea_ratio", fake_compute_land_sea_ratio)
    big_image = make_big_image()

    feature = Rule13Executor().exec_feature(big_image, make_rule13_config())

    rst = {
        "feature": feature,
        "calls": calls,
    }
    expect_rst = {
        "feature": Rule13Feature(land_ratio=24.72),
        "calls": {
            "base64": ["data:image/png;base64,big"],
            "detector": [
                {
                    "received_shape": (IMAGE_SIZE, IMAGE_SIZE, 3),
                    "received_equals_decoded": True,
                    "is_debug": False,
                }
            ],
        },
    }
    assert rst == expect_rst


def test_exec_feature_passes_debug_and_returns_visualization(monkeypatch):
    """Rule13 should pass is_debug and attach visualization only in debug mode."""
    decoded_image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 255, dtype=np.uint8)
    debug_image = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    calls = {"detector": []}

    def fake_base64_to_ndarray(_image_base64: str) -> np.ndarray:
        return decoded_image

    def fake_compute_land_sea_ratio(image_array: np.ndarray, **kwargs):
        calls["detector"].append(
            {
                "received_shape": image_array.shape,
                "received_equals_decoded": np.array_equal(image_array, decoded_image),
                **kwargs,
            }
        )
        return 30.0, "land_sea_ratio", debug_image

    monkeypatch.setattr("src.rules.executors.rule13.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule13.compute_land_sea_ratio", fake_compute_land_sea_ratio)

    feature = Rule13Executor().exec_feature(make_big_image(), make_rule13_config(), is_debug=True)

    rst = {
        "feature_fields": {
            "land_ratio": feature.land_ratio,
            "vis_names": feature.vis_names,
            "vis_image_prefix": feature.vis_images[0].split(",", 1)[0] if feature.vis_images else None,
        },
        "calls": calls,
    }
    expect_rst = {
        "feature_fields": {
            "land_ratio": 30.0,
            "vis_names": ["land_sea_ratio.png"],
            "vis_image_prefix": "data:image/png;base64",
        },
        "calls": {
            "detector": [
                {
                    "received_shape": (IMAGE_SIZE, IMAGE_SIZE, 3),
                    "received_equals_decoded": True,
                    "is_debug": True,
                }
            ],
        },
    }
    assert rst == expect_rst


@pytest.mark.parametrize(
    ("land_ratio", "expected_score"),
    [
        (28.0, 2),
        (31.5, 2),
        (35.0, 2),
        (27.99, 0),
        (35.01, 0),
    ],
)
def test_exec_score_uses_land_ratio_bounds(land_ratio: float, expected_score: int):
    """Rule13 scoring is inclusive for configured land-ratio percent bounds."""
    score = Rule13Executor().exec_score(
        make_rule13_config(land_ratio_min=28.0, land_ratio_max=35.0),
        Rule13Feature(land_ratio=land_ratio),
    )

    rst = score
    expect_rst = Rule13Score(score=expected_score)
    assert rst == expect_rst


@pytest.mark.parametrize(
    "baseline_case",
    load_rule13_baseline_cases(),
    ids=lambda case: Path(case.get("image_full_path") or case["image_path"]).name,
)
def test_exec_feature_and_score_match_real_image_baseline(baseline_case: dict):
    """Real big images should produce the frozen land-sea-ratio feature baseline."""
    executor = Rule13Executor()
    config = make_rule13_config(land_ratio_min=28.0, land_ratio_max=35.0)
    big_image = make_baseline_big_image(baseline_case)

    feature = executor.exec_feature(big_image, config)
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


def test_exec_feature_rejects_non_big_image():
    """Rule13 is a big-image rule and should reject SmallImage input."""
    with pytest.raises(InputTypeError, match="BigImage"):
        Rule13Executor().exec_feature(make_small_image(), make_rule13_config())


def test_exec_feature_rejects_invalid_debug_flag():
    """Rule13 debug flag must be bool."""
    with pytest.raises(InputTypeError, match="is_debug"):
        Rule13Executor().exec_feature(make_big_image(), make_rule13_config(), is_debug=1)  # type: ignore[arg-type]


def test_exec_score_rejects_wrong_feature_type():
    """Rule13 scoring only accepts Rule13Feature."""
    with pytest.raises(InputTypeError, match="Rule13Feature"):
        Rule13Executor().exec_score(make_rule13_config(), Rule8Feature(num_transverse_grooves=1))


def test_exec_score_rejects_invalid_land_ratio():
    """Bypassed model values outside percent range should be rejected at score entry."""
    feature = Rule13Feature.model_construct(land_ratio=101.0)

    with pytest.raises(InputDataError, match="feature.land_ratio"):
        Rule13Executor().exec_score(make_rule13_config(), feature)


def test_exec_score_rejects_invalid_config_bounds():
    """Rule13 config lower bound must not be greater than upper bound."""
    config = make_rule13_config(land_ratio_min=36.0, land_ratio_max=35.0)

    with pytest.raises(InputDataError, match="config.land_ratio_min"):
        Rule13Executor().exec_score(config, Rule13Feature(land_ratio=30.0))


# ============================================================
# Rule13 crops out left/right decoration stripes before scoring
# ============================================================


def test_exec_feature_crops_decorations_before_calling_detector(monkeypatch):
    """Rule13 should hand the cropped red-box region (gray-edges removed) to the detector."""
    full_width = 100
    left_width = 10
    right_width = 15
    decoded_image = np.arange(IMAGE_SIZE * full_width * 3, dtype=np.uint8).reshape(
        (IMAGE_SIZE, full_width, 3)
    )
    expected_cropped = decoded_image[:, left_width : full_width - right_width, :]
    calls = {"detector": []}

    def fake_base64_to_ndarray(_image_base64: str) -> np.ndarray:
        return decoded_image

    def fake_compute_land_sea_ratio(image_array: np.ndarray, **kwargs):
        calls["detector"].append(
            {
                "received_shape": image_array.shape,
                "received_equals_expected_crop": np.array_equal(image_array, expected_cropped),
                **kwargs,
            }
        )
        return 30.0, "", None

    monkeypatch.setattr("src.rules.executors.rule13.base64_to_ndarray", fake_base64_to_ndarray)
    monkeypatch.setattr("src.rules.executors.rule13.compute_land_sea_ratio", fake_compute_land_sea_ratio)

    big_image = make_big_image(lineage=make_lineage(left_width=left_width, right_width=right_width))
    Rule13Executor().exec_feature(big_image, make_rule13_config())

    rst = calls["detector"]
    expect_rst = [
        {
            "received_shape": (IMAGE_SIZE, full_width - left_width - right_width, 3),
            "received_equals_expected_crop": True,
            "is_debug": False,
        }
    ]
    assert rst == expect_rst


def test_exec_feature_rejects_missing_lineage():
    """Rule13 needs decoration widths from lineage and must fail loudly when absent."""
    big_image = make_big_image(lineage=None)
    big_image.lineage = None  # bypass make_big_image default to force the None branch

    with pytest.raises(InputDataError, match="BigImage.lineage"):
        Rule13Executor().exec_feature(big_image, make_rule13_config())


@pytest.mark.parametrize(
    "decoration_widths",
    [
        [],
        [(0,)],
        [(0,), (0,), (0,)],
    ],
    ids=["empty", "single_item", "three_items"],
)
def test_exec_feature_rejects_decoration_count_not_two(monkeypatch, decoration_widths):
    """Rule13 expects exactly [left, right] decoration entries."""
    lineage = make_lineage()
    lineage.decoration_scheme.decoration_implementation = [
        DecorationImpl(
            decoration_width=w[0],
            decoration_height=IMAGE_SIZE,
            decoration_opacity=255,
        )
        for w in decoration_widths
    ]
    big_image = make_big_image(lineage=lineage)

    monkeypatch.setattr(
        "src.rules.executors.rule13.base64_to_ndarray",
        lambda _b64: np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8),
    )

    with pytest.raises(InputDataError, match="must contain exactly 2 items"):
        Rule13Executor().exec_feature(big_image, make_rule13_config())


def test_exec_feature_rejects_decoration_wider_than_image(monkeypatch):
    """left + right decoration_width must leave at least one column of pattern to score."""
    decoded_image = np.zeros((IMAGE_SIZE, 20, 3), dtype=np.uint8)
    monkeypatch.setattr(
        "src.rules.executors.rule13.base64_to_ndarray", lambda _b64: decoded_image
    )

    big_image = make_big_image(lineage=make_lineage(left_width=15, right_width=10))

    with pytest.raises(InputDataError, match="less than image width"):
        Rule13Executor().exec_feature(big_image, make_rule13_config())


def test_exec_feature_debug_vis_matches_golden():
    """Debug visualization must be generated from the cropped (decoration-free) region.

    Uses a real stitched image (correct_black_decoration.png) with 300 px gray borders on
    each side. Asserts that the vis_image pixel content matches the pre-saved golden file,
    proving the visualization reflects the post-crop tread area, not the full image.
    """
    image_path = Path("tests/datasets/stitching/correct_black_decoration.png")
    big_image = make_big_image(
        image_base64=load_image_to_base64(image_path),
        meta=make_meta(size=image_path.stat().st_size),
        lineage=make_lineage(left_width=300, right_width=300),
    )

    feature = Rule13Executor().exec_feature(big_image, make_rule13_config(), is_debug=True)

    assert feature.vis_images is not None, "is_debug=True should produce vis_images"
    assert len(feature.vis_images) == 1

    vis_array = base64_to_ndarray(feature.vis_images[0])
    golden = cv2.imread(str(VIS_GOLDEN_PATH))

    assert golden is not None, f"Golden file not found: {VIS_GOLDEN_PATH}"
    assert np.array_equal(vis_array, golden), (
        f"vis_image shape {vis_array.shape} does not match golden {golden.shape}; "
        "the visualization may have been generated from the un-cropped image"
    )