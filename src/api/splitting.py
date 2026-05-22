"""Splitting pipeline entrypoint."""

from __future__ import annotations

from src.models.tire_struct import TireStruct
from src.piplines.pipline4 import run_pipeline4


def run_splitting_pipeline(input_data: TireStruct) -> TireStruct:
    """Run the splitting pipeline through node-level orchestration."""

    return run_pipeline4(input_data)
