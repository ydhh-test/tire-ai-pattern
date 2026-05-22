from __future__ import annotations

from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta
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


def test_run_splitting_pipeline_delegates_to_pipeline4(monkeypatch):
    from src.api.splitting import run_splitting_pipeline

    tire_struct = _make_tire_struct()
    calls = []

    def fake_run_pipeline4(input_data):
        calls.append(input_data)
        input_data.flag = True
        input_data.err_msg = None
        return input_data

    monkeypatch.setattr("src.api.splitting.run_pipeline4", fake_run_pipeline4)

    result = run_splitting_pipeline(tire_struct)

    assert result is tire_struct
    assert result.flag is True
    assert result.err_msg is None
    assert calls == [tire_struct]
