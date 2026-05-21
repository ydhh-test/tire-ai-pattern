from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from src.common.exceptions import InputTypeError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum
from src.models.image_models import ImageBiz, ImageMeta, SmallImage,BigImage
from src.models.rule_models import BaseRuleConfig
from src.models.tire_struct import TireStruct
from src.rules.registry import get_rule
from src.utils.image_utils import base64_to_ndarray, load_image_to_base64
from src.utils.logger import setup_logger
from src.rules.executors import load_all_executors

setup_logger(level="INFO", console_output=True)


def _make_test_image_base64(image_path: str) -> str:
    return load_image_to_base64(Path(image_path), with_prefix=True)


def tire_struct_from_input(data: dict[str, Any]) -> TireStruct:
    return TireStruct(
        big_image=BigImage(
            image_base64='data:image/png;base64,',
            meta=ImageMeta(
                width=1,
                height=1,
                channels=1,
                mode=ImageModeEnum.GRAY,
                format=ImageFormatEnum.PNG,
                size=0,
            ),
            biz=ImageBiz(
                level=LevelEnum.BIG,
                region=RegionEnum.CENTER,
            ),
        ),
        small_images=[
            _small_image_from_input(raw_image)
            for raw_image in data["small_images"]
        ],
        rules_config=[
            _rule_config_from_input(raw_config)
            for raw_config in data["rules_config"]
        ],
        scheme_rank=data["scheme_rank"],
        is_debug=data.get("is_debug", False),
    )


def _small_image_from_input(raw_image: dict[str, Any]) -> SmallImage:
    image_base64 = raw_image["image_base64"]
    image = base64_to_ndarray(image_base64)
    height, width = image.shape[:2]
    channels = 1 if len(image.shape) == 2 else image.shape[2]

    return SmallImage(
        image_base64=image_base64,
        meta=ImageMeta(
            width=width,
            height=height,
            channels=channels,
            mode=_image_mode_from_channels(channels),
            format=_image_format_from_base64(image_base64),
            size=_image_payload_size(image_base64),
        ),
        biz=ImageBiz(
            level=LevelEnum.SMALL,
            region=RegionEnum(raw_image["region"]),
        ),
    )


def _rule_config_from_input(raw_config: dict[str, Any]) -> BaseRuleConfig:
    rule_name = _normalize_rule_name(raw_config["rule"])
    config_class = get_rule(rule_name)
    if config_class is None:
        raise ValueError(f"unsupported rule config: {raw_config['rule']}")

    config_data = {
        key: value
        for key, value in raw_config.items()
        if key != "rule"
    }
    return config_class(**config_data)


def _normalize_rule_name(rule: str | int) -> str:
    if isinstance(rule, int):
        return f"rule{rule}"
    if isinstance(rule, str):
        rule = rule.lower()
        return rule if rule.startswith("rule") else f"rule{rule}"
    raise InputTypeError(
        function="_normalize_rule_name",
        param="rule",
        expected_type="str or int",
        actual_type=type(rule).__name__,
    )


def _image_mode_from_channels(channels: int) -> ImageModeEnum:
    if channels == 1:
        return ImageModeEnum.GRAY
    if channels == 3:
        return ImageModeEnum.RGB
    return ImageModeEnum.RGBA


def _image_format_from_base64(image_base64: str) -> ImageFormatEnum:
    prefix = image_base64.split(",", 1)[0].lower()
    if "jpeg" in prefix or "jpg" in prefix:
        return ImageFormatEnum.JPG
    return ImageFormatEnum.PNG


def _image_payload_size(image_base64: str) -> int:
    payload = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
    return len(base64.b64decode(payload))


input_data = {
    "small_images": [
        # rule 6-8
        {
            "image_base64": _make_test_image_base64('tests/datasets/test_groove_intersection/center_inf/0.png'),
            "region": "center",
        },
        {
            "image_base64": _make_test_image_base64('tests/datasets/test_groove_intersection/center_inf/1.png'),
            "region": "center",
        },
        {
            "image_base64": _make_test_image_base64('tests/datasets/test_groove_intersection/center_inf/2.png'),
            "region": "center",
        },
        {
            "image_base64": _make_test_image_base64('tests/datasets/test_pattern_continuity/side_inf/0.png'),
            "region": "side",
        },
        # rule 11
        {
            "image_base64": _make_test_image_base64('tests/datasets/task_longitudinal_groove_vis/center_inf/0.png'),
            "region": "center",
        },

                {
            "image_base64": _make_test_image_base64('tests/datasets/task_longitudinal_groove_vis/center_inf/2.png'),
            "region": "center",
        },

                {
            "image_base64": _make_test_image_base64('tests/datasets/task_longitudinal_groove_vis/center_inf/4.png'),
            "region": "center",
        },

                {
            "image_base64": _make_test_image_base64('tests/datasets/task_longitudinal_groove_vis/side_inf/1.png'),
            "region": "side",
        },

                {
            "image_base64": _make_test_image_base64('tests/datasets/task_longitudinal_groove_vis/side_inf/syn_s6_diagonal_stagger.png'),
            "region": "side",
        },

    ],
    "rules_config": [
        {
            "rule": "rule1",
        },
        {
            "rule": "rule2",
        },
        {
            "rule": "rule6",
            "max_score": 10,
        },
        {
            "rule": "rule8",
            "max_score": 4,
            "groove_width_center": 25.0,
            "groove_width_side": 13.0,
        },
        {
            "rule": "rule11",
            "groove_width": 1,
            "min_width_offset_px": 1,
            "edge_margin_ratio": 0.1,
            "min_segment_length_ratio": 0.5,
            "max_angle_from_vertical": 10,
            "max_count_center": 3,
            "max_count_side":2,
        },
        {
            "rule": "rule100",
            "rib_number": 5,
            "rib_sizes": [
                {
                    "rib_name": "rib1",
                    "num_pitchs": 5,
                    "rib_width": 400,
                    "rib_height": 640,
                },
                {
                    "rib_name": "rib2",
                    "num_pitchs": 6,
                    "rib_width": 400,
                    "rib_height": 640,
                },
                {
                    "rib_name": "rib3",
                    "num_pitchs": 6,
                    "rib_width": 400,
                    "rib_height": 640,
                },
                {
                    "rib_name": "rib4",
                    "num_pitchs": 6,
                    "rib_width": 400,
                    "rib_height": 640,
                },
                {
                    "rib_name": "rib5",
                    "num_pitchs": 6,
                    "rib_width": 400,
                    "rib_height": 640,
                },
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {
                    "groove_width": 10,
                    "groove_height": 640,
                },
                {
                    "groove_width": 10,
                    "groove_height": 640,
                },
                {
                    "groove_width": 10,
                    "groove_height": 640,
                },
                {
                    "groove_width": 10,
                    "groove_height": 640,
                },
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {
                    "position": "left",
                    "decoration_width": 300,
                    "decoration_height": 640,
                    "decoration_opacity": 128,
                },
                {
                    "position": "right",
                    "decoration_width": 300,
                    "decoration_height": 640,
                    "decoration_opacity": 128,
                },
            ],
        },
    ],
    "scheme_rank": 1,
}


def run_pipline1():
    from src.piplines.pipline1 import run_pipeline1
    load_all_executors()
    tire_struct = tire_struct_from_input(input_data)
    run_pipeline1(tire_struct=tire_struct)


run_pipline1()
