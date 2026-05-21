# 几何合理性打分器 - 节点层模块

## 文档信息

| 属性 | 值 |
|------|-----|
| **适用模块** | `src/nodes/geometry_scorer.py` |
| **目标读者** | PM、架构师、开发工程师、测试工程师 |

---

## 1. 概述

### 1.1 模块定位

`geometry_scorer` 是几何合理性业务评分的**核心计算节点**，负责基于血缘结构、小图评估结果和大图评估结果，以大图为维度计算归一化总分（0-100分）。

**核心职责**：
- 输入：大图、小图列表、血缘信息、规则配置
- 输出：各项规则得分、归一化总分（x/100）

**补充函数**：
- `score_geometry`：基于已有 feature 重新计算规则得分并刷新总分。适用于用户调整 `rules_config` 中的阈值或参数后，复用已有 feature 重新评分的场景。

### 1.2 业务价值

| 维度 | 说明 |
|------|------|
| **输入输出** | 多对一映射，多条规则得分聚合为单一大图总分 |
| **业务场景** | 轮胎设计方案质量评估、方案排序、质量报告生成 |
| **技术价值** | 实现规则得分的统一归一化，支持规则动态增减 |

### 1.3 流程定位

```
Pipeline-1: generate_big_image_with_evaluation
    节点1: small_image_evaluator → 节点2: stitch_scheme_generator
        ↓
    节点3: big_image_stitcher → 节点4: big_image_evaluator
        ↓
    节点5: geometry_scorer (本模块)
        ↓
    输出: 大图 + 血缘 + 特征 + 归一化总分

Pipeline-3: update_big_image_score
    直接调用 geometry_scorer
        ↓
    输出: 更新后的归一化总分
```

---

## 2. 术语定义

| 术语 | 定义 |
|------|------|
| **血缘 (Lineage)** | 大图生成过程的追溯信息，包含拼接方案、主沟花纹方案、装饰花纹方案 |
| **归一化总分** | 将多条规则得分按比例映射到 0-100 分范围的综合评分 |
| **有效规则** | `max_score > 0` 且规则名称存在于 `individual_scores` 中的规则 |
| **规则权重** | 由 `max_score` 字段定义，体现规则重要程度 |
| **融合打分** | 结合比例型和平均值型的小图规则评分方法 |

---

## 3. 架构设计

### 3.1 模块分层结构

```
┌──────────────────────────────────────────────────────────┐
│              geometry_scorer.py                          │
│              (业务评分与归一化聚合)                       │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐ │
│  │  _calculate_normalized_score()                     │ │
│  │  (归一化算法核心)                                    │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  _calculate_small_image_rule_score()               │ │
│  │  (小图规则融合打分)                                  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
          │
          ├─→ src.models.ImageEvaluation (数据模型)
          ├─→ src.models.BaseRuleConfig (规则配置)
          └─→ src.models.BigImage/SmallImage (图像数据)
```

### 3.2 文件职责划分

| 文件 | 职责 | 核心功能 |
|------|------|----------|
| `geometry_scorer.py` | 几何合理性业务评分主入口 | 规则分类、小图融合打分、归一化计算 |
| `base.py` | 通用评估工具 | 规则配置筛选、重复校验（复用） |
| `rule_models.py` | 规则数据模型 | 规则配置、特征、评分定义 |
| `image_models.py` | 图像数据模型 | 大图、小图、评估结果定义 |

### 3.3 依赖关系

```
geometry_scorer.py
    ├── src.models.ImageEvaluation
    │   ├── rules: List[RuleEvaluation]
    │   └── current_score: int
    ├── src.models.BaseRuleConfig
    │   ├── name: str
    │   └── max_score: int
    ├── src.models.BigImage
    │   ├── evaluation: ImageEvaluation
    │   └── lineage: ImageLineage
    └── src.models.SmallImage
        └── evaluation: ImageEvaluation
```

---

## 4. 核心算法详解

### 4.1 小图规则融合打分算法

**算法名称**：`_calculate_small_image_rule_score`

**算法原理**：融合比例型和平均值型的统一打分规则

$$\text{最终得分} = \text{满足比例} \times \text{平均得分}$$

**计算步骤**：

1. **统计得分**：遍历所有小图，统计每张图的规则得分
2. **计算满足比例**：满足条件的小图数 / 总小图数（得分>0视为满足）
3. **计算平均得分**：所有小图得分之和 / 小图数量
4. **融合计算**：满足比例 × 平均得分
5. **四舍五入**：结果取整并限制在 0-max_score 范围内

**边界处理**：
- 无小图时，返回 0 分
- 无有效得分时，返回 0 分

**示例验证**（Rule14，max_score=2）：

| 方案 | 小图数量 | 每张得分 | 满足比例 | 平均得分 | 最终得分 |
|------|----------|----------|----------|----------|----------|
| a | 4 | [2,0,2,0] | 50% | 1.0 | 1 |
| b | 3 | [2,0,0] | 33% | 0.67 | 0 |
| c | 2 | [2,2] | 100% | 2.0 | 2 |
| d | 4 | [2,2,2,2] | 100% | 2.0 | 2 |

### 4.2 归一化算法

**算法名称**：`_calculate_normalized_score`

**算法原理**：

$$\text{总分} = \left( \frac{\sum \text{实际得分}}{\sum \text{最大可能得分}} \right) \times 100$$

**计算步骤**：

1. **规则分类**：区分大图规则和小图规则
2. **大图规则得分**：直接提取大图评估结果
3. **小图规则得分**：使用融合打分算法计算
4. **得分聚合**：计算所有有效规则的实际得分之和和最大可能得分之和
5. **归一化映射**：将得分比例映射到 0-100 分范围

### 4.3 规则分类策略

| 规则类型 | 规则编号 | 评估维度 | 处理方式 |
|----------|----------|----------|----------|
| 大图规则 | Rule1-5, 7, 12-13, 16-19 | 大图 | 直接提取评估结果 |
| 小图规则 | Rule6, 8-11, 14-15 | 小图聚合 | 融合打分算法 |
| 默认规则 | Rule20, 22 | - | 默认获得 max_score 分数 |

> **分类方式说明**：规则类型通过配置对象的 `rule_type` 属性直接获取，支持 `BIG_IMAGE`、`SMALL_IMAGE`、`DEFAULT` 三种类型（枚举值）。

### 4.4 小图筛选机制

**筛选依据**：根据血缘信息中 `stitching_scheme.ribs_scheme_implementation[].before_image` 字段筛选参与计算的小图。

**筛选流程**：
1. 遍历血缘中的所有 RIB 拼接实现
2. 提取 `before_image` 字段（小图的 base64 数据）
3. 筛选 `small_images` 中 `image_base64` 匹配的小图（只取第一个匹配）
4. 保留重复的 `before_image`，确保参与计算的小图数量与 `rib_number` 一致
5. 仅使用筛选后的小图进行融合打分计算

**设计意图**：
- 确保评分只基于实际参与大图拼接的小图
- 通过精确的图片数据匹配，避免区域标识可能带来的歧义
- 保留重复项，确保评分与拼接方案的 RIB 数量一致
- 保持评分与大图生成过程的一致性

---

## 5. 流程编排与数据流

### 5.1 完整处理流程

```
输入：big_image + small_images + lineage + rules_config
         │
         ▼ [步骤1: 规则分类]
    ┌──────────────┬──────────────┬──────────────┐
    │  大图规则     │  小图规则      │  默认规则     │
    │Rule1-5,7,12, │ Rule6,8-11   │ Rule20,22    │
    │ 13,16-17,    │    14,15     │              │
    │ 18-19        │              │              │
    └──────┬───────┴──────┬───────┴──────┬───────┘
           │              │              │
           ▼              ▼              ▼
    [步骤2: 小图筛选] ──────────────────────►
    根据血缘中的rib_source筛选有效小图
           │
           ▼ [步骤3: 大图规则得分]
    从evaluation.rules直接提取score
           │
           ▼ [步骤4: 小图规则得分]
    融合打分算法（仅使用有效小图）
           │
           ▼ [步骤5: 默认规则得分]
    默认获得max_score
           │
           ▼ [步骤6: 归一化计算总分]
    total_score = Σ(得分) / Σ(max_score) × 100
           │
           ▼ [步骤7: 组装结果]
    返回: {individual_scores, total_score, rule_details}

```

### 5.2 数据流转

| 阶段 | 数据格式 | 说明 |
|------|----------|------|
| 输入 | `BigImage` + `List[SmallImage]` + `ImageLineage` + `List[BaseRuleConfig]` | 完整的图像和配置数据 |
| 中间 | `Dict[str, int]` | 各规则的得分（大图直接提取，小图融合计算） |
| 输出 | `Dict[str, Any]` | 包含各项得分和归一化总分 |

---

## 6. 函数定义

### 6.1 主函数

```python
def calculate_geometric_scores(
    big_image: BigImage,
    small_images: Sequence[SmallImage],
    rules_config: Sequence[BaseRuleConfig],
) -> BigImage:
    """
    几何合理性业务评分封装函数（节点层接口）
    
    输入为大图、小图列表和规则配置，输出为更新评分后的大图。
    
    Args:
        big_image: 已完成 feature 计算的大图对象
        small_images: 小图列表，包含各小图的 evaluation 字段
        rules_config: 规则配置列表，定义各规则的 max_score
    
    Returns:
        BigImage: 更新评分后的大图对象，big_image.scores.compliance 已更新
    """
```

### 6.2 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `big_image` | `BigImage` | 是 | 已完成 feature 计算的大图对象 |
| `small_images` | `Sequence[SmallImage]` | 是 | 小图列表，包含各小图的 evaluation 字段 |
| `rules_config` | `Sequence[BaseRuleConfig]` | 是 | 规则配置列表，定义各规则的 max_score |

### 6.3 核心内部函数

```python
def _calculate_geometric_scores(
    big_image: BigImage,
    small_images: List[SmallImage],
    lineage: ImageLineage,
    rules_config: List[BaseRuleConfig],
) -> dict:
    """
    几何合理性业务评分核心函数（内部调用）
    
    注意：调用前需确保所有参数已通过校验
    
    Args:
        big_image: 待评分的大图对象，包含 evaluation 字段（已校验）
        small_images: 小图列表，包含各小图的 evaluation 字段
        lineage: 血缘信息，用于验证拼接方案（已校验）
        rules_config: 规则配置列表，定义各规则的 max_score
    
    Returns:
        dict: 包含各项得分和总分的结果字典
    """
```

### 6.2 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `big_image` | `BigImage` | 是 | 待评分的大图对象，包含 `evaluation` 字段 |
| `small_images` | `List[SmallImage]` | 是 | 小图列表，包含各小图的 `evaluation` 字段 |
| `lineage` | `ImageLineage` | 是 | 血缘信息，用于验证拼接方案并筛选参与计算的小图 |
| `rules_config` | `List[BaseRuleConfig]` | 是 | 规则配置列表，定义各规则的 `max_score` |

### 6.3 返回值结构

```python
{
    'individual_scores': {
        'rule1_5': 10,      # 对称性总分
        'rule6': 10,        # 节距周期性
        'rule7': 8,         # 主沟数量
        'rule8': 4,         # 横沟数量
        'rule9': 4,         # 钢片数量
        'rule10': 4,        # 花纹块均分
        'rule11': 4,        # 纵向钢片和细沟
        'rule12_16_17': 16, # RIB间连续性总分
        'rule13': 2,        # 海陆比
        'rule14': 2,        # 交点数量
        'rule15': 2,        # 花纹块面积比例
        'rule18': 2,        # 颜色灰度占比
        'rule19': 2,        # 边缘灰色区域
        'rule20': 10,       # 文生图
        'rule22': 20        # 分辨率
    },
    'total_score': 75,           # 归一化总分（0-100）
    'max_possible_score': 100,   # 最大可能得分（所有有效规则 max_score 之和）
    'effective_rule_count': 10,  # 有效规则数量
    'rule_details': [
        {
            'name': 'rule1_5',
            'description': '非对称花纹5个花纹RIB无对称原则、中心旋转、中心线镜像、镜像对称错位、用户指定对称性',
            'score': 10,
            'max_score': 10,
            'is_applied': True,       # score > 0 时为 True，否则为 False，用于快速识别未满足的规则
            'rule_type': 'BIG_IMAGE'  # RuleTypeEnum 枚举值: BIG_IMAGE / SMALL_IMAGE / DEFAULT
        },
        {
            'name': 'rule8',
            'description': '单节距内横沟数量约束',
            'score': 4,
            'max_score': 4,
            'is_applied': True,
            'rule_type': 'small_image'
        },
        # ... 其他规则详情
    ]
}
```

### 6.4 返回值字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `individual_scores` | `Dict[str, int]` | 各规则的实际得分 |
| `total_score` | `int` | 归一化总分（0-100） |
| `max_possible_score` | `int` | 所有有效规则的 `max_score` 之和 |
| `effective_rule_count` | `int` | 参与评分的有效规则数量 |
| `rule_details` | `List[Dict]` | 各规则的详细信息（名称、描述、得分、最大得分、是否应用、规则类型） |

---

## 7. 配置参数说明

### 7.1 规则权重配置

| 序号 | 规则名 | 需求描述 | 权重(max_score) | 规则类型 |
|------|--------|----------|----------------|----------|
| 1 | Rule1_5 | 可控的对称性 | 10 | 大图 |
| 6 | Rule6 | 节距周期性（5-7个节距，无缝拼接） | 10 | 小图 |
| 7 | Rule7 | 主沟宽度8-12mm，3-4条 | 8 | 大图 |
| 8 | Rule8 | 横沟数量约束 | 4 | 小图 |
| 9 | Rule9 | 横向钢片数量约束 | 4 | 小图 |
| 10 | Rule10 | 横向钢片位置均分 | 4 | 小图 |
| 11 | Rule11 | 纵向钢片&细沟数量 | 4 | 小图 |
| 12 | Rule12 | 钢片&横沟连续性 | 6 | 大图 |
| 13 | Rule13 | 海陆比28%-35% | 2 | 大图 |
| 14 | Rule14 | 交点数量≤2 | 2 | 小图 |
| 15 | Rule15 | 花纹块面积比例≤1:1.2 | 2 | 小图 |
| 16 | Rule16 | RIB2/3/4横沟任意组合连续性 | 4 | 大图 |
| 17 | Rule17 | RIB1/2与RIB4/5概率连续 | 6 | 大图 |
| 18 | Rule18 | 颜色灰度变化表征沟深浅 | 2 | 大图 |
| 19 | Rule19 | 边缘灰色区域装饰性造型 | 2 | 大图 |
| 20 | Rule20 | 文生图 | 10 | - |
| 22 | Rule22 | 图片分辨率 | 20 | - |

### 7.2 规则类型分类

| 分类 | 规则编号 | 权重合计 |
|------|----------|----------|
| 大图规则-8条 | Rule1-5, 7, 12-13, 16-19 | 40 |
| 小图规则-7条 | Rule6, 8-11, 14-15 | 30 |
| 文生图 | Rule20 | 10 |
| 超分模型-分辨率 | Rule22 | 20 | 
| **总计** | **17条有效规则** | **100** |

---

## 8. 与现有模块的集成

### 8.1 在 Pipeline-1 中的调用      

```python
# src/api/generation.py

def generate_big_image_with_evaluation(tire_struct: TireStruct) -> TireStruct:
    # ... 节点1-4执行 ...
    
    # 节点5：几何合理性评分
    from src.nodes.geometry_scorer import calculate_geometric_scores
    
    # 传入大图、小图列表和规则配置，结果自动更新到 big_image.scores.compliance
    tire_struct.big_image = calculate_geometric_scores(
        big_image=tire_struct.big_image,
        small_images=tire_struct.small_images,
        rules_config=tire_struct.rules_config
    )
    tire_struct.flag = True
    
    return tire_struct
```

### 8.2 在 Pipeline-3 中的调用

```python
# src/api/scoring.py

def update_big_image_score(tire_struct: TireStruct) -> TireStruct:
    from src.nodes.geometry_scorer import calculate_geometric_scores
    
    # 传入大图、小图列表和规则配置，结果自动更新到 big_image.scores.compliance
    tire_struct.big_image = calculate_geometric_scores(
        big_image=tire_struct.big_image,
        small_images=tire_struct.small_images,
        rules_config=tire_struct.rules_config
    )
    tire_struct.flag = True
    
    return tire_struct
```

---

**文档结束**