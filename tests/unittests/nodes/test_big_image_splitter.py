from __future__ import annotations

from pathlib import Path

import pytest

from src.common.exceptions import InputTypeError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta
from src.models.rule_models import RibSizeItem, Rule100Config
from src.nodes.big_image_splitter import split_big_image
from src.utils.image_utils import base64_to_ndarray, load_image_to_base64


def _make_big_image(image_path: Path) -> BigImage:
    image_base64 = load_image_to_base64(image_path, with_prefix=True)
    image = base64_to_ndarray(image_base64)
    height, width = image.shape[:2]
    channels = 1 if len(image.shape) == 2 else image.shape[2]
    return BigImage(
        image_base64=image_base64,
        meta=ImageMeta(
            width=width,
            height=height,
            channels=channels,
            mode=ImageModeEnum.GRAY if channels == 1 else ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=len(image_base64.split(",", 1)[1]),
        ),
        biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
    )


def _make_rule100_config() -> Rule100Config:
    return Rule100Config(
        rib_number=5,
        rib_sizes=[
            RibSizeItem(rib_name=f"rib{index}", num_pitchs=6, rib_width=100, rib_height=100)
            for index in range(1, 6)
        ],
    )


def test_split_big_image_returns_small_images_from_real_big_image():
    big_image = _make_big_image(Path("tests/datasets/tire_design_images/images/testcase_001.png"))

    result = split_big_image(big_image, [_make_rule100_config()])

    assert [image.biz.region.value for image in result] == [
        "side",
        "side",
        "center",
        "center",
        "center",
    ]
    assert all(image.biz.level == LevelEnum.SMALL for image in result)
    assert all(image.image_base64.startswith("data:image/png;base64,") for image in result)
    assert all(image.meta.width > 0 and image.meta.height > 0 for image in result)


def test_split_big_image_rejects_non_big_image_input():
    with pytest.raises(InputTypeError, match="split_big_image"):
        split_big_image(big_image={}, rules_config=[])
