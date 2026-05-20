import pytest
from src.models.rule_models import (
    Rule8Config, Rule8Feature, Rule8Score,
    Rule11Config, Rule11Feature,
    get_feature_class, get_score_class
)

# ===================== 测试数据（模块级常量）=====================

RULE8_CONFIG_DICT = {"description": "横沟数量约束", "max_score": 4, "groove_width_center": 10.0, "groove_width_side": 8.0}

RULE11_CONFIG_DICT = {"description": "test", "max_score": 4, "groove_width": 5.0, "min_width_offset_px": 1, "edge_margin_ratio": 0.1, "min_segment_length_ratio": 0.5, "max_angle_from_vertical": 15.0, "max_count_center": 3, "max_count_side": 2}

RULE17_CONFIG_DICT = {"description": "", "max_score": 6, "continuity_mode_list": []}


# ===================== Field 约束测试 =====================

class TestFieldConstraints:
    """Field 约束测试"""

    def test_rule17_continuity_mode_list_valid(self):
        """✅ 校验 Rule17Config 使用 continuity_mode_list 字段"""
        from src.models.rule_models import Rule17Config
        input_dict = RULE17_CONFIG_DICT
        config = Rule17Config.model_validate(input_dict)
        assert config.continuity_mode_list == []
        assert config.max_score == 6

    def test_rule17_continuity_mode_list_default(self):
        """✅ 校验 Rule17Config 默认 continuity_mode_list 类型为 List[str]"""
        from src.models.rule_models import Rule17Config
        config = Rule17Config.model_validate(RULE17_CONFIG_DICT)
        assert isinstance(config.continuity_mode_list, list)

    def test_rule8_groove_width_valid(self):
        """✅ 校验规则 15：groove_width > 0"""
        input_dict = RULE8_CONFIG_DICT
        expected_dict = {"groove_width_center": 10.0}

        config = Rule8Config.model_validate(input_dict)
        assert config.groove_width_center == expected_dict["groove_width_center"]

    def test_rule8_groove_width_zero(self):
        """❌ 校验规则 15：groove_width = 0"""
        input_dict = {**RULE8_CONFIG_DICT, "groove_width_center": 0}

        with pytest.raises(ValueError):
            Rule8Config.model_validate(input_dict)


# ===================== name 属性自动提取测试 =====================

class TestRuleNameExtraction:
    """规则 name 属性自动提取测试"""

    def test_config_name_rule8(self):
        """Rule8Config.name == "rule8" """
        input_dict = RULE8_CONFIG_DICT
        expected_dict = {"name": "rule8"}

        config = Rule8Config.model_validate(input_dict)
        assert config.name == expected_dict["name"]

    def test_feature_name_rule8(self):
        """Rule8Feature.name == "rule8" """
        input_dict = {"num_transverse_grooves": 5}
        expected_dict = {"name": "rule8"}

        feature = Rule8Feature.model_validate(input_dict)
        assert feature.name == expected_dict["name"]

    def test_config_name_rule11(self):
        """Rule11Config.name == "rule11" """
        input_dict = RULE11_CONFIG_DICT
        expected_dict = {"name": "rule11"}

        config = Rule11Config.model_validate(input_dict)
        assert config.name == expected_dict["name"]

    def test_no_name_field_in_config(self):
        """Config 类不应手动定义 name 字段"""
        expected_dict = {"has_name_field": False, "name_is_property": True}

        assert ('name' in Rule8Config.model_fields) == expected_dict["has_name_field"]
        assert isinstance(Rule8Config.name, property) == expected_dict["name_is_property"]

    def test_no_name_field_in_feature(self):
        """Feature 类不应手动定义 name 字段"""
        expected_dict = {"has_name_field": False, "name_is_property": True}

        assert ('name' in Rule8Feature.model_fields) == expected_dict["has_name_field"]
        assert isinstance(Rule8Feature.name, property) == expected_dict["name_is_property"]


# ===================== 注册机制测试 =====================

class TestRuleRegistry:
    """规则注册机制测试"""

    def test_get_feature_class_rule8(self):
        """根据规则名获取 Rule8Feature"""
        expected_dict = {"class": Rule8Feature}
        feature_cls = get_feature_class("rule8")
        assert feature_cls == expected_dict["class"]

    def test_get_feature_class_not_found(self):
        """获取不存在的 Feature 类"""
        expected_dict = {"result": None}
        feature_cls = get_feature_class("rule999")
        assert feature_cls == expected_dict["result"]

    def test_get_score_class_rule8(self):
        """根据规则名获取 Rule8Score"""
        expected_dict = {"class": Rule8Score}
        score_cls = get_score_class("rule8")
        assert score_cls == expected_dict["class"]

    def test_dynamic_instantiation(self):
        """动态获取类并实例化"""
        feature_cls = get_feature_class("rule8")
        input_dict = {"num_transverse_grooves": 5}
        expected_dict = {"num_transverse_grooves": 5}

        feature = feature_cls.model_validate(input_dict)
        assert feature.num_transverse_grooves == expected_dict["num_transverse_grooves"]
