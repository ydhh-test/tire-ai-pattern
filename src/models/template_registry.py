"""拼接模板注册表。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from src.models.scheme_models import StitchingTemplate


TemplateT = TypeVar("TemplateT", bound=type["StitchingTemplate"])

_STITCHING_TEMPLATE_TYPES: list[type["StitchingTemplate"]] = []


def register_stitching_template(template_type: TemplateT) -> TemplateT:
    """注册一个可供 Node2 直接使用的拼接模板类。"""

    if template_type not in _STITCHING_TEMPLATE_TYPES:
        _STITCHING_TEMPLATE_TYPES.append(template_type)
    return template_type


def get_stitching_templates() -> Sequence["StitchingTemplate"]:
    """按注册顺序返回全部可用拼接模板实例。"""

    return tuple(template_type() for template_type in _STITCHING_TEMPLATE_TYPES)
