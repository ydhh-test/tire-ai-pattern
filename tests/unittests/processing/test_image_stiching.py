"""
大图生成函数单元测试
"""

import unittest
import numpy as np
import cv2
import base64
from unittest.mock import patch, MagicMock
from src.models.image_models import ImageLineage
from src.models.scheme_models import (
    StitchingScheme, StitchingSchemeAbstract,
    RibSchemeImpl, MainGrooveImpl, DecorationImpl,
    MainGrooveScheme, MainGrooveSchemeAbstract,
    DecorationScheme, DecorationSchemeAbstract
)
from src.models.enums import (
    RibOperation, StitchingSchemeName
)
from src.processing.image_stiching import generate_large_image_from_lineage


class TestImageStiching(unittest.TestCase):
    """大图生成函数测试"""

    def setUp(self):
        """测试前准备"""
        self.image_h = 100
        self.image_w = 100
        self.test_image = np.ones((self.image_h, self.image_w, 3), dtype=np.uint8) * 128
        self.test_base64 = self._ndarray_to_base64(self.test_image)

    def _ndarray_to_base64(self, image: np.ndarray) -> str:
        """将numpy数组转换为base64字符串（用于测试）"""
        success, buffer = cv2.imencode('.png', image)
        if not success:
            raise ValueError("Failed to encode image")
        base64_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/png;base64,{base64_str}"

    def test_generate_large_image_from_lineage_basic(self):
        """测试基本的大图生成功能"""
        # 创建测试数据
        rib1 = RibSchemeImpl(
            rib_source="side",
            rib_operation=(RibOperation.NONE,),
            rib_name="rib1",
            before_image=self.test_base64,
            num_pitchs=1,
            rib_height=self.image_h,
            rib_width=self.image_w,
        )

        rib2 = RibSchemeImpl(
            rib_source="center",
            rib_operation=(RibOperation.NONE,),
            rib_name="rib2",
            before_image=self.test_base64,
            num_pitchs=1,
            rib_height=self.image_h,
            rib_width=self.image_w,
        )

        stitching_scheme = StitchingScheme(
            stitching_scheme_abstract=StitchingSchemeAbstract(
                name=StitchingSchemeName.SYMMETRY_0,
                description="test",
                rib_number=2,
            ),
            ribs_scheme_implementation=[rib1, rib2],
        )

        # 创建包含一个主沟的方案（2个RIB需要1个主沟）
        main_groove_impl = MainGrooveImpl(
            before_image=self.test_base64,
            groove_width=50,
            groove_height=self.image_h,
        )
        test_main_groove = MainGrooveScheme(
            main_groove_scheme_abstract=MainGrooveSchemeAbstract(
                name="test",
                groove_number=1,
            ),
            main_groove_implementation=[main_groove_impl],
        )
        empty_decoration = DecorationScheme(
            decoration_scheme_abstract=DecorationSchemeAbstract(name="empty"),
            decoration_implementation=[],
        )

        lineage = ImageLineage(
            stitching_scheme=stitching_scheme,
            main_groove_scheme=test_main_groove,
            decoration_scheme=empty_decoration,
        )

        # 执行测试
        result_lineage, result_base64 = generate_large_image_from_lineage(lineage)

        # 验证结果
        expected_prefix = "data:image/"
        self.assertIsNotNone(result_lineage)
        self.assertIsNotNone(result_base64)
        self.assertEqual(result_base64[:len(expected_prefix)], expected_prefix)

    def test_rib_operations_sequence(self):
        """测试RIB操作序列处理"""
        from src.core.operation.image_operation import apply_rib_operations_sequence

        # 测试 resize + left 组合
        operations = (RibOperation.RESIZE_HORIZONTAL_2X, RibOperation.LEFT)
        result = apply_rib_operations_sequence(self.test_image, operations)

        expected_height = self.image_h
        expected_width = self.image_w
        self.assertIsNotNone(result)
        self.assertEqual(result.shape[0], expected_height)
        self.assertEqual(result.shape[1], expected_width)

    def test_single_rib_operations(self):
        """测试单个RIB操作"""
        from src.core.operation.image_operation import apply_single_rib_operation

        expected_shape = self.test_image.shape

        # 测试FLIP_LR
        flipped = apply_single_rib_operation(self.test_image, RibOperation.FLIP_LR)
        self.assertIsNotNone(flipped)
        self.assertEqual(flipped.shape, expected_shape)

        # 测试FLIP
        rotated = apply_single_rib_operation(self.test_image, RibOperation.FLIP)
        self.assertIsNotNone(rotated)
        self.assertEqual(rotated.shape, expected_shape)

    def test_horizontal_concatenate(self):
        """测试横向拼接"""
        from src.core.operation.image_operation import horizontal_concatenate

        images = [self.test_image, self.test_image]
        result = horizontal_concatenate(images)

        expected_height = self.image_h
        expected_width = self.image_w * 2
        self.assertIsNotNone(result)
        self.assertEqual(result.shape[0], expected_height)
        self.assertEqual(result.shape[1], expected_width)

    def test_overlay_decoration(self):
        """测试装饰覆盖"""
        from src.core.operation.image_operation import overlay_decoration

        left_dec = np.ones((self.image_h, 50, 3), dtype=np.uint8) * 200
        right_dec = np.ones((self.image_h, 50, 3), dtype=np.uint8) * 50

        result = overlay_decoration(self.test_image, left_dec, right_dec)

        expected_height = self.image_h
        expected_width = self.image_w
        self.assertIsNotNone(result)
        self.assertEqual(result.shape[0], expected_height)
        self.assertEqual(result.shape[1], expected_width)

    def test_input_validation(self):
        """测试输入验证"""
        with self.assertRaises(ValueError):
            generate_large_image_from_lineage(None)

    def test_empty_rib_list(self):
        """测试空RIB列表"""
        stitching_scheme = StitchingScheme(
            stitching_scheme_abstract=StitchingSchemeAbstract(
                name=StitchingSchemeName.SYMMETRY_0,
                description="test",
                rib_number=0,
            ),
            ribs_scheme_implementation=[],
        )

        # 创建空的主沟和装饰方案
        empty_main_groove = MainGrooveScheme(
            main_groove_scheme_abstract=MainGrooveSchemeAbstract(
                name="empty",
                groove_number=0,
            ),
            main_groove_implementation=[],
        )
        empty_decoration = DecorationScheme(
            decoration_scheme_abstract=DecorationSchemeAbstract(name="empty"),
            decoration_implementation=[],
        )

        lineage = ImageLineage(
            stitching_scheme=stitching_scheme,
            main_groove_scheme=empty_main_groove,
            decoration_scheme=empty_decoration,
        )

        with self.assertRaises(ValueError):
            generate_large_image_from_lineage(lineage)


if __name__ == '__main__':
    unittest.main()
