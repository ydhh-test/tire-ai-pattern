"""Big image splitter node."""

from __future__ import annotations

import base64

import numpy as np

from src.common.exceptions import InputTypeError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import BaseRuleConfig, Rule100Config
from src.processing.single_image_splitter import DEFAULT_CONFIG, process_single_file
from src.utils.image_utils import base64_to_ndarray, ndarray_to_base64


def split_big_image(
    big_image: BigImage,
    rules_config: list[BaseRuleConfig],
) -> list[SmallImage]:
    """Split one ``BigImage`` into ``SmallImage`` objects."""

    if not isinstance(big_image, BigImage):
        raise InputTypeError(
            function="split_big_image",
            param="big_image",
            expected_type="BigImage",
            actual_type=type(big_image).__name__,
        )

    split_config = _split_config_from_rules(rules_config)
    big_image_array = base64_to_ndarray(big_image.image_base64)
    split_result = process_single_file(big_image_array, split_config)
    stats = split_result["stats"]
    if stats.get("status") != "success":
        raise RuntimeError(stats.get("error_message", stats.get("status", "split failed")))

    small_images = [
        _small_image_from_array(image, RegionEnum.SIDE)
        for image, _suffix in split_result["side_final_images"]
    ]
    small_images.extend(
        _small_image_from_array(image, RegionEnum.CENTER)
        for image, _suffix in split_result["center_final_images"]
    )
    return small_images


def _split_config_from_rules(rules_config: list[BaseRuleConfig]) -> dict[str, object]:
    config = DEFAULT_CONFIG.copy()
    rule100 = next((rule for rule in rules_config if isinstance(rule, Rule100Config)), None)
    if rule100 is not None and rule100.rib_number in (4, 5):
        config["num_segments_to_remove"] = rule100.rib_number - 1
    return config


def _small_image_from_array(image: np.ndarray, region: RegionEnum) -> SmallImage:
    image_base64 = ndarray_to_base64(image, image_type="png", with_prefix=True)
    height, width = image.shape[:2]
    channels = 1 if len(image.shape) == 2 else image.shape[2]

    return SmallImage(
        image_base64=image_base64,
        meta=ImageMeta(
            width=width,
            height=height,
            channels=channels,
            mode=_image_mode_from_channels(channels),
            format=ImageFormatEnum.PNG,
            size=_image_payload_size(image_base64),
        ),
        biz=ImageBiz(
            level=LevelEnum.SMALL,
            region=region,
        ),
    )


def _image_mode_from_channels(channels: int) -> ImageModeEnum:
    if channels == 1:
        return ImageModeEnum.GRAY
    if channels == 3:
        return ImageModeEnum.RGB
    return ImageModeEnum.RGBA


def _image_payload_size(image_base64: str) -> int:
    payload = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
    return len(base64.b64decode(payload))
