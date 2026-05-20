#!/usr/bin/env python3
"""
完整的TireStruct对象构造示例

大图：tests/datasets/tire_design_images/images/testcase_002.jpg
小图：center和side目录下的图片(4张)
血缘信息：4条主沟配置，使用3/4张小图拼接

=== 可编辑评分配置 ===
"""

# ============ 可编辑配置 - 修改这里的数值即可生效 ============
EDITABLE_CONFIG = {
    "version": "1.0",
    "description": "TireStruct评分配置 - 直接修改score字段即可",
    
    # 小图评分（每个小图包含与RIB的对应关系）
    "small_images": [
        {
            "region": "center",
            "image_file": "testcase_001_center_part4_periodic.png",
            "rib_mapping": [
                {"rib_name": "rib2", "operation": "NONE", "description": "直接使用原始图"},
                {"rib_name": "rib4", "operation": "FLIP", "description": "旋转180°，继承rib2"}
            ],
            "rules": [
                {"name": "rule6", "description": "节距纵向关系无缝拼接", "max_score": 10, "score": 10},  # 可编辑
                {"name": "rule8", "description": "横沟数量约束", "max_score": 4, "score": 4},          # 可编辑
                {"name": "rule11", "description": "纵向钢片与细沟数量约束", "max_score": 4, "score": 4}, # 可编辑
                {"name": "rule14", "description": "交点数量≤2", "max_score": 2, "score": 2}           # 可编辑
            ]
        },
        {
            "region": "center",
            "image_file": "testcase_002_center_part4_periodic.png",
            "rib_mapping": [
                {"rib_name": "rib3", "operation": "LEFT_FLIP", "description": "截取左半并翻转覆盖右侧"}
            ],
            "rules": [
                {"name": "rule6", "description": "节距纵向关系无缝拼接", "max_score": 10, "score": 9},  # 可编辑
                {"name": "rule8", "description": "横沟数量约束", "max_score": 4, "score": 3},          # 可编辑
                {"name": "rule11", "description": "纵向钢片与细沟数量约束", "max_score": 4, "score": 3}, # 可编辑
                {"name": "rule14", "description": "交点数量≤2", "max_score": 2, "score": 1}           # 可编辑
            ]
        },
        {
            "region": "side",
            "image_file": "testcase_001_side_part1_periodic.png",
            "rib_mapping": [
                {"rib_name": "rib1", "operation": "NONE", "description": "直接使用原始图"},
                {"rib_name": "rib5", "operation": "FLIP", "description": "旋转180°，继承rib1"}
            ],
            "rules": [
                {"name": "rule6", "description": "节距纵向关系无缝拼接", "max_score": 10, "score": 8},   # 可编辑
                {"name": "rule8", "description": "横沟数量约束", "max_score": 4, "score": 2},          # 可编辑
                {"name": "rule11", "description": "纵向钢片与细沟数量约束", "max_score": 4, "score": 1}, # 可编辑
                {"name": "rule14", "description": "交点数量≤2", "max_score": 2, "score": 0}           # 可编辑
            ]
        },
        {
            "region": "side",
            "image_file": "testcase_002_side_part1_periodic.png",
            "rib_mapping": [],
            "rules": [
                {"name": "rule6", "description": "节距纵向关系无缝拼接", "max_score": 10, "score": 0},   # 可编辑
                {"name": "rule8", "description": "横沟数量约束", "max_score": 4, "score": 0},          # 可编辑
                {"name": "rule11", "description": "纵向钢片与细沟数量约束", "max_score": 4, "score": 0}, # 可编辑
                {"name": "rule14", "description": "交点数量≤2", "max_score": 2, "score": 0}           # 可编辑
            ]
        }
    ],
    
    # 大图评分
    "big_image": {
        "compliance_score": 0,  # 可编辑：合规性得分
        "rules": [
            {"name": "rule5", "description": "用户指定对称性输出", "max_score": 1, "score": 1},    # 可编辑
            {"name": "rule13", "description": "海陆比28%-35%", "max_score": 2, "score": 1},     # 可编辑
            {"name": "rule16", "description": "RIB2/3/4连续性", "max_score": 4, "score": 4},     # 可编辑
            {"name": "rule17", "description": "RIB1/2与RIB4/5概率连续", "max_score": 6, "score": 0}, # 可编辑
            {"name": "rule18", "description": "灰度变化", "max_score": 2, "score": 2},
            {"name": "rule19", "description": "边缘灰色装饰", "max_score": 2, "score": 2},
            {"name": "rule20", "description": "文生图", "max_score": 10, "score": 0},
            {"name": "rule22", "description": "图像分辨率", "max_score": 20, "score": 0}
        ],
        
        # 血缘信息
        "lineage": {
            "stitching_scheme": "symmetry_1",  # 中心对称
            "rib_count": 5,
            "groove_count": 4,  # 4条主沟
            "rib_sources": {
                "rib1": "testcase_001_side_part1_periodic.png",
                "rib2": "testcase_001_center_part4_periodic.png",
                "rib3": "testcase_002_center_part4_periodic.png",
                "rib4": "testcase_001_center_part4_periodic.png (继承rib2)",
                "rib5": "testcase_001_side_part1_periodic.png (继承rib1)"
            },
            "groove_widths": [30, 30, 30, 30],  # 4条主沟宽度(px)
            "decorations": [
                {"position": "left", "width": 20, "opacity": 128},
                {"position": "right", "width": 20, "opacity": 128}
            ]
        }
    },
    
    "scheme_rank": 1,
    "is_debug": True
}
# ============ 配置结束 ============

import base64
import json
import logging
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('tire_geometry_scorer')

from src.models.tire_struct import TireStruct
from src.models.image_models import (
    SmallImage, BigImage, ImageMeta, ImageBiz, ImageEvaluation,
    RuleEvaluation, ImageScore, ImageLineage
)
from src.models.rule_models import (
    BaseRuleConfig, Rule5Config, Rule6Config, Rule8Config, 
    Rule10Config, Rule11Config, Rule13Config, Rule14Config, 
    Rule16Config, Rule17Config, Rule18Config, Rule19Config, Rule20Config, Rule22Config,
    BaseRuleScore, Rule5Score, Rule6Score, Rule8Score,
    Rule10Score, Rule11Score, Rule13Score, Rule14Score, 
    Rule16Score, Rule17Score, Rule18Score, Rule19Score, Rule20Score, Rule22Score
)
from src.models.scheme_models import (
    StitchingScheme, StitchingSchemeAbstract, RibSchemeImpl,
    MainGrooveScheme, MainGrooveSchemeAbstract, MainGrooveImpl,
    DecorationScheme, DecorationSchemeAbstract, DecorationImpl
)
from src.models.enums import (
    LevelEnum, RegionEnum, SourceTypeEnum, ImageModeEnum, ImageFormatEnum,
    StitchingSchemeName, RibOperation, RuleTypeEnum
)
from src.nodes.geometry_scorer import calculate_geometric_scores


def image_to_base64(file_path: str) -> str:
    """将图片文件转换为base64字符串"""
    with open(file_path, 'rb') as f:
        image_bytes = f.read()
    
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
    base64_str = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{base64_str}"


def create_tire_struct(config: dict) -> TireStruct:
    """根据配置创建TireStruct对象"""
    
    base_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'datasets', 'tire_design_images')
    
    # ========== 建立文件名 <-> base64 映射 ==========
    # 说明：小图类中没有 image_file 字段，通过此映射提供文件名信息
    image_file_to_base64 = {}
    base64_to_image_file = {}
    
    # 小图规则评分映射
    rule_config_map = {
        "rule5": (Rule5Config, Rule5Score),
        "rule6": (Rule6Config, Rule6Score),
        "rule8": (Rule8Config, Rule8Score),
        "rule10": (Rule10Config, Rule10Score),
        "rule11": (Rule11Config, Rule11Score),
        "rule13": (Rule13Config, Rule13Score),
        "rule14": (Rule14Config, Rule14Score),
        "rule16": (Rule16Config, Rule16Score),
        "rule17": (Rule17Config, Rule17Score),
        "rule18": (Rule18Config, Rule18Score),
        "rule19": (Rule19Config, Rule19Score),
        "rule20": (Rule20Config, Rule20Score),
        "rule22": (Rule22Config, Rule22Score),
    }
    
    # 规则特定参数默认值映射
    rule_default_params = {
        "rule8": {
            "groove_width_center": 30.0,
            "groove_width_side": 25.0,
        },
        "rule11": {
            "groove_width": 2.0,
            "min_width_offset_px": 1,
            "edge_margin_ratio": 0.1,
            "min_segment_length_ratio": 0.3,
            "max_angle_from_vertical": 15.0,
            "max_count_center": 3,
            "max_count_side": 2,
        },
        "rule10": {
            "transverse_sipe_width": 2.0,
            "position_tolerance_ratio": 0.2,
            "min_adjacent_groove_count": 2,
        },
        "rule13": {
            "land_ratio_min": 0.28,
            "land_ratio_max": 0.35,
        },
        "rule14": {
            "max_intersections": 2,
        },
        "rule16": {
            "continuity_mode": "any",
            "groove_width": 30.0,
            "blend_width": 10,
        },
        "rule17": {
            "edge_continuity_rib1_rib2": 0.5,
            "edge_continuity_rib4_rib5": 0.5,
            "blend_width": 10,
        },
        "rule18": {
            "enable_gray_depth": True,
            "min_gray_value": 0,
            "max_gray_value": 255,
            "depth_levels": 5,
        },
        "rule19": {
            "tire_design_width": 200,
            "decoration_border_alpha": 0.5,
            "decoration_gray_color": 128,
        },
        "rule20": {
            "prompt": "tire tread pattern design",
            "num_images": 1,
            "output_width": 512,
            "output_height": 512,
        },
        "rule22": {
            "target_width": 512,
            "target_height": 512,
            "keep_aspect_ratio": True,
            "output_format": "png",
        },
    }
    
    # 操作映射
    operation_map = {
        "NONE": RibOperation.NONE,
        "FLIP": RibOperation.FLIP,
        "FLIP_LR": RibOperation.FLIP_LR,
        "LEFT_FLIP": RibOperation.LEFT_FLIP,
        "LEFT": RibOperation.LEFT,
        "RIGHT": RibOperation.RIGHT,
    }
    
    # 创建小图（根据配置动态读取）
    small_images = []
    rib_mappings = []  # 收集所有RIB映射信息
    
    for img_cfg in config["small_images"]:
        # 读取图片
        region = img_cfg["region"]
        image_file = img_cfg["image_file"]
        if region == "center":
            img_path = os.path.join(base_path, "pieces", "center", image_file)
        else:
            img_path = os.path.join(base_path, "pieces", "side", image_file)
        image_base64 = image_to_base64(img_path)
        
        # 保存文件名映射
        image_file_to_base64[image_file] = image_base64
        base64_to_image_file[image_base64] = image_file
        
        # 创建规则评估
        rules = []
        for rule_cfg in img_cfg["rules"]:
            config_cls, score_cls = rule_config_map[rule_cfg["name"]]
            
            # 构建配置参数（包含默认值）
            config_kwargs = {
                "description": rule_cfg["description"],
                "max_score": rule_cfg["max_score"],
                "rule_type": RuleTypeEnum.SMALL_IMAGE
            }
            # 添加规则特定的默认参数
            if rule_cfg["name"] in rule_default_params:
                config_kwargs.update(rule_default_params[rule_cfg["name"]])
            
            rules.append(RuleEvaluation(
                name=rule_cfg["name"],
                config=config_cls(**config_kwargs),
                score=score_cls(score=rule_cfg["score"])
            ))
        
        # 创建小图对象
        small_image = SmallImage(
            image_base64=image_base64,
            meta=ImageMeta(width=512, height=512, channels=1, mode=ImageModeEnum.GRAY, format=ImageFormatEnum.PNG, size=1000),
            biz=ImageBiz(level=LevelEnum.SMALL, region=RegionEnum[region.upper()], source_type=SourceTypeEnum.ORIGINAL),
            evaluation=ImageEvaluation(
                rules=rules,
                current_score=sum(r.score.score for r in rules)
            )
        )
        small_images.append(small_image)
        
        # 收集RIB映射信息（包含 image_base64）
        rib_mappings.extend([
            {
                "rib_name": m["rib_name"],
                "operation": m["operation"],
                "description": m["description"],
                "image_file": image_file,
                "image_base64": image_base64  # 添加 base64 信息
            }
            for m in img_cfg["rib_mapping"]
        ])
    
    # 创建大图规则
    big_rules = []
    for rule_cfg in config["big_image"]["rules"]:
        config_cls, score_cls = rule_config_map[rule_cfg["name"]]
        
        # 构建配置参数（包含默认值）
        # 注意：不传入 rule_type，让配置类使用其内置的默认值
        config_kwargs = {
            "description": rule_cfg["description"],
            "max_score": rule_cfg["max_score"],
        }
        # 添加规则特定的默认参数
        if rule_cfg["name"] in rule_default_params:
            config_kwargs.update(rule_default_params[rule_cfg["name"]])
        
        big_rules.append(RuleEvaluation(
            name=rule_cfg["name"],
            config=config_cls(**config_kwargs),
            score=score_cls(score=rule_cfg["score"])
        ))
    
    # 血缘信息（根据配置中的rib_mapping构建）
    lineage_config = config["big_image"]["lineage"]
    
    # 构建RIB方案实现（根据配置中的rib_mapping）
    ribs_impl = []
    rib_sources = lineage_config["rib_sources"]
    
    # 找出继承关系
    inherit_map = {}
    for rib_name, source in rib_sources.items():
        if "(继承" in source:
            inherit_from = source.split("继承")[1].replace(")", "").strip()
            inherit_map[rib_name] = inherit_from
    
    for rib_name in ["rib1", "rib2", "rib3", "rib4", "rib5"]:
        # 找到该RIB的映射配置
        mapping = next((m for m in rib_mappings if m["rib_name"] == rib_name), None)
        if mapping:
            operation = operation_map.get(mapping["operation"], RibOperation.NONE)
            rib_source = "center" if "center" in mapping["image_file"] else "side"
            rib_same_as = inherit_map.get(rib_name)
            before_image = mapping.get("image_base64")  # 使用小图的 base64
            
            # 获取小图尺寸信息
            if before_image and before_image in small_images:
                img_obj = next((img for img in small_images if img.image_base64 == before_image), None)
                if img_obj and img_obj.meta:
                    rib_height = img_obj.meta.height
                    rib_width = img_obj.meta.width
                else:
                    rib_height = 512
                    rib_width = 512
            else:
                rib_height = 512
                rib_width = 512
            
            ribs_impl.append(RibSchemeImpl(
                rib_source=rib_source,
                rib_operation=(operation,),
                rib_name=rib_name,
                rib_same_as=rib_same_as,
                before_image=before_image,  # 小图 base64
                num_pitchs=5,               # 默认节距数量
                rib_height=rib_height,      # 小图高度
                rib_width=rib_width,        # 小图宽度
                after_image=None,           # 操作后图片（暂为空）
                rib_operation_eval=None     # 操作评估（暂为空）
            ))
    
    stitching_scheme = StitchingScheme(
        stitching_scheme_abstract=StitchingSchemeAbstract(
            name=StitchingSchemeName(lineage_config["stitching_scheme"]),
            description="中心对称拼接",
            rib_number=lineage_config["rib_count"]
        ),
        ribs_scheme_implementation=ribs_impl
    )
    
    main_groove_scheme = MainGrooveScheme(
        main_groove_scheme_abstract=MainGrooveSchemeAbstract(
            name="4-groove",
            groove_number=lineage_config["groove_count"]
        ),
        main_groove_implementation=[
            MainGrooveImpl(groove_width=w, groove_height=512) for w in lineage_config["groove_widths"]
        ]
    )
    
    decoration_scheme = DecorationScheme(
        decoration_scheme_abstract=DecorationSchemeAbstract(name="standard"),
        decoration_implementation=[
            DecorationImpl(
                decoration_width=d["width"],
                decoration_height=512,
                decoration_opacity=d["opacity"]
            ) for d in lineage_config["decorations"]
        ]
    )
    
    lineage = ImageLineage(
        stitching_scheme=stitching_scheme,
        main_groove_scheme=main_groove_scheme,
        decoration_scheme=decoration_scheme
    )
    
    # 创建大图（使用配置中的大图路径）
    big_image_path = os.path.join(base_path, "images", config["big_image"].get("image_file", "testcase_002.jpg"))
    if os.path.exists(big_image_path):
        big_image_base64 = image_to_base64(big_image_path)
    else:
        big_image_base64 = None  # 大图 base64 暂为空
    
    big_image = BigImage(
        image_base64=big_image_base64,
        meta=ImageMeta(width=2620, height=512, channels=3, mode=ImageModeEnum.RGB, format=ImageFormatEnum.JPG, size=50000),
        biz=ImageBiz(level=LevelEnum.BIG, source_type=SourceTypeEnum.CONCAT),
        evaluation=ImageEvaluation(
            rules=big_rules,
            current_score=sum(r.score.score for r in big_rules)
        ),
        scores=[ImageScore(compliance=config["big_image"]["compliance_score"])],
        lineage=lineage
    )
    
    # 创建TireStruct
    tire_struct = TireStruct(
        small_images=small_images,
        big_image=big_image,
        scheme_rank=config["scheme_rank"],
        is_debug=config["is_debug"],
        flag=True
    )
    
    # 返回 TireStruct 和文件名映射（用于 DEBUG 显示）
    # 说明：小图类中没有 image_file 字段，通过此映射提供文件名信息
    return tire_struct, {
        "image_file_to_base64": image_file_to_base64,
        "base64_to_image_file": base64_to_image_file
    }


def print_summary(config: dict):
    """打印配置摘要（使用logger）"""
    logger.info("=" * 80)
    logger.info("TireStruct 评分配置摘要")
    logger.info("=" * 80)
    
    # 小图评分
    logger.info("[小图评分]")
    for i, img in enumerate(config["small_images"]):
        logger.info(f"  [{img['region']}] - 图片: {img['image_file']}")
        logger.info("    ┌────────────┬───────┬─────────────────────────────┐")
        logger.info("    │ 规则名     │ 得分  │ 描述                         │")
        logger.info("    ├────────────┼───────┼─────────────────────────────┤")
        for rule in img["rules"]:
            logger.info(f"    │ {rule['name']:10} │ {rule['score']:2d}/{rule['max_score']:2d} │ {rule['description'][:27]} │")
        logger.info("    └────────────┴───────┴─────────────────────────────┘")
        total = sum(r["score"] for r in img["rules"])
        logger.info(f"    总分: {total}")
        
    # 大图评分
    logger.info("[大图评分]")
    logger.info("  ┌────────────┬───────┬─────────────────────────────┐")
    logger.info("  │ 规则名     │ 得分  │ 描述                         │")
    logger.info("  ├────────────┼───────┼─────────────────────────────┤")
    for rule in config["big_image"]["rules"]:
        logger.info(f"  │ {rule['name']:10} │ {rule['score']:2d}/{rule['max_score']:2d} │ {rule['description'][:27]} │")
    logger.info("  └────────────┴───────┴─────────────────────────────┘")
    total = sum(r["score"] for r in config["big_image"]["rules"])
    logger.info(f"  总分: {total}")
    
    # 血缘信息
    lineage = config["big_image"]["lineage"]
    logger.info("[血缘信息]")
    logger.info(f"  RIB数量: {lineage['rib_count']}")
    logger.info(f"  主沟数量: {lineage['groove_count']}条")
    logger.info("  RIB来源:")
    for rib, source in lineage["rib_sources"].items():
        logger.info(f"    - {rib}: {source}")


def run_e2e_geometry_scorer(config: dict, output_dir: str = "./.results/tire_design_images") -> dict:
    """
    端到端执行几何评分：创建TireStruct → 调用calculate_geometric_scores → 输出JSON结果
    
    Args:
        config: 配置字典
        output_dir: 输出目录
    
    Returns:
        dict: 评分结果（_calculate_geometric_scores输出结构）
    """
    from src.nodes.geometry_scorer import _calculate_geometric_scores
    
    logger.info("=" * 50)
    logger.info("开始端到端几何评分流程")
    logger.info("=" * 50)
    
    # 步骤1: 创建TireStruct对象（及文件名映射）
    logger.info("步骤1: 创建TireStruct对象...")
    tire_struct, file_mapping = create_tire_struct(config)
    base64_to_image_file = file_mapping["base64_to_image_file"]
    logger.info(f"TireStruct创建成功，包含 {len(tire_struct.small_images)} 张小图")
    
    big_image = tire_struct.big_image
    small_images = tire_struct.small_images
    lineage = big_image.lineage if big_image else None
    
    # ========== DEBUG: 小图筛选分析（使用 before_image 匹配） ==========
    logger.info("=" * 50)
    logger.info("DEBUG: 小图筛选分析 (使用 before_image 匹配)")
    logger.info("=" * 50)
    
    # 1. 打印所有小图信息
    logger.info(f"[DEBUG步骤1] 总小图数量: {len(small_images)}")
    for idx, img in enumerate(small_images):
        file_name = base64_to_image_file.get(img.image_base64, "unknown")
        base64_prefix = (img.image_base64[:50] + "...") if img.image_base64 else "None"
        logger.debug(f"  小图[{idx}]: region={img.biz.region}, file={file_name}")
        logger.debug(f"    base64: {base64_prefix}")
        if img.evaluation:
            for rule_eval in img.evaluation.rules:
                score_val = rule_eval.score.score if rule_eval.score else None
                logger.debug(f"    - {rule_eval.name}: score={score_val}")
    
    # 2. 提取血缘中的 before_image（与 _extract_used_small_image_regions 逻辑一致）
    used_before_images = []
    if lineage and lineage.stitching_scheme:
        logger.debug("  血缘RIB实现详情:")
        for rib_impl in lineage.stitching_scheme.ribs_scheme_implementation:
            before_image = rib_impl.before_image
            before_image_prefix = (before_image[:50] + "...") if before_image else "None"
            logger.debug(f"    - rib_name={rib_impl.rib_name}, before_image={before_image_prefix}")
            if before_image and before_image != "SKIPPED_GARBAGE":
                used_before_images.append(before_image)
    logger.info(f"[DEBUG步骤2] 血缘信息提取的before_image数量: {len(used_before_images)}")
    
    # 3. 有效小图筛选（使用 before_image 匹配，与 _calculate_geometric_scores 逻辑一致）
    effective_small_images = []
    matched_indices = set()
    for before_image in used_before_images:
        for idx, img in enumerate(small_images):
            if idx not in matched_indices and img.image_base64 == before_image:
                effective_small_images.append(img)
                matched_indices.add(idx)
                break
    
    logger.info(f"[DEBUG步骤3] 有效小图数量: {len(effective_small_images)}")
    for idx, img in enumerate(effective_small_images):
        config_idx = small_images.index(img)
        file_name = base64_to_image_file.get(img.image_base64, "unknown")
        logger.debug(f"  有效小图[{idx}]: region={img.biz.region}, file={file_name}")
    
    logger.debug("=" * 50)
    # ========== END DEBUG ==========
    
    # 步骤2: 调用 calculate_geometric_scores（使用 TireStruct 接口）
    logger.info("步骤2: 调用calculate_geometric_scores...")
    result_tire_struct = calculate_geometric_scores(tire_struct)
    logger.info("calculate_geometric_scores执行完成")
    
    # 步骤3: 调用 _calculate_geometric_scores 获取详细结果（用于输出）
    logger.info("步骤3: 获取详细评分结果...")
    rules_config = tire_struct.rules_config if hasattr(tire_struct, 'rules_config') else []
    
    # 重新收集 rules_config
    rules_config = []
    if big_image and big_image.evaluation:
        for rule_eval in big_image.evaluation.rules:
            if rule_eval.config:
                rules_config.append(rule_eval.config)
    for small_img in small_images:
        if small_img.evaluation:
            for rule_eval in small_img.evaluation.rules:
                if rule_eval.config and rule_eval.config not in rules_config:
                    rules_config.append(rule_eval.config)
    
    score_detail = _calculate_geometric_scores(
        big_image=big_image,
        small_images=small_images,
        lineage=lineage,
        rules_config=rules_config
    )
    
    # 步骤4: 输出结果到JSON文件
    logger.info("步骤4: 输出结果到JSON文件...")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "e2e_geometry_score_result.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(score_detail, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存到: {output_path}")
    logger.info("=" * 50)
    
    return score_detail


if __name__ == "__main__":
    # 打印配置摘要
    print_summary(EDITABLE_CONFIG)
    
    # 端到端执行几何评分
    result = run_e2e_geometry_scorer(EDITABLE_CONFIG)
    
    # 打印结果摘要
    logger.info("几何评分结果摘要:")
    logger.info(f"  总分: {result.get('total_score', 'N/A')}")
    logger.info(f"  最大可能得分: {result.get('max_possible_score', 'N/A')}")
    logger.info(f"  有效规则数: {result.get('effective_rule_count', 'N/A')}")
    logger.info(f"  各规则得分: {result.get('individual_scores', {})}")
    logger.info(f"  提示：直接修改文件头部的EDITABLE_CONFIG字典中的score值即可更新评分！")
