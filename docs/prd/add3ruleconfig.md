# 新增 Rule100 / Rule101 / Rule102 需求文档

## 1. 背景

在 `generate_large_image_from_lineage()` 大图生成流程中，`ImageLineage` 血缘对象内嵌了 `RibSchemeImpl`、`MainGrooveImpl`、`DecorationImpl` 的运行时尺寸参数（`num_pitchs`、`rib_width`、`groove_width`、`decoration_opacity` 等）。这些参数需要在调用生成函数前由外部配置。

为此新增三个**纯配置型 Rule**，仅承载参数，不参与评分——与 Rule19（装饰边框流程类规则）模式相同。三个 Rule 的配置值将被注入到 `ImageLineage` 的对应字段，驱动后续大图生成。

## 2. 核心目标

新增 Rule100 / Rule101 / Rule102，各包含 Config / Feature / Score 三类定义：

- **Config**：承载业务配置参数
- **Feature**：空壳（`pass`），无特征提取逻辑
- **Score**：空壳，`score=None`，不参与总分计算

同时调整 `BaseRuleConfig.max_score` 和 `BaseRuleScore.score` 支持 `None`。

## 3. 模型设计

### 3.1 基类调整

#### BaseRuleConfig（`src/models/rule_models.py`）

```diff
- max_score: int = Field(ge=0, description="最大可得分")
+ max_score: Optional[int] = Field(default=None, ge=0, description="最大可得分，None表示非打分规则")
```

#### BaseRuleScore（`src/models/rule_models.py`）

```diff
- score: int = Field(description="得分")
+ score: Optional[int] = Field(default=None, description="得分，None表示不参与评分")
```

#### ImageEvaluation._recalculate_total（`src/models/image_models.py`）

```diff
  self.current_score = sum(
      r.score.score for r in self.rules
-     if r.score is not None
+     if r.score is not None and r.score.score is not None
  )
```

---

### 3.2 Rule100：RIB 节距/尺寸配置

```python
class RibSizeItem(BaseModel):
    """单个 RIB 的尺寸配置"""
    rib_name: str = Field(description="RIB名称，如 rib1、rib2")
    num_pitchs: int = Field(ge=1, description="节距数量")
    rib_width: int = Field(ge=1, description="纵向图宽度(像素)")
    rib_height: int = Field(ge=1, description="纵向图高度(像素)")

class Rule100Config(BaseRuleConfig):
    """Rule100：RIB 节距/尺寸配置"""
    description: str = "RIB 节距与尺寸配置"
    # max_score 继承 BaseRuleConfig，默认 None
    rib_number: int = Field(ge=1, description="RIB 数量")
    rib_sizes: List[RibSizeItem] = Field(min_length=1, description="每个RIB的尺寸配置列表")

@register_rule_feature
class Rule100Feature(BaseRuleFeature):
    """Rule100 特征（纯配置型，无特征提取）"""
    pass

@register_rule_score
class Rule100Score(BaseRuleScore):
    """Rule100 评分（纯配置型，无评分）"""
    pass
```

### 3.3 Rule101：主沟尺寸配置

```python
class GrooveSizeItem(BaseModel):
    """单个主沟的尺寸配置"""
    groove_width: int = Field(ge=1, description="主沟宽度(像素)")
    groove_height: int = Field(ge=1, description="主沟高度(像素)")

class Rule101Config(BaseRuleConfig):
    """Rule101：主沟尺寸配置"""
    description: str = "主沟尺寸配置"
    groove_sizes: List[GrooveSizeItem] = Field(min_length=1, description="每个主沟的尺寸配置列表")

@register_rule_feature
class Rule101Feature(BaseRuleFeature):
    """Rule101 特征（纯配置型，无特征提取）"""
    pass

@register_rule_score
class Rule101Score(BaseRuleScore):
    """Rule101 评分（纯配置型，无评分）"""
    pass
```

### 3.4 Rule102：装饰边框配置

```python
class DecorationItem(BaseModel):
    """单个装饰的尺寸与透明度配置"""
    position: str = Field(description="装饰位置：left / right")
    decoration_width: int = Field(ge=1, description="装饰宽度(像素)")
    decoration_height: int = Field(ge=1, description="装饰高度(像素)")
    decoration_opacity: int = Field(ge=0, le=255, description="装饰透明度(0-255)")

class Rule102Config(BaseRuleConfig):
    """Rule102：装饰边框配置"""
    description: str = "装饰边框尺寸与透明度配置"
    decorations: List[DecorationItem] = Field(min_length=1, description="左右装饰配置列表")

@register_rule_feature
class Rule102Feature(BaseRuleFeature):
    """Rule102 特征（纯配置型，无特征提取）"""
    pass

@register_rule_score
class Rule102Score(BaseRuleScore):
    """Rule102 评分（纯配置型，无评分）"""
    pass
```

---

## 4. 血缘对应关系

### 4.1 ImageLineage 结构

```
ImageLineage
├── stitching_scheme: StitchingScheme
│   └── ribs_scheme_implementation: List[RibSchemeImpl]
│       └── [i] num_pitchs   : Optional[int]     ← Rule100.rib_sizes[i].num_pitchs
│       └── [i] rib_width    : Optional[int]     ← Rule100.rib_sizes[i].rib_width
│       └── [i] rib_height   : Optional[int]     ← Rule100.rib_sizes[i].rib_height
│
├── main_groove_scheme: MainGrooveScheme
│   └── main_groove_implementation: List[MainGrooveImpl]
│       └── [i] groove_width  : int             ← Rule101.groove_sizes[i].groove_width
│       └── [i] groove_height : int             ← Rule101.groove_sizes[i].groove_height
│
└── decoration_scheme: DecorationScheme
    └── decoration_implementation: List[DecorationImpl]
        └── [i] decoration_width   : int        ← Rule102.decorations[i].decoration_width
        └── [i] decoration_height  : int        ← Rule102.decorations[i].decoration_height
        └── [i] decoration_opacity : int        ← Rule102.decorations[i].decoration_opacity
```

### 4.2 字段映射表

| RuleConfig | 字段 | 数据类型 | 写入目标 | 目标字段 | 处理函数 |
|---|---|---|---|---|---|
| Rule100 | `rib_number` | `int` | `StitchingSchemeAbstract` | `rib_number` | — |
| Rule100 | `rib_sizes[i].rib_name` | `str` | `RibSchemeImpl[i]` | `rib_name` | — |
| Rule100 | `rib_sizes[i].num_pitchs` | `int` | `RibSchemeImpl[i]` | `num_pitchs` | `_process_rib_images()` `image_stiching.py:87` |
| Rule100 | `rib_sizes[i].rib_width` | `int` | `RibSchemeImpl[i]` | `rib_width` | `_process_rib_images()` `image_stiching.py:91` |
| Rule100 | `rib_sizes[i].rib_height` | `int` | `RibSchemeImpl[i]` | `rib_height` | `_process_rib_images()` `image_stiching.py:91` |
| Rule101 | `groove_sizes[i].groove_width` | `int` | `MainGrooveImpl[i]` | `groove_width` | `_process_main_groove()` `image_stiching.py:125` |
| Rule101 | `groove_sizes[i].groove_height` | `int` | `MainGrooveImpl[i]` | `groove_height` | `_process_main_groove()` `image_stiching.py:125` |
| Rule102 | `decorations[i].position` | `str` | — | — | `overlay_decoration()` `image_stiching.py:349` |
| Rule102 | `decorations[i].decoration_width` | `int` | `DecorationImpl[i]` | `decoration_width` | `_process_decoration()` `image_stiching.py:158` |
| Rule102 | `decorations[i].decoration_height` | `int` | `DecorationImpl[i]` | `decoration_height` | `_process_decoration()` `image_stiching.py:158` |
| Rule102 | `decorations[i].decoration_opacity` | `int` | `DecorationImpl[i]` | `decoration_opacity` | `_process_decoration()` `image_stiching.py:169` |

### 4.3 参数校验链路

`_validate_parameters()`（`image_stiching.py:179-208`）会在预处理后校验：

| 校验项 | 检查字段 | 来源 |
|---|---|---|
| RIB 尺寸完整 | `rib.rib_width` / `rib.rib_height` 非空 | Rule100 |
| 主沟尺寸完整 | `groove.groove_width` / `groove.groove_height` 非空 | Rule101 |
| 装饰尺寸完整 | `decoration.decoration_width` / `decoration.decoration_height` 非空 | Rule102 |
| 拼接数量匹配 | `groove_count == rib_count - 1` | Rule100 / Rule101 联合 |

---

## 5. Executor 实现

三个 Executor 按 Rule19 模板实现，Feature 返回空实例，Score 返回 `score=None`。

### 5.1 模板示例（以 Rule100 为例）

```python
# src/rules/executors/rule100.py
from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import (
    BaseRuleFeature, BaseRuleScore,
    Rule100Config, Rule100Feature, Rule100Score,
)
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule100Executor(RuleExecutor):
    rule_cls = Rule100Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule100Config,
    ) -> BaseRuleFeature:
        return Rule100Feature()

    def exec_score(
        self,
        config: Rule100Config,
        feature: Rule100Feature,
    ) -> BaseRuleScore:
        return Rule100Score(score=None)
```

Rule101Executor / Rule102Executor 同理，仅替换类名。

### 5.2 `__init__.py` 注册

```python
# src/rules/executors/__init__.py
from src.rules.executors.rule100 import Rule100Executor
from src.rules.executors.rule101 import Rule101Executor
from src.rules.executors.rule102 import Rule102Executor

__all__ = [
    # ... 现有列表 ...
    "Rule100Executor",
    "Rule101Executor",
    "Rule102Executor",
]
```

---

## 6. 节点层注册

在 `src/nodes/base.py` 中导入三个 Config 并加入对应的 `*_CONFIGS` 列表。

三个 Rule 均属于大图生成链路（拼接方案生成阶段），应加入到 `STITCH_SCHEME_GENERATOR_CONFIGS`：

```python
from src.models.rule_models import (
    # ... 现有导入 ...
    Rule100Config,
    Rule101Config,
    Rule102Config,
)

STITCH_SCHEME_GENERATOR_CONFIGS: list[type[BaseRuleConfig]] = [
    # ... 现有列表 ...
    Rule100Config,
    Rule101Config,
    Rule102Config,
]
```

---

## 7. 影响范围清单

| 文件 | 变更类型 | 内容 |
|---|---|---|
| `src/models/rule_models.py` | 修改 + 新增 | `BaseRuleConfig.max_score` → `Optional[int]`；`BaseRuleScore.score` → `Optional[int]`；新增 `RibSizeItem`/`GrooveSizeItem`/`DecorationItem`；新增 Rule100/101/102 的 Config/Feature/Score |
| `src/models/image_models.py` | 修改 | `_recalculate_total()` 增加 `score.score is not None` 过滤 |
| `src/rules/executors/rule100.py` | 新增 | `Rule100Executor` — 空壳，`score=None` |
| `src/rules/executors/rule101.py` | 新增 | `Rule101Executor` — 空壳，`score=None` |
| `src/rules/executors/rule102.py` | 新增 | `Rule102Executor` — 空壳，`score=None` |
| `src/rules/executors/__init__.py` | 修改 | 导入并导出三个新 Executor |
| `src/nodes/base.py` | 修改 | 导入三个新 Config，加入 `STITCH_SCHEME_GENERATOR_CONFIGS` |

---

## 8. 需求边界

- **负责**：承载 RIB/主沟/装饰的运行时尺寸参数配置，注入到 `ImageLineage` 血缘对象
- **不负责**：拼接方案的决策逻辑（由模板生成器处理）、实际图像操作（由 `image_stitching.py` 处理）、评分计算
