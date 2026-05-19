# 大图生成函数实施设计

## 1. 设计概述

基于PRD文档和项目架构规范，实现`generate_large_image_from_lineage`函数，该函数负责根据`ImageLineage`血缘信息完成完整的图片处理流程：RIB预处理 → 主沟预处理 → 装饰预处理 → 参数验证 → 横向拼接 → 装饰覆盖。

### 1.1 技术选型决策
- **统一使用cv2**: 项目已有的`src/utils/image_utils.py`完全基于OpenCV (cv2)，所有RIB原子操作均可通过cv2实现
- **数据格式**: 统一使用`np.ndarray` (BGR格式) 进行图像处理
- **移除output_format参数**: 输出大图为base64字符串，无需指定格式参数

### 1.2 架构定位
- **入口层**: `src/processing/`（业务逻辑层）
- **核心算法层**: `src/core/operation/`（纯算法层）
- **工具层**: `src/utils/`（已有图像工具）
- **职责分离**: 
  - `src/processing/`: 处理业务数据类，协调处理流程
  - `src/core/operation/`: 实现纯粹的图像操作算法，输入输出为基本类型
  - `src/utils/`: 提供基础图像转换和处理工具（已存在）

### 1.3 最终文件位置
- **入口函数**: `src/processing/image_stiching.py`
- **业务处理函数**: `src/processing/image_stiching.py`
- **核心算法**: `src/core/operation/image_operation.py`
- **测试文件**: 
  - `tests/unittests/processing/test_image_stiching.py`
  - `tests/unittests/core/operation/test_image_operation.py`

## 2. 函数签名与接口

### 2.1 入口函数
```python
from typing import Tuple
from src.models.image_models import ImageLineage

def generate_large_image_from_lineage(
    lineage: ImageLineage,
    is_debug: bool = False
) -> Tuple[ImageLineage, str]:
    """
    根据血缘信息生成大图
    
    Args:
        lineage: ImageLineage - 包含完整血缘信息的对象
        is_debug: bool - 是否启用调试模式，默认False
    
    Returns:
        Tuple[ImageLineage, str] - (更新后的血缘对象, base64编码的大图)
        
    Raises:
        ValueError: 当参数验证失败时
        RuntimeError: 当图像处理过程中发生错误时
    """
```

## 3. 核心设计：RIB操作执行机制

### 3.1 问题背景
RIB操作以序列形式传入，例如：
- `("resize_horizontal_2x", "left")` → 先横向拉伸2倍，再截取左边  
- `("",)` 或 `()` → 无操作

需要设计合理的执行机制来处理这种序列化操作。

### 3.2 双层执行架构

#### 操作序列执行器（协调层）
- **函数**: `apply_rib_operations_sequence()`
- **位置**: `src/core/operation/image_operation.py`
- **职责**: 按顺序调用单个操作执行器，处理整个操作序列
- **特点**: 自动跳过空操作，保证执行效率

#### 单个操作执行器（执行层）  
- **函数**: `apply_single_rib_operation()`
- **位置**: `src/core/operation/image_operation.py`
- **职责**: 实现15种RIB原子操作的具体逻辑
- **特点**: 专注单一职责，易于测试和维护

### 3.3 执行流程示例
```
输入: ("resize_horizontal_2x", "left")

执行过程:
1. apply_rib_operations_sequence 接收操作序列
2. 循环处理每个操作:
   ├─ resize_horizontal_2x → 图像宽度×2  
   └─ left → 截取左半部分
3. 返回最终处理结果
```

这种设计确保了代码的清晰性、可测试性和可扩展性。

## 4. 整体调用关系

### 4.1 架构概览
```
┌─────────────────────┐
│   入口层            │
│ src/processing/     │
│                     │
│ generate_large_image_from_lineage()
│   ↓ 调用业务处理函数
│   _process_rib_images()
│   _process_main_groove()  
│   _process_decoration()
│   _build_concatenation_sequence()
│   _apply_decorations_to_big_image()
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│   核心算法层        │
│ src/core/operation/ │
│                     │
│ apply_rib_operations_sequence() ←─┐
│ apply_single_rib_operation()     │ 处理RIB操作序列
│ horizontal_concatenate()         │
│ overlay_decoration()             │
│ repeat_vertically()              │
│ apply_opacity()                  │
└─────────────────────┘
          │
          ▼  
┌─────────────────────┐
│   工具层            │
│ src/utils/          │
│ (已存在)            │
│                     │
│ base64_to_ndarray()  │
│ ndarray_to_base64()  │
│ resize_image()       │
└─────────────────────┘
```

### 4.2 各层作用说明

**入口层 (src/processing/)**
- 作为整个功能的统一入口
- 负责业务数据类的操作和流程协调
- 处理参数验证和错误处理
- 对外提供简洁的API接口

**核心算法层 (src/core/operation/)**
- 实现所有图像处理的核心算法
- 输入输出均为基本类型（np.ndarray、base64等）
- 与业务逻辑完全解耦
- 专注于算法正确性和性能优化

**工具层 (src/utils/)**
- 复用项目已有的基础工具函数
- 提供图像格式转换和基础处理能力
- 避免重复造轮子，保持代码一致性

## 5. 详细实现方案

### 5.1 src/core/operation/image_operation.py（纯算法层）
```python
import cv2
import numpy as np
from src.models.enums import RibOperation
from typing import List, Tuple, Optional

# 操作序列执行器 - 按顺序执行多个操作  
def apply_rib_operations_sequence(image: np.ndarray, operations: Tuple[RibOperation, ...]) -> np.ndarray:
    """按顺序执行RIB操作序列"""

# 单个操作执行器 - 执行单个RIB原子操作
def apply_single_rib_operation(image: np.ndarray, operation: RibOperation) -> np.ndarray:
    """执行单个RIB原子操作"""
    
# 其他核心算法函数...
```

### 5.2 src/processing/image_stiching.py（业务层）
```python
import numpy as np
from typing import List, Tuple, Optional
from src.models.image_models import ImageLineage
from src.models.scheme_models import (
    RibSchemeImpl, 
    MainGrooveImpl, 
    DecorationImpl
)
from src.utils.image_utils import (
    base64_to_ndarray,
    ndarray_to_base64,
    resize_image
)
from src.core.operation.image_operation import (
    apply_rib_operations_sequence,
    repeat_vertically,
    apply_opacity,
    horizontal_concatenate,
    overlay_decoration
)

# 业务处理函数 - 输入输出为数据类
def _process_rib_images(ribs: List[RibSchemeImpl], is_debug: bool = False) -> None:
    """
    处理所有RIB图片
    
    流程:
    1. 跳过检查: 如果 rib_image 已存在，跳过处理
    2. 解码 small_image (base64) → np.ndarray
    3. 执行 operations 操作序列（调用core层apply_rib_operations_sequence）
    4. 纵向重复 num_pitchs 次（调用core层算法）
    5. resize(rib_width, rib_height)（调用utils层resize_image）
    6. 编码为base64存入 rib_image
    """
# ... 其他业务函数
```

## 6. 错误处理策略

### 6.1 输入验证
- 在入口函数中验证`lineage`参数的完整性
- 验证所有必需字段是否存在
- 验证尺寸参数是否为正整数

### 6.2 运行时错误
- 图像解码失败时抛出`RuntimeError`
- 操作执行失败时抛出`RuntimeError`并包含具体操作信息
- 拼接尺寸不匹配时抛出`ValueError`

### 6.3 调试支持
- 当`is_debug=True`时，记录关键处理步骤的日志
- 在调试模式下保留中间结果用于问题排查

## 7. 测试策略

### 7.1 核心算法测试（src/core/operation/）
- **单个操作测试**: 测试每个RIB原子操作的正确性
- **操作序列测试**: 测试组合操作如`("resize_horizontal_2x", "left")`
- **边界条件**: 测试各种尺寸、格式、操作组合

### 7.2 业务逻辑测试（src/processing/）
- **端到端测试**: 使用PRD示例数据验证完整流程
- **业务场景测试**: 验证各种血缘配置的处理正确性

## 8. 实施状态

✅ **已完成实现并验证**
- **核心算法层**: `src/core/operation/image_operation.py` - 19/19 测试通过
- **业务逻辑层**: `src/processing/image_stiching.py` - 19/19 测试通过
- **完整集成**: 端到端功能验证成功

## 9. 风险与注意事项

### 9.1 关键风险点
- **操作序列处理**: 确保空操作和复杂组合操作的正确处理
- **尺寸计算**: 奇数宽度等边界情况的处理
- **内存管理**: 大图像处理的内存占用控制

### 9.2 缓解措施
- 充分的单元测试覆盖各种操作组合
- 明确的错误处理和参数验证
- 调试模式下的详细日志支持问题排查