"""Reference configs for pipeline1 (test copy, version-controlled).

Each file is a standalone config module exporting CONFIG (dict) and tire_struct.
Import via prefixed name, e.g.:
    from tests.datasets.ref_configs import cfg_5rib_sym0_no_cont
    result = run_pipeline1(cfg_5rib_sym0_no_cont.tire_struct)

This is a real copy (not a symlink) — tested on each commit to prevent accidental breakage.
Users should modify example/ref_configs/ as reference, not this directory.
"""

import importlib as _importlib

_MODULES = [
    "5rib_sym0_no_cont",
    "5rib_sym1_no_cont",
    "5rib_sym2_no_cont",
    "5rib_sym0_cont1",
    "5rib_sym1_cont1",
    "5rib_sym2_cont2",
    "4rib_sym4_no_cont",
    "4rib_sym4_sym5_no_cont",
    "4rib_sym456_no_cont",
    "4rib_sym456_cont3",
    "4rib_sym456_cont123_bad",
]

for _name in _MODULES:
    _mod = _importlib.import_module(f"tests.datasets.ref_configs.{_name}")
    globals()[f"cfg_{_name}"] = _mod
