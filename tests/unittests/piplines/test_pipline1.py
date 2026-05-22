from __future__ import annotations

from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum, SourceTypeEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import Rule8Config
from src.models.tire_struct import TireStruct
from src.piplines.pipline1 import run_pipeline1


def make_meta() -> ImageMeta:
    return ImageMeta(
        width=10,
        height=10,
        channels=3,
        mode=ImageModeEnum.RGB,
        format=ImageFormatEnum.PNG,
        size=5,
    )


def make_tire_struct() -> TireStruct:
    return TireStruct(
        big_image=BigImage(
            image_base64="data:image/png;base64,big",
            meta=make_meta(),
            biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
        ),
        small_images=[
            SmallImage(
                image_base64="data:image/png;base64,small",
                meta=make_meta(),
                biz=ImageBiz(level=LevelEnum.SMALL, region=RegionEnum.CENTER),
            )
        ],
        rules_config=[Rule8Config(groove_width_center=1, groove_width_side=1)],
        scheme_rank=1,
        is_debug=True,
    )


def test_run_pipeline1_passes_big_image_inputs_to_evaluation_and_scoring(monkeypatch):
    """Verify Pipeline-1 wires Node4 and Node5 with the data they require."""
    tire_struct = make_tire_struct()
    calls: list[tuple[str, object, object, object]] = []

    monkeypatch.setattr("src.piplines.pipline1.load_all_executors", lambda: None)
    monkeypatch.setattr(
        "src.piplines.pipline1.evaluate_small_images",
        lambda small_images, rules_config, is_debug=False: small_images,
    )
    monkeypatch.setattr(
        "src.piplines.pipline1.generate_stitch_scheme",
        lambda big_image, small_images, rules_config, scheme_rank: big_image,
    )
    monkeypatch.setattr(
        "src.piplines.pipline1.stitch_big_image",
        lambda big_image: big_image,
    )

    def fake_evaluate_big_image(big_image, rules_config, is_debug=False):
        calls.append(("evaluate_big_image", big_image, rules_config, is_debug))
        return big_image

    def fake_calculate_geometric_scores(big_image, small_images, rules_config):
        calls.append(("calculate_geometric_scores", big_image, small_images, rules_config))
        return big_image

    monkeypatch.setattr("src.piplines.pipline1.evaluate_big_image", fake_evaluate_big_image)
    monkeypatch.setattr("src.piplines.pipline1.calculate_geometric_scores", fake_calculate_geometric_scores)

    result = run_pipeline1(tire_struct)

    assert result is tire_struct
    assert result.flag is True
    assert result.err_msg is None
    assert calls == [
        ("evaluate_big_image", tire_struct.big_image, tire_struct.rules_config, True),
        ("calculate_geometric_scores", tire_struct.big_image, tire_struct.small_images, tire_struct.rules_config),
    ]
