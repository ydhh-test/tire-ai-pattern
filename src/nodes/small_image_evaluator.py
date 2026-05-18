"""小图评估节点。

本节点用于对每张小图执行当前阶段支持的小图规则，并把每张图独立的
评估结果写回到对应 ``SmallImage.evaluation``。
"""

from __future__ import annotations

from src.common.exceptions import InputDataError
from src.models.image_models import SmallImage
from src.models.rule_models import BaseRuleConfig
from src.nodes.base import SMALL_IMAGE_EVALUATOR_CONFIGS, evaluate_image_with_configs, select_node_configs


NODE_NAME = "small_image_evaluator"


def evaluate_small_images(
    small_images: list[SmallImage],
    rules_config: list[BaseRuleConfig],
    is_debug: bool = False,
) -> list[SmallImage]:
    """评估一组小图并写回每张小图的评估结果。

    函数会从 ``rules_config`` 中筛选小图评估节点支持的规则配置，
    当前执行顺序由 ``SMALL_IMAGE_EVALUATOR_CONFIGS`` 决定。每张小图
    都会独立执行 feature 和 score 计算，并将生成的 ``ImageEvaluation``
    写入该小图的 ``evaluation`` 字段。

    Args:
        small_images: 待评估的小图列表。列表不能为空。
        rules_config: 用户传入的完整规则配置列表，函数只会执行本节点
            支持的规则配置。
        is_debug: 是否在规则特征中附带 debug 可视化结果。

    Returns:
        原始 ``small_images`` 列表对象。列表内每个 ``SmallImage`` 都会
        被原地写入最新的 ``evaluation``。

    Raises:
        InputDataError: 当 ``small_images`` 为空，或规则配置存在重复类型时抛出。
        Exception: 规则执行过程中的异常不会在节点内捕获，会原样向上透传。
    """

    if not small_images:
        raise InputDataError(NODE_NAME, "small_images", "small_images is required")

    configs = select_node_configs(
        rules_config,
        SMALL_IMAGE_EVALUATOR_CONFIGS,
    )

    for small_image in small_images:
        small_image.evaluation = evaluate_image_with_configs(
            small_image,
            configs,
            is_debug=is_debug,
        )

    return small_images
