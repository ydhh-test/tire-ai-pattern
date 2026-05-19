"""
核心图像操作算法单元测试 - 真实图片版本

使用真实的测试图片和预期结果进行验证
"""

import unittest
import numpy as np
import cv2
from pathlib import Path
from src.core.operation.image_operation import (
    apply_single_rib_operation,
    apply_rib_operations_sequence
)
from src.models.enums import RibOperation


class TestImageOperationReal(unittest.TestCase):
    """核心图像操作算法真实图片测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化 - 加载真实测试图片"""
        cls.test_dataset_dir = Path("tests/datasets/stitching")
        cls.original_image = cv2.imread(str(cls.test_dataset_dir / "rib5.png"))

        if cls.original_image is None:
            raise FileNotFoundError(f"无法加载测试图片: {cls.test_dataset_dir / 'rib5.png'}")

        # 验证原始图片尺寸
        assert cls.original_image.shape == (129, 259, 3), f"预期尺寸 (129, 259, 3)，实际 {cls.original_image.shape}"

    def _load_expected_result(self, filename: str) -> np.ndarray:
        """加载预期结果图片"""
        expected_path = self.test_dataset_dir / filename
        expected_image = cv2.imread(str(expected_path))
        if expected_image is None:
            raise FileNotFoundError(f"无法加载预期结果: {expected_path}")
        return expected_image

    def test_apply_single_rib_operation_none_real(self):
        """测试NONE操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.NONE)
        expected = self._load_expected_result("rib5_none.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_flip_lr_real(self):
        """测试FLIP_LR操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.FLIP_LR)
        expected = self._load_expected_result("rib5_fliplr.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_flip_real(self):
        """测试FLIP操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.FLIP)
        expected = self._load_expected_result("rib5_flip.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_resize_horizontal_2x_real(self):
        """测试RESIZE_HORIZONTAL_2X操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.RESIZE_HORIZONTAL_2X)
        expected = self._load_expected_result("rib5_resize_horizontal_2x.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_left_real(self):
        """测试LEFT操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.LEFT)
        expected = self._load_expected_result("rib5_left.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_right_real(self):
        """测试RIGHT操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.RIGHT)
        expected = self._load_expected_result("rib5_right.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_resize_horizontal_1_5x_real(self):
        """测试RESIZE_HORIZONTAL_1_5X操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.RESIZE_HORIZONTAL_1_5X)
        expected = self._load_expected_result("rib5_resize_horizontal_1.5x.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_resize_horizontal_3x_real(self):
        """测试RESIZE_HORIZONTAL_3X操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.RESIZE_HORIZONTAL_3X)
        expected = self._load_expected_result("rib5_resize_horizontal_3x.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_left_2_3_real(self):
        """测试LEFT_2_3操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.LEFT_2_3)
        expected = self._load_expected_result("rib5_left_2_3.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_right_2_3_real(self):
        """测试RIGHT_2_3操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.RIGHT_2_3)
        expected = self._load_expected_result("rib5_right_2_3.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_left_1_3_real(self):
        """测试LEFT_1_3操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.LEFT_1_3)
        expected = self._load_expected_result("rib5_left_1_3.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_single_rib_operation_right_1_3_real(self):
        """测试RIGHT_1_3操作 - 真实图片"""
        result = apply_single_rib_operation(self.original_image, RibOperation.RIGHT_1_3)
        expected = self._load_expected_result("rib5_right_1_3.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_rib_operations_sequence_resize_horizontal_2x_left_real(self):
        """测试resize_horizontal_2x + left操作序列 - 真实图片"""
        operations = (RibOperation.RESIZE_HORIZONTAL_2X, RibOperation.LEFT)
        result = apply_rib_operations_sequence(self.original_image, operations)
        expected = self._load_expected_result("rib5_resize_horizontal_2x_left.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_rib_operations_sequence_resize_horizontal_2x_right_real(self):
        """测试resize_horizontal_2x + right操作序列 - 真实图片"""
        operations = (RibOperation.RESIZE_HORIZONTAL_2X, RibOperation.RIGHT)
        result = apply_rib_operations_sequence(self.original_image, operations)
        expected = self._load_expected_result("rib5_resize_horizontal_2x_right.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_rib_operations_sequence_fliplr_left_real(self):
        """测试fliplr + left操作序列 - 真实图片"""
        operations = (RibOperation.FLIP_LR, RibOperation.LEFT)
        result = apply_rib_operations_sequence(self.original_image, operations)
        expected = self._load_expected_result("rib5_fliplr_left.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_rib_operations_sequence_flip_right_real(self):
        """测试flip + right操作序列 - 真实图片"""
        operations = (RibOperation.FLIP, RibOperation.RIGHT)
        result = apply_rib_operations_sequence(self.original_image, operations)
        expected = self._load_expected_result("rib5_flip_right.png")
        np.testing.assert_array_equal(result, expected)

    def test_apply_rib_operations_sequence_resize_horizontal_1_5x_left_1_3_real(self):
        """测试resize_horizontal_1.5x + left_1_3操作序列 - 真实图片"""
        operations = (RibOperation.RESIZE_HORIZONTAL_1_5X, RibOperation.LEFT_1_3)
        result = apply_rib_operations_sequence(self.original_image, operations)
        expected = self._load_expected_result("rib5_resize_horizontal_1.5x_left_1_3.png")
        np.testing.assert_array_equal(result, expected)


if __name__ == '__main__':
    unittest.main()