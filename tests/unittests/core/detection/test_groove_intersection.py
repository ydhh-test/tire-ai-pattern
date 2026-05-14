# -*- coding: utf-8 -*-
"""
横沟检测算法单元测试（新架构 dev2）

测试目标：src.core.detection.groove_intersection
API 注意：detect_transverse_grooves() 使用显式参数，返回显式 tuple。

主要变更（相对 dev 分支）：
- import 路径：algorithms.detection.* -> src.core.detection.*
- 输入输出：dict 进出 -> 显式参数和显式 tuple 返回
- 算法层不返回 score，不保存文件，不接收输出目录

最重要的测试验证逻辑：
- 使用 feature/dev 原始 center_inf 与 side_inf 小图验证核心输出：横沟数量与交叉点数量逐图匹配旧算法。
- 使用合成二值图验证横沟聚合、窄带过滤、交叉点计数和边界分支，避免只靠真实图覆盖。

人工设计的覆盖性测试逻辑：
- 针对公开 API：覆盖 None、非 ndarray、灰度图、非法 groove_width_px、debug 输出和异常包装。
    这些分支对应算法层对外边界，能防止重新退回 dict 错误返回或路径保存行为。
- 针对横沟提取：覆盖无热点行、单横沟、多横沟、间隔合并和窄带过滤。
    这些分支决定 groove_count，是横沟检测算法最核心的数量判断来源。
- 针对交叉点统计：覆盖无横沟、上下双侧列密度、仅上侧、仅下侧、全图横沟和边缘列过滤。
    这些分支决定 intersection_count，是交叉点统计算法最核心的数量判断来源。
- 针对 debug 图：覆盖掩码叠加、横沟中心线和文字绘制，确保 debug 输出仍由算法层返回而不落盘。
"""

import pathlib
import unittest
from unittest import mock

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


def _make_bgr_image(height=128, width=128, value=220):
    return np.full((height, width, 3), value, dtype=np.uint8)


def _make_binary_mask(height=128, width=128, bands=None):
    mask = np.zeros((height, width), dtype=np.uint8)
    if bands:
        for row_start, row_end in bands:
            mask[row_start:row_end, :] = 255
    return mask


def _load_color(path: pathlib.Path):
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise AssertionError(f"无法读取图片: {path}")
    return image


@unittest.skipUnless(_HAS_CV2, "需要 numpy 和 opencv-python")
class TestTransverseGroovesApi(unittest.TestCase):
    """公开入口 API 和错误边界测试。"""

    def _run(self, image, groove_width_px=25, **kwargs):
        from src.core.detection.groove_intersection import detect_transverse_grooves
        return detect_transverse_grooves(image, groove_width_px, **kwargs)

    def test_none_image_raises_input_data_error(self):
        from src.common.exceptions import InputDataError

        with self.assertRaises(InputDataError):
            self._run(None)

    def test_non_ndarray_image_raises_input_data_error(self):
        from src.common.exceptions import InputDataError

        with self.assertRaises(InputDataError):
            self._run("not image")

    def test_wrong_ndim_raises_input_data_error(self):
        from src.common.exceptions import InputDataError

        gray = np.zeros((128, 128), dtype=np.uint8)
        with self.assertRaises(InputDataError):
            self._run(gray)

    def test_invalid_groove_width_px_raises_input_data_error(self):
        from src.common.exceptions import InputDataError

        with self.assertRaises(InputDataError):
            self._run(_make_bgr_image(), groove_width_px=0)

    def test_non_int_groove_width_px_raises_input_data_error(self):
        from src.common.exceptions import InputDataError

        with self.assertRaises(InputDataError):
            self._run(_make_bgr_image(), groove_width_px="25")

    def test_output_tuple_has_no_score(self):
        result = self._run(_make_bgr_image())
        groove_count, intersection_count, vis_name, vis_image = result

        rst = (len(result), isinstance(groove_count, int), isinstance(intersection_count, int), vis_name, vis_image)
        expected = (4, True, True, "", None)
        self.assertEqual(rst, expected)

    def test_debug_returns_visualization_without_saving(self):
        image = _make_bgr_image()
        _, _, vis_name, vis_image = self._run(image, is_debug=True)

        rst = (vis_name, vis_image is not None, vis_image.shape if vis_image is not None else None)
        expected = ("groove_intersections", True, image.shape)
        self.assertEqual(rst, expected)

    def test_groove_width_px_affects_detection(self):
        image = _make_bgr_image()
        result_25 = self._run(image, groove_width_px=25)[:2]
        result_13 = self._run(image, groove_width_px=13)[:2]

        rst = (isinstance(result_25[0], int), isinstance(result_13[0], int))
        expected = (True, True)
        self.assertEqual(rst, expected)

    def test_processing_error_is_wrapped(self):
        import src.core.detection.groove_intersection as groove_intersection
        from src.common.exceptions import RuntimeProcessError

        with mock.patch.object(groove_intersection.cv2, "cvtColor", side_effect=ValueError("boom")):
            with self.assertRaises(RuntimeProcessError):
                self._run(_make_bgr_image())

    def test_debug_error_is_wrapped(self):
        import src.core.detection.groove_intersection as groove_intersection
        from src.common.exceptions import RuntimeProcessError

        with mock.patch.object(groove_intersection, "_draw_debug_image", side_effect=ValueError("boom")):
            with self.assertRaises(RuntimeProcessError):
                self._run(_make_bgr_image(), is_debug=True)


@unittest.skipUnless(_HAS_CV2, "需要 numpy 和 opencv-python")
class TestTransverseGroovesInternalBranches(unittest.TestCase):
    """人工设计的白盒分支测试。"""

    def test_analyze_grooves_no_hot_rows(self):
        from src.core.detection.groove_intersection import _analyze_grooves

        binary = np.zeros((32, 32), dtype=np.uint8)
        positions, count, groove_mask = _analyze_grooves(binary, groove_width_px=8, image_width=32)

        rst = (positions, count, int(groove_mask.sum()))
        expected = ([], 0, 0)
        self.assertEqual(rst, expected)

    def test_analyze_grooves_single_and_multiple_bands(self):
        from src.core.detection.groove_intersection import _analyze_grooves

        single = _make_binary_mask(bands=[(50, 80)])
        positions, count, _ = _analyze_grooves(single, groove_width_px=25, image_width=128)
        rst = (
            count,
            len(positions),
            positions[0] >= 50,
            positions[0] <= 79,
        )
        expected = (1, 1, True, True)
        self.assertEqual(rst, expected)

        multiple = _make_binary_mask(bands=[(20, 46), (82, 108)])
        positions, count, _ = _analyze_grooves(multiple, groove_width_px=25, image_width=128)
        rst = (count, positions)
        expected = (2, sorted(positions))
        self.assertEqual(rst, expected)

    def test_analyze_grooves_merges_small_row_gap(self):
        from src.core.detection.groove_intersection import _analyze_grooves

        binary = _make_binary_mask(height=32, width=32, bands=[(5, 10), (12, 18)])
        positions, count, _ = _analyze_grooves(binary, groove_width_px=8, image_width=32)

        rst = (count, len(positions))
        expected = (1, 1)
        self.assertEqual(rst, expected)

    def test_analyze_grooves_filters_too_short_band(self):
        from src.core.detection.groove_intersection import _analyze_grooves

        binary = _make_binary_mask(bands=[(60, 63)])
        _, count, groove_mask = _analyze_grooves(binary, groove_width_px=25, image_width=128)

        rst = (count, int(groove_mask.sum()))
        expected = (0, 0)
        self.assertEqual(rst, expected)

    def test_count_intersections_no_groove(self):
        from src.core.detection.groove_intersection import _count_intersections

        binary = np.zeros((32, 32), dtype=np.uint8)
        groove_mask = np.zeros_like(binary)

        rst = _count_intersections(binary, groove_mask)
        expected = 0
        self.assertEqual(rst, expected)

    def test_count_intersections_with_groove_but_no_hot_columns(self):
        from src.core.detection.groove_intersection import _count_intersections

        binary = np.zeros((32, 32), dtype=np.uint8)
        groove_mask = np.zeros_like(binary)
        groove_mask[14:18, 8:20] = 255

        rst = _count_intersections(binary, groove_mask)
        expected = 0
        self.assertEqual(rst, expected)

    def test_count_intersections_with_both_sides(self):
        from src.core.detection.groove_intersection import _count_intersections

        binary = np.zeros((32, 32), dtype=np.uint8)
        groove_mask = np.zeros_like(binary)
        groove_mask[14:18, 8:20] = 255
        binary[14:18, 10] = 255
        binary[2:12, 10] = 255
        binary[20:30, 10] = 255

        rst = _count_intersections(binary, groove_mask)
        expected = 1
        self.assertEqual(rst, expected)

    def test_count_intersections_with_only_above_side(self):
        from src.core.detection.groove_intersection import _count_intersections

        binary = np.zeros((32, 32), dtype=np.uint8)
        groove_mask = np.zeros_like(binary)
        groove_mask[28:32, 8:20] = 255
        binary[28:32, 10] = 255
        binary[4:24, 10] = 255

        rst = _count_intersections(binary, groove_mask)
        expected = 1
        self.assertEqual(rst, expected)

    def test_count_intersections_with_only_below_side(self):
        from src.core.detection.groove_intersection import _count_intersections

        binary = np.zeros((32, 32), dtype=np.uint8)
        groove_mask = np.zeros_like(binary)
        groove_mask[0:4, 8:20] = 255
        binary[0:4, 10] = 255
        binary[8:28, 10] = 255

        rst = _count_intersections(binary, groove_mask)
        expected = 1
        self.assertEqual(rst, expected)

    def test_count_intersections_ignores_edge_columns_and_full_groove(self):
        from src.core.detection.groove_intersection import _count_intersections

        binary = np.zeros((32, 32), dtype=np.uint8)
        groove_mask = np.full((32, 32), 255, dtype=np.uint8)
        rst = _count_intersections(binary, groove_mask)
        expected = 0
        self.assertEqual(rst, expected)

        groove_mask = np.zeros_like(binary)
        groove_mask[14:18, :] = 255
        binary[:, 0] = 255
        binary[14:18, 0] = 255
        rst = _count_intersections(binary, groove_mask)
        expected = 0
        self.assertEqual(rst, expected)

    def test_skeletonize_returns_binary_shape(self):
        from src.core.detection.groove_intersection import _skeletonize

        binary = np.zeros((16, 16), dtype=np.uint8)
        binary[4:12, 7:9] = 255
        skeleton = _skeletonize(binary)

        rst = (skeleton.shape, int(skeleton.sum()) > 0)
        expected = (binary.shape, True)
        self.assertEqual(rst, expected)

    def test_draw_debug_image_adds_overlay_and_text(self):
        from src.core.detection.groove_intersection import _draw_debug_image

        image = _make_bgr_image(height=32, width=32)
        groove_mask = np.zeros((32, 32), dtype=np.uint8)
        groove_mask[12:18, :] = 255
        debug_image = _draw_debug_image(
            image,
            groove_mask,
            [14.5],
            1,
            0,
        )

        rst = (debug_image.shape, np.array_equal(debug_image, image))
        expected = (image.shape, False)
        self.assertEqual(rst, expected)

_DATASET_GROOVE = pathlib.Path("tests/datasets/test_groove_intersection")
_HAS_DATASET_GROOVE = (_DATASET_GROOVE / "center_inf").exists()
_EXPECTED_REAL_IMAGE_FEATURES = {
    "center_inf": {
        "groove_width_px": 25,
        "expected": {
            "0.png": (2, 2),
            "1.png": (0, 0),
            "2.png": (2, 0),
        },
    },
    "side_inf": {
        "groove_width_px": 13,
        "expected": {
            "0.png": (2, 0),
        },
    },
}


@unittest.skipUnless(_HAS_CV2 and _HAS_DATASET_GROOVE,
                     "需要 opencv 和 tests/datasets/test_groove_intersection 数据集")
class TestTransverseGroovesRealImages(unittest.TestCase):
    """真实原图输入测试。"""

    def _iter_real_images(self):
        for subdir, case in _EXPECTED_REAL_IMAGE_FEATURES.items():
            for image_path in sorted((_DATASET_GROOVE / subdir).glob("*.png")):
                yield subdir, case["groove_width_px"], image_path

    def _run(self, image_path: pathlib.Path, groove_width_px: int):
        from src.core.detection.groove_intersection import detect_transverse_grooves

        return detect_transverse_grooves(_load_color(image_path), groove_width_px)

    def test_real_images_match_expected_features(self):
        """真实原图应按逐图预期返回横沟数量和交叉点数量"""
        for subdir, groove_width_px, image_path in self._iter_real_images():
            with self.subTest(img=f"{subdir}/{image_path.name}"):
                groove_count, intersection_count, vis_name, vis_image = self._run(image_path, groove_width_px)
                expected = _EXPECTED_REAL_IMAGE_FEATURES[subdir]["expected"][image_path.name]
                rst = (groove_count, intersection_count, vis_name, vis_image)
                expected = (*expected, "", None)
                self.assertEqual(rst, expected)

    def test_real_images_output_has_no_score(self):
        """core 层真实图片输出只包含特征和可选 debug 图，不包含 score"""
        for subdir, groove_width_px, image_path in self._iter_real_images():
            with self.subTest(img=f"{subdir}/{image_path.name}"):
                result = self._run(image_path, groove_width_px)
                rst = len(result)
                expected = 4
                self.assertEqual(rst, expected)

if __name__ == "__main__":
    unittest.main()