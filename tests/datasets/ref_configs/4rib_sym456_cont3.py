"""
参考配置 1.10：4个RIB，对称性4/5/6三候选，连续性3 (RIB2-RIB3连续)
方案: symmetry_4/5/6 + continuity_3
RIB数量: 4
对称性候选: [symmetry_4, symmetry_5, symmetry_6]
连续性候选: [continuity_3]
"""

from pathlib import Path
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        {"rule": "rule2", "description": "rib中心对称", "max_score": 10},
        {"rule": "rule3", "description": "rib左右对称", "max_score": 10},
        {
            "rule": "rule12",
            "max_score": 6,
            "description": "两个RIB间横向钢片及横沟连续性占比是否满足要求",
            "continuity_ratio_upper": 0.7,
            "continuity_ratio_lower": 0.6,
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_3],
        },
        {
            "rule": "rule16",
            "max_score": 4,
            "description": "中心RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_3],
        },
        {
            "rule": "rule17",
            "max_score": 6,
            "description": "边缘RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_3],
        },
        {
            "rule": "rule100", "rib_number": 4,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
