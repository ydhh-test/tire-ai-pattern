# Nodes 层设计方案

## 1. 当前范围

本设计先细化可以直接推进的 3 个节点：

- `Node1 small_image_evaluator`：小图列表评估。
- `Node4 big_image_evaluator`：单张大图评估。
- `Node5 geometry_scorer`：基于已有 feature / lineage 的业务评分。

暂不展开的节点：

- `Node2 stitch_scheme_generator`：由模板调用生成拼接方案，先保留接口边界。
- `Node3 big_image_stitcher`：由模板执行拼接方案，先保留接口边界。
- `Node6 big_image_splitter`：由额外拆分方法提供，先保留接口边界。

本阶段重点是：节点如何调用 `RuleRunner`，以及如何把结果写回 `TireStruct` / `ImageEvaluation`。

## 2. 核心边界

`src.nodes` 是 pipeline 中的节点编排层。

节点层负责：

- 遍历业务对象。
- 准备 rule 调用入参。
- 调用 `RuleRunner`。
- 初始化并写回 `ImageEvaluation` / `RuleEvaluation`。
- 更新 `current_score`。
- 写回 `TireStruct.small_images` / `TireStruct.big_image`。

节点层不负责：

- 不实现单条规则逻辑。
- 不直接调用底层图像算法。
- 不在节点里计算具体 feature / score。
- 不让 core 认识 `RuleConfig`。
- 不负责 API 协议适配。
- 不负责 debug 文件落盘。

规则调用链路固定为：

```text
node
  -> RuleRunner
    -> RuleExecutor
      -> core algorithm
```

## 3. Rule 调用基本协议

节点不直接调用算法，只通过 `RuleRunner` 调 rule。

当前评估类节点只需要两类能力：

```python
feature = runner.exec_feature(image, config)
score = runner.exec_score(config, feature)
```

`RuleRunner` 使用 `config.name` 查找对应 executor。节点不传 `rule_name`，也不理解单条规则内部逻辑。

节点负责把 `config / feature / score` 组装为：

```python
RuleEvaluation(
    name=config.name,
    config=config,
    feature=feature,
    score=score,
)
```

并放入：

```python
ImageEvaluation.rules
ImageEvaluation.current_score
```

## 4. Node RuleConfig 使用策略

用户会把所有 rule 都放入 `TireStruct.rules_config`。

节点不按 `activation_node_name` 作为主准入条件，而是由每个 node 自己声明当前能使用哪些 `RuleConfig` 类型。

第一阶段不引入额外的 capability 系统。节点通过有序 config class 列表关联 rule：

```text
Node1 small_image_evaluator:
  [Rule6Config, Rule11Config]

Node2 stitch_scheme_generator:
  [Rule1Config, Rule2Config, Rule3Config, Rule4Config, Rule5Config,
   Rule6AConfig, Rule7Config, Rule12Config, Rule16Config, Rule17Config,
   Rule19Config]

Node3 big_image_stitcher:
  不直接消费 RuleConfig，只执行 Node2 生成的 StitchingScheme。

Node4 big_image_evaluator:
  [Rule8Config, Rule13Config, Rule14Config, Rule15Config,
   Rule18Config, Rule21Config, Rule22Config]

Node5 geometry_scorer:
  [Rule8Config, Rule13Config, Rule14Config, Rule15Config,
   Rule18Config, Rule21Config, Rule22Config]

Node6 big_image_splitter:
  当前由额外方法提供，暂不声明 RuleConfig。
```

`Node1` 当前只使用 `Rule6Config` 和 `Rule11Config`：

- `Rule6Config`：小图图案连续性检测，对应旧 `rule6_1`。
- `Rule11Config`：小图纵向细沟 / 纵向钢片检测，对应旧 `rule11`。

虽然旧 dev 中 `rule8_14` 也能处理 `center_inf / side_inf`，但它没有进入旧 `postprocessor.py` 主流程；本阶段不放入 Node1，避免扩大 Node1 职责。

建议在 `src.nodes.rule_configs` 中独立声明每个 node 的 configs 常量。

不要使用 `NODE_RULE_CONFIGS[node_name]` 这类中心化动态索引。每个 node 文件显式导入自己要用的 configs 常量。

```python
SMALL_IMAGE_EVALUATOR_CONFIGS = [
    Rule6Config,
    Rule11Config,
]

STITCH_SCHEME_GENERATOR_CONFIGS = [
    Rule1Config,
    Rule2Config,
    Rule3Config,
    Rule4Config,
    Rule5Config,
    Rule6AConfig,
    Rule7Config,
    Rule12Config,
    Rule16Config,
    Rule17Config,
    Rule19Config,
]

BIG_IMAGE_EVALUATOR_CONFIGS = [
    Rule8Config,
    Rule13Config,
    Rule14Config,
    Rule15Config,
    Rule18Config,
    Rule21Config,
    Rule22Config,
]

GEOMETRY_SCORER_CONFIGS = [
    Rule8Config,
    Rule13Config,
    Rule14Config,
    Rule15Config,
    Rule18Config,
    Rule21Config,
    Rule22Config,
]
```

再提供统一选择函数：

```python
def select_node_configs(
    rules_config: list[BaseRuleConfig],
    ordered_config_types: list[type[BaseRuleConfig]],
) -> list[BaseRuleConfig]:
    config_by_type = {type(config): config for config in rules_config}

    return [
        config_by_type[config_type]
        for config_type in ordered_config_types
        if config_type in config_by_type
    ]
```

node 内使用方式：

```python
from src.nodes.rule_configs import SMALL_IMAGE_EVALUATOR_CONFIGS
from src.nodes.rule_configs import select_node_configs


configs = select_node_configs(
    tire_struct.rules_config,
    SMALL_IMAGE_EVALUATOR_CONFIGS,
)
```

如果用户没有提供某个节点需要的 config，该节点不自动补默认值。默认值由 API / config 层决定。

排序规则：

- 各 node 独立 configs 常量中的列表顺序就是节点执行顺序。
- 不使用用户传入 `rules_config` 的原始顺序。
- 不使用 `activation_node_name` 排序。
- 同一种 `RuleConfig` 不建议重复出现；如果重复出现，默认报错，避免同一规则被执行两次后覆盖结果。

重复配置校验：

```python
def validate_no_duplicate_config_types(configs: list[BaseRuleConfig]) -> None:
    seen: set[type[BaseRuleConfig]] = set()
    for config in configs:
        config_type = type(config)
        if config_type in seen:
            raise ValueError(f"duplicate rule config: {config.name}")
        seen.add(config_type)
```

## 5. 通用评估写回流程

Node1 和 Node4 都属于“feature + score”评估节点，流程一致：

```text
input image + configs
  -> 初始化 ImageEvaluation
  -> 对每个 config 调 runner.exec_feature(image, config)
  -> 对每个 feature 调 runner.exec_score(config, feature)
  -> 写入 RuleEvaluation
  -> 汇总 current_score
  -> 写回 image.evaluation
```

建议抽一个 nodes 内部 helper：

```python
from src.models.image_models import BaseImage, ImageEvaluation, RuleEvaluation
from src.models.rule_models import BaseRuleConfig
from src.rules.runner import RuleRunner


def evaluate_image_with_configs(
    image: BaseImage,
    configs: list[BaseRuleConfig],
    runner: RuleRunner,
) -> ImageEvaluation:
    rule_evaluations = []

    for config in configs:
        feature = runner.exec_feature(image, config)
        score = runner.exec_score(config, feature)
        rule_evaluations.append(
            RuleEvaluation(
                name=config.name,
                config=config,
                feature=feature,
                score=score,
            )
        )

    return ImageEvaluation(rules=rule_evaluations)
```

`ImageEvaluation` 自身会在 `set_score` 时重算总分；如果直接构造 rules，则 helper 需要显式设置 `current_score`，或者构造后调用内部汇总方法。推荐实现时不要依赖私有方法，直接计算：

```python
evaluation.current_score = sum(
    rule.score.score
    for rule in evaluation.rules
    if rule.score is not None
)
```

## 6. Node 入参与出参总表

所有 pipeline 的主状态对象都是 `TireStruct`。节点可以额外接收上一个节点的中间产物，但最终需要写回 `TireStruct` 或返回明确中间对象。

| Node | 函数 | 入参 | 出参 | 写回字段 |
| --- | --- | --- | --- | --- |
| Node1 | `evaluate_small_images` | `TireStruct` | `TireStruct` | `small_images[*].evaluation`, `flag`, `err_msg` |
| Node2 | `generate_stitch_scheme` | `TireStruct` | `StitchingScheme` | 不直接写回，交给 Node3 写入 lineage |
| Node3 | `stitch_big_image` | `TireStruct`, `StitchingScheme` | `TireStruct` | `big_image`, `big_image.lineage`, `flag`, `err_msg` |
| Node4 | `evaluate_big_image` | `TireStruct` | `TireStruct` | `big_image.evaluation`, `flag`, `err_msg` |
| Node5 | `score_geometry` | `TireStruct` | `TireStruct` | `big_image.evaluation.rules[*].score`, `big_image.evaluation.current_score`, `flag`, `err_msg` |
| Node6 | `split_big_image` | `TireStruct` | `TireStruct` | `small_images`, `flag`, `err_msg` |

建议接口汇总：

```python
def evaluate_small_images(tire_struct: TireStruct) -> TireStruct:
    ...


def generate_stitch_scheme(tire_struct: TireStruct) -> StitchingScheme:
    ...


def stitch_big_image(
    tire_struct: TireStruct,
    stitching_scheme: StitchingScheme,
) -> TireStruct:
    ...


def evaluate_big_image(tire_struct: TireStruct) -> TireStruct:
    ...


def score_geometry(tire_struct: TireStruct) -> TireStruct:
    ...


def split_big_image(tire_struct: TireStruct) -> TireStruct:
    ...
```

Pipeline 中的调用关系：

```text
Pipeline-1:
  TireStruct(small_images, rules_config, scheme_rank)
    -> Node1 returns TireStruct
    -> Node2 returns StitchingScheme
    -> Node3 returns TireStruct(big_image)
    -> Node4 returns TireStruct(big_image.evaluation)
    -> Node5 returns TireStruct(big_image.evaluation.current_score)

Pipeline-2:
  TireStruct(big_image, rules_config)
    -> Node3 returns TireStruct(big_image)

Pipeline-3:
  TireStruct(big_image, rules_config)
    -> Node4 returns TireStruct(big_image.evaluation)
    -> Node5 returns TireStruct(big_image.evaluation.current_score)

Pipeline-4:
  TireStruct(big_image, rules_config)
    -> Node6 returns TireStruct(small_images)
```

## 7. Node1: small_image_evaluator

定位：小图列表评估节点。

输入：

- `TireStruct.small_images`
- 当前节点需要执行的 rule configs

输出：

- 每张 `SmallImage.evaluation`
- `TireStruct.small_images`
- 失败时更新 `TireStruct.flag / TireStruct.err_msg`

执行流程：

```text
1. 校验 tire_struct.small_images 非空。
2. 获取 Node1 当前要执行的 configs。
3. 遍历 small_images。
4. 对每张 small_image 调 evaluate_image_with_configs。
5. 将返回的 ImageEvaluation 写回 small_image.evaluation。
6. 所有小图处理成功后，tire_struct.flag = True。
7. 任一规则调用失败时，tire_struct.flag = False，并写 err_msg。
```

建议接口：

```python
from src.models.tire_struct import TireStruct


def evaluate_small_images(tire_struct: TireStruct) -> TireStruct:
    ...
```

关键约束：

- 小图是列表，必须逐张处理。
- 每张小图独立拥有自己的 `ImageEvaluation`。
- Node1 不删除小图。
- 如果旧流程中的 rule 会做“筛掉图片”，新流程应先写成 feature / score / status，不在 Node1 直接删除。
- Node1 不生成大图、不拼接、不落盘 debug。

旧 dev 对应关系：

- `rule6_1.process_pattern_continuity`：旧流程会复制目录并删除不连续图片；新流程应由 rule executor 返回连续性 feature / score。
- `rule11.process_longitudinal_grooves`：旧流程遍历 `center_inf / side_inf`；新流程遍历 `TireStruct.small_images`。

Node1 configs：

```python
SMALL_IMAGE_EVALUATOR_CONFIGS = [
    Rule6Config,
    Rule11Config,
]
```

Node1 验证：

- `small_images` 必须非空。
- `rules_config` 中同一种 `RuleConfig` 不能重复。
- 选出的 configs 可以为空；为空时表示本节点不执行任何小图 rule，但仍返回原 `TireStruct`。
- 如果选出的 config 对应 executor 未实现 `exec_feature` 或 `exec_score`，由 `RuleRunner` / executor 抛错，Node1 捕获后写入 `flag=False` 和 `err_msg`。

Node1 顺序影响：

- `Rule6Config` 先于 `Rule11Config`。
- 当前两个 rule 都只写自己的 `RuleEvaluation`，理论上没有强数据依赖。
- 保留固定顺序是为了让 `ImageEvaluation.rules` 稳定，便于测试、追踪和前端展示。

## 8. Node4: big_image_evaluator

定位：单张大图评估节点。

输入：

- `TireStruct.big_image`
- 当前节点需要执行的 rule configs

输出：

- `BigImage.evaluation`
- `TireStruct.big_image`
- 失败时更新 `TireStruct.flag / TireStruct.err_msg`

执行流程：

```text
1. 校验 tire_struct.big_image 存在。
2. 获取 Node4 当前要执行的 configs。
3. 对 tire_struct.big_image 调 evaluate_image_with_configs。
4. 将返回的 ImageEvaluation 写回 big_image.evaluation。
5. 处理成功后，tire_struct.flag = True。
6. 规则调用失败时，tire_struct.flag = False，并写 err_msg。
```

建议接口：

```python
from src.models.tire_struct import TireStruct


def evaluate_big_image(tire_struct: TireStruct) -> TireStruct:
    ...
```

关键约束：

- 大图是单个对象，不做列表遍历。
- Node4 可以重新跑图像检测类 feature。
- Node4 负责 `feature + score` 的完整评估写回。
- Node4 不生成拼接方案、不执行拼接、不拆分大图。

旧 dev 对应关系：

- `rule13.process_horizontal_image_score`：旧流程遍历输出目录中的横图；新流程只处理当前 `TireStruct.big_image`。
- 未来如果 rule8 / rule14 等规则需要重新看大图，也应放入 Node4，而不是 Node5。

Node4 configs：

```python
BIG_IMAGE_EVALUATOR_CONFIGS = [
    Rule8Config,
    Rule13Config,
    Rule14Config,
    Rule15Config,
    Rule18Config,
    Rule21Config,
    Rule22Config,
]
```

Node4 验证：

- `big_image` 必须存在。
- `rules_config` 中同一种 `RuleConfig` 不能重复。
- 选出的 configs 可以为空；为空时表示本节点不执行任何大图检测评分。
- 如果选出的 config 对应 executor 未实现 `exec_feature` 或 `exec_score`，由 `RuleRunner` / executor 抛错，Node4 捕获后写入 `flag=False` 和 `err_msg`。

Node4 顺序影响：

- 当前顺序主要用于稳定输出。
- 如果后续出现“大图 rule B 依赖 rule A 的 feature”的情况，需要把 A 放在 B 前面，并在这里明确标注依赖关系。

## 9. Node5: geometry_scorer

定位：几何合理性业务评分节点。

Node5 只做“基于已有信息的评分”，不重新检测图像。

输入：

- `TireStruct.big_image`
- `BigImage.lineage`
- `BigImage.evaluation` 中已有的 feature
- 当前节点需要执行的 score configs

输出：

- 更新后的 `BigImage.evaluation`
- 更新后的 `ImageEvaluation.current_score`
- 失败时更新 `TireStruct.flag / TireStruct.err_msg`

执行流程：

```text
1. 校验 tire_struct.big_image 存在。
2. 校验 big_image.evaluation 存在。
3. 获取 Node5 当前要执行的 configs。
4. 对每个 config：
   4.1 从 big_image.evaluation 中按 config.name 查找已有 RuleEvaluation。
   4.2 读取已有 feature。
   4.3 调 runner.exec_score(config, feature)。
   4.4 用新 config / score 更新对应 RuleEvaluation。
5. 重新汇总 current_score。
6. 处理成功后，tire_struct.flag = True。
7. 如果缺少 feature，返回明确错误，提示需要先执行 Node4 或对应 feature 节点。
```

建议接口：

```python
from src.models.tire_struct import TireStruct


def score_geometry(tire_struct: TireStruct) -> TireStruct:
    ...
```

关键约束：

- Node5 不调用 `runner.exec_feature`。
- Node5 只调用 `runner.exec_score`。
- Node5 不重新跑底层图像检测。
- Node5 可以使用 `BigImage.lineage.stitching_scheme` 辅助定位已有结构，但不修改 scheme。
- 如果某个评分必须重新看图像，应放到 Node4。

Node5 缺失 feature 的处理策略：

```text
默认 fail fast。
```

原因：

- Node5 的职责是重算 score，不负责补 feature。
- 如果静默跳过，最终总分会不可信。
- 明确失败能提示调用方补跑 Node4。

Node5 configs：

```python
GEOMETRY_SCORER_CONFIGS = [
    Rule8Config,
    Rule13Config,
    Rule14Config,
    Rule15Config,
    Rule18Config,
    Rule21Config,
    Rule22Config,
]
```

Node5 验证：

- `big_image` 必须存在。
- `big_image.evaluation` 必须存在。
- `rules_config` 中同一种 `RuleConfig` 不能重复。
- 选出的 configs 可以为空；为空时只重新汇总已有 `current_score`，不新增 score。
- 对每个选出的 config，必须能在 `big_image.evaluation` 中找到同名 `RuleEvaluation`。
- 对应 `RuleEvaluation.feature` 必须存在。
- 如果 executor 未实现 `exec_score`，由 `RuleRunner` / executor 抛错，Node5 捕获后写入 `flag=False` 和 `err_msg`。

Node5 顺序影响：

- 当前顺序主要用于稳定重算和输出。
- Node5 不生成 feature，因此顺序不应产生新的 feature 依赖。
- 如果后续出现“score B 依赖 score A”的规则，需要把 A 放在 B 前面，并在这里明确标注依赖关系。

## 10. Node2 / Node3 / Node6 保留边界

### Node2: stitch_scheme_generator

当前确认：

```text
Node2 由模板调用生成拼接方案。
```

边界：

- 输入 `TireStruct.small_images + rules_config + scheme_rank`。
- 输出 `ImageLineage`。
- 根据配置生成完整、可执行、可复现的拼接方案。
- 不执行真实拼图。

Node2 当前设计调整为“先过滤模板，再组合模板，再生成方案，再按排序选择第 N 名”：

```text
1. 使用 STITCH_SCHEME_GENERATOR_CONFIGS 筛出 Node2 支持的 rules_config。
2. 通过模板注册表读取可用拼接模板。
3. 按 rib_number 和启用配置过滤对称性模板。
4. 按 rib_number 保留连续性模板。
5. 将过滤后的对称性模板与连续性模板做笛卡尔组合。
6. 按对称性模板的原始入口 RIB 选择小图，并展开成 5 个 RIB 位置图片。
7. 候选方案分数等于 5 个 RIB 位置图片评分总和；重复使用同一张图时按出现次数重复计分。
8. 按方案总分降序排序；同分时使用对称性模板名、连续性模板名与按 RIB 顺序的小图内容哈希生成稳定排序键。
9. 根据 scheme_rank 选择最终候选方案。
10. 合并对称性模板与连续性模板，读取 Rule100Config / Rule101Config / Rule102Config，实例化完整 ImageLineage。
```

顺序说明：

- `rib_number` 是硬过滤条件，不满足时模板直接淘汰。
- 对称性模板决定入口选图，连续性模板只在后续合并阶段决定最终 RIB 的继承关系和操作。
- 连续性模板不会额外增加选图数量；图片数量过滤以对称性模板的原始入口 RIB 为准。
- Node2 不给模板重新评分；候选方案分数来自 5 个 RIB 位置图片评分总和。
- 同分排序必须可复现，同时避免长期偏向固定模板；当前排序不依赖随机种子。
- `scheme_rank` 只在候选方案排序完成后生效，用于选择第几名方案。
- 最终 lineage 的每个 RIB 必须按合并后的 `inherit_from` 找到正确来源图片，不能简单使用候选列表中同位置图片。
- `Rule100Config` 固化 RIB 数量与各 RIB 的节距 / 尺寸。
- `Rule101Config` 固化主沟尺寸，主沟原始图由 Node2 生成对应尺寸的黑色图。
- `Rule102Config` 固化装饰尺寸与透明度，装饰原始图由 Node2 生成对应尺寸的黑色图。

Node2 的输出必须足够完整，使 Node3 不再读取 `rules_config`。所有会影响拼图结果的配置，都要在 Node2 阶段固化进 `StitchingScheme` 或 lineage 相关结构。

Node2 configs：

```python
STITCH_SCHEME_GENERATOR_CONFIGS = [
    Rule1Config,
    Rule2Config,
    Rule3Config,
    Rule4Config,
    Rule5Config,
    Rule6AConfig,
    Rule7Config,
    Rule12Config,
    Rule16Config,
    Rule17Config,
    Rule19Config,
    Rule100Config,
    Rule101Config,
    Rule102Config,
]
```

Node2 验证：

- `small_images` 必须非空。
- `rules_config` 中同一种 `RuleConfig` 不能重复。
- 至少需要能确定一个基础横向模板；如果 `Rule1Config` 到 `Rule5Config` 都不存在，应返回明确错误。
- 必须存在 `Rule100Config` / `Rule101Config` / `Rule102Config`。
- `Rule100Config.rib_sizes` 必须覆盖最终 lineage 中所有 RIB。
- `scheme_rank` 如果存在，必须大于等于 1，且不能超过候选方案数量。
- 模板调用所需字段必须在对应 config 中存在；字段级校验主要交给 Pydantic model。
- Node2 不验证真实拼图能力，因为真实执行在 Node3。

Node2 顺序影响：

- Node2 的顺序有业务影响。
- 必须先按 `rib_number` 做硬过滤。
- 必须先完成模板过滤，再枚举候选拼接方案。
- 必须先完成对称性入口选图和 5 个 RIB 位置展开，再计算分数。
- 必须先完成方案评分和稳定排序，再应用 `scheme_rank`。
- 必须在最终候选确定后，再把 `Rule100Config` / `Rule101Config` / `Rule102Config` 固化到 lineage。
- Node2 需要记录开始、模板过滤、图片数量统计、排列思路、候选生成、得分统计、最高分模板组合、候选选中、lineage 实例化这些摘要日志，便于排查整体执行状态。

### Node3: big_image_stitcher

当前确认：

```text
Node3 由模板执行调用完成真实拼图。
```

边界：

- 输入 Node2 生成的 `ImageLineage`。
- 只执行 lineage。
- 不再根据 `ruleconfig` 扩展拼接方案。
- 输出 `BigImage`，并写入 `BigImage.lineage.stitching_scheme`。

### Node6: big_image_splitter

当前确认：

```text
Node6 由其他额外方法提供。
```

边界：

- 输入 `TireStruct.big_image`。
- 输出 `TireStruct.small_images`。
- 具体拆分算法和 rule 调用方式后续单独设计。

## 11. 错误处理

节点层不吞掉规则错误。

建议统一处理：

```text
try:
    执行节点逻辑
except Exception as exc:
    tire_struct.flag = False
    tire_struct.err_msg = f"{NODE_NAME} failed: {exc}"
    return tire_struct
```

成功时：

```text
tire_struct.flag = True
tire_struct.err_msg = None
```

如果希望 pipeline 在错误时立即中断，由 API pipeline 根据 `flag` 决定是否继续后续 node。

## 12. 测试策略

Rule config 选择单元测试：

- `select_node_configs` 只选择传入 configs 常量中声明的 config。
- 返回 configs 按传入 configs 常量顺序排序，而不是按用户输入顺序。
- 同一种 `RuleConfig` 重复出现时报错。
- 未声明的 config 会被当前 node 忽略。

Node1 单元测试：

- 多张小图时，每张小图都写入独立 `ImageEvaluation`。
- 每个 config 都调用一次 `exec_feature` 和 `exec_score`。
- configs 按 Node1 config 列表顺序执行：`Rule6Config` 先于 `Rule11Config`。
- 某张小图失败时，`flag=False`，`err_msg` 包含 node 名称。
- Node1 不修改 `big_image`。

Node4 单元测试：

- `big_image` 存在时写入 `BigImage.evaluation`。
- 大图是单对象，只调用一次每个 config。
- `big_image` 缺失时明确失败。
- Node4 不修改 `small_images`。

Node5 单元测试：

- 已有 feature 时只调用 `exec_score`，不调用 `exec_feature`。
- configs 按 Node5 config 列表顺序重算 score。
- 使用新 config 重算 score，并更新 `current_score`。
- feature 缺失时 fail fast。
- Node5 不修改 `BigImage.lineage.stitching_scheme`。

## 13. 当前结论

本阶段可实现节点：

```text
Node1: small_images(list) -> 每张 SmallImage.evaluation
Node4: big_image(single) -> BigImage.evaluation
Node5: BigImage.evaluation(existing feature) -> 重算 score/current_score
```

稳定调用关系：

```text
RuleConfig selection:
  NODE_CONFIGS_CONSTANT -> select -> sort -> validate duplicates / node preconditions

Node1 / Node4:
  RuleRunner.exec_feature
  RuleRunner.exec_score

Node5:
  RuleRunner.exec_score only
```

Node2 / Node3 / Node6 先保留边界，不在本设计中展开实现细节。
