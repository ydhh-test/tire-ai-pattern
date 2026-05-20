# 规则调整需求文档

> 涉及规则：Rule1-5、Rule12、Rule16、Rule17
> 变更范围：`src/models/rule_models.py`（模型定义）、`src/rules/executors/`（执行器）、`src/nodes/base.py`（节点注册）

---

## 1. 背景

目前 Rule1-3（对称性规则）、Rule12（RIB横向连续性）、Rule16-17（连续性拼接）处于**桩代码状态**：Executor 仅绑定了 `rule_cls`，未重写 `exec_feature()` / `exec_score()` 方法。同时 Config 中的 `max_score`、`description`、`rule_type` 等字段需要更新以匹配业务验收标准。

本次需求对8条规则（Rule1-5、Rule12、Rule16、Rule17）进行配置调整和执行器实现。

---

## 2. 公共约定

### 2.1 exec_feature 中访问血缘数据

部分规则的 `exec_feature` 需要读取 `StitchingSchemeName`（来自 `StitchingSchemeAbstract.name`）。

访问路径：

```
image (BigImage)
  └── lineage (ImageLineage)
        └── stitching_scheme (StitchingScheme)
              └── stitching_scheme_abstract (StitchingSchemeAbstract)
                    └── name: StitchingSchemeName   ← 目标字段
```

当 `image` 为 `SmallImage` 或无 `lineage` 时，`exec_feature` 应返回默认值（`is_active=False` 或 `is_continuous=False`）。

### 2.2 exec_score 计分模式

所有规则的 `exec_score` 遵循统一模式：

```python
def exec_score(self, config, feature):
    if feature.is_active:  # 或 feature.is_continuous
        score = config.max_score
    else:
        score = 0
    return XxxScore(score=score)
```

### 2.3 添加 `from __future__ import annotations`

新增/修改的执行器文件统一在首行加入 `from __future__ import annotations`。

---

## 3. Rule1 调整

### 3.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"5个花纹RIB无对称原则"` | `"rib无对称"` |
| `max_score` | `8` | `10` |
| `rule_type` | `None`（未定义） | `RuleTypeEnum.BIG_IMAGE` |

### 3.2 Feature 变更

在 `Rule1Feature` 中新增字段：

```python
@register_rule_feature
class Rule1Feature(BaseRuleFeature):
    """Rule1特征：rib无对称"""
    is_active: bool = Field(description="是否生效")
```

### 3.3 模型定义（`src/models/rule_models.py`）

```python
class Rule1Config(BaseRuleConfig):
    """Rule1：rib无对称"""
    description: str = "rib无对称"
    max_score: int = 10
    rule_type: RuleTypeEnum = RuleTypeEnum.BIG_IMAGE
```

### 3.4 Executor 实现（`src/rules/executors/rule1.py`）

```python
from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule1Config, Rule1Feature, Rule1Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule1Executor(RuleExecutor):
    rule_cls = Rule1Config

    def exec_feature(self, image: BaseImage, config: Rule1Config) -> Rule1Feature:
        """根据血缘中的 StitchingSchemeName 判断是否匹配无对称方案"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule1Feature(is_active=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_active = scheme_name in (
            StitchingSchemeName.SYMMETRY_0,   # 5-rib 无对称
            StitchingSchemeName.SYMMETRY_4,   # 4-rib 无对称
        )
        return Rule1Feature(is_active=is_active)

    def exec_score(self, config: Rule1Config, feature: Rule1Feature) -> Rule1Score:
        score = config.max_score if feature.is_active else 0
        return Rule1Score(score=score)
```

### 3.5 SchemeName 映射关系

| Rule | 描述 | 匹配的 StitchingSchemeName |
|------|------|---------------------------|
| Rule1 | rib无对称 | `SYMMETRY_0`, `SYMMETRY_4` |
| Rule2 | rib中心对称 | `SYMMETRY_1`, `SYMMETRY_5` |
| Rule3 | rib左右对称 | `SYMMETRY_2`, `SYMMETRY_6` |

---

## 4. Rule2 调整

### 4.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"中心旋转180°对称花纹"` | `"rib中心对称"` |
| `max_score` | `8` | `10` |
| `rule_type` | `None`（未定义） | `RuleTypeEnum.BIG_IMAGE` |

### 4.2 Feature 变更

在 `Rule2Feature` 中新增字段：

```python
@register_rule_feature
class Rule2Feature(BaseRuleFeature):
    """Rule2特征：rib中心对称"""
    is_active: bool = Field(description="是否生效")
```

### 4.3 模型定义（`src/models/rule_models.py`）

```python
class Rule2Config(BaseRuleConfig):
    """Rule2：rib中心对称"""
    description: str = "rib中心对称"
    max_score: int = 10
    rule_type: RuleTypeEnum = RuleTypeEnum.BIG_IMAGE
```

### 4.4 Executor 实现（`src/rules/executors/rule2.py`）

```python
from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule2Config, Rule2Feature, Rule2Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule2Executor(RuleExecutor):
    rule_cls = Rule2Config

    def exec_feature(self, image: BaseImage, config: Rule2Config) -> Rule2Feature:
        """根据血缘中的 StitchingSchemeName 判断是否匹配中心对称方案"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule2Feature(is_active=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_active = scheme_name in (
            StitchingSchemeName.SYMMETRY_1,   # 5-rib 中心旋转180°对称
            StitchingSchemeName.SYMMETRY_5,   # 4-rib 中心旋转180°对称
        )
        return Rule2Feature(is_active=is_active)

    def exec_score(self, config: Rule2Config, feature: Rule2Feature) -> Rule2Score:
        score = config.max_score if feature.is_active else 0
        return Rule2Score(score=score)
```

---

## 5. Rule3 调整

### 5.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"中心线镜像对称"` | `"rib左右对称"` |
| `max_score` | `8` | `10` |
| `rule_type` | `None`（未定义） | `RuleTypeEnum.BIG_IMAGE` |

### 5.2 Feature 变更

在 `Rule3Feature` 中新增字段：

```python
@register_rule_feature
class Rule3Feature(BaseRuleFeature):
    """Rule3特征：rib左右对称"""
    is_active: bool = Field(description="是否生效")
```

### 5.3 模型定义（`src/models/rule_models.py`）

```python
class Rule3Config(BaseRuleConfig):
    """Rule3：rib左右对称"""
    description: str = "rib左右对称"
    max_score: int = 10
    rule_type: RuleTypeEnum = RuleTypeEnum.BIG_IMAGE
```

### 5.4 Executor 实现（`src/rules/executors/rule3.py`）

```python
from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule3Config, Rule3Feature, Rule3Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule3Executor(RuleExecutor):
    rule_cls = Rule3Config

    def exec_feature(self, image: BaseImage, config: Rule3Config) -> Rule3Feature:
        """根据血缘中的 StitchingSchemeName 判断是否匹配左右对称方案"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule3Feature(is_active=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_active = scheme_name in (
            StitchingSchemeName.SYMMETRY_2,   # 5-rib 左右镜像对称
            StitchingSchemeName.SYMMETRY_6,   # 4-rib 左右镜像对称
        )
        return Rule3Feature(is_active=is_active)

    def exec_score(self, config: Rule3Config, feature: Rule3Feature) -> Rule3Score:
        score = config.max_score if feature.is_active else 0
        return Rule3Score(score=score)
```

---

## 6. Rule4 调整

### 6.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"中心线镜像对称可错位"` | `"未实现"` |
| `max_score` | `8` | `None` |
| 整体 | 正常启用 | **注释掉**（Config/Feature/Score 整段注释） |

### 6.2 模型定义（`src/models/rule_models.py`）

```python
# class Rule4Config(BaseRuleConfig):
#     """Rule4：未实现"""
#     description: str = "未实现"
#     # max_score 继承 BaseRuleConfig，默认 None

# @register_rule_feature
# class Rule4Feature(BaseRuleFeature):
#     """Rule4特征：未实现"""
#     pass

# @register_rule_score
# class Rule4Score(BaseRuleScore):
#     """Rule4评分：未实现"""
#     pass
```

### 6.3 Executor 处理（`src/rules/executors/rule4.py`）

整体注释掉：

```python
# from src.models.rule_models import Rule4Config
# from src.rules.base import RuleExecutor
# from src.rules.registry import register_rule_executor
#
# @register_rule_executor
# class Rule4Executor(RuleExecutor):
#     rule_cls = Rule4Config
```

### 6.4 节点注册（`src/nodes/base.py`）

从 `STITCH_SCHEME_GENERATOR_CONFIGS` 中移除（或注释掉）`Rule4Config`：

```python
# Rule4Config,  # 已注释
```

---

## 7. Rule5 调整

### 7.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"根据用户指定的对称性进行输出"` | `"分数已合并入rule1～4"` |
| `max_score` | `1` | `None` |
| 整体 | 正常启用 | **注释掉**（Config/Feature/Score 整段注释） |

### 7.2 模型定义（`src/models/rule_models.py`）

```python
# class Rule5Config(BaseRuleConfig):
#     """Rule5：分数已合并入rule1～4"""
#     description: str = "分数已合并入rule1～4"
#     # max_score 继承 BaseRuleConfig，默认 None

# @register_rule_feature
# class Rule5Feature(BaseRuleFeature):
#     """Rule5特征：分数已合并入rule1～4"""
#     pass

# @register_rule_score
# class Rule5Score(BaseRuleScore):
#     """Rule5评分：分数已合并入rule1～4"""
#     pass
```

### 7.3 Executor 处理（`src/rules/executors/rule5.py`）

整体注释掉：

```python
# from src.models.rule_models import Rule5Config
# from src.rules.base import RuleExecutor
# from src.rules.registry import register_rule_executor
#
# @register_rule_executor
# class Rule5Executor(RuleExecutor):
#     rule_cls = Rule5Config
```

### 7.4 节点注册（`src/nodes/base.py`）

从 `STITCH_SCHEME_GENERATOR_CONFIGS` 中移除（或注释掉）`Rule5Config`：

```python
# Rule5Config,  # 已注释
```

---

## 8. Rule12 调整

### 8.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"两个RIB间横向钢片及横沟连续性占比60%-70%"` | `"两个RIB间横向钢片及横沟连续性占比是否满足要求"` |
| `max_score` | `0` | `6` |
| `continuity_mode` | `str` | **删除** |
| `groove_width` | `float` | **删除** |
| `blend_width` | `int` | **删除** |
| — | — | **新增** `continuity_ratio_upper: float` |
| — | — | **新增** `continuity_ratio_lower: float` |
| — | — | **新增** `continuity_mode_list: List[str]` |

### 8.2 Feature 变更

`is_continuous` 类型由 `bool` 改为 `float`，语义由"是否连续"变为"连续性占比"。

```python
@register_rule_feature
class Rule12Feature(BaseRuleFeature):
    """Rule12特征：RIB横向连续性占比"""
    continuity_ratio: float = Field(description="连续性占比")
```

### 8.3 模型定义（`src/models/rule_models.py`）

```python
class Rule12Config(BaseRuleConfig):
    """Rule12：两个RIB间横向钢片及横沟连续性占比是否满足要求"""
    description: str = "两个RIB间横向钢片及横沟连续性占比是否满足要求"
    max_score: int = 6
    continuity_ratio_upper: float = Field(description="连续性占比上界")
    continuity_ratio_lower: float = Field(description="连续性占比下界")
    continuity_mode_list: List[str] = Field(description="连续性模式列表")
```

### 8.4 Executor 实现（`src/rules/executors/rule12.py`）

```python
from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import Rule12Config, Rule12Feature, Rule12Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule12Executor(RuleExecutor):
    rule_cls = Rule12Config

    def exec_feature(self, image: BaseImage, config: Rule12Config) -> Rule12Feature:
        """
        计算连续性占比：
        continuity_ratio = len(非CONTINUITY_0的元素) / len(continuity_mode_list)
        """
        if not config.continuity_mode_list:
            return Rule12Feature(continuity_ratio=0.0)

        non_zero_count = sum(
            1 for mode in config.continuity_mode_list
            if mode != StitchingSchemeName.CONTINUITY_0.value
        )
        ratio = non_zero_count / len(config.continuity_mode_list)
        return Rule12Feature(continuity_ratio=ratio)

    def exec_score(self, config: Rule12Config, feature: Rule12Feature) -> Rule12Score:
        """连续性占比在 [lower, upper] 范围内则得分"""
        in_range = config.continuity_ratio_lower <= feature.continuity_ratio <= config.continuity_ratio_upper
        score = config.max_score if in_range else 0
        return Rule12Score(score=score)
```

### 8.5 exec_score 逻辑说明

- 特征 `continuity_ratio` 在上界与下界之间（含边界）：`score = config.max_score`（6）
- 不在范围内：`score = 0`

---

## 9. Rule16 调整

### 9.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"RIB2/3/4上的横沟或横向钢片可任意组合连续性"` | `"中心RIB上的横沟或横向钢片可任意组合连续性"` |
| `max_score` | `0` | `4` |
| `continuity_mode` | `str` | **删除** |
| `groove_width` | `float` | **删除** |
| `blend_width` | `int` | **删除** |
| — | — | **新增** `continuity_mode_list: List[str]` |

### 9.2 模型定义（`src/models/rule_models.py`）

```python
class Rule16Config(BaseRuleConfig):
    """Rule16：中心RIB上的横沟或横向钢片可任意组合连续性"""
    description: str = "中心RIB上的横沟或横向钢片可任意组合连续性"
    max_score: int = 4
    continuity_mode_list: List[str] = Field(description="连续性模式列表")
```

### 9.3 Executor 实现（`src/rules/executors/rule16.py`）

```python
from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule16Config, Rule16Feature, Rule16Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule16Executor(RuleExecutor):
    rule_cls = Rule16Config

    def exec_feature(self, image: BaseImage, config: Rule16Config) -> Rule16Feature:
        """判断血缘中的 StitchingSchemeName 是否为 CONTINUITY_1/2/3"""
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule16Feature(is_continuous=False)

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_continuous = scheme_name in (
            StitchingSchemeName.CONTINUITY_1,
            StitchingSchemeName.CONTINUITY_2,
            StitchingSchemeName.CONTINUITY_3,
        )
        return Rule16Feature(is_continuous=is_continuous)

    def exec_score(self, config: Rule16Config, feature: Rule16Feature) -> Rule16Score:
        score = config.max_score if feature.is_continuous else 0
        return Rule16Score(score=score)
```

### 9.4 Feature 不变

`Rule16Feature` 保持现有定义（`is_continuous: bool`），无需改动。

---

## 10. Rule17 调整

> **注意**：需求原文第8条标注为"Rule16调整"，但根据描述"边缘RIB上的横沟或横向钢片可任意组合连续性"和现有代码比对，实际调整目标为 **Rule17**（原 Rule17 描述为"RIB1与RIB2、RIB4与RIB5可连续可不连续"）。

### 10.1 变更描述

| 属性 | 旧值 | 新值 |
|------|------|------|
| `description` | `"RIB1与RIB2、RIB4与RIB5可连续可不连续，各占50%"` | `"边缘RIB上的横沟或横向钢片可任意组合连续性"` |
| `max_score` | `0` | `6` |
| `edge_continuity_rib1_rib2` | `float` | **删除** |
| `edge_continuity_rib4_rib5` | `float` | **删除** |
| `blend_width` | `int` | **删除** |
| — | — | **新增** `continuity_mode_list: List[str]` |

### 10.2 模型定义（`src/models/rule_models.py`）

```python
class Rule17Config(BaseRuleConfig):
    """Rule17：边缘RIB上的横沟或横向钢片可任意组合连续性"""
    description: str = "边缘RIB上的横沟或横向钢片可任意组合连续性"
    max_score: int = 6
    continuity_mode_list: List[str] = Field(description="连续性模式列表")
```

### 10.3 Feature 变更

`Rule17Feature` 需调整为单字段：

```python
@register_rule_feature
class Rule17Feature(BaseRuleFeature):
    """Rule17特征：边缘RIB任意组合连续性"""
    is_continuous: bool = Field(description="是否连续")
```

### 10.4 Executor 实现（`src/rules/executors/rule17.py`）

```python
from __future__ import annotations

from src.models.image_models import BaseImage, BigImage
from src.models.rule_models import Rule17Config, Rule17Feature, Rule17Score
from src.models.enums import StitchingSchemeName
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule17Executor(RuleExecutor):
    rule_cls = Rule17Config

    def exec_feature(self, image: BaseImage, config: Rule17Config) -> Rule17Feature:
        """
        TODO: 判断血缘中的 StitchingSchemeName 是否在边缘RIB连续性列表中。
        目前还没有对应的 CONTINUITY_N 被定义，该列表为空。
        后续定义了 CONTINUITY_N 枚举值之后，填充到 _EDGE_CONTINUITY_LIST 中。
        """
        if not isinstance(image, BigImage) or image.lineage is None:
            return Rule17Feature(is_continuous=False)

        # TODO: 等待 CONTINUITY_N 枚举定义后更新此列表
        _EDGE_CONTINUITY_LIST: tuple = ()

        scheme_name = image.lineage.stitching_scheme.stitching_scheme_abstract.name
        is_continuous = scheme_name in _EDGE_CONTINUITY_LIST
        return Rule17Feature(is_continuous=is_continuous)

    def exec_score(self, config: Rule17Config, feature: Rule17Feature) -> Rule17Score:
        score = config.max_score if feature.is_continuous else 0
        return Rule17Score(score=score)
```

### 10.5 设计说明

- `_EDGE_CONTINUITY_LIST` 当前为空元组，所有输入均返回 `is_continuous=False`、`score=0`
- 待 `StitchingSchemeName` 枚举中定义了对应的 `CONTINUITY_N` 之后，将该列表填充即可生效
- 此设计确保 Rule17 在执行流程中不阻塞，且不影响总分计算

---

## 11. 影响范围清单

| 文件 | 变更类型 | 内容 |
|------|----------|------|
| `src/models/rule_models.py` | 修改 | Rule1-3Config: 改 description/max_score/加 rule_type；Rule4-5Config: 改 description/max_score、注释整段；Rule12Config: 改 description/max_score、删 3 字段、加 3 字段；Rule16Config: 改 description/max_score、删 3 字段、加 continuity_mode_list；Rule17Config: 改 description/max_score、删 3 字段、加 continuity_mode_list |
| `src/models/rule_models.py` | 修改 | Rule1-3Feature: 加 is_active 字段；Rule5Feature: 注释；Rule12Feature: is_continuous(bool→float) 改名 continuity_ratio；Rule17Feature: 改字段 |
| `src/models/rule_models.py` | 修改 | Rule4-5Score: 注释 |
| `src/rules/executors/rule1.py` | 修改 | 实现 exec_feature + exec_score |
| `src/rules/executors/rule2.py` | 修改 | 实现 exec_feature + exec_score |
| `src/rules/executors/rule3.py` | 修改 | 实现 exec_feature + exec_score |
| `src/rules/executors/rule4.py` | 修改 | 注释整文件 |
| `src/rules/executors/rule5.py` | 修改 | 注释整文件 |
| `src/rules/executors/rule12.py` | 修改 | 实现 exec_feature + exec_score |
| `src/rules/executors/rule16.py` | 修改 | 实现 exec_feature + exec_score |
| `src/rules/executors/rule17.py` | 修改 | 实现 exec_feature（含 TODO）+ exec_score |
| `src/nodes/base.py` | 修改 | `STITCH_SCHEME_GENERATOR_CONFIGS` 移除 Rule4Config/Rule5Config |
| `src/rules/executors/__init__.py` | 修改 | 注释掉 `from src.rules.executors.rule4 import Rule4Executor` 和 `from src.rules.executors.rule5 import Rule5Executor` |

---

## 12. 变更汇总对比

### 12.1 Config 变更汇总

| Rule | description | max_score | rule_type | 特殊操作 |
|------|-------------|-----------|-----------|----------|
| Rule1 | rib无对称 | 10 | BIG_IMAGE | — |
| Rule2 | rib中心对称 | 10 | BIG_IMAGE | — |
| Rule3 | rib左右对称 | 10 | BIG_IMAGE | — |
| Rule4 | 未实现 | None | — | 注释 |
| Rule5 | 分数已合并入rule1～4 | None | — | 注释 |
| Rule12 | 两个RIB间横向钢片及横沟连续性占比是否满足要求 | 6 | — | 删 3 字段，加 3 字段 |
| Rule16 | 中心RIB上的横沟或横向钢片可任意组合连续性 | 4 | — | 删 3 字段，加 continuity_mode_list |
| Rule17 | 边缘RIB上的横沟或横向钢片可任意组合连续性 | 6 | — | 删 3 字段，加 continuity_mode_list |

### 12.2 Executor 实现状态变更

| Rule | 旧状态 | 新状态 |
|------|--------|--------|
| Rule1 | 桩代码（空壳） | 完整实现（exec_feature + exec_score） |
| Rule2 | 桩代码（空壳） | 完整实现（exec_feature + exec_score） |
| Rule3 | 桩代码（空壳） | 完整实现（exec_feature + exec_score） |
| Rule4 | 桩代码（空壳） | 注释掉 |
| Rule5 | 桩代码（空壳） | 注释掉 |
| Rule12 | 桩代码（空壳） | 完整实现（exec_feature + exec_score） |
| Rule16 | 桩代码（空壳） | 完整实现（exec_feature + exec_score） |
| Rule17 | 桩代码（空壳） | 完整实现（exec_feature 含 TODO + exec_score） |

---

## 13. 需求边界

- **负责**：Config 字段增删改、Feature 字段增删改、Executor 的 exec_feature/exec_score 实现、节点注册列表更新
- **不负责**：核心检测算法实现（由 `src/core/detection/` 负责）、上下游 API 接口适配、测试用例编写
- Rule17 当前 `_EDGE_CONTINUITY_LIST` 为空，等待后续 `StitchingSchemeName` 枚举扩展后填充
