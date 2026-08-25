#!/usr/bin/env python3
"""
Launch the CNN (ecg_copy) LR x weight_decay grid for one dataset, reading
hyperparameters from configs/cnn/{base,<dataset>}.yaml (via configs/
load_config.py) instead of hand-writing config.json per run like the old
pvc-generalizability/ecg/*_resnet_grid*.py scripts did.

Each (lr, wd) combo becomes one config.json (ecg_copy/train.py's expected
format) + one subprocess run of ecg_copy/ecg/train.py, with
CUDA_VISIBLE_DEVICES pinned per run and jobs queued round-robin across the
given GPUs (one job at a time per GPU).

Usage:
    python scripts/run_cnn_grid.py --dataset MIT_BIH --gpus 4 5
    python scripts/run_cnn_grid.py --dataset INCART --gpus 4 5
"""
import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "configs"))
from load_config import load_config  # noqa: E402

TRAIN_SCRIPT = "/home/melaniem/ecg_copy/ecg/train.py"
WANDB_ENTITY = "melanie-maier-tum-aim"


def build_config_json(cfg: dict, lr: float, wd: float, run_dir: Path) -> Path:
    arch = cfg["architecture"]
    training = cfg["training"]
    params = {
        "save_dir": str(run_dir),
        "generator": True,
        "input_shape": arch["input_shape"],
        "clipnorm": training["clipnorm"],
        "conv_activation": arch["conv_activation"],
        "conv_dropout": arch["conv_dropout"],
        "conv_init": arch["conv_init"],
        "conv_filter_length": arch["conv_filter_length"],
        "conv_num_filters_start": arch["conv_num_filters_start"],
        "conv_subsample_lengths": arch["conv_subsample_lengths"],
        "conv_increase_channels_at": arch["conv_increase_channels_at"],
        "conv_num_skip": arch["conv_num_skip"],
        "is_regular_conv": arch["is_regular_conv"],
        "train": cfg["data"]["train_json"],
        "dev": cfg["data"]["val_json"],
        "learning_rate": lr,
        "batch_size": training["batch_size"],
        "weight_decay": wd,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = run_dir / "config.json"
    cfg_path.write_text(json.dumps(params, indent=2))
    return cfg_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["MIT_BIH", "INCART", "NAKO"], required=True)
    ap.add_argument("--gpus", type=int, nargs="+", required=True)
    ap.add_argument("--wandb", action="store_true", default=True)
    ap.add_argument("--no-wandb", dest="wandb", action="store_false")
    args = ap.parse_args()

    cfg = load_config("cnn", args.dataset)
    lr_grid = cfg["lr_grid"]
    wd_grid = cfg["weight_decay_grid"]
    combos = list(itertools.product(lr_grid, wd_grid))
    print(f"[{args.dataset}] {len(combos)} runs (lr x wd): {combos}")

    configs_dir = REPO_ROOT / "configs" / "cnn"
    runs_root = (configs_dir / cfg["output_dir"]).resolve()  # ../../runs/cnn/<dataset>

    # Convert data paths (relative to configs/cnn/) to absolute paths for
    # config.json, since train.py will be invoked with a different cwd.
    cfg["data"]["train_json"] = str((configs_dir / cfg["data"]["train_json"]).resolve())
    cfg["data"]["val_json"] = str((configs_dir / cfg["data"]["val_json"]).resolve())

    n_gpus = len(args.gpus)
    procs = [None] * n_gpus  # one running process slot per GPU
    queue = list(combos)
    logs = []

    while queue or any(p is not None for p in procs):
        for i in range(n_gpus):
            if procs[i] is not None and procs[i].poll() is not None:
                rc = procs[i].returncode
                print(f"  [gpu {args.gpus[i]}] finished (exit {rc})")
                procs[i] = None
            if procs[i] is None and queue:
                lr, wd = queue.pop(0)
                run_name = f"CNN_{args.dataset}_lr{lr:g}_wd{wd:g}"
                run_dir = runs_root / run_name
                cfg_path = build_config_json(cfg, lr, wd, run_dir)
                log_path = run_dir / "stdout_stderr.log"

                cmd = ["python3", TRAIN_SCRIPT, str(cfg_path), "-e", run_name]
                if args.wandb:
                    cmd += ["--wandb", "--wandb_project", f"cnn-grid-{args.dataset}",
                            "--wandb_entity", WANDB_ENTITY]

                env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(args.gpus[i])}

                print(f"  [gpu {args.gpus[i]}] launching {run_name}")
                log_f = open(log_path, "w")
                logs.append(log_f)
                procs[i] = subprocess.Popen(cmd, cwd="/home/melaniem/ecg_copy/ecg",
                                             env=env, stdout=log_f, stderr=subprocess.STDOUT)
        time.sleep(5)

    for f in logs:
        f.close()
    print(f"[{args.dataset}] all {len(combos)} runs finished")


if __name__ == "__main__":
    main()
