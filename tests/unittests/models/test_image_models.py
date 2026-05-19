import pytest
from src.models.enums import RegionEnum
from src.models.image_models import SmallImage, ImageMeta, ImageBiz, ImageEvaluation, RuleEvaluation

# ===================== 测试数据（模块级常量）=====================

META_DICT = {"width": 512, "height": 512, "channels": 3, "mode": "RGB", "format": "png", "size": 10000}

BIZ_DICT = {"level": "small", "region": "side", "source_type": "original"}

SMALL_IMAGE_DICT = {"image_base64": "data:image/png;base64,xxx", "meta": META_DICT, "biz": BIZ_DICT}

RULE8_CONFIG_DICT = {"description": "test", "max_score": 4, "groove_width_center": 10.0, "groove_width_side": 8.0}

RULE11_CONFIG_DICT = {"description": "test", "max_score": 4, "groove_width": 5.0, "min_width_offset_px": 1, "edge_margin_ratio": 0.1, "min_segment_length_ratio": 0.5, "max_angle_from_vertical": 15.0, "max_count_center": 3, "max_count_side": 2}


# ===================== ImageMeta 校验规则测试 =====================

class TestImageMetaValidation:
    """ImageMeta 校验规则测试"""

    def test_field_constraints_width_valid(self):
        """✅ 校验规则 4：width = 1"""
        input_dict = {**META_DICT, "width": 1}
        expected_dict = {"width": 1}

        meta = ImageMeta.model_validate(input_dict)
        assert meta.width == expected_dict["width"]

    def test_field_constraints_width_zero(self):
        """❌ 校验规则 4：width = 0"""
        input_dict = {**META_DICT, "width": 0}

        with pytest.raises(ValueError):
            ImageMeta.model_validate(input_dict)

    def test_field_constraints_channels_min(self):
        """✅ 校验规则 5：channels = 1"""
        input_dict = {**META_DICT, "channels": 1, "mode": "GRAY"}
        expected_dict = {"channels": 1}

        meta = ImageMeta.model_validate(input_dict)
        assert meta.channels == expected_dict["channels"]

    def test_field_constraints_channels_max(self):
        """✅ 校验规则 5：channels = 4"""
        input_dict = {**META_DICT, "channels": 4, "mode": "RGBA"}
        expected_dict = {"channels": 4}

        meta = ImageMeta.model_validate(input_dict)
        assert meta.channels == expected_dict["channels"]

    def test_field_constraints_channels_rgb(self):
        """✅ 校验规则 5：channels = 3 (RGB)"""
        input_dict = {**META_DICT, "channels": 3, "mode": "RGB"}
        expected_dict = {"channels": 3}

        meta = ImageMeta.model_validate(input_dict)
        assert meta.channels == expected_dict["channels"]

    def test_field_constraints_channels_zero(self):
        """❌ 校验规则 5：channels = 0"""
        input_dict = {**META_DICT, "channels": 0}

        with pytest.raises(ValueError):
            ImageMeta.model_validate(input_dict)

    def test_field_constraints_channels_five(self):
        """❌ 校验规则 5：channels = 5 超出范围"""
        input_dict = {**META_DICT, "channels": 5}

        with pytest.raises(ValueError):
            ImageMeta.model_validate(input_dict)

    def test_model_validator_dimensions_at_limit(self):
        """✅ 校验规则 6：width = 10000"""
        input_dict = {**META_DICT, "width": 10000}
        expected_dict = {"width": 10000}

        meta = ImageMeta.model_validate(input_dict)
        assert meta.width == expected_dict["width"]

    def test_model_validator_dimensions_over(self):
        """❌ 校验规则 6：width = 10001"""
        input_dict = {**META_DICT, "width": 10001}

        with pytest.raises(ValueError, match="图像尺寸超过上限10000像素"):
            ImageMeta.model_validate(input_dict)


# ===================== ImageBiz 校验规则测试 =====================

class TestImageBizValidation:
    """ImageBiz 校验规则测试"""

    def test_validate_region_for_original_with_region(self):
        """✅ 校验规则 7：原始数据有 region"""
        input_dict = {"level": "small", "region": "side", "source_type": "original"}
        expected_dict = {"region": "side"}

        biz = ImageBiz.model_validate(input_dict)
        assert biz.region.value == expected_dict["region"]

    def test_validate_region_for_original_without_region(self):
        """❌ 校验规则 7：原始数据没有 region"""
        input_dict = {"level": "small", "region": None, "source_type": "original"}

        with pytest.raises(ValueError, match="原始数据必须指定region"):
            ImageBiz.model_validate(input_dict)

    def test_validate_inherit_with_reference(self):
        """✅ 校验规则 8：继承来源有 inherit_from"""
        input_dict = {"level": "big", "source_type": "inherit", "inherit_from": "rib1"}
        expected_dict = {"inherit_from": "rib1"}

        biz = ImageBiz.model_validate(input_dict)
        assert biz.inherit_from == expected_dict["inherit_from"]

    def test_validate_inherit_without_reference(self):
        """❌ 校验规则 8：继承来源没有 inherit_from"""
        input_dict = {"level": "big", "source_type": "inherit", "inherit_from": None}

        with pytest.raises(ValueError, match="继承来源必须指定inherit_from"):
            ImageBiz.model_validate(input_dict)


# ===================== BaseImage 校验规则测试 =====================

class TestBaseImageValidation:
    """BaseImage 校验规则测试"""

    def test_validate_base64_format_valid(self):
        """✅ 校验规则 3：包含 data:image/ 前缀"""
        input_dict = SMALL_IMAGE_DICT
        expected_dict = {"has_prefix": True}

        image = SmallImage.model_validate(input_dict)
        assert image.image_base64.startswith("data:image/") == expected_dict["has_prefix"]

    def test_validate_base64_format_jpeg(self):
        """✅ 校验规则 3：包含 data:image/jpeg 前缀"""
        input_dict = {**SMALL_IMAGE_DICT, "image_base64": "data:image/jpeg;base64,/9j/4AAQ"}
        expected_dict = {"has_prefix": True}

        image = SmallImage.model_validate(input_dict)
        assert image.image_base64.startswith("data:image/") == expected_dict["has_prefix"]

    def test_validate_base64_format_invalid(self):
        """❌ 校验规则 3：缺少 data:image/ 前缀"""
        input_dict = {**SMALL_IMAGE_DICT, "image_base64": "invalid"}

        with pytest.raises(ValueError, match="image_base64必须包含data:image"):
            SmallImage.model_validate(input_dict)

    def test_validate_base64_format_missing_prefix(self):
        """❌ 校验规则 3：缺少 data:image/ 前缀，但有 base64 内容"""
        input_dict = {**SMALL_IMAGE_DICT, "image_base64": "iVBORw0KGgo="}

        with pytest.raises(ValueError, match="image_base64必须包含data:image"):
            SmallImage.model_validate(input_dict)

    def test_validate_base64_format_wrong_prefix(self):
        """❌ 校验规则 3：错误的前缀格式"""
        input_dict = {**SMALL_IMAGE_DICT, "image_base64": "data:video/mp4;base64,xxx"}

        with pytest.raises(ValueError, match="image_base64必须包含data:image"):
            SmallImage.model_validate(input_dict)


# ===================== ImageEvaluation 校验规则测试 =====================

class TestImageEvaluationValidation:
    """ImageEvaluation 校验规则测试"""

    def test_validate_unique_names_valid(self):
        """✅ 校验规则 9：名称不重复"""
        input_dict = {"rules": [{"name": "rule8", "config": RULE8_CONFIG_DICT}, {"name": "rule11", "config": RULE11_CONFIG_DICT}]}
        expected_dict = {"rules_count": 2}

        evaluation = ImageEvaluation.model_validate(input_dict)
        assert len(evaluation.rules) == expected_dict["rules_count"]

    def test_validate_unique_names_duplicate(self):
        """❌ 校验规则 9：名称重复"""
        input_dict = {"rules": [{"name": "rule8", "config": RULE8_CONFIG_DICT}, {"name": "rule8", "config": RULE8_CONFIG_DICT}]}

        with pytest.raises(ValueError, match="规则名称不能重复"):
            ImageEvaluation.model_validate(input_dict)


class TestImageEvaluationMethods:
    """ImageEvaluation 方法测试"""

    def test_set_score_updates_total(self):
        """设置评分后自动更新总分"""
        from src.models.rule_models import Rule8Score, Rule11Score
        input_dict = {"rules": [{"name": "rule8", "config": RULE8_CONFIG_DICT}, {"name": "rule11", "config": RULE11_CONFIG_DICT}]}
        expected_dict = {"current_score": 7}

        evaluation = ImageEvaluation.model_validate(input_dict)
        evaluation.set_score("rule8", Rule8Score(score=4))
        evaluation.set_score("rule11", Rule11Score(score=3))

        assert evaluation.current_score == expected_dict["current_score"]


# ===================== RuleEvaluation 校验规则测试 =====================

class TestRuleEvaluationValidation:
    """RuleEvaluation 校验规则测试"""

    def test_validate_name_consistency_valid(self):
        """✅ 校验规则 10：feature 和 score 名称一致"""
        from src.models.rule_models import Rule8Config, Rule8Feature, Rule8Score
        input_dict = {"name": "rule8", "config": RULE8_CONFIG_DICT}
        expected_dict = {"name": "rule8"}

        evaluation = RuleEvaluation.model_validate(input_dict)
        # 运行时赋值子类实例，name 从子类类名自动提取
        evaluation.feature = Rule8Feature(num_transverse_grooves=5)
        evaluation.score = Rule8Score(score=4)
        assert evaluation.name == expected_dict["name"]

    def test_validate_name_consistency_feature_mismatch(self):
        """❌ 校验规则 10：feature 名称不一致"""
        from src.models.rule_models import Rule11Feature
        input_dict = {"name": "rule8", "config": RULE8_CONFIG_DICT}

        evaluation = RuleEvaluation.model_validate(input_dict)
        with pytest.raises(ValueError, match="feature.name"):
            evaluation.feature = Rule11Feature(num_longitudinal_grooves=3, region=RegionEnum.CENTER)

    def test_validate_name_consistency_score_mismatch(self):
        """❌ 校验规则 10：score 名称不一致"""
        from src.models.rule_models import Rule11Score
        input_dict = {"name": "rule8", "config": RULE8_CONFIG_DICT}

        evaluation = RuleEvaluation.model_validate(input_dict)
        with pytest.raises(ValueError, match="score.name"):
            evaluation.score = Rule11Score(score=3)
