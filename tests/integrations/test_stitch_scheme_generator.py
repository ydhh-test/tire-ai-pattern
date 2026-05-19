from __future__ import annotations

import pytest

from src.common.exceptions import InputDataError
from src.models.enums import (
    ImageFormatEnum,
    ImageModeEnum,
    LevelEnum,
    RegionEnum,
    SourceTypeEnum,
    StitchingSchemeName,
    RibOperation,
)
from src.models.image_models import (
    ImageLineage,
    ImageBiz,
    ImageEvaluation,
    ImageMeta,
    RuleEvaluation,
    SmallImage,
)
from src.models.rule_models import (
    DecorationItem,
    GrooveSizeItem,
    RibSizeItem,
    Rule1Config,
    Rule1Score,
    Rule2Config,
    Rule3Config,
    Rule8Config,
    Rule100Config,
    Rule101Config,
    Rule102Config,
)
from src.models.scheme_models import (
    Continuity0,
    Continuity1,
    RibTemplate,
    StitchingTemplate,
    Symmetry0,
    Symmetry1,
)
from src.models.template_registry import get_stitching_templates
from src.nodes.stitch_scheme_generator import (
    _TemplateCombination,
    _filter_templates,
    _instantiate_stitching_scheme,
    _small_image_content_hash,
    _CandidateScheme,
    generate_stitch_scheme,
)
from src.utils.image_utils import base64_to_ndarray

def make_small_image(region: RegionEnum, payload: str, score: int) -> SmallImage:
    return SmallImage(
        image_base64=f"data:image/png;base64,{payload}",
        meta=ImageMeta(
            width=10,
            height=10,
            channels=3,
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=10,
        ),
        biz=ImageBiz(
            level=LevelEnum.SMALL,
            region=region,
            source_type=SourceTypeEnum.ORIGINAL,
        ),
        evaluation=ImageEvaluation(
            rules=[
                RuleEvaluation(
                    name="rule1",
                    config=Rule1Config(),
                    score=Rule1Score(score=score),
                )
            ],
            current_score=score,
        ),
    )

def test_generate_stitch_scheme(small_images=None, rules_config=None):
    if not small_images:
        small_images = [
            make_small_image(RegionEnum.SIDE, "side-a", 5),
            make_small_image(RegionEnum.SIDE, "side-b", 8),
            make_small_image(RegionEnum.SIDE, "side-c", 8),
            make_small_image(RegionEnum.CENTER, "center-a", 3),
            make_small_image(RegionEnum.CENTER, "center-b", 2),
            make_small_image(RegionEnum.CENTER, "center-add", 10),
            make_small_image(RegionEnum.CENTER, "center-1ddd", 10),
            make_small_image(RegionEnum.CENTER, "center-dd", 10),
        ]
    if not rules_config:
        rules_config = [
            Rule1Config(),
            Rule2Config(),
            Rule8Config(groove_width_center=1, groove_width_side=2),
            Rule100Config(
                    rib_number=5,
                    rib_sizes=[
                        RibSizeItem(rib_name="rib1", num_pitchs=5, rib_width=400, rib_height=640),
                        RibSizeItem(rib_name="rib2", num_pitchs=6, rib_width=200, rib_height=640),
                        RibSizeItem(rib_name="rib3", num_pitchs=6, rib_width=200, rib_height=640),
                        RibSizeItem(rib_name="rib4", num_pitchs=6, rib_width=200, rib_height=640),
                        RibSizeItem(rib_name="rib5", num_pitchs=6, rib_width=200, rib_height=640),
                    ],
            ),
            Rule101Config(groove_sizes=[GrooveSizeItem(groove_width=10, groove_height=640)]),
            Rule102Config(
                    decorations=[
                        DecorationItem(
                            position="left",
                            decoration_width=300,
                            decoration_height=640,
                            decoration_opacity=128,
                        )
                    ],
            ),
        ]

    
    generate_stitch_scheme(small_images, rules_config, 1)


def test_sort_and_lineage():
    # 当前主要是测试排名，无对称性和对称性的最高总分会是一样，查看日志：最终方案[1]

    # 生成方案Symmetry0_Continuity2
    small_images = [
        make_small_image(RegionEnum.SIDE, "side-a", 5),
        make_small_image(RegionEnum.SIDE, "side-b", 8),
        make_small_image(RegionEnum.SIDE, "side-c", 8),
        make_small_image(RegionEnum.CENTER, "center-a", 3),
        make_small_image(RegionEnum.CENTER, "center-b", 2),
        make_small_image(RegionEnum.CENTER, "center-add", 10),
        make_small_image(RegionEnum.CENTER, "center-1ddd", 10),
        make_small_image(RegionEnum.CENTER, "center-dd", 10),
    ]
    #test_generate_stitch_scheme(small_images)
    
    # 日志输出
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 小图清单：side:8f8b5329(score=5), side:7e0bd07e(score=8), side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2), center:68fc99ce(score=10), center:8704b04f(score=10), center:92f696db(score=10)
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 符合配置: [Rule1Config[5个花纹RIB无对称原则], Rule2Config[中心旋转180°对称花纹], Rule100Config[RIB 节距与尺寸配置], Rule101Config[主沟尺寸配置], Rule102Config[装饰边 框尺寸与透明度配置]]
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 符合对称性模板: [Symmetry0[花纹RIB无对称原则], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）]]
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 符合连续性模板: [Continuity0[无操作模版，不修改对称性方案], Continuity1[RIB2-RIB3连续，边缘独立], Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 小图数量: 中心=5, 边缘=3, 全部=8
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 准备工作: 对称性模板=2, 连续性模板=3, 中心图片=5, 边缘图片=3
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 排列思路: 公式=A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] = 360 + 360 + 360 + 60 + 60 + 60 = 1260
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 生成方案数量: 1260
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 得分统计: 方案数=1260, 最高分=46, 最低分=17
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - 最终方案[1]: Symmetry0[花纹RIB无对称原则] + Continuity2[RIB3-RIB4连续，边缘独立] | score=46 | images=[side:da2ccdbf(score=8), center:92f696db(score=10), center:68fc99ce(score=10), center:8704b04f(score=10), side:7e0bd07e(score=8)]
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - lineage.rib[1]: name=rib1, source=side, same_as=None, operation=('',), size=(5,400,640), image=da2ccdbf
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - lineage.rib[2]: name=rib2, source=center, same_as=None, operation=('',), size=(6,200,640), image=92f696db
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - lineage.rib[3]: name=rib3, source=center, same_as=rib4, operation=('', 'resize_horizontal_2x', 'left'), size=(6,200,640), image=8704b04f
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - lineage.rib[4]: name=rib4, source=center, same_as=None, operation=('', 'resize_horizontal_2x', 'right'), size=(6,200,640), image=8704b04f
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - lineage.rib[5]: name=rib5, source=side, same_as=None, operation=('',), size=(6,200,640), image=7e0bd07e
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - lineage.groove[1]: width=10, height=640, image=6da393a5
    # 2026-05-19 12:00:07 - 拼接方案 - INFO - lineage.decoration[1]: width=300, height=640, opacity=128, image=9705cbbf

    # 仅修改图片内容： Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立]
    small_images = [
        make_small_image(RegionEnum.SIDE, "side-a", 5),
        make_small_image(RegionEnum.SIDE, "side-b", 8),
        make_small_image(RegionEnum.SIDE, "side-c", 8),
        make_small_image(RegionEnum.CENTER, "center-a", 3),
        make_small_image(RegionEnum.CENTER, "center-b", 2),
        make_small_image(RegionEnum.CENTER, "center-acddd", 10),
        make_small_image(RegionEnum.CENTER, "center-1d", 10),
        make_small_image(RegionEnum.CENTER, "center-dddd", 10),
    ]
    # test_generate_stitch_scheme(small_images)

    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 小图清单：side:8f8b5329(score=5), side:7e0bd07e(score=8), side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2), center:68fc99ce(score=10), center:8704b04f(score=10), center:4567b284(score=10)
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 符合配置: [Rule1Config[5个花纹RIB无对称原则], Rule2Config[中心旋转180°对称花纹], Rule100Config[RIB 节距与尺寸配置], Rule101Config[主沟尺寸配置], Rule102Config[装饰边框尺寸与透明度配置]]
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 符合对称性模板: [Symmetry0[花纹RIB无对称原则], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）]]
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 符合连续性模板: [Continuity0[无操作模版，不修改对称性方案], Continuity1[RIB2-RIB3连续，边缘独立], Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 小图数量: 中心=5, 边缘=3, 全部=8
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 准备工作: 对称性模板=2, 连续性模板=3, 中心图片=5, 边缘图片=3
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 排列思路: 公式=A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] = 360 + 360 + 360 + 60 + 60 + 60 = 1260
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 生成方案数量: 1260
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 得分统计: 方案数=1260, 最高分=46, 最低分=17
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - 最终方案[1]: Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立] | score=46 | images=[side:da2ccdbf(score=8), center:4567b284(score=10), center:68fc99ce(score=10), center:4567b284(score=10), side:da2ccdbf(score=8)]
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - lineage.rib[1]: name=rib1, source=side, same_as=None, operation=('',), size=(5,400,640), image=da2ccdbf
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - lineage.rib[2]: name=rib2, source=center, same_as=None, operation=('', 'resize_horizontal_2x', 'left'), size=(6,200,640), image=4567b284
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - lineage.rib[3]: name=rib3, source=center, same_as=rib2, operation=('', 'resize_horizontal_2x', 'right'), size=(6,200,640), image=4567b284
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - lineage.rib[4]: name=rib4, source=center, same_as=rib2, operation=('flip',), size=(6,200,640), image=4567b284
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - lineage.rib[5]: name=rib5, source=side, same_as=rib1, operation=('flip',), size=(6,200,640), image=da2ccdbf
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - lineage.groove[1]: width=10, height=640, image=6da393a5
    # 2026-05-19 12:08:13 - 拼接方案 - INFO - lineage.decoration[1]: width=300, height=640, opacity=128, image=9705cbbf

    # 仅修改图片内容： Symmetry0[花纹RIB无对称原则] + Continuity1[RIB2-RIB3连续，边缘独立]
    small_images = [
        make_small_image(RegionEnum.SIDE, "side-a", 5),
        make_small_image(RegionEnum.SIDE, "side-b", 8),
        make_small_image(RegionEnum.SIDE, "side-c", 8),
        make_small_image(RegionEnum.CENTER, "center-a", 3),
        make_small_image(RegionEnum.CENTER, "center-b", 2),
        make_small_image(RegionEnum.CENTER, "center-acd", 10),
        make_small_image(RegionEnum.CENTER, "center-1adad", 10),
        make_small_image(RegionEnum.CENTER, "center-add1a", 10),
    ]
    test_generate_stitch_scheme(small_images)
    
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 小图清单：side:8f8b5329(score=5), side:7e0bd07e(score=8), side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2), center:5978a179(score=10), center:e10a5282(score=10), center:0d51d92c(score=10)
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 符合配置: [Rule1Config[5个花纹RIB无对称原则], Rule2Config[中心旋转180°对称花纹], Rule100Config[RIB 节距与尺寸配置], Rule101Config[主沟尺寸配置], Rule102Config[装饰边框尺寸与透明度配置]]
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 符合对称性模板: [Symmetry0[花纹RIB无对称原则], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）]]
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 符合连续性模板: [Continuity0[无操作模版，不修改对称性方案], Continuity1[RIB2-RIB3连续，边缘独立], Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 小图数量: 中心=5, 边缘=3, 全部=8
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 准备工作: 对称性模板=2, 连续性模板=3, 中心图片=5, 边缘图片=3
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 排列思路: 公式=A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] = 360 + 360 + 360 + 60 + 60 + 60 = 1260
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 生成方案数量: 1260
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 得分统计: 方案数=1260, 最高分=46, 最低分=17
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - 最终方案[1]: Symmetry0[花纹RIB无对称原则] + Continuity1[RIB2-RIB3连续，边缘独立] | score=46 | images=[side:da2ccdbf(score=8), center:5978a179(score=10), center:e10a5282(score=10), center:0d51d92c(score=10), side:7e0bd07e(score=8)]
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - lineage.rib[1]: name=rib1, source=side, same_as=None, operation=('',), size=(5,400,640), image=da2ccdbf
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - lineage.rib[2]: name=rib2, source=center, same_as=None, operation=('', 'resize_horizontal_2x', 'left'), size=(6,200,640), image=5978a179
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - lineage.rib[3]: name=rib3, source=center, same_as=rib2, operation=('', 'resize_horizontal_2x', 'right'), size=(6,200,640), image=5978a179
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - lineage.rib[4]: name=rib4, source=center, same_as=None, operation=('',), size=(6,200,640), image=0d51d92c
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - lineage.rib[5]: name=rib5, source=side, same_as=None, operation=('',), size=(6,200,640), image=7e0bd07e
    # 2026-05-19 12:09:21 - 拼接方案 - INFO - lineage.groove[1]: width=10, height=640, image=6da393a5


def test_node2_score():
    # 可选取最高分，由于对称性可以获取两次边缘，所以一定只选取到对称性方案, 查看日志行：最高分模板组合
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 最高分模板组合: [Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity0[无操作模版，不修改对称性方案], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity2[RIB3-RIB4连续，边缘独立]]
    small_images = [
        make_small_image(RegionEnum.SIDE, "side-a", 5),
        make_small_image(RegionEnum.SIDE, "side-b", 6),
        make_small_image(RegionEnum.SIDE, "side-c", 8),
        make_small_image(RegionEnum.CENTER, "center-a", 3),
        make_small_image(RegionEnum.CENTER, "center-b", 2),
        make_small_image(RegionEnum.CENTER, "center-acd", 2),
        make_small_image(RegionEnum.CENTER, "center-1adad", 10),
        make_small_image(RegionEnum.CENTER, "center-add1a", 10),
    ]
    test_generate_stitch_scheme(small_images)
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 小图清单：side:8f8b5329(score=5), side:7e0bd07e(score=6), side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2), center:5978a179(score=2), center:e10a5282(score=10), center:0d51d92c(score=10)
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 符合配置: [Rule1Config[5个花纹RIB无对称原则], Rule2Config[中心旋转180°对称花纹], Rule100Config[RIB 节距与尺寸配置], Rule101Config[主沟尺寸配置], Rule102Config[装饰边框尺寸与透明度配置]]
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 符合对称性模板: [Symmetry0[花纹RIB无对称原则], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）]]
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 符合连续性模板: [Continuity0[无操作模版，不修改对称性方案], Continuity1[RIB2-RIB3连续，边缘独立], Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 小图数量: 中心=5, 边缘=3, 全部=8
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 准备工作: 对称性模板=2, 连续性模板=3, 中心图片=5, 边缘图片=3
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 排列思路: 公式=A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] = 360 + 360 + 360 + 60 + 60 + 60 = 1260      
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 生成方案数量: 1260
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 得分统计: 方案数=1260, 最高分=46, 最低分=16
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 最高分模板组合: [Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity0[无操作模版，不修改对称性方案], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - 最终方案[1]: Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity2[RIB3-RIB4连续，边缘独立] | score=46 | images=[side:da2ccdbf(score=8), center:0d51d92c(score=10), center:e10a5282(score=10), center:0d51d92c(score=10), side:da2ccdbf(score=8)]
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - lineage.rib[1]: name=rib1, source=side, same_as=None, operation=('',), size=(5,400,640), image=da2ccdbf
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - lineage.rib[2]: name=rib2, source=center, same_as=None, operation=('',), size=(6,200,640), image=0d51d92c
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - lineage.rib[3]: name=rib3, source=center, same_as=rib2, operation=('flip', 'resize_horizontal_2x', 'left'), size=(6,200,640), image=0d51d92c
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - lineage.rib[4]: name=rib4, source=center, same_as=rib2, operation=('flip', 'resize_horizontal_2x', 'right'), size=(6,200,640), image=0d51d92c
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - lineage.rib[5]: name=rib5, source=side, same_as=rib1, operation=('flip',), size=(6,200,640), image=da2ccdbf
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - lineage.groove[1]: width=10, height=640, image=6da393a5
    # 2026-05-19 12:19:04 - 拼接方案 - INFO - lineage.decoration[1]: width=300, height=640, opacity=128, image=9705cbbf


def test_node2_templatefilter():
    # 没有Rule1
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 符合对称性模板: [Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）]]
    rules_config = [
        Rule2Config(),
        Rule8Config(groove_width_center=1, groove_width_side=2),
        Rule100Config(
                rib_number=5,
                rib_sizes=[
                    RibSizeItem(rib_name="rib1", num_pitchs=5, rib_width=400, rib_height=640),
                    RibSizeItem(rib_name="rib2", num_pitchs=6, rib_width=200, rib_height=640),
                    RibSizeItem(rib_name="rib3", num_pitchs=6, rib_width=200, rib_height=640),
                    RibSizeItem(rib_name="rib4", num_pitchs=6, rib_width=200, rib_height=640),
                    RibSizeItem(rib_name="rib5", num_pitchs=6, rib_width=200, rib_height=640),
                ],
        ),
        Rule101Config(groove_sizes=[GrooveSizeItem(groove_width=10, groove_height=640)]),
        Rule102Config(
                decorations=[
                    DecorationItem(
                        position="left",
                        decoration_width=300,
                        decoration_height=640,
                        decoration_opacity=128,
                    )
                ],
        ),
    ]
    # test_generate_stitch_scheme(rules_config=rules_config)

    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 小图清单：side:8f8b5329(score=5), side:7e0bd07e(score=8), side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2), center:9df276d1(score=10), center:65f83782(score=10), center:e4af0ff9(score=10)
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 符合配置: [Rule2Config[中心旋转180°对称花纹], Rule100Config[RIB 节距与尺寸配置], Rule101Config[主沟尺寸配置], Rule102Config[装饰边框尺寸与透明度配置]]
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 符合对称性模板: [Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）]]
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 符合连续性模板: [Continuity0[无操作模版，不修改对称性方案], Continuity1[RIB2-RIB3连续，边缘独立], Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 小图数量: 中心=5, 边缘=3, 全部=8
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 准备工作: 对称性模板=1, 连续性模板=3, 中心图片=5, 边缘图片=3
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 排列思路: 公式=A[1,3]*A[2,5] + A[1,3]*A[2,5] + A[1,3]*A[2,5] = 60 + 60 + 60 = 180
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 生成方案数量: 180
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 得分统计: 方案数=180, 最高分=46, 最低分=17
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 最高分模板组合: [Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity0[无操作模版，不修改对称性方案], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - 最终方案[1]: Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立] | score=46 | images=[side:7e0bd07e(score=8), center:9df276d1(score=10), center:e4af0ff9(score=10), center:9df276d1(score=10), side:7e0bd07e(score=8)]
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - lineage.rib[1]: name=rib1, source=side, same_as=None, operation=('',), size=(5,400,640), image=7e0bd07e
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - lineage.rib[2]: name=rib2, source=center, same_as=None, operation=('', 'resize_horizontal_2x', 'left'), size=(6,200,640), image=9df276d1
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - lineage.rib[3]: name=rib3, source=center, same_as=rib2, operation=('', 'resize_horizontal_2x', 'right'), size=(6,200,640), image=9df276d1
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - lineage.rib[4]: name=rib4, source=center, same_as=rib2, operation=('flip',), size=(6,200,640), image=9df276d1
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - lineage.rib[5]: name=rib5, source=side, same_as=rib1, operation=('flip',), size=(6,200,640), image=7e0bd07e
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - lineage.groove[1]: width=10, height=640, image=6da393a5
    # 2026-05-19 12:34:38 - 拼接方案 - INFO - lineage.decoration[1]: width=300, height=640, opacity=128, image=9705cbbf

    # 没有Rule2
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 符合对称性模板: [Symmetry0[花纹RIB无对称原则]]
    rules_config = [
        Rule1Config(),
        Rule8Config(groove_width_center=1, groove_width_side=2),
        Rule100Config(
                rib_number=5,
                rib_sizes=[
                    RibSizeItem(rib_name="rib1", num_pitchs=5, rib_width=400, rib_height=640),
                    RibSizeItem(rib_name="rib2", num_pitchs=6, rib_width=200, rib_height=640),
                    RibSizeItem(rib_name="rib3", num_pitchs=6, rib_width=200, rib_height=640),
                    RibSizeItem(rib_name="rib4", num_pitchs=6, rib_width=200, rib_height=640),
                    RibSizeItem(rib_name="rib5", num_pitchs=6, rib_width=200, rib_height=640),
                ],
        ),
        Rule101Config(groove_sizes=[GrooveSizeItem(groove_width=10, groove_height=640)]),
        Rule102Config(
                decorations=[
                    DecorationItem(
                        position="left",
                        decoration_width=300,
                        decoration_height=640,
                        decoration_opacity=128,
                    )
                ],
        ),
    ]
    # test_generate_stitch_scheme(rules_config=rules_config)

    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 小图清单：side:8f8b5329(score=5), side:7e0bd07e(score=8), side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2), center:9df276d1(score=10), center:65f83782(score=10), center:e4af0ff9(score=10)
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 符合配置: [Rule1Config[5个花纹RIB无对称原则], Rule100Config[RIB 节距与尺寸配置], Rule101Config[主沟尺寸配置], Rule102Config[装饰边框尺寸与透明度配置]]
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 符合对称性模板: [Symmetry0[花纹RIB无对称原则]]
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 符合连续性模板: [Continuity0[无操作模版，不修改对称性方案], Continuity1[RIB2-RIB3连续，边缘独立], Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 小图数量: 中心=5, 边缘=3, 全部=8
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 准备工作: 对称性模板=1, 连续性模板=3, 中心图片=5, 边缘图片=3
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 排列思路: 公式=A[2,3]*A[3,5] + A[2,3]*A[3,5] + A[2,3]*A[3,5] = 360 + 360 + 360 = 1080
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 生成方案数量: 1080
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 得分统计: 方案数=1080, 最高分=46, 最低分=28
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 最高分模板组合: [Symmetry0[花纹RIB无对称原则] + Continuity0[无操作模版，不修改对称性方案], Symmetry0[花纹RIB无对称原则] + Continuity1[RIB2-RIB3连续，边缘独立], Symmetry0[花纹RIB无对称原则] + Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - 最终方案[1]: Symmetry0[花纹RIB无对称原则] + Continuity0[无操作模版，不修改对称性方案] | score=46 | images=[side:7e0bd07e(score=8), center:9df276d1(score=10), center:e4af0ff9(score=10), center:65f83782(score=10), side:da2ccdbf(score=8)]
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - lineage.rib[1]: name=rib1, source=side, same_as=None, operation=('',), size=(5,400,640), image=7e0bd07e
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - lineage.rib[2]: name=rib2, source=center, same_as=None, operation=('',), size=(6,200,640), image=9df276d1
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - lineage.rib[3]: name=rib3, source=center, same_as=None, operation=('',), size=(6,200,640), image=e4af0ff9
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - lineage.rib[4]: name=rib4, source=center, same_as=None, operation=('',), size=(6,200,640), image=65f83782
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - lineage.rib[5]: name=rib5, source=side, same_as=None, operation=('',), size=(6,200,640), image=da2ccdbf
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - lineage.groove[1]: width=10, height=640, image=6da393a5
    # 2026-05-19 12:36:32 - 拼接方案 - INFO - lineage.decoration[1]: width=300, height=640, opacity=128, image=9705cbbf


    # 图片数量不够，中心只有两个
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 过滤对称性模板: Symmetry0[花纹RIB无对称原则]，原因: center需要3张，实际2张
    small_images = [
        make_small_image(RegionEnum.SIDE, "side-a", 5),
        make_small_image(RegionEnum.SIDE, "side-b", 6),
        make_small_image(RegionEnum.SIDE, "side-c", 8),
        make_small_image(RegionEnum.CENTER, "center-a", 3),
        make_small_image(RegionEnum.CENTER, "center-b", 2),
    ]
    test_generate_stitch_scheme(small_images)
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 小图清单：side:8f8b5329(score=5), side:7e0bd07e(score=6), side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2)
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 符合配置: [Rule1Config[5个花纹RIB无对称原则], Rule2Config[中心旋转180°对称花纹], Rule100Config[RIB 节距与尺寸配置], Rule101Config[主沟尺寸配置], Rule102Config[装饰边框尺寸与透明度配置]]
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 符合对称性模板: [Symmetry0[花纹RIB无对称原则], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）]]
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 符合连续性模板: [Continuity0[无操作模版，不修改对称性方案], Continuity1[RIB2-RIB3连续，边缘独立], Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 小图数量: 中心=2, 边缘=3, 全部=5
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 过滤对称性模板: Symmetry0[花纹RIB无对称原则]，原因: center需要3张，实际2张
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 准备工作: 对称性模板=1, 连续性模板=3, 中心图片=2, 边缘图片=3
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 排列思路: 公式=A[1,3]*A[2,2] + A[1,3]*A[2,2] + A[1,3]*A[2,2] = 6 + 6 + 6 = 18
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 生成方案数量: 18
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 得分统计: 方案数=18, 最高分=24, 最低分=17
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 最高分模板组合: [Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity0[无操作模版，不修改对称性方案], Symmetry1[花纹RIB中心对称（左侧旋转180度 是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立], Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity2[RIB3-RIB4连续，边缘独立]]
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - 最终方案[1]: Symmetry1[花纹RIB中心对称（左侧旋转180度是右侧）] + Continuity1[RIB2-RIB3连续，边缘独立] | score=24 | images=[side:da2ccdbf(score=8), center:7ba55b73(score=3), center:a1ccc07c(score=2), center:7ba55b73(score=3), side:da2ccdbf(score=8)]
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - lineage.rib[1]: name=rib1, source=side, same_as=None, operation=('',), size=(5,400,640), image=da2ccdbf
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - lineage.rib[2]: name=rib2, source=center, same_as=None, operation=('', 'resize_horizontal_2x', 'left'), size=(6,200,640), image=7ba55b73
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - lineage.rib[3]: name=rib3, source=center, same_as=rib2, operation=('', 'resize_horizontal_2x', 'right'), size=(6,200,640), image=7ba55b73
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - lineage.rib[4]: name=rib4, source=center, same_as=rib2, operation=('flip',), size=(6,200,640), image=7ba55b73
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - lineage.rib[5]: name=rib5, source=side, same_as=rib1, operation=('flip',), size=(6,200,640), image=da2ccdbf
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - lineage.groove[1]: width=10, height=640, image=6da393a5
    # 2026-05-19 12:38:25 - 拼接方案 - INFO - lineage.decoration[1]: width=300, height=640, opacity=128, image=9705cbbf


# test_sort_and_lineage()
test_node2_templatefilter()
