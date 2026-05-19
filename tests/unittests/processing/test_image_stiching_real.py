"""
大图生成函数单元测试 - 真实图片版本

使用真实的测试图片进行端到端验证
"""

import unittest
import numpy as np
import cv2
import base64
from pathlib import Path
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


class TestImageStichingReal(unittest.TestCase):
    """大图生成函数真实图片测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化 - 加载真实测试图片"""
        cls.test_dataset_dir = Path("tests/datasets/stitching")

        # 加载rib5.png作为主要测试图片
        cls.rib5_image = cv2.imread(str(cls.test_dataset_dir / "rib5.png"))
        if cls.rib5_image is None:
            raise FileNotFoundError(f"无法加载测试图片: {cls.test_dataset_dir / 'rib5.png'}")

        # 加载except.png作为主沟图片
        cls.except_image = cv2.imread(str(cls.test_dataset_dir / "except.png"))
        if cls.except_image is None:
            raise FileNotFoundError(f"无法加载主沟图片: {cls.test_dataset_dir / 'except.png'}")

    def _ndarray_to_base64(self, image: np.ndarray) -> str:
        """将numpy数组转换为base64字符串"""
        success, buffer = cv2.imencode('.png', image)
        if not success:
            raise ValueError("Failed to encode image")
        base64_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/png;base64,{base64_str}"

    def test_generate_large_image_from_lineage_basic_real(self):
        """测试基本的大图生成功能 - 真实图片（单RIB，无主沟）"""
        rib5_base64 = self._ndarray_to_base64(self.rib5_image)
        expected_prefix = "data:image/"

        rib1 = RibSchemeImpl(
            rib_source="side",
            rib_operation=(RibOperation.NONE,),
            rib_name="rib1",
            before_image=rib5_base64,
            num_pitchs=1,
            rib_height=self.rib5_image.shape[0],
            rib_width=self.rib5_image.shape[1],
        )

        stitching_scheme = StitchingScheme(
            stitching_scheme_abstract=StitchingSchemeAbstract(
                name=StitchingSchemeName.SYMMETRY_0,
                description="test with real images",
                rib_number=1,
            ),
            ribs_scheme_implementation=[rib1],
        )

        # 创建空的主沟和装饰方案（单RIB不需要主沟）
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

        # 执行测试
        result_lineage, result_base64 = generate_large_image_from_lineage(lineage)

        # 验证结果
        self.assertIsNotNone(result_lineage)
        self.assertIsNotNone(result_base64)
        self.assertEqual(result_base64[:len(expected_prefix)], expected_prefix)

    def test_rib_operations_with_real_images(self):
        """测试RIB操作序列处理 - 真实图片"""
        rib5_base64 = self._ndarray_to_base64(self.rib5_image)
        expected_prefix = "data:image/"

        # 测试 resize + left 组合操作
        rib_with_operations = RibSchemeImpl(
            rib_source="side",
            rib_operation=(RibOperation.RESIZE_HORIZONTAL_2X, RibOperation.LEFT),
            rib_name="rib_with_ops",
            before_image=rib5_base64,
            num_pitchs=1,
            rib_height=self.rib5_image.shape[0],
            rib_width=self.rib5_image.shape[1],
        )

        stitching_scheme = StitchingScheme(
            stitching_scheme_abstract=StitchingSchemeAbstract(
                name=StitchingSchemeName.SYMMETRY_0,
                description="test operations with real images",
                rib_number=1,
            ),
            ribs_scheme_implementation=[rib_with_operations],
        )

        # 创建空的主沟和装饰方案（单RIB不需要主沟）
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

        # 执行测试
        result_lineage, result_base64 = generate_large_image_from_lineage(lineage)

        # 验证结果
        self.assertIsNotNone(result_lineage)
        self.assertIsNotNone(result_base64)
        self.assertEqual(result_base64[:len(expected_prefix)], expected_prefix)


if __name__ == '__main__':
    unittest.main()
