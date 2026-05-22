from __future__ import annotations

from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import Rule1Config
from src.models.tire_struct import TireStruct


def _make_tire_struct() -> TireStruct:
    return TireStruct(
        big_image=BigImage(
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
        ),
    )


def test_run_pipeline4_delegates_to_big_image_splitter(monkeypatch):
    from src.piplines.pipline4 import run_pipeline4

    tire_struct = _make_tire_struct()
    tire_struct.rules_config = [Rule1Config()]
    split_small_image = SmallImage(
        image_base64="data:image/png;base64,small",
        meta=ImageMeta(
            width=1,
            height=1,
            channels=3,
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=5,
        ),
        biz=ImageBiz(level=LevelEnum.SMALL, region="center"),
    )
    calls = []

    def fake_split_big_image(input_data, rules_config=None):
        calls.append((input_data, rules_config))
        return [split_small_image]

    monkeypatch.setattr("src.piplines.pipline4.split_big_image", fake_split_big_image)

    result = run_pipeline4(tire_struct)

    assert result is tire_struct
    assert result.small_images == [split_small_image]
    assert result.flag is True
    assert result.err_msg is None
    assert calls == [(tire_struct.big_image, tire_struct.rules_config)]
