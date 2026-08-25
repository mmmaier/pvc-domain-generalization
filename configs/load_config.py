#!/usr/bin/env python3
"""
Resolve a model/dataset config by deep-merging its `extends: base.yaml`
parent into the per-dataset override file. Used by training launchers
(not yet written) so hyperparameters live in one place instead of being
hardcoded per run script.

Usage:
    python load_config.py --model cnn --dataset NAKO
    python load_config.py --model otis --dataset MIT_BIH
"""
import argparse
from pathlib import Path

import yaml

CONFIG_ROOT = Path(__file__).parent


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, val in override.items():
        if key == "extends":
            continue
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def load_config(model: str, dataset: str) -> dict:
    cfg_dir = CONFIG_ROOT / model
    override_path = cfg_dir / f"{dataset}.yaml"
    override = yaml.safe_load(override_path.read_text())

    base_name = override.get("extends")
    if base_name:
        base = yaml.safe_load((cfg_dir / base_name).read_text())
        return deep_merge(base, override)
    return override


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["cnn", "otis"], required=True)
    ap.add_argument("--dataset", choices=["NAKO", "MIT_BIH", "INCART"], required=True)
    args = ap.parse_args()

    cfg = load_config(args.model, args.dataset)
    print(yaml.dump(cfg, sort_keys=False))


if __name__ == "__main__":
    main()
