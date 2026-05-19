"""
大图生成业务处理模块

负责根据ImageLineage血缘信息完成完整的图片处理流程：
RIB预处理 → 主沟预处理 → 装饰预处理 → 参数验证 → 横向拼接 → 装饰覆盖
"""

import copy
import json

import cv2
import numpy as np
from typing import Any, Dict, List, Tuple, Optional

from src.models.image_models import ImageLineage
from src.models.scheme_models import (
    RibSchemeImpl,
    MainGrooveImpl,
    DecorationImpl
)
from src.utils.image_utils import (
    base64_to_ndarray,
    ndarray_to_base64,
    resize_image
)
from src.utils.logger import get_logger
from src.core.operation.image_operation import (
    apply_rib_operations_sequence,
    repeat_vertically,
    apply_opacity,
    horizontal_concatenate,
    overlay_decoration
)

logger = get_logger(__name__)


def _sanitize_lineage_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """深拷贝 lineage 字典，将 base64 图片值替换为摘要信息（不修改原对象）。"""
    sanitized = copy.deepcopy(data)

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith("data:image/"):
                    obj[key] = f"<base64 {len(value)} chars>"
                elif isinstance(value, (dict, list)):
                    _walk(value)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                if isinstance(item, str) and item.startswith("data:image/"):
                    obj[idx] = f"<base64 {len(item)} chars>"
                elif isinstance(item, (dict, list)):
                    _walk(item)

    _walk(sanitized)
    return sanitized


def _process_rib_images(ribs: List[RibSchemeImpl], is_debug: bool = False) -> None:
    """
    处理所有RIB图片

    流程:
    1. 跳过检查: 如果 after_image 已存在，跳过处理
    2. 解码 before_image (base64) → np.ndarray
    3. 执行 rib_operation 操作序列（调用core层apply_rib_operations_sequence）
    4. 纵向重复 num_pitchs 次（调用core层算法）
    5. resize(rib_width, rib_height)（调用utils层resize_image）
    6. 编码为base64存入 after_image
    """
    for rib in ribs:
        # 跳过检查
        if rib.after_image is not None:
            continue

        if rib.before_image is None:
            raise ValueError(f"RIB {rib.rib_name} 的 before_image 不能为空")

        # 解码 before_image
        image_array = base64_to_ndarray(rib.before_image)

        # 执行操作序列
        processed_image = apply_rib_operations_sequence(image_array, rib.rib_operation)

        # 纵向重复
        if rib.num_pitchs and rib.num_pitchs > 1:
            processed_image = repeat_vertically(processed_image, rib.num_pitchs)

        # 调整尺寸
        if rib.rib_width and rib.rib_height:
            processed_image = resize_image(
                processed_image,
                rib.rib_width,
                rib.rib_height,
                mode="stretch"
            )

        # 编码为base64
        rib.after_image = ndarray_to_base64(processed_image)


def _process_main_groove(main_grooves: List[MainGrooveImpl], is_debug: bool = False) -> None:
    """
    处理主沟图片

    流程:
    1. 跳过检查: 如果 after_image 已存在，跳过处理
    2. 解码 before_image (base64) → np.ndarray
    3. resize(groove_width, groove_height)（调用utils层resize_image）
    4. 编码为base64存入 after_image
    """
    for groove in main_grooves:
        # 跳过检查
        if groove.after_image is not None:
            continue

        if groove.before_image is None:
            continue

        # 解码图像
        image_array = base64_to_ndarray(groove.before_image)

        # 调整尺寸
        if groove.groove_width and groove.groove_height:
            resized_image = resize_image(
                image_array,
                groove.groove_width,
                groove.groove_height,
                mode="stretch"
            )
            groove.after_image = ndarray_to_base64(resized_image)


def _process_decoration(decorations: List[DecorationImpl], is_debug: bool = False) -> None:
    """
    处理装饰图片

    流程:
    1. 跳过检查: 如果 after_image 已存在，跳过处理
    2. 解码 before_image (base64) → np.ndarray
    3. resize(decoration_width, decoration_height)（调用utils层resize_image）
    4. 应用 decoration_opacity 透明度（调用core层算法）
    5. 编码为base64存入 after_image
    """
    for decoration in decorations:
        # 跳过检查
        if decoration.after_image is not None:
            continue

        if decoration.before_image is None:
            continue

        # 解码图像
        image_array = base64_to_ndarray(decoration.before_image)

        # 调整尺寸
        if decoration.decoration_width and decoration.decoration_height:
            resized_image = resize_image(
                image_array,
                decoration.decoration_width,
                decoration.decoration_height,
                mode="stretch"
            )
        else:
            resized_image = image_array

        # 应用透明度
        if decoration.decoration_opacity is not None:
            transparent_image = apply_opacity(resized_image, decoration.decoration_opacity)
            # 保留BGRA格式以支持透明度混合
        else:
            transparent_image = resized_image

        # 编码为base64
        decoration.after_image = ndarray_to_base64(transparent_image)


def _validate_parameters(
    ribs: List[RibSchemeImpl],
    main_grooves: List[MainGrooveImpl],
    decorations: List[DecorationImpl]
) -> None:
    """
    验证参数合规性

    规则:
    - 所有图片高度一致
    - 装饰宽度 ≤ 总宽度/2
    - 必需字段存在
    - 尺寸参数有效（正整数）
    """
    # 验证RIBs
    for i, rib in enumerate(ribs):
        if rib.after_image is None:
            raise ValueError(f"RIB {i} 的 after_image 未处理")
        if not rib.rib_width or not rib.rib_height:
            raise ValueError(f"RIB {i} 的尺寸参数不完整")

    # 验证主沟
    for i, groove in enumerate(main_grooves):
        if not groove.groove_width or not groove.groove_height:
            raise ValueError(f"主沟 {i} 的尺寸参数不完整")

    # 验证装饰
    for i, decoration in enumerate(decorations):
        if not decoration.decoration_width or not decoration.decoration_height:
            raise ValueError(f"装饰 {i} 的尺寸参数不完整")


def _build_concatenation_sequence(
    ribs: List[RibSchemeImpl],
    main_grooves: List[MainGrooveImpl]
) -> List[np.ndarray]:
    """
    构建横向拼接序列: rib1 + groove + rib2 + groove + ... + ribN

    Returns:
        List[np.ndarray]: 图像数组列表，按拼接顺序排列
    """
    sequence = []

    rib_count = len(ribs)
    groove_count = len(main_grooves)

    # 验证数量匹配
    if groove_count != rib_count - 1:
        raise ValueError(f"主沟数量({grove_count})应等于RIB数量({rib_count})减1")

    # 构建序列
    for i in range(rib_count):
        # 添加RIB
        rib_image = base64_to_ndarray(ribs[i].after_image)
        sequence.append(rib_image)

        # 添加主沟（除了最后一个RIB后不需要主沟）
        if i < rib_count - 1:
            groove_image = base64_to_ndarray(main_grooves[i].after_image)
            sequence.append(groove_image)

    return sequence


def _apply_resize_as_first_rib(
    concatenated_image: np.ndarray,
    first_rib_height: int,
    first_rib_width: int
) -> np.ndarray:
    """
    实现 _RESIZE_AS_FIRST_RIB 操作

    Args:
        concatenated_image: 拼接后的图像
        first_rib_height: 第一张RIB的高度
        first_rib_width: 第一张RIB的宽度

    Returns:
        np.ndarray: 调整尺寸后的图像
    """
    from src.utils.image_utils import resize_image
    return resize_image(
        concatenated_image,
        first_rib_width,
        first_rib_height,
        mode="stretch"
    )


def generate_large_image_from_lineage(
    lineage: ImageLineage,
    is_debug: bool = False
) -> Tuple[ImageLineage, str]:
    """
    根据血缘信息生成大图

    Args:
        lineage: ImageLineage - 包含完整血缘信息的对象
        is_debug: bool - 是否启用调试模式，默认False

    Returns:
        Tuple[ImageLineage, str] - (更新后的血缘对象, base64编码的大图)

    Raises:
        ValueError: 当参数验证失败时
        RuntimeError: 当图像处理过程中发生错误时
    """
    if lineage is None:
        raise ValueError("lineage 参数不能为空")

    # 记录 lineage 输入
    _raw_dict = json.loads(lineage.model_dump_json())
    if is_debug:
        logger.debug("lineage input: %s", lineage.model_dump_json(indent=2))
    else:
        logger.info("lineage input: %s", json.dumps(_sanitize_lineage_dict(_raw_dict), ensure_ascii=False))

    # 提取各方案组件
    stitching_scheme = lineage.stitching_scheme
    main_groove_scheme = lineage.main_groove_scheme
    decoration_scheme = lineage.decoration_scheme

    if stitching_scheme is None:
        raise ValueError("lineage.stitching_scheme 不能为空")

    ribs = stitching_scheme.ribs_scheme_implementation
    if not ribs:
        raise ValueError("RIB列表不能为空")

    main_grooves = []
    if main_groove_scheme and main_groove_scheme.main_groove_implementation:
        main_grooves = main_groove_scheme.main_groove_implementation

    decorations = []
    if decoration_scheme and decoration_scheme.decoration_implementation:
        decorations = decoration_scheme.decoration_implementation

    # RIB预处理
    _process_rib_images(ribs, is_debug)

    # 主沟预处理
    _process_main_groove(main_grooves, is_debug)

    # 装饰预处理
    _process_decoration(decorations, is_debug)

    # 参数验证
    _validate_parameters(ribs, main_grooves, decorations)

    # 构建拼接序列
    image_sequence = _build_concatenation_sequence(ribs, main_grooves)

    # 横向拼接
    concatenated_image = horizontal_concatenate(image_sequence)

    # 处理 _RESIZE_AS_FIRST_RIB 后处理（如果需要）
    # 检查是否有后处理操作需要执行
    if (stitching_scheme.stitching_scheme_abstract.name ==
            "continuity_0"):  # 示例：continuity_0方案需要后处理
        first_rib = ribs[0]
        if first_rib.rib_height and first_rib.rib_width:
            concatenated_image = _apply_resize_as_first_rib(
                concatenated_image,
                first_rib.rib_height,
                first_rib.rib_width
            )

    # 装饰覆盖
    final_image = concatenated_image
    if len(decorations) >= 2:
        left_decoration = base64_to_ndarray(decorations[0].after_image)
        right_decoration = base64_to_ndarray(decorations[1].after_image)
        final_image = overlay_decoration(final_image, left_decoration, right_decoration)
    elif len(decorations) == 1:
        # 只有一个装饰，应用到两侧
        decoration_img = base64_to_ndarray(decorations[0].after_image)
        final_image = overlay_decoration(final_image, decoration_img, decoration_img)

    # 编码为base64
    large_image_base64 = ndarray_to_base64(final_image)

    return lineage, large_image_base64