from __future__ import annotations

from src.models.enums import ContinuityModeName, ImageFormatEnum, ImageModeEnum, LevelEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta
from src.models.rule_models import Rule16Config
from src.rules.executors.rule16 import Rule16Executor


def test_rule16_exec_feature_accepts_is_debug_argument_without_lineage():
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
    config = Rule16Config(continuity_mode_list=[ContinuityModeName.CONTINUITY_1])

    feature = Rule16Executor().exec_feature(image, config, is_debug=False)

    assert feature.is_continuous is False
