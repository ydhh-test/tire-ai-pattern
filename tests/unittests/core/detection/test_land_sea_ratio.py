# -*- coding: utf-8 -*-
"""
海陆比算法单元测试（新架构 dev2）

测试目标：src.core.detection.land_sea_ratio
API 注意：compute_land_sea_ratio() 只接收图像和 is_debug，返回 (ratio_percent, vis_name, vis_image)。
评分逻辑已移至规则层 Rule13Executor，本文件不测试评分。

主要变更（相对旧版本）：
- 移除 target_min / target_max / margin 参数（业务配置，属于规则层）
- 移除 score 返回值（评分逻辑，属于规则层）
- debug 图不再标注评分，只标注海陆比值

最重要的测试验证逻辑：
- 使用 feature/dev 原始大图（combine_horizontal/）验证海陆比值与老算法一致。
- 使用合成图像验证黑色/灰色像素统计边界（_compute_black_area / _compute_gray_area）。
- 通过覆盖率工具确认 _compute_black_area / _compute_gray_area / _draw_debug_image
  内所有分支均被覆盖。

人工设计的覆盖性测试逻辑：
- 针对公开 API 边界：覆盖 None、非 ndarray、灰度图（2D）等输入异常。
- 针对纯白图：海陆比应为 0%，验证零像素边界不崩溃。
- 针对 debug 图：覆盖 is_debug=True/False，验证 vis_name/vis_image 的返回类型。
- 针对等价性：对三张真实测试图逐图验证 ratio_percent 与老算法计算结果一致。
  注意：debug 图移除了评分标注，与 wise_image_dev1 不再逐像素等价，不做像素级比对。
"""

import pathlib
import unittest

_DATASET_BASE = pathlib.Path(__file__).parent.parent.parent.parent / "datasets" / "test_land_sea_ratio"
_WISE_IMAGE_DEV2 = pathlib.Path(__file__).parent.parent.parent.parent.parent / ".results" / "wise_image_dev2" / "land_sea_ratio"

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False
_COMBINE_HORIZONTAL = _DATASET_BASE / "combine_horizontal"
_WISE_IMAGE_DEV1 = _DATASET_BASE / "wise_image_dev1"


def _make_ratio_image(height: int, width: int, black_ratio: float, gray_ratio: float) -> "np.ndarray":
    """
    构造给定黑色/灰色占比的 BGR 测试图像。
    黑色像素值 = 30，灰色像素值 = 100，白色像素值 = 240。
    """
    total = height * width
    black_count = int(total * black_ratio)
    gray_count = int(total * gray_ratio)

    gray_img = np.full((total,), 240, dtype=np.uint8)
    gray_img[:black_count] = 30
    gray_img[black_count:black_count + gray_count] = 100
    gray_img = gray_img.reshape(height, width)

    return cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)


def _load_image(path: pathlib.Path) -> "np.ndarray":
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise AssertionError(f"无法读取图片: {path}")
    return img


@unittest.skipUnless(_HAS_CV2, "需要 numpy 和 opencv-python")
class TestComputeLandSeaRatioApi(unittest.TestCase):
    """公开 API 边界和输入校验测试。"""

    def _run(self, image, **kwargs):
        from src.core.detection.land_sea_ratio import compute_land_sea_ratio
        return compute_land_sea_ratio(image, **kwargs)

    def test_none_image_raises(self):
        from src.common.exceptions import InputDataError
        with self.assertRaises(InputDataError):
            self._run(None)

    def test_non_ndarray_raises(self):
        from src.common.exceptions import InputDataError
        with self.assertRaises(InputDataError):
            self._run("not_an_image")

    def test_grayscale_2d_image_raises(self):
        from src.common.exceptions import InputDataError
        gray = np.zeros((100, 100), dtype=np.uint8)
        with self.assertRaises(InputDataError):
            self._run(gray)

    def test_return_types_no_debug(self):
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        ratio_percent, vis_name, vis_image = self._run(image)
        expected_vis_name = ""
        self.assertIsInstance(ratio_percent, float)
        self.assertEqual(vis_name, expected_vis_name)
        self.assertIsNone(vis_image)

    def test_return_types_with_debug(self):
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        ratio_percent, vis_name, vis_image = self._run(image, is_debug=True)
        expected_vis_name = "land_sea_ratio"
        expected_shape = image.shape
        self.assertIsInstance(ratio_percent, float)
        self.assertEqual(vis_name, expected_vis_name)
        self.assertIsInstance(vis_image, np.ndarray)
        self.assertEqual(vis_image.shape, expected_shape)

    def test_ratio_range(self):
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        ratio_percent, _, _ = self._run(image)
        expected_ratio_min = 0.0
        expected_ratio_max = 100.0
        self.assertGreaterEqual(ratio_percent, expected_ratio_min)
        self.assertLessEqual(ratio_percent, expected_ratio_max)

    def test_pure_white_image_ratio_zero(self):
        """纯白图：海陆比为 0%。验证零边界不崩溃。"""
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        ratio_percent, _, _ = self._run(image)
        expected_ratio = 0.0
        self.assertAlmostEqual(ratio_percent, expected_ratio, places=2)


@unittest.skipUnless(_HAS_CV2, "需要 numpy 和 opencv-python")
class TestBlackGrayArea(unittest.TestCase):
    """_compute_black_area 和 _compute_gray_area 内部函数白盒测试。"""

    def test_black_area_all_black(self):
        from src.core.detection.land_sea_ratio import _compute_black_area
        gray = np.full((100, 100), 30, dtype=np.uint8)
        area = _compute_black_area(gray)
        expected_area = 10000
        self.assertEqual(area, expected_area)

    def test_black_area_no_black(self):
        from src.core.detection.land_sea_ratio import _compute_black_area
        gray = np.full((100, 100), 200, dtype=np.uint8)
        area = _compute_black_area(gray)
        expected_area = 0
        self.assertEqual(area, expected_area)

    def test_black_area_boundary_50(self):
        from src.core.detection.land_sea_ratio import _compute_black_area
        gray = np.full((100, 100), 50, dtype=np.uint8)
        area = _compute_black_area(gray)
        expected_area = 10000
        self.assertEqual(area, expected_area)

    def test_black_area_boundary_51(self):
        from src.core.detection.land_sea_ratio import _compute_black_area
        gray = np.full((100, 100), 51, dtype=np.uint8)
        area = _compute_black_area(gray)
        expected_area = 0
        self.assertEqual(area, expected_area)

    def test_gray_area_all_gray(self):
        from src.core.detection.land_sea_ratio import _compute_gray_area
        gray = np.full((100, 100), 100, dtype=np.uint8)
        area = _compute_gray_area(gray)
        expected_area = 10000
        self.assertEqual(area, expected_area)

    def test_gray_area_no_gray(self):
        from src.core.detection.land_sea_ratio import _compute_gray_area
        gray = np.full((100, 100), 30, dtype=np.uint8)
        area = _compute_gray_area(gray)
        expected_area = 0
        self.assertEqual(area, expected_area)

    def test_gray_area_boundary_200(self):
        from src.core.detection.land_sea_ratio import _compute_gray_area
        gray = np.full((100, 100), 200, dtype=np.uint8)
        area = _compute_gray_area(gray)
        expected_area = 10000
        self.assertEqual(area, expected_area)

    def test_gray_area_boundary_201(self):
        from src.core.detection.land_sea_ratio import _compute_gray_area
        gray = np.full((100, 100), 201, dtype=np.uint8)
        area = _compute_gray_area(gray)
        expected_area = 0
        self.assertEqual(area, expected_area)


@unittest.skipUnless(_HAS_CV2, "需要 numpy 和 opencv-python")
class TestRuntimeErrors(unittest.TestCase):
    """RuntimeProcessError 抛出路径测试（mock 注入异常）。"""

    def test_computation_failure_wraps_as_runtime_error(self):
        """当内部 cv2.cvtColor 抛出时，应包装为 RuntimeProcessError。"""
        from src.common.exceptions import RuntimeProcessError
        from unittest.mock import patch
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        with patch("src.core.detection.land_sea_ratio.cv2.cvtColor", side_effect=RuntimeError("mock")):
            from src.core.detection.land_sea_ratio import compute_land_sea_ratio
            with self.assertRaises(RuntimeProcessError):
                compute_land_sea_ratio(image)

    def test_debug_draw_failure_wraps_as_runtime_error(self):
        """当 _draw_debug_image 抛出时，应包装为 RuntimeProcessError。"""
        from src.common.exceptions import RuntimeProcessError
        from unittest.mock import patch
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        with patch("src.core.detection.land_sea_ratio._draw_debug_image", side_effect=RuntimeError("mock")):
            from src.core.detection.land_sea_ratio import compute_land_sea_ratio
            with self.assertRaises(RuntimeProcessError):
                compute_land_sea_ratio(image, is_debug=True)


@unittest.skipUnless(_HAS_CV2, "需要 numpy 和 opencv-python")
class TestDebugVisualization(unittest.TestCase):
    """debug 可视化输出测试。"""

    def _run(self, image, **kwargs):
        from src.core.detection.land_sea_ratio import compute_land_sea_ratio
        return compute_land_sea_ratio(image, **kwargs)

    def test_no_debug_returns_none_and_empty_string(self):
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        _, vis_name, vis_image = self._run(image, is_debug=False)
        expected_vis_name = ""
        self.assertEqual(vis_name, expected_vis_name)
        self.assertIsNone(vis_image)

    def test_debug_returns_correct_name(self):
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        _, vis_name, _ = self._run(image, is_debug=True)
        expected_vis_name = "land_sea_ratio"
        self.assertEqual(vis_name, expected_vis_name)

    def test_debug_image_same_shape_as_input(self):
        image = _make_ratio_image(200, 300, 0.3, 0.1)
        _, _, vis_image = self._run(image, is_debug=True)
        expected_shape = image.shape
        self.assertEqual(vis_image.shape, expected_shape)

    def test_debug_image_dtype_uint8(self):
        image = _make_ratio_image(100, 100, 0.3, 0.0)
        _, _, vis_image = self._run(image, is_debug=True)
        expected_dtype = np.uint8
        self.assertEqual(vis_image.dtype, expected_dtype)


@unittest.skipUnless(_HAS_CV2, "需要 numpy 和 opencv-python")
class TestRealImages(unittest.TestCase):
    """
    使用真实测试图像验证海陆比值与老算法等价，并做 debug 图像素级比对。

    只验证 ratio_percent，不验证 score（评分逻辑已移至规则层）。
    wise_image_dev1 存放的是不带评分标注的新基准图（已人工确认），
    新架构运行时生成的 debug 图与之做逐像素比对，保证可视化不被误改。
    测试自动生成图保存到 .results/wise_image_dev2/land_sea_ratio/ 供人工检查。

    预期结果（由老算法计算，在准备数据集脚本中已确认）：
    - sym_0_r1_0_r2_0_r3_0_r4_0_r5_0.png: ratio=24.72%
    - sym_1_r1_0_r2_0_r3_1_r4_0_r5_0.png: ratio=24.36%
    - sym_3_r1_0_r2_0_r3_0_r4_0_r5_0.png: ratio=25.25%
    """

    EXPECTED_RATIO = {
        "sym_0_r1_0_r2_0_r3_0_r4_0_r5_0.png": 24.72,
        "sym_1_r1_0_r2_0_r3_1_r4_0_r5_0.png": 24.36,
        "sym_3_r1_0_r2_0_r3_0_r4_0_r5_0.png": 25.25,
    }

    def _run(self, image, **kwargs):
        from src.core.detection.land_sea_ratio import compute_land_sea_ratio
        return compute_land_sea_ratio(image, **kwargs)

    def test_real_image_ratios_match_old_algorithm(self):
        """逐图验证新架构海陆比值与老算法计算结果一致。"""
        for filename, expected_ratio in self.EXPECTED_RATIO.items():
            image_path = _COMBINE_HORIZONTAL / filename
            if not image_path.exists():
                self.skipTest(f"测试图像不存在: {image_path}")
            image = _load_image(image_path)
            ratio_percent, _, _ = self._run(image)
            with self.subTest(filename=filename):
                self.assertAlmostEqual(
                    ratio_percent, expected_ratio, places=2,
                    msg=f"{filename}: 海陆比不匹配，期望 {expected_ratio}，实际 {ratio_percent}",
                )

    def test_debug_image_pixel_equal_to_dev1_baseline(self):
        """
        新架构 debug 图与 wise_image_dev1 基准图逐像素比对，防止可视化被误改。
        同时将新架构 debug 图保存到 .results/wise_image_dev2/land_sea_ratio/ 供人工检查。
        """
        _WISE_IMAGE_DEV2.mkdir(parents=True, exist_ok=True)

        for filename in self.EXPECTED_RATIO:
            image_path = _COMBINE_HORIZONTAL / filename
            dev1_path = _WISE_IMAGE_DEV1 / filename
            if not image_path.exists() or not dev1_path.exists():
                self.skipTest(f"测试数据不完整: {image_path} 或 {dev1_path}")

            image = _load_image(image_path)
            dev1_image = _load_image(dev1_path)

            _, _, vis_image = self._run(image, is_debug=True)

            dev2_path = _WISE_IMAGE_DEV2 / filename
            success, buf = cv2.imencode(".png", vis_image)
            if success:
                np.array(buf).tofile(str(dev2_path))

            with self.subTest(filename=filename):
                self.assertTrue(
                    np.array_equal(vis_image, dev1_image),
                    msg=(
                        f"{filename}: debug 图与基准不一致，"
                        f"请对比 {dev1_path} 和 {dev2_path}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
