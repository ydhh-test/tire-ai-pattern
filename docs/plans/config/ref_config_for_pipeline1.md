# 实施文档：pipeline1 参考配置

> PRD: [docs/prd/ref_config_for_pipeline1.md](../../prd/ref_config_for_pipeline1.md)
> 状态: 实施中

---

## 1. 实施步骤总览

| 步骤 | 内容 | 涉及文件 | 依赖 |
|---|---|---|---|
| S1 | 新增 `DecorationPositionEnum` | `src/models/enums.py` | — |
| S2 | 同步 `DecorationItem.position` 类型 | `src/models/rule_models.py` | S1 |
| S3 | 创建共享 builder `_builder.py` | `src/config/_builder.py` | S2 |
| S4 | 创建 11 个参考配置文件 | `src/config/ref_*.py` (11个) | S3 |

---

## 2. S1：新增 `DecorationPositionEnum`

**文件**：`src/models/enums.py`

在 `ImageFormatEnum` 之后、`StitchingSchemeName` 之前插入：

```python
class DecorationPositionEnum(str, Enum):
    """装饰位置枚举"""
    LEFT = "left"    # 左侧装饰
    RIGHT = "right"  # 右侧装饰
```

**位置标注**（插入到第 50 行附近，`ImageFormatEnum` 类定义之后）：

```
class ImageFormatEnum(str, Enum):
    ...


class DecorationPositionEnum(str, Enum):  # <-- 新增
    ...


class StitchingSchemeName(str, Enum):
    ...
```

---

## 3. S2：同步 `DecorationItem.position` 类型

**文件**：`src/models/rule_models.py`

### 3.1 修改 import

在文件顶部 `from .enums import ...` 行中追加 `DecorationPositionEnum`：

```python
# 修改前
from .enums import RuleTypeEnum

# 修改后
from .enums import RuleTypeEnum, DecorationPositionEnum
```

### 3.2 修改 `DecorationItem.position` 类型

```python
# 修改前
class DecorationItem(BaseModel):
    """单个装饰的尺寸与透明度配置"""
    position: str = Field(description="装饰位置：left / right")

# 修改后
class DecorationItem(BaseModel):
    """单个装饰的尺寸与透明度配置"""
    position: DecorationPositionEnum = Field(description="装饰位置：left / right")
```

**验证**：`python -c "from src.models.rule_models import DecorationItem; print(DecorationItem.__fields__)"` 不报错。

---

## 4. S3：创建 `src/config/_builder.py`

### 4.1 模块职责

从 `CONFIG` dict 构建 `TireStruct`。对外暴露单一函数 `build_tire_struct()`。

### 4.2 完整代码

```python
"""共享 dict→TireStruct 构建器，供所有参考配置文件调用。"""

from __future__ import annotations

import base64
from typing import Any

from src.common.exceptions import InputTypeError
from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum
from src.models.image_models import BigImage, ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import BaseRuleConfig
from src.models.tire_struct import TireStruct
from src.rules.registry import get_rule
from src.utils.image_utils import base64_to_ndarray


# ============================================================
# 公开 API
# ============================================================

def build_tire_struct(config: dict) -> TireStruct:
    """从 CONFIG dict 构建 TireStruct。

    处理流程：
    1. small_images 中 image_base64 → SmallImage
    2. rules_config 中 dict → RuleConfig 实例
    3. big_image: None → 占位 BigImage，dict → 真实 BigImage
    4. 组装 TireStruct
    """
    return TireStruct(
        big_image=_build_big_image(config.get("big_image")),
        small_images=[
            _build_small_image(item)
            for item in config["small_images"]
        ],
        rules_config=[
            _build_rule_config(item)
            for item in config["rules_config"]
        ],
        scheme_rank=config["scheme_rank"],
        is_debug=config.get("is_debug", False),
    )


# ============================================================
# 内部构建函数
# ============================================================

def _build_small_image(raw: dict[str, Any]) -> SmallImage:
    """从 single small_images 元素构建 SmallImage。"""
    image_base64 = raw["image_base64"]
    image = base64_to_ndarray(image_base64)
    height, width = image.shape[:2]
    channels = 1 if len(image.shape) == 2 else image.shape[2]

    return SmallImage(
        image_base64=image_base64,
        meta=ImageMeta(
            width=width,
            height=height,
            channels=channels,
            mode=_channels_to_mode(channels),
            format=_base64_to_format(image_base64),
            size=_base64_payload_size(image_base64),
        ),
        biz=ImageBiz(
            level=LevelEnum.SMALL,
            region=RegionEnum(raw["region"]),
        ),
    )


def _build_rule_config(raw: dict[str, Any]) -> BaseRuleConfig:
    """从 single rules_config 元素构建 RuleConfig 实例。"""
    rule_name = _normalize_rule_name(raw["rule"])
    config_class = get_rule(rule_name)
    if config_class is None:
        raise ValueError(f"unsupported rule config: {raw['rule']}")

    config_data = {
        key: value
        for key, value in raw.items()
        if key != "rule"
    }
    return config_class(**config_data)


def _build_big_image(raw: dict | None) -> BigImage:
    """从 big_image 元素构建 BigImage。

    None → 占位 BigImage
    dict → 真实 BigImage（含 image_base64）
    """
    if raw is None:
        return _placeholder_big_image()
    return BigImage(
        image_base64=raw["image_base64"],
        meta=ImageMeta(
            width=1, height=1, channels=3,
            mode=ImageModeEnum.RGB, format=ImageFormatEnum.PNG, size=0,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, region=RegionEnum.CENTER),
    )


def _placeholder_big_image() -> BigImage:
    """pipeline1 输入用占位 BigImage。"""
    return BigImage(
        image_base64="data:image/png;base64,",
        meta=ImageMeta(
            width=1, height=1, channels=1,
            mode=ImageModeEnum.GRAY, format=ImageFormatEnum.PNG, size=0,
        ),
        biz=ImageBiz(level=LevelEnum.BIG, region=RegionEnum.CENTER),
    )


# ============================================================
# 工具函数
# ============================================================

def _normalize_rule_name(rule: str | int) -> str:
    """规则名归一化：支持 "rule1", "1", 1 等格式。"""
    if isinstance(rule, int):
        return f"rule{rule}"
    if isinstance(rule, str):
        rule = rule.lower()
        return rule if rule.startswith("rule") else f"rule{rule}"
    raise InputTypeError(
        function="_normalize_rule_name",
        param="rule",
        expected_type="str or int",
        actual_type=type(rule).__name__,
    )


def _channels_to_mode(channels: int) -> ImageModeEnum:
    if channels == 1:
        return ImageModeEnum.GRAY
    if channels == 3:
        return ImageModeEnum.RGB
    return ImageModeEnum.RGBA


def _base64_to_format(image_base64: str) -> ImageFormatEnum:
    prefix = image_base64.split(",", 1)[0].lower()
    if "jpeg" in prefix or "jpg" in prefix:
        return ImageFormatEnum.JPG
    return ImageFormatEnum.PNG


def _base64_payload_size(image_base64: str) -> int:
    payload = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
    return len(base64.b64decode(payload))
```

### 4.3 与现有测试代码的关系

本模块将 `tests/integrations/test_pipline1.py` 中的以下函数提取并整理：

| 原函数（test 中） | 对应新函数 | 变化 |
|---|---|---|
| `tire_struct_from_input()` | `build_tire_struct()` | 支持 `big_image=None` 自动占位 |
| `_small_image_from_input()` | `_build_small_image()` | 无变化 |
| `_rule_config_from_input()` | `_build_rule_config()` | 无变化 |
| `_normalize_rule_name()` | `_normalize_rule_name()` | 无变化 |
| `_image_mode_from_channels()` | `_channels_to_mode()` | 重命名更简洁 |
| `_image_format_from_base64()` | `_base64_to_format()` | 重命名 |
| `_image_payload_size()` | `_base64_payload_size()` | 重命名 |
| — | `_build_big_image()` | 新增 |
| — | `_placeholder_big_image()` | 新增 |

---

## 5. S4：创建 11 个参考配置文件

每个配置文件都是独立完整的 Python 模块，不含别名、不引用外部共享块。
CONFIG dict 内每个值都是字面量或完整的函数调用，用户可以直接看懂和修改。

### 5.1: `src/config/ref_5rib_sym0_no_cont.py`

```python
"""
参考配置 1.1：5个RIB，无对称，无连续性
方案: symmetry_0
RIB数量: 5
对称性候选: [symmetry_0]
连续性候选: 无
"""

from pathlib import Path
from src.models.enums import RegionEnum, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        {
            "rule": "rule100", "rib_number": 5,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib5", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.2: `src/config/ref_5rib_sym1_no_cont.py`

```python
"""
参考配置 1.2：5个RIB，中心旋转180°对称，无连续性
方案: symmetry_1
RIB数量: 5
对称性候选: [symmetry_1]
连续性候选: 无
"""

from pathlib import Path
from src.models.enums import RegionEnum, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule2", "description": "rib中心对称", "max_score": 10},
        {
            "rule": "rule100", "rib_number": 5,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib5", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.3: `src/config/ref_5rib_sym2_no_cont.py`

```python
"""
参考配置 1.3：5个RIB，左右镜像对称，无连续性
方案: symmetry_2
RIB数量: 5
对称性候选: [symmetry_2]
连续性候选: 无
"""

from pathlib import Path
from src.models.enums import RegionEnum, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule3", "description": "rib左右对称", "max_score": 10},
        {
            "rule": "rule100", "rib_number": 5,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib5", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.4: `src/config/ref_5rib_sym0_cont1.py`

```python
"""
参考配置 1.4：5个RIB，无对称，连续性1 (RIB2-RIB3连续)
方案: symmetry_0 + continuity_1
RIB数量: 5
对称性候选: [symmetry_0]
连续性候选: [continuity_0, continuity_1]
"""

from pathlib import Path
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
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
        {
            "rule": "rule100", "rib_number": 5,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib5", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.5: `src/config/ref_5rib_sym1_cont1.py`

```python
"""
参考配置 1.5：5个RIB，中心旋转180°对称，连续性1 (RIB2-RIB3连续)
方案: symmetry_1 + continuity_1
RIB数量: 5
对称性候选: [symmetry_1]
连续性候选: [continuity_0, continuity_1]
"""

from pathlib import Path
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule2", "description": "rib中心对称", "max_score": 10},
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
        {
            "rule": "rule100", "rib_number": 5,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib5", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.6: `src/config/ref_5rib_sym2_cont2.py`

```python
"""
参考配置 1.6：5个RIB，左右镜像对称，连续性2 (RIB3-RIB4连续)
方案: symmetry_2 + continuity_2
RIB数量: 5
对称性候选: [symmetry_2]
连续性候选: [continuity_0, continuity_2]
"""

from pathlib import Path
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib5.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule3", "description": "rib左右对称", "max_score": 10},
        {
            "rule": "rule12",
            "max_score": 6,
            "description": "两个RIB间横向钢片及横沟连续性占比是否满足要求",
            "continuity_ratio_upper": 0.7,
            "continuity_ratio_lower": 0.6,
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_0, StitchingSchemeName.CONTINUITY_2],
        },
        {
            "rule": "rule16",
            "max_score": 4,
            "description": "中心RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_0, StitchingSchemeName.CONTINUITY_2],
        },
        {
            "rule": "rule17",
            "max_score": 6,
            "description": "边缘RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_0],
        },
        {
            "rule": "rule100", "rib_number": 5,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib5", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.7: `src/config/ref_4rib_sym4_no_cont.py`

```python
"""
参考配置 1.7：4个RIB，无对称，无连续性
方案: symmetry_4
RIB数量: 4
对称性候选: [symmetry_4]
连续性候选: 无
"""

from pathlib import Path
from src.models.enums import RegionEnum, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        {
            "rule": "rule100", "rib_number": 4,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.8: `src/config/ref_4rib_sym4_sym5_no_cont.py`

```python
"""
参考配置 1.8：4个RIB，对称性4和5双候选，无连续性
方案: symmetry_4 或 symmetry_5
RIB数量: 4
对称性候选: [symmetry_4, symmetry_5]
连续性候选: 无
"""

from pathlib import Path
from src.models.enums import RegionEnum, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        {"rule": "rule2", "description": "rib中心对称", "max_score": 10},
        {
            "rule": "rule100", "rib_number": 4,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.9: `src/config/ref_4rib_sym456_no_cont.py`

```python
"""
参考配置 1.9：4个RIB，对称性4/5/6三候选，无连续性
方案: symmetry_4 / symmetry_5 / symmetry_6
RIB数量: 4
对称性候选: [symmetry_4, symmetry_5, symmetry_6]
连续性候选: 无
"""

from pathlib import Path
from src.models.enums import RegionEnum, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        {"rule": "rule2", "description": "rib中心对称", "max_score": 10},
        {"rule": "rule3", "description": "rib左右对称", "max_score": 10},
        {
            "rule": "rule100", "rib_number": 4,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.10: `src/config/ref_4rib_sym456_cont3.py`

```python
"""
参考配置 1.10：4个RIB，对称性4/5/6三候选，连续性3 (RIB2-RIB3连续)
方案: symmetry_4/5/6 + continuity_3
RIB数量: 4
对称性候选: [symmetry_4, symmetry_5, symmetry_6]
连续性候选: [continuity_3]
"""

from pathlib import Path
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        {"rule": "rule2", "description": "rib中心对称", "max_score": 10},
        {"rule": "rule3", "description": "rib左右对称", "max_score": 10},
        {
            "rule": "rule12",
            "max_score": 6,
            "description": "两个RIB间横向钢片及横沟连续性占比是否满足要求",
            "continuity_ratio_upper": 0.7,
            "continuity_ratio_lower": 0.6,
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_3],
        },
        {
            "rule": "rule16",
            "max_score": 4,
            "description": "中心RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_3],
        },
        {
            "rule": "rule17",
            "max_score": 6,
            "description": "边缘RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [StitchingSchemeName.CONTINUITY_3],
        },
        {
            "rule": "rule100", "rib_number": 4,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

### 5.11: `src/config/ref_4rib_sym456_cont123_bad.py` (反例)

```python
"""
【反例】参考配置 1.11：4个RIB，对称性4/5/6三候选，连续性1/2/3
方案: symmetry_4/5/6 + continuity_3（实际只有 continuity_3 生效）
RIB数量: 4
对称性候选: [symmetry_4, symmetry_5, symmetry_6]
连续性候选: [continuity_1, continuity_2, continuity_3]

反例说明:
  continuity_1 / continuity_2 是 5-rib 的连续性模板，在 rib_number=4 时
  会在模板匹配阶段被静默忽略。实际生效的只有 continuity_3。
  用户看到的现象：配置了三个连续性模式，但 pipeline1 只产出一个。
"""

from pathlib import Path
from src.models.enums import RegionEnum, StitchingSchemeName, DecorationPositionEnum
from src.utils.image_utils import load_image_to_base64

CONFIG = {
    "scheme_rank": 1,
    "is_debug": False,
    "big_image": None,
    "small_images": [
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib1.png"), with_prefix=True), "region": RegionEnum.SIDE},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib2.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib3.png"), with_prefix=True), "region": RegionEnum.CENTER},
        {"image_base64": load_image_to_base64(Path("tests/datasets/stitching/rib4.png"), with_prefix=True), "region": RegionEnum.SIDE},
    ],
    "rules_config": [
        {"rule": "rule1", "description": "rib无对称", "max_score": 10},
        {"rule": "rule2", "description": "rib中心对称", "max_score": 10},
        {"rule": "rule3", "description": "rib左右对称", "max_score": 10},
        {
            "rule": "rule12",
            "max_score": 6,
            "description": "两个RIB间横向钢片及横沟连续性占比是否满足要求",
            "continuity_ratio_upper": 0.7,
            "continuity_ratio_lower": 0.6,
            "continuity_mode_list": [
                StitchingSchemeName.CONTINUITY_1,  # 5-rib模板，不匹配，将被忽略
                StitchingSchemeName.CONTINUITY_2,  # 5-rib模板，不匹配，将被忽略
                StitchingSchemeName.CONTINUITY_3,  # 唯一生效的
            ],
        },
        {
            "rule": "rule16",
            "max_score": 4,
            "description": "中心RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [
                StitchingSchemeName.CONTINUITY_1,
                StitchingSchemeName.CONTINUITY_2,
                StitchingSchemeName.CONTINUITY_3,
            ],
        },
        {
            "rule": "rule17",
            "max_score": 6,
            "description": "边缘RIB上的横沟或横向钢片可任意组合连续性",
            "continuity_mode_list": [
                StitchingSchemeName.CONTINUITY_1,
                StitchingSchemeName.CONTINUITY_2,
                StitchingSchemeName.CONTINUITY_3,
            ],
        },
        {
            "rule": "rule100", "rib_number": 4,
            "rib_sizes": [
                {"rib_name": "rib1", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
                {"rib_name": "rib2", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib3", "num_pitchs": 5, "rib_width": 200, "rib_height": 640},
                {"rib_name": "rib4", "num_pitchs": 5, "rib_width": 400, "rib_height": 640},
            ],
        },
        {
            "rule": "rule101",
            "groove_sizes": [
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
                {"groove_width": 20, "groove_height": 640},
            ],
        },
        {
            "rule": "rule102",
            "decorations": [
                {"position": DecorationPositionEnum.LEFT, "decoration_width": 300, "decoration_height": 640, "decoration_opacity": 128},
            ],
        },
    ],
}

from src.config._builder import build_tire_struct

tire_struct = build_tire_struct(CONFIG)
```

---

## 6. 各配置 rules_config 一览表

| 配置 | 对称规则 | continuity_mode_list | rib_number | 小图数 |
|---|---|---|---|---|
| 1.1 | rule1 | — | 5 | 5 |
| 1.2 | rule2 | — | 5 | 5 |
| 1.3 | rule3 | — | 5 | 5 |
| 1.4 | rule1 | CONTINUITY_0, CONTINUITY_1 | 5 | 5 |
| 1.5 | rule2 | CONTINUITY_0, CONTINUITY_1 | 5 | 5 |
| 1.6 | rule3 | CONTINUITY_0, CONTINUITY_2 | 5 | 5 |
| 1.7 | rule1 | — | 4 | 4 |
| 1.8 | rule1, rule2 | — | 4 | 4 |
| 1.9 | rule1, rule2, rule3 | — | 4 | 4 |
| 1.10 | rule1, rule2, rule3 | CONTINUITY_3 | 4 | 4 |
| 1.11 (**反例**) | rule1, rule2, rule3 | CONTINUITY_1, CONTINUITY_2, CONTINUITY_3 | 4 | 4 |

---

## 7. 验证步骤

### 7.1 S1-S2 验证

```bash
python -c "
from src.models.enums import DecorationPositionEnum
print(DecorationPositionEnum.LEFT, DecorationPositionEnum.RIGHT)

from src.models.rule_models import DecorationItem
d = DecorationItem(position=DecorationPositionEnum.LEFT, decoration_width=300, decoration_height=640, decoration_opacity=128)
print(d)
"
```

### 7.2 S3 验证

```bash
python -c "
from src.config._builder import build_tire_struct
print('_builder.py loaded successfully')
"
```

### 7.3 S4 逐个验证

```bash
# 每个配置文件需验证：导入不报错、tire_struct 可构造
python -c "
from src.config.ref_5rib_sym0_no_cont import tire_struct, CONFIG
assert tire_struct.scheme_rank == 1
assert len(tire_struct.small_images) == 5
assert len(tire_struct.rules_config) == 4  # rule1 + 100/101/102
print('1.1 OK')
"

python -c "
from src.config.ref_4rib_sym456_no_cont import tire_struct
assert len(tire_struct.small_images) == 4
assert len(tire_struct.rules_config) == 6  # rule1+2+3 + 100/101/102
print('1.9 OK')
"
```

### 7.4 完整 pipeline1 执行验证

```python
# tests/integrations/test_ref_configs.py（参考示例，不必创建）
from src.config.ref_5rib_sym0_no_cont import tire_struct
from src.piplines.pipline1 import run_pipeline1
from src.rules.executors import load_all_executors

load_all_executors()
result = run_pipeline1(tire_struct)
assert result.flag is True
```

---

## 8. 实施顺序建议

```
S1 (enums.py) → S2 (rule_models.py) → S3 (_builder.py) → S4 (11个config文件)
```

S4 内部按难度递增：
1. 先 1.1 - 1.3（最简单，无连续性）
2. 再 1.7 - 1.9（4-rib 无连续性）
3. 再 1.4 - 1.6（有连续性）
4. 再 1.10（4-rib 有连续性）
5. 最后 1.11（反例）
