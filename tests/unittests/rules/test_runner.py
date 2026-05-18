from src.models.enums import ImageFormatEnum, ImageModeEnum, LevelEnum, RegionEnum
from src.models.image_models import ImageBiz, ImageMeta, SmallImage
from src.models.rule_models import BaseRuleConfig, BaseRuleFeature, BaseRuleScore
from src.rules.runner import RuleRunner


class RulexConfig(BaseRuleConfig):
    description: str = "image op"
    max_score: int = 0


class RulexFeature(BaseRuleFeature):
    value: int


class RulexScore(BaseRuleScore):
    pass


def make_small_image() -> SmallImage:
    return SmallImage(
        image_base64="data:image/png;base64,small",
        meta=ImageMeta(
            width=10,
            height=20,
            channels=3,
            mode=ImageModeEnum.RGB,
            format=ImageFormatEnum.PNG,
            size=5,
        ),
        biz=ImageBiz(level=LevelEnum.SMALL, region=RegionEnum.CENTER),
    )



class RulexExecutor:
    def __init__(self) -> None:
        self.calls = []

    def exec_feature(self, image, config, is_debug=False):
        self.calls.append(("feature", image, config, is_debug))
        return RulexFeature(value=3)

    def exec_score(self, config, feature):
        self.calls.append(("score", config, feature))
        return RulexScore(score=7)



def test_exec_feature_uses_config_name_for_lookup(monkeypatch):
    """验证 RuleRunner.exec_feature 使用 config.name 查找并调用 executor。"""
    executor = RulexExecutor()
    monkeypatch.setattr("src.rules.runner.get_rule_executor", lambda rule_name: executor)
    image = make_small_image()
    config = RulexConfig()

    result = RuleRunner.exec_feature(image, config)

    assert result == RulexFeature(value=3)
    assert executor.calls == [("feature", image, config, False)]


def test_exec_feature_passes_debug_flag(monkeypatch):
    """验证 RuleRunner.exec_feature 会把 debug 开关透传给 executor。"""
    executor = RulexExecutor()
    monkeypatch.setattr("src.rules.runner.get_rule_executor", lambda rule_name: executor)
    image = make_small_image()
    config = RulexConfig()

    result = RuleRunner.exec_feature(image, config, is_debug=True)

    assert result == RulexFeature(value=3)
    assert executor.calls == [("feature", image, config, True)]


def test_exec_score_uses_config_name_for_lookup(monkeypatch):
    """验证 RuleRunner.exec_score 使用 config.name 查找并调用 executor。"""
    executor = RulexExecutor()
    monkeypatch.setattr("src.rules.runner.get_rule_executor", lambda rule_name: executor)
    config = RulexConfig()
    feature = RulexFeature(value=3)

    result = RuleRunner.exec_score(config, feature)

    assert result == RulexScore(score=7)
    assert executor.calls == [("score", config, feature)]
