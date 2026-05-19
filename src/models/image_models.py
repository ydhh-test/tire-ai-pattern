# ============================================================
# 图像模型 - 节点层
#
# 包含：
#   - ImageMeta / ImageBiz（图像元信息/业务信息）
#   - RuleEvaluation / ImageEvaluation（规则评估结果）
#   - BaseImage / SmallImage / BigImage（图像基类及子类）
#   - ImageScore / ImageLineage（大图评分/血缘）
#
# 注意：
#   - RuleEvaluation / ImageEvaluation 需开启 validate_assignment
#   - 使用 from __future__ import annotations 支持前向引用
# ============================================================

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator

from .enums import LevelEnum, RegionEnum, SourceTypeEnum, ImageModeEnum, ImageFormatEnum
from .rule_models import BaseRuleConfig, BaseRuleFeature, BaseRuleScore
from .scheme_models import StitchingScheme, MainGrooveScheme, DecorationScheme


# ===================== 图像元信息 =====================

class ImageMeta(BaseModel):
    """
    图像元信息

    描述图像本身的物理属性，不包含业务含义。
    """

    width: int = Field(ge=1, description="图像宽度(像素)，必须>=1")
    height: int = Field(ge=1, description="图像高度(像素)，必须>=1")
    channels: int = Field(ge=1, le=4, description="通道数，1~4")
    mode: ImageModeEnum = Field(description="图像颜色模式")
    format: ImageFormatEnum = Field(description="图像格式")
    size: int = Field(ge=0, description="文件大小(字节)")

    @model_validator(mode="after")
    def _validate_dimensions(self) -> ImageMeta:
        """私有校验：尺寸合理性检查"""
        if self.width > 10000 or self.height > 10000:
            raise ValueError("图像尺寸超过上限10000像素")
        return self


# ===================== 图像业务信息 =====================

class ImageBiz(BaseModel):
    """
    图像业务信息

    描述图像的业务属性：层级（小图/大图）、区域、来源类型。
    """

    level: LevelEnum = Field(description="图像层级：小图/大图")
    region: Optional[RegionEnum] = Field(default=None, description="区域：side/center，原始数据时填写")
    source_type: SourceTypeEnum = Field(default=SourceTypeEnum.ORIGINAL, description="来源类型")
    inherit_from: Optional[str] = Field(default=None, description="继承自哪个rib_name")

    @model_validator(mode="after")
    def _validate_region_for_original(self) -> ImageBiz:
        """私有校验：原始数据必须有区域信息"""
        if self.source_type == SourceTypeEnum.ORIGINAL and self.region is None:
            raise ValueError("原始数据必须指定region")
        return self

    @model_validator(mode="after")
    def _validate_inherit_has_reference(self) -> ImageBiz:
        """私有校验：继承来源必须有inherit_from"""
        if self.source_type == SourceTypeEnum.INHERIT and self.inherit_from is None:
            raise ValueError("继承来源必须指定inherit_from")
        return self


# ===================== 规则评估结果 =====================

class RuleEvaluation(BaseModel):
    """
    单条规则的评估结果

    封装单个规则的完整评估信息：配置、特征、评分。
    feature和score在运行时填充。
    """

    model_config = ConfigDict(validate_assignment=True)  # 允许运行时填充

    name: str = Field(description="规则名称")
    config: BaseRuleConfig = Field(description="规则配置")
    feature: Optional[BaseRuleFeature] = Field(default=None, description="规则特征，运行时填充")
    score: Optional[BaseRuleScore] = Field(default=None, description="规则评分，运行时填充")

    @model_validator(mode="after")
    def _validate_name_consistency(self) -> RuleEvaluation:
        """校验：如果填充了feature/score，name必须一致"""
        if self.feature is not None and self.feature.name != self.name:
            raise ValueError(f"feature.name ({self.feature.name}) != rule name ({self.name})")
        if self.score is not None and self.score.name != self.name:
            raise ValueError(f"score.name ({self.score.name}) != rule name ({self.name})")
        return self


class ImageEvaluation(BaseModel):
    """
    图像评估结果

    包含所有规则的评估列表和当前总分。
    通过name关联config/feature/score，避免列表索引错位。
    """

    model_config = ConfigDict(validate_assignment=True)  # 允许运行时填充

    rules: List[RuleEvaluation] = Field(default_factory=list, description="规则评估列表")
    current_score: int = Field(default=0, description="当前得分，所有规则评分汇总后填充", ge=0)

    def get_rule(self, name: str) -> Optional[RuleEvaluation]:
        """根据规则名获取评估结果"""
        for r in self.rules:
            if r.name == name:
                return r
        return None

    def set_feature(self, name: str, feature: BaseRuleFeature) -> None:
        """设置规则特征"""
        for r in self.rules:
            if r.name == name:
                r.feature = feature
                return
        raise ValueError(f"规则 {name} 不存在")

    def set_score(self, name: str, score: BaseRuleScore) -> None:
        """设置规则评分"""
        for r in self.rules:
            if r.name == name:
                r.score = score
                self._recalculate_total()
                return
        raise ValueError(f"规则 {name} 不存在")

    def _recalculate_total(self) -> None:
        """重新计算总分"""
        self.current_score = sum(
            r.score.score for r in self.rules
            if r.score is not None and r.score.score is not None
        )

    @model_validator(mode="after")
    def _validate_unique_names(self) -> ImageEvaluation:
        """私有校验：规则名称不能重复"""
        names = [r.name for r in self.rules]
        if len(names) != len(set(names)):
            raise ValueError("规则名称不能重复")
        return self


# ===================== 图像基类 =====================

class BaseImage(BaseModel):
    """
    图像基类

    封装图像的四个核心维度：
    - image_base64: 图像原始数据
    - meta: 图像元信息（宽高、通道等）
    - biz: 业务信息（层级、区域等）
    - evaluation: 评估结果（运行时计算后填充）

    子类：SmallImage（小图）、BigImage（大图）
    """

    image_base64: str = Field(description="图像base64，含data:image/*;base64,前缀")
    meta: ImageMeta = Field(description="图像元信息（宽高、通道等）")
    biz: ImageBiz = Field(description="业务信息（层级、区域、来源标记）")
    evaluation: Optional[ImageEvaluation] = Field(default=None, description="评估结果，运行时计算后填充")

    @model_validator(mode="after")
    def _validate_base64_format(self) -> BaseImage:
        """私有校验：base64格式检查"""
        if not self.image_base64.startswith("data:image/"):
            raise ValueError("image_base64必须包含data:image/*;base64,前缀")
        return self


# ===================== 小图 =====================

class SmallImage(BaseImage):
    """
    小图

    直接继承BaseImage，无额外字段。
    小图是大图的组成单元，来源于用户输入或大图拆分。
    """
    pass


# ===================== 大图评分 =====================

class ImageScore(BaseModel):
    """
    大图单条评分

    仅用于与前端格式对齐，前端不传。
    """

    compliance: int = Field(description="合规性得分")


# ===================== 大图血缘信息 =====================

class ImageLineage(BaseModel):
    """
    大图血缘信息

    用于复现和追溯大图生成过程。
    包含拼接方案、主沟花纹方案、装饰花纹方案。
    """

    stitching_scheme: StitchingScheme = Field(description="拼接方案")
    main_groove_scheme: MainGrooveScheme = Field(description="主沟花纹方案")
    decoration_scheme: DecorationScheme = Field(description="装饰花纹方案")
    meta: Optional[ImageMeta] = Field(default=None, description="大图meta备份，用于独立复现")


# ===================== 大图 =====================

class BigImage(BaseImage):
    """
    大图

    继承BaseImage，额外扩展：
    1. scores：大图评分列表（后端内部使用，与前端格式对齐）
    2. lineage：大图血缘信息（用于追溯、复现大图生成过程）
    """

    scores: Optional[List[ImageScore]] = Field(default=None, description="大图评分列表，后端内部使用")
    lineage: Optional[ImageLineage] = Field(default=None, description="大图血缘信息，可无")