# Rule 8 横沟数量规则说明

`src.rules.executors.rule8` 实现了 Rule 8 的规则层逻辑，负责统计轮胎小图中的横沟数量，并输出相应评分。该模块属于规则层（rule layer），只负责规则判定与特征/得分的结构化表达，不直接实现底层图像算法。

## 适用场景

- 小图评估链路：对每张小图调用规则层，判断是否检测到横沟，并给出 Rule 8 得分。
- 规则层单元测试：通过 mock 算法层，验证规则层的入参、出参和评分逻辑。
- 链路连通性验证：可使用真实图片样例，确认规则层到算法层的完整调用链路可正常运行。

不适合在该模块内完成的工作：
- 具体的图像处理、横沟提取与交点检测（应由算法层实现）。
- 图片的物理删除、保存、移动。
- `.results/` 目录组织、task_id、pipeline 调度等上层流程。

## 快速开始

```python
from src.rules.executors.rule8 import Rule8Executor
from src.models.rule_models import Rule8Config
from src.models.enums import RuleTypeEnum
from src.models.image_models import BaseImage

# 构造规则配置
config = Rule8Config(
    max_score=4,
    rule_type=RuleTypeEnum.BIG_IMAGE,
    groove_width_center=25.0,
    groove_width_side=13.0,
)

# 构造小图对象（假设 image_base64 已准备好）
image = BaseImage(image_base64=...)

# 执行规则层特征提取
feature = Rule8Executor().exec_feature(image, config)

# 执行规则层评分
score = Rule8Executor().exec_score(config, feature)

print(feature.num_transverse_grooves, score.score)
```

## API 入口

### `Rule8Executor.exec_feature`

```python
def exec_feature(self, image: BaseImage, config: Rule8Config) -> Rule8Feature
```

- 解码 base64 图片为 BGR ndarray。
- 根据 `image.biz.region` 选择横沟宽度参数：
  - `RegionEnum.CENTER` 使用 `config.groove_width_center`
  - `RegionEnum.SIDE` 使用 `config.groove_width_side`
- 将宽度参数四舍五入为整数，并保证最小值为 1。
- 调用算法层 `detect_transverse_grooves`。
- 返回 `Rule8Feature(num_transverse_grooves=...)`。

### `Rule8Executor.exec_score`

```python
def exec_score(self, config: Rule8Config, feature: Rule8Feature) -> Rule8Score
```

- 当 `feature.num_transverse_grooves > 0` 时返回 `config.max_score`。
- 当未检测到横沟时返回 0。

## 规则层与算法层分工

- 规则层（本模块）：只负责结构化特征、评分和参数选择，不直接处理图像细节。
- 算法层（`src.core.detection.groove_intersection`）：只负责横沟检测与交点统计，不关心 Rule 8 评分。

## 参数选择说明

- Rule 8 的规则层显式区分 center 和 side 两类图片。
- `_select_groove_width_px()` 会根据 `image.biz.region` 选择不同配置值，并转换为算法层需要的整数像素宽度。
- 这样可以把业务配置保留在规则层，算法层只接收明确的图像与数值参数。

## 调试与可视化

- 当前 `Rule8Executor` 不透传算法层的 debug 可视化结果。
- `Rule8Feature.vis_names / vis_images` 在当前实现中保持为 `None`。
- 如需可视化排查，应直接在算法层 `src.core.detection.groove_intersection` 中开启和验证 debug 输出。

## 单元测试建议

- 推荐对规则层进行 mock 算法的单元测试，重点验证入参、出参和评分逻辑。
- 可额外加入少量真实图片链路测试，验证 `exec_feature -> detect_transverse_grooves` 是否真正打通。
- 详见 `tests/unittests/rules/test_rule8.py`。
