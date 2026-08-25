#!/usr/bin/env python3
"""
Convert PVC beat-window HDF5 shards (NAKO / MIT_BIH / INCART, under
data_hdf5/) into the three input formats used across this project's model
paradigms:

  - CNN     : {split}_signals.npy (float32, [N, 1280], memmap-friendly)
              + {split}.json      (JSONL: index, labels, record_id)
              Consumed by ecg_copy/ecg/load.py (8 stride-2 residual blocks
              need a length divisible by 256). That loader also crops to
              1280 itself, but the array it receives is already 1280-long
              here, so that's a harmless no-op -- the crop is enforced once,
              in this script, rather than depending on a pinned baseline
              loader to keep doing it correctly.

  - OTiS    : {split}_data.pt / {split}_labels.pt / {split}_ids.pt
              list of ("ECG", tensor) tuples, tensor shape (1, 1280);
              one-hot float labels; int64 record/study ids.

  - RRM-XGB : {dataset}_{split}_rrm.parquet
              one row per beat: dataset, split, record_id, beat_index,
              label, qrs_position, the eight rr_* interval fields already
              present in the shards, and the 1280-sample ecg window (as a
              float32 list column) so wavelet-morphology descriptors can be
              computed later straight from this table without going back to
              the HDF5 shards. ("RRM" = RR-interval + Morphology.)

All three formats are derived from the same in-memory arrays in a single
pass over the shards, so there is no risk of the three model paradigms
silently seeing different beats/labels.

HDF5 shards store 1281 raw samples per beat (+-2.5s at 256Hz, R-peak at
0-indexed sample 640 -- see the 'r_index_python' attr on each shard). All
three formats are cropped to the same 1280 samples (indices 0:1280 of the
raw window, i.e. the last raw sample is dropped) right here, so every
downstream consumer sees an identical, fixed-length window.

Dataset layout on disk (see DATASET_CONFIGS below):
  - NAKO      : one zip per split-batch, flat members (nako_*.h5),
                id field 'study_id'. 'test' has no zip yet (pending export).
  - MIT_BIH   : single zip, members under MIT_BIH/{split}/*.h5,
                id field 'record_id'.
  - INCART    : single zip, members under INCART/{split}/*.h5,
                id field 'record_id'.

This script only WRITES converted files; it does not read/write the
patient-level split CSVs (incart_patient_split.csv, mitbih_patient_split.csv,
NAKO_demographics_patient_level.csv) -- the HDF5 shards are already
pre-split (train/validation/test) at export time.
"""
import argparse
import json
import shutil
import zipfile
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import torch

RAW_LEN = 1281
CROP_LEN = 1280  # samples used by CNN/OTiS; drop the last raw sample
SPLITS = ("train", "validation", "test")

RR_FIELDS = [
    "rr_m1_samples", "rr_m1_seconds",
    "rr_m2_samples", "rr_m2_seconds",
    "rr_p1_samples", "rr_p1_seconds",
    "rr_p2_samples", "rr_p2_seconds",
]

DATA_ROOT = Path("/home/melaniem/data_hdf5")

# Explicit, per-dataset knowledge of where each split's shards live.
# Extend the lists here as new zips are exported (e.g. NAKO test, or
# additional NAKO validation batches) -- no other code needs to change.
DATASET_CONFIGS = {
    "NAKO": {
        "id_field": "study_id",
        # Directories, not explicit filenames: NAKO drops one zip per
        # split-batch (e.g. more val shards may be added to val/ before a
        # run) -- every *.zip found under the split folder is picked up
        # automatically, so this config doesn't need editing again.
        "split_zips": {
            "train": DATA_ROOT / "NAKO/train",
            "validation": DATA_ROOT / "NAKO/val",
            "test": DATA_ROOT / "NAKO/test",  # not yet exported -- run separately later, not needed for first training loop
        },
        "member_prefix": {"train": None, "validation": None, "test": None},
    },
    "MIT_BIH": {
        "id_field": "record_id",
        "split_zips": {
            "train": [DATA_ROOT / "MIT_BIH/MIT_BIH.zip"],
            "validation": [DATA_ROOT / "MIT_BIH/MIT_BIH.zip"],
            "test": [DATA_ROOT / "MIT_BIH/MIT_BIH.zip"],
        },
        "member_prefix": {
            "train": "MIT_BIH/train/",
            "validation": "MIT_BIH/validation/",
            "test": "MIT_BIH/test/",
        },
    },
    "INCART": {
        "id_field": "record_id",
        "split_zips": {
            "train": [DATA_ROOT / "INCART/INCART.zip"],
            "validation": [DATA_ROOT / "INCART/INCART.zip"],
            "test": [DATA_ROOT / "INCART/INCART.zip"],
        },
        "member_prefix": {
            "train": "INCART/train/",
            "validation": "INCART/validation/",
            "test": "INCART/test/",
        },
    },
}


def shard_names(zip_path: Path, prefix: str | None) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        names = (n for n in zf.namelist() if n.endswith(".h5"))
        if prefix is not None:
            names = (n for n in names if n.startswith(prefix))
        return sorted(names)


def resolve_zip_paths(entry) -> list[Path]:
    """entry is either an explicit list of zip Paths, or a directory Path
    that gets globbed for every *.zip inside it (NAKO's convention, where
    new split batches are dropped in as additional zips over time)."""
    if isinstance(entry, Path):
        if not entry.is_dir():
            return []
        return sorted(entry.glob("*.zip"))
    return list(entry)


def resolve_targets(dataset: str, split: str) -> list[tuple[Path, str]]:
    cfg = DATASET_CONFIGS[dataset]
    prefix = cfg["member_prefix"][split]
    targets = []
    for zp in resolve_zip_paths(cfg["split_zips"][split]):
        if not zp.exists():
            print(f"  [warn] zip not found, skipping: {zp}")
            continue
        for member in shard_names(zp, prefix):
            targets.append((zp, member))
    return targets


def load_shard(zip_path: Path, member: str, id_field: str, tmp_dir: Path):
    """Extracts one shard to tmp_dir, reads its arrays, deletes the file."""
    local_path = tmp_dir / Path(member).name
    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as src, open(local_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    try:
        with h5py.File(local_path, "r") as f:
            ecg = f["ecg"][:]                       # (n, 1281) float32
            label = f["label"][:, 0]                # (n,) uint8
            record_id = f[id_field][:, 0]           # (n,) int64
            beat_index = f["beat_index"][:, 0]      # (n,) int32
            qrs_position = f["qrs_position"][:, 0]  # (n,) int64
            rr = {k: f[k][:, 0] for k in RR_FIELDS}
    finally:
        local_path.unlink()
    return ecg, label, record_id, beat_index, qrs_position, rr


def convert(dataset: str, split: str, cnn_out: Path, otis_out: Path, rrm_out: Path,
            tmp_dir: Path, max_shards: int | None):
    targets = resolve_targets(dataset, split)
    if max_shards is not None:
        targets = targets[:max_shards]

    if not targets:
        print(f"[{dataset}/{split}] no shards found -- skipping (nothing exported yet?)")
        return

    print(f"[{dataset}/{split}] {len(targets)} shard(s)")

    ecg_chunks, label_chunks, id_chunks = [], [], []
    beat_idx_chunks, qrs_chunks = [], []
    rr_chunks = {k: [] for k in RR_FIELDS}

    for i, (zp, member) in enumerate(targets, 1):
        print(f"  [{i}/{len(targets)}] {zp.name}:{member}")
        ecg, label, record_id, beat_index, qrs_position, rr = load_shard(
            zp, member, DATASET_CONFIGS[dataset]["id_field"], tmp_dir)
        if ecg.shape[1] != RAW_LEN:
            raise ValueError(f"{member}: expected {RAW_LEN} samples, got {ecg.shape[1]}")
        ecg_chunks.append(ecg)
        label_chunks.append(label)
        id_chunks.append(record_id)
        beat_idx_chunks.append(beat_index)
        qrs_chunks.append(qrs_position)
        for k in RR_FIELDS:
            rr_chunks[k].append(rr[k])

    ecg_all = np.concatenate(ecg_chunks, axis=0)
    label_all = np.concatenate(label_chunks, axis=0).astype(np.int64)
    id_all = np.concatenate(id_chunks, axis=0).astype(np.int64)
    beat_idx_all = np.concatenate(beat_idx_chunks, axis=0).astype(np.int64)
    qrs_all = np.concatenate(qrs_chunks, axis=0).astype(np.int64)
    rr_all = {k: np.concatenate(v, axis=0) for k, v in rr_chunks.items()}
    n = ecg_all.shape[0]
    print(f"[{dataset}/{split}] total beats: {n:,} (pos={int(label_all.sum()):,})")

    # Crop once, here, to CROP_LEN (drops the last raw sample) -- every
    # format below shares this exact array, so there's a single place that
    # decides the window length instead of three.
    ecg_all = np.ascontiguousarray(ecg_all[:, :CROP_LEN])

    # ---- CNN format ----
    cnn_out.mkdir(parents=True, exist_ok=True)
    np.save(cnn_out / f"{split}_signals.npy", ecg_all)
    with open(cnn_out / f"{split}.json", "w") as f:
        for i in range(n):
            f.write(json.dumps({
                "index": i,
                "labels": [str(int(label_all[i]))],
                "record_id": int(id_all[i]),
            }) + "\n")
    print(f"[{dataset}/{split}] CNN format written to {cnn_out}")

    # ---- OTiS format ----
    otis_out.mkdir(parents=True, exist_ok=True)
    ecg_torch = torch.from_numpy(ecg_all)
    data_list = [("ECG", ecg_torch[i].unsqueeze(0)) for i in range(n)]
    labels_onehot = torch.nn.functional.one_hot(
        torch.from_numpy(label_all), num_classes=2
    ).float()
    torch.save(data_list, otis_out / f"{split}_data.pt")
    torch.save(labels_onehot, otis_out / f"{split}_labels.pt")
    torch.save(torch.from_numpy(id_all), otis_out / f"{split}_ids.pt")
    print(f"[{dataset}/{split}] OTiS format written to {otis_out}")

    # ---- RRM-XGB format: one table, cropped 1280-sample window kept ----
    rrm_out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({
        "dataset": dataset,
        "split": split,
        "record_id": id_all,
        "beat_index": beat_idx_all,
        "label": label_all,
        "qrs_position": qrs_all,
        **rr_all,
        "ecg": list(ecg_all),
    })
    parquet_path = rrm_out / f"{dataset}_{split}_rrm.parquet"
    df.to_parquet(parquet_path, engine="pyarrow", index=False)
    print(f"[{dataset}/{split}] RRM-XGB format written to {parquet_path}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", choices=list(DATASET_CONFIGS) + ["all"], required=True)
    ap.add_argument("--split", choices=list(SPLITS) + ["all"], required=True)
    ap.add_argument("--cnn_root", type=Path,
                     default=Path("/home/melaniem/pvc-domain-generalization/cnn_data"))
    ap.add_argument("--otis_root", type=Path,
                     default=Path("/home/melaniem/pvc-domain-generalization/otis_data"))
    ap.add_argument("--rrm_root", type=Path,
                     default=Path("/home/melaniem/pvc-domain-generalization/rrm_data"))
    ap.add_argument("--tmp_dir", type=Path,
                     default=Path("/tmp/hdf5_shard_extract"))
    ap.add_argument("--max_shards", type=int, default=None,
                     help="Only process the first N shards per dataset/split (quick test run)")
    args = ap.parse_args()

    args.tmp_dir.mkdir(parents=True, exist_ok=True)

    datasets = list(DATASET_CONFIGS) if args.dataset == "all" else [args.dataset]
    splits = list(SPLITS) if args.split == "all" else [args.split]

    for dataset in datasets:
        for split in splits:
            convert(
                dataset, split,
                cnn_out=args.cnn_root / dataset,
                otis_out=args.otis_root / dataset,
                rrm_out=args.rrm_root / dataset,
                tmp_dir=args.tmp_dir,
                max_shards=args.max_shards,
            )


if __name__ == "__main__":
    main()
