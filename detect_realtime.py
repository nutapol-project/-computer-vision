"""Webcam/video detection and persistent tracking. No hardware commands."""
import argparse
import csv
from pathlib import Path
import time

NAMES = ["Recyclable", "Organic", "General", "Hazardous"]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="0", help="Camera index or video path")
    p.add_argument("--weights", default=str(Path(__file__).resolve().parent / "best.pt"))
    p.add_argument("--demo", action="store_true", help="Generic COCO detection, NOT waste classification")
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="cpu")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--save-video", action="store_true")
    p.add_argument("--output", default="outputs")
    args = p.parse_args()
    if not 0 < args.conf <= 1:
        p.error("--conf must be between 0 and 1")
    if not args.demo and not Path(args.weights).is_file():
        p.error("Waste model missing. Train first or use --demo for generic objects.")
    import cv2
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt" if args.demo else args.weights)
    if not args.demo and [model.names[k] for k in sorted(model.names)] != NAMES:
        p.error("Model classes must be exactly: " + ", ".join(NAMES))
    source = int(args.source) if args.source.isdecimal() else args.source
    cap = cv2.VideoCapture(source)
    writer = None
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open source: {args.source}")
        folder = Path(args.output) / time.strftime("%Y%m%d-%H%M%S")
        folder.mkdir(parents=True, exist_ok=False)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not 1 <= fps <= 240:
            fps = 30
        frame_index = 0
        start = time.perf_counter()
        with (folder / "detections.csv").open("w", newline="", encoding="utf-8") as f:
            log = csv.writer(f)
            log.writerow(["frame", "source_seconds", "track_id", "class", "confidence", "x1", "y1", "x2", "y2"])
            while True:
                ok, frame = cap.read()
                if not ok:
                    if frame_index == 0 or isinstance(source, int):
                        raise RuntimeError("No camera frame received; check camera connection/permissions.")
                    break
                frame_index += 1
                result = model.track(frame, persist=True, tracker="bytetrack.yaml",
                                     conf=args.conf, imgsz=args.imgsz, device=args.device,
                                     verbose=False)[0]
                canvas = result.plot()
                boxes = result.boxes
                if boxes is not None:
                    coords = boxes.xyxy.cpu().tolist()
                    classes = boxes.cls.int().cpu().tolist()
                    scores = boxes.conf.cpu().tolist()
                    ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [""] * len(coords)
                    seconds = time.perf_counter() - start if isinstance(source, int) else (frame_index - 1) / fps
                    for tid, cls, score, xyxy in zip(ids, classes, scores, coords):
                        log.writerow([frame_index, round(seconds, 3), tid, model.names[cls], round(score, 4), *xyxy])
                label = "DEMO: generic objects" if args.demo else "Waste tracking: 4 classes"
                cv2.putText(canvas, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                if args.save_video:
                    if writer is None:
                        height, width = canvas.shape[:2]
                        writer = cv2.VideoWriter(str(folder / "tracked.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
                        if not writer.isOpened():
                            raise RuntimeError("Cannot create output video")
                    writer.write(canvas)
                if not args.headless:
                    cv2.imshow("Waste tracking - Q to quit", canvas)
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        break
        print(f"Saved results: {folder.resolve()}")
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
