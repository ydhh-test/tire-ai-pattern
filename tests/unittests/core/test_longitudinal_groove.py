"""
纵向细沟 core 算法测试说明。

这些测试只验证算法层是否能从 128×128 小图中提取纵向细沟特征，不验证规则层打分。
测试图像使用白底黑色竖条合成，便于明确期望的细沟数量、中心位置和边缘过滤行为。
同时覆盖调试模式输出和输入异常，确保算法边界清晰、调用失败时使用项目异常类直接暴露问题。
"""

from pathlib import Path
import shutil

import cv2
import numpy as np
import pytest

from src.common.exceptions import InputDataError, InputTypeError
from src.core import longitudinal_groove as lg
from src.core.longitudinal_groove import detect_longitudinal_grooves


IMAGE_SIZE = 128
DATASET_SOURCE_ROOT = Path(__file__).parents[2] / "datasets" / "task_longitudinal_groove_vis"
DATASET_IMAGE_FOLDERS = ("center_inf", "side_inf")
DEBUG_BASELINE_ROOT = DATASET_SOURCE_ROOT / "debug_baseline"
RESULT_ROOT = Path(__file__).parents[3] / ".results" / "task_longitudinal_groove_vis"
DATASET_RUNTIME_ROOT = RESULT_ROOT / "dataset"
DEBUG_OUTPUT_ROOT = RESULT_ROOT / "debug"
DATASET_IMAGE_RELATIVE_PATHS = [
    image_path.relative_to(DATASET_SOURCE_ROOT)
    for folder_name in DATASET_IMAGE_FOLDERS
    for image_path in sorted((DATASET_SOURCE_ROOT / folder_name).glob("*.png"))
]


def make_small_image_with_grooves(center_columns: list[int], line_width: int = 4) -> np.ndarray:
    image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), 255, dtype=np.uint8)
    half_width = line_width // 2
    for center_column in center_columns:
        start_column = max(0, center_column - half_width)
        end_column = min(IMAGE_SIZE, start_column + line_width)
        image[12:116, start_column:end_column] = 0
    return image


def copy_dataset_image_to_results(relative_image_path: Path) -> Path:
    source_path = DATASET_SOURCE_ROOT / relative_image_path
    rst = {"source_exists": source_path.exists()}
    expect_rst = {"source_exists": True}
    assert rst == expect_rst

    runtime_path = DATASET_RUNTIME_ROOT / relative_image_path
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, runtime_path)
    return runtime_path


def save_debug_image_like_dev(image_path: Path, debug_image: np.ndarray) -> Path:
    image_group = get_debug_image_group(image_path)
    output_dir = DEBUG_OUTPUT_ROOT / image_group
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{image_path.stem}_debug.png"
    success, buffer = cv2.imencode(".png", debug_image)
    rst = {"encode_success": success}
    expect_rst = {"encode_success": True}
    assert rst == expect_rst
    buffer.tofile(str(output_path))
    return output_path


def get_debug_image_group(image_path: Path) -> str:
    return "center" if image_path.parent.name == "center_inf" else "side"


def get_debug_baseline_path(image_path: Path) -> Path:
    image_group = get_debug_image_group(image_path)
    return DEBUG_BASELINE_ROOT / image_group / f"{image_path.stem}_debug.png"


class TestDetectLongitudinalGrooves:
    """纵向细沟 core 算法测试。"""

    @pytest.mark.parametrize("relative_image_path", DATASET_IMAGE_RELATIVE_PATHS, ids=lambda path: path.name)
    def test_dataset_images_can_run_detector_from_results(self, relative_image_path: Path):
        """dev 迁移来的小图 debug 图应与当前黄金基准保持一致。"""
        image_path = copy_dataset_image_to_results(relative_image_path)

        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            pytest.fail(f"读取测试图失败: {image_path}")

        rst = {"image_shape": image.shape}
        expect_rst = {"image_shape": (IMAGE_SIZE, IMAGE_SIZE, 3)}
        assert rst == expect_rst

        groove_count, groove_positions_px, groove_widths_px, line_mask, debug_image = detect_longitudinal_grooves(image, is_debug=True)

        rst = {
            "count_matches_lengths": groove_count == len(groove_positions_px) == len(groove_widths_px),
            "positions_in_image": all(0 <= position < IMAGE_SIZE for position in groove_positions_px),
            "widths_positive": all(width > 0 for width in groove_widths_px),
            "line_mask_exists": line_mask is not None,
            "line_mask_shape": line_mask.shape if line_mask is not None else None,
            "debug_image_exists": debug_image is not None,
            "debug_image_shape": debug_image.shape if debug_image is not None else None,
        }
        expect_rst = {
            "count_matches_lengths": True,
            "positions_in_image": True,
            "widths_positive": True,
            "line_mask_exists": True,
            "line_mask_shape": (IMAGE_SIZE, IMAGE_SIZE),
            "debug_image_exists": True,
            "debug_image_shape": image.shape,
        }
        assert rst == expect_rst

        debug_output_path = save_debug_image_like_dev(image_path, debug_image)
        rst = {"debug_output_exists": debug_output_path.exists()}
        expect_rst = {"debug_output_exists": True}
        assert rst == expect_rst

        saved_debug_image = cv2.imread(str(debug_output_path), cv2.IMREAD_COLOR)
        if saved_debug_image is None:
            pytest.fail(f"读取 debug 输出图失败: {debug_output_path}")

        rst = {"saved_debug_shape": saved_debug_image.shape}
        expect_rst = {"saved_debug_shape": image.shape}
        assert rst == expect_rst

        baseline_debug_path = get_debug_baseline_path(image_path)
        rst = {"baseline_exists": baseline_debug_path.exists()}
        expect_rst = {"baseline_exists": True}
        assert rst == expect_rst

        baseline_debug_image = cv2.imread(str(baseline_debug_path), cv2.IMREAD_COLOR)
        if baseline_debug_image is None:
            pytest.fail(f"读取 debug 基准图失败: {baseline_debug_path}")

        rst = {
            "baseline_debug_shape": baseline_debug_image.shape,
            "debug_matches_baseline": np.array_equal(saved_debug_image, baseline_debug_image),
        }
        expect_rst = {
            "baseline_debug_shape": saved_debug_image.shape,
            "debug_matches_baseline": True,
        }
        assert rst == expect_rst, f"debug 图与基准不一致: output={debug_output_path}, baseline={baseline_debug_path}"

    def test_image_with_two_grooves_detects_two_lines(self):
        """小图中的两条纵向细沟应被完整检测出来。"""
        image = make_small_image_with_grooves([40, 86])

        groove_count, groove_positions_px, _groove_widths_px, line_mask, debug_image = detect_longitudinal_grooves(image)

        rst = {
            "groove_count": groove_count,
            "groove_positions_count": len(groove_positions_px),
            "groove_positions_match": np.allclose(groove_positions_px, [39.5, 85.5], atol=2.0),
            "line_mask": line_mask,
            "debug_image": debug_image,
        }
        expect_rst = {
            "groove_count": 2,
            "groove_positions_count": 2,
            "groove_positions_match": True,
            "line_mask": None,
            "debug_image": None,
        }
        assert rst == expect_rst

    def test_two_grooves_only_reports_features(self):
        """小图中出现两条纵向细沟时，算法只报告特征，不在 core 层扣分。"""
        image = make_small_image_with_grooves([40, 86])

        groove_count, _groove_positions_px, groove_widths_px, _line_mask, _debug_image = detect_longitudinal_grooves(image)

        rst = {
            "groove_count": groove_count,
            "groove_widths_count": len(groove_widths_px),
        }
        expect_rst = {
            "groove_count": 2,
            "groove_widths_count": 2,
        }
        assert rst == expect_rst

    def test_edge_residual_is_ignored(self):
        """靠左边缘的主沟残留应被边缘忽略参数过滤。"""
        image = make_small_image_with_grooves([5])

        groove_count, groove_positions_px, groove_widths_px, _line_mask, _debug_image = detect_longitudinal_grooves(image)

        rst = {
            "groove_count": groove_count,
            "groove_positions_px": groove_positions_px,
            "groove_widths_px": groove_widths_px,
        }
        expect_rst = {
            "groove_count": 0,
            "groove_positions_px": [],
            "groove_widths_px": [],
        }
        assert rst == expect_rst

    def test_debug_mode_returns_mask_and_debug_image(self):
        """is_debug=True 时应返回纵向细沟掩码和调试标注图。"""
        image = make_small_image_with_grooves([64])

        groove_count, _groove_positions_px, _groove_widths_px, line_mask, debug_image = detect_longitudinal_grooves(image, is_debug=True)

        rst = {
            "groove_count": groove_count,
            "line_mask_exists": line_mask is not None,
            "line_mask_shape": line_mask.shape if line_mask is not None else None,
            "debug_image_exists": debug_image is not None,
            "debug_image_shape": debug_image.shape if debug_image is not None else None,
        }
        expect_rst = {
            "groove_count": 1,
            "line_mask_exists": True,
            "line_mask_shape": (IMAGE_SIZE, IMAGE_SIZE),
            "debug_image_exists": True,
            "debug_image_shape": image.shape,
        }
        assert rst == expect_rst

    def test_non_bgr_image_raises_input_data_error(self):
        """非 BGR 图像数组应直接抛出 InputDataError。"""
        image = np.full((IMAGE_SIZE, IMAGE_SIZE), 255, dtype=np.uint8)

        with pytest.raises(InputDataError) as exc_info:
            detect_longitudinal_grooves(image)

        rst = {"has_shape_message": "shape (H, W, 3)" in str(exc_info.value)}
        expect_rst = {"has_shape_message": True}
        assert rst == expect_rst

    def test_non_array_image_raises_input_type_error(self):
        """非 ndarray 图像输入应直接抛出 InputTypeError。"""
        with pytest.raises(InputTypeError) as exc_info:
            detect_longitudinal_grooves(None)

        rst = {"has_image_message": "image" in str(exc_info.value)}
        expect_rst = {"has_image_message": True}
        assert rst == expect_rst

    def test_invalid_pixel_parameter_raises_input_data_error(self):
        """像素阈值参数不合理时应直接抛出 InputDataError。"""
        image = make_small_image_with_grooves([64])

        with pytest.raises(InputDataError) as exc_info:
            detect_longitudinal_grooves(image, min_width_px=0)

        rst = {"has_min_width_message": "min_width_px" in str(exc_info.value)}
        expect_rst = {"has_min_width_message": True}
        assert rst == expect_rst


class TestLongitudinalGrooveCoverageBranches:
    """补齐纵向细沟模块的边界与分支覆盖。"""

    def test_input_type_branches_are_raised(self):
        """输入类型分支应抛出项目异常。"""
        image = make_small_image_with_grooves([64])

        with pytest.raises(InputTypeError):
            detect_longitudinal_grooves(image, is_debug=1)  # type: ignore[arg-type]

    def test_input_relation_branches_are_raised(self):
        """参数关系约束分支应抛出 InputDataError。"""
        image = make_small_image_with_grooves([64])

        with pytest.raises(InputDataError):
            detect_longitudinal_grooves(image, min_width_px=5, max_width_px=4)

        with pytest.raises(InputDataError):
            detect_longitudinal_grooves(image, min_width_px=5, narrow_cluster_px=4)

        with pytest.raises(InputDataError):
            detect_longitudinal_grooves(image, max_angle_deg=85)

    def test_positive_number_and_int_validators_branches(self):
        """数值验证函数的类型和范围分支。"""
        image = make_small_image_with_grooves([64])

        with pytest.raises(InputTypeError):
            detect_longitudinal_grooves(image, nominal_width_px=True)  # type: ignore[arg-type]

        with pytest.raises(InputDataError):
            detect_longitudinal_grooves(image, nominal_width_px=0)

        with pytest.raises(InputTypeError):
            detect_longitudinal_grooves(image, min_width_px=1.5)  # type: ignore[arg-type]

        with pytest.raises(InputTypeError):
            detect_longitudinal_grooves(image, edge_margin_px=1.5)  # type: ignore[arg-type]

        with pytest.raises(InputDataError):
            detect_longitudinal_grooves(image, edge_margin_px=-1)

    def test_split_row_data_by_angle_handles_empty_and_single(self):
        """轨迹切分需覆盖空输入与单元素输入分支。"""
        single = [(10, 30.0, 4.0)]

        rst = {
            "empty_segments": lg._split_row_data_by_angle([], max_angle_deg=30.0),
            "single_segments": lg._split_row_data_by_angle(single, max_angle_deg=30.0),
        }
        expect_rst = {
            "empty_segments": [],
            "single_segments": [single],
        }
        assert rst == expect_rst

    def test_split_row_data_by_angle_splits_on_large_tilt(self):
        """当相邻行偏转角超阈值时应切分轨迹。"""
        row_data = [
            (0, 10.0, 4.0),
            (1, 10.0, 4.0),
            (2, 40.0, 4.0),
            (3, 40.0, 4.0),
        ]

        segments = lg._split_row_data_by_angle(row_data, max_angle_deg=10.0, smooth_half_window=0)

        rst = {
            "segments_count": len(segments),
            "segments": segments,
        }
        expect_rst = {
            "segments_count": 2,
            "segments": [row_data[:2], row_data[2:]],
        }
        assert rst == expect_rst

    def test_build_groove_tracks_covers_gap_finish_and_candidate_skip(self):
        """覆盖轨迹超 gap 完结与候选冲突跳过分支。"""
        all_row_clusters = [
            (0, [(10, 10), (20, 20)]),
            (1, [(11, 11)]),
            (10, [(12, 12)]),
        ]

        tracks = lg._build_groove_tracks(all_row_clusters, max_dx=20.0, max_gap_rows=5)

        rst = {
            "has_min_track_count": len(tracks) >= 2,
            "has_connected_track": any(len(track) >= 2 for track in tracks),
        }
        expect_rst = {
            "has_min_track_count": True,
            "has_connected_track": True,
        }
        assert rst == expect_rst

    def test_split_columns_into_clusters_splits_discontinuous_columns(self):
        """同一行列索引出现间断时应拆分成多个簇。"""
        component_columns = np.array([0, 1, 2, 7, 8], dtype=np.int32)

        clusters = lg._split_columns_into_clusters(component_columns, left_offset=2)

        rst = {"clusters": clusters}
        expect_rst = {"clusters": [(2, 4), (9, 10)]}
        assert rst == expect_rst

    def test_validate_segment_branches(self):
        """候选段校验覆盖空段、过短和宽度越界分支。"""
        too_short = [(0, 10.0, 4.0)]
        too_wide = [(0, 10.0, 20.0), (1, 10.0, 20.0), (2, 10.0, 20.0)]

        rst = {
            "empty_segment": lg._validate_segment([], min_width_px=3, max_width_px=12, min_segment_length_px=2),
            "too_short_segment": lg._validate_segment(
                too_short,
                min_width_px=3,
                max_width_px=12,
                min_segment_length_px=2,
            ),
            "too_wide_segment": lg._validate_segment(
                too_wide,
                min_width_px=3,
                max_width_px=12,
                min_segment_length_px=2,
            ),
        }
        expect_rst = {
            "empty_segment": None,
            "too_short_segment": None,
            "too_wide_segment": None,
        }
        assert rst == expect_rst

    def test_dedupe_segments_merges_overlapped_segments(self):
        """横向接近且纵向重叠超过阈值的段应被合并。"""
        raw_segments = [
            (10.0, 3.0, 0, 10),
            (11.0, 4.0, 2, 8),
        ]

        deduped = lg._dedupe_segments(raw_segments, dedup_distance_px=5.0)

        merged_center, merged_width, merged_first_row, merged_last_row = (
            deduped[0] if deduped else (None, None, None, None)
        )
        rst = {
            "deduped_count": len(deduped),
            "merged_center": merged_center,
            "merged_width": merged_width,
            "merged_first_row": merged_first_row,
            "merged_last_row": merged_last_row,
        }
        expect_rst = {
            "deduped_count": 1,
            "merged_center": pytest.approx(10.5),
            "merged_width": pytest.approx(4.0),
            "merged_first_row": 0,
            "merged_last_row": 10,
        }
        assert rst == expect_rst

    def test_analyze_vertical_lines_skips_short_component(self):
        """连通域高度不足时应被直接跳过。"""
        binary = np.zeros((32, 32), dtype=np.uint8)
        binary[10:14, 16] = 255

        positions, count, line_mask, widths = lg._analyze_vertical_lines(
            binary=binary,
            min_width_px=1,
            narrow_cluster_px=3,
            edge_margin_px=0,
            min_segment_length_px=12,
            max_angle_deg=30.0,
            max_width_px=12,
            dedup_distance_px=8.0,
        )

        rst = {
            "positions": positions,
            "count": count,
            "widths": widths,
            "line_mask_sum": int(line_mask.sum()),
        }
        expect_rst = {
            "positions": [],
            "count": 0,
            "widths": [],
            "line_mask_sum": 0,
        }
        assert rst == expect_rst

    def test_analyze_vertical_lines_continue_on_empty_row_cluster(self, monkeypatch: pytest.MonkeyPatch):
        """当组件行列为空时应走 continue 分支并且不产出细沟。"""
        binary = np.zeros((32, 32), dtype=np.uint8)
        binary[2:28, 15:18] = 255

        original_where = lg.np.where

        def fake_where(_condition):
            return (np.array([], dtype=np.int64),)

        monkeypatch.setattr(lg.np, "where", fake_where)
        try:
            positions, count, line_mask, widths = lg._analyze_vertical_lines(
                binary=binary,
                min_width_px=1,
                narrow_cluster_px=3,
                edge_margin_px=0,
                min_segment_length_px=5,
                max_angle_deg=30.0,
                max_width_px=12,
                dedup_distance_px=8.0,
            )
        finally:
            monkeypatch.setattr(lg.np, "where", original_where)

        rst = {
            "positions": positions,
            "count": count,
            "widths": widths,
            "line_mask_sum": int(line_mask.sum()),
        }
        expect_rst = {
            "positions": [],
            "count": 0,
            "widths": [],
            "line_mask_sum": 0,
        }
        assert rst == expect_rst

    def test_analyze_vertical_lines_continue_on_rejected_segment(self):
        """当候选段宽度不满足约束时应跳过，不计入结果。"""
        binary = np.zeros((64, 64), dtype=np.uint8)
        binary[8:56, 32] = 255

        positions, count, line_mask, widths = lg._analyze_vertical_lines(
            binary=binary,
            min_width_px=3,
            narrow_cluster_px=12,
            edge_margin_px=0,
            min_segment_length_px=8,
            max_angle_deg=30.0,
            max_width_px=12,
            dedup_distance_px=8.0,
        )

        rst = {
            "positions": positions,
            "count": count,
            "widths": widths,
            "line_mask_sum": int(line_mask.sum()),
        }
        expect_rst = {
            "positions": [],
            "count": 0,
            "widths": [],
            "line_mask_sum": 0,
        }
        assert rst == expect_rst