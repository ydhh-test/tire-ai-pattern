from __future__ import annotations

from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta
from src.models.rule_models import Rule3Config
from src.rules.executors.rule3 import Rule3Executor


def test_rule3_exec_feature_accepts_is_debug_argument_without_lineage():
    image = BigImage(
        image_base64="data:image/png;base64,big",
        meta=ImageMeta(
            width=1,
            height=1,
            channels=3,
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=3,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
    )

    feature = Rule3Executor().exec_feature(image, Rule3Config(), is_debug=False)

    assert feature.is_active is False
