"""
参考配置 1.3：5个RIB，左右镜像对称，无连续性
方案: symmetry_2
RIB数量: 5
对称性候选: [symmetry_2]
连续性候选: 无
"""

from pathlib import Path
from src.models.enums import RegionEnum, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule3", "description": "rib左右对称", "max_score": 10},
        {
            "rule": "rule100", "rib_number": 5,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib5", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
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
