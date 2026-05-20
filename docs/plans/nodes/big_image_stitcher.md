# 大图拼接节点（Node3）实施文档

## 1. 定位

Node3 `big_image_stitcher` 属于节点层（`src.nodes`），负责将 `BigImage` 中已固化的 `ImageLineage` 血缘信息转化为实际大图。

- **输入**：`BigImage`（含 `lineage` 字段，已由 pipeline 在调用前挂载完整的 RIB/主沟/装饰方案）
- **输出**：`BigImage`（原地更新 `image_base64` 和 `lineage` 的 `after_image` 字段）
- **核心调用**：`src.processing.image_stiching.generate_large_image_from_lineage()`
- **不消费 RuleConfig**：Node3 不读取 `rules_config`，只执行 lineage 中已固化的拼接方案

获取 `ImageLineage`、更新 `image_base64` 和 `lineage.after_image` 都是 node 层自身的职责。

当前代码是占位实现（`src/nodes/big_image_stitcher.py`），抛出 `NotImplementedError`。

相关文件：
- 节点占位代码：`src/nodes/big_image_stitcher.py`
- 处理层实现：`src/processing/image_stiching.py`
- 处理层文档：`docs/guide/processing/image_stiching.md`
- 节点设计文档：`docs/plans/rules/nodes_design.md`（Section 10, Node3）
- 集成测试：`tests/integrations/test_large_image_stitching.py`
- 单元测试占位：`tests/unittests/nodes/test_big_image_stitcher.py`

---

## 2. 函数签名

```python
def stitch_big_image(
    big_image: BigImage,
    is_debug: bool = False,
) -> BigImage:
    ...
```

- `big_image`：输入/输出对象，要求 `big_image.lineage` 已被 pipeline 挂载。
- `is_debug`：调试模式，透传给 `generate_large_image_from_lineage`，默认 `False`。
- 返回值：同一个 `BigImage` 对象引用，原地更新了 `image_base64` 和 `lineage`。

> 当前占位签名为 `stitch_big_image(input_data: Any, rules_config: Any | None = None) -> Any`，需要改为强类型版本。

---

## 3. 实现流程

### 3.1 整体步骤

```
stitch_big_image(big_image, is_debug)
  │
  ├─ 1. 输入校验
  │     - big_image 不允许为 None
  │     - big_image.lineage 不能为 None
  │     - big_image.lineage.stitching_scheme 不能为 None
  │
  ├─ 2. 提取 ImageLineage
  │     - lineage = big_image.lineage
  │
  ├─ 3. 调用处理层
  │     - generate_large_image_from_lineage(lineage, is_debug=is_debug)
  │     - 返回 (updated_lineage, base64_large_image)
  │
  ├─ 4. 写回 BigImage
  │     - big_image.image_base64 = base64_large_image
  │     - big_image.lineage = updated_lineage
  │
  └─ 5. 返回
        - return big_image
```

### 3.2 获取 ImageLineage

Node3 直接从输入 `BigImage.lineage` 中获取。pipeline 调用 Node3 之前负责将 Node2 生成的 `ImageLineage` 挂载到 `BigImage.lineage` 上。

```python
lineage = big_image.lineage
```

### 3.3 调用处理层

```python
from src.processing.image_stiching import generate_large_image_from_lineage

updated_lineage, large_image_base64 = generate_large_image_from_lineage(
    lineage,
    is_debug=is_debug,
)
```

`generate_large_image_from_lineage` 的处理流程（参见 `docs/guide/processing/image_stiching.md`）：

```
1. RIB 预处理    → _process_rib_images（解码 → 操作序列 → 纵向重复 → resize → 编码）
2. 主沟预处理     → _process_main_groove（解码 → resize → 编码）
3. 装饰预处理     → _process_decoration（解码 → resize → 透明度 → 编码）
4. 参数验证       → _validate_parameters
5. 构建拼接序列   → _build_concatenation_sequence（RIB ↔ 主沟 交替排列）
6. 横向拼接       → horizontal_concatenate (core)
7. 后处理（可选） → _apply_resize_as_first_rib（仅 continuity_0 方案）
8. 装饰覆盖       → overlay_decoration (core)
9. 编码输出       → ndarray_to_base64 (utils)
```

### 3.4 写回 BigImage

处理层返回的 `updated_lineage`（`after_image` 已填充）和 `large_image_base64` 直接写回输入对象的对应字段：

```python
big_image.image_base64 = large_image_base64
big_image.lineage = updated_lineage
```

注意：
- 输入 `BigImage` 进入 Node3 时，`image_base64` 可能是占位值；Node3 负责将其替换为生成的拼接大图。
- `updated_lineage` 中每个 RIB/主沟/装饰的 `after_image` 已被处理层填充。写回后，调用方可通过 `big_image.lineage.stitching_scheme.ribs_scheme_implementation[*].after_image` 访问中间结果。

---

## 4. 输入校验

```python
from src.common.exceptions import InputDataError

NODE_NAME = "big_image_stitcher"

if big_image is None:
    raise InputDataError(NODE_NAME, "big_image", "big_image is required")
if big_image.lineage is None:
    raise InputDataError(NODE_NAME, "lineage", "big_image.lineage is required")
```

| 检查项 | 条件 | 不满足时行为 |
|--------|------|--------------|
| `big_image` 非空 | `big_image is not None` | `raise InputDataError` |
| `lineage` 非空 | `big_image.lineage is not None` | `raise InputDataError` |
| `stitching_scheme` 非空 | 非 None | 由 `generate_large_image_from_lineage` 内部抛出 `ValueError` |
| RIB 列表非空 | `len(ribs) >= 1` | 由 `generate_large_image_from_lineage` 内部抛出 `ValueError` |

---

## 5. 完整伪代码

```python
"""大图拼接节点（Node3）。

接收 pipeline 传入的 BigImage（已挂载 ImageLineage），
调用处理层执行实际拼接，原地更新 image_base64 和 lineage。
"""

from __future__ import annotations

from src.common.exceptions import InputDataError
from src.models.image_models import BigImage
from src.processing.image_stiching import generate_large_image_from_lineage
from src.utils.logger import get_logger

logger = get_logger(__name__)

NODE_NAME = "big_image_stitcher"


def stitch_big_image(
    big_image: BigImage,
    is_debug: bool = False,
) -> BigImage:
    if big_image is None:
        raise InputDataError(NODE_NAME, "big_image", "big_image is required")
    if big_image.lineage is None:
        raise InputDataError(NODE_NAME, "lineage", "big_image.lineage is required")

    updated_lineage, large_image_base64 = generate_large_image_from_lineage(
        big_image.lineage,
        is_debug=is_debug,
    )

    big_image.image_base64 = large_image_base64
    big_image.lineage = updated_lineage

    return big_image
```

---

## 6. 测试计划

### 6.1 修改现有单元测试

文件：`tests/unittests/nodes/test_big_image_stitcher.py`

当前只验证了占位实现抛出 `NotImplementedError`。实现后需要替换为实际测试。

### 6.2 新增单元测试用例

| 测试函数名 | 验证点 |
|-----------|--------|
| `test_stitch_big_image_success` | 正常拼接：5 RIB + 4 主沟 → image_base64 更新，lineage after_image 填充 |
| `test_big_image_none_raises` | `big_image=None` 抛出 `InputDataError` |
| `test_lineage_none_raises` | `big_image.lineage=None` 抛出 `InputDataError` |
| `test_stitching_scheme_none_raises` | `lineage.stitching_scheme=None` → 底层 `ValueError` 上抛 |
| `test_groove_mismatch_raises` | 主沟数 ≠ RIB数-1 → 底层 `ValueError` 上抛 |
| `test_output_is_same_object` | 返回值是输入对象的同一引用 |
| `test_image_base64_updated` | 输出的 `image_base64` 以 `data:image/` 开头 |
| `test_after_image_filled_on_lineage` | lineage 各组件 after_image 被填充 |

### 6.3 测试数据

可复用 `tests/integrations/test_large_image_stitching.py` 中的 `_build_lineage_with_black_decoration()` 辅助函数来构造测试用的 `ImageLineage`。

构造输入 `BigImage` 时，需要提供最小有效字段（`image_base64` 可以是占位值）：

```python
from src.models.image_models import BigImage, ImageMeta, ImageBiz
from src.models.enums import LevelEnum, ImageModeEnum, ImageFormatEnum

def _make_input_big_image(lineage: ImageLineage) -> BigImage:
    return BigImage(
        image_base64="data:image/png;base64,placeholder",
        meta=ImageMeta(width=1, height=1, channels=3, mode=ImageModeEnum.RGB, format=ImageFormatEnum.PNG, size=0),
        biz=ImageBiz(level=LevelEnum.BIG),
        lineage=lineage,
    )
```

### 6.4 示例测试

```python
def test_stitch_big_image_success():
    lineage = _build_lineage_with_black_decoration()
    big_image = _make_input_big_image(lineage)

    result = stitch_big_image(big_image)

    assert result is big_image
    assert result.image_base64.startswith("data:image/")
    assert result.image_base64 != "data:image/png;base64,placeholder"

    ribs = result.lineage.stitching_scheme.ribs_scheme_implementation
    for rib in ribs:
        assert rib.after_image is not None
```

---

## 7. 修改清单

| 文件 | 修改内容 |
|------|----------|
| `src/nodes/big_image_stitcher.py` | 替换占位函数为完整实现（遵循上述伪代码） |
| `tests/unittests/nodes/test_big_image_stitcher.py` | 替换占位测试为 8 个实际测试用例 |

---

## 8. 依赖关系

```
src.nodes.big_image_stitcher
  │
  ├─ src.processing.image_stiching.generate_large_image_from_lineage
  │    ├─ src.core.operation.image_operation（横向拼接、装饰覆盖）
  │    └─ src.utils.image_utils（编解码、resize）
  │
  ├─ src.models.image_models（BigImage）
  ├─ src.common.exceptions（InputDataError）
  └─ src.utils.logger（日志）
```

---

## 9. 注意事项

1. **Node3 不消费 RuleConfig**：所有拼接参数已由 Node2 固化到 `ImageLineage` 中，Node3 只执行。

2. **处理层不做架构变更**：`src/processing/image_stiching.py` 的功能和接口保持不变。

3. **BigImage 原地更新**：Node3 遵循与其他 node（如 `big_image_evaluator`）相同的模式 —— 接收对象引用，原地修改后返回同一引用，不创建新对象。

4. **pipeline 职责**：pipeline 在调用 Node3 前负责将 Node2 输出的 `ImageLineage` 挂载到 `BigImage.lineage`。Node3 不主动构造 lineage。

5. **输入 BigImage 的 image_base64**：进入 Node3 前，`image_base64` 可以是任意合法的占位值（满足 `data:image/` 前缀即可）。Node3 会将其完全替换为拼接结果。

6. **异常传播**：Node3 不捕获处理层的异常（`ValueError`、`cv2.error` 等），由上层 pipeline 决定如何处理。这与 Node1/Node4 通过 `TireStruct.flag/err_msg` 包装异常的方式不同 —— Node3 的接口更简洁，不需要 `flag/err_msg` 中间状态。
