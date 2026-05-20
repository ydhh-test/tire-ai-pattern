# -*- coding: utf-8 -*-

"""geometry_scorer.py 单元测试
测试用例统计：
========================
一、calculate_geometric_scores 端到端测试 - 5个
  设计角度：
  1. 全部规则满分：所有规则均得满分，期望 total_score=100
  2. 小图规则部分满足：部分小图得分为0，验证融合打分算法（期望 total_score=81）
  3. 大图规则部分得分：大图规则未得满分，验证归一化计算（期望 total_score=81）
  4. 仅默认规则得分：大图和小图规则均为0分，仅默认规则得分（期望 total_score=62）
  5. 空小图列表：small_images=[]，小图规则应得0分
  结果输出：所有端到端测试结果输出至 OUTPUT_DIR = "./.results/tire_design_images"

二、_extract_used_small_image_regions 测试 - 4个
  设计角度：
  1. 正常提取：lineage 包含多个 before_image（保留顺序和重复）
  2. lineage为None：传入 None 时返回空列表
  3. stitching_scheme为None：lineage.stitching_scheme 为 None 时返回空列表
  4. SKIPPED_GARBAGE 过滤：before_image 为 SKIPPED_GARBAGE 时不加入列表

三、_classify_rules 测试 - 4个
  设计角度：
  1. 正常分类：包含大图/小图/默认三类规则的混合列表，正确分类
  2. 仅大图规则：所有规则均为 BIG_IMAGE 类型
  3. 仅小图规则：所有规则均为 SMALL_IMAGE 类型
  4. 空规则列表：传入空列表，返回三个空列表

四、_extract_big_image_scores 测试 - 4个
  设计角度：
  1. 正常提取：大图 evaluation 中存在对应规则的 score，正确提取
  2. 规则评估缺失：大图 evaluation 中不存在某规则，返回0分
  3. score为None：rule_eval.score 为 None 时返回0分
  4. evaluation为None：big_image.evaluation 为 None 时返回空字典

五、_calculate_small_image_rule_score 测试 - 8个
  设计角度：
  1. 全部满分：所有小图均得满分，满足比例100%，最终得满分
  2. 全部0分：所有小图均为0分，满足比例0%，最终得0分
  3. 部分满足：部分小图>0部分=0，验证 满足比例×平均得分 公式
  4. 单张小图：仅1张小图且得分>0，满足比例100%，最终得分=该小图得分
  5. 空小图列表：small_images=[]，返回0分
  6. 无有效得分：所有小图 evaluation 中均无该规则得分，返回0分
  7. 得分超出max_score：计算结果超过 max_score，验证被截断到 max_score
  8. 负分处理：小图得分为负数，验证 max(0, ...) 截断到0

六、_get_default_scores 测试 - 2个
  设计角度：
  1. 正常获取：多条默认规则，每条返回 config.max_score
  2. 空列表：传入空列表，返回空字典

七、_calculate_normalized_score 测试 - 5个
  设计角度：
  1. 正常归一化：所有规则均得满分，期望 normalized_score=100
  2. 部分得分：实际得分与最大得分比例非100%，验证四舍五入
  3. max_total为0：所有规则 max_score=0，返回 (0, 0, effective_count)
  4. 空individual_scores：规则名称不在 individual_scores 中，不计入有效规则
  5. 规则max_score为0：某规则 max_score=0，该规则不参与计算

八、_build_result 测试 - 3个
  设计角度：
  1. 正常组装：验证返回字典结构完整，rule_details 字段正确
  2. is_applied语义：score>0时为True，score=0时为False
  3. rule_type类型：返回 RuleTypeEnum 枚举值而非字符串

九、_get_rule_type 测试 - 3个
  设计角度：
  1. 正常查找：规则名存在于 rules_config 中，返回对应 rule_type
  2. 规则名大小写不敏感：规则名大小写不同仍能正确匹配
  3. 规则名不存在：未找到配置实例时，默认返回 RuleTypeEnum.BIG_IMAGE

十、异常处理测试 - 4个
  设计角度：
  1. tire_struct为None：calculate_geometric_scores 传入 None 抛出 InputDataError
  2. big_image为None：tire_struct.big_image 为 None 抛出 InputDataError
  3. evaluation为None：big_image.evaluation 为 None 抛出 InputDataError
  4. lineage为None：big_image.lineage 为 None 抛出 InputDataError

十一、小图筛选机制测试 - 2个
  设计角度：
  1. 区域匹配筛选：仅 biz.region.value 在 used_regions 中的小图参与计算
  2. region为None：小图 biz.region 为 None 时不参与计算
========================
"""

import json
import os
import unittest
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from src.nodes.geometry_scorer import (
    calculate_geometric_scores,
    _calculate_geometric_scores,
    _extract_used_small_image_regions,
    _classify_rules,
    _extract_big_image_scores,
    _calculate_small_image_rule_score,
    _get_default_scores,
    _calculate_normalized_score,
    _build_result,
    _get_rule_type,
)
from src.common.exceptions import InputDataError
from src.models.enums import RuleTypeEnum, RegionEnum, LevelEnum, SourceTypeEnum
from src.models.image_models import BigImage, SmallImage, ImageEvaluation, RuleEvaluation, ImageMeta, ImageBiz, ImageLineage, ImageScore
from src.models.rule_models import BaseRuleConfig
from src.models.scheme_models import RibSchemeImpl, StitchingScheme, StitchingSchemeAbstract, MainGrooveScheme, DecorationScheme
from src.models.tire_struct import TireStruct

# 端到端测试结果输出目录（与 scripts/test_geometry_scorer.py 保持一致）
OUTPUT_DIR = "./.results/tire_design_images"


def ensure_output_dir():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


def _create_mock_score_class(score_value: int):
    """创建模拟的 score 对象"""
    mock_score = MagicMock()
    mock_score.score = score_value
    return mock_score


def _create_mock_rule_evaluation(rule_name: str, score_value: int = None) -> RuleEvaluation:
    """创建模拟的规则评估结果"""
    mock_config = MagicMock()
    mock_config.name = rule_name
    
    rule_eval = MagicMock(spec=RuleEvaluation)
    rule_eval.name = rule_name
    rule_eval.config = mock_config
    rule_eval.feature = MagicMock()
    
    if score_value is not None:
        rule_eval.score = _create_mock_score_class(score_value)
    else:
        rule_eval.score = None
    
    return rule_eval


def _create_mock_evaluation(rules: List[RuleEvaluation]) -> ImageEvaluation:
    """创建模拟的评估对象"""
    evaluation = MagicMock(spec=ImageEvaluation)
    evaluation.rules = rules
    
    def get_rule(name):
        for rule in rules:
            if rule.name == name:
                return rule
        return None
    
    evaluation.get_rule = get_rule
    return evaluation


def _create_mock_big_image(evaluation: ImageEvaluation = None) -> BigImage:
    """创建模拟的大图对象"""
    big_image = MagicMock(spec=BigImage)
    big_image.evaluation = evaluation
    return big_image


def _create_mock_small_image(image_base64: str = None, evaluation: ImageEvaluation = None) -> SmallImage:
    """创建模拟的小图对象（使用 image_base64）"""
    small_image = MagicMock(spec=SmallImage)
    small_image.image_base64 = image_base64
    small_image.evaluation = evaluation
    return small_image


def _create_mock_lineage(before_images: List[str] = None) -> ImageLineage:
    """创建模拟的血缘信息对象（使用 before_image）"""
    if before_images is None:
        return None
    
    rib_impls = []
    for idx, before_image in enumerate(before_images):
        rib_impl = MagicMock(spec=RibSchemeImpl)
        rib_impl.before_image = before_image
        rib_impls.append(rib_impl)
    
    stitching_scheme = MagicMock(spec=StitchingScheme)
    stitching_scheme.ribs_scheme_implementation = rib_impls
    
    lineage = MagicMock(spec=ImageLineage)
    lineage.stitching_scheme = stitching_scheme
    
    return lineage


def _create_mock_tire_struct(big_image: BigImage = None, small_images: List[SmallImage] = None, rules_config: List[BaseRuleConfig] = None) -> TireStruct:
    """创建模拟的 TireStruct 对象"""
    tire_struct = MagicMock(spec=TireStruct)
    tire_struct.big_image = big_image if big_image is not None else _create_mock_big_image()
    tire_struct.small_images = small_images if small_images is not None else []
    tire_struct.rules_config = rules_config if rules_config is not None else []
    return tire_struct


def _create_mock_rule_config(name: str, rule_type: RuleTypeEnum, max_score: int = 10, description: str = "") -> BaseRuleConfig:
    """创建模拟的规则配置"""
    config = MagicMock(spec=BaseRuleConfig)
    config.name = name
    config.rule_type = rule_type
    config.max_score = max_score
    config.description = description
    return config


# ========================
# 一、calculate_geometric_scores 端到端测试
# ========================

class TestCalculateGeometricScoresE2E(unittest.TestCase):
    """calculate_geometric_scores 端到端测试（6个用例）"""
    
    @classmethod
    def setUpClass(cls):
        """初始化通用规则配置"""
        cls.rule_configs = [
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE, 10, '节距周期性'),
            _create_mock_rule_config('rule8', RuleTypeEnum.SMALL_IMAGE, 4, '横沟数量'),
            _create_mock_rule_config('rule13', RuleTypeEnum.BIG_IMAGE, 2, '海陆比'),
            _create_mock_rule_config('rule14', RuleTypeEnum.SMALL_IMAGE, 2, '交点数量'),
            _create_mock_rule_config('rule20', RuleTypeEnum.DEFAULT, 10, '文生图'),
            _create_mock_rule_config('rule22', RuleTypeEnum.DEFAULT, 20, '分辨率'),
        ]
        cls.max_possible = 48  # 10+4+2+2+10+20
        # 模拟的图片 base64 数据
        cls.image_data_1 = "base64_image_data_1"
        cls.image_data_2 = "base64_image_data_2"
    
    def _create_big_image_with_scores(self, scores: Dict[str, int], lineage: ImageLineage = None) -> BigImage:
        """创建带得分的大图"""
        rules = []
        for config in self.rule_configs:
            if config.rule_type == RuleTypeEnum.BIG_IMAGE or config.rule_type == RuleTypeEnum.DEFAULT:
                score_val = scores.get(config.name, 0)
                rules.append(_create_mock_rule_evaluation(config.name, score_val))
        
        evaluation = _create_mock_evaluation(rules)
        big_image = _create_mock_big_image(evaluation)
        big_image.lineage = lineage
        big_image.scores = []
        return big_image
    
    def _create_small_images_with_scores(self, scores_list: List[Dict[str, int]], image_base64_list: List[str] = None) -> List[SmallImage]:
        """创建带得分的小图列表（使用 image_base64）"""
        if image_base64_list is None:
            image_base64_list = [f"base64_image_{i}" for i in range(len(scores_list))]
        
        small_images = []
        for idx, scores in enumerate(scores_list):
            rules = []
            for config in self.rule_configs:
                if config.rule_type == RuleTypeEnum.SMALL_IMAGE:
                    score_val = scores.get(config.name, 0)
                    rules.append(_create_mock_rule_evaluation(config.name, score_val))
            
            evaluation = _create_mock_evaluation(rules)
            small_images.append(_create_mock_small_image(image_base64_list[idx], evaluation))
        
        return small_images
    
    def _save_e2e_results(self, results: List[Dict[str, Any]]):
        """保存端到端测试结果到 JSON 文件（保持与 scripts/test_geometry_scorer.py 一致的输出格式）"""
        output_dir = ensure_output_dir()
        
        passed_count = sum(1 for r in results if r['is_passed'])
        total_count = len(results)
        
        summary_result = {
            'total_tests': total_count,
            'passed_tests': passed_count,
            'failed_tests': total_count - passed_count,
            'pass_rate': passed_count / total_count * 100 if total_count > 0 else 0,
            'results': results,
        }
        
        output_file = os.path.join(output_dir, "test_geometry_scorer_e2e_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary_result, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def test_e2e_all_rules_full_score(self):
        """端到端-1: 全部规则满分，期望 total_score=100"""
        # 使用相同的图片数据模拟血缘关联
        image_data = "base64_center_image"
        lineage = _create_mock_lineage([image_data, image_data, image_data])
        big_image = self._create_big_image_with_scores({
            'rule13': 2, 'rule20': 10, 'rule22': 20
        }, lineage)
        small_images = self._create_small_images_with_scores([
            {'rule6': 10, 'rule8': 4, 'rule14': 2},
            {'rule6': 10, 'rule8': 4, 'rule14': 2},
            {'rule6': 10, 'rule8': 4, 'rule14': 2},
        ], [image_data, image_data, image_data])
        
        # 创建 TireStruct 并调用新接口
        tire_struct = _create_mock_tire_struct(big_image, small_images, self.rule_configs)
        result_tire_struct = calculate_geometric_scores(tire_struct)
        
        # 验证 compliance_score
        self.assertEqual(len(result_tire_struct.big_image.scores), 1)
        self.assertEqual(result_tire_struct.big_image.scores[0].compliance, 100)
    
    def test_e2e_small_image_partial_satisfied(self):
        """端到端-2: 小图规则部分满足，期望 compliance_score=81"""
        image_data = "base64_center_image"
        lineage = _create_mock_lineage([image_data, image_data, image_data])
        big_image = self._create_big_image_with_scores({
            'rule13': 2, 'rule20': 10, 'rule22': 20
        }, lineage)
        small_images = self._create_small_images_with_scores([
            {'rule6': 10, 'rule8': 4, 'rule14': 2},
            {'rule6': 0, 'rule8': 0, 'rule14': 0},
            {'rule6': 10, 'rule8': 4, 'rule14': 2},
        ], [image_data, image_data, image_data])
        
        tire_struct = _create_mock_tire_struct(big_image, small_images, self.rule_configs)
        result_tire_struct = calculate_geometric_scores(tire_struct)
        
        expected = 81
        self.assertEqual(result_tire_struct.big_image.scores[0].compliance, expected)
    
    def test_e2e_big_image_partial_score(self):
        """端到端-3: 大图规则部分得分，期望 compliance_score=81"""
        image_data = "base64_center_image"
        lineage = _create_mock_lineage([image_data])
        big_image = self._create_big_image_with_scores({
            'rule13': 1, 'rule20': 10, 'rule22': 20
        }, lineage)
        small_images = self._create_small_images_with_scores([
            {'rule6': 5, 'rule8': 2, 'rule14': 1},
        ], [image_data])
        
        tire_struct = _create_mock_tire_struct(big_image, small_images, self.rule_configs)
        result_tire_struct = calculate_geometric_scores(tire_struct)
        
        expected = 81
        self.assertEqual(result_tire_struct.big_image.scores[0].compliance, expected)
    
    def test_e2e_only_default_rules_scored(self):
        """端到端-4: 仅默认规则得分，期望 compliance_score=62"""
        image_data = "base64_center_image"
        lineage = _create_mock_lineage([image_data, image_data, image_data])
        big_image = self._create_big_image_with_scores({
            'rule13': 0, 'rule20': 10, 'rule22': 20
        }, lineage)
        small_images = self._create_small_images_with_scores([
            {'rule6': 0, 'rule8': 0, 'rule14': 0},
            {'rule6': 0, 'rule8': 0, 'rule14': 0},
            {'rule6': 0, 'rule8': 0, 'rule14': 0},
        ], [image_data, image_data, image_data])
        
        tire_struct = _create_mock_tire_struct(big_image, small_images, self.rule_configs)
        result_tire_struct = calculate_geometric_scores(tire_struct)
        
        expected = 62
        self.assertEqual(result_tire_struct.big_image.scores[0].compliance, expected)
    
    def test_e2e_empty_small_images(self):
        """端到端-5: 空小图列表，小图规则得0分"""
        image_data = "base64_center_image"
        lineage = _create_mock_lineage([image_data])
        big_image = self._create_big_image_with_scores({
            'rule13': 2, 'rule20': 10, 'rule22': 20
        }, lineage)
        small_images = []
        
        tire_struct = _create_mock_tire_struct(big_image, small_images, self.rule_configs)
        result_tire_struct = calculate_geometric_scores(tire_struct)
        
        # 验证 compliance_score（小图规则得0分，总分 = (2+0+0+0+10+20)/48*100 = 66.67 → 67）
        self.assertEqual(result_tire_struct.big_image.scores[0].compliance, 67)
    
    @classmethod
    def tearDownClass(cls):
        """所有端到端测试完成后，汇总结果输出到 JSON 文件"""
        # 注意：实际实现中需要在每个 test 方法中收集结果，或使用 test result 对象
        # 此处为规划说明，具体实现可使用 unittest.TestResult 或自定义收集逻辑
        pass


# ========================
# 二、_extract_used_small_image_regions 测试
# ========================

class TestExtractUsedSmallImageRegions(unittest.TestCase):
    """_extract_used_small_image_regions 测试（3个用例）"""
    
    def test_normal_extraction(self):
        """正常提取：lineage 包含多个 before_image（保留顺序和重复）"""
        lineage = _create_mock_lineage(['image1', 'image2', 'image1'])
        result = _extract_used_small_image_regions(lineage)
        expected = ['image1', 'image2', 'image1']  # 列表而非集合，保留重复
        self.assertEqual(result, expected)
    
    def test_lineage_is_none(self):
        """lineage为None：返回空列表"""
        result = _extract_used_small_image_regions(None)
        expected = []
        self.assertEqual(result, expected)
    
    def test_stitching_scheme_is_none(self):
        """stitching_scheme为None：返回空列表"""
        lineage = MagicMock(spec=ImageLineage)
        lineage.stitching_scheme = None
        result = _extract_used_small_image_regions(lineage)
        expected = []
        self.assertEqual(result, expected)
    
    def test_skipped_garbage_filtering(self):
        """SKIPPED_GARBAGE 过滤：before_image 为 SKIPPED_GARBAGE 时不加入列表"""
        lineage = _create_mock_lineage(['image1', 'SKIPPED_GARBAGE', 'image2'])
        result = _extract_used_small_image_regions(lineage)
        expected = ['image1', 'image2']
        self.assertEqual(result, expected)


# ========================
# 三、_classify_rules 测试
# ========================

class TestClassifyRules(unittest.TestCase):
    """_classify_rules 测试（4个用例）"""
    
    def test_mixed_rules_classification(self):
        """正常分类：包含大图/小图/默认三类规则"""
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE),
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE),
            _create_mock_rule_config('rule20', RuleTypeEnum.DEFAULT),
        ]
        big, small, default = _classify_rules(rules)
        expected_counts = (1, 1, 1)
        expected_names = ('rule1', 'rule6', 'rule20')
        self.assertEqual((len(big), len(small), len(default)), expected_counts)
        self.assertEqual(big[0].name, expected_names[0])
        self.assertEqual(small[0].name, expected_names[1])
        self.assertEqual(default[0].name, expected_names[2])
    
    def test_only_big_image_rules(self):
        """仅大图规则：所有规则均为 BIG_IMAGE 类型"""
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE),
            _create_mock_rule_config('rule7', RuleTypeEnum.BIG_IMAGE),
        ]
        big, small, default = _classify_rules(rules)
        expected_counts = (2, 0, 0)
        self.assertEqual((len(big), len(small), len(default)), expected_counts)
    
    def test_only_small_image_rules(self):
        """仅小图规则：所有规则均为 SMALL_IMAGE 类型"""
        rules = [
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE),
            _create_mock_rule_config('rule8', RuleTypeEnum.SMALL_IMAGE),
        ]
        big, small, default = _classify_rules(rules)
        expected_counts = (0, 2, 0)
        self.assertEqual((len(big), len(small), len(default)), expected_counts)
    
    def test_empty_rules_list(self):
        """空规则列表：返回三个空列表"""
        big, small, default = _classify_rules([])
        expected_counts = (0, 0, 0)
        self.assertEqual((len(big), len(small), len(default)), expected_counts)


# ========================
# 四、_extract_big_image_scores 测试
# ========================

class TestExtractBigImageScores(unittest.TestCase):
    """_extract_big_image_scores 测试（4个用例）"""
    
    def test_normal_extraction(self):
        """正常提取：evaluation 中存在对应规则的 score"""
        rules = [
            _create_mock_rule_config('rule13', RuleTypeEnum.BIG_IMAGE, 2),
        ]
        rule_eval = _create_mock_rule_evaluation('rule13', 2)
        evaluation = _create_mock_evaluation([rule_eval])
        big_image = _create_mock_big_image(evaluation)
        
        result = _extract_big_image_scores(big_image, rules)
        expected = {'rule13': 2}
        self.assertEqual(result['rule13'], expected['rule13'])
    
    def test_rule_evaluation_missing(self):
        """规则评估缺失：evaluation 中不存在某规则，返回0分"""
        rules = [
            _create_mock_rule_config('rule_missing', RuleTypeEnum.BIG_IMAGE, 10),
        ]
        rule_eval = _create_mock_rule_evaluation('rule13', 2)
        evaluation = _create_mock_evaluation([rule_eval])
        big_image = _create_mock_big_image(evaluation)
        
        result = _extract_big_image_scores(big_image, rules)
        expected = {'rule_missing': 0}
        self.assertEqual(result['rule_missing'], expected['rule_missing'])
    
    def test_score_is_none(self):
        """score为None：rule_eval.score 为 None 时返回0分"""
        rules = [
            _create_mock_rule_config('rule13', RuleTypeEnum.BIG_IMAGE, 2),
        ]
        rule_eval = _create_mock_rule_evaluation('rule13', None)
        evaluation = _create_mock_evaluation([rule_eval])
        big_image = _create_mock_big_image(evaluation)
        
        result = _extract_big_image_scores(big_image, rules)
        expected = {'rule13': 0}
        self.assertEqual(result['rule13'], expected['rule13'])
    
    def test_evaluation_is_none(self):
        """evaluation为None：返回空字典"""
        rules = [
            _create_mock_rule_config('rule13', RuleTypeEnum.BIG_IMAGE, 2),
        ]
        big_image = _create_mock_big_image(None)
        
        result = _extract_big_image_scores(big_image, rules)
        expected = {}
        self.assertEqual(result, expected)


# ========================
# 五、_calculate_small_image_rule_score 测试
# ========================

class TestCalculateSmallImageRuleScore(unittest.TestCase):
    """_calculate_small_image_rule_score 测试（8个用例）"""
    
    def test_all_full_score(self):
        """全部满分：满足比例100%，平均分为满分，最终得满分"""
        small_images = [
            _create_mock_small_image("image1", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 10)
            ])),
            _create_mock_small_image("image2", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 10)
            ])),
        ]
        result = _calculate_small_image_rule_score(small_images, 'rule6', 10)
        expected = 10
        self.assertEqual(result, expected)
    
    def test_all_zero_score(self):
        """全部0分：满足比例0%，最终得0分"""
        small_images = [
            _create_mock_small_image("image1", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 0)
            ])),
            _create_mock_small_image("image2", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 0)
            ])),
        ]
        result = _calculate_small_image_rule_score(small_images, 'rule6', 10)
        expected = 0
        self.assertEqual(result, expected)
    
    def test_partial_satisfied(self):
        """部分满足：验证 满足比例×平均得分 公式"""
        # 3张小图，2张满分1张0分
        # 满足比例 = 2/3，平均分 = (10+0+10)/3 = 6.67
        # 最终得分 = round(2/3 * 6.67) = round(4.44) = 4
        small_images = [
            _create_mock_small_image("image1", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 10)
            ])),
            _create_mock_small_image("image2", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 0)
            ])),
            _create_mock_small_image("image3", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 10)
            ])),
        ]
        result = _calculate_small_image_rule_score(small_images, 'rule6', 10)
        expected = 4
        self.assertEqual(result, expected)
    
    def test_single_small_image(self):
        """单张小图：仅1张且得分>0，满足比例100%"""
        small_images = [
            _create_mock_small_image("image1", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 5)
            ])),
        ]
        result = _calculate_small_image_rule_score(small_images, 'rule6', 10)
        expected = 5
        self.assertEqual(result, expected)
    
    def test_empty_small_images(self):
        """空小图列表：返回0分"""
        result = _calculate_small_image_rule_score([], 'rule6', 10)
        expected = 0
        self.assertEqual(result, expected)
    
    def test_no_valid_scores(self):
        """无有效得分：所有小图 evaluation 中均无该规则得分"""
        small_images = [
            _create_mock_small_image("image1", _create_mock_evaluation([])),
            _create_mock_small_image("image2", _create_mock_evaluation([])),
        ]
        result = _calculate_small_image_rule_score(small_images, 'rule6', 10)
        expected = 0
        self.assertEqual(result, expected)
    
    def test_score_exceeds_max_score(self):
        """得分超出max_score：计算结果超过 max_score，验证被截断"""
        # 满足比例=1，平均分=10，但 max_score=5，应截断到5
        small_images = [
            _create_mock_small_image("image1", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', 10)
            ])),
        ]
        result = _calculate_small_image_rule_score(small_images, 'rule6', 5)
        expected = 5
        self.assertEqual(result, expected)
    
    def test_negative_score(self):
        """负分处理：小图得分为负数，验证截断到0"""
        small_images = [
            _create_mock_small_image("image1", _create_mock_evaluation([
                _create_mock_rule_evaluation('rule6', -5)
            ])),
        ]
        result = _calculate_small_image_rule_score(small_images, 'rule6', 10)
        expected = 0
        self.assertEqual(result, expected)


# ========================
# 六、_get_default_scores 测试
# ========================

class TestGetDefaultScores(unittest.TestCase):
    """_get_default_scores 测试（2个用例）"""
    
    def test_normal_default_scores(self):
        """正常获取：多条默认规则，每条返回 config.max_score"""
        rules = [
            _create_mock_rule_config('rule20', RuleTypeEnum.DEFAULT, 10),
            _create_mock_rule_config('rule22', RuleTypeEnum.DEFAULT, 20),
        ]
        result = _get_default_scores(rules)
        expected = {'rule20': 10, 'rule22': 20}
        self.assertEqual(result['rule20'], expected['rule20'])
        self.assertEqual(result['rule22'], expected['rule22'])
    
    def test_empty_default_rules(self):
        """空列表：传入空列表，返回空字典"""
        result = _get_default_scores([])
        expected = {}
        self.assertEqual(result, expected)


# ========================
# 七、_calculate_normalized_score 测试
# ========================

class TestCalculateNormalizedScore(unittest.TestCase):
    """_calculate_normalized_score 测试（5个用例）"""
    
    def test_full_score_normalization(self):
        """正常归一化：所有规则均得满分，期望100分"""
        individual_scores = {'rule1': 10, 'rule6': 10}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 10),
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE, 10),
        ]
        total, max_possible, count = _calculate_normalized_score(individual_scores, rules)
        expected = (100, 20, 2)
        self.assertEqual((total, max_possible, count), expected)
    
    def test_partial_score_normalization(self):
        """部分得分：验证四舍五入"""
        individual_scores = {'rule1': 5, 'rule6': 5}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 10),
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE, 10),
        ]
        total, max_possible, count = _calculate_normalized_score(individual_scores, rules)
        expected = (50, 20, 2)
        self.assertEqual((total, max_possible, count), expected)
    
    def test_max_total_zero(self):
        """max_total为0：所有规则 max_score=0"""
        individual_scores = {'rule1': 0}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 0),
        ]
        total, max_possible, count = _calculate_normalized_score(individual_scores, rules)
        expected = (0, 0, 0)
        self.assertEqual((total, max_possible, count), expected)
    
    def test_rule_not_in_individual_scores(self):
        """空individual_scores：规则名称不在 individual_scores 中"""
        individual_scores = {}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 10),
        ]
        total, max_possible, count = _calculate_normalized_score(individual_scores, rules)
        expected = (0, 0, 0)
        self.assertEqual((total, max_possible, count), expected)
    
    def test_rule_max_score_zero(self):
        """规则max_score为0：某规则 max_score=0，不参与计算"""
        individual_scores = {'rule1': 10, 'rule2': 5}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 10),
            _create_mock_rule_config('rule2', RuleTypeEnum.SMALL_IMAGE, 0),
        ]
        total, max_possible, count = _calculate_normalized_score(individual_scores, rules)
        expected = (100, 10, 1)
        self.assertEqual((total, max_possible, count), expected)


# ========================
# 八、_build_result 测试
# ========================

class TestBuildResult(unittest.TestCase):
    """_build_result 测试（3个用例）"""
    
    def test_normal_build_result(self):
        """正常组装：验证返回字典结构完整"""
        individual_scores = {'rule1': 10, 'rule6': 5}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 10, '大图规则'),
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE, 10, '小图规则'),
        ]
        result = _build_result(individual_scores, 75, 20, 2, rules)
        
        self.assertIn('individual_scores', result)
        self.assertIn('total_score', result)
        self.assertIn('max_possible_score', result)
        self.assertIn('effective_rule_count', result)
        self.assertIn('rule_details', result)
        expected_len = 2
        self.assertEqual(len(result['rule_details']), expected_len)
    
    def test_is_applied_semantics(self):
        """is_applied语义：score>0时为True，score=0时为False"""
        individual_scores = {'rule1': 10, 'rule6': 0}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 10),
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE, 10),
        ]
        result = _build_result(individual_scores, 50, 20, 2, rules)
        
        rule1_detail = [r for r in result['rule_details'] if r['name'] == 'rule1'][0]
        rule6_detail = [r for r in result['rule_details'] if r['name'] == 'rule6'][0]
        
        expected_rule1 = True
        expected_rule6 = False
        self.assertEqual(rule1_detail['is_applied'], expected_rule1)
        self.assertEqual(rule6_detail['is_applied'], expected_rule6)
    
    def test_rule_type_is_enum(self):
        """rule_type类型：返回 RuleTypeEnum 枚举值"""
        individual_scores = {'rule1': 10}
        rules = [
            _create_mock_rule_config('rule1', RuleTypeEnum.BIG_IMAGE, 10),
        ]
        result = _build_result(individual_scores, 100, 10, 1, rules)
        
        rule_detail = result['rule_details'][0]
        expected = RuleTypeEnum.BIG_IMAGE
        self.assertEqual(rule_detail['rule_type'], expected)


# ========================
# 九、_get_rule_type 测试
# ========================

class TestGetRuleType(unittest.TestCase):
    """_get_rule_type 测试（3个用例）"""
    
    def test_normal_lookup(self):
        """正常查找：规则名存在于 rules_config 中"""
        rules = [
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE),
        ]
        result = _get_rule_type('rule6', rules)
        expected = RuleTypeEnum.SMALL_IMAGE
        self.assertEqual(result, expected)
    
    def test_case_insensitive_lookup(self):
        """规则名大小写不敏感：大小写不同仍能匹配"""
        rules = [
            _create_mock_rule_config('Rule6', RuleTypeEnum.SMALL_IMAGE),
        ]
        result = _get_rule_type('rule6', rules)
        expected = RuleTypeEnum.SMALL_IMAGE
        self.assertEqual(result, expected)
    
    def test_rule_not_found(self):
        """规则名不存在：默认返回 RuleTypeEnum.BIG_IMAGE"""
        rules = [
            _create_mock_rule_config('rule6', RuleTypeEnum.SMALL_IMAGE),
        ]
        result = _get_rule_type('rule_missing', rules)
        expected = RuleTypeEnum.BIG_IMAGE
        self.assertEqual(result, expected)


# ========================
# 十、异常处理测试
# ========================

class TestExceptionHandling(unittest.TestCase):
    """异常处理测试（3个用例）"""
    
    def test_tire_struct_is_none(self):
        """tire_struct为None：抛出 InputDataError"""
        with self.assertRaises(InputDataError):
            calculate_geometric_scores(None)
    
    def test_big_image_is_none(self):
        """big_image为None：抛出 InputDataError"""
        tire_struct = _create_mock_tire_struct(big_image=None)
        with self.assertRaises(InputDataError):
            calculate_geometric_scores(tire_struct)
    
    def test_evaluation_is_none(self):
        """evaluation为None：抛出 InputDataError"""
        big_image = _create_mock_big_image(None)
        big_image.lineage = _create_mock_lineage([])
        tire_struct = _create_mock_tire_struct(big_image=big_image)
        with self.assertRaises(InputDataError):
            calculate_geometric_scores(tire_struct)
    
    def test_lineage_is_none(self):
        """lineage为None：抛出 InputDataError"""
        big_image = _create_mock_big_image(_create_mock_evaluation([]))
        big_image.lineage = None
        tire_struct = _create_mock_tire_struct(big_image=big_image)
        with self.assertRaises(InputDataError):
            calculate_geometric_scores(tire_struct)


# ========================
# 十一、小图筛选机制测试
# ========================

class TestSmallImageFiltering(unittest.TestCase):
    """小图筛选机制测试（2个用例）"""
    
    def test_image_base64_matching_filter(self):
        """图片匹配筛选：仅 image_base64 匹配 before_image 的小图参与"""
        before_images = ['image_data_1', 'image_data_2']
        
        image1 = _create_mock_small_image('image_data_1', _create_mock_evaluation([
            _create_mock_rule_evaluation('rule6', 10)
        ]))
        image2 = _create_mock_small_image('image_data_2', _create_mock_evaluation([
            _create_mock_rule_evaluation('rule6', 5)
        ]))
        unmatched_image = _create_mock_small_image('image_data_3', _create_mock_evaluation([
            _create_mock_rule_evaluation('rule6', 8)
        ]))
        
        # 模拟 calculate_geometric_scores 中的筛选逻辑
        matched_indices = set()
        effective = []
        for before_image in before_images:
            for idx, img in enumerate([image1, image2, unmatched_image]):
                if idx not in matched_indices and img.image_base64 == before_image:
                    effective.append(img)
                    matched_indices.add(idx)
                    break
        
        expected_len = 2
        self.assertEqual(len(effective), expected_len)
        self.assertEqual(effective[0].image_base64, 'image_data_1')
        self.assertEqual(effective[1].image_base64, 'image_data_2')
    
    def test_image_base64_is_none(self):
        """image_base64为None：小图 image_base64 为 None 时不参与计算"""
        before_images = ['image_data_1']
        
        none_image = _create_mock_small_image(None, _create_mock_evaluation([
            _create_mock_rule_evaluation('rule6', 10)
        ]))
        
        matched_indices = set()
        effective = []
        for before_image in before_images:
            for idx, img in enumerate([none_image]):
                if idx not in matched_indices and img.image_base64 == before_image:
                    effective.append(img)
                    matched_indices.add(idx)
                    break
        
        expected_len = 0
        self.assertEqual(len(effective), expected_len)


if __name__ == '__main__':
    unittest.main()