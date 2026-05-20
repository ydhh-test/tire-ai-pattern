import pytest

from src.common.exceptions import InputDataError
from src.models.enums import (
    ImageFormatEnum,
    ImageModeEnum,
    LevelEnum,
    RibOperation,
    SourceTypeEnum,
    StitchingSchemeName,
)
from src.models.image_models import BigImage, ImageBiz, ImageLineage, ImageMeta
from src.models.scheme_models import (
    DecorationScheme,
    DecorationSchemeAbstract,
    MainGrooveImpl,
    MainGrooveScheme,
    MainGrooveSchemeAbstract,
    RibSchemeImpl,
    StitchingScheme,
    StitchingSchemeAbstract,
)
from src.nodes.big_image_stitcher import stitch_big_image

from tests.integrations.test_large_image_stitching import (
    _build_lineage_with_black_decoration,
)


def _make_input_big_image(lineage: ImageLineage) -> BigImage:
    return BigImage(
        image_base64="data:image/png;base64,placeholder",
        meta=ImageMeta(
            width=1, height=1, channels=3,
            mode=ImageModeEnum.RGB, format=ImageFormatEnum.PNG, size=0,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
        lineage=lineage,
    )


class TestStitchBigImageSuccess:
    """正常拼接场景"""

    def test_stitch_big_image_success(self):
        """5 RIB + 4 主沟 → image_base64 更新，lineage after_image 填充"""
        lineage = _build_lineage_with_black_decoration()
        big_image = _make_input_big_image(lineage)

        result = stitch_big_image(big_image)

        assert result is big_image
        assert result.image_base64.startswith("data:image/")
        assert result.image_base64 != "data:image/png;base64,placeholder"

        ribs = result.lineage.stitching_scheme.ribs_scheme_implementation
        for rib in ribs:
            assert rib.after_image is not None
            assert rib.after_image.startswith("data:image/")

    def test_output_is_same_object(self):
        """返回值是输入对象的同一引用"""
        lineage = _build_lineage_with_black_decoration()
        big_image = _make_input_big_image(lineage)

        result = stitch_big_image(big_image)

        assert result is big_image

    def test_image_base64_updated(self):
        """输出的 image_base64 以 data:image/ 开头且不等于占位值"""
        lineage = _build_lineage_with_black_decoration()
        big_image = _make_input_big_image(lineage)

        result = stitch_big_image(big_image)

        assert result.image_base64.startswith("data:image/")
        assert result.image_base64 != "data:image/png;base64,placeholder"

    def test_after_image_filled_on_lineage(self):
        """lineage 各组件 after_image 被填充"""
        lineage = _build_lineage_with_black_decoration()
        big_image = _make_input_big_image(lineage)

        result = stitch_big_image(big_image)

        ribs = result.lineage.stitching_scheme.ribs_scheme_implementation
        for rib in ribs:
            assert rib.after_image is not None, f"{rib.rib_name} after_image 未填充"

        grooves = result.lineage.main_groove_scheme.main_groove_implementation
        for i, groove in enumerate(grooves):
            assert groove.after_image is not None, f"主沟 {i} after_image 未填充"

        decorations = result.lineage.decoration_scheme.decoration_implementation
        for i, dec in enumerate(decorations):
            assert dec.after_image is not None, f"装饰 {i} after_image 未填充"


class TestStitchBigImageInputError:
    """输入校验场景"""

    def test_big_image_none_raises(self):
        """big_image=None 抛出 InputDataError"""
        with pytest.raises(InputDataError, match="big_image is required"):
            stitch_big_image(None)  # type: ignore[arg-type]

    def test_lineage_none_raises(self):
        """big_image.lineage=None 抛出 InputDataError"""
        big_image = BigImage(
            image_base64="data:image/png;base64,placeholder",
            meta=ImageMeta(
                width=1, height=1, channels=3,
                mode=ImageModeEnum.RGB, format=ImageFormatEnum.PNG, size=0,
            ),
            biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
            lineage=None,
        )
        with pytest.raises(InputDataError, match="big_image.lineage is required"):
            stitch_big_image(big_image)

    def test_groove_mismatch_raises(self):
        """主沟数 ≠ RIB数-1 → 底层 ValueError 上抛"""
        # 构造 3 个 RIB（需要 2 个主沟），但传入 1 个主沟
        # 使用 1x1 透明 PNG 作为有效 base64 图片，确保能通过解码
        _valid_png_base64 = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "YPj/HwADBwIAMCbHYQAAAABJRU5ErkJggg=="
        )
        rib_impl = RibSchemeImpl(
            rib_source="center",
            rib_operation=(RibOperation.NONE,),
            rib_name="test_rib",
            before_image=_valid_png_base64,
            num_pitchs=1,
            rib_height=64,
            rib_width=32,
        )
        stitching_scheme = StitchingScheme(
            stitching_scheme_abstract=StitchingSchemeAbstract(
                name=StitchingSchemeName.SYMMETRY_0,
                description="test",
                rib_number=3,
            ),
            ribs_scheme_implementation=[rib_impl, rib_impl, rib_impl],
        )
        groove_impl = MainGrooveImpl(
            before_image=_valid_png_base64,
            groove_width=10,
            groove_height=64,
        )
        lineage = ImageLineage(
            stitching_scheme=stitching_scheme,
            main_groove_scheme=MainGrooveScheme(
                main_groove_scheme_abstract=MainGrooveSchemeAbstract(
                    name="test", groove_number=1,
                ),
                main_groove_implementation=[groove_impl],
            ),
            decoration_scheme=DecorationScheme(
                decoration_scheme_abstract=DecorationSchemeAbstract(name="test"),
                decoration_implementation=[],
            ),
        )
        big_image = _make_input_big_image(lineage)

        with pytest.raises(ValueError):
            stitch_big_image(big_image)
