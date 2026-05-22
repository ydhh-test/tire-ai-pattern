from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from scripts.test_integrations_pipline4_to_pipline1 import run_pipeline4_to_pipeline1_case


def test_pipeline4_to_pipeline1_writes_visible_artifacts():
    output_dir = Path(".results/pipeline4_to_pipeline1/testcase_001")

    manifest = run_pipeline4_to_pipeline1_case(output_dir=output_dir)

    assert manifest["pipeline4"]["flag"] is True
    assert manifest["pipeline4"]["small_image_count"] == 5
    assert manifest["pipeline4"]["regions"] == ["side", "side", "center", "center", "center"]
    assert manifest["pipeline1"]["flag"] is True
    assert len(manifest["pipeline1"]["ranked_big_image_paths"]) == 20
    assert manifest["pipeline1"]["ranked_big_image_paths"][0].endswith("rank_01_big_image.png")
    assert manifest["pipeline1"]["ranked_big_image_paths"][-1].endswith("rank_20_big_image.png")
    assert manifest["pipeline1"]["config_summary"]["rib_widths"] == [577, 126, 126, 126, 577]
    assert manifest["pipeline1"]["config_summary"]["groove_widths"] == [53, 58, 58, 53]
    assert manifest["pipeline1"]["config_summary"]["decoration_widths"] == [239, 239]
    assert manifest["pipeline1"]["config_summary"]["symmetry_rules"] == ["rule1", "rule2", "rule3"]
    assert manifest["pipeline1"]["config_summary"]["continuity_modes"] == [
        "continuity_0",
        "continuity_1",
        "continuity_2",
    ]
    assert Path(manifest["manifest_path"]).exists()
    assert all(Path(path).exists() for path in manifest["pipeline4"]["small_image_paths"])
    assert all(Path(path).exists() for path in manifest["pipeline1"]["ranked_big_image_paths"])
    assert all(
        _load_image_width(Path(path)) == manifest["pipeline1"]["config_summary"]["target_width"]
        for path in manifest["pipeline1"]["ranked_big_image_paths"]
    )


def _load_image_width(path: Path) -> int:
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    return image.shape[1]
