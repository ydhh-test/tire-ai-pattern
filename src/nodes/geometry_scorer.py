"""几何评分节点。

本节点基于大图评估结果、小图评估结果和大图血缘信息，计算几何合理性
合规总分，并写回 ``BigImage.scores``。
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Sequence

from src.common.exceptions import InputDataError
from src.models.enums import RuleTypeEnum
from src.models.image_models import BigImage, SmallImage, ImageLineage, ImageScore
from src.models.rule_models import BaseRuleConfig
from src.nodes.base import (
    BIG_IMAGE_EVALUATOR_CONFIGS,
    DEFAULT_RULE_CONFIGS,
    SMALL_IMAGE_EVALUATOR_CONFIGS,
    select_node_configs,
)


NODE_NAME = "geometry_scorer"


def calculate_geometric_scores(
    big_image: BigImage,
    small_images: Sequence[SmallImage],
    rules_config: Sequence[BaseRuleConfig],
) -> BigImage:
    """
    几何合理性业务评分封装函数（节点层接口）

    输入为大图、小图列表和规则配置，输出为更新评分后的大图。

    Args:
        big_image: 已完成 feature 计算的大图对象
        small_images: 小图列表，包含各小图的 evaluation 字段
        rules_config: 规则配置列表，定义各规则的 max_score

    Returns:
        BigImage: 更新评分后的大图对象，big_image.scores.compliance 已更新

    Raises:
        InputDataError: 当必要参数缺失时抛出
    """
    # ========== 最外层参数校验（统一入口） ==========

    # 校验 big_image
    if big_image is None:
        raise InputDataError(NODE_NAME, "big_image", "big_image is required")

    # 校验 big_image.evaluation
    if big_image.evaluation is None:
        raise InputDataError(
            NODE_NAME,
            "big_image.evaluation",
            "big_image.evaluation is required",
        )

    # 校验 lineage
    lineage = big_image.lineage
    if lineage is None:
        raise InputDataError(NODE_NAME, "big_image.lineage", "big_image.lineage is required")

    # ========== 调用核心评分函数 ==========
    score_result = _calculate_geometric_scores(
        big_image=big_image,
        small_images=small_images,
        lineage=lineage,
        rules_config=rules_config,
    )

    # ========== 更新 compliance_score ==========
    if big_image.scores is None:
        big_image.scores = []

    compliance_score_exists = False
    for score in big_image.scores:
        if hasattr(score, 'compliance'):
            score.compliance = score_result['total_score']
            compliance_score_exists = True
            break

    if not compliance_score_exists:
        big_image.scores.append(ImageScore(compliance=score_result['total_score']))

    return big_image


def _calculate_geometric_scores(
    big_image: BigImage,
    small_images: List[SmallImage],
    lineage: ImageLineage,
    rules_config: List[BaseRuleConfig],
) -> dict:
    """
    几何合理性业务评分核心函数（基于已有评分计算）

    注意：调用前需确保所有参数已通过校验（由外层 calculate_geometric_scores 负责）
    只从 evaluation.rules 中提取 score 进行计算，通过图片 base64 信息进行有效小图索引匹配

    Args:
        big_image: 待评分的大图对象，包含 evaluation 字段
        small_images: 小图列表，包含各小图的 evaluation 字段
        lineage: 血缘信息，用于验证拼接方案
        rules_config: 规则配置列表，定义各规则的 max_score

    Returns:
        dict: 包含各项得分和总分的结果字典
        {
            'individual_scores': Dict[str, int],  # 各规则得分
            'total_score': int,                   # 归一化总分（0-100）
            'max_possible_score': int,           # 最大可能得分
            'effective_rule_count': int,         # 有效规则数量
            'rule_details': List[Dict],          # 规则详情列表
        }
    """

    # 步骤1: 规则分类
    big_image_rules = select_node_configs(rules_config, BIG_IMAGE_EVALUATOR_CONFIGS)
    small_image_rules = select_node_configs(rules_config, SMALL_IMAGE_EVALUATOR_CONFIGS)
    default_rules = select_node_configs(rules_config, DEFAULT_RULE_CONFIGS)

    # 步骤2: 从血缘中筛选参与计算的小图
    used_before_images = _extract_used_small_image_regions(lineage)
    
    # 为每个 before_image 找到匹配的小图（只取第一个匹配）
    effective_small_images = []
    matched_indices = set()  # 记录已匹配的小图索引，避免重复使用
    
    for before_image in used_before_images:
        for idx, img in enumerate(small_images):
            if idx not in matched_indices and img.image_base64 == before_image:
                effective_small_images.append(img)
                matched_indices.add(idx)
                break  # 只取第一个匹配

    # 步骤3: 大图规则得分（直接从 evaluation 提取）
    big_image_scores = _extract_big_image_scores(big_image, big_image_rules)

    # 步骤4: 小图规则得分（融合打分，仅使用有效小图）
    small_image_scores = {}
    for rule in small_image_rules:
        small_image_scores[rule.name] = _calculate_small_image_rule_score(
            effective_small_images, rule.name, rule.max_score
        )

    # 步骤5: 默认规则得分
    default_scores = _get_default_scores(default_rules)

    # 步骤6: 归一化计算总分
    all_scores = {**big_image_scores, **small_image_scores, **default_scores}
    total_score, max_possible_score, effective_rule_count = _calculate_normalized_score(
        all_scores, big_image_rules + small_image_rules + default_rules
    )

    # 步骤7: 组装结果
    return _build_result(
        all_scores, total_score, max_possible_score, effective_rule_count, rules_config
    )


def _extract_used_small_image_regions(lineage: ImageLineage) -> list[str]:
    """
    从血缘信息中提取实际参与大图拼接的小图的 before_image 列表

    修改要点：
    1. 返回列表而非集合，保留重复的 before_image
    2. 确保 rib_number 为 5 时有 5 个元素，rib_number 为 4 时有 4 个元素

    Args:
        lineage: 血缘信息对象，包含拼接方案详情

    Returns:
        list[str]: 参与拼接的 before_image 列表（保留顺序和重复）
    """
    used_images = []

    if lineage and lineage.stitching_scheme:
        for rib_impl in lineage.stitching_scheme.ribs_scheme_implementation:
            if rib_impl.before_image and rib_impl.before_image != "SKIPPED_GARBAGE":
                used_images.append(rib_impl.before_image)

    return used_images


def _extract_big_image_scores(
    big_image: BigImage,
    big_image_rules: List[BaseRuleConfig],
) -> Dict[str, int]:
    """
    从大图评估结果中直接提取规则得分

    只从 evaluation.rules 中提取 score，不处理图片数据

    Returns:
        Dict[str, int]: 各规则得分字典
    """
    scores = {}

    evaluation = big_image.evaluation
    if evaluation is None:
        return scores

    for config in big_image_rules:
        rule_eval = evaluation.get_rule(config.name)
        if rule_eval is not None and rule_eval.score is not None:
            scores[config.name] = rule_eval.score.score
        else:
            scores[config.name] = 0

    return scores


def _calculate_small_image_rule_score(
    small_images: List[SmallImage],
    rule_name: str,
    max_score: int,
) -> int:
    """
    小图规则融合打分算法

    算法原理：最终得分 = 满足比例 × 平均得分
    只从 evaluation.rules 中提取 score，不处理图片数据

    Args:
        small_images: 小图列表
        rule_name: 规则名称
        max_score: 规则最大得分

    Returns:
        int: 融合后的规则得分（0-max_score）
    """
    if not small_images:
        return 0

    scores = []
    for small_image in small_images:
        if small_image.evaluation is not None:
            rule_eval = small_image.evaluation.get_rule(rule_name)
            if rule_eval is not None and rule_eval.score is not None:
                scores.append(rule_eval.score.score)

    if not scores:
        return 0

    satisfied_count = sum(1 for s in scores if s > 0)
    satisfy_ratio = satisfied_count / len(scores)

    avg_score = sum(scores) / len(scores)

    final_score = round(satisfy_ratio * avg_score)

    return max(0, min(final_score, max_score))


def _get_default_scores(default_rules: List[BaseRuleConfig]) -> Dict[str, int]:
    """
    获取默认规则得分

    Returns:
        Dict[str, int]: 默认规则得分字典
    """
    scores = {}
    for config in default_rules:
        scores[config.name] = config.max_score
    return scores


def _calculate_normalized_score(
    individual_scores: Dict[str, int],
    rules_config: List[BaseRuleConfig],
) -> Tuple[int, int, int]:
    """
    归一化算法

    算法原理：总分 = (Σ实际得分 / Σ最大可能得分) × 100

    Args:
        individual_scores: 各规则的实际得分
        rules_config: 规则配置列表

    Returns:
        Tuple[int, int, int]: (归一化总分, 最大可能得分, 有效规则数量)
    """
    actual_total = 0
    max_total = 0
    effective_count = 0

    for config in rules_config:
        rule_name = config.name
        if config.max_score > 0 and rule_name in individual_scores:
            actual_total += individual_scores[rule_name]
            max_total += config.max_score
            effective_count += 1

    if max_total == 0:
        return 0, 0, effective_count

    normalized_score = round((actual_total / max_total) * 100)
    return normalized_score, max_total, effective_count


def _build_result(
    individual_scores: Dict[str, int],
    total_score: int,
    max_possible_score: int,
    effective_rule_count: int,
    rules_config: List[BaseRuleConfig],
) -> dict:
    """
    组装最终结果字典

    Returns:
        dict: 符合需求文档结构的结果字典
    """
    rule_details = []
    rule_name_to_config = {config.name: config for config in rules_config}

    for rule_name, score in individual_scores.items():
        config = rule_name_to_config.get(rule_name)
        rule_type = _get_rule_type(rule_name, rules_config)

        rule_details.append({
            'name': rule_name,
            'description': config.description if config else '',
            'score': score,
            'max_score': config.max_score if config else 0,
            'is_applied': score > 0,
            'rule_type': rule_type,
        })

    return {
        'individual_scores': individual_scores,
        'total_score': total_score,
        'max_possible_score': max_possible_score,
        'effective_rule_count': effective_rule_count,
        'rule_details': rule_details,
    }


def _get_rule_type(rule_name: str, rules_config: List[BaseRuleConfig]) -> str:
    """
    获取规则类型

    直接从配置对象的 rule_type 属性获取。

    Args:
        rule_name: 规则名称
        rules_config: 规则配置列表（用于查找对应的配置实例）

    Returns:
        str: 'big_image' | 'small_image' | 'default'
    """
    # 查找对应的配置实例
    for config in rules_config:
        if config.name.lower() == rule_name.lower():
            return config.rule_type

    # 未找到配置实例，默认返回大图规则类型
    return RuleTypeEnum.BIG_IMAGE


def _get_rule_type_from_config(config: BaseRuleConfig) -> str:
    """
    统一获取规则类型

    直接从配置对象的 rule_type 属性获取。

    Args:
        config: 规则配置实例

    Returns:
        str: 'big_image' | 'small_image' | 'default'
    """
    return config.rule_type
