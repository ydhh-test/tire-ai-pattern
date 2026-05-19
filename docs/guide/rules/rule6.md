# Rule 6_1 连续性规则说明

`src.rules.executors.rule6` 实现了 Rule 6_1 的规则层逻辑，负责判定轮胎小图花纹是否连续，并输出相应评分。该模块属于规则层（rule layer），只负责规则判定与特征/得分的结构化表达，不直接实现底层图像算法。

## 适用场景

- 小图评估链路：对每张小图调用规则层，判断其花纹是否连续。
- 规则层单元测试：通过 mock 算法层，验证规则层的入参、出参和评分逻辑。
- 调试/可视化：在 `is_debug=True` 时，规则层可透传算法层的中间可视化产物，便于人工排查。

不适合在该模块内完成的工作：
- 具体的图像处理与花纹检测（应由算法层实现）。
- 图片的物理删除、保存、移动。
- `.results/` 目录组织、task_id、pipeline 调度等上层流程。

## 快速开始

```python
from src.rules.executors.rule6 import Rule6Executor, Rule6Config, Rule6Feature
from src.models.image_models import BaseImage

# 构造规则配置
config = Rule6Config(is_debug=True)

# 构造小图对象（假设 image_base64 已准备好）
image = BaseImage(image_base64=...)

# 执行规则层特征提取
feature = Rule6Executor().exec_feature(image, config)

# 执行规则层评分
score = Rule6Executor().exec_score(config, feature)

print(feature.is_continuous, score.score)
```

## API 入口

### `Rule6Executor.exec_feature`

```python
def exec_feature(self, image: BaseImage, config: Rule6Config) -> Rule6Feature
```

- 解码 base64 图片，转灰度，调用算法层 `detect_pattern_continuity`。
- 返回 `Rule6Feature(is_continuous=...)`。
- 若 `is_debug=True` 且算法层返回可视化产物，则透传 `vis_names`、`vis_images`。

### `Rule6Executor.exec_score`

```python
def exec_score(self, config: Rule6Config, feature: Rule6Feature) -> Rule6Score
```

- 连续返回 `config.max_score`，不连续返回 0。

## 规则层与算法层分工

- 规则层（本模块）：只负责结构化特征、评分、可视化透传，不直接处理图像细节。
- 算法层（如 `src.core.detection.pattern_continuity`）：只负责图像花纹检测，不关心规则评分。

## 调试与可视化

- `Rule6Config.is_debug=True` 时，算法层可返回中间可视化产物，规则层会以 `vis_names`、`vis_images` 字段透传，便于人工排查。

## 单元测试建议

- 推荐对规则层进行 mock 算法的单元测试，重点验证入参、出参和评分逻辑。
- 详见 `tests/unittests/rules/test_rule6.py`。
