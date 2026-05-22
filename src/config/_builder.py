"""共享 dict→TireStruct 构建器，供所有参考配置文件调用。"""

from __future__ import annotations

import base64
from typing import Any

from src.common.exceptions import InputTypeError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import BaseRuleConfig
from src.models.tire_struct import TireStruct
from src.rules.executors import load_all_executors
from src.rules.registry import get_rule
from src.utils.image_utils import base64_to_ndarray

# 确保所有规则执行器已注册（idempotent）
load_all_executors()


# ============================================================
# 公开 API
# ============================================================

def build_tire_struct(config: dict) -> TireStruct:
    """从 CONFIG dict 构建 TireStruct。

    处理流程：
    1. small_images 中 image_base64 → SmallImage
    2. rules_config 中 dict → RuleConfig 实例
    3. big_image: None → 占位 BigImage，dict → 真实 BigImage
    4. 组装 TireStruct
    """
    return TireStruct(
        big_image=_build_big_image(config.get("big_image")),
        small_images=[
            _build_small_image(item)
            for item in config["small_images"]
        ],
        rules_config=[
            _build_rule_config(item)
            for item in config["rules_config"]
        ],
        scheme_rank=config["scheme_rank"],
        is_debug=config.get("is_debug", False),
    )


# ============================================================
# 内部构建函数
# ============================================================

def _build_small_image(raw: dict[str, Any]) -> SmallImage:
    """从 single small_images 元素构建 SmallImage。"""
    image_base64 = raw["image_base64"]
    image = base64_to_ndarray(image_base64)
    height, width = image.shape[:2]
    channels = 1 if len(image.shape) == 2 else image.shape[2]

    return SmallImage(
        image_base64=image_base64,
        meta=ImageMeta(
            width=width,
            height=height,
            channels=channels,
            mode=_channels_to_mode(channels),
            format=_base64_to_format(image_base64),
            size=_base64_payload_size(image_base64),
        ),
        biz=ImageBiz(
            level=LevelEnum.SMALL,
            region=RegionEnum(raw["region"]),
        ),
    )


def _build_rule_config(raw: dict[str, Any]) -> BaseRuleConfig:
    """从 single rules_config 元素构建 RuleConfig 实例。"""
    rule_name = _normalize_rule_name(raw["rule"])
    config_class = get_rule(rule_name)
    if config_class is None:
        raise ValueError(f"unsupported rule config: {raw['rule']}")

    config_data = {
        key: value
        for key, value in raw.items()
        if key != "rule"
    }
    return config_class(**config_data)


def _build_big_image(raw: dict | None) -> BigImage:
    """从 big_image 元素构建 BigImage。

    None → 占位 BigImage
    dict → 真实 BigImage（含 image_base64）
    """
    if raw is None:
        return _placeholder_big_image()
    return BigImage(
        image_base64=raw["image_base64"],
        meta=ImageMeta(
            width=1, height=1, channels=3,
            mode=ImageModeEnum.RGB, format=ImageFormatEnum.PNG, size=0,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, region=RegionEnum.CENTER),
    )


def _placeholder_big_image() -> BigImage:
    """pipeline1 输入用占位 BigImage。"""
    return BigImage(
        image_base64="data:image/png;base64,",
        meta=ImageMeta(
            width=1, height=1, channels=1,
            mode=ImageModeEnum.GRAY, format=ImageFormatEnum.PNG, size=0,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, region=RegionEnum.CENTER),
    )


# ============================================================
# 工具函数
# ============================================================

def _normalize_rule_name(rule: str | int) -> str:
    """规则名归一化：支持 "rule1", "1", 1 等格式。"""
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


def _channels_to_mode(channels: int) -> ImageModeEnum:
    if channels == 1:
        return ImageModeEnum.GRAY
    if channels == 3:
        return ImageModeEnum.RGB
    return ImageModeEnum.RGBA


def _base64_to_format(image_base64: str) -> ImageFormatEnum:
    prefix = image_base64.split(",", 1)[0].lower()
    if "jpeg" in prefix or "jpg" in prefix:
        return ImageFormatEnum.JPG
    return ImageFormatEnum.PNG


def _base64_payload_size(image_base64: str) -> int:
    payload = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
    return len(base64.b64decode(payload))
