"""大图评估节点。

本节点用于对单张大图执行当前阶段支持的大图规则，完整计算每条规则的
feature 和 score，并把评估结果写回 ``BigImage.evaluation``。
"""

from __future__ import annotations

from src.common.exceptions import InputDataError
from src.models.image_models import BigImage
from src.models.rule_models import BaseRuleConfig
from src.nodes.base import BIG_IMAGE_EVALUATOR_CONFIGS, evaluate_image_with_configs, select_node_configs


NODE_NAME = "big_image_evaluator"


def evaluate_big_image(
    big_image: BigImage | None,
    rules_config: list[BaseRuleConfig],
    is_debug: bool = False,
) -> BigImage:
    """评估单张大图并写回大图评估结果。

    函数会从 ``rules_config`` 中筛选大图评估节点支持的规则配置，
    当前执行顺序由 ``BIG_IMAGE_EVALUATOR_CONFIGS`` 决定。该节点负责
    首次完整执行大图规则的 feature 和 score 计算。

    Args:
        big_image: 待评估的大图对象。不能为 ``None``。
        rules_config: 用户传入的完整规则配置列表，函数只会执行本节点
            支持的规则配置。
        is_debug: 是否在规则特征中附带 debug 可视化结果。

    Returns:
        原始 ``big_image`` 对象。函数会原地写入最新的
        ``big_image.evaluation``。

    Raises:
        InputDataError: 当 ``big_image`` 缺失，或规则配置存在重复类型时抛出。
        Exception: 规则执行过程中的异常不会在节点内捕获，会原样向上透传。
    """

    if big_image is None:
        raise InputDataError(NODE_NAME, "big_image", "big_image is required")

    configs = select_node_configs(
        rules_config,
        BIG_IMAGE_EVALUATOR_CONFIGS,
    )
    big_image.evaluation = evaluate_image_with_configs(
        big_image,
        configs,
        is_debug=is_debug,
    )

    return big_image
