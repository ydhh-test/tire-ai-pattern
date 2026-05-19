# 大图生成业务处理模块说明

## 概览

本模块属于 processing 业务处理层，负责根据 `ImageLineage` 血缘信息完成完整的大图生成流程。该层编排 core 层的图像操作算法和 utils 层的工具函数，不实现具体图像处理逻辑。

---

## `generate_large_image_from_lineage`

模块的入口函数，接收完整的血缘信息对象，输出生成的大图和更新后的血缘对象。

### 输入参数

- `lineage`：`ImageLineage` 实例，包含拼接方案、主沟方案、装饰方案的完整信息。
- `is_debug`：`bool`，是否启用调试模式，默认 `False`。启用时 lineage 输入以 DEBUG 级别日志输出完整 JSON，否则以 INFO 级别输出脱敏版（base64 图片值替换为长度摘要）。

### 输出结果

- `Tuple[ImageLineage, str]`：`(更新后的血缘对象, base64 编码的大图字符串)`。
- 更新后的血缘对象中，每个 RIB / 主沟 / 装饰的 `after_image` 字段已被填充。
- base64 大图字符串带 `data:image/png;base64,` 前缀。

### 处理流程

```
lineage 输入
  │
  ├─ 1. RIB 预处理      _process_rib_images
  ├─ 2. 主沟预处理       _process_main_groove
  ├─ 3. 装饰预处理       _process_decoration
  ├─ 4. 参数验证         _validate_parameters
  ├─ 5. 构建拼接序列     _build_concatenation_sequence
  ├─ 6. 横向拼接         horizontal_concatenate (core)
  ├─ 7. 后处理（可选）   _apply_resize_as_first_rib
  ├─ 8. 装饰覆盖         overlay_decoration (core)
  └─ 9. 编码输出         ndarray_to_base64 (utils)
```

### 异常行为

- `lineage` 为 `None` 时，抛出 `ValueError`。
- `lineage.stitching_scheme` 为 `None` 或 RIB 列表为空时，抛出 `ValueError`。
- 预处理阶段中 RIB `before_image` 为 `None` 且 `after_image` 也为 `None` 时，抛出 `ValueError`。
- 拼接阶段主沟数量不等于 `RIB 数量 - 1` 时，抛出 `ValueError`。

### 调试行为

当 `is_debug=True` 时，lineage 输入的完整 JSON（含 base64 图片值）以 DEBUG 级别输出。默认 `is_debug=False` 时，lineage JSON 中以 `<base64 N chars>` 替代实际的图片 base64 字符串。

---

## 内部处理函数

以下函数为模块内部使用，不直接暴露给调用方。理解这些函数有助于排查问题和扩展功能。

### `_process_rib_images`

处理所有 RIB 的 before_image，生成 after_image。

#### 输入参数

- `ribs`：`List[RibSchemeImpl]`，待处理的 RIB 实现列表。
- `is_debug`：`bool`，调试模式开关（当前未使用）。

#### 处理流程

对于每个 RIB：

1. **跳过检查**：若 `rib.after_image` 已存在，直接跳过。
2. **解码**：将 `rib.before_image`（base64）解码为 `np.ndarray`。
3. **操作序列**：调用 `apply_rib_operations_sequence(image, rib.rib_operation)` 执行 RIB 操作。
4. **纵向重复**：若 `rib.num_pitchs > 1`，调用 `repeat_vertically` 纵向重复。
5. **尺寸调整**：若 `rib.rib_width` 和 `rib.rib_height` 均存在，调用 `resize_image(mode="stretch")` 缩放到目标尺寸。
6. **编码**：将处理后的图像编码为 base64，存入 `rib.after_image`。

#### 边界处理

- `rib.num_pitchs` 为 `None` 或 `1` 时，跳过纵向重复。
- `rib.rib_width` 或 `rib.rib_height` 为 `None`/`0` 时，跳过尺寸调整。

---

### `_process_main_groove`

处理所有主沟的 before_image，生成 after_image。

#### 输入参数

- `main_grooves`：`List[MainGrooveImpl]`，待处理的主沟列表。
- `is_debug`：`bool`，调试模式开关（当前未使用）。

#### 处理流程

对于每个主沟：

1. **跳过检查**：若 `groove.after_image` 已存在或 `groove.before_image` 为 `None`，跳过。
2. **解码**：将 `groove.before_image`（base64）解码为 `np.ndarray`。
3. **尺寸调整**：若 `groove.groove_width` 和 `groove.groove_height` 均存在，调用 `resize_image(mode="stretch")` 缩放。
4. **编码**：存入 `groove.after_image`。

---

### `_process_decoration`

处理所有装饰的 before_image，应用透明度并生成 after_image。

#### 输入参数

- `decorations`：`List[DecorationImpl]`，待处理的装饰列表。
- `is_debug`：`bool`，调试模式开关（当前未使用）。

#### 处理流程

对于每个装饰：

1. **跳过检查**：若 `decoration.after_image` 已存在或 `decoration.before_image` 为 `None`，跳过。
2. **解码**：将 before_image 解码为 `np.ndarray`。
3. **尺寸调整**：按 `decoration_width` × `decoration_height` 缩放（stretch 模式）。
4. **透明度应用**：若 `decoration.decoration_opacity` 存在，调用 `apply_opacity` 转为 BGRA 格式并设置透明通道。
5. **编码**：存入 `decoration.after_image`。

#### 注意事项

- 应用透明度后输出为 BGRA（4 通道）格式，保留 alpha 通道以支持后续 `overlay_decoration` 的半透明混合。
- 若未指定透明度，保持原始格式直接编码。

---

### `_validate_parameters`

验证处理后的各项参数是否满足拼接前置条件。

#### 校验规则

- 所有 RIB 的 `after_image` 必须已处理（非 None）。
- 所有 RIB 的 `rib_width` / `rib_height` 必须存在。
- 所有主沟的 `groove_width` / `groove_height` 必须存在。
- 所有装饰的 `decoration_width` / `decoration_height` 必须存在。

#### 异常行为

不满足条件时抛出 `ValueError`，错误信息包含具体索引位置。

---

### `_build_concatenation_sequence`

根据 RIB 列表和主沟列表构建横向拼接的图像序列。

#### 拼接规则

```
序列格式：[RIB0, Groove0, RIB1, Groove1, ..., RIBN-1]
```

即：rib_count 个 RIB 和 groove_count 个主沟，主沟数必须等于 `rib_count - 1`。

#### 输入参数

- `ribs`：`List[RibSchemeImpl]`，RIB 列表。
- `main_grooves`：`List[MainGrooveImpl]`，主沟列表。

#### 输出结果

- `List[np.ndarray]`：按拼接顺序排列的图像数组列表。

#### 异常行为

- 主沟数量不等于 `RIB 数量 - 1` 时，抛出 `ValueError`。

---

### `_apply_resize_as_first_rib`

将拼接后的大图缩放到与第一个 RIB 相同的尺寸。当前仅在拼接方案名为 `continuity_0` 时触发。

#### 输入参数

- `concatenated_image`：拼接后的图像 `np.ndarray`。
- `first_rib_height`：第一个 RIB 的高度。
- `first_rib_width`：第一个 RIB 的宽度。

#### 输出结果

- `np.ndarray`：缩放到 `(first_rib_height, first_rib_width)` 的图像，stretch 模式。

#### 触发条件

```
stitching_scheme.stitching_scheme_abstract.name == "continuity_0"
```

---

## 完整数据流

```
ImageLineage
  │
  │  stitching_scheme.ribs_scheme_implementation → _process_rib_images
  │    └─ before_image (base64)  → 解码 → 操作序列 → 纵向重复 → resize → after_image (base64)
  │
  │  main_groove_scheme.main_groove_implementation → _process_main_groove
  │    └─ before_image (base64) → 解码 → resize → after_image (base64)
  │
  │  decoration_scheme.decoration_implementation → _process_decoration
  │    └─ before_image (base64) → 解码 → resize → 透明度 → after_image (base64)
  │
  ├─ _validate_parameters（所有 after_image 和尺寸参数就绪）
  ├─ _build_concatenation_sequence（RIB 与主沟交替排列）
  ├─ horizontal_concatenate（横向拼接）
  ├─ _apply_resize_as_first_rib（可选后处理）
  ├─ overlay_decoration（装饰覆盖）
  └─ ndarray_to_base64（编码输出）
```