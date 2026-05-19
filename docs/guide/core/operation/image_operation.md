# 核心图像操作算法说明

## 概览

本模块属于 core 算法层，提供纯图像处理算法函数。所有函数输入输出均为基本类型（`np.ndarray`、base64 字符串等），不依赖任何业务数据类，与业务逻辑完全解耦。上层 processing 层和 API 层通过调用本模块完成具体的图像处理步骤。

---

## `apply_single_rib_operation`

执行单个 RIB 原子操作，是 RIB 图像处理的最小粒度操作单元。

### 输入参数

- `image`：输入图像，BGR 格式 `np.ndarray`，形状为 `(H, W, 3)`。
- `operation`：`RibOperation` 枚举值，指定要执行的原子操作。

### 输出结果

- `np.ndarray`：处理后的图像，尺寸取决于操作类型（部分操作会改变宽度）。

### 支持的操作

| 操作 | 行为 | 输出尺寸 |
|---|---|---|
| `NONE` | 不处理，返回副本 | 不变 |
| `FLIP_LR` | 左右镜像翻转 | 不变 |
| `FLIP` | 旋转 180° | 不变 |
| `RESIZE_HORIZONTAL_2X` | 横向拉伸 2 倍 | W×2, H 不变 |
| `RESIZE_HORIZONTAL_1_5X` | 横向拉伸 1.5 倍 | W×1.5, H 不变 |
| `RESIZE_HORIZONTAL_3X` | 横向拉伸 3 倍 | W×3, H 不变 |
| `LEFT` | 截取左半部分 | W//2, H 不变 |
| `RIGHT` | 截取右半部分 | W//2, H 不变 |
| `LEFT_FLIP_LR` | 左半左右镜像覆盖到右侧 | 不变 |
| `LEFT_FLIP` | 左半旋转 180° 覆盖到右侧 | 不变 |
| `LEFT_2_3` | 截取左 2/3 | W×2/3, H 不变 |
| `RIGHT_2_3` | 截取右 2/3 | W×1/3~2/3, H 不变 |
| `LEFT_1_3` | 截取左 1/3 | W×1/3, H 不变 |
| `RIGHT_1_3` | 截取右 1/3 | W×1/3, H 不变 |

其中 `LEFT_FLIP_LR` 和 `LEFT_FLIP` 是覆盖操作（不改变输出尺寸），其余均为截取或拉伸操作。

### 边界处理

- 图像宽度小于 2 时，截取和覆盖操作返回 `image.copy()`。
- 奇数宽度时，覆盖操作以左侧半区为基准，右侧不足部分用最后一列填充。
- 拉伸操作的 `new_width` 计算结果 ≤ 0 时，强制设为 1。
- 截取操作的起始列索引超出图像宽度时，强制修正为 `w - 1`。

### 异常行为

- 入参 `image` 为 `None` 或空数组时，抛出 `ValueError("输入图像不能为空")`。
- 操作枚举值不在以上列表中时，抛出 `ValueError(f"Unsupported operation: {operation}")`。
- 处理过程中发生 cv2/numpy 异常时，包装为 `RuntimeError`。
- `_RESIZE_AS_FIRST_RIB` 不支持在此函数中独立调用，抛出 `NotImplementedError`。

---

## `apply_rib_operations_sequence`

按顺序执行 RIB 操作序列，将多个原子操作串联执行。

### 输入参数

- `image`：输入图像，BGR 格式 `np.ndarray`。
- `operations`：`Tuple[RibOperation, ...]`，操作序列元组。

### 输出结果

- `np.ndarray`：按序列依次处理后的图像。

### 算法流程

1. 若 `operations` 为空元组，直接返回输入图像副本。
2. 遍历操作序列，跳过 `NONE` 操作。
3. 对每个非空操作调用 `apply_single_rib_operation`，将上一次的输出作为下一次的输入。

### 典型组合示例

| 输入序列 | 效果 |
|---|---|
| `(RESIZE_HORIZONTAL_2X, LEFT)` | 横向拉伸 2 倍后截取左边，等效于在原图左侧区域取完整图 |
| `(FLIP_LR, LEFT)` | 左右镜像后截取左边 |
| `(RESIZE_HORIZONTAL_1_5X, LEFT_1_3)` | 拉伸 1.5 倍后取左 1/3 |

---

## `repeat_vertically`

将图像纵向重复指定次数。用于根据节距数（num_pitchs）扩展 RIB 图案的高度。

### 输入参数

- `image`：输入图像 `np.ndarray`。
- `num_times`：重复次数，必须为正整数。

### 输出结果

- `np.ndarray`：纵向拼接后的图像，高度为 `H × num_times`，宽度不变。

### 边界处理

- `num_times == 1` 时返回输入图像副本，不执行拼接。
- `num_times <= 0` 时抛出 `ValueError`。

### 实现细节

使用 `np.tile(image, (num_times, 1, 1))` 沿第 0 维（高度）重复，适用于 (H, W) 灰度图和 (H, W, C) 彩色图。

---

## `apply_opacity`

将 BGR 图像转换为带 alpha 通道的 BGRA 图像，并设置统一的透明度值。

### 输入参数

- `image`：输入图像，BGR 格式或灰度图 `np.ndarray`。
- `opacity`：透明度值，整数，范围 0-255（0=完全透明，255=完全不透明）。

### 输出结果

- `np.ndarray`：BGRA 格式图像，形状为 `(H, W, 4)`，alpha 通道值统一设为 `opacity`。

### 处理逻辑

- 灰度图（2D）：先通过 `cv2.COLOR_GRAY2BGRA` 转为 BGRA。
- 彩色图（3D）：通过 `cv2.COLOR_BGR2BGRA` 转为 BGRA。
- 设置整个 alpha 通道为指定值。

### 异常行为

- `opacity` 不在 0-255 范围内时，抛出 `ValueError`。

---

## `horizontal_concatenate`

将多个图像沿水平方向（宽度）拼接。

### 输入参数

- `images`：`List[np.ndarray]`，图像列表。所有图像必须具有相同的高度。

### 输出结果

- `np.ndarray`：横向拼接后的图像，高度不变，宽度为所有输入宽度之和。

### 边界处理

- 列表为空时抛出 `ValueError`。
- 单元素列表时返回该元素副本。
- 元素高度不一致时抛出 `ValueError`，错误信息中包含所有高度值以便定位。

### 实现细节

使用 `np.concatenate(images, axis=1)` 沿第 1 维（宽度）拼接。

---

## `overlay_decoration`

在基础图像的左右边缘应用半透明装饰覆盖。该函数**不改变图像分辨率**，覆盖操作在指定区域原地完成。

### 输入参数

- `base_image`：基础图像 `np.ndarray`，BGR 格式。
- `left_decoration`：左侧装饰图像 `np.ndarray`，BGR 或 BGRA（带 alpha 通道）。
- `right_decoration`：右侧装饰图像 `np.ndarray`，BGR 或 BGRA。

### 输出结果

- `np.ndarray`：应用装饰覆盖后的图像，BGR 格式，尺寸与 `base_image` 完全相同。

### 透明度混合逻辑

装饰图为 BGRA（4 通道）时，按 alpha 通道进行半透明混合：

```
result[channel] = alpha × decoration[channel] + (1 - alpha) × base[channel]
```

装饰图为 BGR（3 通道、无 alpha）时，直接覆盖。

### 位置规则

- 左侧装饰：覆盖 `base_image[:, :left_w, :]` 区域。
- 右侧装饰：覆盖 `base_image[:, base_w - right_w:, :]` 区域。
- 右侧覆盖从右边缘向左延伸，不依赖左侧覆盖的位置。

### 前置校验

- 装饰图高度必须与基础图像高度一致。
- 装饰图宽度不能超过基础图像宽度。
- 以上条件不满足时抛出 `ValueError`。

### 实现细节

使用 `np.float32` 精度完成混合计算，最终 `np.clip(result, 0, 255).astype(np.uint8)` 转回 uint8，避免浮点溢出。
