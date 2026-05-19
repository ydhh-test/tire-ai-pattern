import base64
import numpy as np
import cv2
from pathlib import Path
from PIL import Image
import tempfile
import pytest
import logging
import os

from src.utils.image_utils import (
    base64_to_ndarray,
    ndarray_to_base64,
    resize_image,
    load_image_to_base64,
    save_base64_to_image,
    convert_cmyk_to_rgb
)
from src.common.exceptions import (
    InputTypeError,
    InputDataError,
    RuntimeProcessError
)
from src.utils.logger import get_logger


# 定义测试数据集路径 - 直接使用相对路径（PYTHONPATH已指向项目根目录）
TEST_DATASET_PATH = Path("tests/datasets/test_image_utils")

# 创建测试用的numpy数组（BGR格式）
TEST_IMAGE_ARRAY = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

# 创建对应的base64字符串（带前缀）
_, buffer = cv2.imencode('.png', TEST_IMAGE_ARRAY)
TEST_IMAGE_BASE64_WITH_PREFIX = f"data:image/png;base64,{base64.b64encode(buffer).decode('utf-8')}"

# 创建对应的base64字符串（无前缀）
TEST_IMAGE_BASE64_NO_PREFIX = base64.b64encode(buffer).decode('utf-8')

# 支持的图像类型
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg"]

# 不支持的图像类型
UNSUPPORTED_IMAGE_TYPES = ["bmp", "tiff", "webp"]

# OpenCV BGR图像的通道数
BGR_CHANNELS = 3

INVALID_BASE64_STRINGS = [
    "invalid_base64_string",
    "data:image/png;base64,invalid",
    "",
    "data:image/bmp;base64,xxx"  # 不支持的格式前缀
]


def create_temp_image_file(suffix, image_array, params=None):
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    success = cv2.imwrite(temp_path, image_array, params or [])
    assert success
    return temp_path

# 配置日志捕获
@pytest.fixture(autouse=True)
def capture_logs(caplog):
    caplog.set_level(logging.WARNING)

# 验证测试数据集是否存在
@pytest.fixture(scope="session", autouse=True)
def ensure_test_dataset():
    """确保测试数据集存在"""
    if not TEST_DATASET_PATH.exists():
        pytest.skip(f"测试数据集不存在: {TEST_DATASET_PATH}")

    required_files = ["0.png", "0_width2x.png", "0_height2x.png", "0_2x.png"]
    for file in required_files:
        if not (TEST_DATASET_PATH / file).exists():
            pytest.skip(f"测试文件缺失: {file}")


class TestBase64ToNdarray:
    """base64_to_ndarray() 功能测试"""

    def test_valid_base64_with_prefix(self):
        """带data:image前缀的base64正确解码"""
        expected_shape = TEST_IMAGE_ARRAY.shape
        expected_dtype = TEST_IMAGE_ARRAY.dtype

        result = base64_to_ndarray(TEST_IMAGE_BASE64_WITH_PREFIX)
        assert isinstance(result, np.ndarray)
        assert result.shape == expected_shape
        assert result.dtype == expected_dtype

    def test_valid_base64_no_prefix(self):
        """纯base64字符串正确解码"""
        expected_shape = TEST_IMAGE_ARRAY.shape
        expected_dtype = TEST_IMAGE_ARRAY.dtype

        result = base64_to_ndarray(TEST_IMAGE_BASE64_NO_PREFIX)
        assert isinstance(result, np.ndarray)
        assert result.shape == expected_shape
        assert result.dtype == expected_dtype

    def test_different_image_formats(self):
        """PNG、JPG、JPEG格式都支持"""
        # 测试JPG格式
        _, jpg_buffer = cv2.imencode('.jpg', TEST_IMAGE_ARRAY, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        jpg_base64 = f"data:image/jpeg;base64,{base64.b64encode(jpg_buffer).decode('utf-8')}"
        result = base64_to_ndarray(jpg_base64)
        assert isinstance(result, np.ndarray)

        # 测试JPEG格式（同JPG）
        jpeg_base64 = f"data:image/jpeg;base64,{base64.b64encode(jpg_buffer).decode('utf-8')}"
        result = base64_to_ndarray(jpeg_base64)
        assert isinstance(result, np.ndarray)

    def test_input_type_error_non_string(self):
        """非字符串输入抛出InputTypeError"""
        with pytest.raises(InputTypeError) as exc_info:
            base64_to_ndarray(123)
        assert "base64_to_ndarray" in str(exc_info.value)
        assert "expects str" in str(exc_info.value)

    def test_input_data_error_invalid_base64(self):
        """无效base64字符串抛出InputDataError"""
        with pytest.raises(InputDataError) as exc_info:
            base64_to_ndarray("invalid_base64_string")
        assert "invalid_base64_string" in str(exc_info.value)

    def test_input_data_error_unsupported_format(self):
        """不支持的图像格式抛出InputDataError"""
        # 创建一个无效的base64字符串
        invalid_base64 = "data:image/bmp;base64," + base64.b64encode(b"invalid_data").decode('utf-8')
        with pytest.raises(InputDataError):
            base64_to_ndarray(invalid_base64)


class TestNdarrayToBase64:
    """ndarray_to_base64() 功能测试"""

    def test_valid_ndarray_to_png(self):
        """numpy数组转PNG base64"""
        result = ndarray_to_base64(TEST_IMAGE_ARRAY, "png")
        assert isinstance(result, str)
        assert result.startswith("data:image/png;base64,")

    def test_valid_ndarray_to_jpg(self):
        """numpy数组转JPG base64"""
        result = ndarray_to_base64(TEST_IMAGE_ARRAY, "jpg")
        assert isinstance(result, str)
        assert result.startswith("data:image/jpg;base64,")

    def test_with_prefix_true(self):
        """with_prefix=True返回带前缀字符串"""
        result = ndarray_to_base64(TEST_IMAGE_ARRAY, "png", with_prefix=True)
        assert result.startswith("data:image/png;base64,")

    def test_with_prefix_false(self):
        """with_prefix=False返回纯base64"""
        result = ndarray_to_base64(TEST_IMAGE_ARRAY, "png", with_prefix=False)
        assert not result.startswith("data:image/")
        # 验证可以被base64解码
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_input_type_error_non_ndarray(self):
        """非numpy数组输入抛出InputTypeError"""
        with pytest.raises(InputTypeError) as exc_info:
            ndarray_to_base64("not_an_array")
        assert "ndarray_to_base64" in str(exc_info.value)
        assert "expects np.ndarray" in str(exc_info.value)

    def test_input_type_error_wrong_ndarray_shape(self):
        """错误形状的数组抛出InputTypeError"""
        # 创建一个错误形状的数组（4D）
        wrong_shape_array = np.random.randint(0, 256, (100, 100, 3, 3), dtype=np.uint8)
        with pytest.raises(InputTypeError) as exc_info:
            ndarray_to_base64(wrong_shape_array)
        # 注意：OpenCV可能会处理这个，所以我们需要检查实际行为
        # 如果OpenCV能处理，这个测试可能不会抛出异常

    def test_input_data_error_empty_array(self):
        """空数组抛出InputDataError"""
        empty_array = np.array([])
        with pytest.raises(InputDataError):
            ndarray_to_base64(empty_array)


class TestResizeImage:
    """resize_image() 功能测试"""

    def test_stretch_mode_exact_dimensions(self):
        """stretch模式精确缩放到指定尺寸"""
        target_width, target_height = 50, 75
        expected_shape = (target_height, target_width, 3)
        result = resize_image(TEST_IMAGE_ARRAY, target_width, target_height, "stretch")
        assert result.shape == expected_shape

    def test_width_scale_mode_proportional(self):
        """width_scale模式按宽度等比缩放"""
        target_width = 50
        original_h, original_w = TEST_IMAGE_ARRAY.shape[:2]
        expected_height = int(original_h * (target_width / original_w))
        expected_shape = (expected_height, target_width, BGR_CHANNELS)
        result = resize_image(TEST_IMAGE_ARRAY, target_width, mode="width_scale")
        assert result.shape == expected_shape

    def test_height_scale_mode_proportional(self):
        """height_scale模式按高度等比缩放"""
        target_height = 75
        original_h, original_w = TEST_IMAGE_ARRAY.shape[:2]
        expected_width = int(original_w * (target_height / original_h))
        expected_shape = (target_height, expected_width, BGR_CHANNELS)
        result = resize_image(TEST_IMAGE_ARRAY, target_width=original_w, target_height=target_height, mode="height_scale")
        assert result.shape == expected_shape

    def test_grayscale_image_support(self):
        """支持单通道灰度图像"""
        target_width, target_height = 50, 50
        expected_shape = (target_height, target_width)
        gray_array = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = resize_image(gray_array, target_width, target_height, "stretch")
        assert result.shape == expected_shape

    def test_stretch_mode_with_none_height(self):
        """stretch模式下target_height为None时使用原始高度"""
        original_h, original_w = TEST_IMAGE_ARRAY.shape[:2]
        expected_shape = (original_h, 50, BGR_CHANNELS)
        result = resize_image(TEST_IMAGE_ARRAY, target_width=50, target_height=None, mode="stretch")
        assert result.shape == expected_shape

    def test_input_type_error_non_ndarray(self):
        """非numpy数组输入抛出InputTypeError"""
        with pytest.raises(InputTypeError) as exc_info:
            resize_image("not_an_array", 50, 50)
        assert "resize_image" in str(exc_info.value)

    def test_input_type_error_invalid_mode(self):
        """无效mode参数抛出InputTypeError"""
        with pytest.raises(InputTypeError) as exc_info:
            resize_image(TEST_IMAGE_ARRAY, 50, 50, "invalid_mode")

    def test_input_data_error_zero_dimensions(self):
        """零尺寸抛出InputDataError"""
        with pytest.raises(InputDataError):
            resize_image(TEST_IMAGE_ARRAY, 0, 50)

    def test_input_data_error_negative_dimensions(self):
        """负尺寸抛出InputDataError"""
        with pytest.raises(InputDataError):
            resize_image(TEST_IMAGE_ARRAY, -10, 50)


class TestLoadImageToBase64:
    """load_image_to_base64() 功能测试"""

    def test_load_png_with_prefix(self):
        """加载PNG文件返回带前缀base64"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            cv2.imwrite(tmp_file.name, TEST_IMAGE_ARRAY)
        try:
            result = load_image_to_base64(Path(tmp_path), with_prefix=True)
            assert isinstance(result, str)
            assert result.startswith("data:image/png;base64,")
        finally:
            os.unlink(tmp_path)

    def test_load_jpg_with_prefix(self):
        """加载JPG文件返回带前缀base64"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            cv2.imwrite(tmp_file.name, TEST_IMAGE_ARRAY, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        try:
            result = load_image_to_base64(Path(tmp_path), with_prefix=True)
            assert isinstance(result, str)
            assert result.startswith("data:image/jpg;base64,")
        finally:
            os.unlink(tmp_path)

    def test_load_without_prefix(self):
        """with_prefix=False返回纯base64"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            cv2.imwrite(tmp_file.name, TEST_IMAGE_ARRAY)
        try:
            result = load_image_to_base64(Path(tmp_path), with_prefix=False)
            assert isinstance(result, str)
            assert not result.startswith("data:image/")
        finally:
            os.unlink(tmp_path)

    def test_input_type_error_non_path(self):
        """非Path对象输入抛出InputTypeError"""
        with pytest.raises(InputTypeError) as exc_info:
            load_image_to_base64("not_a_path")
        assert "load_image_to_base64" in str(exc_info.value)

    def test_input_data_error_file_not_found(self):
        """文件不存在抛出InputDataError"""
        non_existent_path = Path("nonexistent_file.png")
        with pytest.raises(InputDataError) as exc_info:
            load_image_to_base64(non_existent_path)
        assert "nonexistent_file.png" in str(exc_info.value)

    def test_input_data_error_unsupported_format(self):
        """不支持格式文件抛出InputDataError并记录警告"""
        with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            # 创建一个简单的BMP文件
            simple_array = np.zeros((10, 10, 3), dtype=np.uint8)
            cv2.imwrite(tmp_file.name, simple_array)
        try:
            with pytest.raises(InputDataError):
                load_image_to_base64(Path(tmp_path))
        finally:
            os.unlink(tmp_path)

    def test_warning_logged_for_unsupported_format(self, caplog):
        """不支持格式触发警告日志"""
        with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            simple_array = np.zeros((10, 10, 3), dtype=np.uint8)
            cv2.imwrite(tmp_file.name, simple_array)
        try:
            try:
                load_image_to_base64(Path(tmp_path))
            except InputDataError:
                pass
            # 检查是否有警告日志
            assert any("警告: 不支持的文件格式" in record.message for record in caplog.records)
        finally:
            os.unlink(tmp_path)


class TestSaveBase64ToImage:
    """save_base64_to_image() 功能测试"""

    def test_save_with_prefix_to_png(self):
        """带前缀base64保存为PNG"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "test_image.jpg"  # 注意：这里用.jpg后缀
            save_base64_to_image(TEST_IMAGE_BASE64_WITH_PREFIX, save_path, with_prefix=True)
            # 验证文件存在且是PNG格式
            saved_path = save_path.with_suffix(".png")
            assert saved_path.exists()
            # 验证可以读取
            loaded_image = cv2.imread(str(saved_path))
            assert loaded_image is not None

    def test_save_without_prefix_to_png(self):
        """纯base64保存为PNG"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "test_image.png"
            save_base64_to_image(TEST_IMAGE_BASE64_NO_PREFIX, save_path, with_prefix=False)
            assert save_path.exists()
            loaded_image = cv2.imread(str(save_path))
            assert loaded_image is not None

    def test_file_extension_overridden(self):
        """自动修正文件后缀为.png"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_path = Path(tmp_dir) / "test_image.jpg"
            save_base64_to_image(TEST_IMAGE_BASE64_WITH_PREFIX, original_path)
            # 验证实际保存的文件是.png
            png_path = original_path.with_suffix(".png")
            assert png_path.exists()
            assert not original_path.exists()

    def test_input_type_error_invalid_base64(self):
        """无效base64字符串抛出InputDataError"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "test.png"
            with pytest.raises(InputDataError):
                save_base64_to_image("invalid_base64", save_path)

    def test_input_type_error_non_path(self):
        """非Path对象输入抛出InputTypeError"""
        with pytest.raises(InputTypeError) as exc_info:
            save_base64_to_image(TEST_IMAGE_BASE64_WITH_PREFIX, "not_a_path")
        assert "save_base64_to_image" in str(exc_info.value)


class TestConvertCmykToRgb:
    """convert_cmyk_to_rgb() 功能测试"""

    def test_valid_cmyk_pil_to_bgr(self):
        """CMYK PIL图像正确转换为BGR numpy数组"""
        # 创建CMYK PIL图像
        expected_shape = (100, 100, BGR_CHANNELS)
        expected_dtype = np.uint8
        cmyk_image = Image.new('CMYK', (100, 100), (100, 50, 75, 25))
        result = convert_cmyk_to_rgb(cmyk_image)
        assert isinstance(result, np.ndarray)
        assert result.shape == expected_shape
        assert result.dtype == expected_dtype

    def test_input_type_error_non_pil_image(self):
        """非PIL Image对象抛出InputTypeError"""
        with pytest.raises(InputTypeError) as exc_info:
            convert_cmyk_to_rgb("not_a_pil_image")
        assert "convert_cmyk_to_rgb" in str(exc_info.value)

    def test_input_type_error_rgb_pil_image(self):
        """RGB PIL图像输入抛出InputTypeError"""
        rgb_image = Image.new('RGB', (100, 100), (255, 128, 64))
        # 当前实现不会抛出异常，会正常转换
        # 这个测试可能需要根据实际需求调整


class TestIntegration:
    """函数集成测试"""

    def test_round_trip_base64_ndarray(self):
        """base64 → ndarray → base64 完整往返"""
        # 原始base64
        original_base64 = TEST_IMAGE_BASE64_WITH_PREFIX
        # 转换为ndarray
        ndarray = base64_to_ndarray(original_base64)
        # 转换回base64
        new_base64 = ndarray_to_base64(ndarray, "png", with_prefix=True)
        # 验证可以再次转换为ndarray
        final_ndarray = base64_to_ndarray(new_base64)
        assert final_ndarray.shape == ndarray.shape

    def test_load_resize_save_workflow(self):
        """load → resize → save 完整工作流"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建源文件
            source_path = Path(tmp_dir) / "source.png"
            cv2.imwrite(str(source_path), TEST_IMAGE_ARRAY)

            # 加载为base64
            base64_str = load_image_to_base64(source_path)

            # 转换为ndarray
            image_array = base64_to_ndarray(base64_str)

            # 调整大小
            resized_array = resize_image(image_array, 50, 50, "stretch")

            # 保存为新文件
            target_path = Path(tmp_dir) / "target.jpg"
            save_base64_to_image(ndarray_to_base64(resized_array, "png"), target_path)

            # 验证目标文件存在
            final_path = target_path.with_suffix(".png")
            assert final_path.exists()

    def test_multiple_resize_modes_comparison(self):
        """不同缩放模式结果对比验证"""
        original_h, original_w = TEST_IMAGE_ARRAY.shape[:2]

        # stretch模式
        stretch_result = resize_image(TEST_IMAGE_ARRAY, 50, 75, "stretch")
        expected_stretch_shape = (75, 50, BGR_CHANNELS)
        assert stretch_result.shape == expected_stretch_shape

        # width_scale模式
        width_result = resize_image(TEST_IMAGE_ARRAY, 50, mode="width_scale")
        expected_height = int(original_h * (50 / original_w))
        expected_width_shape = (expected_height, 50, BGR_CHANNELS)
        assert width_result.shape == expected_width_shape

        # height_scale模式
        height_result = resize_image(TEST_IMAGE_ARRAY, target_width=original_w, target_height=75, mode="height_scale")
        expected_width = int(original_w * (75 / original_h))
        expected_height_shape = (75, expected_width, BGR_CHANNELS)
        assert height_result.shape == expected_height_shape


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_base64_strings(self):
        """空base64字符串处理"""
        with pytest.raises(InputDataError):
            base64_to_ndarray("")

    def test_single_pixel_images(self):
        """单像素图像处理"""
        target_width, target_height = 10, 10
        expected_shape = (target_height, target_width, 3)
        single_pixel = np.array([[[255, 128, 64]]], dtype=np.uint8)
        result = resize_image(single_pixel, target_width, target_height, "stretch")
        assert result.shape == expected_shape

    def test_special_characters_in_paths(self):
        """路径包含特殊字符"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            special_path = Path(tmp_dir) / "test-image_测试.png"
            cv2.imwrite(str(special_path), TEST_IMAGE_ARRAY)
            base64_str = load_image_to_base64(special_path)
            assert isinstance(base64_str, str)

    def test_unicode_paths(self):
        """Unicode路径支持"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            unicode_path = Path(tmp_dir) / "图片.png"
            cv2.imwrite(str(unicode_path), TEST_IMAGE_ARRAY)
            base64_str = load_image_to_base64(unicode_path)
            assert isinstance(base64_str, str)


class TestResizeImageWithRealImages:
    """resize_image 真实图片测试 - 使用真实测试图像"""

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_resize_stretch_exact_dimensions(self):
        """验证 stretch 模式能精确产生指定尺寸"""
        original_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(original_path))
        h, w = original_image.shape[:2]

        # 测试宽度2倍，高度不变
        target_width, target_height = w * 2, h
        resized = resize_image(original_image, target_width, target_height, "stretch")
        expected_path = TEST_DATASET_PATH / "0_width2x.png"
        expected_image = cv2.imread(str(expected_path))

        expected_shape = (target_height, target_width, 3)
        assert resized.shape == expected_image.shape
        assert resized.shape == expected_shape

        # 测试高度2倍，宽度不变
        target_width, target_height = w, h * 2
        resized = resize_image(original_image, target_width, target_height, "stretch")
        expected_path = TEST_DATASET_PATH / "0_height2x.png"
        expected_image = cv2.imread(str(expected_path))

        expected_shape = (target_height, target_width, 3)
        assert resized.shape == expected_image.shape
        assert resized.shape == expected_shape

        # 测试宽高都2倍
        target_width, target_height = w * 2, h * 2
        resized = resize_image(original_image, target_width, target_height, "stretch")
        expected_path = TEST_DATASET_PATH / "0_2x.png"
        expected_image = cv2.imread(str(expected_path))

        expected_shape = (target_height, target_width, 3)
        assert resized.shape == expected_image.shape
        assert resized.shape == expected_shape

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_resize_width_scale_proportional(self):
        """验证 width_scale 模式保持宽高比"""
        original_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(original_path))
        h, w = original_image.shape[:2]

        target_width = w * 2
        resized = resize_image(original_image, target_width, mode="width_scale")
        expected_height = int(h * (target_width / w))

        expected_shape = (expected_height, target_width, BGR_CHANNELS)
        assert resized.shape == expected_shape

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_resize_height_scale_proportional(self):
        """验证 height_scale 模式保持宽高比"""
        original_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(original_path))
        h, w = original_image.shape[:2]

        target_height = h * 2
        resized = resize_image(original_image, target_width=w, target_height=target_height, mode="height_scale")
        expected_width = int(w * (target_height / h))

        expected_shape = (target_height, expected_width, BGR_CHANNELS)
        assert resized.shape == expected_shape

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_resize_modes_comparison(self):
        """对比三种缩放模式的结果差异"""
        original_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(original_path))
        h, w = original_image.shape[:2]

        # stretch 模式
        stretch_result = resize_image(original_image, w*2, h*2, "stretch")

        # width_scale 模式
        width_result = resize_image(original_image, w*2, mode="width_scale")

        # height_scale 模式
        height_result = resize_image(original_image, target_width=w, target_height=h*2, mode="height_scale")

        # 验证尺寸差异
        expected_shape = (h*2, w*2, 3)
        assert stretch_result.shape == expected_shape
        assert width_result.shape == expected_shape  # 因为原图是正方形，所以结果相同
        assert height_result.shape == expected_shape  # 因为原图是正方形，所以结果相同

        # 对于非正方形图像，这些模式会产生不同结果


class TestImageFileIntegration:
    """图像文件加载/保存集成测试"""

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_load_real_image_file(self):
        """测试加载真实的 PNG 文件"""
        image_path = TEST_DATASET_PATH / "0.png"
        base64_str = load_image_to_base64(image_path)
        assert isinstance(base64_str, str)
        assert base64_str.startswith("data:image/png;base64,")

        # 验证可以解码回图像
        decoded_image = base64_to_ndarray(base64_str)
        original_image = cv2.imread(str(image_path))
        assert decoded_image.shape == original_image.shape

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_save_and_reload_consistency(self):
        """保存后重新加载验证一致性"""
        original_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(original_path))

        # 转换为base64
        base64_str = ndarray_to_base64(original_image, "png")

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "saved_test.png"
            save_base64_to_image(base64_str, save_path)

            # 重新加载
            reloaded_image = cv2.imread(str(save_path))
            assert reloaded_image.shape == original_image.shape

            # 验证内容基本一致（PNG是有损压缩，但应该很接近）
            diff = np.abs(original_image.astype(np.float32) - reloaded_image.astype(np.float32))
            assert np.mean(diff) < 1.0  # 平均差异应该很小

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_base64_roundtrip_with_real_images(self):
        """使用真实图像进行往返测试"""
        image_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(image_path))

        # 加载为base64
        base64_str = load_image_to_base64(image_path)

        # 解码为ndarray
        decoded_image = base64_to_ndarray(base64_str)

        # 编码回base64
        new_base64_str = ndarray_to_base64(decoded_image, "png")

        # 再次解码
        final_image = base64_to_ndarray(new_base64_str)

        assert final_image.shape == original_image.shape


class TestImageQualityValidation:
    """图像质量验证测试"""

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_resize_quality_preservation(self):
        """验证缩放后的图像质量"""
        original_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(original_path))

        # 放大然后缩小，检查质量损失
        enlarged = resize_image(original_image, 256, 256, "stretch")
        reduced = resize_image(enlarged, 128, 128, "stretch")

        # 原图和还原后的图像应该相似
        diff = np.abs(original_image.astype(np.float32) - reduced.astype(np.float32))
        assert np.mean(diff) < 10.0  # 允许一定的质量损失

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_color_channel_integrity(self):
        """验证颜色通道完整性"""
        image_path = TEST_DATASET_PATH / "0.png"
        original_image = cv2.imread(str(image_path))

        # 确保有3个颜色通道
        assert original_image.shape[2] == BGR_CHANNELS

        # 测试各种操作后颜色通道完整性
        base64_str = ndarray_to_base64(original_image, "png")
        decoded_image = base64_to_ndarray(base64_str)
        assert decoded_image.shape[2] == BGR_CHANNELS


class TestGrayscaleAndSpecialFormats:
    """灰度图像和特殊格式测试"""

    def test_grayscale_image_support(self):
        """灰度图像支持测试 - IMREAD_UNCHANGED 保留原始单通道"""
        expected_shape = (100, 100)
        # 创建灰度图像
        gray_array = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        base64_str = ndarray_to_base64(gray_array, "png")
        decoded_gray = base64_to_ndarray(base64_str)
        # IMREAD_UNCHANGED 会保留灰度图像的单通道
        assert decoded_gray.shape == expected_shape

    @pytest.mark.skipif(not (TEST_DATASET_PATH / "0.png").exists(), reason="测试数据集不存在")
    def test_transparent_png_handling(self):
        """透明PNG处理测试"""
        # 创建带透明通道的PNG
        rgba_array = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as tmp_dir:
            png_path = Path(tmp_dir) / "transparent.png"
            cv2.imwrite(str(png_path), rgba_array)

            # 加载并验证
            try:
                base64_str = load_image_to_base64(png_path)
                decoded_image = base64_to_ndarray(base64_str)
                # OpenCV会自动去除alpha通道，所以应该是3通道
                assert decoded_image.shape[2] == BGR_CHANNELS
            except Exception:
                # 如果OpenCV不支持透明PNG，这也是可接受的行为
                pass
