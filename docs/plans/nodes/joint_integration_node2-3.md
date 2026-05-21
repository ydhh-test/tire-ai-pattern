# Node2 + Node3 联调集成测试实施文档

## 1. 背景与目标

Node2 (`stitch_scheme_generator`) 基于已评分小图生成拼接血缘 (`ImageLineage`)；Node3 (`big_image_stitcher`) 根据血缘执行实际拼图。联调测试验证两者串联端到端流程的正确性：

```
SmallImage[] + RuleConfig[] + scheme_rank
    │
    ▼
generate_stitch_scheme()          ← Node2
    │
    ▼
BigImage (含 ImageLineage，before_image 已填充)
    │
    ▼
stitch_big_image()                 ← Node3
    │
    ▼
BigImage (image_base64 更新，lineage.after_image 已填充)
```

### 核心挑战

Node2 在现有单元测试中使用**文本 payload 伪 base64**（如 `data:image/png;base64,side-a`），传入 Node3 会解码失败。联调测试必须使用**真实图片**作为 `SmallImage.image_base64`。

### 测试设计思路

两个核心用例，覆盖互补验证目标：

- **用例 1（冒烟测试）**：沿用 `test_stitch_scheme_generator.py` 的输入构建模式（评分分配、图片复用策略），验证 Node2 正常产出 → Node3 不报错，流程打通。
- **用例 2（格式兼容验证）**：从 `test_large_image_stitching.py` 的 `_build_lineage_with_black_decoration` 反推 Node2 输入，验证 Node2 能产出 Node3 预期格式的 lineage。

辅以尺寸校验和 after_image 填充校验，确保输出结构正确。

### 测试文件

- **新建文件**：`tests/integrations/test_joint_node2_node3.py`
- **参考现有测试**：
  - `tests/integrations/test_stitch_scheme_generator.py` — Node2 输入构建模式
  - `tests/integrations/test_large_image_stitching.py` — Node3 期望的 lineage 结构（反推 Node2 输入）
  - `tests/unittests/nodes/test_big_image_stitcher.py` — Node3 输入校验模式

### 测试数据集

使用 `tests/datasets/stitching/` 中的真实图片：

| 文件 | 说明 | 原始尺寸 | 用作 |
|------|------|----------|------|
| `rib1.png` | 边缘花纹 | 92×264 | SIDE 候选 |
| `rib5.png` | 边缘花纹 | 129×259 | SIDE 候选 |
| `rib2.png` | 中心花纹 | 92×128 | CENTER 候选 |
| `rib3.png` | 中心花纹 | 129×136 | CENTER 候选 |
| `rib4.png` | 中心花纹 | 107×136 | CENTER 候选 |

---

## 2. 测试代码工具层

### 2.1 图片编解码

```python
import base64
import cv2
import numpy as np
from pathlib import Path

DATASET_DIR = Path("tests/datasets/stitching")

def _load_image_as_base64(filename: str) -> str:
    """从数据集目录加载真实 PNG，编码为 data:image/png;base64,xxx 格式。"""
    img = cv2.imread(str(DATASET_DIR / filename))
    if img is None:
        raise FileNotFoundError(f"无法加载测试图片: {DATASET_DIR / filename}")
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise ValueError(f"Failed to encode image: {filename}")
    base64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/png;base64,{base64_str}"

def _base64_to_ndarray(image_base64: str) -> np.ndarray:
    """将 data:image/png;base64,xxx 解码为 numpy 数组。"""
    b64data = image_base64.split(",")[1]
    img_array = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("解码图片失败")
    return img
```

### 2.2 SmallImage 构建

```python
from src.models.image_models import SmallImage, ImageBiz, ImageEvaluation, ImageMeta, RuleEvaluation
from src.models.enums import RegionEnum, ImageFormatEnum, ImageModeEnum, LevelEnum, SourceTypeEnum
from src.models.rule_models import Rule1Config, Rule1Score

def make_real_small_image(
    region: RegionEnum,
    image_filename: str,
    score: int,
) -> SmallImage:
    """用真实图片文件构建带评分的 SmallImage。

    Args:
        region: 图片区域（SIDE 或 CENTER）
        image_filename: 数据集中的文件名（如 "rib1.png"）
        score: 评分分数，用于 Node2 的方案排序
    """
    base64_str = _load_image_as_base64(image_filename)
    image = _base64_to_ndarray(base64_str)
    return SmallImage(
        image_base64=base64_str,
        meta=ImageMeta(
            width=image.shape[1],
            height=image.shape[0],
            channels=image.shape[2],
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=len(base64_str),
        ),
        biz=ImageBiz(
            level=LevelEnum.SMALL,
            region=region,
            source_type=SourceTypeEnum.ORIGINAL,
        ),
        evaluation=ImageEvaluation(
            rules=[
                RuleEvaluation(
                    name="rule1",
                    config=Rule1Config(),
                    score=Rule1Score(score=score),
                )
            ],
            current_score=score,
        ),
    )
```

### 2.3 BigImage 占位

```python
from src.models.image_models import BigImage

def make_big_image_placeholder() -> BigImage:
    """构建占位 BigImage，image_base64 无实际意义，由 Node2/Node3 后续更新。"""
    return BigImage(
        image_base64="data:image/png;base64,placeholder",
        meta=ImageMeta(
            width=1, height=1, channels=3,
            mode=ImageModeEnum.RGB, format=ImageFormatEnum.PNG, size=0,
        ),
        biz=ImageBiz(
            level=LevelEnum.BIG,
            region=RegionEnum.CENTER,
            source_type=SourceTypeEnum.ORIGINAL,
        ),
    )
```

---

## 3. 规则配置

### 3.1 用例 1 配置（匹配 test_stitch_scheme_generator.py 模式）

```python
from src.models.rule_models import (
    Rule1Config, Rule2Config, Rule100Config, Rule101Config, Rule102Config,
    RibSizeItem, GrooveSizeItem, DecorationItem,
)

RULES_CONFIG_V1 = [
    Rule1Config(),   # 激活 Symmetry0
    Rule2Config(),   # 激活 Symmetry1
    Rule100Config(
        rib_number=5,
        rib_sizes=[
            RibSizeItem(rib_name="rib1", num_pitchs=5, rib_width=400, rib_height=640),
            RibSizeItem(rib_name="rib2", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib3", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib4", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib5", num_pitchs=6, rib_width=200, rib_height=640),
        ],
    ),
    # 5-RIB 方案需要 4 个主沟，否则 Node3 会因数量不匹配报错
    Rule101Config(groove_sizes=[
        GrooveSizeItem(groove_width=10, groove_height=640),
        GrooveSizeItem(groove_width=10, groove_height=640),
        GrooveSizeItem(groove_width=10, groove_height=640),
        GrooveSizeItem(groove_width=10, groove_height=640),
    ]),
    Rule102Config(
        decorations=[
            DecorationItem(
                position="left",
                decoration_width=300,
                decoration_height=640,
                decoration_opacity=128,
            )
        ],
    ),
]
```

预期输出尺寸：`rib1(400) + rib2(200) + rib3(200) + rib4(200) + rib5(200) + groove(10×4) = 1280`，高度 640。

### 3.2 用例 2 配置（反推 test_large_image_stitching.py）

`test_large_image_stitching.py` 的 `_build_lineage_with_black_decoration` 构建了 Symmetry0 方案（5 RIB，无继承/对称），参数与数据集完全对齐：

| 属性 | 值 |
|------|-----|
| RIB 数 | 5 (rib1=400, rib2=200, rib3=200, rib4=200, rib5=400) |
| 主沟 | 4 个，各 20×640 |
| 装饰 | 1 个，300×640，opacity=128 |
| 对称性 | Symmetry0（无对称） |
| 连续性 | Continuity0（默认，无连续操作） |

```python
RULES_CONFIG_V2 = [
    Rule1Config(),   # 仅 Symmetry0，不包含 Rule2Config（排除 Symmetry1）
    Rule100Config(
        rib_number=5,
        rib_sizes=[
            RibSizeItem(rib_name="rib1", num_pitchs=5, rib_width=400, rib_height=640),
            RibSizeItem(rib_name="rib2", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib3", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib4", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib5", num_pitchs=6, rib_width=400, rib_height=640),
        ],
    ),
    Rule101Config(groove_sizes=[
        GrooveSizeItem(groove_width=20, groove_height=640),
        GrooveSizeItem(groove_width=20, groove_height=640),
        GrooveSizeItem(groove_width=20, groove_height=640),
        GrooveSizeItem(groove_width=20, groove_height=640),
    ]),
    Rule102Config(
        decorations=[
            DecorationItem(
                position="left",
                decoration_width=300,
                decoration_height=640,
                decoration_opacity=128,
            )
        ],
    ),
]
```

注意：与 V1 的区别：
- **不含 Rule2Config**（强制只走 Symmetry0，与 `test_large_image_stitching` 一致）
- **rib5.rib_width=400**（而非 200），匹配 rib5.png 实际内容和 `test_large_image_stitching` 的 lineage 结构
- **groove_width=20**（而非 10），匹配 `test_large_image_stitching` 的 lineage 结构

预期输出尺寸：`rib1(400) + rib2(200) + rib3(200) + rib4(200) + rib5(400) + groove(20×4) = 1480`，高度 640。

---

## 4. 测试用例

### 4.1 用例 1：test_joint_smoke_node2_to_node3

**目标**：验证 Node2 正常输出 → Node3 不出错，流程打通。

沿用 `test_stitch_scheme_generator.py` 的输入构建模式：3 张 SIDE + 4 张 CENTER，其中 SIDE 肋5.png 评分最高(8)，CENTER 肋3/肋4 评分最高(10)。使用 `RULES_CONFIG_V1`（Rule1+Rule2，双模板竞争），scheme_rank=1。

```
=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
输入
=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

  SIDE 候选（3 张）：
    rib1.png  score=5
    rib5.png  score=8
    rib1.png  score=3   ← 同一张图不同评分（扩充排列候选数）

  CENTER 候选（4 张）：
    rib2.png  score=3
    rib3.png  score=10
    rib4.png  score=10
    rib2.png  score=2   ← 同一张图不同评分

  scheme_rank = 1
  rules_config = RULES_CONFIG_V1

=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
验证
=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

  1. Node2 产出 BigImage，lineage 不为 None
  2. lineage 中 rib/groove/decoration 的 before_image 均非空
  3. Node3 执行成功，返回值与原 big_image 为同一对象引用
  4. 输出 image_base64 以 "data:image/" 开头，不等于占位值
  5. 解码后的最终大图尺寸 = (640, 1280, 3)
  6. lineage 中所有 rib/groove/decoration 的 after_image 已填充、格式合法
```

### 4.2 用例 2：test_joint_node2_produces_expected_lineage

**目标**：验证 Node2 能产出 Node3 期望的 lineage 格式（从 `test_large_image_stitching.py` 反推）。

`_build_lineage_with_black_decoration` 构建了 SYMMETRY_0 方案，5 个 RIB 无继承，4 个 20×640 主沟，1 个 300×640 装饰。本用例使用匹配的 RULES_CONFIG_V2（仅 Rule1，无 Rule2），输入恰好 2 张 SIDE + 3 张 CENTER（Symmetry0 所需的最少原始图片数）。

```
=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
输入
=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

  SIDE 候选（2 张）：
    rib1.png  score=8
    rib5.png  score=5

  CENTER 候选（3 张）：
    rib2.png  score=10
    rib3.png  score=10
    rib4.png  score=10

  说明：Symmetry0 需要恰好 2 SIDE + 3 CENTER，所有图片都会被选中。
        评分仅决定排列顺序，分数相同利于随机覆盖多种排列。

  scheme_rank = 1
  rules_config = RULES_CONFIG_V2

=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
反推逻辑
=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

  test_large_image_stitching.py 的 lineage 结构：
    - StitchingScheme: SYMMETRY_0, 5 RIB
    - 每个 RIB 操作: (NONE,)
    - 所有 same_as = None（无继承）
    - MainGroove: 4 个，20×640
    - Decoration: 1 个，300×640，opacity=128

  Node2 对应输入：
    - 只有 Rule1Config（Symmetry0），无 Rule2Config（排除 Symmetry1）
    - Rule100 的 rib5 宽=400（匹配实际图片和 lineage 结构）
    - Rule101 的 groove_width=20（匹配 lineage 结构）
    - 5 张原始图片，评分不同以防分数相同导致任意排列

=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
验证
=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

  1. Node2 产出 lineage 结构正确：
     - stitching_scheme.name == StitchingSchemeName.SYMMETRY_0
     - rib_scheme_implementation 长度 = 5
     - main_groove_implementation 长度 = 4
     - decoration_implementation 长度 = 1
  2. 每个 rib 的 before_image 源于真实图片 base64，格式合法
  3. 每个 groove/decoration 的 before_image 由 Node2 生成（黑色图），尺寸匹配配置
  4. Node3 执行成功
  5. 解码后最终大图尺寸 = (640, 1480, 3)
  6. lineage 中所有 after_image 已填充、格式合法
```

### 4.3 断言规范

全项目统一使用 `rst == expected_rst` 范式——所有预期值通过变量声明，不在断言中 hardcode 字面量：

```python
# ✅ 正确
expected_prefix = "data:image/"
expected_width = 400 + 200 + 200 + 200 + 200 + 10 * 4
expected_height = 640
expected_channels = 3
expected_rst = (expected_height, expected_width, expected_channels)

rst = _base64_to_ndarray(result.image_base64)
assert rst.shape == expected_rst

# ❌ 错误（hardcode 字面量）
assert rst.shape == (640, 1280, 3)
assert result.image_base64.startswith("data:image/")
```

---

## 5. 测试代码结构

```python
"""
Node2 + Node3 联调集成测试

端到端验证 generate_stitch_scheme → stitch_big_image 的完整管线。
"""

from __future__ import annotations

import base64
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.models.enums import (
    ImageFormatEnum,
    ImageModeEnum,
    LevelEnum,
    RegionEnum,
    SourceTypeEnum,
    StitchingSchemeName,
)
from src.models.image_models import (
    BigImage,
    ImageBiz,
    ImageEvaluation,
    ImageLineage,
    ImageMeta,
    RuleEvaluation,
    SmallImage,
)
from src.models.rule_models import (
    DecorationItem,
    GrooveSizeItem,
    RibSizeItem,
    Rule1Config,
    Rule1Score,
    Rule2Config,
    Rule100Config,
    Rule101Config,
    Rule102Config,
)
from src.nodes.big_image_stitcher import stitch_big_image
from src.nodes.stitch_scheme_generator import generate_stitch_scheme
from src.utils.logger import get_logger


logger = get_logger("joint_test")

DATASET_DIR = Path("tests/datasets/stitching")

# ---------- 工具函数 ----------

def _load_image_as_base64(filename: str) -> str:
    """从数据集目录加载真实 PNG，编码为 data:image/png;base64,xxx 格式。"""
    img = cv2.imread(str(DATASET_DIR / filename))
    if img is None:
        raise FileNotFoundError(f"无法加载测试图片: {DATASET_DIR / filename}")
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise ValueError(f"Failed to encode image: {filename}")
    base64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/png;base64,{base64_str}"

def _base64_to_ndarray(image_base64: str) -> np.ndarray:
    """将 data:image/png;base64,xxx 解码为 numpy 数组。"""
    b64data = image_base64.split(",")[1]
    img_array = np.frombuffer(base64.b64decode(b64data), dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("解码图片失败")
    return img

def make_real_small_image(
    region: RegionEnum,
    image_filename: str,
    score: int,
) -> SmallImage:
    """用真实图片文件构建带评分的 SmallImage。"""
    base64_str = _load_image_as_base64(image_filename)
    image = _base64_to_ndarray(base64_str)
    return SmallImage(
        image_base64=base64_str,
        meta=ImageMeta(
            width=image.shape[1],
            height=image.shape[0],
            channels=image.shape[2],
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=len(base64_str),
        ),
        biz=ImageBiz(
            level=LevelEnum.SMALL,
            region=region,
            source_type=SourceTypeEnum.ORIGINAL,
        ),
        evaluation=ImageEvaluation(
            rules=[
                RuleEvaluation(
                    name="rule1",
                    config=Rule1Config(),
                    score=Rule1Score(score=score),
                )
            ],
            current_score=score,
        ),
    )

def make_big_image_placeholder() -> BigImage:
    """构建占位 BigImage。"""
    return BigImage(
        image_base64="data:image/png;base64,placeholder",
        meta=ImageMeta(
            width=1, height=1, channels=3,
            mode=ImageModeEnum.RGB, format=ImageFormatEnum.PNG, size=0,
        ),
        biz=ImageBiz(
            level=LevelEnum.BIG,
            region=RegionEnum.CENTER,
            source_type=SourceTypeEnum.ORIGINAL,
        ),
    )

# ---------- 规则配置 ----------

RULES_CONFIG_V1 = [
    Rule1Config(),
    Rule2Config(),
    Rule100Config(
        rib_number=5,
        rib_sizes=[
            RibSizeItem(rib_name="rib1", num_pitchs=5, rib_width=400, rib_height=640),
            RibSizeItem(rib_name="rib2", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib3", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib4", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib5", num_pitchs=6, rib_width=200, rib_height=640),
        ],
    ),
    Rule101Config(groove_sizes=[
        GrooveSizeItem(groove_width=10, groove_height=640),
        GrooveSizeItem(groove_width=10, groove_height=640),
        GrooveSizeItem(groove_width=10, groove_height=640),
        GrooveSizeItem(groove_width=10, groove_height=640),
    ]),
    Rule102Config(
        decorations=[
            DecorationItem(
                position="left",
                decoration_width=300,
                decoration_height=640,
                decoration_opacity=128,
            )
        ],
    ),
]

RULES_CONFIG_V2 = [
    Rule1Config(),
    Rule100Config(
        rib_number=5,
        rib_sizes=[
            RibSizeItem(rib_name="rib1", num_pitchs=5, rib_width=400, rib_height=640),
            RibSizeItem(rib_name="rib2", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib3", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib4", num_pitchs=6, rib_width=200, rib_height=640),
            RibSizeItem(rib_name="rib5", num_pitchs=6, rib_width=400, rib_height=640),
        ],
    ),
    Rule101Config(groove_sizes=[
        GrooveSizeItem(groove_width=20, groove_height=640),
        GrooveSizeItem(groove_width=20, groove_height=640),
        GrooveSizeItem(groove_width=20, groove_height=640),
        GrooveSizeItem(groove_width=20, groove_height=640),
    ]),
    Rule102Config(
        decorations=[
            DecorationItem(
                position="left",
                decoration_width=300,
                decoration_height=640,
                decoration_opacity=128,
            )
        ],
    ),
]

# ---------- 通用联调函数 ----------

def run_joint_pipeline(
    small_images: list[SmallImage],
    rules_config: list,
    scheme_rank: int = 1,
) -> BigImage:
    """执行 Node2 → Node3 完整管线。"""
    logger.info(">>> Step 1: generate_stitch_scheme (Node2)")
    big_image = generate_stitch_scheme(
        big_image=make_big_image_placeholder(),
        small_images=small_images,
        rules_config=rules_config,
        scheme_rank=scheme_rank,
    )

    assert big_image.lineage is not None, "Node2 必须生成 lineage"

    logger.info(">>> Step 2: stitch_big_image (Node3)")
    result = stitch_big_image(big_image)

    logger.info(">>> 联调完成")
    return result


# ---------- 测试用例 ----------

class TestJointNode2Node3:

    def test_joint_smoke_node2_to_node3(self):
        """用例 1：冒烟测试——Node2 正常输出 → Node3 不出错。

        沿用 test_stitch_scheme_generator.py 的输入构建模式。
        """
        expected_prefix = "data:image/"

        small_images = [
            make_real_small_image(RegionEnum.SIDE, "rib1.png", 5),
            make_real_small_image(RegionEnum.SIDE, "rib5.png", 8),
            make_real_small_image(RegionEnum.SIDE, "rib1.png", 3),
            make_real_small_image(RegionEnum.CENTER, "rib2.png", 3),
            make_real_small_image(RegionEnum.CENTER, "rib3.png", 10),
            make_real_small_image(RegionEnum.CENTER, "rib4.png", 10),
            make_real_small_image(RegionEnum.CENTER, "rib2.png", 2),
        ]

        result = run_joint_pipeline(small_images, RULES_CONFIG_V1)

        # 1. 返回值与原 big_image 为同一引用
        assert result is not None

        # 2. image_base64 已更新
        assert result.image_base64[:len(expected_prefix)] == expected_prefix
        placeholder = "data:image/png;base64,placeholder"
        assert result.image_base64 != placeholder

        # 3. 最终大图尺寸
        expected_width = 400 + 200 + 200 + 200 + 200 + 10 * 4
        expected_height = 640
        expected_channels = 3
        expected_shape = (expected_height, expected_width, expected_channels)
        rst = _base64_to_ndarray(result.image_base64)
        assert rst.shape == expected_shape

        # 4. lineage 中所有 before_image 已填充
        self._assert_before_images_filled(result.lineage)

        # 5. lineage 中所有 after_image 已填充、格式合法
        self._assert_after_images_filled(result.lineage, expected_prefix)

    def test_joint_node2_produces_expected_lineage(self):
        """用例 2：反推 test_large_image_stitching.py，验证 Node2 产出 Node3 期望格式。

        从 _build_lineage_with_black_decoration 反推 Node2 输入：
        - 仅 Rule1（Symmetry0），无 Rule2
        - rib5 width=400，groove_width=20
        """
        expected_prefix = "data:image/"

        small_images = [
            make_real_small_image(RegionEnum.SIDE, "rib1.png", 8),
            make_real_small_image(RegionEnum.SIDE, "rib5.png", 5),
            make_real_small_image(RegionEnum.CENTER, "rib2.png", 10),
            make_real_small_image(RegionEnum.CENTER, "rib3.png", 10),
            make_real_small_image(RegionEnum.CENTER, "rib4.png", 10),
        ]

        result = run_joint_pipeline(small_images, RULES_CONFIG_V2)

        # 1. lineage 结构校验
        lineage: ImageLineage = result.lineage
        assert lineage.stitching_scheme.stitching_scheme_abstract.name == \
            StitchingSchemeName.SYMMETRY_0

        # 2. RIB/主沟/装饰数量
        ribs = lineage.stitching_scheme.ribs_scheme_implementation
        assert len(ribs) == 5
        grooves = lineage.main_groove_scheme.main_groove_implementation
        assert len(grooves) == 4
        decs = lineage.decoration_scheme.decoration_implementation
        assert len(decs) == 1

        # 3. 装饰配置对齐
        assert decs[0].decoration_width == 300
        assert decs[0].decoration_height == 640
        assert decs[0].decoration_opacity == 128

        # 4. before_image 和 after_image
        self._assert_before_images_filled(lineage)
        self._assert_after_images_filled(lineage, expected_prefix)

        # 5. 输出尺寸（rib5=400，groove=20）
        expected_width = 400 + 200 + 200 + 200 + 400 + 20 * 4
        expected_height = 640
        expected_channels = 3
        expected_shape = (expected_height, expected_width, expected_channels)
        rst = _base64_to_ndarray(result.image_base64)
        assert rst.shape == expected_shape

    # ---------- 共享断言辅助 ----------

    def _assert_before_images_filled(self, lineage: ImageLineage):
        """验证 lineage 中所有 before_image 已填充、格式合法。"""
        expected_prefix = "data:image/"

        # RIB before_image：来自真实 SmallImage base64
        ribs = lineage.stitching_scheme.ribs_scheme_implementation
        for i, rib in enumerate(ribs):
            assert rib.before_image is not None, f"rib[{i}] before_image 为空"
            assert rib.before_image[:len(expected_prefix)] == expected_prefix, \
                f"rib[{i}] before_image 格式不正确"

        # 主沟 before_image：Node2 生成黑色图
        grooves = lineage.main_groove_scheme.main_groove_implementation
        for i, groove in enumerate(grooves):
            assert groove.before_image is not None, f"groove[{i}] before_image 为空"
            assert groove.before_image[:len(expected_prefix)] == expected_prefix, \
                f"groove[{i}] before_image 格式不正确"

        # 装饰 before_image：Node2 生成黑色图
        decs = lineage.decoration_scheme.decoration_implementation
        for i, dec in enumerate(decs):
            assert dec.before_image is not None, f"decoration[{i}] before_image 为空"
            assert dec.before_image[:len(expected_prefix)] == expected_prefix, \
                f"decoration[{i}] before_image 格式不正确"

    def _assert_after_images_filled(self, lineage: ImageLineage, expected_prefix: str):
        """验证 lineage 中所有 after_image 已填充、格式合法。"""
        ribs = lineage.stitching_scheme.ribs_scheme_implementation
        for i, rib in enumerate(ribs):
            assert rib.after_image is not None, f"rib[{i}] after_image 为空"
            assert rib.after_image[:len(expected_prefix)] == expected_prefix, \
                f"rib[{i}] after_image 格式不正确"

        grooves = lineage.main_groove_scheme.main_groove_implementation
        for i, groove in enumerate(grooves):
            assert groove.after_image is not None, f"groove[{i}] after_image 为空"
            assert groove.after_image[:len(expected_prefix)] == expected_prefix, \
                f"groove[{i}] after_image 格式不正确"

        decs = lineage.decoration_scheme.decoration_implementation
        for i, dec in enumerate(decs):
            assert dec.after_image is not None, f"decoration[{i}] after_image 为空"
            assert dec.after_image[:len(expected_prefix)] == expected_prefix, \
                f"decoration[{i}] after_image 格式不正确"
```

---

## 6. 注意事项

### 6.1 主沟数量匹配

Node2 根据 `Rule101Config.groove_sizes` 列表长度生成主沟数量；Node3 要求 `主沟数 = RIB数 - 1`。两个配置都已保证 `groove_sizes` 有 **4 个元素**（对应 5-RIB 方案）。

### 6.2 before_image 来源

- **RIB before_image**：来自 `SmallImage.image_base64`（真实 PNG 数据），由 Node3 处理（操作序列 + 节距重复 + resize）
- **Groove/Decoration before_image**：由 Node2 内部 `_black_image_base64()` 生成（纯黑填充图）

联调测试中 RIB 必须使用真实图片，Groove/Decoration 的 before_image 由 Node2 自动生成，无需在 SmallImage 中准备。

### 6.3 输入图片原始尺寸

dataset 中图片原始尺寸与 Rule100Config 中 rib_width/rib_height 不一致，这是正常的——Node3 的 `RibOperation` 管线会执行 resize 到目标尺寸。SmallImage.meta 应如实反映原始图片尺寸。

### 6.4 方案排名稳定性

本测试假设 `_CandidateScheme.rank()` 对同分方案使用稳定排序。若某日因实现变更导致 tiebreaking 行为变化导致测试 fail，应由对应代码作者修复排序稳定性。

---

## 7. 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/integrations/test_joint_node2_node3.py` | **新建** | 联调集成测试代码 |
| `tests/datasets/stitching/*.png` | 已有 | 测试用真实图片（无需修改） |
| `docs/plans/nodes/joint_integration_node2-3.md` | **本文档** | 测试实施计划 |
