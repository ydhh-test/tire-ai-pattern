# 横沟检测算法

`src.core.detection.groove_intersection` 提供横沟交点检测能力，用于统计一张轮胎小图中的横向粗线条数量，并输出横沟与纵向线条的交叉点数量。

该模块属于 `src.core` 算法层，只负责从内存中的 BGR 图像提取算法特征。它不负责规则评分、不保存文件、不读写 `.results/`，也不处理业务流程调度。

## 适用场景

使用该算法时，输入应是一张已经读入内存的 BGR 小图。

典型调用方包括：

- 上层业务模块：消费 `groove_count` 和 `intersection_count` 做后续决策。
- 调试工具：在 `is_debug=True` 时获取染色图，用于人工比对和排查误判。
- 单元测试：构造合成二值图或真实轮胎小图，验证横沟聚合和交叉点统计逻辑。

不适合在该模块内完成的工作：

- 规则评分和业务判定。
- 图片删除、移动、重命名或保存。
- `.results/` 目录组织。
- 接口协议、节点调度等上层流程概念。

## 快速开始

```python
import cv2
import numpy as np

from src.core.detection.groove_intersection import detect_transverse_grooves

buf = np.fromfile("small_tire.png", dtype=np.uint8)
image = cv2.imdecode(buf, cv2.IMREAD_COLOR)

groove_count, intersection_count, _, _ = detect_transverse_grooves(
    image,
    groove_width_px=25,
)

print(groove_count, intersection_count)
```

Windows 中文路径下，推荐使用 `np.fromfile()` 和 `cv2.imdecode()` 读取图片，避免 `cv2.imread()` 对非 ASCII 路径支持不稳定的问题。

## API 入口

### `detect_transverse_grooves`

```python
detect_transverse_grooves(
    image: np.ndarray,
    groove_width_px: int,
    is_debug: bool = False,
) -> tuple[int, int, str, np.ndarray | None]
```

检测 BGR 小图中的横沟数量，并统计横沟与纵向线条的交叉点数量。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `image` | `np.ndarray` | 必填 | 输入 BGR 图像，形状必须为 `(H, W, 3)`。不接受二维灰度图。 |
| `groove_width_px` | `int` | 必填 | 横沟最小宽度（像素），必须 >= 1。由调用方按场景决定传入值。 |
| `is_debug` | `bool` | `False` | 是否返回 debug 染色图。算法层只返回图像对象，不保存文件。 |

典型像素宽度参考值（由调用方决定，不是算法内部常量）：

| 小图类型 | 建议 `groove_width_px` |
| --- | --- |
| center | `25` |
| side | `13` |

### 返回值

函数返回显式 tuple：

```python
groove_count, intersection_count, vis_name, vis_image = detect_transverse_grooves(
    image,
    groove_width_px=25,
)
```

| 返回项 | 类型 | 说明 |
| --- | --- | --- |
| `groove_count` | `int` | 检测到的横沟数量。 |
| `intersection_count` | `int` | 横沟与纵向线条的交叉点数量。 |
| `vis_name` | `str` | debug 染色图建议文件名。`is_debug=False` 时为空字符串；`is_debug=True` 时为 `groove_intersections`。 |
| `vis_image` | `np.ndarray | None` | debug 染色图。`is_debug=False` 时为 `None`。 |

算法层不会返回 score、规则通过状态、保存路径或结果字典。

## 算法逻辑

### 1. 输入校验

算法首先检查：

- `image` 不为 `None`。
- `image` 是 `np.ndarray`。
- `image` 是三通道 BGR 图。
- `groove_width_px` 是 `int` 且 >= 1。

如果输入不满足约定，会抛出 `InputDataError`。

### 2. 灰度化与自适应二值化

算法将 BGR 图转为灰度图，并做轻量高斯模糊：

```python
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (3, 3), 0)
```

随后使用自适应阈值提取暗色沟槽前景：

```python
binary = cv2.adaptiveThreshold(
    blurred,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV,
    blockSize=31,
    C=5,
)
```

效果是：暗色沟槽变为白色前景，浅色背景变为黑色背景。

### 3. 横沟区域识别

`_analyze_grooves()` 通过水平投影识别横向带状区域：

1. 逐行统计前景像素数。
2. 当前景像素数达到 `max(groove_width_px, image_width // 4)` 时，该行被视为候选横沟行。
3. 合并相邻候选行，允许最多 `3` 行空白间隔。
4. 过滤高度不足的行组，最小高度为 `max(3, groove_width_px // 5)`。
5. 返回横沟中心位置、横沟数量和横沟掩码。

### 4. 交叉点统计

`_count_intersections()` 统计横沟与纵向线条的交叉点数量。

对每条横沟，算法分别分析横沟上方和下方的列密度：

- 上下两侧都存在时，要求两侧列密度都达到约 `15%` 阈值。
- 只有一侧存在时，使用更严格的约 `25%` 阈值。
- 相邻热列按 `5 px` 间隔容差合并为一个纵向线条聚类。
- 位于图像最左或最右边界的聚类会被过滤。
- 每个纵向聚类与每条横沟最多计为一个交叉点。

### 5. Debug 染色图

当 `is_debug=True` 时，函数额外返回染色图：

```python
groove_count, intersection_count, vis_name, vis_image = detect_transverse_grooves(
    image,
    groove_width_px=13,
    is_debug=True,
)
```

返回内容：

- `vis_name == "groove_intersections"`
- `vis_image` 为 BGR 图像数组

染色图中：

- 检测到的横沟区域叠加绿色半透明掩码。
- 每条横沟中心绘制水平线。
- 左上角绘制检测特征文字：`G:{groove_count}` 与 `X:{intersection_count}`。

## 示例

### 示例 1：基础横沟检测

```python
groove_count, intersection_count, _, _ = detect_transverse_grooves(
    image,
    groove_width_px=25,
)

print(f"横沟数量: {groove_count}")
print(f"交叉点数量: {intersection_count}")
```

### 示例 2：生成 debug 图但不在算法层保存

```python
groove_count, intersection_count, vis_name, vis_image = detect_transverse_grooves(
    image,
    groove_width_px=13,
    is_debug=True,
)

if vis_image is not None:
    cv2.imwrite(f".results/{vis_name}.png", vis_image)
```

保存路径由调用方决定。算法层只返回建议文件名和图像数组。

## 等价性验证

本算法迁移后，测试沿用真实图片输入与固定特征期望值做回归。测试数据目录包含：

```text
tests/datasets/test_groove_intersection/
  center_inf/
  side_inf/
```

- `center_inf/` 与 `side_inf/` 保存真实输入小图。
- 单元测试对这些真实图的 `groove_count` 与 `intersection_count` 做固定期望值比对。

任意一张图的特征输出不一致，都表示横沟检测或交点统计出现回归。debug 图只验证返回形状和绘制结果发生变化，不在算法文档中维护额外图片基准。

## 异常

| 异常 | 场景 |
| --- | --- |
| `InputDataError` | 输入图像为空、不是 ndarray、不是 BGR 三通道图，或 `groove_width_px` 不满足约定。 |
| `RuntimeProcessError` | OpenCV 处理、横沟分析、交叉点统计或 debug 图生成过程中出现运行时异常。 |

## 内部函数说明

| 函数 | 说明 |
| --- | --- |
| `_analyze_grooves` | 通过水平投影提取横沟中心位置、数量和掩码。 |
| `_count_intersections` | 基于横沟上下两侧列密度统计交叉点数量。 |
| `_skeletonize` | 形态学骨架化工具函数，用于白盒验证和后续调试。 |
| `_draw_debug_image` | 在 BGR 原图上绘制横沟掩码、中心线和文字标注。 |

## 设计边界

- 算法层接收 `groove_width_px`（像素）作为参数。
- 算法层不返回 score 或规则通过状态，只返回基础特征和可选 debug 图。
- 算法层不处理文件保存和业务流程编排。