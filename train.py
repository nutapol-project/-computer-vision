"""Train or evaluate the four-class waste detector."""
import argparse
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", default="data.yaml")
    p.add_argument("--model", default="yolov8n.pt")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="cpu")
    p.add_argument("--evaluate", metavar="WEIGHTS")
    p.add_argument("--split", choices=["val", "test"], default="test")
    args = p.parse_args()
    import yaml
    from ultralytics import YOLO
    from validate_dataset import validate
    config = Path(args.data).resolve()
    validate(config, splits=(args.split,) if args.evaluate else ("train", "val"))
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    data["path"] = str((config.parent / data["path"]).resolve())
    # Resolve the dataset root independently of Ultralytics' global settings.
    output = Path("runs").resolve()
    output.mkdir(exist_ok=True)
    resolved = output / "data-resolved.yaml"
    resolved.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    if args.evaluate:
        if not Path(args.evaluate).is_file():
            p.error("Evaluation weights do not exist")
        YOLO(args.evaluate).val(data=str(resolved), split=args.split, device=args.device, plots=True)
    else:
        YOLO(args.model).train(data=str(resolved), epochs=args.epochs,
                              batch=args.batch, imgsz=args.imgsz, device=args.device,
                              workers=0, project=str(output / "detect"), name="waste", seed=42)

if __name__ == "__main__":
    main()
