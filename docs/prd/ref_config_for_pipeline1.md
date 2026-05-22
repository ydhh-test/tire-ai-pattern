# 需求文档：pipeline1 参考配置

> 版本: v2.0
> 状态: 草稿

---

## 1. 背景与目标

### 1.1 背景

`pipeline1`（小图生成大图管线）通过 `TireStruct` 接收输入。当前缺少一组结构化的参考配置，导致：

- **e2e 测试**每个用例手写 `rules_config` + 构造 `SmallImage`，重复代码多
- **外部调用方**没有一目了然的示例，不清楚要传哪些字段、字段格式是什么

### 1.2 目标

在 `example/ref_configs/` 下提供 **11 个参考配置 Python 模块**，每个模块同时满足两个使用场景：

| 场景 | 使用方式 |
|---|---|
| 用户参考 & 修改参数 | 查看/编辑 `example/ref_configs/` 下的 `.py` 文件 |
| 测试（CI / 本地验证） | 导入 `tests.datasets.ref_configs` 中的 `cfg_xxx` 模块（版本受控，不被用户修改影响） |

### 1.3 核心理念：Python dict，表达式为值

```
用户编辑 CONFIG dict ──→ build_tire_struct(CONFIG) ──→ TireStruct 实例
     ↑ 可读可改，值可以是函数调用                               ↑ 供程序消费
```

- **`CONFIG`** 是 Python dict。与 JSON dict 最本质的区别：**值可以是函数调用**。例如 `load_image_to_base64(Path("img.png"))` 在 Python 定义时就求值为 base64 字符串，用户可以写函数调用，也可以直接填 base64 字面量
- **`tire_struct`** 由共享 builder (`src/config/_builder.py`) 从 `CONFIG` 自动构建，builder 拿到的是**已求值后的结果**（base64 字符串、数字等），不需要处理文件路径
- 用户修改 `CONFIG` 后，重新调用 `build_tire_struct(CONFIG)` 即可获得新的 `TireStruct`

### 1.4 非目标

- 不设计 JSON/YAML 配置文件格式（值只能是字面量，丧失 Python 表达力）
- 不修改 pipeline1 的任何执行逻辑

---

## 2. 模块格式约定

每个参考配置文件必须遵守以下结构：

```python
"""
参考配置 X.X：<一行描述>
方案: <symmetry_name> [+ <continuity_name>]
RIB数量: N
"""

from pathlib import Path
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

# ============================================================
# 【用户编辑区】修改此字典即可自定义配置
#   所有字符串枚举优先使用 src.models.enums 中的枚举值：
#     region           → RegionEnum.SIDE / RegionEnum.CENTER
#     连续性模式        → StitchingSchemeName.CONTINUITY_0 等
#     装饰位置          → DecorationPositionEnum.LEFT / DecorationPositionEnum.RIGHT
#   - small_images:   每张小图的 image_base64 与 region
#                     可以用 load_image_to_base64(Path(...)) 从文件加载
#                     也可以直接填 "data:image/png;base64,iVBOR..." 字符串
#   - big_image:      默认 None，builder 自动创建占位 BigImage
#   - rules_config:   规则配置列表，"rule" 字段指定规则名
#   - scheme_rank:    方案排名，1=取最优方案
#   - is_debug:       可选，默认 False
# ============================================================
CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {
            "image_base64": load_image_to_base64(
                Path("tests/datasets/stitching/rib1.png"), with_prefix=True
            ),
            "region": RegionEnum.SIDE,
        },
        # ...
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        # ...
    ],
}

# ============================================================
# 【自动生成区】由 builder 根据 CONFIG 自动构建，无需手动编辑
# ============================================================
from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 2.1 两个出口

| 导出名 | 类型 | 用途 |
|---|---|---|
| `CONFIG` | `dict` | 用户阅读和编辑的源数据 |
| `tire_struct` | `TireStruct` | 直接传给 `run_pipeline1()` 的程序对象 |

使用示例：

```python
# 方式一：测试直接用（不可被用户修改的版本受控副本）
from tests.datasets.ref_configs import cfg_5rib_sym0_no_cont
from src.piplines.pipline1 import run_pipeline1
run_pipeline1(cfg_5rib_sym0_no_cont.tire_struct)

# 方式二：用户参考后修改（基于 example/ 下的展示副本）
from example.ref_configs import cfg_5rib_sym0_no_cont
import copy
CONFIG = copy.deepcopy(cfg_5rib_sym0_no_cont.CONFIG)
CONFIG["scheme_rank"] = 2                # 换一个方案
CONFIG["small_images"][0]["image_base64"] = load_image_to_base64(
    Path("/data/my_rib1.png"), with_prefix=True
)                                              # 换图片
from src.config._builder import build_tire_struct
my_struct = build_tire_struct(CONFIG)
run_pipeline1(my_struct)

> **两份配置的关系**：
> - `example/ref_configs/` — 展示用，用户可以随意修改以实验
> - `tests/datasets/ref_configs/` — 测试用，版本受控，每次新提交都会被测试到，防止改坏
> - 两份内容相同，但互不影响
```

---

## 3. `CONFIG` dict 字段说明

### 3.1 顶层字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `small_images` | `list[dict]` | 是 | — | 小图列表，每个元素见 3.2 |
| `rules_config` | `list[dict]` | 是 | — | 规则配置列表，每个元素见 3.3 |
| `scheme_rank` | `int` | 是 | — | 方案排名，1=最优方案 |
| `big_image` | `dict \| None` | 否 | `None` | `None`=builder 自动创建占位 BigImage；见 3.4 |
| `is_debug` | `bool` | 否 | `False` | 调试开关 |

### 3.2 `small_images` 元素

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `image_base64` | `str` | 是 | 图片的 base64 编码（含 `data:image/...;base64,` 前缀） |
| `region` | `RegionEnum` | 是 | `RegionEnum.SIDE` 或 `RegionEnum.CENTER` |

> **如何填写 `image_base64`**：
> ```python
> # 方式一：从文件加载（推荐）
> "image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True)
>
> # 方式二：直接填 base64 字符串
> "image_base64": "data:image/png;base64,iVBORw0KGgo..."
> ```
> Python dict 在定义时就会执行函数调用，所以 builder 拿到的始终是已求值的 base64 字符串。

### 3.3 `rules_config` 元素

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `rule` | `str` | 是 | 规则名：`"rule1"`, `"rule2"`, `"rule100"` 等。支持数字简写 `1`, `100` |
| `description` | `str` | 否 | 规则描述（rule1/2/3/100/101/102 有默认值，可省略） |
| `max_score` | `int` | 否 | 最大得分 |
| *(其他)* | — | — | 各规则的特有字段，如 `rib_sizes`、`groove_sizes`、`continuity_mode_list` 等 |

示例：

```python
# 简单规则
{"rule": "rule1", "description": "rib无对称", "max_score": 10}

# 纯配置规则（含嵌套列表）
{
    "rule": "rule100",
    "rib_number": 5,
    "rib_sizes": [
        {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
        # ...
    ],
}

# 连续性规则（continuity_mode_list 使用 StitchingSchemeName 枚举）
{
    "rule": "rule12",
    "max_score": 6,
    "description": "两个RIB间横向钢片及横沟连续性占比是否满足要求",
    "continuity_ratio_upper": 0.7,
    "continuity_ratio_lower": 0.6,
    "continuity_mode_list": [StitchingSchemeName.CONTINUITY_0, StitchingSchemeName.CONTINUITY_1],
},
```

### 3.4 `big_image` 字段

| 值 | builder 行为 |
|---|---|
| `None` 或缺失 | 创建标准占位 BigImage（用于 pipeline1 输入） |
| `{"image_base64": load_image_to_base64(...)}` | 加载真实大图（用于 pipeline2/3/4 输入） |
| `{"image_base64": "data:image/png;base64,..."}` | 直接使用 base64 字符串 |

> **注意**：pipeline1 的大图是**输出**，不是输入，因此参考配置中 `big_image` 均设为 `None`。

### 3.5 新增枚举：`DecorationPositionEnum`

装饰位置目前使用裸 `str`（`"left"` / `"right"`），需新增枚举以保持一致：

```python
# src/models/enums.py 新增

class DecorationPositionEnum(str, Enum):
    """装饰位置枚举"""
    LEFT = "left"    # 左侧装饰
    RIGHT = "right"  # 右侧装饰
```

> **关联改动**：`rule_models.py` 中 `DecorationItem.position` 字段类型需同步从 `str` 改为 `DecorationPositionEnum`。

---

## 4. `src/config/_builder.py` 职责

这是一个共享模块，供所有参考配置文件调用。职责是**从 CONFIG dict 构建 TireStruct**。

### 4.1 核心函数

```python
def build_tire_struct(config: dict) -> TireStruct:
```

### 4.2 处理流程

```
1. 解析 small_images:
   image_base64 ──→ base64_to_ndarray() ──→ 推断宽/高/通道/格式 ──→ SmallImage
   （注意：image_base64 已是字符串，因为 CONFIG 定义时 load_image_to_base64() 已求值）

2. 解析 rules_config:
   {"rule": "rule1", ...} ──→ get_rule("rule1") ──→ Rule1Config(**rest)

3. 解析 big_image:
   None ──→ 创建占位 BigImage
   {"image_base64": "..."} ──→ 构造 BigImage（image_base64 已在定义时求值）

4. 组装 TireStruct:
   TireStruct(
       small_images=[...],
       big_image=...,    # 占位或真实
       rules_config=[...],
       scheme_rank=config["scheme_rank"],
       is_debug=config.get("is_debug", False),
   )
```

### 4.3 与现有代码的关系

`_builder.py` 本质上是将 `tests/integrations/test_pipline1.py` 中的 `tire_struct_from_input()`、`_small_image_from_input()`、`_rule_config_from_input()` 等函数提取为独立模块，做以下整理：

- `big_image` 支持 `None` → 自动创建占位 BigImage
- 合并为一个公开函数 `build_tire_struct()`

---

## 5. 11 个参考配置详表

### 5.1 总览矩阵

| # | 文件名 | RIB | 对称规则 | 连续性规则 | 连续模式 | 预期方案 |
|---|---|---|---|---|---|---|
| 1.1 | `5rib_sym0_no_cont.py` | 5 | rule1 | — | — | Symmetry0 |
| 1.2 | `5rib_sym1_no_cont.py` | 5 | rule2 | — | — | Symmetry1 |
| 1.3 | `5rib_sym2_no_cont.py` | 5 | rule3 | — | — | Symmetry2 |
| 1.4 | `5rib_sym0_cont1.py` | 5 | rule1 | rule12,16,17 | continuity_1 | Symmetry0 + Continuity1 |
| 1.5 | `5rib_sym1_cont1.py` | 5 | rule2 | rule12,16,17 | continuity_1 | Symmetry1 + Continuity1 |
| 1.6 | `5rib_sym2_cont2.py` | 5 | rule3 | rule12,16,17 | continuity_2 | Symmetry2 + Continuity2 |
| 1.7 | `4rib_sym4_no_cont.py` | 4 | rule1 | — | — | Symmetry4 |
| 1.8 | `4rib_sym4_sym5_no_cont.py` | 4 | rule1, rule2 | — | — | Symmetry4 或 5 |
| 1.9 | `4rib_sym456_no_cont.py` | 4 | rule1,2,3 | — | — | Symmetry4/5/6 |
| 1.10 | `4rib_sym456_cont3.py` | 4 | rule1,2,3 | rule12,16,17 | continuity_3 | Symmetry4/5/6 + Continuity3 |
| 1.11 | `4rib_sym456_cont123_bad.py` | 4 | rule1,2,3 | rule12,16,17 | continuity_1,2,3 | **反例** |

### 5.2 统一默认参数

为保持一致性，所有 5-rib 配置共享同一组尺寸，所有 4-rib 配置共享同一组尺寸。

**5-rib 小图清单**（2 SIDE + 3 CENTER，共 5 张）：

```python
from pathlib import Path
from src.models.enums import RegionEnum
from src.utils.image_utils import load_image_to_base64

"small_images": [
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
],
```

**5-rib RIB 尺寸**（Rule100）：

| RIB | num_pitchs | rib_width | rib_height |
|---|---|---|---|
| rib1 | 5 | 400 | 640 |
| rib2 | 5 | 200 | 640 |
| rib3 | 5 | 200 | 640 |
| rib4 | 5 | 200 | 640 |
| rib5 | 5 | 400 | 640 |

**5-rib 主沟**（Rule101）：4 个，各 `groove_width=20`, `groove_height=640`

---

**4-rib 小图清单**（2 SIDE + 2 CENTER，共 4 张）：

```python
"small_images": [
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
    {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.SIDE},
],
```

**4-rib RIB 尺寸**（Rule100）：

| RIB | num_pitchs | rib_width | rib_height |
|---|---|---|---|
| rib1 | 5 | 400 | 640 |
| rib2 | 5 | 200 | 640 |
| rib3 | 5 | 200 | 640 |
| rib4 | 5 | 400 | 640 |

**4-rib 主沟**（Rule101）：3 个，各 `groove_width=20`, `groove_height=640`

---

**所有配置共享装饰**（Rule102）：

```python
from src.models.enums import DecorationPositionEnum

"decorations": [
    {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
],
```

---

### 5.3 各配置的 rules_config 差异

#### 基础 rules_config 骨架（5-rib 无连续性变体）

```python
[
    # === 对称性规则（按需选择 1 个或多个）===
    {"rule": "rule1", "description": "rib无对称", "max_score": 10},

    # === 尺寸规则（必选）===
    {"rule": "rule100", "rib_number": 5, "rib_sizes": [...5个RIB...]},
    {"rule": "rule101", "groove_sizes": [...4个主沟...]},
    {"rule": "rule102", "decorations": [...1个装饰...]},
]
```

#### 连续性规则组（有连续性时追加）

```python
[
    # === 对称性规则 ===
    {"rule": "rule2", ...},

    # === 连续性规则（这三个规则共同决定可选连续性模式）===
    # 注意：continuity_mode_list 使用 StitchingSchemeName 枚举值
    {
        "rule": "rule12",
        "max_score": 6,
        "description": "两个RIB间横向钢片及横沟连续性占比是否满足要求",
        "continuity_ratio_upper": 0.7,
        "continuity_ratio_lower": 0.6,
        "continuity_mode_list": [StitchingSchemeName.CONTINUITY_0, StitchingSchemeName.CONTINUITY_1],
    },
    {
        "rule": "rule16",
        "max_score": 4,
        "description": "中心RIB上的横沟或横向钢片可任意组合连续性",
        "continuity_mode_list": [StitchingSchemeName.CONTINUITY_0, StitchingSchemeName.CONTINUITY_1],
    },
    {
        "rule": "rule17",
        "max_score": 6,
        "description": "边缘RIB上的横沟或横向钢片可任意组合连续性",
        "continuity_mode_list": [StitchingSchemeName.CONTINUITY_0],
    },

    # === 尺寸规则 ===
    {"rule": "rule100", "rib_number": 5, ...},
    {"rule": "rule101", ...},
    {"rule": "rule102", ...},
]
```

#### 各配置的差值表

| 配置 | 对称规则 | continuity_mode_list (StitchingSchemeName) | rib_number |
|---|---|---|---|---|
| 1.1 | rule1 | — | 5 |
| 1.2 | rule2 | — | 5 |
| 1.3 | rule3 | — | 5 |
| 1.4 | rule1 | `[CONTINUITY_0, CONTINUITY_1]` | 5 |
| 1.5 | rule2 | `[CONTINUITY_0, CONTINUITY_1]` | 5 |
| 1.6 | rule3 | `[CONTINUITY_0, CONTINUITY_2]` | 5 |
| 1.7 | rule1 | — | 4 |
| 1.8 | rule1, rule2 | — | 4 |
| 1.9 | rule1, rule2, rule3 | — | 4 |
| 1.10 | rule1, rule2, rule3 | `[CONTINUITY_3]` | 4 |
| 1.11 | rule1, rule2, rule3 | `[CONTINUITY_1, CONTINUITY_2, CONTINUITY_3]` (反例) | 4 |

### 5.4 反例 1.11 说明

`4rib_sym456_cont123_bad.py` 的 `continuity_mode_list` 包含了 `"continuity_1"` 和 `"continuity_2"`。

- `continuity_1` / `continuity_2` 是 **5-rib 的连续性模板**（`Continuity1` / `Continuity2` 的 `rib_number=5`）
- 当 `Rule100Config.rib_number=4` 时，这些模板的 rib_number 不匹配，会被系统**静默忽略**
- 实际可用的连续性只有 `continuity_3`

**反面教学意义**：
- 配置不兼容的模式不会导致崩溃，但会产生"配置了但没生效"的困惑
- 用户应确保 `continuity_mode_list` 中的模式与 `rib_number` 匹配
- 可作为 e2e 测试用例验证系统的鲁棒降级行为

---

## 6. 文件清单

### 6.1 新增文件

```
example/ref_configs/                         # 展示用副本，用户可随意修改
├── __init__.py
├── 5rib_sym0_no_cont.py
├── 5rib_sym1_no_cont.py
├── 5rib_sym2_no_cont.py
├── 5rib_sym0_cont1.py
├── 5rib_sym1_cont1.py
├── 5rib_sym2_cont2.py
├── 4rib_sym4_no_cont.py
├── 4rib_sym4_sym5_no_cont.py
├── 4rib_sym456_no_cont.py
├── 4rib_sym456_cont3.py
└── 4rib_sym456_cont123_bad.py

tests/datasets/ref_configs/                  # 测试用副本，版本受控，每次提交都被测试
├── __init__.py
├── 5rib_sym0_no_cont.py
├── ... (同上 11 个文件)

src/config/
└── _builder.py                              # 共享 dict→TireStruct 构建器
```

### 6.2 修改现有文件

| 文件 | 改动 |
|---|---|
| `src/models/enums.py` | 新增 `DecorationPositionEnum` |
| `src/models/rule_models.py` | `DecorationItem.position` 类型从 `str` 改为 `DecorationPositionEnum` |

---

## 7. 验收标准

### 7.1 功能验收

| # | 验收项 | 验证方式 |
|---|---|---|
| 1 | 每个配置文件的 `tire_struct` 可成功构造，不抛异常 | 在测试中 `from tests.datasets.ref_configs import cfg_xxx; cfg_xxx.tire_struct` |
| 2 | `tire_struct` 可直接传给 `run_pipeline1()` 运行 | 1.1-1.10 通过 pipeline1 完整执行 |
| 3 | 1.11 不导致 pipeline1 崩溃 | 运行不抛异常，continuity_1/2 被静默忽略 |
| 4 | 预期方案名与实际 pipeline1 输出一致 | 检查 `tire_struct.big_image.lineage.stitching_scheme.stitching_scheme_abstract.name` |
| 5 | `CONFIG` 是 dict，值只包含基础类型、枚举值和函数调用结果，不含 Pydantic 模型对象 | `isinstance(CONFIG, dict)` 为 True，遍历所有叶子节点确认无 Pydantic 实例 |
| 6 | 用户修改 `CONFIG` 后重新调用 `build_tire_struct(CONFIG)` 可获得更新后的 `TireStruct` | 修改 image_base64 源 / rib_width，验证 tire_struct 反映变更 |

### 7.2 文档验收

| # | 验收项 |
|---|---|
| 1 | 每个配置文件顶部有准确的 docstring（方案名、RIB 数） |
| 2 | `CONFIG` 上方有中文注释说明各字段含义 |
| 3 | 自动生成区用注释分隔（`# ==========【自动生成区】==========`） |
| 4 | 反例文件顶部有"反例"字样和说明 |

---

## 8. 附录

### 8.1 对称性模板匹配速查

对称性由规则激活，每个模板通过 `matching_rule_names` 绑定：

| 方案名 | 模板类 | RIB | 激活规则 | 描述 |
|---|---|---|---|---|
| symmetry_0 | Symmetry0 | 5 | rule1 | 无对称 |
| symmetry_1 | Symmetry1 | 5 | rule2 | 中心旋转180° |
| symmetry_2 | Symmetry2 | 5 | rule3 | 左右镜像 |
| symmetry_4 | Symmetry4 | 4 | rule1 | 无对称 |
| symmetry_5 | Symmetry5 | 4 | rule2 | 中心旋转180° |
| symmetry_6 | Symmetry6 | 4 | rule3 | 左右镜像 |

> 注：rule1 同时激活 symmetry_0 和 symmetry_4，实际由 `Rule100Config.rib_number` 决定匹配哪个。rule2/rule3 同理。

### 8.2 连续性模板匹配速查

| 方案名 | 模板类 | RIB | continuity_mode_list 值 (StitchingSchemeName) |
|---|---|---|---|
| continuity_0 | Continuity0 | 5 | `CONTINUITY_0` |
| continuity_1 | Continuity1 | 5 | `CONTINUITY_1` |
| continuity_2 | Continuity2 | 5 | `CONTINUITY_2` |
| continuity_3 | Continuity3 | 4 | `CONTINUITY_3` |

### 8.3 完整的规则配置字段速查

所有可在 `rules_config` 元素中使用的规则及其特有字段：

| 规则 | 用途 | 特有字段 |
|---|---|---|
| rule1 | 无对称 | `description`, `max_score` |
| rule2 | 中心对称 | `description`, `max_score` |
| rule3 | 左右对称 | `description`, `max_score` |
| rule12 | 连续性占比 | `max_score`, `continuity_ratio_upper`, `continuity_ratio_lower`, `continuity_mode_list` |
| rule16 | 中心RIB连续性 | `max_score`, `continuity_mode_list` |
| rule17 | 边缘RIB连续性 | `max_score`, `continuity_mode_list` |
| rule100 | RIB尺寸 | `rib_number`, `rib_sizes` |
| rule101 | 主沟尺寸 | `groove_sizes` |
| rule102 | 装饰边框 | `decorations` |

### 8.4 CONFIG 中使用的枚举速查

所有 CONFIG 文件统一从 `src.models.enums` 导入枚举：

```python
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
```

| 枚举 | CONFIG 中的使用位置 | 有效值 |
|---|---|---|
| `RegionEnum` | `small_images[].region` | `SIDE`, `CENTER` |
| `StitchingSchemeName` | `rules_config` 中 `continuity_mode_list` 的子元素 | `CONTINUITY_0` ~ `CONTINUITY_3`, `SYMMETRY_0` ~ `SYMMETRY_6` |
| `DecorationPositionEnum` | `rules_config` 中 `decorations[].position` | `LEFT`, `RIGHT` |

> `StitchingSchemeName` 继承 `str, Enum`，因此 `StitchingSchemeName.CONTINUITY_0` 的字符串值为 `"continuity_0"`，与 Pydantic 模型中 `List[str]` 类型兼容。

---

## 9. 待确认事项

1. **反例 1.11 的 e2e 测试**：是否需要独立的测试用例来验证"连续性模式被静默忽略"的降级行为？
2. **`__init__.py` 聚合导出**：是否需要在 `src/config/__init__.py` 中统一 `import` 所有参考配置，方便一次性导入？
