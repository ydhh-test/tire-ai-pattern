# Rule11 纵向细沟数量规则说明

## 规则职责

`Rule11Executor` 负责从 `SmallImage` 中提取纵向细沟或纵向钢片数量，并根据小图区域执行数量上限评分。

规则层只做以下事情：

- 校验输入必须是 `SmallImage` 和 `Rule11Config`。
- 校验 `SmallImage.biz.region` 必须是 `center` 或 `side`。
- 将 `SmallImage.image_base64` 解码为 BGR 图像。
- 调用 `detect_longitudinal_grooves` 获取纵向线条数量。
- 返回携带 `num_longitudinal_grooves` 和 `region` 的 `Rule11Feature`。
- 根据 `region` 选择 `max_count_center` 或 `max_count_side` 计算 `Rule11Score`。

## Core 调用边界

`Rule11Executor` 调用 `detect_longitudinal_grooves` 时只透传图像数组和 `is_debug`。检测阈值、边缘排除、线段长度等算法细节由 core 算法默认参数负责，规则层不再从配置中二次派生这些参数。

规则层不保存 debug 文件，也不把完整 `SmallImage` 或 `Rule11Config` 传入 core。

## Debug 行为

默认 `is_debug=False`，`Rule11Feature.vis_names` 和 `Rule11Feature.vis_images` 均为 `None`。

当 `is_debug=True` 时，`Rule11Executor` 会把该参数透传给 `detect_longitudinal_grooves`。如果 core 返回 `debug_image`，规则层会将其编码为 base64，并写入：

- `vis_names`: `rule11_longitudinal_grooves.png`
- `vis_images`: debug 图对应的 base64 字符串

## 评分逻辑

由于评分接口只接收 `config + feature`，`Rule11Feature` 会携带小图的 `region`。

- `region=center` 时使用 `config.max_count_center`。
- `region=side` 时使用 `config.max_count_side`。
- 纵向线条数量不超过对应上限时得 `config.max_score`。
- 纵向线条数量超过对应上限时得 `0`。