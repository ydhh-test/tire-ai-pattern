"""
大图拼接集成测试

使用真实图片验证完整的端到端流程：
5个RIB + 4个主沟 + 黑色半透明装饰覆盖
"""

import base64
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.models.enums import (
    RibOperation,
    StitchingSchemeName,
)
from src.models.image_models import ImageLineage
from src.models.scheme_models import (
    DecorationImpl,
    DecorationScheme,
    DecorationSchemeAbstract,
    MainGrooveImpl,
    MainGrooveScheme,
    MainGrooveSchemeAbstract,
    RibSchemeImpl,
    StitchingScheme,
    StitchingSchemeAbstract,
)
from src.processing.image_stiching import generate_large_image_from_lineage


DATASET_DIR = Path("tests/datasets/stitching")
EXPECTED_PATH = DATASET_DIR / "correct_black_decoration.png"


def _ndarray_to_base64(image: np.ndarray) -> str:
    success, buffer = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Failed to encode image")
    base64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/png;base64,{base64_str}"


def _resize_image(image: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    return cv2.resize(image, (target_width, target_height))


def _build_lineage_with_black_decoration() -> ImageLineage:
    """
    构建与 correct_black_decoration.png 相同配置的 ImageLineage。

    配置：
    - rib1、rib5: 400×640, 区域 SIDE
    - rib2、rib3、rib4: 200×640, 区域 CENTER
    - num_pitchs = 5
    - 主沟: 4 个, 20×640, 黑色
    - 装饰: 300×640, 纯黑色, 50% 透明度
    """
    target_rib_configs = {
        1: {"width": 400, "height": 640, "source": "side"},
        2: {"width": 200, "height": 640, "source": "center"},
        3: {"width": 200, "height": 640, "source": "center"},
        4: {"width": 200, "height": 640, "source": "center"},
        5: {"width": 400, "height": 640, "source": "side"},
    }

    ribs_scheme_implementation = []
    for i in range(1, 6):
        config = target_rib_configs[i]
        rib_path = DATASET_DIR / f"rib{i}.png"
        rib_img = cv2.imread(str(rib_path))
        assert rib_img is not None, f"无法加载 {rib_path}"
        resized = _resize_image(rib_img, config["width"], config["height"])

        rib_impl = RibSchemeImpl(
            rib_source=config["source"],
            rib_operation=(RibOperation.NONE,),
            rib_name=f"rib{i}",
            before_image=_ndarray_to_base64(resized),
            num_pitchs=5,
            rib_height=config["height"],
            rib_width=config["width"],
        )
        ribs_scheme_implementation.append(rib_impl)

    stitching_scheme = StitchingScheme(
        stitching_scheme_abstract=StitchingSchemeAbstract(
            name=StitchingSchemeName.SYMMETRY_0,
            description="integration test",
            rib_number=5,
        ),
        ribs_scheme_implementation=ribs_scheme_implementation,
    )

    # 4 个主沟, 20×640, 黑色
    groove_img = np.zeros((640, 20, 3), dtype=np.uint8)
    groove_base64 = _ndarray_to_base64(groove_img)
    main_groove_impls = [
        MainGrooveImpl(before_image=groove_base64, groove_width=20, groove_height=640)
        for _ in range(4)
    ]
    main_groove_scheme = MainGrooveScheme(
        main_groove_scheme_abstract=MainGrooveSchemeAbstract(name="test", groove_number=4),
        main_groove_implementation=main_groove_impls,
    )

    # 装饰: 300×640, 纯黑色, 50% 透明度
    decoration_img = np.zeros((640, 300, 3), dtype=np.uint8)
    decoration_base64 = _ndarray_to_base64(decoration_img)
    decoration_impl = DecorationImpl(
        before_image=decoration_base64,
        decoration_width=300,
        decoration_height=640,
        decoration_opacity=128,
    )
    decoration_scheme = DecorationScheme(
        decoration_scheme_abstract=DecorationSchemeAbstract(name="test"),
        decoration_implementation=[decoration_impl],
    )

    return ImageLineage(
        stitching_scheme=stitching_scheme,
        main_groove_scheme=main_groove_scheme,
        decoration_scheme=decoration_scheme,
    )


class TestLargeImageStitchingIntegration:
    """大图拼接端到端集成测试"""

    @pytest.fixture(scope="class")
    def expected_image(self) -> np.ndarray:
        expected = cv2.imread(str(EXPECTED_PATH))
        if expected is None:
            pytest.fail(f"预期结果文件不存在: {EXPECTED_PATH}")
        return expected

    expected_prefix = "data:image/"

    def test_generates_same_result_as_expected(self, expected_image):
        """验证生成的完整大图与预期结果完全一致"""
        lineage = _build_lineage_with_black_decoration()
        result_lineage, result_base64 = generate_large_image_from_lineage(lineage)

        assert result_base64[:len(self.expected_prefix)] == self.expected_prefix, (
            "输出应为 data:image 前缀的 base64"
        )

        # 解码结果图像
        b64data = result_base64.split(",")[1]
        img_array = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
        actual = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        assert actual is not None, "解码生成的大图失败"
        assert actual.shape == expected_image.shape, (
            f"尺寸不匹配: 实际 {actual.shape}, 预期 {expected_image.shape}"
        )

        np.testing.assert_array_equal(actual, expected_image)

    def test_output_size_matches_ribs_and_grooves(self):
        """验证输出尺寸 = RIB总宽 + 主沟总宽（装饰不扩展尺寸）"""
        lineage = _build_lineage_with_black_decoration()
        _, result_base64 = generate_large_image_from_lineage(lineage)

        b64data = result_base64.split(",")[1]
        img_array = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
        actual = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        expected_width = 400 + 200 + 200 + 200 + 400 + 20 * 4  # 1480
        expected_height = 640
        assert actual.shape == (expected_height, expected_width, 3)

    def test_decoration_makes_white_background_darker(self):
        """验证黑色半透明装饰使白色背景区域变暗"""
        lineage = _build_lineage_with_black_decoration()
        _, result_base64 = generate_large_image_from_lineage(lineage)

        b64data = result_base64.split(",")[1]
        img_array = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
        actual = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # 原始 RIB 背景约为 214, 黑色装饰 0 + 50% → 约 107
        left_region = actual[:, :300]
        left_mean = float(np.mean(left_region))
        expected_min_brightness = 50
        expected_max_brightness = 160
        assert left_mean > expected_min_brightness, "左侧不应全黑"
        assert left_mean < expected_max_brightness, f"左侧应因黑色装饰变暗，实际均值 {left_mean}"

    def test_after_image_fields_are_filled(self):
        """验证处理完成后 after_image 被正确填充，且像素值与预期一致"""
        lineage = _build_lineage_with_black_decoration()
        result_lineage, result_base64 = generate_large_image_from_lineage(lineage)

        # 验证输出图片
        assert result_base64[:len(self.expected_prefix)] == self.expected_prefix, "输出应为 base64 图片"

        # --- 验证 RIB after_image ---
        ribs = result_lineage.stitching_scheme.ribs_scheme_implementation
        for rib in ribs:
            assert rib.after_image is not None, f"{rib.rib_name} 的 after_image 为空"
            assert rib.after_image[:len(self.expected_prefix)] == self.expected_prefix, (
                f"{rib.rib_name} 的 after_image 格式不正确"
            )

            # 解码并与预期图片逐像素对比
            b64data = rib.after_image.split(",")[1]
            arr = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
            actual = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
            expected = cv2.imread(str(DATASET_DIR / f"{rib.rib_name}_after.png"), cv2.IMREAD_UNCHANGED)
            assert expected is not None, f"预期图片 {rib.rib_name}_after.png 不存在"
            np.testing.assert_array_equal(actual, expected, f"{rib.rib_name} after_image 像素不一致")

        # --- 验证主沟 after_image ---
        grooves = result_lineage.main_groove_scheme.main_groove_implementation
        for i, groove in enumerate(grooves):
            assert groove.after_image is not None, f"主沟 {i} 的 after_image 为空"
            assert groove.after_image[:len(self.expected_prefix)] == self.expected_prefix, (
                f"主沟 {i} 的 after_image 格式不正确"
            )

            b64data = groove.after_image.split(",")[1]
            arr = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
            actual = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
            expected = cv2.imread(str(DATASET_DIR / f"main_groove_after_{i}.png"), cv2.IMREAD_UNCHANGED)
            assert expected is not None, f"预期图片 main_groove_after_{i}.png 不存在"
            np.testing.assert_array_equal(actual, expected, f"主沟 {i} after_image 像素不一致")

        # --- 验证装饰 after_image ---
        decorations = result_lineage.decoration_scheme.decoration_implementation
        for i, dec in enumerate(decorations):
            assert dec.after_image is not None, f"装饰 {i} 的 after_image 为空"
            assert dec.after_image[:len(self.expected_prefix)] == self.expected_prefix, (
                f"装饰 {i} 的 after_image 格式不正确"
            )

            b64data = dec.after_image.split(",")[1]
            arr = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
            actual = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
            expected = cv2.imread(str(DATASET_DIR / f"decoration_after_{i}.png"), cv2.IMREAD_UNCHANGED)
            assert expected is not None, f"预期图片 decoration_after_{i}.png 不存在"
            np.testing.assert_array_equal(actual, expected, f"装饰 {i} after_image 像素不一致")

    def test_skip_when_after_image_exists(self, expected_image):
        """验证 after_image 已存在时跳过处理，不合法 before_image 不会导致错误"""
        lineage = _build_lineage_with_black_decoration()

        # 从磁盘加载预期的 after_image，预填充到 lineage 中
        ribs = lineage.stitching_scheme.ribs_scheme_implementation
        for rib in ribs:
            expected_path = DATASET_DIR / f"{rib.rib_name}_after.png"
            expected_img = cv2.imread(str(expected_path), cv2.IMREAD_UNCHANGED)
            assert expected_img is not None, f"预期图片 {expected_path} 不存在"
            rib.after_image = _ndarray_to_base64(expected_img)
            rib.before_image = "SKIPPED_GARBAGE"

        grooves = lineage.main_groove_scheme.main_groove_implementation
        for i, groove in enumerate(grooves):
            expected_path = DATASET_DIR / f"main_groove_after_{i}.png"
            expected_img = cv2.imread(str(expected_path), cv2.IMREAD_UNCHANGED)
            assert expected_img is not None, f"预期图片 {expected_path} 不存在"
            groove.after_image = _ndarray_to_base64(expected_img)
            groove.before_image = "SKIPPED_GARBAGE"

        decs = lineage.decoration_scheme.decoration_implementation
        for i, dec in enumerate(decs):
            expected_path = DATASET_DIR / f"decoration_after_{i}.png"
            expected_img = cv2.imread(str(expected_path), cv2.IMREAD_UNCHANGED)
            assert expected_img is not None, f"预期图片 {expected_path} 不存在"
            dec.after_image = _ndarray_to_base64(expected_img)
            dec.before_image = "SKIPPED_GARBAGE"

        # 不应抛出异常（skip 逻辑跳过了解码 before_image）
        result_lineage, result_base64 = generate_large_image_from_lineage(lineage)

        # 输出应与预期完全一致
        b64data = result_base64.split(",")[1]
        img_array = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
        actual = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        assert actual is not None, "解码生成的大图失败"
        assert actual.shape == expected_image.shape, (
            f"尺寸不匹配: 实际 {actual.shape}, 预期 {expected_image.shape}"
        )
        np.testing.assert_array_equal(actual, expected_image)
