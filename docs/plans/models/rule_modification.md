# Rule1-5 / Rule12 / Rule16-17 修改实施文档

## 总体步骤

1. 修改 `src/models/rule_models.py` — Rule1-3 Config/Feature 改动
2. 修改 `src/models/rule_models.py` — Rule4-5 整段注释
3. 修改 `src/models/rule_models.py` — Rule12 Config/Feature 重构
4. 修改 `src/models/rule_models.py` — Rule16 Config 改动
5. 修改 `src/models/rule_models.py` — Rule17 Config/Feature 重构
6. 修改 `src/rules/executors/rule1.py` — 实现 exec_feature + exec_score
7. 修改 `src/rules/executors/rule2.py` — 实现 exec_feature + exec_score
8. 修改 `src/rules/executors/rule3.py` — 实现 exec_feature + exec_score
9. 修改 `src/rules/executors/rule4.py` — 整文件注释
10. 修改 `src/rules/executors/rule5.py` — 整文件注释
11. 修改 `src/rules/executors/rule12.py` — 实现 exec_feature + exec_score
12. 修改 `src/rules/executors/rule16.py` — 实现 exec_feature + exec_score
13. 修改 `src/rules/executors/rule17.py` — 实现 exec_feature + exec_score
14. 修改 `src/nodes/base.py` — STITCH_SCHEME_GENERATOR_CONFIGS 移除 Rule4/Rule5

---

## 步骤 1：修改 Rule1-3 Config/Feature — `src/models/rule_models.py`

### 1.1 修改 Rule1Config

找到（约第 179 行）：

```python
class Rule1Config(BaseRuleConfig):
    """Rule1：5个花纹RIB无对称原则"""
    description: str = "5个花纹RIB无对称原则"
    max_score: int = 8
```

改为：

```python
class Rule1Config(BaseRuleConfig):
    """Rule1：rib无对称"""
    description: str = "rib无对称"
    max_score: int = 10
    rule_type: RuleTypeEnum = RuleTypeEnum.BIG_IMAGE
```

### 1.2 修改 Rule2Config

找到（约第 185 行）：

```python
class Rule2Config(BaseRuleConfig):
    """Rule2：中心旋转180°对称花纹"""
    description: str = "中心旋转180°对称花纹"
    max_score: int = 8
```

改为：

```python
class Rule2Config(BaseRuleConfig):
    """Rule2：rib中心对称"""
    description: str = "rib中心对称"
    max_score: int = 10
    rule_type: RuleTypeEnum = RuleTypeEnum.BIG_IMAGE
```

### 1.3 修改 Rule3Config

找到（约第 191 行）：

```python
class Rule3Config(BaseRuleConfig):
    """Rule3：中心线镜像对称"""
    description: str = "中心线镜像对称"
    max_score: int = 8
```

改为：

```python
class Rule3Config(BaseRuleConfig):
    """Rule3：rib左右对称"""
    description: str = "rib左右对称"
    max_score: int = 10
    rule_type: RuleTypeEnum = RuleTypeEnum.BIG_IMAGE
```

### 1.4 修改 Rule1Feature（约第 207 行）

找到：

```python
@register_rule_feature
class Rule1Feature(BaseRuleFeature):
    """Rule1特征：横图拼接子规则，特征字段待业务细化"""
    pass
```

改为：

```python
@register_rule_feature
class Rule1Feature(BaseRuleFeature):
    """Rule1特征：rib无对称"""
    is_active: bool = Field(description="是否生效")
```

### 1.5 修改 Rule2Feature（约第 213 行）

找到：

```python
@register_rule_feature
class Rule2Feature(BaseRuleFeature):
    """Rule2特征：横图拼接子规则，特征字段待业务细化"""
    pass
```

改为：

```python
@register_rule_feature
class Rule2Feature(BaseRuleFeature):
    """Rule2特征：rib中心对称"""
    is_active: bool = Field(description="是否生效")
```

### 1.6 修改 Rule3Feature（约第 219 行）

找到：

```python
@register_rule_feature
class Rule3Feature(BaseRuleFeature):
    """Rule3特征：横图拼接子规则，特征字段待业务细化"""
    pass
```

改为：

```python
@register_rule_feature
class Rule3Feature(BaseRuleFeature):
    """Rule3特征：rib左右对称"""
    is_active: bool = Field(description="是否生效")
```

---

## 步骤 2：注释 Rule4 — `src/models/rule_models.py`

### 2.1 注释 Rule4Config（约第 197 行）

找到：

```python
class Rule4Config(BaseRuleConfig):
    """Rule4：中心线镜像对称可错位"""
    description: str = "中心线镜像对称可错位"
    max_score: int = 8
```

改为（整段注释）：

```python
# class Rule4Config(BaseRuleConfig):
#     """Rule4：未实现"""
#     description: str = "未实现"
#     # max_score 继承 BaseRuleConfig，默认 None
```

### 2.2 注释 Rule4Feature（约第 224 行）

找到：

```python
@register_rule_feature
class Rule4Feature(BaseRuleFeature):
    """Rule4特征：横图拼接子规则，特征字段待业务细化"""
    pass
```

改为：

```python
# @register_rule_feature
# class Rule4Feature(BaseRuleFeature):
#     """Rule4特征：未实现"""
#     pass
```

### 2.3 注释 Rule4Score（约第 249 行）

找到：

```python
@register_rule_score
class Rule4Score(BaseRuleScore):
    """Rule4评分"""
    pass
```

改为：

```python
# @register_rule_score
# class Rule4Score(BaseRuleScore):
#     """Rule4评分：未实现"""
#     pass
```

---

## 步骤 3：注释 Rule5 — `src/models/rule_models.py`

### 3.1 注释 Rule5Config（约第 203 行）

找到：

```python
class Rule5Config(BaseRuleConfig):
    """Rule5：根据用户指定的对称性进行输出"""
    description: str = "根据用户指定的对称性进行输出"
    max_score: int = 1
```

改为：

```python
# class Rule5Config(BaseRuleConfig):
#     """Rule5：分数已合并入rule1～4"""
#     description: str = "分数已合并入rule1～4"
#     # max_score 继承 BaseRuleConfig，默认 None
```

### 3.2 注释 Rule5Feature（约第 231 行）

找到：

```python
@register_rule_feature
class Rule5Feature(BaseRuleFeature):
    """Rule5特征：横图拼接子规则，特征字段待业务细化"""
    pass
```

改为：

```python
# @register_rule_feature
# class Rule5Feature(BaseRuleFeature):
#     """Rule5特征：分数已合并入rule1～4"""
#     pass
```

### 3.3 注释 Rule5Score（约第 255 行）

找到：

```python
@register_rule_score
class Rule5Score(BaseRuleScore):
    """Rule5评分"""
    pass
```

改为：

```python
# @register_rule_score
# class Rule5Score(BaseRuleScore):
#     """Rule5评分：分数已合并入rule1～4"""
#     pass
```

---

## 步骤 4：修改 Rule12 Config/Feature — `src/models/rule_models.py`

### 4.1 修改 Rule12Config（约第 453 行）

找到：

```python
class Rule12Config(BaseRuleConfig):
    """Rule12：两个RIB间横向钢片及横沟连续性占比60%-70%"""
    description: str = "两个RIB间横向钢片及横沟连续性占比60%-70%"
    max_score: int = 0
    continuity_mode: str = Field(description="连续性模式：RIB2-RIB3|RIB3-RIB4|RIB2-RIB3-RIB4|none")
    groove_width: float = Field(description="主沟宽度(像素)")
    blend_width: int = Field(description="融合宽度(像素)")
```

改为：

```python
class Rule12Config(BaseRuleConfig):
    """Rule12：两个RIB间横向钢片及横沟连续性占比是否满足要求"""
    description: str = "两个RIB间横向钢片及横沟连续性占比是否满足要求"
    max_score: int = 6
    continuity_ratio_upper: float = Field(description="连续性占比上界")
    continuity_ratio_lower: float = Field(description="连续性占比下界")
    continuity_mode_list: List[str] = Field(description="连续性模式列表")
```

### 4.2 修改 Rule12Feature（约第 462 行）

找到：

```python
@register_rule_feature
class Rule12Feature(BaseRuleFeature):
    """Rule12特征：RIB横向连续性"""
    is_continuous: bool = Field(description="是否连续")
```

改为：

```python
@register_rule_feature
class Rule12Feature(BaseRuleFeature):
    """Rule12特征：RIB横向连续性占比"""
    continuity_ratio: float = Field(description="连续性占比")
```

---

## 步骤 5：修改 Rule16 Config — `src/models/rule_models.py`

### 5.1 修改 Rule16Config（约第 553 行）

找到：

```python
class Rule16Config(BaseRuleConfig):
    """Rule16：RIB2/3/4上的横沟或横向钢片可任意组合连续性"""
    description: str = "RIB2/3/4上的横沟或横向钢片可任意组合连续性"
    max_score: int = 0
    continuity_mode: str = Field(description="三RIB组合模式")
    groove_width: float = Field(description="主沟宽度(像素)")
    blend_width: int = Field(description="融合宽度(像素)")
```

改为：

```python
class Rule16Config(BaseRuleConfig):
    """Rule16：中心RIB上的横沟或横向钢片可任意组合连续性"""
    description: str = "中心RIB上的横沟或横向钢片可任意组合连续性"
    max_score: int = 4
    continuity_mode_list: List[str] = Field(description="连续性模式列表")
```

### 5.2 Rule16Feature / Rule16Score 不变

`Rule16Feature` 保持 `is_continuous: bool` 不变，无需修改。

---

## 步骤 6：修改 Rule17 Config/Feature — `src/models/rule_models.py`

### 6.1 修改 Rule17Config（约第 562 行）

找到：

```python
class Rule17Config(BaseRuleConfig):
    """Rule17：RIB1与RIB2、RIB4与RIB5可连续可不连续，各占50%"""
    description: str = "RIB1与RIB2、RIB4与RIB5可连续可不连续，各占50%"
    max_score: int = 0
    edge_continuity_rib1_rib2: float = Field(ge=0, le=1, description="RIB1-RIB2连续概率")
    edge_continuity_rib4_rib5: float = Field(ge=0, le=1, description="RIB4-RIB5连续概率")
    blend_width: int = Field(description="融合宽度(像素)")
```

改为：

```python
class Rule17Config(BaseRuleConfig):
    """Rule17：边缘RIB上的横沟或横向钢片可任意组合连续性"""
    description: str = "边缘RIB上的横沟或横向钢片可任意组合连续性"
    max_score: int = 6
    continuity_mode_list: List[str] = Field(description="连续性模式列表")
```

### 6.2 修改 Rule17Feature（约第 577 行）

找到：

```python
@register_rule_feature
class Rule17Feature(BaseRuleFeature):
    """Rule17特征：RIB1/2与RIB4/5概率连续"""
    rib1_rib2_continuous: bool = Field(description="RIB1-RIB2是否连续")
    rib4_rib5_continuous: bool = Field(description="RIB4-RIB5是否连续")
```

改为：

```python
@register_rule_feature
class Rule17Feature(BaseRuleFeature):
    """Rule17特征：边缘RIB任意组合连续性"""
    is_continuous: bool = Field(description="是否连续")
```

---

## 步骤 7：实现 Rule1Executor — `src/rules/executors/rule1.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule1Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule1Executor(RuleExecutor):
    rule_cls = Rule1Config
```

改为：

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

---

## 步骤 8：实现 Rule2Executor — `src/rules/executors/rule2.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule2Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule2Executor(RuleExecutor):
    rule_cls = Rule2Config
```

改为：

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

## 步骤 9：实现 Rule3Executor — `src/rules/executors/rule3.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule3Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule3Executor(RuleExecutor):
    rule_cls = Rule3Config
```

改为：

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

## 步骤 10：注释 Rule4Executor — `src/rules/executors/rule4.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule4Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule4Executor(RuleExecutor):
    rule_cls = Rule4Config
```

改为（整文件注释）：

```python
# from src.models.rule_models import Rule4Config
# from src.rules.base import RuleExecutor
# from src.rules.registry import register_rule_executor
#
# @register_rule_executor
# class Rule4Executor(RuleExecutor):
#     rule_cls = Rule4Config
```

---

## 步骤 11：注释 Rule5Executor — `src/rules/executors/rule5.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule5Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule5Executor(RuleExecutor):
    rule_cls = Rule5Config
```

改为（整文件注释）：

```python
# from src.models.rule_models import Rule5Config
# from src.rules.base import RuleExecutor
# from src.rules.registry import register_rule_executor
#
# @register_rule_executor
# class Rule5Executor(RuleExecutor):
#     rule_cls = Rule5Config
```

---

## 步骤 12：实现 Rule12Executor — `src/rules/executors/rule12.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule12Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule12Executor(RuleExecutor):
    rule_cls = Rule12Config
```

改为：

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
        in_range = (
            config.continuity_ratio_lower
            <= feature.continuity_ratio
            <= config.continuity_ratio_upper
        )
        score = config.max_score if in_range else 0
        return Rule12Score(score=score)
```

---

## 步骤 13：实现 Rule16Executor — `src/rules/executors/rule16.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule16Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule16Executor(RuleExecutor):
    rule_cls = Rule16Config
```

改为：

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

---

## 步骤 14：实现 Rule17Executor — `src/rules/executors/rule17.py`

找到现有文件内容：

```python
from src.models.rule_models import Rule17Config
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule17Executor(RuleExecutor):
    rule_cls = Rule17Config
```

改为：

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

---

## 步骤 15：更新节点注册 — `src/nodes/base.py`

### 15.1 从导入块中移除 Rule4Config / Rule5Config

找到（约第 17-18 行）：

```python
    Rule4Config,
    Rule5Config,
```

改为（注释掉）：

```python
    # Rule4Config,  # 已注释
    # Rule5Config,  # 已注释
```

### 15.2 从 STITCH_SCHEME_GENERATOR_CONFIGS 中移除

找到（约第 49-51 行）：

```python
STITCH_SCHEME_GENERATOR_CONFIGS: list[type[BaseRuleConfig]] = [
    Rule1Config,
    Rule2Config,
    Rule3Config,
    Rule4Config,
    Rule5Config,
    Rule6AConfig,
    Rule7Config,
```

改为：

```python
STITCH_SCHEME_GENERATOR_CONFIGS: list[type[BaseRuleConfig]] = [
    Rule1Config,
    Rule2Config,
    Rule3Config,
    # Rule4Config,  # 已注释
    # Rule5Config,  # 已注释
    Rule6AConfig,
    Rule7Config,
```

---

## 步骤 16：更新 Executor 模块映射 — `src/rules/executors/__init__.py`

找到（约第 9-10 行）：

```python
    "Rule4Executor": "src.rules.executors.rule4",
    "Rule5Executor": "src.rules.executors.rule5",
```

改为（注释掉）：

```python
    # "Rule4Executor": "src.rules.executors.rule4",  # 已注释
    # "Rule5Executor": "src.rules.executors.rule5",  # 已注释
```

> **注意**：注释掉的是模块映射条目，不是整个 `_EXECUTOR_MODULES` dict。`rule4.py` 和 `rule5.py` 文件本身已在步骤 10/11 中注释。

---

## 变更清单

| 序号 | 文件 | 操作 | 说明 |
|------|------|------|------|
| 1 | `src/models/rule_models.py` | 修改 | Rule1Config: description→"rib无对称"、max_score→10、加 rule_type |
| 2 | `src/models/rule_models.py` | 修改 | Rule2Config: description→"rib中心对称"、max_score→10、加 rule_type |
| 3 | `src/models/rule_models.py` | 修改 | Rule3Config: description→"rib左右对称"、max_score→10、加 rule_type |
| 4 | `src/models/rule_models.py` | 修改 | Rule1-3Feature: 加 is_active: bool、改 docstring |
| 5 | `src/models/rule_models.py` | 注释 | Rule4Config/Feature/Score 整段注释 |
| 6 | `src/models/rule_models.py` | 注释 | Rule5Config/Feature/Score 整段注释 |
| 7 | `src/models/rule_models.py` | 修改 | Rule12Config: description/max_score→6、删 3 字段、加 3 字段 |
| 8 | `src/models/rule_models.py` | 修改 | Rule12Feature: is_continuous(bool)→continuity_ratio(float) |
| 9 | `src/models/rule_models.py` | 修改 | Rule16Config: description/max_score→4、删 3 字段、加 continuity_mode_list |
| 10 | `src/models/rule_models.py` | 修改 | Rule17Config: description/max_score→6、删 3 字段、加 continuity_mode_list |
| 11 | `src/models/rule_models.py` | 修改 | Rule17Feature: 两字段→is_continuous: bool |
| 12 | `src/rules/executors/rule1.py` | 修改 | 实现 exec_feature + exec_score |
| 13 | `src/rules/executors/rule2.py` | 修改 | 实现 exec_feature + exec_score |
| 14 | `src/rules/executors/rule3.py` | 修改 | 实现 exec_feature + exec_score |
| 15 | `src/rules/executors/rule4.py` | 注释 | 整文件注释 |
| 16 | `src/rules/executors/rule5.py` | 注释 | 整文件注释 |
| 17 | `src/rules/executors/rule12.py` | 修改 | 实现 exec_feature + exec_score |
| 18 | `src/rules/executors/rule16.py` | 修改 | 实现 exec_feature + exec_score |
| 19 | `src/rules/executors/rule17.py` | 修改 | 实现 exec_feature（含 TODO）+ exec_score |
| 20 | `src/rules/executors/__init__.py` | 修改 | 注释 Rule4Executor/Rule5Executor 模块映射 |
| 21 | `src/nodes/base.py` | 修改 | 导入 + STITCH_SCHEME_GENERATOR_CONFIGS 注释 Rule4/Rule5 |

---

## 验证清单

### 模型层验证

- [ ] `rule1 = Rule1Config()` 实例化后 `.name == "rule1"`、`.max_score == 10`、`.rule_type == RuleTypeEnum.BIG_IMAGE`
- [ ] `rule2 = Rule2Config()` 实例化后 `.name == "rule2"`、`.max_score == 10`、`.rule_type == RuleTypeEnum.BIG_IMAGE`
- [ ] `rule3 = Rule3Config()` 实例化后 `.name == "rule3"`、`.max_score == 10`、`.rule_type == RuleTypeEnum.BIG_IMAGE`
- [ ] `rule12 = Rule12Config()` 实例化后 `.name == "rule12"`、`.max_score == 6`、`.continuity_mode_list` 正常
- [ ] `rule16 = Rule16Config()` 实例化后 `.name == "rule16"`、`.max_score == 4`
- [ ] `rule17 = Rule17Config()` 实例化后 `.name == "rule17"`、`.max_score == 6`
- [ ] `Rule4Config` / `Rule5Config` 已被注释，import 时报 ImportError
- [ ] `Rule12Feature.continuity_ratio` 为 float 类型
- [ ] `Rule17Feature` 只有 `is_continuous: bool`，不再有 `rib1_rib2_continuous` / `rib4_rib5_continuous`

### 执行器验证

- [ ] `get_rule_executor("rule1")` 返回 `Rule1Executor` 实例
- [ ] `get_rule_executor("rule2")` 返回 `Rule2Executor` 实例
- [ ] `get_rule_executor("rule3")` 返回 `Rule3Executor` 实例
- [ ] `get_rule_executor("rule12")` 返回 `Rule12Executor` 实例
- [ ] `get_rule_executor("rule16")` 返回 `Rule16Executor` 实例
- [ ] `get_rule_executor("rule17")` 返回 `Rule17Executor` 实例
- [ ] `get_rule_executor("rule4")` 抛出 ValueError（注册已取消）
- [ ] `get_rule_executor("rule5")` 抛出 ValueError（注册已取消）

### Rule1-3 血缘匹配验证

- [ ] BigImage + `SYMMETRY_0` → `Rule1Feature.is_active == True`
- [ ] BigImage + `SYMMETRY_1` → `Rule1Feature.is_active == False`
- [ ] BigImage + `SYMMETRY_1` → `Rule2Feature.is_active == True`
- [ ] BigImage + `SYMMETRY_0` → `Rule2Feature.is_active == False`
- [ ] BigImage + `SYMMETRY_2` → `Rule3Feature.is_active == True`
- [ ] BigImage + `SYMMETRY_0` → `Rule3Feature.is_active == False`
- [ ] SmallImage（无 lineage）→ `is_active == False`
- [ ] BigImage + `lineage is None` → `is_active == False`

### Rule12 连续性占比验证

- [ ] `continuity_mode_list = ["continuity_1", "continuity_2"]` → `continuity_ratio = 1.0`
- [ ] `continuity_mode_list = ["continuity_0", "continuity_1"]` → `continuity_ratio = 0.5`
- [ ] `continuity_mode_list = ["continuity_0", "continuity_0"]` → `continuity_ratio = 0.0`
- [ ] `continuity_mode_list = []` → `continuity_ratio = 0.0`
- [ ] ratio 在下界与上界之间 → `score = 6`
- [ ] ratio 不在范围内 → `score = 0`

### Rule16 连续性匹配验证

- [ ] BigImage + `CONTINUITY_1` → `is_continuous == True`
- [ ] BigImage + `CONTINUITY_2` → `is_continuous == True`
- [ ] BigImage + `CONTINUITY_3` → `is_continuous == True`
- [ ] BigImage + `CONTINUITY_0` → `is_continuous == False`
- [ ] BigImage + `SYMMETRY_0` → `is_continuous == False`
- [ ] is_continuous == True → `score = 4`
- [ ] is_continuous == False → `score = 0`

### Rule17 验证

- [ ] 任何输入 → `is_continuous == False`（列表为空）
- [ ] `score == 0`

### 节点注册验证

- [ ] `STITCH_SCHEME_GENERATOR_CONFIGS` 不包含 `Rule4Config`、`Rule5Config`
- [ ] `STITCH_SCHEME_GENERATOR_CONFIGS` 仍包含 `Rule1/2/3/6A/7/12/16/17/19/100/101/102Config`

### 回归验证

- [ ] 现有测试全部通过（Rule4/5 注释不影响其他规则）
- [ ] `load_all_executors()` 不报错（Rule4/5 模块映射虽然注释了，但 `_EXECUTOR_MODULES` 中无对应条目，`__init__.py` 的 lazy-loading 不会触发 import）
