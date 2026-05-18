# ============================================================
# TireStruct - 接入层
#
# 轮胎图像全流程统一数据结构
# 开启 validate_assignment=True 支持运行时赋值校验
# ============================================================

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator

from .image_models import SmallImage, BigImage
from .rule_models import BaseRuleConfig


class TireStruct(BaseModel):
    """
    轮胎图像全流程统一数据结构

    所有Pipeline的输入和输出都使用这个结构。
    每个字段标注了在哪个流程生效、是入参还是出参。
    开启validate_assignment确保运行时赋值的合法性。
    """

    model_config = ConfigDict(validate_assignment=True)

    # ===================== 图像数据 =====================
    # 小图列表
    # 👉 入参：仅Pipeline-1使用
    # 👉 出参：仅Pipeline-4输出
    small_images: List[SmallImage] = Field(default_factory=list, description="小图列表，含特征/评分")

    # 大图（包含血缘、特征、评分）
    # 👉 入参：Pipeline-2 / Pipeline-3 / Pipeline-4使用
    # 👉 出参：Pipeline-1 / Pipeline-2 / Pipeline-3输出
    big_image: Optional[BigImage] = Field(default=None, description="大图，含血缘/特征/评分")

    # ===================== 业务规则与配置 =====================
    # 规则配置列表（评分规则/拆分规则/拼接规则）
    # 👉 入参：Pipeline-1 / Pipeline-3 / Pipeline-4使用
    rules_config: List[BaseRuleConfig] = Field(default_factory=list, description="规则配置列表")

    # 方案排名（第几名方案）
    # 👉 入参：仅Pipeline-1使用
    scheme_rank: Optional[int] = Field(default=None, description="方案排名，从1开始")

    # ===================== 执行结果与状态 =====================
    # 调试开关
    is_debug: bool = Field(default=False, description="调试开关，开启后输出可视化中间结果")

    # 执行成功/失败标志
    # 👉 出参：所有Pipeline统一输出
    flag: Optional[bool] = Field(default=None, description="执行成功/失败标志")

    # 错误/拒绝原因
    # 👉 出参：所有Pipeline统一输出
    err_msg: Optional[str] = Field(default=None, description="错误或拒绝原因")

    @model_validator(mode="after")
    def _validate_images_required(self) -> TireStruct:
        """私有校验：必须有小图或大图至少一种"""
        has_small = len(self.small_images) > 0
        has_big = self.big_image is not None
        if not has_small and not has_big:
            raise ValueError("必须输入小图或大图，流程无法执行")
        return self

    @model_validator(mode="after")
    def _validate_scheme_rank(self) -> TireStruct:
        """私有校验：方案排名必须>=1"""
        if self.scheme_rank is not None and self.scheme_rank < 1:
            raise ValueError("方案排名必须>=1")
        return self
