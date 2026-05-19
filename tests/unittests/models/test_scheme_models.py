import pytest
from src.models.scheme_models import RibTemplate, Symmetry0, RibSchemeImpl, DecorationImpl
from src.models.enums import RibOperation


# ===================== 模板类 frozen 测试 =====================

class TestTemplateFrozen:
    """模板类 frozen 测试"""

    def test_rib_template_frozen(self):
        """RibTemplate 不可修改"""
        input_dict = {"region": "side", "operation_template": [""], "rib_name": "rib1"}

        rib = RibTemplate.model_validate(input_dict)
        with pytest.raises(Exception):
            rib.region = "center"

    def test_symmetry0_frozen(self):
        """Symmetry0 不可修改"""
        template = Symmetry0()
        with pytest.raises(Exception):
            template.rib_number = 10


# ===================== RibSchemeImpl 校验规则测试 =====================

class TestRibSchemeImplValidation:
    """RibSchemeImpl 校验规则测试"""

    def test_validate_name_required_top_level_with_name(self):
        """✅ 校验规则 11：有 rib_name 时正常"""
        input_dict = {"rib_source": "side", "rib_operation": (RibOperation.NONE,), "rib_name": "rib1"}

        rib = RibSchemeImpl.model_validate(input_dict)
        assert rib.rib_name == "rib1"

    def test_validate_name_required_top_level_without_name(self):
        """❌ 校验规则 11：没有 rib_name 时抛错"""
        input_dict = {"rib_source": "side", "rib_operation": (RibOperation.NONE,)}

        with pytest.raises(ValueError, match="最外层 RIB 必须有 rib_name"):
            RibSchemeImpl.model_validate(input_dict)

    def test_validate_name_nested_without_name(self):
        """✅ 校验规则 11：嵌套 RibSchemeImpl 同样需要 rib_name"""
        # RibSchemeImpl 通过 rib_operation 嵌套另一个 RibSchemeImpl
        sub_rib = RibSchemeImpl(rib_source="side", rib_operation=(RibOperation.NONE,), rib_name="nested_rib")
        parent_rib = RibSchemeImpl(
            rib_source="center",
            rib_operation=(sub_rib,),
            rib_name="parent_rib",
        )
        assert parent_rib.rib_name == "parent_rib"
        nested = parent_rib.rib_operation[0]
        assert isinstance(nested, RibSchemeImpl)
        assert nested.rib_name == "nested_rib"

    def test_validate_inherit_with_reference(self):
        """✅ 校验规则 12：rib_same_as 有值时正常"""
        input_dict = {
            "rib_source": "side",
            "rib_operation": (RibOperation.FLIP,),
            "rib_name": "rib5",
            "rib_same_as": "rib1",
        }

        rib = RibSchemeImpl.model_validate(input_dict)
        assert rib.rib_same_as == "rib1"

    def test_validate_inherit_without_reference(self):
        """✅ 校验规则 12：rib_same_as 默认为 None"""
        input_dict = {"rib_source": "side", "rib_operation": (RibOperation.FLIP,), "rib_name": "rib5"}

        rib = RibSchemeImpl.model_validate(input_dict)
        assert rib.rib_same_as is None


# ===================== RibSchemeImpl 可变性测试 =====================

class TestRibSchemeImplMutability:
    """RibSchemeImpl 可变性测试（validate_assignment=True）"""

    def test_runtime_fill_fields(self):
        """运行时填充字段"""
        input_dict = {"rib_source": "original", "rib_operation": (RibOperation.NONE,), "rib_name": "rib1"}
        expected_dict = {"before_image": "base64_data", "num_pitchs": 10, "rib_height": 100}

        rib = RibSchemeImpl.model_validate(input_dict)
        rib.before_image = expected_dict["before_image"]
        rib.num_pitchs = expected_dict["num_pitchs"]
        rib.rib_height = expected_dict["rib_height"]

        assert rib.before_image == expected_dict["before_image"]
        assert rib.num_pitchs == expected_dict["num_pitchs"]
        assert rib.rib_height == expected_dict["rib_height"]


# ===================== DecorationImpl 校验规则测试 =====================

class TestDecorationImplValidation:
    """DecorationImpl 校验规则测试"""

    def test_decoration_opacity_min(self):
        """✅ 校验规则 13：decoration_opacity = 0"""
        input_dict = {"decoration_opacity": 0, "decoration_width": 100, "decoration_height": 100}
        expected_dict = {"decoration_opacity": 0}

        impl = DecorationImpl.model_validate(input_dict)
        assert impl.decoration_opacity == expected_dict["decoration_opacity"]

    def test_decoration_opacity_max(self):
        """✅ 校验规则 13：decoration_opacity = 255"""
        input_dict = {"decoration_opacity": 255, "decoration_width": 100, "decoration_height": 100}
        expected_dict = {"decoration_opacity": 255}

        impl = DecorationImpl.model_validate(input_dict)
        assert impl.decoration_opacity == expected_dict["decoration_opacity"]

    def test_decoration_opacity_under(self):
        """❌ 校验规则 13：decoration_opacity = -1"""
        input_dict = {"decoration_opacity": -1, "decoration_width": 100, "decoration_height": 100}

        with pytest.raises(ValueError):
            DecorationImpl.model_validate(input_dict)

    def test_decoration_opacity_over(self):
        """❌ 校验规则 13：decoration_opacity = 256"""
        input_dict = {"decoration_opacity": 256, "decoration_width": 100, "decoration_height": 100}

        with pytest.raises(ValueError):
            DecorationImpl.model_validate(input_dict)
