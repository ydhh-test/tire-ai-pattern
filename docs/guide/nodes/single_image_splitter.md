
# 大图拆分核心算法 - 单图处理模块

## 文档信息

| 属性 | 值 |
|------|-----|
| **适用模块** | `src/processing/single_image_splitter.py` |
| **目标读者** | PM、架构师、开发工程师、测试工程师 |

---

## 1. 概述

### 1.1 模块定位

`single_image_splitter` 是大图拆分功能的**核心流程入口**，负责将完整的轮胎设计大图拆分为多个小图（side 侧边图和 center 中间图）。

**核心职责**：
- 输入：完整设计图（base64 编码的 BGR 图像）+ 切分规则配置
- 输出：多张小图（base64 编码）+ 异常检测结果

### 1.2 业务价值

| 维度 | 说明 |
|------|------|
| **输入输出** | 一对多映射，单张大图拆分为多个小图 |
| **业务场景** | 轮胎设计图自动化切分，可支持后续用户自定义拼接流程 |
| **技术价值** | 实现设计图的结构化分解 |

---

## 2. 术语定义

| 术语 | 定义 | 坐标系假设 |
|------|------|------------|
| **主沟 (Groove)** | RIB 之间的宽沟槽，宽度 8-12mm，3 条或 4 条由用户定义 | 沿 Y 轴延伸 |
| **RIB** | 轮胎宽度方向的纵向条带（RIB1-5，从两侧到中心） | 横向（X 轴） |
| **大图** | 用户完整的设计图，包含所有 RIB 和主沟 | - |
| **小图** | 拆分后的子图像，包含 center 小图和 side 小图 | - |
| **节距 (Pitch)** | 轮胎圆周方向的重复单元，包含 5-7 个横向纹理周期 | 纵向（Y 轴） |

**坐标系约定**：
- **X 轴**：横向（RIB 排列方向）
- **Y 轴**：纵向（节距重复方向）

---

## 3. 架构设计

### 3.1 模块分层结构

```
┌──────────────────────────────────────────────────────────┐
│              processing/single_image_splitter.py          │
│              (流程编排与主入口)                           │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  cropping   │  │  analysis   │  │ validation  │     │
│  │ (裁剪切分)   │  │ (分析检测)   │  │ (配置校验)   │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
└─────────┼────────────────┼────────────────┼─────────────┘
          ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ OpenCV  │      │ NumPy   │      │ Logger  │
    │ 图像处理 │      │ 数值计算 │      │ 日志记录 │
    └─────────┘      └─────────┘      └─────────┘
```

### 3.2 文件职责划分

| 文件 | 职责 | 核心功能 |
|------|------|----------|
| `processing/single_image_splitter.py` | 流程编排主入口 | 调用各算法模块，组织完整处理流程 |
| `split/cropping.py` | 裁剪与切分算法 | 纵向切分、边缘清理、横向切分 |
| `split/analysis.py` | 图像分析与检测 | 主色调分析、竖直线去除、异常检测 |
| `split/validation.py` | 配置参数校验 | 参数合法性验证 |

### 3.3 依赖关系

```
processing/single_image_splitter.py
    ├── core.split.cropping
    │   ├── remove_black_and_split_segments
    │   ├── remove_side_white
    │   ├── remove_edge_gray
    │   ├── random_horizontal_crop
    │   └── detect_periodic_blocks
    ├── core.split.analysis
    │   ├── analyze_dominant_color
    │   ├── remove_vertical_lines_center
    │   └── analyze_single_image_abnormalities
    └── core.split.validation
        └── _validate_vertical_parts_to_keep
```

---

## 4. 核心算法详解

### 4.1 纵向切分算法

**算法名称**：`remove_black_and_split_segments`

**算法原理**：
1. 将图像转换为 RGB 格式
2. 检测连续全黑列（像素值 < 10 的列）
3. 选择宽度最大的 N 个黑色段作为主沟（N = num_segments_to_remove）
4. 移除这些黑色段，返回剩余的 RIB 图像列表

**关键参数**：
- `num_segments_to_remove`: 移除的主沟数量（支持 3 或 4）

**输出结果**：
- 4 主沟模式：返回 5 张图像（RIB1-5）
- 3 主沟模式：返回 4 张图像（RIB1-4）

### 4.2 边缘清理算法

#### 4.2.1 白边去除
**算法名称**：`remove_side_white`

**原理**：基于阈值的边缘检测，去除单侧白色边缘（阈值 > 250）

#### 4.2.2 灰边去除
**算法名称**：`remove_edge_gray`

**原理**：
1. 分析图像主色调（`analyze_dominant_color`）
2. 在边缘区域（默认 23% 宽度）检测与主色调接近的灰色区域
3. 将灰色区域替换为白色（255,255,255）

### 4.3 横向切分算法

#### 4.3.1 周期检测
**算法名称**：`detect_periodic_blocks`

**原理**：
1. 计算行密度自相关函数
2. 检测周期性峰值，确定节距周期
3. 提取第一个有效周期块（包含足够纹理信息）

**参数范围**：
- 最小周期数：5
- 最大周期数：7

#### 4.3.2 随机裁剪（备选方案）
**算法名称**：`random_horizontal_crop`

**触发条件**：当周期检测失败时使用

**原理**：随机选择 Y 轴位置裁剪一个节距高度的图像块

#### 4.3.3 竖直线去除
**算法名称**：`remove_vertical_lines_center`

**原理**：
1. 使用 Canny 边缘检测
2. Hough 变换检测竖直线
3. 去除图像中央区域的竖直线，保护与其他线段的交点

### 4.4 异常检测算法

**算法名称**：`analyze_single_image_abnormalities`

**检测维度**：

| 检测项 | 判定条件 | 异常描述 |
|--------|----------|----------|
| 宽高比 | 宽/高 > 4 或 高/宽 > 4 | 宽高比异常 |
| 颜色种类 | 唯一颜色数 < 3 | 颜色种类过少 |

---

## 5. 流程编排与数据流

### 5.1 完整处理流程

```
输入图像 (BGR格式)
       │
       ▼ [纵向切分]
┌─────────────────────────────┐
│ remove_black_and_split_segments │
└─────────────────────────────┘
       │
       ▼ [得到分段]
vertical_parts = [img1, img2, img3, img4, img5]  (4主沟)
                 或 [img1, img2, img3, img4]      (3主沟)
       │
       ▼ [可选: 配置过滤]
filtered_parts = 根据 vertical_parts_to_keep 保留指定索引
       │
       ▼ [分类 + 白边去除 + 宽度过滤]
┌─────────────┬─────────────────┐
│ side_images │   center_images │
│ [(1, img1), │ [(2, img2),     │
│  (5, img5)] │  (3, img3),     │
│  (4主沟)    │  (4, img4)]     │
│             │  (center不经过   │
│             │   灰边去除)      │
└─────────────┴─────────────────┘
       │                 │
       ▼ [灰边去除]       │
side_images_cleaned       │
       │                 │
       └────────┬────────┘
                ▼ [横向切分]
    ┌───────────────────────────┐
    │ detect_periodic_blocks    │
    │ 或 random_horizontal_crop │
    │ + remove_vertical_lines   │
    └───────────────────────────┘
                │
                ▼ [异常检测三分流]
┌───────────────┬───────────────┬───────────────┐
│side_final     │center_final   │abnormal       │
│_images        │_images        │_images        │
│[(img, suffix)]│[(img, suffix)]│[(img, suffix, │
│               │               │ abnormalities)]│
└───────────────┴───────────────┴───────────────┘
```

### 5.2 数据流详细说明

#### 阶段一：纵向切分，为RIB图

```
输入: img (numpy.ndarray, BGR)
         │
         ▼ [remove_black_and_split_segments]
输出: vertical_parts = [numpy.ndarray, ...]
         │
         ├─ 4主沟模式: 5个元素 (RIB1-5)
         └─ 3主沟模式: 4个元素 (RIB1-4)
```

#### 阶段二：配置过滤（可选）

```
输入: vertical_parts, vertical_parts_to_keep=[1,2,3,4]
         │
         ▼ [列表过滤]
输出: filtered_parts = 只保留索引在配置中的图像段
```

#### 阶段三：分类与白边去除

```
输入: filtered_parts
         │
         ▼ [分类逻辑]
输出: side_images + center_images
         │
         ├─ side_images: 索引为 1 和 最后一个的图像
         │               (经过 remove_side_white)
         │
         └─ center_images: 中间索引的图像
                           (不经过灰边去除)
```

#### 阶段四：灰边去除（仅 side）

```
输入: side_images
         │
         ▼ [analyze_dominant_color + remove_edge_gray]
输出: side_images_cleaned
```

#### 阶段五：RIB图横向切分为小图

```
输入: side_images_cleaned + center_images
         │
         ▼ [detect_periodic_blocks / random_horizontal_crop]
         ▼ [remove_vertical_lines_center]
输出: side_final_images + center_final_images
         │
         ├─ 每个输入图像生成 1-2 个输出（带/不带去线版本）
         │
         └─ suffix: "_side_partX_periodic" 或 "_center_partX_random"
```

#### 阶段六：异常检测

```
输入: side_final_images + center_final_images
         │
         ▼ [analyze_single_image_abnormalities]
输出: 三分流
         ├─ side_final_images: 正常侧边图像
         ├─ center_final_images: 正常中间图像
         └─ abnormal_images: 异常图像（含异常描述）
```

### 5.3 数据结构定义

**输入参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| image | numpy.ndarray | - | BGR 格式图像 |
| num_segments_to_remove | int | 4 | 主沟数量（3 或 4） |
| gray_tolerance | int | 20 | 灰色容差 |
| gray_edge_percent | int | 50 | 边缘百分比 |
| vertical_parts_to_keep | list[int] | None | 保留的纵向分段索引 |

**输出结果**：

```python
{
    'side_final_images': list[(numpy.ndarray, str)],   # 正常侧边图像
    'center_final_images': list[(numpy.ndarray, str)], # 正常中间图像
    'abnormal_images': list[(numpy.ndarray, str, list)], # 异常图像
    'stats': {
        'status': str,           # 'success' / 'error' / 'config_error'
        'vertical_segments': int,
        'gray_edge_removed': int,
        'horizontal_splits': int,
        'abnormal_count': int,
        'error_message': str     # 仅在 error 状态时存在
    }
}
```

---

## 6. 配置说明

### 6.1 配置参数表

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|----------|------|
| num_segments_to_remove | int | 4 | [3, 4] | 主沟数量 |
| gray_tolerance | int | 20 | 0-255 | 灰色检测容差 |
| gray_edge_percent | int | 50 | 0-100 | 边缘处理宽度百分比 |
| vertical_parts_to_keep | list[int] | None | 有效索引范围 | 保留的分段索引 |

### 6.2 参数校验规则

当提供 `vertical_parts_to_keep` 时，需满足：

| 规则 | 校验逻辑 | 错误信息 |
|------|----------|----------|
| 非空 | 列表不能为空 | "vertical_parts_to_keep不能为空列表" |
| 无重复 | 列表值不能重复 | "包含重复值: {duplicates}" |
| 有效范围 | 值必须在 [1, num_segments_to_remove+1] | "包含无效索引" |
| 包含side | 必须包含至少一个side索引 | "必须包含side部分" |
| 包含center | 必须包含至少一个center索引 | "必须包含center部分" |

### 6.3 side/center 索引映射

| num_segments_to_remove | side 索引 | center 索引 |
|------------------------|-----------|-------------|
| 4（5个RIB） | {1, 5} | {2, 3, 4} |
| 3（4个RIB） | {1, 4} | {2, 3} |

---

## 7. 验收标准

### 7.1 功能验收点

| 验收项 | 验收标准 |
|--------|----------|
| 纵向切分 | 4主沟输入正确拆分为5段，3主沟拆分为4段 |
| 白边去除 | 图像边缘白色区域被正确裁剪 |
| 灰边去除 | 侧边图像边缘灰色区域替换为白色 |
| 周期检测 | 正确识别节距周期并提取有效块 |
| 随机裁剪 | 周期检测失败时正确回退到随机裁剪 |
| 竖直线去除 | 中央区域竖直线被去除，交点被保护 |
| 异常检测 | 宽高比异常和颜色过少图像被正确识别 |

### 7.2 边界条件处理

| 边界场景 | 处理方式 |
|----------|----------|
| 过窄图像段（宽度 < 5） | 跳过该段，记录警告日志 |
| 黑色段数量不足 | 记录警告，使用所有检测到的黑色段 |
| 周期检测失败 | 回退到随机裁剪 |
| 配置参数错误 | 返回 config_error 状态和错误信息 |

### 7.3 异常场景覆盖

| 异常类型 | 触发条件 | 预期行为 |
|----------|----------|----------|
| 配置错误 | 参数不在有效范围 | 返回错误状态和描述 |
| 图像处理错误 | 图像格式错误/损坏 | 返回错误状态和堆栈 |
| 空图像输入 | 图像数组为空 | 返回错误状态 |

---

**文档结束**
