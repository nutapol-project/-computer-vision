"""Build a narrated explainer video for the capstone demo (Q3).

Uses real artifacts only: the architecture diagram, the per-class results
chart (from real Kaggle eval numbers), and genuine CPU inference output from
the actual trained best.pt run on real test-set images (see
infer_real_examples.py). Narration is English (TTS) because no Thai SAPI
voice is installed on this machine; see DEMO_SCRIPT.md for a Thai live
narration alternative.

Run: python report/build_video.py
Produces: report/SortSense_Demo_Video.mp4
"""
import subprocess
import wave
from pathlib import Path

import pyttsx3
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

HERE = Path(__file__).parent
WORK = HERE / "video_work"
WORK.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

W, H = 1280, 720
GREEN = (26, 60, 26)
AMBER = (138, 75, 0)
GREY = (85, 85, 85)
BG = (247, 249, 247)

F_TITLE = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 46)
F_H1 = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 38)
F_BODY = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 26)
F_SMALL = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
F_CAP = ImageFont.truetype("C:/Windows/Fonts/segoeuii.ttf", 20)


def wrap(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def new_slide():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=GREEN)
    return img, d


def text_slide(title, bullets, footer=None):
    img, d = new_slide()
    d.text((70, 60), title, font=F_H1, fill=GREEN)
    d.line([(70, 120), (W - 70, 120)], fill=(200, 200, 200), width=2)
    y = 170
    for b in bullets:
        lines = wrap(d, b, F_BODY, W - 180)
        d.ellipse([70, y + 10, 82, y + 22], fill=GREEN)
        for i, line in enumerate(lines):
            d.text((100, y), line, font=F_BODY, fill=(20, 20, 20))
            y += 40
        y += 16
    if footer:
        d.text((70, H - 50), footer, font=F_SMALL, fill=GREY)
    return img


def image_slide(title, image_path, caption=None, img_w=None, img_h=None):
    img, d = new_slide()
    d.text((70, 50), title, font=F_H1, fill=GREEN)
    pic = Image.open(image_path).convert("RGB")
    max_w, max_h = W - 140, H - 230
    scale = min(max_w / pic.width, max_h / pic.height)
    if img_w:
        scale = min(scale, img_w / pic.width)
    new_size = (int(pic.width * scale), int(pic.height * scale))
    pic = pic.resize(new_size)
    x = (W - pic.width) // 2
    y = 140
    img.paste(pic, (x, y))
    if caption:
        lines = wrap(d, caption, F_CAP, W - 160)
        yy = y + pic.height + 20
        for line in lines:
            d.text((80, yy), line, font=F_CAP, fill=GREY)
            yy += 26
    return img


def title_slide():
    img, d = new_slide()
    d.rectangle([0, 0, W, H], fill=(26, 60, 26))
    d.text((W // 2, H // 2 - 70), "SortSense", font=ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 72),
           fill=(255, 255, 255), anchor="mm")
    d.text((W // 2, H // 2 + 10), "Real-time waste detection with YOLOv8", font=F_H1,
           fill=(220, 235, 220), anchor="mm")
    d.text((W // 2, H // 2 + 70), "Capstone Demo — Deep Learning", font=F_BODY,
           fill=(190, 210, 190), anchor="mm")
    return img


SLIDES = []


def add(image, narration):
    SLIDES.append((image, narration))


add(title_slide(),
    "SortSense is a four-class waste detector: Recyclable, Organic, General, and Hazardous. "
    "This is a quick walkthrough of the problem, the model, and the results, including one case "
    "where the model gets it wrong.")

add(text_slide("The Problem", [
    "Detect and classify waste from camera images in real time, into four categories: "
    "Recyclable, Organic, General, and Hazardous.",
    "This is object detection, not plain image classification: the model must locate each "
    "item with a bounding box, and handle multiple items per frame.",
    "The target use case is a live webcam feed, so the model also needs to run fast.",
]),
    "The problem is detecting and classifying waste from camera images in real time, into four "
    "categories: Recyclable, Organic, General, and Hazardous. This is object detection, not plain "
    "image classification, because the model has to locate each item with a bounding box, and "
    "handle multiple items per frame. The target use case is a live webcam feed, so the model "
    "also has to run fast.")

add(text_slide("The Data", [
    "200 self-collected, manually labeled photos; 229 bounding boxes total.",
    "Split: 151 train / 25 validation / 24 test images, fixed, not re-randomized per run.",
    "Before every training run, a SHA256 hash check confirms no image repeats across splits.",
    "Limitation: Hazardous has only 4 objects in the test set, so its per-class numbers are noisy.",
]),
    "The dataset is 200 self-collected, manually labeled photos, with 229 bounding boxes total. "
    "It's split into 151 training images, 25 validation images, and 24 test images, and that split "
    "is fixed, not re-randomized every run. Before every training run, a SHA256 hash check confirms "
    "no image repeats across splits, so there's no test leakage. The main limitation is that the "
    "Hazardous class has only 4 objects in the test set, so its numbers are noisy.")

add(image_slide("Architecture: YOLOv8", str(HERE / "architecture_diagram.png"),
                 "CNN backbone, multi-scale feature fusion, three detection heads, then NMS."),
    "The model is YOLOv8, a single-stage CNN object detector. It's pretrained on COCO and then "
    "fine-tuned end to end on our four waste classes, which matters a lot given only 200 training "
    "images. The backbone extracts CNN features, the neck fuses them across scales, and three "
    "detection heads predict boxes and classes before non-max suppression removes duplicates.")

add(text_slide("Training Setup", [
    "Loss: CIoU box loss + classification BCE + distribution focal loss (Ultralytics defaults).",
    "Optimizer: auto-selected AdamW with weight decay and a cosine learning-rate schedule.",
    "Regularization: transfer learning, early stopping (patience 25 of 100 epochs), default "
    "augmentation (mosaic, HSV jitter, flip, scale), and weight decay.",
    "Fixed seed 42 for every run, so results reproduce.",
]),
    "On training: the loss combines box regression, classification, and a distribution focal "
    "loss, all Ultralytics defaults. The optimizer is auto-selected AdamW with weight decay and a "
    "cosine schedule. For regularization we rely on transfer learning, early stopping with a "
    "patience of 25 out of a maximum 100 epochs, and the default Ultralytics augmentation: mosaic, "
    "color jitter, flips and scaling. Every run uses a fixed seed of 42, so results reproduce.")

add(image_slide("Success Case: Real Inference", str(HERE / "inference_demo" / "1_13.jpg"),
                 "Real test-set image, real CPU inference with the trained model — correctly detected as Recyclable, confidence 0.97."),
    "Here's a success case. This is a real image from the held-out test set, run through the "
    "actual trained model on CPU, not a mockup. The model correctly detects it as Recyclable with "
    "97 percent confidence.")

add(image_slide("Honest Failure Case: Hazardous", str(HERE / "inference_demo" / "H93.jpg"),
                 "Real inference output. Ground truth has two separate Hazardous objects (phone screen + battery); the model only returns one merged box."),
    "And here's an honest failure case, also real inference, not staged. The ground truth for this "
    "image has two separate hazardous objects: a broken phone screen and an exposed battery. The "
    "model only returns one merged bounding box, missing the second object. This matches what we "
    "see in the overall numbers: Hazardous has the lowest recall of any class, around 50 percent, "
    "most likely because it has the fewest and most visually varied training examples.")

add(image_slide("Baseline vs Main Model", str(HERE / "per_class_results.png"),
                 "YOLOv8n baseline, per-class test results. Recyclable is strongest; Hazardous is clearly the weakest across every metric."),
    "For evaluation, we compare YOLOv8n as a baseline against YOLOv8m as the main model, trained "
    "with identical data, hyperparameters, and seed, so the only difference is model size. This "
    "chart shows the YOLOv8n baseline broken down by class: Recyclable is the strongest performer, "
    "and Hazardous is clearly the weakest across every metric, which lines up with the failure case "
    "we just saw.")

add(text_slide("Limitations & Next Steps", [
    "Dataset is small (200 images); Hazardous especially so. Numbers are not production-grade.",
    "Qualitatively observed duplicate/merged bounding boxes on some objects.",
    "Next: collect more Hazardous examples, tune per-class confidence/NMS thresholds, and add a "
    "human-in-the-loop review step before acting on low-confidence predictions.",
]),
    "To wrap up: the dataset is small, especially for the Hazardous class, so these numbers "
    "shouldn't be read as production-grade. We've also seen duplicate or merged bounding boxes on "
    "some objects. Next steps are collecting more Hazardous examples, tuning confidence and N-M-S "
    "thresholds per class, and adding a human review step before acting on low-confidence "
    "predictions, since getting Hazardous wrong has real safety consequences.")

add(title_slide(), "Thanks for watching. Code, training notebooks, and the full report are in the GitHub repository linked in the description.")


def tts_to_wav(text, path, voice_id=None, rate=172):
    engine = pyttsx3.init()
    if voice_id:
        engine.setProperty("voice", voice_id)
    engine.setProperty("rate", rate)
    engine.save_to_file(text, str(path))
    engine.runAndWait()


def wav_duration(path):
    with wave.open(str(path), "rb") as f:
        return f.getnframes() / f.getframerate()


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main():
    voice_id = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_ZIRA_11.0"
    clip_paths = []

    for i, (img, narration) in enumerate(SLIDES):
        png = WORK / f"slide_{i:02d}.png"
        wav = WORK / f"slide_{i:02d}.wav"
        mp4 = WORK / f"clip_{i:02d}.mp4"
        img.save(png)
        tts_to_wav(narration, wav, voice_id=voice_id)
        dur = wav_duration(wav) + 0.6
        run([
            FFMPEG, "-y", "-loop", "1", "-i", str(png), "-i", str(wav),
            "-vf", "scale=1280:720,format=yuv420p",
            "-af", "apad=pad_dur=0.6",
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{dur:.2f}", str(mp4),
        ])
        clip_paths.append(mp4)
        print(f"slide {i}: {dur:.1f}s")

    concat_list = WORK / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in clip_paths), encoding="utf-8")
    out = HERE / "SortSense_Demo_Video.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(out)])
    total = sum(wav_duration(WORK / f"slide_{i:02d}.wav") + 0.6 for i in range(len(SLIDES)))
    print(f"written: report/SortSense_Demo_Video.mp4 (~{total/60:.1f} min)")


if __name__ == "__main__":
    main()
