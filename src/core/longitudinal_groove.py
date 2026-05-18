from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src.common.exceptions import InputDataError, InputTypeError
from src.utils.logger import get_logger


RowData = list[tuple[int, float, float]]
Segment = tuple[float, float, int, int]

logger = get_logger(__name__)


@dataclass
class _ActiveTrack:
    """逐行追踪中的临时纵向轨迹。"""

    data: RowData
    last_row: int
    last_center_x: float


def detect_longitudinal_grooves(
    image: np.ndarray,
    nominal_width_px: float = 4.0,
    min_width_px: int = 3,
    max_width_px: int = 12,
    narrow_cluster_px: int = 12,
    edge_margin_px: int = 13,
    min_segment_length_px: int = 16,
    max_angle_deg: float = 30.0,
    is_debug: bool = False,
) -> tuple[int, list[float], list[float], np.ndarray | None, np.ndarray | None]:
    """
    检测小图中的纵向细沟或纵向钢片。

    算法层只负责输出检测特征，不接收小图类型，不进行打分，也不判断 center/side 的数量是否合规。
    调用方可基于 ``groove_count``、``groove_positions_px`` 和 ``groove_widths_px`` 执行后续业务逻辑。

    参数：
        image: BGR 图像数组，形状必须为 ``(H, W, 3)``。
        nominal_width_px: 纵向细沟名义宽度，单位为像素。
        min_width_px: 候选线段的最小逐行均值宽度，单位为像素。
        max_width_px: 候选线段的最大逐行均值宽度，单位为像素。
        narrow_cluster_px: 单行窄簇筛选宽度上限，单位为像素。
        edge_margin_px: 左右边缘忽略宽度，单位为像素。
        min_segment_length_px: 候选线段的最小纵向长度，单位为像素。
        max_angle_deg: 相邻行中心点允许偏离竖直方向的最大角度。
        is_debug: 为 ``True`` 时返回 ``line_mask`` 和 ``debug_image``；否则二者为 ``None``。

    返回：
        五元组：纵向细沟数量、中心位置列表、宽度列表、掩码、调试图。

    抛出异常：
        InputTypeError: 入参类型不符合约定。
        InputDataError: 入参数据内容不满足算法前置条件。
    """
    _validate_inputs(
        image=image,
        nominal_width_px=nominal_width_px,
        min_width_px=min_width_px,
        max_width_px=max_width_px,
        narrow_cluster_px=narrow_cluster_px,
        edge_margin_px=edge_margin_px,
        min_segment_length_px=min_segment_length_px,
        max_angle_deg=max_angle_deg,
        is_debug=is_debug,
    )
    logger.debug("开始纵向细沟检测")

    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(gray_image, (3, 3), 0)
    binary_image = cv2.adaptiveThreshold(
        blurred_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=31,
        C=5,
    )

    dedup_distance_px = nominal_width_px * 2.0
    positions, groove_count, line_mask, widths = _analyze_vertical_lines(
        binary=binary_image,
        min_width_px=min_width_px,
        narrow_cluster_px=narrow_cluster_px,
        edge_margin_px=edge_margin_px,
        min_segment_length_px=min_segment_length_px,
        max_angle_deg=max_angle_deg,
        max_width_px=max_width_px,
        dedup_distance_px=dedup_distance_px,
    )

    result_mask = None
    debug_image = None
    if is_debug:
        result_mask = line_mask
        debug_image = _draw_debug_image(
            image=image,
            line_mask=line_mask,
            positions=positions,
            count=groove_count,
        )

    logger.debug("纵向细沟检测完成，数量=%d，位置=%s", groove_count, positions)
    return groove_count, positions, widths, result_mask, debug_image


def _validate_inputs(
    image: np.ndarray,
    nominal_width_px: float,
    min_width_px: int,
    max_width_px: int,
    narrow_cluster_px: int,
    edge_margin_px: int,
    min_segment_length_px: int,
    max_angle_deg: float,
    is_debug: bool,
) -> None:
    if not isinstance(image, np.ndarray):
        raise InputTypeError("detect_longitudinal_grooves", "image", "np.ndarray", type(image).__name__)
    if image.ndim != 3 or image.shape[2] != 3:
        raise InputDataError("detect_longitudinal_grooves", "image", "expected BGR image with shape (H, W, 3)", image.shape)
    if not isinstance(is_debug, bool):
        raise InputTypeError("detect_longitudinal_grooves", "is_debug", "bool", type(is_debug).__name__)

    _validate_positive_number("nominal_width_px", nominal_width_px)
    _validate_positive_int("min_width_px", min_width_px)
    _validate_positive_int("max_width_px", max_width_px)
    _validate_positive_int("narrow_cluster_px", narrow_cluster_px)
    _validate_non_negative_int("edge_margin_px", edge_margin_px)
    _validate_positive_int("min_segment_length_px", min_segment_length_px)
    _validate_positive_number("max_angle_deg", max_angle_deg)

    if max_width_px < min_width_px:
        raise InputDataError("detect_longitudinal_grooves", "max_width_px", "must be greater than or equal to min_width_px", max_width_px)
    if narrow_cluster_px < min_width_px:
        raise InputDataError("detect_longitudinal_grooves", "narrow_cluster_px", "must be greater than or equal to min_width_px", narrow_cluster_px)
    if max_angle_deg >= 85:
        raise InputDataError("detect_longitudinal_grooves", "max_angle_deg", "must be less than 85", max_angle_deg)


def _is_real_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_positive_number(param: str, value: object) -> None:
    if not _is_real_number(value):
        raise InputTypeError("detect_longitudinal_grooves", param, "int or float", type(value).__name__)
    if value <= 0:
        raise InputDataError("detect_longitudinal_grooves", param, "must be positive", value)


def _validate_positive_int(param: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InputTypeError("detect_longitudinal_grooves", param, "int", type(value).__name__)
    if value <= 0:
        raise InputDataError("detect_longitudinal_grooves", param, "must be positive", value)


def _validate_non_negative_int(param: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InputTypeError("detect_longitudinal_grooves", param, "int", type(value).__name__)
    if value < 0:
        raise InputDataError("detect_longitudinal_grooves", param, "must be non-negative", value)


def _bridge_small_vertical_gaps(binary: np.ndarray, max_gap_px: int = 4) -> np.ndarray:
    """用纵向闭运算桥接细沟中的小断点。"""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max_gap_px + 1))
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)


def _split_row_data_by_angle(
    row_data: RowData,
    max_angle_deg: float,
    smooth_half_window: int = 3,
) -> list[RowData]:
    """按局部偏转角度把一条轨迹切分为若干近竖直子段。"""
    if not row_data:
        return []
    if len(row_data) == 1:
        return [row_data]

    center_values = np.array([row_item[1] for row_item in row_data], dtype=np.float64)
    smoothed_centers = np.array(
        [
            center_values[max(0, index - smooth_half_window): min(len(row_data), index + smooth_half_window + 1)].mean()
            for index in range(len(row_data))
        ]
    )

    max_slope = float(np.tan(np.radians(max_angle_deg)))
    segments: list[RowData] = []
    segment_start = 0

    for row_index in range(1, len(row_data)):
        previous_row = row_data[row_index - 1][0]
        current_row = row_data[row_index][0]
        row_gap = max(1, current_row - previous_row)
        center_delta = abs(smoothed_centers[row_index] - smoothed_centers[row_index - 1])

        if center_delta > max_slope * row_gap:
            segments.append(row_data[segment_start:row_index])
            segment_start = row_index

    segments.append(row_data[segment_start:])
    return [segment for segment in segments if segment]


def _build_groove_tracks(
    all_row_clusters: list[tuple[int, list[tuple[int, int]]]],
    max_dx: float = 8.0,
    max_gap_rows: int = 5,
) -> list[RowData]:
    """根据逐行窄簇构建跨行纵向轨迹。"""
    active_tracks: list[_ActiveTrack] = []
    finished_tracks: list[RowData] = []

    for row_index, clusters in all_row_clusters:
        cluster_info = [((start_col + end_col) / 2.0, float(end_col - start_col + 1)) for start_col, end_col in clusters]

        still_active: list[_ActiveTrack] = []
        for track in active_tracks:
            if row_index - track.last_row > max_gap_rows:
                finished_tracks.append(track.data)
            else:
                still_active.append(track)
        active_tracks = still_active

        candidates: list[tuple[float, int, int]] = []
        for track_index, track in enumerate(active_tracks):
            for cluster_index, (center_x, _row_width) in enumerate(cluster_info):
                distance = abs(center_x - track.last_center_x)
                if distance <= max_dx:
                    candidates.append((distance, track_index, cluster_index))
        candidates.sort()

        matched_tracks: set[int] = set()
        matched_clusters: set[int] = set()
        for _distance, track_index, cluster_index in candidates:
            if track_index in matched_tracks or cluster_index in matched_clusters:
                continue
            center_x, row_width = cluster_info[cluster_index]
            active_tracks[track_index].data.append((row_index, center_x, row_width))
            active_tracks[track_index].last_row = row_index
            active_tracks[track_index].last_center_x = center_x
            matched_tracks.add(track_index)
            matched_clusters.add(cluster_index)

        for cluster_index, (center_x, row_width) in enumerate(cluster_info):
            if cluster_index not in matched_clusters:
                active_tracks.append(_ActiveTrack(data=[(row_index, center_x, row_width)], last_row=row_index, last_center_x=center_x))

    for track in active_tracks:
        finished_tracks.append(track.data)
    return finished_tracks


def _analyze_vertical_lines(
    binary: np.ndarray,
    min_width_px: int,
    narrow_cluster_px: int,
    edge_margin_px: int = 0,
    min_segment_length_px: int = 1,
    max_angle_deg: float = 30.0,
    max_width_px: int = 12,
    dedup_distance_px: float = 8.0,
) -> tuple[list[float], int, np.ndarray, list[float]]:
    """从二值图中提取纵向细沟位置、数量、掩码和宽度。"""
    working_binary = binary.copy()
    image_width = binary.shape[1]

    if edge_margin_px > 0:
        working_binary[:, :edge_margin_px] = 0
        working_binary[:, max(0, image_width - edge_margin_px):] = 0

    bridged_binary = _bridge_small_vertical_gaps(working_binary, max_gap_px=4)
    max_tilt_vertical_span = int(min_width_px / np.tan(np.radians(max_angle_deg)))
    vertical_open_height = max(3, min(max_tilt_vertical_span, min_segment_length_px // 2))
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_open_height))
    bridged_binary = cv2.morphologyEx(bridged_binary, cv2.MORPH_OPEN, open_kernel)

    label_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        (bridged_binary > 0).astype(np.uint8), connectivity=8
    )

    line_mask = np.zeros_like(binary)
    raw_segments: list[Segment] = []

    for label_id in range(1, label_count):
        left = int(stats[label_id, cv2.CC_STAT_LEFT])
        top = int(stats[label_id, cv2.CC_STAT_TOP])
        bbox_width = int(stats[label_id, cv2.CC_STAT_WIDTH])
        bbox_height = int(stats[label_id, cv2.CC_STAT_HEIGHT])

        if bbox_height < min_segment_length_px:
            continue

        all_row_clusters: list[tuple[int, list[tuple[int, int]]]] = []
        for row_index in range(top, top + bbox_height):
            component_columns = np.where(labels[row_index, left: left + bbox_width + 1] == label_id)[0]
            if len(component_columns) == 0:
                continue

            row_clusters = _split_columns_into_clusters(component_columns, left)
            narrow_clusters = [
                (start_col, end_col)
                for start_col, end_col in row_clusters
                if (end_col - start_col + 1) <= narrow_cluster_px
            ]
            if narrow_clusters:
                all_row_clusters.append((row_index, narrow_clusters))

        if not all_row_clusters:
            continue

        tracks = _build_groove_tracks(all_row_clusters, max_dx=narrow_cluster_px, max_gap_rows=5)
        for track_data in tracks:
            for segment in _split_row_data_by_angle(track_data, max_angle_deg):
                accepted_segment = _validate_segment(
                    segment=segment,
                    min_width_px=min_width_px,
                    max_width_px=max_width_px,
                    min_segment_length_px=min_segment_length_px,
                )
                if accepted_segment is None:
                    continue

                center_x, mean_width, first_row, last_row = accepted_segment
                _paint_segment_mask(line_mask, segment)
                raw_segments.append((center_x, mean_width, first_row, last_row))

    deduped_segments = _dedupe_segments(raw_segments, dedup_distance_px)
    positions = [position for position, _width, _first_row, _last_row in deduped_segments]
    widths = [width for _position, width, _first_row, _last_row in deduped_segments]
    return positions, len(deduped_segments), line_mask, widths


def _split_columns_into_clusters(component_columns: np.ndarray, left_offset: int) -> list[tuple[int, int]]:
    """把同一行内的前景列切分为多个连续列簇。"""
    row_clusters: list[tuple[int, int]] = []
    cluster_start = int(component_columns[0])
    for column_index in range(1, len(component_columns)):
        if int(component_columns[column_index]) - int(component_columns[column_index - 1]) > 2:
            row_clusters.append((cluster_start + left_offset, int(component_columns[column_index - 1]) + left_offset))
            cluster_start = int(component_columns[column_index])
    row_clusters.append((cluster_start + left_offset, int(component_columns[-1]) + left_offset))
    return row_clusters


def _validate_segment(
    segment: RowData,
    min_width_px: int,
    max_width_px: int,
    min_segment_length_px: int,
) -> Segment | None:
    """校验候选子段的纵向长度和逐行均值宽度。"""
    if not segment:
        return None

    first_row = segment[0][0]
    last_row = segment[-1][0]
    segment_height = last_row - first_row + 1
    if segment_height < min_segment_length_px:
        return None

    mean_width = float(np.mean([row_width for _row_index, _center_x, row_width in segment]))
    if mean_width < min_width_px or mean_width > max_width_px:
        return None

    center_x = float(np.mean([center_x for _row_index, center_x, _row_width in segment]))
    return center_x, mean_width, first_row, last_row


def _paint_segment_mask(line_mask: np.ndarray, segment: RowData) -> None:
    """把通过校验的子段绘制到纵向细沟掩码上。"""
    for row_index, center_x, row_width in segment:
        start_col = max(0, int(round(center_x - row_width / 2.0)))
        end_col = min(line_mask.shape[1] - 1, int(round(center_x + row_width / 2.0)))
        line_mask[row_index, start_col: end_col + 1] = 255


def _dedupe_segments(raw_segments: list[Segment], dedup_distance_px: float) -> list[Segment]:
    """合并横向位置接近且纵向范围高度重叠的重复子段。"""
    raw_segments.sort(key=lambda item: item[0])
    deduped_segments: list[Segment] = []

    for center_x, width, first_row, last_row in raw_segments:
        merged = False
        for segment_index, (existing_center_x, existing_width, existing_first_row, existing_last_row) in enumerate(deduped_segments):
            if abs(center_x - existing_center_x) >= dedup_distance_px:
                continue

            overlap = max(0, min(last_row, existing_last_row) - max(first_row, existing_first_row) + 1)
            min_span = min(last_row - first_row + 1, existing_last_row - existing_first_row + 1)
            if min_span > 0 and overlap / min_span > 0.5:
                deduped_segments[segment_index] = (
                    (existing_center_x + center_x) / 2.0,
                    max(existing_width, width),
                    min(existing_first_row, first_row),
                    max(existing_last_row, last_row),
                )
                merged = True
                break

        if not merged:
            deduped_segments.append((center_x, width, first_row, last_row))

    return deduped_segments


def _draw_debug_image(
    image: np.ndarray,
    line_mask: np.ndarray,
    positions: list[float],
    count: int,
) -> np.ndarray:
    """生成用于人工检查的纵向细沟调试图。"""
    debug_image = image.copy()
    overlay = np.zeros_like(debug_image)
    overlay[line_mask > 0] = (200, 100, 0)
    debug_image = cv2.addWeighted(debug_image, 0.7, overlay, 0.3, 0)

    image_height = debug_image.shape[0]
    for position in positions:
        center_col = int(round(position))
        cv2.line(debug_image, (center_col, 0), (center_col, image_height - 1), (0, 255, 0), 1)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.35
    font_thickness = 1
    text_color = (255, 255, 255)
    background_color = (0, 0, 0)
    labels = [f"lines:{count}"]
    text_y = 10
    for label in labels:
        (text_width, text_height), _baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
        cv2.rectangle(debug_image, (1, text_y - text_height - 1), (3 + text_width, text_y + 2), background_color, -1)
        cv2.putText(debug_image, label, (2, text_y), font, font_scale, text_color, font_thickness, cv2.LINE_AA)
        text_y += text_height + 4

    return debug_image


__all__ = ["detect_longitudinal_grooves"]
