"""Pipeline-4 orchestration.

Pipeline-4 splits one big image into small images in the shared
``TireStruct`` so the result can be passed to Pipeline-1.
"""

from __future__ import annotations

from src.common.exceptions import InputDataError, InputTypeError
from src.models.tire_struct import TireStruct
from src.nodes.big_image_splitter import split_big_image
from src.utils.logger import get_logger


PIPELINE_NAME = "pipeline4"
logger = get_logger("pipeline4")


def run_pipeline4(tire_struct: TireStruct) -> TireStruct:
    """Run Pipeline-4 through the Node6 big image splitter."""

    if not isinstance(tire_struct, TireStruct):
        raise InputTypeError(
            function="run_pipeline4",
            param="tire_struct",
            expected_type="TireStruct",
            actual_type=type(tire_struct).__name__,
        )

    if tire_struct.big_image is None:
        raise InputDataError(
            object_name="TireStruct",
            field_path="big_image",
            rule="must not be None for pipeline4",
        )

    try:
        tire_struct.small_images = split_big_image(tire_struct.big_image, tire_struct.rules_config)
    except Exception as exc:
        logger.exception("%s failed at step: split_big_image", PIPELINE_NAME)
        tire_struct.small_images = []
        tire_struct.flag = False
        tire_struct.err_msg = f"{PIPELINE_NAME}.split_big_image failed: {exc}"
        return tire_struct

    tire_struct.flag = True
    tire_struct.err_msg = None
    return tire_struct
