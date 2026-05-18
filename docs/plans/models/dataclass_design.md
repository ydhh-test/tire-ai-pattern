# AI 执行指南：基于 dataclass_design_v2.md 生成代码

## 1. 执行前置条件

### 1.1 必读文档顺序
```
1. docs/ai_context_entrypoint.md（入口文档）
2. docs/project_coding_standards_agent.md（执行短规则）
3. docs/project_coding_standards.md（完整规范）
4. 本文档（dataclass_design.md）★
```

### 1.2 文档优先级
发生冲突时：
```
本文档（dataclass_design.md，最高）
  > project_coding_standards.md
  > project_coding_standards_agent.md
```

### 1.3 执行确认清单
开始写代码前，AI 必须确认：
- [ ] 已理解数据结构层级（接入层 → 节点层 → 规则层 → 基础层）
- [ ] 已理解类继承/组合关系
- [ ] 已理解模板类与运行时类的分离机制
- [ ] 已理解 Feature/Score 注册机制
- [ ] 已理解 Pipeline 流程（1-4）
- [ ] 已明确本次任务涉及哪些类/文件

---

### 1.4 数据结构层级说明

本项目数据结构分为四层：

```
┌─────────────────────────────────────────────────────────────┐
│                      数据结构层级                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │  接入层   │ → │  节点层   │ → │  规则层   │ → │  基础层   │ │
│  │TireStruct│   │  Images  │   │  Rules   │   │Algorithms│ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↕ 对应
┌─────────────────────────────────────────────────────────────┐
│                      被调用层级                               │
│    入参/出参       实例化/传递    规则执行     算法调用       │
└─────────────────────────────────────────────────────────────┘
```

**层级职责：**
- **接入层**：统一入口/出口，封装所有输入输出（TireStruct）
- **节点层**：图像实例化、血缘管理、评估结果存储（SmallImage、BigImage、ImageEvaluation等）
- **规则层**：规则配置、特征提取、评分计算（RuleConfig、RuleFeature、RuleScore）
- **基础层**：底层算法实现（不属于 src/models，属于业务逻辑层）

---

### 1.5 类继承/组合关系图

```
                    TireStruct (接入层)
                         │
            ┌────────────┼────────────┐
            │            │            │
      SmallImage    BigImage    List[BaseRuleConfig]
            │            │
            └─────┬──────┘
                  │(继承)
             BaseImage (节点层)
                  │
        ┌─────────┼─────────┐
        │         │         │
    image_base64  meta      biz      evaluation
   (str)       (ImageMeta)(ImageBiz)(ImageEvaluation)
                  │         │            │
                  ▼         ▼            ▼
              元信息字段   业务字段    ┌─────────┬─────────┐
              (width等)  (level等)   feature   score
                                         │         │
                                         ▼         ▼
                                    List[RuleNFeature]
                                    List[RuleNScore]

说明：
- 实线 = 继承关系
- 缩进 = 字段包含关系（Pydantic 模型字段）
- TireStruct 开启 validate_assignment，支持运行时修改
- 其他类默认不可变，如需可变请自行添加 ConfigDict(validate_assignment=True)
```

---

### 1.6 Pipeline 流程图

```
Pipeline-1: 小图输入 → 大图生成
    输入: small_images + rules_config
    Node1: 小图评估
    Node2: 拼接方案生成
    Node3: 拼接大图
    Node4: 大图评估
    Node5: 几何合理性业务评分
    输出: big_image

Pipeline-2: 大图输入 → 拼接大图（复用Pipeline-1部分节点）
    输入: big_image + rules_config
    Node3: 拼接大图
    输出: big_image

Pipeline-3: 大图输入 → 业务评分（复用Pipeline-1部分节点）
    输入: big_image + rules_config
    Node5: 几何合理性业务评分
    输出: big_image (含evaluation)

Pipeline-4: 大图拆分
    输入: big_image + rules_config
    Node6: 大图拆分
    输出: small_images

数据流转:
    Pipeline-1 → Pipeline-3 → Pipeline-4
    Pipeline-2 → Pipeline-3 → Pipeline-4
```

**字段标注说明：**
- TireStruct 字段注释中的 `👉 入参` / `👉 出参` 标记对应上述 Pipeline

---

## 2. 文件组织规范

### 2.1 目录结构（5个文件）
```
src/models/
├── __init__.py           # 空文件，仅作为包标记
├── enums.py              # 所有枚举（7个枚举类）
├── tire_struct.py        # 接入层（TireStruct）
├── image_models.py       # 节点层全部
│                         #   BaseImage / SmallImage / BigImage
│                         #   ImageMeta / ImageBiz
│                         #   ImageEvaluation / RuleEvaluation
│                         #   ImageScore / ImageLineage
├── scheme_models.py      # 方案层全部
│                         #   拼接模板类（frozen）+ 拼接运行时类
│                         #   主沟花纹方案
│                         #   装饰花纹方案
└── rule_models.py        # 规则层全部
                          #   BaseRuleConfig + RuleNConfig（22个）
                          #   BaseRuleFeature + RuleNFeature（22个）
                          #   BaseRuleScore + RuleNScore（22个）
                          #   注册表 + 装饰器
```

**导入方式：**
所有导入直接指向文件，不通过 __init__.py：
```python
from src.models.enums import LevelEnum, RegionEnum
from src.models.tire_struct import TireStruct
from src.models.image_models import SmallImage, BigImage
from src.models.rule_models import Rule8Config, get_feature_class
```

### 2.2 文件职责边界
| 文件 | 内容 | 行数预估 |
|------|------|---------|
| enums.py | LevelEnum, RegionEnum, SourceTypeEnum, ImageModeEnum, ImageFormatEnum, StitchingSchemeName, RibOperation | ~80行 |
| tire_struct.py | TireStruct | ~60行 |
| image_models.py | BaseImage, SmallImage, BigImage, ImageMeta, ImageBiz, ImageEvaluation, RuleEvaluation, ImageScore, ImageLineage | ~200行 |
| scheme_models.py | 拼接模板类（6个）+ 运行时类（3个）+ 主沟方案（3个）+ 装饰方案（3个） | ~400行 |
| rule_models.py | BaseRule*3 + RuleN*66 + 注册表 | ~800行 |

---

## 3. 代码生成步骤

### 3.1 第一步：生成枚举（enums.py）
```python
# 执行要点：
# 1. 所有枚举继承 str, Enum
# 2. 每个枚举值必须有注释
# 3. 枚举命名以 Enum 结尾

from enum import Enum


class LevelEnum(str, Enum):
    """图像层级枚举"""
    SMALL = "small"  # 小图
    BIG = "big"      # 大图


class RegionEnum(str, Enum):
    """实际区域类型枚举"""
    SIDE = "side"      # 侧边区域
    CENTER = "center"  # 中心区域


class SourceTypeEnum(str, Enum):
    """数据来源类型枚举"""
    ORIGINAL = "original"  # 原始输入
    INHERIT = "inherit"    # 继承自其他RIB
    CONCAT = "concat"      # 拼接生成


class ImageModeEnum(str, Enum):
    """图像颜色模式枚举"""
    GRAY = "GRAY"    # 灰度图
    RGB = "RGB"      # RGB三通道
    RGBA = "RGBA"    # RGBA四通道


class ImageFormatEnum(str, Enum):
    """图像格式枚举"""
    JPG = "jpg"  # JPEG格式
    PNG = "png"  # PNG格式
    BMP = "bmp"  # BMP格式
    RAW = "raw"  # 原始数据


class StitchingSchemeName(str, Enum):
    """拼接方案名称枚举"""
    SYMMETRY_0 = "symmetry_0"          # 无对称
    SYMMETRY_1 = "symmetry_1"          # 中心旋转180°对称
    CONTINUITY_0 = "continuity_0"      # RIB2-3-4中间全连续
    CONTINUITY_1 = "continuity_1"      # 其他连续性
    __CONCATENATE_0 = "_concatenate_0"  # 内部：两张图拼接


class RibOperation(str, Enum):
    """RIB原子操作枚举"""
    NONE = ""                               # 无操作
    FLIP_LR = "fliplr"                      # 左右对称
    FLIP = "flip"                           # 旋转180度
    LEFT_FLIP_LR = "left_fliplr"            # 左半左右对称覆盖右侧
    LEFT_FLIP = "left_flip"                 # 左半旋转180覆盖右侧
    RESIZE_HORIZONTAL_2X = "resize_horizontal_2x"      # 横向拉伸2倍
    LEFT = "left"                           # 截取左边
    RIGHT = "right"                         # 截取右边
    RESIZE_HORIZONTAL_1_5X = "resize_horizontal_1.5x"  # 横向拉伸1.5倍
    RESIZE_HORIZONTAL_3X = "resize_horizontal_3x"      # 横向拉伸3倍
    LEFT_2_3 = "left_2/3"                   # 截取左2/3
    RIGHT_2_3 = "right_2/3"                 # 截取右2/3
    LEFT_1_3 = "left_1/3"                   # 截取左1/3
    RIGHT_1_3 = "right_1/3"                 # 截取右1/3
    __RESIZE_AS_FIRST_RIB = "_resize_as_first_rib"  # 内部：图片大小向第一张图对齐
```

### 3.2 第二步：生成 TireStruct（tire_struct.py）
```python
# 执行要点：
# 1. TireStruct 必须开启 validate_assignment=True
# 2. 每个字段注释必须标注在哪个Pipeline生效（入参/出参）
# 3. model_validator 必须按设计文档要求编写

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator


class TireStruct(BaseModel):
    """
    轮胎图像全流程统一数据结构

    所有Pipeline的输入和输出都使用这个结构。
    每个字段标注了在哪个流程生效、是入参还是出参。
    开启validate_assignment确保运行时赋值的合法性。
    """

    model_config = ConfigDict(validate_assignment=True)

    # ===================== 图像数据 =====================
    # 小图列表
    # 👉 入参：仅Pipeline-1使用
    # 👉 出参：仅Pipeline-4输出
    small_images: List["SmallImage"] = Field(default_factory=list, description="小图列表")

    # 大图（包含血缘、特征、评分）
    # 👉 入参：Pipeline-2 / Pipeline-3 / Pipeline-4使用
    # 👉 出参：Pipeline-1 / Pipeline-2 / Pipeline-3输出
    big_image: Optional["BigImage"] = Field(default=None, description="大图，含血缘/特征/评分")

    # ===================== 业务规则与配置 =====================
    # 规则配置列表（评分规则/拆分规则/拼接规则）
    # 👉 入参：Pipeline-1 / Pipeline-3 / Pipeline-4使用
    rules_config: List["BaseRuleConfig"] = Field(default_factory=list, description="规则配置列表")

    # 方案排名（第几名方案）
    # 👉 入参：仅Pipeline-1使用
    scheme_rank: Optional[int] = Field(default=None, description="方案排名，从1开始")

    # ===================== 执行结果与状态 =====================
    # 调试开关
    is_debug: bool = Field(default=False, description="调试开关，开启后输出可视化中间结果")

    # 执行成功/失败标志
    # 👉 出参：所有Pipeline统一输出
    flag: Optional[bool] = Field(default=None, description="执行成功/失败标志")

    # 错误/拒绝原因
    # 👉 出参：所有Pipeline统一输出
    err_msg: Optional[str] = Field(default=None, description="错误或拒绝原因")

    @model_validator(mode="after")
    def _validate_images_required(self) -> "TireStruct":
        """私有校验：必须有小图或大图至少一种"""
        has_small = len(self.small_images) > 0
        has_big = self.big_image is not None
        if not has_small and not has_big:
            raise ValueError("必须输入小图或大图，流程无法执行")
        return self

    @model_validator(mode="after")
    def _validate_scheme_rank(self) -> "TireStruct":
        """私有校验：方案排名必须>=1"""
        if self.scheme_rank is not None and self.scheme_rank < 1:
            raise ValueError("方案排名必须>=1")
        return self
```

### 3.3 第三步：生成图像模型（image_models.py）
```python
# 执行要点：
# 1. 所有字段必须显式声明类型
# 2. 可变默认值使用 Field(default_factory=...)
# 3. 私有校验方法以 _validate_ 开头，使用 @model_validator
# 4. 每个 model_validator 必须返回 self
# 5. ImageEvaluation 需要开启 validate_assignment（因为有 set_feature/set_score 方法）

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .enums import LevelEnum, RegionEnum, SourceTypeEnum, ImageModeEnum, ImageFormatEnum


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
    def _validate_dimensions(self) -> "ImageMeta":
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
    def _validate_region_for_original(self) -> "ImageBiz":
        """私有校验：原始数据必须有区域信息"""
        if self.source_type == SourceTypeEnum.ORIGINAL and self.region is None:
            raise ValueError("原始数据必须指定region")
        return self

    @model_validator(mode="after")
    def _validate_inherit_has_reference(self) -> "ImageBiz":
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
    config: "BaseRuleConfig" = Field(description="规则配置")
    feature: Optional["BaseRuleFeature"] = Field(default=None, description="规则特征，运行时填充")
    score: Optional["BaseRuleScore"] = Field(default=None, description="规则评分，运行时填充")

    @model_validator(mode="after")
    def _validate_name_consistency(self) -> "RuleEvaluation":
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

    def set_feature(self, name: str, feature: "BaseRuleFeature") -> None:
        """设置规则特征"""
        for r in self.rules:
            if r.name == name:
                r.feature = feature
                return
        raise ValueError(f"规则 {name} 不存在")

    def set_score(self, name: str, score: "BaseRuleScore") -> None:
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
            if r.score is not None
        )

    @model_validator(mode="after")
    def _validate_unique_names(self) -> "ImageEvaluation":
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
    def _validate_base64_format(self) -> "BaseImage":
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

    stitching_scheme: "StitchingScheme" = Field(description="拼接方案")
    main_groove_scheme: "MainGrooveScheme" = Field(description="主沟花纹方案")
    decoration_scheme: "DecorationScheme" = Field(description="装饰花纹方案")
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
```

### 3.4 第四步：生成方案模型（scheme_models.py）

#### 3.4.0 模板实例化流程

在生成方案模型前，必须理解模板类与运行时类的分离机制：

```
模板类（frozen=True，只定义规则）
    │
    ▼
TemplateInstantiator.instantiate(template, images)
    * 接收 StitchingTemplate + 实际图像数据
    * 遍历 rib_template_list
    * 遇到 sub_template_name 递归展开
    * 输出 List[RibSchemeImpl]
    │
    ▼
运行时类（存储实际数据）
```

**关键说明：**
- **模板类**：静态定义，`frozen=True`，不可修改，只定义拼接规则
- **运行时类**：存储实际数据，`validate_assignment=True`，支持运行时填充
- **展开机制**：通过 `sub_template_name` 字段递归调用子模板

#### 3.4.1 代码生成

```python
# 执行要点：
# 1. 模板类必须设置 frozen=True
# 2. 运行时类必须开启 validate_assignment=True
# 3. 模板类不存运行时数据，只定义规则
# 4. 子模板展开通过 sub_template_name 实现

from typing import Optional, List, Tuple
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .enums import RegionEnum, SourceTypeEnum, StitchingSchemeName, RibOperation


# ============================================================
# 第一部分：拼接模板类（frozen=True）
# ============================================================

class RibTemplate(BaseModel):
    """
    RIB模板定义

    只定义操作序列模板，不存运行时数据。
    """

    model_config = ConfigDict(frozen=True)

    region: Optional[RegionEnum] = Field(default=None, description="来源区域")
    source_type: SourceTypeEnum = Field(default=SourceTypeEnum.ORIGINAL, description="来源类型")
    inherit_from: Optional[str] = Field(default=None, description="继承自哪个rib_name")
    operation_template: Tuple[RibOperation, ...] = Field(description="操作序列模板")
    rib_name: Optional[str] = Field(default=None, description="RIB名称，如rib1，最外层必填")
    sub_template_name: Optional[StitchingSchemeName] = Field(default=None, description="子模板名称")


class StitchingTemplate(BaseModel):
    """
    拼接模板基类

    静态配置模板，只定义拼接规则，不存合成图片。
    子类：Symmetry0、Symmetry1、Continuity0、_Concatenate0等。
    """

    model_config = ConfigDict(frozen=True)

    name: StitchingSchemeName = Field(description="拼接方案名称枚举")
    description: str = Field(description="方案描述")
    rib_number: int = Field(description="RIB数量")
    mode: str = Field(description="模式")
    rib_template_list: List[RibTemplate] = Field(description="RIB模板定义列表")
    post_processing: Optional[Tuple[RibOperation, ...]] = Field(default=None, description="后处理操作序列")


class Symmetry0(StitchingTemplate):
    """拼接模板：symmetry_0 - 5个花纹RIB无对称原则"""

    name: StitchingSchemeName = StitchingSchemeName.SYMMETRY_0
    description: str = "花纹RIB无对称原则"
    rib_number: int = 5
    mode: str = "symmetry"
    rib_template_list: List[RibTemplate] = [
        RibTemplate(region=RegionEnum.SIDE, operation_template=(RibOperation.NONE,), rib_name="rib1"),
        RibTemplate(region=RegionEnum.CENTER, operation_template=(RibOperation.NONE,), rib_name="rib2"),
        RibTemplate(region=RegionEnum.CENTER, operation_template=(RibOperation.NONE,), rib_name="rib3"),
        RibTemplate(region=RegionEnum.CENTER, operation_template=(RibOperation.NONE,), rib_name="rib4"),
        RibTemplate(region=RegionEnum.SIDE, operation_template=(RibOperation.NONE,), rib_name="rib5"),
    ]


class Symmetry1(StitchingTemplate):
    """拼接模板：symmetry_1 - 花纹RIB中心对称（左侧旋转180度是右侧）"""

    name: StitchingSchemeName = StitchingSchemeName.SYMMETRY_1
    description: str = "花纹RIB中心对称（左侧旋转180度是右侧）"
    rib_number: int = 5
    mode: str = "symmetry"
    rib_template_list: List[RibTemplate] = [
        RibTemplate(region=RegionEnum.SIDE, operation_template=(RibOperation.NONE,), rib_name="rib1"),
        RibTemplate(region=RegionEnum.CENTER, operation_template=(RibOperation.NONE,), rib_name="rib2"),
        RibTemplate(region=RegionEnum.CENTER, operation_template=(RibOperation.LEFT_FLIP,), rib_name="rib3"),
        RibTemplate(region=RegionEnum.CENTER, source_type=SourceTypeEnum.INHERIT, inherit_from="rib2",
                    operation_template=(RibOperation.FLIP,), rib_name="rib4"),
        RibTemplate(region=RegionEnum.SIDE, source_type=SourceTypeEnum.INHERIT, inherit_from="rib1",
                    operation_template=(RibOperation.FLIP,), rib_name="rib5"),
    ]


# class _Concatenate0(StitchingTemplate):
#     """拼接模板：_concatenate_0 - 用于两张图像的拼接（供内部使用）"""

#     name: StitchingSchemeName = StitchingSchemeName._CONCATENATE_0
#     description: str = "两张图合并为1张，仅供内部使用"
#     rib_number: int = 2
#     mode: str = "concatenate"
#     rib_template_list: List[RibTemplate] = [
#         RibTemplate(source_type=SourceTypeEnum.INHERIT, inherit_from="rib2",
#                     operation_template=(RibOperation.RESIZE_HORIZONTAL_3X, RibOperation.RIGHT_1_3)),
#         RibTemplate(source_type=SourceTypeEnum.INHERIT, inherit_from="rib4",
#                     operation_template=(RibOperation.RESIZE_HORIZONTAL_3X, RibOperation.LEFT_1_3)),
#     ]
#     post_processing: Tuple[RibOperation, ...] = (RibOperation._RESIZE_AS_FIRST_RIB,)


# class Continuity0(StitchingTemplate):
#     """拼接模板：continuity_0 - RIB2-RIB3-RIB4中间三条全连续，边缘独立"""

#     name: StitchingSchemeName = StitchingSchemeName.CONTINUITY_0
#     description: str = "RIB2-RIB3-RIB4中间全连续，边缘独立"
#     rib_number: int = 5
#     mode: str = "continuity"
#     matching_rule_names: Tuple[str, ...] = tuple()
#     rib_template_list: List[RibTemplate] = [
#         RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.NONE,), rib_name="rib1"),
#         RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.RESIZE_HORIZONTAL_1_5X, RibOperation.LEFT_2_3), rib_name="rib2"),
#         RibTemplate(source_type=SourceTypeEnum.CONCAT, sub_template_name=StitchingSchemeName._CONCATENATE_0, rib_name="rib3"),
#         RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.RESIZE_HORIZONTAL_1_5X, RibOperation.RIGHT_2_3), rib_name="rib4"),
#         RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.NONE,), rib_name="rib5"),
#     ]

class Continuity0(StitchingTemplate):
    """拼接模板：continuity_0 - RIB2-RIB3连续，边缘独立"""

    name: StitchingSchemeName = StitchingSchemeName.CONTINUITY_0
    description: str = "RIB2-RIB3连续，边缘独立"
    rib_number: int = 5
    mode: str = "continuity"
    matching_rule_names: Tuple[str, ...] = tuple()
    rib_template_list: List[RibTemplate] = [
        RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.NONE,), rib_name="rib1"),
        RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.RESIZE_HORIZONTAL_2X, RibOperation.LEFT), rib_name="rib2"),
        RibTemplate(
            source_type=SourceTypeEnum.INHERIT, operation_template=(RibOperation.RESIZE_HORIZONTAL_2X, RibOperation.RIGHT), rib_name="rib3",   inherit_from="rib2",),
        RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.NONE,), rib_name="rib4"),
        RibTemplate(source_type=SourceTypeEnum.ORIGINAL, operation_template=(RibOperation.NONE,), rib_name="rib5"),
    ]


# ============================================================
# 第二部分：拼接运行时类（validate_assignment=True）
# ============================================================

class RibSchemeImpl(BaseModel):
    """
    RIB拼接方案实现实体（运行时）

    由TemplateInstantiator从StitchingTemplate实例化而来。
    包含操作序列、执行结果图片、节距数等运行时信息。
    """

    model_config = ConfigDict(validate_assignment=True)

    region: Optional[RegionEnum] = Field(default=None, description="来源区域")
    source_type: SourceTypeEnum = Field(description="来源类型")
    inherit_from: Optional[str] = Field(default=None, description="继承自哪个rib_name")
    operations: Tuple[RibOperation, ...] = Field(description="操作序列")
    rib_name: Optional[str] = Field(default=None, description="RIB名称")
    is_nested: bool = Field(default=False, description="是否嵌套RIB")

    # ---- 运行时填充字段 ----
    small_image: Optional[str] = Field(default=None, description="小图base64")
    num_pitchs: Optional[int] = Field(default=None, description="节距数量")
    rib_height: Optional[int] = Field(default=None, description="RIB纵向图高度")
    rib_width: Optional[int] = Field(default=None, description="RIB纵向图宽度")
    rib_image: Optional[str] = Field(default=None, description="操作后的纵向图base64")

    @model_validator(mode="after")
    def _validate_name_required_for_top_level(self) -> "RibSchemeImpl":
        """私有校验：最外层RIB必须有名称"""
        if not self.is_nested and self.rib_name is None:
            raise ValueError("最外层RIB必须有rib_name")
        return self

    @model_validator(mode="after")
    def _validate_inherit_has_reference(self) -> "RibSchemeImpl":
        """私有校验：继承来源必须有inherit_from"""
        if self.source_type == SourceTypeEnum.INHERIT and self.inherit_from is None:
            raise ValueError("继承来源必须指定inherit_from")
        return self


class StitchingSchemeAbstract(BaseModel):
    """拼接方案摘要 - 人类可读的方案描述信息"""

    name: StitchingSchemeName = Field(description="方案名称枚举")
    description: str = Field(description="方案描述")
    rib_number: int = Field(description="RIB数量")


class StitchingScheme(BaseModel):
    """
    大图拼接完整方案（运行时）

    由TemplateInstantiator生成，存储实际执行数据和结果。
    """

    stitching_scheme_abstract: StitchingSchemeAbstract = Field(description="拼接方案摘要")
    ribs_scheme_implementation: List[RibSchemeImpl] = Field(default_factory=list, description="RIB拼接方案实现列表")


# ============================================================
# 第三部分：主沟花纹方案
# ============================================================

class MainGrooveImpl(BaseModel):
    """主沟花纹实现实体（程序使用）- 存储主沟的图像数据和尺寸信息"""

    groove_image: Optional[str] = Field(default=None, description="主沟图base64")
    groove_width: int = Field(description="主沟宽度(像素)")
    groove_height: int = Field(description="主沟高度(像素)")


class MainGrooveSchemeAbstract(BaseModel):
    """主沟方案摘要（给人看）"""

    name: str = Field(description="方案名称")
    description: Optional[str] = Field(default=None, description="方案描述")
    groove_number: int = Field(description="主沟数量")


class MainGrooveScheme(BaseModel):
    """主沟花纹完整方案 - 包含方案摘要和实现列表"""

    main_groove_scheme_abstract: Optional[MainGrooveSchemeAbstract] = Field(default=None, description="主沟方案摘要")
    main_groove_implementation: List[MainGrooveImpl] = Field(default_factory=list, description="主沟实现列表")


# ============================================================
# 第四部分：装饰花纹方案
# ============================================================

class DecorationImpl(BaseModel):
    """装饰花纹实现实体（程序使用）- 存储装饰花纹的图像数据、尺寸和透明度"""

    decoration_image: Optional[str] = Field(default=None, description="装饰花纹图base64")
    decoration_width: int = Field(description="装饰宽度(像素)")
    decoration_height: int = Field(description="装饰高度(像素)")
    decoration_opacity: int = Field(ge=0, le=255, description="边缘花纹透明度")


class DecorationSchemeAbstract(BaseModel):
    """装饰方案摘要（给人看）"""

    name: str = Field(description="方案名称")
    description: Optional[str] = Field(default=None, description="方案描述")


class DecorationScheme(BaseModel):
    """装饰花纹完整方案 - 包含方案摘要和实现列表"""

    decoration_scheme_abstract: Optional[DecorationSchemeAbstract] = Field(default=None, description="装饰方案摘要")
    decoration_implementation: List[DecorationImpl] = Field(default_factory=list, description="装饰实现列表")
```

### 3.5 第五步：生成规则模型（rule_models.py）

#### 3.5.0 RuleRunner 职责说明

在生成规则模型前，必须理解规则执行机制。RuleRunner 是规则执行调度器（非数据类），职责如下：

**核心定位：**
- 集成 rule_name、RuleConfig、RuleFeature、RuleScore 及对应执行方法
- 不属于 src/models，属于业务逻辑层

**核心方法：**
1. `exec_feature(image, config) -> RuleNFeature`
   - 接收图像和配置，执行特征提取
   - 内部调用基础算法函数（显式传参，不塞对象）
   - 返回 Feature 对象

2. `exec_score(config, feature) -> RuleNScore`
   - 只依赖 config + feature，不依赖 image
   - 支持传入新 config 重新算分，不重跑 feature
   - 返回 Score 对象

**自动装载机制：**
- 通过装饰器/注册表自动发现规则类
- 无需硬编码 if/elif 或维护函数列表
- 新增规则只需写 Config/Feature/Score 三个类

**职责边界：**
- **规则层**：只负责计算，返回 Feature/Score
- **节点层**：负责将结果写回 SmallImage/BigImage.evaluation
- **feature 和 score 计算必须完全独立分开**

#### 3.5.1 代码生成

```python
# 执行要点：
# 1. Config 类继承 BaseRuleConfig
# 2. Feature 类必须使用 @register_rule_feature 装饰器
# 3. Score 类必须使用 @register_rule_score 装饰器
# 4. name 属性从类名自动提取，不要手动定义
# 5. 所有规则放在同一个文件，按 Rule1-Rule22 顺序排列

from typing import Optional, List, Dict, Type
from pydantic import BaseModel, Field


# ============================================================
# 第一部分：注册机制
# ============================================================

_FEATURE_REGISTRY: Dict[str, Type["BaseRuleFeature"]] = {}
_SCORE_REGISTRY: Dict[str, Type["BaseRuleScore"]] = {}


def register_rule_feature(cls: Type["BaseRuleFeature"]) -> Type["BaseRuleFeature"]:
    """注册规则特征类到全局注册表"""
    _FEATURE_REGISTRY[cls.__name__] = cls
    return cls


def register_rule_score(cls: Type["BaseRuleScore"]) -> Type["BaseRuleScore"]:
    """注册规则评分类到全局注册表"""
    _SCORE_REGISTRY[cls.__name__] = cls
    return cls


def get_feature_class(name: str) -> Type["BaseRuleFeature"]:
    """根据规则名获取特征类"""
    return _FEATURE_REGISTRY.get(f"{name}Feature")


def get_score_class(name: str) -> Type["BaseRuleScore"]:
    """根据规则名获取评分类"""
    return _SCORE_REGISTRY.get(f"{name}Score")


# ============================================================
# 第二部分：基类定义
# ============================================================

class BaseRuleConfig(BaseModel):
    """
    规则配置基类

    所有规则配置的公共基类，定义通用字段。
    子类继承并扩展具体阈值字段。
    name属性自动从类名提取（如Rule8Config → rule8）。
    """

    description: str = Field(description="规则描述")
    max_score: int = Field(ge=0, description="最大可得分")
    activation_node_name: str = Field(description="生效节点名称")

    @property
    def name(self) -> str:
        """规则名称，从类名自动提取（如Rule8Config → rule8）"""
        return self.__class__.__name__.lower().replace("config", "")


class BaseRuleFeature(BaseModel):
    """
    规则特征基类

    所有规则特征的公共基类。
    name属性自动从类名提取（如Rule8Feature → rule8）。

    注意：
    - Feature只包含用于打分的特征数据，不能访问图片
    - 支持debug模式，输出可视化图片（vis_names/vis_images）
    """

    vis_names: Optional[List[str]] = Field(default=None, description="可视化名称列表，debug模式使用")
    vis_images: Optional[List[str]] = Field(default=None, description="可视化图片base64列表，debug模式使用")

    @property
    def name(self) -> str:
        """规则名称，从类名自动提取（如Rule8Feature → rule8）"""
        return self.__class__.__name__.lower().replace("feature", "")


class BaseRuleScore(BaseModel):
    """
    规则评分基类

    所有规则评分的公共基类。
    name属性自动从类名提取（如Rule8Score → rule8）。
    """

    score: int = Field(description="得分")

    @property
    def name(self) -> str:
        """规则名称，从类名自动提取（如Rule8Score → rule8）"""
        return self.__class__.__name__.lower().replace("score", "")


# ============================================================
# 第三部分：Rule1-5 横图拼接子规则
# ============================================================

class Rule1Config(BaseRuleConfig):
    """Rule1：5个花纹RIB无对称原则"""
    description: str = "5个花纹RIB无对称原则"
    max_score: int = 8
    activation_node_name: str = ""


class Rule2Config(BaseRuleConfig):
    """Rule2：中心旋转180°对称花纹"""
    description: str = "中心旋转180°对称花纹"
    max_score: int = 8
    activation_node_name: str = ""


class Rule3Config(BaseRuleConfig):
    """Rule3：中心线镜像对称"""
    description: str = "中心线镜像对称"
    max_score: int = 8
    activation_node_name: str = ""


class Rule4Config(BaseRuleConfig):
    """Rule4：中心线镜像对称可错位"""
    description: str = "中心线镜像对称可错位"
    max_score: int = 8
    activation_node_name: str = ""


class Rule5Config(BaseRuleConfig):
    """Rule5：根据用户指定的对称性进行输出"""
    description: str = "根据用户指定的对称性进行输出"
    max_score: int = 1
    activation_node_name: str = ""


@register_rule_feature
class Rule1Feature(BaseRuleFeature):
    """Rule1特征：横图拼接子规则，特征字段待业务细化"""
    pass


@register_rule_feature
class Rule2Feature(BaseRuleFeature):
    """Rule2特征：横图拼接子规则，特征字段待业务细化"""
    pass


@register_rule_feature
class Rule3Feature(BaseRuleFeature):
    """Rule3特征：横图拼接子规则，特征字段待业务细化"""
    pass


@register_rule_feature
class Rule4Feature(BaseRuleFeature):
    """Rule4特征：横图拼接子规则，特征字段待业务细化"""
    pass


@register_rule_feature
class Rule5Feature(BaseRuleFeature):
    """Rule5特征：横图拼接子规则，特征字段待业务细化"""
    pass


@register_rule_score
class Rule1Score(BaseRuleScore):
    """Rule1评分"""
    pass


@register_rule_score
class Rule2Score(BaseRuleScore):
    """Rule2评分"""
    pass


@register_rule_score
class Rule3Score(BaseRuleScore):
    """Rule3评分"""
    pass


@register_rule_score
class Rule4Score(BaseRuleScore):
    """Rule4评分"""
    pass


@register_rule_score
class Rule5Score(BaseRuleScore):
    """Rule5评分"""
    pass


# ============================================================
# 第四部分：Rule6-6A 连续性检测与拼接节距
# ============================================================

class Rule6Config(BaseRuleConfig):
    """Rule6：节距纵向关系无缝拼接/图案连续性检测"""
    description: str = "节距纵向关系无缝拼接 / 图案连续性检测"
    max_score: int = 10
    activation_node_name: str = ""


class Rule6AConfig(BaseRuleConfig):
    """Rule6A：拼接节距 - 非打分规则，后续可能摘出为新类"""
    description: str = "拼接节距"
    max_score: int = 0
    activation_node_name: str = ""
    default_stitch_count: int = Field(description="拼接次数")
    target_resolution_width: int = Field(description="目标分辨率宽度(像素)")


@register_rule_feature
class Rule6Feature(BaseRuleFeature):
    """Rule6特征：连续性检测"""
    is_continuous: bool = Field(description="是否连续")


@register_rule_feature
class Rule6AFeature(BaseRuleFeature):
    """Rule6A特征：截距数量"""
    num_pitchs: int = Field(description="节距数量")


@register_rule_score
class Rule6Score(BaseRuleScore):
    """Rule6（连续性检测）评分"""
    pass


@register_rule_score
class Rule6AScore(BaseRuleScore):
    """Rule6A（拼接节距）评分"""
    pass


# ============================================================
# 第五部分：Rule7 主沟宽度/数量（已被融入）
# ============================================================

class Rule7Config(BaseRuleConfig):
    """Rule7：主沟宽度/数量 - 现被rule1to5横图拼接、rule12/16/17连续性拼接吸收"""
    description: str = "主沟宽度/数量约束"
    max_score: int = 0
    activation_node_name: str = ""
    main_groove_width: float = Field(description="主沟宽度(像素)")
    main_groove_width_min: float = Field(description="主沟宽度下限(像素)")
    main_groove_width_max: float = Field(description="主沟宽度上限(像素)")
    main_groove_count_min: int = Field(description="主沟数量下限")
    main_groove_count_max: int = Field(description="主沟数量上限")
    preferred_groove_count: int = Field(description="优先目标数量")
    preferred_groove_ratio: float = Field(description="优先目标占比")


@register_rule_feature
class Rule7Feature(BaseRuleFeature):
    """Rule7特征：主沟宽度/数量，已被融入"""
    num_main_grooves: int = Field(description="主沟数量")
    main_groove_widths: List[float] = Field(description="主沟宽度列表")
    main_groove_positions: List[int] = Field(description="主沟位置列表")
    all_widths_in_range: bool = Field(description="所有宽度是否在范围内")
    preferred_count_hit: bool = Field(description="优先数量是否命中")


@register_rule_score
class Rule7Score(BaseRuleScore):
    """Rule7（主沟宽度/数量）评分，已被融入"""
    pass


# ============================================================
# 第六部分：Rule8 横沟数量
# ============================================================

class Rule8Config(BaseRuleConfig):
    """Rule8：横沟数量约束"""
    description: str = "横沟数量约束"
    max_score: int = 4
    activation_node_name: str = ""
    groove_width_center: float = Field(gt=0, description="center横沟宽度(像素)")
    groove_width_side: float = Field(gt=0, description="side横沟宽度(像素)")


@register_rule_feature
class Rule8Feature(BaseRuleFeature):
    """Rule8特征：横沟数量"""
    num_transverse_grooves: int = Field(ge=0, description="横沟数量")


@register_rule_score
class Rule8Score(BaseRuleScore):
    """Rule8（横沟数量）评分"""
    pass


# ============================================================
# 第七部分：Rule9-10 横向钢片（未实现）
# ============================================================

class Rule9Config(BaseRuleConfig):
    """Rule9：横向钢片数量约束（未实现）"""
    description: str = "横向钢片数量约束"
    max_score: int = 0
    activation_node_name: str = ""
    transverse_sipe_width: float = Field(description="横向钢片宽度(像素)")
    min_sipe_count_rib1_5: int = Field(description="RIB1/5钢片数量下限")
    max_sipe_count_rib1_5: int = Field(description="RIB1/5钢片数量上限")
    min_sipe_count_rib2_4: int = Field(description="RIB2/4钢片数量下限")
    max_sipe_count_rib2_4: int = Field(description="RIB2/4钢片数量上限")


class Rule10Config(BaseRuleConfig):
    """Rule10：横向钢片位置需均分两横沟之间花纹块（未实现）"""
    description: str = "横向钢片位置需均分两横沟之间花纹块"
    max_score: int = 0
    activation_node_name: str = ""
    transverse_sipe_width: float = Field(description="横向钢片宽度(像素)")
    position_tolerance_ratio: float = Field(description="允许偏离均分位置的比例阈值")
    min_adjacent_groove_count: int = Field(description="至少需要两条横沟才能判断均分")


@register_rule_feature
class Rule9Feature(BaseRuleFeature):
    """Rule9特征：横向钢片数量，未实现"""
    num_transverse_sipes_rib1_5: int = Field(description="RIB1/5横向钢片数量")
    num_transverse_sipes_rib2_4: int = Field(description="RIB2/4横向钢片数量")
    is_count_valid: bool = Field(description="数量是否合规")


@register_rule_feature
class Rule10Feature(BaseRuleFeature):
    """Rule10特征：横向钢片位置，未实现"""
    sipe_positions: List[float] = Field(description="钢片位置列表")
    groove_positions: List[float] = Field(description="横沟位置列表")
    position_deviation_ratio: float = Field(description="位置偏差比例")
    is_evenly_distributed: bool = Field(description="是否均匀分布")


@register_rule_score
class Rule9Score(BaseRuleScore):
    """Rule9（横向钢片数量）评分，未实现"""
    pass


@register_rule_score
class Rule10Score(BaseRuleScore):
    """Rule10（横向钢片位置）评分，未实现"""
    pass


# ============================================================
# 第八部分：Rule11 纵向细沟&纵向钢片
# ============================================================

class Rule11Config(BaseRuleConfig):
    """Rule11：纵向钢片与纵向细沟数量约束"""
    description: str = "纵向钢片与纵向细沟数量约束"
    max_score: int = 4
    activation_node_name: str = ""
    groove_width: float = Field(description="纵向线条名义宽度(像素)")
    min_width_offset_px: int = Field(description="宽度下限偏移(像素)")
    edge_margin_ratio: float = Field(description="左右边缘排除比例")
    min_segment_length_ratio: float = Field(description="连续线段最小长度比例")
    max_angle_from_vertical: float = Field(description="主轴允许偏离竖直方向的最大角度(度)")
    max_count_center: int = Field(description="center允许的最大纵向线条数")
    max_count_side: int = Field(description="side允许的最大纵向线条数")


@register_rule_feature
class Rule11Feature(BaseRuleFeature):
    """Rule11特征：纵向细沟&纵向钢片数量"""
    num_longitudinal_grooves: int = Field(description="纵向线条数量")


@register_rule_score
class Rule11Score(BaseRuleScore):
    """Rule11（纵向细沟&纵向钢片）评分"""
    pass


# ============================================================
# 第九部分：Rule12 RIB横向连续性
# ============================================================

class Rule12Config(BaseRuleConfig):
    """Rule12：两个RIB间横向钢片及横沟连续性占比60%-70%"""
    description: str = "两个RIB间横向钢片及横沟连续性占比60%-70%"
    max_score: int = 0
    activation_node_name: str = ""
    continuity_mode: str = Field(description="连续性模式：RIB2-RIB3|RIB3-RIB4|RIB2-RIB3-RIB4|none")
    groove_width: float = Field(description="主沟宽度(像素)")
    blend_width: int = Field(description="融合宽度(像素)")


@register_rule_feature
class Rule12Feature(BaseRuleFeature):
    """Rule12特征：RIB横向连续性"""
    is_continuous: bool = Field(description="是否连续")


@register_rule_score
class Rule12Score(BaseRuleScore):
    """Rule12（RIB横向连续性）评分"""
    pass


# ============================================================
# 第十部分：Rule13 海陆比/陆地占比
# ============================================================

class Rule13Config(BaseRuleConfig):
    """Rule13：1个节距TDW范围内海陆比在28%-35%"""
    description: str = "1个节距TDW范围内海陆比在28%-35%"
    max_score: int = 2
    activation_node_name: str = ""
    land_ratio_min: float = Field(description="合格陆地占比下限")
    land_ratio_max: float = Field(description="合格陆地占比上限")


@register_rule_feature
class Rule13Feature(BaseRuleFeature):
    """Rule13特征：海陆比（其实是陆地占比）"""
    land_ratio: float = Field(description="陆地占比")


@register_rule_score
class Rule13Score(BaseRuleScore):
    """Rule13（海陆比/陆地占比）评分"""
    pass


# ============================================================
# 第十一部分：Rule14 交点数量
# ============================================================

class Rule14Config(BaseRuleConfig):
    """Rule14：钢片&横沟与其他线条交点数量<=2"""
    description: str = "钢片&横沟与其他线条交点数量≤2"
    max_score: int = 2
    activation_node_name: str = ""
    max_intersections: int = Field(description="允许的最大交叉点数量")


@register_rule_feature
class Rule14Feature(BaseRuleFeature):
    """Rule14特征：交点数量"""
    num_intersections: int = Field(description="交叉点数量")


@register_rule_score
class Rule14Score(BaseRuleScore):
    """Rule14（交点数量）评分"""
    pass


# ============================================================
# 第十二部分：Rule15 花纹块面积比例（未实现）
# ============================================================

class Rule15Config(BaseRuleConfig):
    """Rule15：各节距中细沟&横沟分割出的花纹块面积比例（未实现）"""
    description: str = "各节距中细沟&横沟分割出的花纹块面积比例≤1:1.2"
    max_score: int = 0
    activation_node_name: str = ""
    max_block_area_ratio: float = Field(description="各花纹块面积比例上限：1.2")
    min_block_area_px: int = Field(description="过滤噪声用最小花纹块面积(像素)")
    rib_index_start: int = Field(description="RIB起始索引，默认RIB1")
    rib_index_end: int = Field(description="RIB结束索引，默认RIB5")


@register_rule_feature
class Rule15Feature(BaseRuleFeature):
    """Rule15特征：花纹块面积比例，未实现"""
    block_area_ratios: List[float] = Field(description="各花纹块面积比例列表")
    max_block_area_ratio: float = Field(description="最大面积比例")
    is_area_ratio_valid: bool = Field(description="面积比例是否合规")


@register_rule_score
class Rule15Score(BaseRuleScore):
    """Rule15（花纹块面积比例）评分，未实现"""
    pass


# ============================================================
# 第十三部分：Rule16-17 连续性拼接
# ============================================================

class Rule16Config(BaseRuleConfig):
    """Rule16：RIB2/3/4上的横沟或横向钢片可任意组合连续性"""
    description: str = "RIB2/3/4上的横沟或横向钢片可任意组合连续性"
    max_score: int = 0
    activation_node_name: str = ""
    continuity_mode: str = Field(description="三RIB组合模式")
    groove_width: float = Field(description="主沟宽度(像素)")
    blend_width: int = Field(description="融合宽度(像素)")


class Rule17Config(BaseRuleConfig):
    """Rule17：RIB1与RIB2、RIB4与RIB5可连续可不连续，各占50%"""
    description: str = "RIB1与RIB2、RIB4与RIB5可连续可不连续，各占50%"
    max_score: int = 0
    activation_node_name: str = ""
    edge_continuity_rib1_rib2: float = Field(ge=0, le=1, description="RIB1-RIB2连续概率")
    edge_continuity_rib4_rib5: float = Field(ge=0, le=1, description="RIB4-RIB5连续概率")
    blend_width: int = Field(description="融合宽度(像素)")


@register_rule_feature
class Rule16Feature(BaseRuleFeature):
    """Rule16特征：RIB2/3/4任意组合连续性"""
    is_continuous: bool = Field(description="是否连续")


@register_rule_feature
class Rule17Feature(BaseRuleFeature):
    """Rule17特征：RIB1/2与RIB4/5概率连续"""
    rib1_rib2_continuous: bool = Field(description="RIB1-RIB2是否连续")
    rib4_rib5_continuous: bool = Field(description="RIB4-RIB5是否连续")


@register_rule_score
class Rule16Score(BaseRuleScore):
    """Rule16（RIB2/3/4任意组合连续性）评分"""
    pass


@register_rule_score
class Rule17Score(BaseRuleScore):
    """Rule17（RIB1/2与RIB4/5概率连续）评分"""
    pass


# ============================================================
# 第十四部分：Rule18 颜色灰度变化（未实现）
# ============================================================

class Rule18Config(BaseRuleConfig):
    """Rule18：颜色灰度变化用于表征沟的深浅（未实现）"""
    description: str = "颜色灰度变化用于表征沟的深浅"
    max_score: int = 0
    activation_node_name: str = ""
    enable_gray_depth: bool = Field(description="是否启用灰度深度")
    min_gray_value: int = Field(description="最小灰度值")
    max_gray_value: int = Field(description="最大灰度值")
    depth_levels: int = Field(description="灰度深度级别数")


@register_rule_feature
class Rule18Feature(BaseRuleFeature):
    """Rule18特征：颜色灰度变化，未实现"""
    gray_value_min: int = Field(description="最小灰度值")
    gray_value_max: int = Field(description="最大灰度值")
    gray_depth_levels: int = Field(description="灰度深度级别数")
    has_gray_depth_variation: bool = Field(description="是否有灰度深度变化")


@register_rule_score
class Rule18Score(BaseRuleScore):
    """Rule18（颜色灰度变化）评分，未实现"""
    pass


# ============================================================
# 第十五部分：Rule19 装饰边框
# ============================================================

class Rule19Config(BaseRuleConfig):
    """Rule19：PDW与TDW之间边缘灰色区域可结合横沟或钢片做装饰性造型 - 纯流程类规则，无评分"""
    description: str = "PDW与TDW之间边缘灰色区域可结合横沟或钢片做装饰性造型"
    max_score: int = 0
    activation_node_name: str = ""
    tire_design_width: int = Field(description="花纹有效宽度(像素)")
    decoration_border_alpha: float = Field(ge=0, le=1, description="透明度")
    decoration_gray_color: int = Field(description="灰色RGB值")


@register_rule_feature
class Rule19Feature(BaseRuleFeature):
    """Rule19特征：装饰边框，流程类，无可评分特征"""
    pass


@register_rule_score
class Rule19Score(BaseRuleScore):
    """Rule19（装饰边框）评分，纯流程类无评分"""
    pass


# ============================================================
# 第十六部分：Rule20 文生图（未实现）
# ============================================================

class Rule20Config(BaseRuleConfig):
    """Rule20：用户输入文字生成合理的花纹概念图片（未实现）"""
    description: str = "用户输入文字生成合理的花纹概念图片"
    max_score: int = 0
    activation_node_name: str = ""
    prompt: str = Field(description="提示词")
    negative_prompt: Optional[str] = Field(default=None, description="负面提示词")
    num_images: int = Field(description="生成图片数量")
    seed: Optional[int] = Field(default=None, description="随机种子")
    output_width: int = Field(description="输出宽度(像素)")
    output_height: int = Field(description="输出高度(像素)")


@register_rule_feature
class Rule20Feature(BaseRuleFeature):
    """Rule20特征：文生图，未实现"""
    prompt_used: str = Field(description="使用的提示词")
    generated_image_count: int = Field(description="生成图片数量")
    generation_success: bool = Field(description="生成是否成功")


@register_rule_score
class Rule20Score(BaseRuleScore):
    """Rule20（文生图）评分，未实现"""
    pass


# ============================================================
# 第十七部分：Rule21-22 已被融入
# ============================================================

class Rule21Config(BaseRuleConfig):
    """Rule21：针对用户提出的业务目标量化要求支持配置 - 现被configs与各RuleConfig吸收"""
    description: str = "针对用户提出的业务目标量化要求支持配置"
    max_score: int = 0
    activation_node_name: str = ""
    configurable_rule_names: List[str] = Field(description="可配置规则名称列表")
    strict_validation: bool = Field(description="是否严格校验")
    allow_partial_override: bool = Field(description="是否允许部分覆盖")


class Rule22Config(BaseRuleConfig):
    """Rule22：能够根据需要输出指定清晰度的图片 - 现被rule6a纵图拼接resolution配置吸收"""
    description: str = "能够根据需要输出指定清晰度的图片"
    max_score: int = 0
    activation_node_name: str = ""
    target_width: int = Field(description="目标宽度(像素)")
    target_height: int = Field(description="目标高度(像素)")
    keep_aspect_ratio: bool = Field(description="是否保持宽高比")
    output_format: str = Field(description="输出格式")


@register_rule_feature
class Rule21Feature(BaseRuleFeature):
    """Rule21特征：参数可配置，已被融入"""
    configurable_rule_names: List[str] = Field(description="可配置规则名称列表")
    validated_config_count: int = Field(description="已校验配置数量")
    invalid_config_messages: List[str] = Field(description="无效配置消息列表")
    is_config_valid: bool = Field(description="配置是否有效")


@register_rule_feature
class Rule22Feature(BaseRuleFeature):
    """Rule22特征：图片分辨率，已被融入"""
    output_width: int = Field(description="输出宽度(像素)")
    output_height: int = Field(description="输出高度(像素)")
    resolution_matched: bool = Field(description="分辨率是否匹配")


@register_rule_score
class Rule21Score(BaseRuleScore):
    """Rule21（参数可配置）评分，已被融入"""
    pass


@register_rule_score
class Rule22Score(BaseRuleScore):
    """Rule22（图片分辨率）评分，已被融入"""
    pass
```

---

## 4. 关键约束检查表

### 4.1 每个类生成后必须检查
- [ ] 类名与设计文档一致
- [ ] 字段名与设计文档一致
- [ ] 字段类型与设计文档一致
- [ ] 字段描述与设计文档一致
- [ ] Field 约束与设计文档一致
- [ ] model_validator 与设计文档一致

### 4.2 必须遵守的约束
| 约束项 | 要求 | 违反后果 |
|--------|------|---------|
| TireStruct.validate_assignment | 必须开启 | 运行时赋值不校验 |
| RuleEvaluation.validate_assignment | 必须开启 | set_feature/set_score 失败 |
| ImageEvaluation.validate_assignment | 必须开启 | current_score 无法更新 |
| RibSchemeImpl.validate_assignment | 必须开启 | 运行时字段无法填充 |
| 模板类.frozen | 必须设置 | 模板被误修改 |
| 可变默认值 | 必须用 Field(default_factory=...) | 共享可变默认值bug |
| Feature注册 | 必须加装饰器 | 无法通过名称查找 |
| Score注册 | 必须加装饰器 | 无法通过名称查找 |
| 私有校验方法 | 必须以 _validate_ 开头 | 命名不规范 |

### 4.3 禁止事项
- ❌ 禁止在未明确要求的类开启 validate_assignment
- ❌ 禁止在模板类中存运行时数据
- ❌ 禁止在 Feature 类中访问图片数据
- ❌ 禁止手动定义 name 属性（必须自动提取）
- ❌ 禁止使用 `dict` 或 `list` 作为默认值（必须用 default_factory）
- ❌ 禁止修改设计文档中的校验规则

---

## 5. 校验规则表（按设计文档）

AI 在生成每个类后，必须对照此表检查：

| 类名 | 校验规则 | 错误信息 |
|------|---------|---------|
| TireStruct | 必须有小图或大图 | "必须输入小图或大图，流程无法执行" |
| TireStruct | scheme_rank >= 1 | "方案排名必须>=1" |
| BaseImage | base64格式检查 | "image_base64必须包含data:image/*;base64,前缀" |
| ImageMeta | width/height >= 1 | Field约束 |
| ImageMeta | channels 1-4 | Field约束 |
| ImageMeta | 尺寸<=10000 | "图像尺寸超过上限10000像素" |
| ImageBiz | 原始数据必须有region | "原始数据必须指定region" |
| ImageBiz | 继承来源必须有inherit_from | "继承来源必须指定inherit_from" |
| ImageEvaluation | 规则名称不能重复 | "规则名称不能重复" |
| RuleEvaluation | feature/score名称一致 | "feature.name != rule name" |
| RibSchemeImpl | 最外层必须有rib_name | "最外层RIB必须有rib_name" |
| RibSchemeImpl | 继承来源必须有inherit_from | "继承来源必须指定inherit_from" |
| DecorationImpl | decoration_opacity 0~255 | Field约束 |
| Rule17Config | edge_continuity 0~1 | Field约束 |
| Rule8Config | groove_width > 0 | Field约束 |

---

## 6. 常见错误示例

### 6.1 错误1：可变默认值
```python
# ❌ 错误
class MyModel(BaseModel):
    items: List[str] = []

# ✅ 正确
class MyModel(BaseModel):
    items: List[str] = Field(default_factory=list)
```

### 6.2 错误2：忘记开启 validate_assignment
```python
# ❌ 错误（TireStruct 必须开启）
class TireStruct(BaseModel):
    pass

# ✅ 正确
class TireStruct(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
```

### 6.3 错误3：模板类未设置 frozen
```python
# ❌ 错误（模板类必须 frozen）
class StitchingTemplate(BaseModel):
    pass

# ✅ 正确
class StitchingTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)
```

### 6.4 错误4：忘记注册装饰器
```python
# ❌ 错误
class Rule8Feature(BaseRuleFeature):
    pass

# ✅ 正确
@register_rule_feature
class Rule8Feature(BaseRuleFeature):
    pass
```

### 6.5 错误5：model_validator 未返回 self
```python
# ❌ 错误
@model_validator(mode="after")
def _validate(self) -> "MyModel":
    if self.width < 0:
        raise ValueError("width must >= 0")
    # 缺少 return self

# ✅ 正确
@model_validator(mode="after")
def _validate(self) -> "MyModel":
    if self.width < 0:
        raise ValueError("width must >= 0")
    return self
```

---

## 7. 注释规范

### 7.1 类注释
```python
class TireStruct(BaseModel):
    """
    轮胎图像全流程统一数据结构

    所有Pipeline的输入和输出都使用这个结构。
    每个字段标注了在哪个流程生效、是入参还是出参。
    开启validate_assignment确保运行时赋值的合法性。
    """
```

### 7.2 字段注释（TireStruct专用）
```python
# 小图列表
# 👉 入参：仅Pipeline-1使用
# 👉 出参：仅Pipeline-4输出
small_images: List[SmallImage] = Field(default_factory=list, description="小图列表")
```

### 7.3 校验方法注释
```python
@model_validator(mode="after")
def _validate_images_required(self) -> "TireStruct":
    """私有校验：必须有小图或大图至少一种"""
    # 实现代码
```

---

## 8. 执行输出格式

AI 执行过程中，应按以下格式输出进度：

```
【执行进度】
✅ 已完成：enums.py（7个枚举类）
✅ 已完成：tire_struct.py（1个类）
⏳ 正在生成：image_models.py（9个类）
⏸️ 等待：scheme_models.py（15个类）
⏸️ 等待：rule_models.py（69个类）
...

【检查结果】
✅ TireStruct.validate_assignment 已开启
✅ RuleEvaluation.validate_assignment 已开启
✅ ImageEvaluation.validate_assignment 已开启
✅ RibSchemeImpl.validate_assignment 已开启
✅ 模板类 frozen=True 已设置
✅ 可变默认值使用 Field(default_factory=...)
✅ Feature/Score 注册装饰器已添加
...

【完成统计】
- 总文件数：5（enums.py, tire_struct.py, image_models.py, scheme_models.py, rule_models.py）
- 总类数：101
- 总校验规则：15
```

---

## 9. 最终检查清单

代码生成完成后，AI 必须输出：

```
【最终检查】
- [ ] 所有类名与设计文档一致
- [ ] 所有字段名与设计文档一致
- [ ] 所有校验规则与设计文档一致
- [ ] TireStruct 已开启 validate_assignment
- [ ] RuleEvaluation 已开启 validate_assignment
- [ ] ImageEvaluation 已开启 validate_assignment
- [ ] RibSchemeImpl 已开启 validate_assignment
- [ ] 模板类已设置 frozen=True
- [ ] Feature/Score 已添加注册装饰器
- [ ] 无共享可变默认值
- [ ] 无手动定义 name 属性
- [ ] 所有 model_validator 返回 self

【设计文档偏离说明】
- 无偏离 / 偏离点：XXX（必须显式说明）

【建议后续步骤】
1. 编写单元测试（tests/unittests/）
2. 编写集成测试（tests/integrations/）
3. 更新依赖声明
```

---

## 10. 文件依赖关系

```
enums.py
  ↓
tire_struct.py ──────┐
  ↓                  │
image_models.py      │
  ↓                  │
scheme_models.py     │
  ↓                  │
rule_models.py ←─────┘
```

**导入顺序说明：**
1. `enums.py` 无依赖，最先导入
2. `tire_struct.py` 依赖 `image_models.py` 和 `rule_models.py`（使用字符串前向引用）
3. `image_models.py` 依赖 `enums.py` 和 `scheme_models.py`（使用字符串前向引用）
4. `scheme_models.py` 依赖 `enums.py`
5. `rule_models.py` 无外部依赖

**模块间导入规则：**
- 所有跨文件导入直接指向源文件：`from .enums import LevelEnum`
- 存在循环依赖时使用字符串前向引用：`List["SmallImage"]`
- __init__.py 保持空文件，不做重新导出

---

**文档结束**
