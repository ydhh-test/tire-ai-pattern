"""Node2：基于已评分小图生成并排序拼接方案。"""

from __future__ import annotations

import hashlib
from itertools import permutations, product
from math import perm
from typing import Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict

from src.common.exceptions import InputDataError
from src.models.enums import RibOperation, SourceTypeEnum, StitchingSchemeName

from src.models.image_models import (
    ImageLineage,
    SmallImage,
    BigImage
)
from src.models.template_registry import get_stitching_templates
from src.models.rule_models import (
    BaseRuleConfig,
    Rule100Config,
    Rule101Config,
    Rule102Config,
)
from src.models.scheme_models import (
    RibTemplate,
    DecorationImpl,
    DecorationScheme,
    DecorationSchemeAbstract,
    MainGrooveImpl,
    MainGrooveScheme,
    MainGrooveSchemeAbstract,
    RibSchemeImpl,
    StitchingScheme,
    StitchingSchemeAbstract,
    StitchingTemplate,
)
from src.nodes.base import select_node_configs, STITCH_SCHEME_GENERATOR_CONFIGS
from src.utils.image_utils import ndarray_to_base64
from src.utils.logger import get_logger


logger = get_logger('拼接方案')


class _CandidateScheme(BaseModel):
    """进入最终 `scheme_rank` 选择前的候选方案。"""

    model_config = ConfigDict(frozen=True)

    template: "_TemplateCombination"
    selected_images: tuple[SmallImage, ...]
    total_score: int

    def __init__(self, *args: object, **data: object):
        field_names = ("template", "selected_images", "total_score")
        if len(args) > len(field_names):
            raise TypeError(f"expected at most {len(field_names)} positional arguments")
        for field_name, value in zip(field_names, args):
            if field_name in data:
                raise TypeError(f"got multiple values for argument '{field_name}'")
            data[field_name] = value
        super().__init__(**data)

    @property
    def log_display(self) -> str:
        return self.template.log_display

    @property
    def image_log_display(self) -> str:
        return _image_log_display(self.selected_images)

    @property
    def small_images(self) -> tuple[SmallImage, ...]:
        """兼容旧调用；候选方案实际保存的是最终 rib 位置图片。"""

        return self.selected_images

    @property
    def sort_key(self) -> tuple[int, str]:
        ordered_hashes = "|".join(
            _small_image_content_hash(image.image_base64)
            for image in self.selected_images
        )
        tie_breaker = hashlib.sha256(
            (
                f"{ordered_hashes}|{self.template.symmetry_template.name}|"
                f"{self.template.continuity_template.name}"
            ).encode("utf-8")
        ).hexdigest()
        return (-self.total_score, tie_breaker)

    @classmethod
    def rank(cls, candidates: Sequence["_CandidateScheme"]) -> list["_CandidateScheme"]:
        return sorted(candidates, key=lambda candidate: candidate.sort_key)


class _TemplateCombination(BaseModel):
    """一个 symmetry 模板与一个 continuity 模板组成的最终模板组合。"""

    model_config = ConfigDict(frozen=True)

    symmetry_template: StitchingTemplate
    continuity_template: StitchingTemplate

    def __init__(self, *args: object, **data: object):
        field_names = ("symmetry_template", "continuity_template")
        if len(args) > len(field_names):
            raise TypeError(f"expected at most {len(field_names)} positional arguments")
        for field_name, value in zip(field_names, args):
            if field_name in data:
                raise TypeError(f"got multiple values for argument '{field_name}'")
            data[field_name] = value
        super().__init__(**data)

    @property
    def rib_number(self) -> int:
        return self.symmetry_template.rib_number

    @property
    def name(self) -> StitchingSchemeName:
        return self.symmetry_template.name

    @property
    def description(self) -> str:
        return f"{self.symmetry_template.description} + {self.continuity_template.description}"

    @property
    def log_display(self) -> str:
        return (
            f"{self.symmetry_template.log_display}"
            f" + {self.continuity_template.log_display}"
        )


def _filter_templates(
    templates: Sequence[StitchingTemplate],
    *,
    target_rib_number: int,
    configs: Sequence[BaseRuleConfig],
) -> tuple[list[StitchingTemplate], list[StitchingTemplate]]:
    """分别筛出可用的 symmetry 模板和 continuity 模板。"""

    enabled_rule_names = {config.name for config in configs}
    symmetry_templates = [
        template
        for template in templates
        if template.mode == "symmetry"
        and template.rib_number == target_rib_number
        and bool(set(template.matching_rule_names) & enabled_rule_names)
    ]
    continuity_templates = [
        template
        for template in templates
        if template.mode == "continuity"
        and template.rib_number == target_rib_number
    ]

    return symmetry_templates, continuity_templates


def _combine_templates(
    symmetry_templates: Sequence[StitchingTemplate],
    continuity_templates: Sequence[StitchingTemplate],
) -> list[_TemplateCombination]:
    """把对称性模板与连续性模板做笛卡尔组合。"""

    return [
        _TemplateCombination(symmetry_template, continuity_template)
        for symmetry_template in symmetry_templates
        for continuity_template in continuity_templates
    ]


def _image_log_display(images: list[SmallImage]) -> str:
    return ", ".join(
        (
            f"{image.biz.region.value}:"
            f"{_small_image_content_hash(image.image_base64)[:8]}"
            f"(score={_small_image_score(image)})"
        )
        for image in images
    )

def _small_image_content_hash(image_base64: str) -> str:
    """仅对真实编码内容做哈希，忽略 data-url 前缀。"""

    _, _, raw_content = image_base64.partition(",")
    return hashlib.sha256(raw_content.encode("utf-8")).hexdigest()


def _small_image_score(image: SmallImage) -> int:
    """读取 Node1 已产出的分数；Node2 不重复计算。"""

    if image.evaluation is None:
        raise InputDataError("small_images", "evaluation", "must exist before Node2")
    return image.evaluation.current_score


def _candidate_total_score(
    template: _TemplateCombination,
    small_images: Sequence[SmallImage],
) -> int:
    """按最终输出 rib 数量计分；同一张图若被复用，也按复用次数重复计分。"""

    return sum(
        _small_image_score(image)
        for image in _expand_candidate_images(template, small_images)
    )


def _expand_candidate_images(
    template: _TemplateCombination,
    selected_slot_images: Sequence[SmallImage],
) -> tuple[SmallImage, ...]:
    """按 symmetry 入口选图结果，展开成 5 个 rib 位置上的图片。"""

    selected_iter = iter(selected_slot_images)
    image_by_rib_name: dict[str, SmallImage] = {}

    for rib_template in template.symmetry_template.rib_template_list:
        rib_name = rib_template.rib_name or ""
        if rib_template.source_type == SourceTypeEnum.ORIGINAL:
            image_by_rib_name[rib_name] = next(selected_iter)
            continue

        inherited_image = image_by_rib_name.get(rib_template.inherit_from or "")
        if inherited_image is None:
            raise InputDataError(
                "template",
                "inherit_from",
                "must reference an earlier symmetry rib",
                rib_template.inherit_from,
            )
        image_by_rib_name[rib_name] = inherited_image

    return tuple(
        image_by_rib_name[rib_template.rib_name or ""]
        for rib_template in template.symmetry_template.rib_template_list
    )


def _continuity_group_to_selection_slot(template: _TemplateCombination) -> dict[str, str]:
    """根据 continuity 分组，把每个分组映射到实际需要选择图片的槽位。"""

    original_slots_by_region: dict[str, list[str]] = {}
    for rib_template in _original_rib_templates(template.symmetry_template):
        if rib_template.region is None:
            continue
        original_slots_by_region.setdefault(rib_template.region.value, []).append(rib_template.rib_name or "")

    symmetry_ribs_by_name = {
        rib_template.rib_name or "": rib_template
        for rib_template in template.symmetry_template.rib_template_list
    }
    groups_by_region: dict[str, list[str]] = {}
    for continuity_rib in template.continuity_template.rib_template_list:
        group_key = continuity_rib.inherit_from or continuity_rib.rib_name or ""
        symmetry_rib = symmetry_ribs_by_name.get(group_key)
        if symmetry_rib is None or symmetry_rib.region is None:
            raise InputDataError(
                "template",
                "inherit_from",
                "must reference a symmetry rib with region",
                group_key,
            )
        region_groups = groups_by_region.setdefault(symmetry_rib.region.value, [])
        if group_key not in region_groups:
            region_groups.append(group_key)

    group_to_slot_key: dict[str, str] = {}
    for region, group_keys in groups_by_region.items():
        slot_keys = original_slots_by_region.get(region, [])
        if not slot_keys:
            raise InputDataError(
                "template",
                "region",
                "must have at least one original image slot",
                region,
            )
        for index, group_key in enumerate(group_keys):
            group_to_slot_key[group_key] = slot_keys[index % len(slot_keys)]

    return group_to_slot_key


def _selection_image_slot_keys(template: _TemplateCombination) -> list[str]:
    """返回本组合真正需要选图的槽位，顺序用于排列和日志填充。"""

    group_to_slot_key = _continuity_group_to_selection_slot(template)
    slot_keys: list[str] = []
    for continuity_rib in template.continuity_template.rib_template_list:
        group_key = continuity_rib.inherit_from or continuity_rib.rib_name or ""
        slot_key = group_to_slot_key[group_key]
        if slot_key not in slot_keys:
            slot_keys.append(slot_key)
    return slot_keys


def _original_rib_templates(template: StitchingTemplate):
    """仅返回真正需要消费输入小图的 RIB 位置。"""

    return [
        rib_template
        for rib_template in template.rib_template_list
        if rib_template.source_type == SourceTypeEnum.ORIGINAL
    ]


def _resolve_symmetry_source_ribs(template: StitchingTemplate) -> dict[str, RibTemplate]:
    """把 symmetry 模板中的每个 rib 归并到最终依赖的原始 rib。"""

    source_ribs: dict[str, RibTemplate] = {}
    for rib_template in template.rib_template_list:
        rib_name = rib_template.rib_name or ""
        if rib_template.source_type == SourceTypeEnum.ORIGINAL:
            source_ribs[rib_name] = rib_template
            continue

        inherited = source_ribs.get(rib_template.inherit_from or "")
        if inherited is None:
            raise InputDataError(
                "template",
                "inherit_from",
                "must reference an earlier rib",
                rib_template.inherit_from,
            )
        source_ribs[rib_name] = inherited
    return source_ribs


def _combine_rib_operations(
    source_operations: Sequence[RibOperation],
    continuity_operations: Sequence[RibOperation],
) -> tuple[RibOperation, ...]:
    """合并两步模板操作；连续性无操作时，保留 symmetry 的结果。"""

    if tuple(continuity_operations) == (RibOperation.NONE,):
        return tuple(source_operations)
    return tuple(source_operations) + tuple(continuity_operations)


def _merge_template_combination_ribs(template: _TemplateCombination) -> list[RibTemplate]:
    """把 symmetry 与 continuity 两步模板合并成最终输出的 5 个 RibTemplate。"""

    symmetry_ribs_by_name = {
        rib_template.rib_name or "": rib_template
        for rib_template in template.symmetry_template.rib_template_list
    }
    symmetry_source_ribs = _resolve_symmetry_source_ribs(template.symmetry_template)
    merged_ribs: list[RibTemplate] = []

    for continuity_rib in template.continuity_template.rib_template_list:
        rib_name = continuity_rib.rib_name or ""
        symmetry_rib_name = continuity_rib.inherit_from or rib_name
        symmetry_rib = symmetry_ribs_by_name.get(symmetry_rib_name)
        source_rib = symmetry_source_ribs.get(symmetry_rib_name)
        if symmetry_rib is None or source_rib is None:
            raise InputDataError(
                "template",
                "inherit_from",
                "must reference a symmetry rib",
                symmetry_rib_name,
            )

        final_operations = _combine_rib_operations(
            symmetry_rib.operation_template or tuple(),
            continuity_rib.operation_template or tuple(),
        )
        source_rib_name = source_rib.rib_name or ""
        if source_rib_name == rib_name:
            merged_ribs.append(
                RibTemplate(
                    region=source_rib.region,
                    source_type=SourceTypeEnum.ORIGINAL,
                    operation_template=final_operations,
                    rib_name=rib_name,
                )
            )
            continue

        # continuity 可以指向 symmetry 中的派生 rib；这里把继承链压平成
        # “最终输出 rib -> 原始来源 rib”，并把两阶段操作顺序合并起来。
        merged_ribs.append(
            RibTemplate(
                region=source_rib.region,
                source_type=SourceTypeEnum.INHERIT,
                inherit_from=source_rib_name,
                operation_template=final_operations,
                rib_name=rib_name,
            )
        )

    return merged_ribs


def _required_image_counts(template: _TemplateCombination) -> dict[str, int]:
    """统计 symmetry 入口真正需要选择的图片数量。"""

    counts: dict[str, int] = {}
    for rib_template in _original_rib_templates(template.symmetry_template):
        region_name = rib_template.region.value
        counts[region_name] = counts.get(region_name, 0) + 1
    return counts


def _missing_image_reasons(
    template: _TemplateCombination,
    image_counts: dict[str, int],
) -> list[str]:
    required_counts = _required_image_counts(template)
    return [
        f"{region}需要{required_count}张，实际{image_counts.get(region, 0)}张"
        for region, required_count in required_counts.items()
        if image_counts.get(region, 0) < required_count
    ]


def _filter_continuity_templates_by_image_count(
    symmetry_templates: Sequence[StitchingTemplate],
    continuity_templates: Sequence[StitchingTemplate],
    small_images: Sequence[SmallImage],
) -> list[StitchingTemplate]:
    """仅按图片数量过滤 continuity；symmetry 列表在这一阶段保持不变。"""

    image_counts = _count_small_images_by_region(small_images)
    filtered_templates: list[StitchingTemplate] = []

    for continuity_template in continuity_templates:
        missing_reasons_by_symmetry: list[str] = []
        for symmetry_template in symmetry_templates:
            combination = _TemplateCombination(symmetry_template, continuity_template)
            missing_reasons = _missing_image_reasons(combination, image_counts)
            if not missing_reasons:
                filtered_templates.append(continuity_template)
                break
            missing_reasons_by_symmetry.append(
                f"{symmetry_template.log_display}: {'；'.join(missing_reasons)}"
            )
        else:
            logger.info(
                "过滤连续性模板: %s，原因: %s",
                continuity_template.log_display,
                "；".join(missing_reasons_by_symmetry),
            )

    return filtered_templates


def _filter_symmetry_templates_by_image_count(
    symmetry_templates: Sequence[StitchingTemplate],
    small_images: Sequence[SmallImage],
) -> list[StitchingTemplate]:
    """按输入图片数量过滤 symmetry 模板。"""

    image_counts = _count_small_images_by_region(small_images)
    filtered_templates: list[StitchingTemplate] = []

    for symmetry_template in symmetry_templates:
        required_counts = {
            region: sum(
                1
                for rib_template in _original_rib_templates(symmetry_template)
                if rib_template.region.value == region
            )
            for region in image_counts
        }
        missing_reasons = [
            f"{region}需要{required_count}张，实际{image_counts.get(region, 0)}张"
            for region, required_count in required_counts.items()
            if image_counts.get(region, 0) < required_count
        ]
        if missing_reasons:
            logger.info(
                "过滤对称性模板: %s，原因: %s",
                symmetry_template.log_display,
                "；".join(missing_reasons),
            )
            continue
        filtered_templates.append(symmetry_template)

    return filtered_templates


def _enumerate_candidate_images(
    template: _TemplateCombination,
    small_images: Sequence[SmallImage],
) -> list[tuple[SmallImage, ...]]:
    """枚举某个模板下所有可行的小图分配。"""

    selection_ribs = _original_rib_templates(template.symmetry_template)
    # 区域：符合图片
    images_by_region = {
        region: [image for image in small_images if image.biz.region == region]
        for region in {rib.region for rib in selection_ribs}
    }
    # 模板区域：要求图片数量
    per_region_requirements = {
        region: sum(1 for rib in selection_ribs if rib.region == region)
        for region in images_by_region
    }
    
    # 不符合数量，直接返回
    for region, required_count in per_region_requirements.items():
        if len(images_by_region[region]) < required_count:
            return []

    # 每个 region 先各自生成“有序选择”，这样后面才能严格按模板 RIB 顺序回填。
    region_orders = {
        region: list(permutations(images, per_region_requirements[region]))
        for region, images in images_by_region.items()
    }

    candidates: list[tuple[SmallImage, ...]] = []
    # 各 region 的排列做笛卡尔积，才能覆盖 side / center 同时存在冗余候选图的情况。
    for region_choice in product(*region_orders.values()):
        selected_by_region = {
            region: list(choice)
            for region, choice in zip(region_orders.keys(), region_choice)
        }
        ordered_images: list[SmallImage] = []
        for rib in selection_ribs:
            ordered_images.append(selected_by_region[rib.region].pop(0))
        candidates.append(tuple(ordered_images))
    return candidates


def _build_candidates(
    templates: Sequence[_TemplateCombination],
    small_images: Sequence[SmallImage],
) -> list[_CandidateScheme]:
    """把已过滤模板展开成带总分的候选方案。"""

    candidates: list[_CandidateScheme] = []
    for template in templates:
        for selected_images in _enumerate_candidate_images(template, small_images):
            expanded_images = _expand_candidate_images(template, selected_images)
            total_score = sum(_small_image_score(image) for image in expanded_images)
            candidates.append(
                _CandidateScheme(
                    template=template,
                    selected_images=expanded_images,
                    total_score=total_score,
                )
            )
    return candidates


def _count_small_images_by_region(small_images: Sequence[SmallImage]) -> dict[str, int]:
    """统计各区域小图数量，供模板数量过滤和日志使用。"""

    counts: dict[str, int] = {}
    for image in small_images:
        region_name = image.biz.region.value
        counts[region_name] = counts.get(region_name, 0) + 1
    return counts


def _candidate_count_formula_summary(
    templates: Sequence[_TemplateCombination],
    image_counts: dict[str, int],
) -> str:
    """生成便于人眼快速扫过的排列组合摘要。"""

    existing_center = image_counts.get("center", 0)
    existing_side = image_counts.get("side", 0)
    formula_parts: list[str] = []
    result_parts: list[str] = []

    for template in templates:
        required_counts = _required_image_counts(template)
        required_center = required_counts.get("center", 0)
        required_side = required_counts.get("side", 0)
        if existing_center < required_center or existing_side < required_side:
            continue

        result = perm(existing_side, required_side) * perm(existing_center, required_center)
        formula_parts.append(
            f"A[{required_side},{existing_side}]*A[{required_center},{existing_center}]"
        )
        result_parts.append(str(result))

    total_count = sum(int(result) for result in result_parts)
    return f"{' + '.join(formula_parts)} = {' + '.join(result_parts)} = {total_count}"


def _get_config(
    configs: Sequence[BaseRuleConfig],
    config_type: type[BaseRuleConfig],
) -> BaseRuleConfig:
    for config in configs:
        if isinstance(config, config_type):
            return config
    raise InputDataError("rules_config", config_type.__name__, "must exist for Node2")


def _black_image_base64(width: int, height: int) -> str:
    """生成主沟和装饰方案需要的黑底源图。"""

    return ndarray_to_base64(np.zeros((height, width, 3), dtype=np.uint8))


def _instantiate_stitching_scheme(
    candidate: _CandidateScheme,
    rule100_config: Rule100Config,
) -> StitchingScheme:
    """把候选图和 Rule100 几何参数固化成运行时方案。"""

    rib_size_by_name = {item.rib_name: item for item in rule100_config.rib_sizes}
    ribs: list[RibSchemeImpl] = []
    final_rib_templates = _merge_template_combination_ribs(candidate.template)
    image_by_symmetry_rib_name = {
        rib_template.rib_name or "": image
        for rib_template, image in zip(
            candidate.template.symmetry_template.rib_template_list,
            candidate.selected_images,
        )
    }

    # 先把 symmetry 与 continuity 合并成最终 5 个 RibTemplate；
    # 后续实例化只负责补图片和 Rule100 几何参数，避免两套逻辑分叉。
    for rib_template in final_rib_templates:
        rib_name = rib_template.rib_name or ""
        rib_size = rib_size_by_name.get(rib_name)
        if rib_size is None:
            raise InputDataError(
                "rule100_config",
                "rib_sizes",
                "must cover every output rib",
                rib_name,
            )

        source_rib_name = rib_template.inherit_from or rib_name
        source_image = image_by_symmetry_rib_name.get(source_rib_name)
        if source_image is None:
            raise InputDataError(
                "template",
                "inherit_from",
                "must reference a prepared symmetry rib image",
                source_rib_name,
            )

        ribs.append(
            RibSchemeImpl(
                rib_source=source_image.biz.region.value,
                rib_operation=rib_template.operation_template or tuple(),
                rib_name=rib_template.rib_name,
                rib_same_as=None if source_rib_name == rib_name else source_rib_name,
                before_image=source_image.image_base64,
                num_pitchs=rib_size.num_pitchs,
                rib_width=rib_size.rib_width,
                rib_height=rib_size.rib_height,
            )
        )

    return StitchingScheme(
        stitching_scheme_abstract=StitchingSchemeAbstract(
            name=candidate.template.name,
            description=candidate.template.description,
            rib_number=candidate.template.rib_number,
        ),
        ribs_scheme_implementation=ribs,
    )


def _instantiate_main_groove_scheme(rule101_config: Rule101Config) -> MainGrooveScheme:
    """根据 Rule101 几何参数生成主沟方案。"""

    return MainGrooveScheme(
        main_groove_scheme_abstract=MainGrooveSchemeAbstract(
            name=rule101_config.name,
            description=rule101_config.description,
            groove_number=len(rule101_config.groove_sizes),
        ),
        main_groove_implementation=[
            MainGrooveImpl(
                before_image=_black_image_base64(item.groove_width, item.groove_height),
                groove_width=item.groove_width,
                groove_height=item.groove_height,
            )
            for item in rule101_config.groove_sizes
        ],
    )


def _instantiate_decoration_scheme(rule102_config: Rule102Config) -> DecorationScheme:
    """根据 Rule102 几何参数生成装饰方案。"""

    return DecorationScheme(
        decoration_scheme_abstract=DecorationSchemeAbstract(
            name=rule102_config.name,
            description=rule102_config.description,
        ),
        decoration_implementation=[
            DecorationImpl(
                before_image=_black_image_base64(item.decoration_width, item.decoration_height),
                decoration_width=item.decoration_width,
                decoration_height=item.decoration_height,
                decoration_opacity=item.decoration_opacity,
            )
            for item in rule102_config.decorations
        ],
    )


def _short_image_hash(image_base64: str | None) -> str:
    """日志中只输出图片短 hash，避免整段 base64 淹没核心信息。"""

    if not image_base64:
        return "None"
    return _small_image_content_hash(image_base64)[:8]


def _log_lineage_detail(lineage: ImageLineage) -> None:
    """分行输出最终 lineage，方便按 rib / groove / decoration 逐项检查。"""

    for index, rib in enumerate(lineage.stitching_scheme.ribs_scheme_implementation, start=1):
        logger.info(
            "lineage.rib[%s]: name=%s, source=%s, same_as=%s, operation=%s, size=(%s,%s,%s), image=%s",
            index,
            rib.rib_name,
            rib.rib_source,
            rib.rib_same_as,
            tuple(operation.value for operation in rib.rib_operation),
            rib.num_pitchs,
            rib.rib_width,
            rib.rib_height,
            _short_image_hash(rib.before_image),
        )

    for index, groove in enumerate(lineage.main_groove_scheme.main_groove_implementation, start=1):
        logger.info(
            "lineage.groove[%s]: width=%s, height=%s, image=%s",
            index,
            groove.groove_width,
            groove.groove_height,
            _short_image_hash(groove.before_image),
        )

    for index, decoration in enumerate(lineage.decoration_scheme.decoration_implementation, start=1):
        logger.info(
            "lineage.decoration[%s]: width=%s, height=%s, opacity=%s, image=%s",
            index,
            decoration.decoration_width,
            decoration.decoration_height,
            decoration.decoration_opacity,
            _short_image_hash(decoration.before_image),
        )


def generate_stitch_scheme(
    big_image: BigImage,
    small_images: Sequence[SmallImage],
    rules_config: Sequence[BaseRuleConfig],
    scheme_rank: int,
) -> BigImage:
    """根据小图、规则配置和排名生成指定的拼接 lineage。"""

    if scheme_rank < 1:
        raise InputDataError("scheme_rank", "value", "must be greater than or equal to 1")

    logger.info('小图清单：%s', _image_log_display(small_images))

    templates = get_stitching_templates()
    rule100_config = _get_config(rules_config, Rule100Config)
    rule101_config = _get_config(rules_config, Rule101Config)
    rule102_config = _get_config(rules_config, Rule102Config)

    configs = select_node_configs(
        rules_config,
        STITCH_SCHEME_GENERATOR_CONFIGS,
    )

    logger.info('符合配置: [%s]', ', '.join([f'{conf.__class__.__name__}[{conf.description}]' for conf in configs]))

    symmetry_templates, continuity_templates = _filter_templates(
        templates,
        target_rib_number=rule100_config.rib_number,
        configs=configs,
    )

    logger.info('符合对称性模板: [%s]', ', '.join([f'{temp.log_display}' for temp in symmetry_templates]))
    logger.info('符合连续性模板: [%s]', ', '.join([f'{temp.log_display}' for temp in continuity_templates]))


    if not symmetry_templates or not continuity_templates:
        raise InputDataError("templates", "filtered", "must contain at least one template")

    image_counts = _count_small_images_by_region(small_images)
    logger.info(
        "小图数量: 中心=%s, 边缘=%s, 全部=%s",
        image_counts.get("center", 0),
        image_counts.get("side", 0),
        len(small_images),
    )

    quantity_matched_symmetry_templates = _filter_symmetry_templates_by_image_count(
        symmetry_templates,
        small_images,
    )
    quantity_matched_continuity_templates = _filter_continuity_templates_by_image_count(
        quantity_matched_symmetry_templates,
        continuity_templates,
        small_images,
    )

    logger.info(
        "准备工作: 对称性模板=%s, 连续性模板=%s, 中心图片=%s, 边缘图片=%s",
        len(quantity_matched_symmetry_templates),
        len(quantity_matched_continuity_templates),
        image_counts.get("center", 0),
        image_counts.get("side", 0),
    )
    if not quantity_matched_symmetry_templates or not quantity_matched_continuity_templates:
        raise InputDataError("templates", "image_count", "must contain at least one feasible template")

    combined_templates = _combine_templates(
        quantity_matched_symmetry_templates,
        quantity_matched_continuity_templates,
    )
    formula_summary = _candidate_count_formula_summary(
        combined_templates,
        image_counts,
    )
    logger.info("排列思路: 公式=%s", formula_summary)

    # TODO
    # 生成的方案数量过多，可能需要渐进式生成，按照同分的依次往下
    # 如果满足scheme_rank的数量，则终止生成
    candidate_inputs: list[tuple[_TemplateCombination, tuple[SmallImage, ...]]] = []
    for template in combined_templates:
        selected_image_groups = _enumerate_candidate_images(template, small_images)
        candidate_inputs.extend((template, selected_images) for selected_images in selected_image_groups)

    logger.info("生成方案数量: %s", len(candidate_inputs))
    if not candidate_inputs:
        raise InputDataError("candidates", "generated", "must contain at least one scheme")
 
    candidates = []
    for template, selected_images in candidate_inputs:
        expanded_images = _expand_candidate_images(template, selected_images)
        candidates.append(
            _CandidateScheme(
                template=template,
                selected_images=expanded_images,
                total_score=sum(_small_image_score(image) for image in expanded_images),
            )
        )
    candidate_scores = [candidate.total_score for candidate in candidates]
    logger.info(
        "得分统计: 方案数=%s, 最高分=%s, 最低分=%s",
        len(candidates),
        max(candidate_scores),
        min(candidate_scores)
    )
    highest_score = max(candidate_scores)
    highest_score_template_displays = list(
        dict.fromkeys(
            candidate.log_display
            for candidate in candidates
            if candidate.total_score == highest_score
        )
    )
    logger.info(
        "最高分模板组合: [%s]",
        ", ".join(highest_score_template_displays),
    )

    if not candidates:
        raise InputDataError("candidates", "generated", "must contain at least one scheme")

    ranked = _CandidateScheme.rank(candidates)
    if scheme_rank > len(ranked):
        raise InputDataError(
            "scheme_rank",
            "scheme_rank",
            "must not exceed candidate count",
            scheme_rank,
        )
    selected_candidate = ranked[scheme_rank - 1]
    logger.info(
        "最终方案[%s]: %s | score=%s | images=[%s]",
        scheme_rank,
        selected_candidate.log_display,
        selected_candidate.total_score,
        selected_candidate.image_log_display,
    )

    lineage = ImageLineage(
        stitching_scheme=_instantiate_stitching_scheme(selected_candidate, rule100_config),
        main_groove_scheme=_instantiate_main_groove_scheme(rule101_config),
        decoration_scheme=_instantiate_decoration_scheme(rule102_config),
    )
    _log_lineage_detail(lineage)

    big_image.lineage = lineage

    return big_image
