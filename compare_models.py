"""Compare baseline vs main model on the same test split.

Reads the test-metrics.json files produced by the Kaggle training notebooks
(kaggle_train_waste_real_v3_hazard_single.ipynb for the YOLOv8n baseline,
kaggle_train_waste_real_v3_yolov8m.ipynb for the YOLOv8m main model) and
prints a results table for the report. Both notebooks evaluate on the same
dataset_waste_real_v3_hazard_single test split (24 images / 25 objects),
so the numbers are directly comparable.
"""
import argparse
import json
from pathlib import Path

METRICS = [
    ("precision", "metrics/precision(B)"),
    ("recall", "metrics/recall(B)"),
    ("mAP50", "metrics/mAP50(B)"),
    ("mAP50-95", "metrics/mAP50-95(B)"),
]


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {name: data[key] for name, key in METRICS if key in data}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", required=True, metavar="test-metrics.json",
                    help="YOLOv8n test-metrics.json (baseline, smaller model)")
    p.add_argument("--main", required=True, metavar="test-metrics-yolov8m.json",
                    help="YOLOv8m test-metrics.json (main model)")
    args = p.parse_args()

    baseline = load(args.baseline)
    main_model = load(args.main)

    print(f"{'metric':<10} {'baseline (YOLOv8n)':>20} {'main (YOLOv8m)':>16} {'delta':>8}")
    for name, _ in METRICS:
        if name not in baseline or name not in main_model:
            continue
        b, m = baseline[name], main_model[name]
        print(f"{name:<10} {b:>20.3f} {m:>16.3f} {m - b:>+8.3f}")


if __name__ == "__main__":
    main()
