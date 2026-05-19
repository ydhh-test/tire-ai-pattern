# Node2 拼接方案生成设计

## 1. 目标

`Node2 / stitch_scheme_generator` 用于从多张已经完成评分的小图中生成候选拼接方案，并返回排名第 `N` 的最终方案。

本设计明确以下原则：

- 先过滤拼接模板，再生成候选方案。
- Node2 使用小图已有评分，不负责重新给模板评分。
- 方案分数等于该方案所使用小图分数之和。
- 同分方案需要稳定排序，同时避免长期偏向固定模板。
- Node2 只生成可执行 lineage，不执行真实拼图。

## 2. 与旧方案的差异

现有 `docs/plans/rules/nodes_design.md` 中的 Node2 设计，更偏向“由 `Rule1Config` 到 `Rule5Config` 先决定基础模板，再由其他规则继续扩展方案”。

本次任务确认后的业务口径调整为：

1. 从全部模板中先做过滤。
2. 过滤通过后，再结合小图生成候选拼接方案。
3. 最终返回按方案分排序后的第 `N` 名。

因此，后续实现时应以本文档为 Node2 的直接设计依据；旧文档中的 Node2 段落需要在实现前后同步修订，避免两套口径并存。

## 3. 输入与输出

### 3.1 输入

Node2 需要以下输入：

- 已完成评分的小图列表
- 规则配置列表 `rules_config`
- `scheme_rank`

其中，小图应已经具备可读取的评分结果。Node2 不负责执行小图评分节点。

`rules_config` 会先通过 `STITCH_SCHEME_GENERATOR_CONFIGS` 筛选出 Node2 支持的配置。模板本身通过注册表导入，Node2 不在业务逻辑中手动维护模板清单。

### 3.2 输出

Node2 输出：

- 一个排名为 `scheme_rank` 的 `ImageLineage`

输出方案必须满足：

- 可执行
- 可复现
- 已固化模板信息
- 已固化所选小图组合
- 已固化 RIB 尺寸、主沟尺寸、装饰尺寸与透明度配置

Node3 只消费 Node2 生成的 lineage 并执行拼接，不再重新参与模板筛选或排序。

## 4. 总体流程

```text
small_images(with scores)
        |
        v
select_node_configs_by_STITCH_SCHEME_GENERATOR_CONFIGS
        |
        v
filter_symmetry_templates_and_continuity_templates
        |
        v
combine_symmetry_template_with_continuity_template
        |
        v
enumerate_entry_images_by_symmetry_template
        |
        v
expand_entry_images_to_all_rib_positions
        |
        v
score_candidates_by_sum_of_expanded_small_image_scores
        |
        v
stable_rank_candidates
        |
        v
select scheme_rank = N
        |
        v
instantiate ImageLineage
```

## 5. 模板过滤与组合

模板分为两类：

- 对称性模板：决定第一步入口图片如何选择，以及 5 个 RIB 位置如何由入口图片展开。
- 连续性模板：决定第二步如何在对称性结果之上合并继承关系与操作。

两类模板都必须满足目标 `rib_number`：

```text
template.rib_number == target_rib_number
```

### 5.1 对称性模板过滤

对称性模板需要同时满足：

```text
template.mode == "symmetry"
and template.rib_number == target_rib_number
and template.matching_rule_names 与 enabled_rule_names 有交集
```

`enabled_rule_names` 来自 `STITCH_SCHEME_GENERATOR_CONFIGS` 筛选后的 `configs`。前置节点已经保证进入 `_filter_templates` 的 `configs` 是 Node2 支持的配置，因此这里不再做二次配置类型过滤，只使用这些配置名称判断模板是否启用。

### 5.2 连续性模板过滤

```text
template.mode == "continuity"
and template.rib_number == target_rib_number
```

连续性模板目前不通过 `enabled_rule_names` 做启用过滤。它会先保留，再在图片数量检查阶段确认是否能与至少一个可用对称性模板组合。

### 5.3 模板组合

过滤得到的模板不会只选一个，而是做笛卡尔组合：

```text
template_combinations = symmetry_templates x continuity_templates
```

例如过滤后有 2 个对称性模板、2 个连续性模板，则进入候选枚举的是 4 个模板组合。

### 5.4 图片数量过滤

图片数量只按对称性模板的原始入口 RIB 统计。原因是对称性模板是第一步入口操作，真正需要从小图池中选择哪些图片，由对称性模板决定。

连续性模板在数量过滤阶段只判断“是否能与至少一个数量满足的对称性模板组合”。它本身不额外增加选图数量。

## 6. 候选方案生成

对于每个过滤通过的模板组合，Node2 基于对称性模板的入口 RIB 要求，从小图集合中枚举可行图片组合。

当输入小图数量多于对称性模板实际需要数量时，Node2 不要求“输入数量刚好等于使用数量”，而是按入口 RIB 所需的 region 数量从候选池中枚举排列组合。

例如某个对称性模板入口需要 `side x1 + center x2`，即使输入为 `side x3 + center x5`，也应从中生成所有入口图片组合，再展开为 5 个 RIB 位置上的图片。

候选方案至少应包含：

- 使用的对称性模板名称
- 使用的连续性模板名称
- 按对称性模板展开后的 5 个 RIB 位置图片
- 方案总分
- 可供 Node3 执行的 `ImageLineage`

这里的关键约束是：

- 小图入口选择只跟对称性模板有关
- 候选方案中的 `selected_images` 保存的是对称性入口展开后的 5 个 RIB 位置图片
- 后续连续性模板会合并成最终 `RibTemplate`，但不改变候选方案的入口选图来源
- 后续排序、哈希、复现都依赖这个顺序

### 6.1 两阶段 RibTemplate 合并

最终拼接方案需要把对称性模板与连续性模板合并成 5 个 `RibTemplate`。

合并规则：

- 先解析对称性模板中每个 RIB 最终来自哪个原始入口 RIB。
- 再遍历连续性模板的 RIB。
- 如果连续性 RIB 指向某个对称性 RIB，则继续追溯到该对称性 RIB 的原始入口来源。
- 最终输出的 `RibTemplate` 使用“最终 RIB -> 原始入口 RIB”的扁平继承关系。
- 两阶段 operation 按顺序合并，连续性无操作时保留对称性操作。

例如：

```text
Symmetry1 + Continuity2
rib3 -> inherit_from="rib2" -> FLIP, RESIZE_HORIZONTAL_2X, LEFT
rib4 -> inherit_from="rib2" -> FLIP, RESIZE_HORIZONTAL_2X, RIGHT
```

此时 `selected_images` 仍然记录对称性阶段展开后的 5 个 RIB 位置图片；lineage 实例化时，每个最终 RIB 会按合并后的 `inherit_from` 找到正确来源图片。

## 7. 方案评分

候选拼接方案的分数定义为：

```text
scheme_total_score = sum(selected_small_image_scores)
```

这里的 `selected_small_image_scores` 指候选方案展开后的 5 个 RIB 位置图片分数。即使同一张小图因为对称性被重复使用，也需要按重复出现的位置重复计分。

当前版本不引入：

- 平均分
- 最小分约束
- 位置权重
- 模板额外加分

后续若需要扩展，应单独修订设计，不在当前版本预留未使用的复杂度。

## 8. 排序与固定随机性

### 8.1 排序目标

排序需要同时满足：

1. 高分优先
2. 同一批输入多次运行结果一致
3. 同分时避免长期偏向固定模板

### 8.2 小图内容标识

当前模型中不存在稳定的 `image_id`。

因此，Node2 使用图片内容生成稳定标识：

1. 从 `image_base64` 中去掉 `data:image/...;base64,` 前缀
2. 对真实内容部分计算 `sha256`
3. 得到每张小图的 `content_hash`

### 8.3 排序键

候选方案排序键：

```text
(
    -scheme_total_score,
    stable_hash(symmetry_template_name + continuity_template_name + ordered_small_image_content_hashes),
)
```

说明：

- `ordered_small_image_content_hashes` 必须按对称性展开后的 5 个 RIB 位置顺序排列
- 第二排序键同时包含对称性模板名称、连续性模板名称和所选小图内容
- 这样可以保证同一输入稳定复现，同时避免纯 `template_name` 排序导致某类模板长期占优
- 这里不使用随机种子；排序完全由输入图片内容、模板组合名称和分数决定，跨机器、跨时间应保持一致

### 8.4 哈希碰撞

`sha256` 的碰撞概率在工程上可忽略。

当前版本默认不额外引入第三排序键。若未来需要理论上的严格全序，再补充极端碰撞下的兜底规则。

## 9. `scheme_rank`

`scheme_rank` 表示最终返回排序后的第 `N` 个候选方案。

约束：

- `scheme_rank >= 1`
- `scheme_rank <= candidate_scheme_count`

若不满足，应返回明确错误，而不是回退到默认方案。

## 10. 边界与职责

### 10.1 Node2 负责

- 模板过滤
- 模板组合
- 候选方案枚举
- 方案评分
- 稳定排序
- 按 `scheme_rank` 选择最终方案
- 读取 `Rule100Config` 并填充每个 RIB 的 `num_pitchs / rib_width / rib_height`
- 读取 `Rule101Config` 并生成主沟方案；主沟原始图使用对应尺寸的黑色图
- 读取 `Rule102Config` 并生成装饰方案；装饰原始图使用对应尺寸的黑色图
- 生成完整 `ImageLineage`

### 10.2 Node2 不负责

- 小图评分
- 真实图像拼接
- 大图评分
- 重新解释 Node1 的评分逻辑

### 10.3 Node3 负责

- 消费 Node2 输出的 `ImageLineage`
- 执行真实拼图
- 产出大图与血缘信息

## 11. 校验要求

Node2 至少需要校验：

- 小图列表非空
- 目标 `rib_number` 有效
- `scheme_rank >= 1`
- `Rule100Config` / `Rule101Config` / `Rule102Config` 均存在
- `Rule100Config.rib_sizes` 覆盖最终 lineage 中所有 RIB
- 存在至少一个通过过滤的模板
- 存在至少一个可行候选方案
- `scheme_rank` 不超过候选方案数量
- 参与排序的小图均具备可读取评分

## 12. 日志要求

Node2 需要在业务关键阶段输出 `INFO` 日志，便于从一条执行链路中快速判断当前处于哪一步：

- 开始执行：输入小图数量、模板数量、目标 `rib_number`、`scheme_rank`、启用规则
- 模板过滤完成：对称性模板数量和名称、连续性模板数量和名称
- 图片数量统计：中心图片数量、边缘图片数量、全部图片数量
- 图片数量过滤：被过滤模板及原因
- 排列思路：只输出公式摘要，例如 `A[2,2]*A[2,3]=12`，不输出每个组合明细
- 候选生成完成：实际候选方案数量
- 得分统计：候选数量、最高分、最低分
- 最高分模板组合：去重后的模板组合名称，不输出图片信息
- 最终候选选中：排名、模板组合、方案总分、5 个 RIB 位置图片摘要
- lineage 实例化完成：分别输出每个 rib、groove、decoration 的来源、尺寸、操作和图片摘要

日志中不记录 base64、完整图片内容或其他高体量字段，只记录足够定位流程状态的摘要信息。

## 13. 测试建议

### 13.1 模板过滤

- `rib_number` 不匹配的模板一定被过滤
- 对称性模板会根据 `STITCH_SCHEME_GENERATOR_CONFIGS` 过滤出的配置启用
- 同一批模板在配置完整时全部保留，移除某个配置后对应对称性模板会被过滤
- 连续性模板先按 `rib_number` 保留，再在图片数量阶段判断是否能与可用对称性模板组合

### 13.2 图片数量过滤

- 中心图片 3 张时，可以选择 `Symmetry0` 和 `Symmetry1`
- 中心图片 2 张时，只能选择数量满足的对称性模板
- 被过滤的对称性模板需要输出原因
- 连续性模板只有在无法与任何数量满足的对称性模板组合时才会被过滤

### 13.3 方案评分

- 方案分数等于 5 个 RIB 位置图片分数之和
- 对称性导致同一张小图重复出现时，该小图分数按出现次数重复计算
- 不同组合得到正确总分

### 13.4 排序稳定性

- 同一批输入重复运行，排序结果完全一致
- 同分候选方案不会因为模板名固定顺序而总是选中同一个模板
- 小图内容变化后，tie-breaker 结果随之变化，包括同分排序结果可能变化
- 排序不依赖随机种子

### 13.5 `scheme_rank`

- `scheme_rank = 1` 返回第一名
- `scheme_rank = N` 返回第 `N` 名
- 越界时返回明确错误

### 13.6 lineage 实例化

- `Rule100Config` 中的 RIB 尺寸配置会写入 `RibSchemeImpl`
- 最终 RIB 使用合并后的 `inherit_from` 找到正确来源图片
- `Symmetry1 + Continuity2` 这类组合中，连续性复用 `rib2` 时，对应 lineage 图片应来自 `rib2` 的入口图片，而不是候选位置上的另一张图片
- `Rule101Config` 会生成对应数量和尺寸的主沟方案
- `Rule102Config` 会生成对应数量、尺寸和透明度的装饰方案
- 主沟和装饰的 `before_image` 都是指定尺寸的黑色图

### 13.7 日志

- 正常执行时能看到模板过滤、图片数量统计、排列思路、候选生成、得分统计、最高分模板组合、候选选中、lineage 实例化阶段
- 日志只输出摘要字段，不输出图片 base64

## 14. 后续需要同步的旧文档

本次调整已同步更新：

- `docs/plans/rules/nodes_design.md`

该文档中的 Node2 说明已修订为：

- 先过滤模板
- 再组合对称性模板与连续性模板
- 对称性模板决定入口选图
- 连续性模板参与最终 RIB 继承关系与 operation 合并
- 评分来源于展开后的 5 个 RIB 位置图片
- 返回第 `N` 名方案
- 使用稳定哈希实现可复现的同分排序
