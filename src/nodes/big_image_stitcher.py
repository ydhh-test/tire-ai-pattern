"""大图拼接节点（Node3）。

接收 pipeline 传入的 BigImage（已挂载 ImageLineage），
调用处理层执行实际拼接，原地更新 image_base64 和 lineage。
"""

from __future__ import annotations

from src.common.exceptions import InputDataError
from src.models.image_models import BigImage
from src.processing.image_stiching import generate_large_image_from_lineage
from src.utils.logger import get_logger

logger = get_logger(__name__)

NODE_NAME = "big_image_stitcher"


def stitch_big_image(
    big_image: BigImage,
    is_debug: bool = False,
) -> BigImage:
    if big_image is None:
        raise InputDataError(NODE_NAME, "big_image", "big_image is required")
    if big_image.lineage is None:
        raise InputDataError(NODE_NAME, "lineage", "big_image.lineage is required")

    updated_lineage, large_image_base64 = generate_large_image_from_lineage(
        big_image.lineage,
        is_debug=is_debug,
    )

    big_image.image_base64 = large_image_base64
    big_image.lineage = updated_lineage

    return big_image
