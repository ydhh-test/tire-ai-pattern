# compute_land_sea_ratio

## 功能概述

`compute_land_sea_ratio` 是海陆比算法的核心入口，用于计算轮胎花纹样稿的海陆比（黑色区域与灰色区域占图像总面积的百分比）。

海陆比是评估轮胎花纹排水性能的重要指标。黑色区域代表深沟槽，灰色区域代表浅沟槽或细花纹，两者之和与总面积的比值即为海陆比。

本模块属于算法层（`src/core/scoring/`），只负责像素统计和比值计算，不含任何评分或业务配置逻辑。评分逻辑由规则层 `Rule13Executor` 负责。

---

## 函数入口

```python
from src.core.scoring.land_sea_ratio import compute_land_sea_ratio
```

---

## 函数签名

```python
def compute_land_sea_ratio(
    image: np.ndarray,
    is_debug: bool = False,
) -> tuple[float, str, np.ndarray | None]:
```

---

## 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `image` | `np.ndarray` | 必填 | 输入 BGR 图像，形状必须为 `(H, W, 3)` |
| `is_debug` | `bool` | `False` | 是否输出可视化调试图像 |

---

## 输出参数

函数返回一个包含三个元素的 tuple：

| 位置 | 名称 | 类型 | 说明 |
|---|---|---|---|
| 0 | `ratio_percent` | `float` | 实际海陆比百分比，保留两位小数。例如 `24.72` 表示 24.72% |
| 1 | `vis_name` | `str` | 建议的可视化文件名（不含扩展名）。非 debug 模式返回空字符串 `""` |
| 2 | `vis_image` | `np.ndarray` 或 `None` | 可视化图像（BGR）。非 debug 模式返回 `None` |

---

## 算法逻辑

计算流程分为三步：

**第一步：灰度转换**

将输入 BGR 图像转换为单通道灰度图，后续所有像素统计基于灰度值进行。

**第二步：像素面积统计**

- 黑色区域：灰度值在 `[0, 50]` 范围内的像素，统计其数量（`black_area`）
- 灰色区域：灰度值在 `[51, 200]` 范围内的像素，统计其数量（`gray_area`）
- 总面积：图像宽 × 高（像素数）

**第三步：海陆比计算**

```
ratio_percent = (black_area + gray_area) / total_area × 100
```

结果保留两位小数。

**可选：debug 可视化**

当 `is_debug=True` 时，在原图上叠加颜色标注：
- 黑色区域叠加红色半透明覆盖层（alpha=0.5）
- 灰色区域叠加绿色半透明覆盖层（alpha=0.5）
- 左上角用 PIL 绘制海陆比百分比文字（字体大小自适应图像尺寸，文字颜色根据背景亮度自动选黑/白，支持中文显示）

---

## 异常处理

| 异常类 | 触发条件 |
|---|---|
| `InputDataError` | `image` 为 `None`，或非 `np.ndarray`，或形状不是 `(H, W, 3)` |
| `RuntimeProcessError` | 内部 cv2 计算失败，原始异常挂在 `__cause__` 上 |
| `RuntimeProcessError` | debug 可视化生成失败，原始异常挂在 `__cause__` 上 |

---

## 使用示例

### 基础用法

```python
import cv2
from src.core.scoring.land_sea_ratio import compute_land_sea_ratio

image = cv2.imread("combine_horizontal/sample.png")

ratio_percent, _, _ = compute_land_sea_ratio(image)
print(f"海陆比: {ratio_percent}%")
```

### 生成 debug 可视化图像

```python
import pathlib
import numpy as np

ratio_percent, vis_name, vis_image = compute_land_sea_ratio(image, is_debug=True)

# 由调用方决定是否保存，算法层不保存文件
if vis_image is not None:
    output_path = pathlib.Path("output") / f"{vis_name}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    success, buf = cv2.imencode(".png", vis_image)
    if success:
        np.array(buf).tofile(str(output_path))
```

### 规则层调用方式（Rule13Executor）

评分逻辑由规则层负责，算法层只提供 `ratio_percent`：

```python
# Rule13Executor.exec_feature 内部
ratio_percent, _, _ = compute_land_sea_ratio(bgr)
return Rule13Feature(land_ratio=ratio_percent)

# Rule13Executor.exec_score 内部
if config.land_ratio_min <= ratio <= config.land_ratio_max:
    score = config.max_score          # 2 分（优秀）
elif ratio 在容差区间内:
    score = 1                         # 1 分（合格）
else:
    score = 0                         # 0 分（不合格）
```

---

## 内部辅助函数

以下函数为算法内部函数，由 `compute_land_sea_ratio` 调用，不作为公开 API。

### `_compute_black_area(gray: np.ndarray) -> int`

统计灰度值在 `[0, 50]` 范围内的像素数（黑色区域）。

### `_compute_gray_area(gray: np.ndarray) -> int`

统计灰度值在 `[51, 200]` 范围内的像素数（灰色区域）。

### `_draw_debug_image(image, gray, ratio_percent) -> np.ndarray`

生成带颜色叠加标注的可视化图像，左上角标注海陆比值。

### `_put_chinese_text(bgr_image, text, position, font_size, color_bgr) -> np.ndarray`

用 PIL 在 BGR 图像上绘制中文文字，避免 `cv2.putText` 中文乱码。字体优先加载系统 `simhei.ttf`，找不到时降级为 PIL 默认字体。

---

## 测试覆盖

| 测试类 | 覆盖内容 |
|---|---|
| `TestComputeLandSeaRatioApi` | 输入边界：None、非 ndarray、灰度图；返回类型；纯白图零边界 |
| `TestBlackGrayArea` | 黑色/灰色区域边界值（灰度值 50/51、200/201） |
| `TestDebugVisualization` | is_debug=True/False 的返回类型、文件名、图像形状、dtype |
| `TestRuntimeErrors` | 内部计算异常和 debug 异常的 RuntimeProcessError 包装 |
| `TestRealImages` | 真实大图海陆比值等价性验证；与 wise_image_dev1 像素级比对 |

---

## 迁移说明

本模块从老架构 `feature/dev` 的 `rules/scoring/land_sea_ratio.py` 迁移而来，并在 `feature/dev2_rule6_1_rule` 分支完成算法层独立性重构。

| 项目 | 老架构 | 初次迁移（dev2） | 当前版本（重构后） |
|---|---|---|---|
| 模块路径 | `rules.scoring.land_sea_ratio` | `src.core.scoring.land_sea_ratio` | `src.core.scoring.land_sea_ratio` |
| 函数入参 | `(img, conf: dict)` | `(image, target_min, target_max, margin, is_debug)` | `(image, is_debug)` |
| 函数出参 | `(score: int, details: dict)` | `(score, ratio_percent, vis_name, vis_image)` | `(ratio_percent, vis_name, vis_image)` |
| 评分逻辑 | 算法层内部 | 算法层内部（`_score()`） | 规则层 `Rule13Executor.exec_score` |
| 业务参数 | 从配置 dict 读取 | 算法层显式参数 | 规则层 `Rule13Config` 字段 |
| 可视化文字 | `cv2.putText`（中文乱码） | `cv2.putText`（中文乱码） | PIL `ImageDraw.text`（中文正常） |
| 文件操作 | 算法层包含 `Path`、`json.dump` | 算法层无文件 I/O | 算法层无文件 I/O |
