# Rule100 / Rule101 / Rule102 实施文档

## 总体步骤

1. 调整 `BaseRuleConfig.max_score` 和 `BaseRuleScore.score` 为 `Optional[int]`
2. 新增 `RibSizeItem` / `GrooveSizeItem` / `DecorationItem` 子模型
3. 新增 Rule100 / 101 / 102 的 Config / Feature / Score 类
4. 新建三个 Executor 文件并注册
5. 在 `nodes/base.py` 中导入并加入节点配置列表

---

## 步骤 1：调整基类 — `src/models/rule_models.py`

### 1.1 更新 `BaseRuleConfig.max_score`

找到：

```python
class BaseRuleConfig(BaseModel):
    description: str = Field(description="规则描述")
    max_score: int = Field(ge=0, description="最大可得分")
```

改为：

```python
class BaseRuleConfig(BaseModel):
    description: str = Field(description="规则描述")
    max_score: Optional[int] = Field(default=None, ge=0, description="最大可得分，None表示非打分规则")
```

### 1.2 更新 `BaseRuleScore.score`

找到：

```python
class BaseRuleScore(BaseModel):
    score: int = Field(description="得分")
```

改为：

```python
class BaseRuleScore(BaseModel):
    score: Optional[int] = Field(default=None, description="得分，None表示不参与评分")
```

---

## 步骤 2：新增子模型 — `src/models/rule_models.py`

在文件末尾（第十八部分之前或之后的合适位置）新增三个 Item 类：

```python
# ============================================================
# 第十八部分：Rule100-102 辅助 Item 模型
# ============================================================

class RibSizeItem(BaseModel):
    """单个 RIB 的尺寸配置"""
    rib_name: str = Field(description="RIB名称，如 rib1、rib2")
    num_pitchs: int = Field(ge=1, description="节距数量")
    rib_width: int = Field(ge=1, description="纵向图宽度(像素)")
    rib_height: int = Field(ge=1, description="纵向图高度(像素)")


class GrooveSizeItem(BaseModel):
    """单个主沟的尺寸配置"""
    groove_width: int = Field(ge=1, description="主沟宽度(像素)")
    groove_height: int = Field(ge=1, description="主沟高度(像素)")


class DecorationItem(BaseModel):
    """单个装饰的尺寸与透明度配置"""
    position: str = Field(description="装饰位置：left / right")
    decoration_width: int = Field(ge=1, description="装饰宽度(像素)")
    decoration_height: int = Field(ge=1, description="装饰高度(像素)")
    decoration_opacity: int = Field(ge=0, le=255, description="装饰透明度(0-255)")
```

---

## 步骤 3：新增 Rule100/101/102 — `src/models/rule_models.py`

在同一区块继续新增：

```python
# ============================================================
# 第十九部分：Rule100-102 纯配置型规则
# ============================================================

class Rule100Config(BaseRuleConfig):
    """Rule100：RIB 节距/尺寸配置"""
    description: str = "RIB 节距与尺寸配置"
    # max_score 继承 BaseRuleConfig，默认 None
    rib_number: int = Field(ge=1, description="RIB 数量")
    rib_sizes: List[RibSizeItem] = Field(min_length=1, description="每个RIB的尺寸配置列表")


class Rule101Config(BaseRuleConfig):
    """Rule101：主沟尺寸配置"""
    description: str = "主沟尺寸配置"
    groove_sizes: List[GrooveSizeItem] = Field(min_length=1, description="每个主沟的尺寸配置列表")


class Rule102Config(BaseRuleConfig):
    """Rule102：装饰边框配置"""
    description: str = "装饰边框尺寸与透明度配置"
    decorations: List[DecorationItem] = Field(min_length=1, description="左右装饰配置列表")


@register_rule_feature
class Rule100Feature(BaseRuleFeature):
    """Rule100 特征（纯配置型，无特征提取）"""
    pass


@register_rule_feature
class Rule101Feature(BaseRuleFeature):
    """Rule101 特征（纯配置型，无特征提取）"""
    pass


@register_rule_feature
class Rule102Feature(BaseRuleFeature):
    """Rule102 特征（纯配置型，无特征提取）"""
    pass


@register_rule_score
class Rule100Score(BaseRuleScore):
    """Rule100 评分（纯配置型，无评分）"""
    pass


@register_rule_score
class Rule101Score(BaseRuleScore):
    """Rule101 评分（纯配置型，无评分）"""
    pass


@register_rule_score
class Rule102Score(BaseRuleScore):
    """Rule102 评分（纯配置型，无评分）"""
    pass
```

> 注意：由于 `BaseRuleConfig.max_score` 已改为 `Optional[int] = None`，三个 Config 无需显式声明 `max_score`，会自动继承默认值 `None`。

---

## 步骤 4：新建 Executor 文件

### 4.1 `src/rules/executors/rule100.py`

```python
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

### 4.2 `src/rules/executors/rule101.py`

```python
from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import (
    BaseRuleFeature, BaseRuleScore,
    Rule101Config, Rule101Feature, Rule101Score,
)
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule101Executor(RuleExecutor):
    rule_cls = Rule101Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule101Config,
    ) -> BaseRuleFeature:
        return Rule101Feature()

    def exec_score(
        self,
        config: Rule101Config,
        feature: Rule101Feature,
    ) -> BaseRuleScore:
        return Rule101Score(score=None)
```

### 4.3 `src/rules/executors/rule102.py`

```python
from __future__ import annotations

from src.models.image_models import BaseImage
from src.models.rule_models import (
    BaseRuleFeature, BaseRuleScore,
    Rule102Config, Rule102Feature, Rule102Score,
)
from src.rules.base import RuleExecutor
from src.rules.registry import register_rule_executor


@register_rule_executor
class Rule102Executor(RuleExecutor):
    rule_cls = Rule102Config

    def exec_feature(
        self,
        image: BaseImage,
        config: Rule102Config,
    ) -> BaseRuleFeature:
        return Rule102Feature()

    def exec_score(
        self,
        config: Rule102Config,
        feature: Rule102Feature,
    ) -> BaseRuleScore:
        return Rule102Score(score=None)
```

---

## 步骤 5：注册 Executor — `src/rules/executors/__init__.py`

### 5.1 在文件顶部导入区域追加：

```python
from src.rules.executors.rule100 import Rule100Executor
from src.rules.executors.rule101 import Rule101Executor
from src.rules.executors.rule102 import Rule102Executor
```

### 5.2 在 `__all__` 列表末尾追加：

```python
    "Rule100Executor",
    "Rule101Executor",
    "Rule102Executor",
```

---

## 步骤 6：节点层注册 — `src/nodes/base.py`

### 6.1 在 `from src.models.rule_models import (...)` 导入块中追加：

```python
    Rule100Config,
    Rule101Config,
    Rule102Config,
```

### 6.2 在 `STITCH_SCHEME_GENERATOR_CONFIGS` 列表末尾追加：

```python
    Rule100Config,
    Rule101Config,
    Rule102Config,
```

---

## 步骤 7：修复 `_recalculate_total` — `src/models/image_models.py`

找到 `ImageEvaluation._recalculate_total` 方法（约第 142 行），修改过滤条件：

```diff
      self.current_score = sum(
          r.score.score for r in self.rules
-         if r.score is not None
+         if r.score is not None and r.score.score is not None
      )
```

---

## 步骤 8：更新文件头部注释 — `src/models/rule_models.py`

在文件顶部摘要注释中追加新规则编号说明：

```diff
  #   - Rule1-22Config / Rule1-22Feature / Rule1-22Score（22个规则）
+ #   - RibSizeItem / GrooveSizeItem / DecorationItem（Rule100-102 辅助模型）
+ #   - Rule100-102Config / Rule100-102Feature / Rule100-102Score（3个纯配置型规则）
```

并在文件末尾的注释块中体现步骤 2 和步骤 3 新增的两个分区。

---

## 变更清单

| 序号 | 文件 | 操作 | 说明 |
|---|---|---|---|
| 1 | `src/models/rule_models.py` | 修改 | `BaseRuleConfig.max_score` → `Optional[int] = None` |
| 2 | `src/models/rule_models.py` | 修改 | `BaseRuleScore.score` → `Optional[int] = None` |
| 3 | `src/models/rule_models.py` | 新增 | `RibSizeItem` / `GrooveSizeItem` / `DecorationItem` |
| 4 | `src/models/rule_models.py` | 新增 | `Rule100/101/102 Config/Feature/Score`（共 9 个类） |
| 5 | `src/models/rule_models.py` | 修改 | 文件头部注释追加新规则摘要 |
| 6 | `src/models/image_models.py` | 修改 | `_recalculate_total()` 增加 `score.score is not None` |
| 7 | `src/rules/executors/rule100.py` | 新建 | `Rule100Executor` |
| 8 | `src/rules/executors/rule101.py` | 新建 | `Rule101Executor` |
| 9 | `src/rules/executors/rule102.py` | 新建 | `Rule102Executor` |
| 10 | `src/rules/executors/__init__.py` | 修改 | 导入并导出 3 个新 Executor |
| 11 | `src/nodes/base.py` | 修改 | 导入 + `STITCH_SCHEME_GENERATOR_CONFIGS` 追加 |

---

## 验证清单

- [ ] `BaseRuleConfig.max_score` 默认值为 `None`，现有规则 `max_score: int = 8` 仍然正常
- [ ] `BaseRuleScore.score` 默认值为 `None`，现有 `exec_score()` 返回 `score=5` 仍然正常
- [ ] 三个新 Rule 实例化时 `config.name` 返回 `"rule100"` / `"rule101"` / `"rule102"`
- [ ] `get_feature_class("rule100")` / `get_score_class("rule100")` 能正常返回对应类
- [ ] `get_rule_executor("rule100")` 能正常返回 `Rule100Executor` 实例
- [ ] `_recalculate_total()` 在 score 为 `None` 的规则存在时不会报错
- [ ] 现有测试全部通过（BaseRuleConfig/BaseRuleScore 的改动不破坏已有逻辑）
