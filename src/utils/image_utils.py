from typing import Literal
from pathlib import Path
import base64
import binascii
import numpy as np
import cv2
from PIL import Image
from src.common.exceptions import InputTypeError, InputDataError, RuntimeProcessError
from src.utils.logger import get_logger


ImageType = Literal["png", "jpg", "jpeg"]
ResizeMode = Literal["stretch", "width_scale", "height_scale"]

logger = get_logger(__name__)


def base64_to_ndarray(image_base64: str) -> np.ndarray:
    """将 base64 字符串解码为 BGR np.ndarray。
    入参 image_base64 允许包含 "data:image/png;base64," 前缀，函数内部去除。
    依赖：base64.b64decode + np.frombuffer + cv2.imdecode"""
    # 类型检查
    if not isinstance(image_base64, str):
        raise InputTypeError("base64_to_ndarray", "image_base64", "str", type(image_base64).__name__)

    # 空字符串检查
    if not image_base64:
        raise InputDataError("base64_to_ndarray", "image_base64", "must not be empty", image_base64)

    try:
        # 去除前缀
        if image_base64.startswith("data:image/"):
            image_base64 = image_base64.split(",")[1]

        # 解码 - 使用IMREAD_UNCHANGED保留alpha通道
        image_data = base64.b64decode(image_base64)
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)

        if image is None:
            raise InputDataError("base64_to_ndarray", "image_base64", "invalid base64 or unsupported image format")

        return image
    except Exception as e:
        if isinstance(e, (InputTypeError, InputDataError)):
            raise
        if isinstance(e, binascii.Error):
            raise InputDataError("base64_to_ndarray", "image_base64", "invalid base64 string", image_base64)
        raise RuntimeProcessError("base64_to_ndarray", "failed to decode base64 image", e)


def ndarray_to_base64(
    image: np.ndarray,
    image_type: ImageType = "png",
    with_prefix: bool = True
) -> str:
    """将 BGR np.ndarray 编码为 base64 字符串。
    依赖：cv2.imencode + base64.b64encode
    with_prefix=True 时返回 "data:image/png;base64,xxx"。"""
    # 类型检查
    if not isinstance(image, np.ndarray):
        raise InputTypeError("ndarray_to_base64", "image", "np.ndarray", type(image).__name__)

    if not isinstance(image_type, str):
        raise InputTypeError("ndarray_to_base64", "image_type", "str", type(image_type).__name__)

    if not isinstance(with_prefix, bool):
        raise InputTypeError("ndarray_to_base64", "with_prefix", "bool", type(with_prefix).__name__)

    # 数据检查
    if image.size == 0:
        raise InputDataError("ndarray_to_base64", "image", "image array must not be empty")

    # 验证数组形状
    if len(image.shape) not in [2, 3]:
        raise InputTypeError("ndarray_to_base64", "image", "2D or 3D numpy array", f"{len(image.shape)}D array")

    if image_type not in ["png", "jpg", "jpeg"]:
        raise InputDataError("ndarray_to_base64", "image_type", "must be one of ['png', 'jpg', 'jpeg']", image_type)

    try:
        # 编码
        success, buffer = cv2.imencode(f".{image_type}", image)
        if not success:
            raise InputDataError("ndarray_to_base64", "image", "failed to encode image")

        image_base64 = base64.b64encode(buffer).decode('utf-8')

        if with_prefix:
            image_base64 = f"data:image/{image_type};base64,{image_base64}"

        return image_base64
    except Exception as e:
        if isinstance(e, (InputTypeError, InputDataError)):
            raise
        raise RuntimeProcessError("ndarray_to_base64", "failed to encode image to base64", e)


def resize_image(
    image: np.ndarray,
    target_width: int,
    target_height: int | None = None,
    mode: ResizeMode = "stretch"
) -> np.ndarray:
    """系统统一图像缩放工具函数
    输入图像必须为 np.ndarray 格式，shape 遵循 (H, W, C) 或 (H, W) 规范

    Parameters:
        image (np.ndarray): 输入原始图像，仅支持 numpy 数组
        target_width (int): 目标输出宽度
        target_height (int | None): 目标输出高度
        mode (ResizeMode): 图像缩放模式
            - "stretch": 普通缩放，直接按指定宽高拉伸/缩放到目标尺寸
            - "width_scale": 以目标宽度为基准，按原图比例等比缩放，高度自适应
            - "height_scale": 以目标高度为基准，按原图比例等比缩放，宽度自适应

    Returns:
        np.ndarray: 缩放后的图像"""
    # 类型检查
    if not isinstance(image, np.ndarray):
        raise InputTypeError("resize_image", "image", "np.ndarray", type(image).__name__)

    if not isinstance(target_width, int):
        raise InputTypeError("resize_image", "target_width", "int", type(target_width).__name__)

    if target_height is not None and not isinstance(target_height, int):
        raise InputTypeError("resize_image", "target_height", "int or None", type(target_height).__name__)

    if not isinstance(mode, str):
        raise InputTypeError("resize_image", "mode", "str", type(mode).__name__)

    # 数据检查
    if image.size == 0:
        raise InputDataError("resize_image", "image", "image array must not be empty")

    if target_width <= 0:
        raise InputDataError("resize_image", "target_width", "must be positive", target_width)

    if target_height is not None and target_height <= 0:
        raise InputDataError("resize_image", "target_height", "must be positive or None", target_height)

    if mode not in ["stretch", "width_scale", "height_scale"]:
        raise InputTypeError("resize_image", "mode", "one of ['stretch', 'width_scale', 'height_scale']", mode)

    try:
        h, w = image.shape[:2]

        if mode == "stretch":
            resized_image = cv2.resize(image, (target_width, target_height or h))
        elif mode == "width_scale":
            scale_factor = target_width / w
            new_height = int(h * scale_factor)
            resized_image = cv2.resize(image, (target_width, new_height))
        elif mode == "height_scale":
            actual_target_height = target_height or h
            scale_factor = actual_target_height / h
            new_width = int(w * scale_factor)
            resized_image = cv2.resize(image, (new_width, actual_target_height))

        return resized_image
    except Exception as e:
        if isinstance(e, (InputTypeError, InputDataError)):
            raise
        raise RuntimeProcessError("resize_image", "failed to resize image", e)


def load_image_to_base64(file_path: Path, with_prefix: bool = True) -> str:
    """读取 图片文件 并直接转为 base64。
    至少支持 png、jpg等常见格式（除了png，都要报告warning）"""
    # 类型检查
    if not isinstance(file_path, Path):
        raise InputTypeError("load_image_to_base64", "file_path", "Path", type(file_path).__name__)

    if not isinstance(with_prefix, bool):
        raise InputTypeError("load_image_to_base64", "with_prefix", "bool", type(with_prefix).__name__)

    try:
        # 读取图片
        image = cv2.imread(str(file_path))

        if image is None:
            raise InputDataError("load_image_to_base64", "file_path", "cannot read image file or file not found", str(file_path))

        # 获取文件扩展名
        file_extension = file_path.suffix.lower()

        if file_extension not in [".png", ".jpg", ".jpeg"]:
            logger.warning(f"警告: 不支持的文件格式: {file_extension}")
            # 根据测试要求，对于不支持的格式应该抛出异常
            raise InputDataError("load_image_to_base64", "file_path", f"unsupported file format: {file_extension}", str(file_path))

        # 编码为 base64
        success, buffer = cv2.imencode(file_extension, image)
        if not success:
            raise InputDataError("load_image_to_base64", "file_path", "failed to encode image")

        image_base64 = base64.b64encode(buffer).decode('utf-8')

        if with_prefix:
            image_base64 = f"data:image/{file_extension[1:]};base64,{image_base64}"

        return image_base64
    except Exception as e:
        if isinstance(e, (InputTypeError, InputDataError)):
            raise
        raise RuntimeProcessError("load_image_to_base64", "failed to load and encode image", e)


def save_base64_to_image(base64_str: str, save_path: Path, with_prefix: bool = True) -> None:
    """将图片base64字符串解码后保存为本地文件，**强制存储格式为PNG**。
    自动修正文件后缀为.png，忽略原路径后缀；
    兼容带data:image前缀和纯base64字符串。"""
    # 类型检查
    if not isinstance(base64_str, str):
        raise InputTypeError("save_base64_to_image", "base64_str", "str", type(base64_str).__name__)

    if not isinstance(save_path, Path):
        raise InputTypeError("save_base64_to_image", "save_path", "Path", type(save_path).__name__)

    if not isinstance(with_prefix, bool):
        raise InputTypeError("save_base64_to_image", "with_prefix", "bool", type(with_prefix).__name__)

    try:
        # 去除前缀
        if with_prefix and base64_str.startswith("data:image/"):
            base64_str = base64_str.split(",")[1]

        # 解码
        image_data = base64.b64decode(base64_str)
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            raise InputDataError("save_base64_to_image", "base64_str", "invalid base64 string or unsupported image format")

        # 保存为 PNG 格式
        save_path = save_path.with_suffix(".png")
        success = cv2.imwrite(str(save_path), image)
        if not success:
            raise RuntimeProcessError("save_base64_to_image", "failed to write image file", Exception(f"Cannot write to {save_path}"))

    except Exception as e:
        if isinstance(e, (InputTypeError, InputDataError)):
            raise
        if isinstance(e, binascii.Error):
            raise InputDataError("save_base64_to_image", "base64_str", "invalid base64 string", base64_str)
        raise RuntimeProcessError("save_base64_to_image", "failed to decode and save base64 image", e)


def convert_cmyk_to_rgb(img_pil) -> np.ndarray:
    """将PIL CMYK图像转换为OpenCV BGR格式（内存转换，无需文件IO）
    Args:
        img_pil: PIL Image对象 (CMYK模式)
    Returns:
        numpy数组 (BGR格式)"""
    # 类型检查
    if not hasattr(img_pil, 'mode') or not hasattr(img_pil, 'convert'):
        raise InputTypeError("convert_cmyk_to_rgb", "img_pil", "PIL Image", type(img_pil).__name__)

    if img_pil.mode != 'CMYK':
        raise InputDataError("convert_cmyk_to_rgb", "img_pil", "image mode must be CMYK", img_pil.mode)

    try:
        # 转换为 RGB
        img_rgb = img_pil.convert("RGB")

        # 转换为 OpenCV BGR 格式
        img_bgr = cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2BGR)

        return img_bgr
    except Exception as e:
        if isinstance(e, (InputTypeError, InputDataError)):
            raise
        raise RuntimeProcessError("convert_cmyk_to_rgb", "failed to convert CMYK to BGR", e)