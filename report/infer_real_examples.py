"""Run the real trained model (best.pt) on real test-set images, CPU only.

Produces genuine detection output used in the demo video (report/build_video.py):
no staged/mocked results, just best.pt run against held-out test images.

Run: .venv\\Scripts\\python.exe report/infer_real_examples.py
"""
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).parent.parent
OUT = Path(__file__).parent / "inference_demo"
OUT.mkdir(exist_ok=True)

# Picked from dataset_waste_real_v3_hazard_single/labels/test:
#   1_13.jpg -> ground truth class 0 (Recyclable), single object
#   H93.jpg  -> ground truth class 3 (Hazardous), TWO objects (phone screen + battery)
IMAGES = [
    ROOT / "dataset_waste_real_v3_hazard_single/images/test/1_13.jpg",
    ROOT / "dataset_waste_real_v3_hazard_single/images/test/H84.jpg",
    ROOT / "dataset_waste_real_v3_hazard_single/images/test/H93.jpg",
    ROOT / "dataset_waste_real_v3_hazard_single/images/test/2_04.jpg",
]


def main():
    model = YOLO(str(ROOT / "best.pt"))
    results = model.predict(source=[str(p) for p in IMAGES], conf=0.45, imgsz=640,
                             device="cpu", save=False)
    for img_path, result in zip(IMAGES, results):
        preds = [(model.names[int(b.cls.item())], round(float(b.conf.item()), 3)) for b in result.boxes]
        print(img_path.name, "->", preds)
        from PIL import Image
        Image.fromarray(result.plot()[..., ::-1]).save(OUT / img_path.name)
    print("saved annotated images to report/inference_demo/")


if __name__ == "__main__":
    main()
