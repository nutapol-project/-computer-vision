"""Validate YOLO bounding-box labels before training."""
from pathlib import Path
import argparse
import math

NAMES = ["Recyclable", "Organic", "General", "Hazardous"]

def validate(config, splits=("train", "val", "test")):
    import yaml
    data = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    if data.get("names") != dict(enumerate(NAMES)):
        raise ValueError("data.yaml class order must be Recyclable, Organic, General, Hazardous")
    root = (Path(config).resolve().parent / data["path"]).resolve()
    errors = []
    total = 0
    for split in splits:
        directory = root / data[split]
        images = sorted(p for p in directory.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp"))
        if not images:
            errors.append(f"{split}: no images in {directory}")
        for image in images:
            relative = image.relative_to(root)
            parts = list(relative.parts)
            if parts[0] != "images":
                errors.append(f"{image}: expected dataset/images/<split>")
                continue
            parts[0] = "labels"
            label = root.joinpath(*parts).with_suffix(".txt")
            if not label.is_file():
                errors.append(f"Missing label: {label} (use an empty file for background)")
                continue
            for line_no, line in enumerate(label.read_text(encoding="utf-8").splitlines(), 1):
                try:
                    c, x, y, w, h = map(float, line.split())
                    if not all(math.isfinite(v) for v in (c, x, y, w, h)):
                        raise ValueError()
                    if c not in range(4) or not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                        raise ValueError()
                    if x-w/2 < -0.001 or y-h/2 < -0.001 or x+w/2 > 1.001 or y+h/2 > 1.001:
                        raise ValueError()
                    total += 1
                except ValueError:
                    errors.append(f"{label}:{line_no}: invalid 'class x_center y_center width height'")
        print(f"{split}: {len(images)} images")
    if errors:
        raise ValueError("\n".join(errors[:30]))
    print(f"Labels valid: {total} bounding boxes")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", default="data.yaml")
    args = p.parse_args()
    validate(args.data)
