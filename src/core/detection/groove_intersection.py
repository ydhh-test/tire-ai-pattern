# -*- coding: utf-8 -*-

"""
横沟检测模块

检测小图中的横向粗线条（横沟）数量，并统计横沟与纵向线条的交叉点数量。
"""

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

from src.common.exceptions import InputDataError, RuntimeProcessError


logger = logging.getLogger(__name__)

_VIS_NAME = "groove_intersections"


def detect_transverse_grooves(
    image: np.ndarray,
    groove_width_px: int,
    is_debug: bool = False,
) -> Tuple[int, int, str, Optional[np.ndarray]]:
    """
    检测横沟数量和横沟与纵向线条的交叉点数量。

    Parameters:
    - image: 输入 BGR 图像，形状为 (H, W, 3)
    - groove_width_px: 横沟最小宽度（像素），必须 >= 1
    - is_debug: 是否输出 debug 可视化图

    Returns:
    - groove_count: 检测到的横沟数量
    - intersection_count: 横沟与纵向线条的交叉点数量
    - vis_name: debug 可视化建议文件名；非 debug 模式为空字符串
    - vis_image: debug 可视化图像；非 debug 模式为 None

    注意：算法层不计算规则得分、不保存文件，也不处理输出目录。
    """
    logger.debug("开始横沟检测，groove_width_px=%d", groove_width_px)

    if image is None:
        raise InputDataError("image", "value", "must not be None")

    if not isinstance(image, np.ndarray):
        raise InputDataError("image", "type", "expected np.ndarray", type(image).__name__)

    if image.ndim != 3 or image.shape[2] != 3:
        raise InputDataError("image", "shape", "expected (H, W, 3) BGR image", image.shape)

    if not isinstance(groove_width_px, int):
        raise InputDataError("groove_width_px", "type", "expected int", type(groove_width_px).__name__)

    if groove_width_px < 1:
        raise InputDataError("groove_width_px", "value", "must be >= 1", groove_width_px)

    image_height, image_width = image.shape[:2]

    logger.debug(
        "横沟参数: groove_width_px=%d",
        groove_width_px,
    )

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=31,
            C=5,
        )

        groove_positions, groove_count, groove_mask = _analyze_grooves(
            binary,
            groove_width_px,
            image_width,
        )
        intersection_count = _count_intersections(binary, groove_mask)

        logger.debug(
            "横沟检测明细: groove_count=%d, groove_positions=%s, intersection_count=%d, image_size=%s",
            groove_count,
            groove_positions,
            intersection_count,
            (image_height, image_width),
        )
    except Exception as original_error:
        raise RuntimeProcessError(
            "detect_transverse_grooves",
            "横沟检测过程失败",
            original_error,
        )

    vis_name = ""
    vis_image = None
    if is_debug:
        try:
            vis_image = _draw_debug_image(
                image,
                groove_mask,
                groove_positions,
                groove_count,
                intersection_count,
            )
            vis_name = _VIS_NAME
        except Exception as original_error:
            raise RuntimeProcessError(
                "_draw_debug_image",
                "横沟可视化处理失败",
                original_error,
            )

    return groove_count, intersection_count, vis_name, vis_image


def _analyze_grooves(
    binary: np.ndarray,
    groove_width_px: int,
    image_width: int,
) -> Tuple[List[float], int, np.ndarray]:
    """通过水平投影识别横向带状区域。"""
    row_sums = (binary > 0).sum(axis=1)
    min_px_per_row = max(groove_width_px, image_width // 4)
    hot_rows = np.where(row_sums >= min_px_per_row)[0]

    groups: List[List[int]] = []
    for row_index in hot_rows.tolist():
        if groups and row_index - groups[-1][-1] <= 3:
            groups[-1].append(row_index)
        else:
            groups.append([row_index])

    min_height = max(3, groove_width_px // 5)
    valid_groups = [group for group in groups if len(group) >= min_height]

    groove_mask = np.zeros_like(binary)
    for group in valid_groups:
        row_start = min(group)
        row_end = max(group) + 1
        groove_mask[row_start:row_end, :] = binary[row_start:row_end, :]

    positions = sorted(float(np.mean(group)) for group in valid_groups)
    return positions, len(positions), groove_mask


def _skeletonize(binary: np.ndarray) -> np.ndarray:
    """使用腐蚀-膨胀差分法对二值图做形态学骨架化。"""
    skeleton = np.zeros_like(binary)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    image = binary.copy()

    while True:
        eroded = cv2.erode(image, element)
        opened = cv2.dilate(eroded, element)
        edge = cv2.subtract(image, opened)
        skeleton = cv2.bitwise_or(skeleton, edge)
        image = eroded
        if cv2.countNonZero(image) == 0:
            break

    return skeleton


def _count_intersections(binary: np.ndarray, groove_mask: np.ndarray) -> int:
    """统计横沟与纵向线条的交叉点数量。"""
    image_height, image_width = binary.shape
    groove_row_active = groove_mask.sum(axis=1) > 0
    groove_row_indices = np.where(groove_row_active)[0]
    if len(groove_row_indices) == 0:
        return 0

    groove_row_groups: List[Tuple[int, int]] = []
    group_start = int(groove_row_indices[0])
    group_end = int(groove_row_indices[0])
    for row_index in groove_row_indices[1:]:
        row_index = int(row_index)
        if row_index - group_end <= 2:
            group_end = row_index
        else:
            groove_row_groups.append((group_start, group_end))
            group_start = row_index
            group_end = row_index
    groove_row_groups.append((group_start, group_end))

    all_rows = np.arange(image_height)
    intersections = 0

    for groove_row_start, groove_row_end in groove_row_groups:
        above_rows = np.where(~groove_row_active & (all_rows < groove_row_start))[0]
        below_rows = np.where(~groove_row_active & (all_rows > groove_row_end))[0]
        above_count = len(above_rows)
        below_count = len(below_rows)

        if above_count == 0 and below_count == 0:
            continue

        if above_count > 0 and below_count > 0:
            threshold_above = max(2, (above_count * 15 + 99) // 100) / image_height
            threshold_below = max(2, (below_count * 15 + 99) // 100) / image_height
            density_above = (binary[above_rows, :] > 0).sum(axis=0) / image_height
            density_below = (binary[below_rows, :] > 0).sum(axis=0) / image_height
            hot_columns = (density_above >= threshold_above) & (density_below >= threshold_below)
        elif above_count > 0:
            threshold_above = max(2, (above_count * 25 + 99) // 100) / image_height
            density_above = (binary[above_rows, :] > 0).sum(axis=0) / image_height
            hot_columns = density_above >= threshold_above
        else:
            threshold_below = max(2, (below_count * 25 + 99) // 100) / image_height
            density_below = (binary[below_rows, :] > 0).sum(axis=0) / image_height
            hot_columns = density_below >= threshold_below

        hot_column_indices = np.where(hot_columns)[0]
        if len(hot_column_indices) == 0:
            continue

        vertical_clusters: List[Tuple[int, int]] = []
        cluster_start = int(hot_column_indices[0])
        cluster_end = int(hot_column_indices[0])
        for column_index in hot_column_indices[1:]:
            column_index = int(column_index)
            if column_index - cluster_end <= 5:
                cluster_end = column_index
            else:
                vertical_clusters.append((cluster_start, cluster_end))
                cluster_start = column_index
                cluster_end = column_index
        vertical_clusters.append((cluster_start, cluster_end))

        vertical_clusters = [
            (cluster_start, cluster_end)
            for cluster_start, cluster_end in vertical_clusters
            if cluster_start > 0 and cluster_end < image_width - 1
        ]

        groove_rows_binary = binary[groove_row_start:groove_row_end + 1, :]
        for column_start, column_end in vertical_clusters:
            if (groove_rows_binary[:, column_start:column_end + 1] > 0).any():
                intersections += 1

    return intersections


def _draw_debug_image(
    image: np.ndarray,
    groove_mask: np.ndarray,
    groove_positions: List[float],
    groove_count: int,
    intersection_count: int,
) -> np.ndarray:
    """在原图上叠加横沟掩码、横沟中心线和检测结果文字。"""
    debug_image = image.copy()

    overlay = np.zeros_like(debug_image)
    overlay[groove_mask > 0] = (0, 200, 0)
    debug_image = cv2.addWeighted(debug_image, 0.7, overlay, 0.3, 0)

    _, image_width = debug_image.shape[:2]
    for groove_position in groove_positions:
        row_position = int(round(groove_position))
        cv2.line(debug_image, (0, row_position), (image_width - 1, row_position), (0, 255, 0), 1)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.35
    font_thickness = 1
    text_color = (255, 255, 255)
    background_color = (0, 0, 0)
    lines = [
        f"G:{groove_count}",
        f"X:{intersection_count}",
    ]
    current_y = 10
    for line in lines:
        (text_width, text_height), _ = cv2.getTextSize(line, font, font_scale, font_thickness)
        cv2.rectangle(
            debug_image,
            (1, current_y - text_height - 1),
            (3 + text_width, current_y + 2),
            background_color,
            -1,
        )
        cv2.putText(
            debug_image,
            line,
            (2, current_y),
            font,
            font_scale,
            text_color,
            font_thickness,
            cv2.LINE_8,
        )
        current_y += text_height + 4

    return debug_image