"""Build the capstone PDF report from the content in this file.

Run: python report/build_report.py
Produces: report/SortSense_Capstone_Report.pdf

Uses a system Thai-capable font (Tahoma) since reportlab's built-in fonts
have no Thai glyphs. wordWrap='CJK' is used so long Thai text (which has
no spaces between words) still wraps inside the page width.
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    ListFlowable, ListItem, PageBreak, HRFlowable,
)

HERE = Path(__file__).parent
FONT_DIR = Path("C:/Windows/Fonts")

pdfmetrics.registerFont(TTFont("Thai", str(FONT_DIR / "tahoma.ttf")))
pdfmetrics.registerFont(TTFont("Thai-Bold", str(FONT_DIR / "tahomabd.ttf")))

GREEN = colors.HexColor("#1a3c1a")
AMBER = colors.HexColor("#8a4b00")

styles = {
    "title": ParagraphStyle("title", fontName="Thai-Bold", fontSize=19, leading=25,
                             spaceAfter=4, wordWrap="CJK"),
    "subtitle": ParagraphStyle("subtitle", fontName="Thai", fontSize=11, leading=16,
                                textColor=colors.HexColor("#444444"), spaceAfter=4, wordWrap="CJK"),
    "meta": ParagraphStyle("meta", fontName="Thai", fontSize=9.5, leading=14,
                            textColor=colors.HexColor("#666666"), spaceAfter=14, wordWrap="CJK"),
    "h1": ParagraphStyle("h1", fontName="Thai-Bold", fontSize=14, leading=20,
                          spaceBefore=16, spaceAfter=8, textColor=GREEN, wordWrap="CJK"),
    "h2": ParagraphStyle("h2", fontName="Thai-Bold", fontSize=11.5, leading=16,
                          spaceBefore=10, spaceAfter=4, wordWrap="CJK"),
    "body": ParagraphStyle("body", fontName="Thai", fontSize=10.3, leading=15.5,
                            spaceAfter=6, alignment=4, wordWrap="CJK"),
    "bullet": ParagraphStyle("bullet", fontName="Thai", fontSize=10.3, leading=15,
                              leftIndent=14, spaceAfter=3, wordWrap="CJK"),
    "caption": ParagraphStyle("caption", fontName="Thai", fontSize=9, leading=13,
                               textColor=colors.HexColor("#555555"), spaceAfter=12,
                               alignment=1, wordWrap="CJK"),
    "todo": ParagraphStyle("todo", fontName="Thai-Bold", fontSize=9.8, leading=14,
                            textColor=AMBER, spaceBefore=4, spaceAfter=10, wordWrap="CJK"),
    "tablehead": ParagraphStyle("tablehead", fontName="Thai-Bold", fontSize=9.5,
                                 leading=13, textColor=colors.white, wordWrap="CJK"),
    "tablecell": ParagraphStyle("tablecell", fontName="Thai", fontSize=9.5,
                                 leading=13, wordWrap="CJK"),
}


def P(text, style="body"):
    return Paragraph(text, styles[style])


def bullets(items):
    return ListFlowable(
        [ListItem(P(t, "bullet"), bulletColor=GREEN) for t in items],
        bulletType="bullet", start="circle", leftIndent=14,
    )


def table(rows, col_widths):
    data = [[P(c, "tablehead") for c in rows[0]]] + [[P(c, "tablecell") for c in r] for r in rows[1:]]
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f2")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def rule():
    return HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc"),
                       spaceBefore=2, spaceAfter=10)


def build():
    story = []

    # --- Header ---
    story.append(P("SortSense: ระบบตรวจจับและแยกประเภทขยะด้วย YOLOv8", "title"))
    story.append(P("รายงานโครงงาน Capstone — Deep Learning", "subtitle"))
    story.append(P(
        "ผู้จัดทำ: [กรอกชื่อ-นามสกุล / รหัสนักศึกษา] &nbsp;&nbsp;|&nbsp;&nbsp; "
        "วันที่: 29 ตุลาคม 2026 &nbsp;&nbsp;|&nbsp;&nbsp; "
        "Repo: [กรอกลิงก์ GitHub]", "meta"))
    story.append(rule())

    # --- 1. Problem & Data ---
    story.append(P("1. ปัญหาและข้อมูล (Problem &amp; Data)", "h1"))
    story.append(P(
        "โจทย์ของโครงงานคือการตรวจจับและจำแนกประเภทขยะจากภาพ/วิดีโอกล้องแบบเรียลไทม์ ออกเป็น 4 ประเภท "
        "ได้แก่ Recyclable (รีไซเคิล), Organic (อินทรีย์), General (ทั่วไป) และ Hazardous (อันตราย) "
        "เพื่อแนะนำถังขยะที่ถูกต้องให้ผู้ใช้งานแบบอัตโนมัติ งานนี้เป็น object detection ไม่ใช่เพียง "
        "image classification เพราะต้องระบุตำแหน่ง (bounding box) ของขยะแต่ละชิ้นในภาพ รองรับหลายวัตถุ "
        "ต่อเฟรม และต้องประมวลผลได้เร็วพอสำหรับกล้องสด (webcam / กล้อง iPad)", "body"))
    story.append(P("ข้อมูล (Data)", "h2"))
    story.append(bullets([
        "แหล่งที่มา: ภาพถ่ายขยะจริงที่เก็บและติดป้ายกำกับ (bounding box) เอง ไม่ใช่ชุดข้อมูลสาธารณะ "
        "(self-collected &amp; manually annotated)",
        "ขนาดชุดข้อมูล: 200 ภาพ / 229 bounding boxes (ชุด dataset_waste_real_v3_hazard_single)",
        "การแบ่งชุดข้อมูล: Train 151 ภาพ / Validation 25 ภาพ / Test 24 ภาพ แบ่งแบบ fixed split "
        "ไม่ใช่ random split ใหม่ทุกครั้งที่รัน เพื่อให้ผล reproducible",
        "ป้องกัน test leakage: ก่อนเทรนทุกครั้งมีขั้นตอนคำนวณ SHA256 hash ของไฟล์ภาพทุกไฟล์ และตรวจว่า "
        "ไม่มีภาพใดซ้ำกันข้าม split (ดูขั้นตอน \"2. ตรวจภาพและ labels\" ใน Kaggle notebook)",
    ]))
    story.append(P(
        "ข้อจำกัดสำคัญของข้อมูล: ชุดข้อมูลมีขนาดเล็กมากเมื่อเทียบกับงาน object detection ทั่วไป "
        "โดยเฉพาะคลาส Hazardous ที่มีตัวอย่างใน Test เพียง 4 วัตถุ ทำให้ตัวเลขผลลัพธ์ต่อคลาสของ Hazardous "
        "มีความแปรปรวนสูงและควรตีความอย่างระมัดระวัง (รายละเอียดเพิ่มเติมในหัวข้อผลลัพธ์และข้อจำกัด)", "body"))

    # --- 2. Architecture & training ---
    story.append(P("2. สถาปัตยกรรมโมเดลและการเทรน (Architecture &amp; Training Choices)", "h1"))
    story.append(P(
        "โมเดลที่ใช้คือ YOLOv8 (Ultralytics) ซึ่งเป็น CNN แบบ single-stage object detector เลือกใช้ด้วยเหตุผล 3 ข้อ: "
        "(1) งานต้องตรวจจับหลายวัตถุพร้อมตำแหน่งในภาพเดียว เหมาะกับสถาปัตยกรรม detector มากกว่า classifier ธรรมดา "
        "(2) ต้องประมวลผลแบบเรียลไทม์บนกล้องเว็บ/iPad ซึ่ง YOLO ออกแบบมาเพื่อความเร็วโดยเฉพาะ "
        "(3) มี pretrained weights บน COCO ให้ทำ transfer learning ได้ทันที ซึ่งจำเป็นมากเมื่อชุดข้อมูลมีเพียง 200 ภาพ", "body"))

    img_path = HERE / "architecture_diagram.png"
    if img_path.exists():
        story.append(Image(str(img_path), width=16 * cm, height=16 * cm * 0.37))
        story.append(P("ภาพที่ 1: สถาปัตยกรรม YOLOv8 — backbone แบบ CNN, neck รวม feature หลายขนาด, "
                        "detection head 3 scale และ NMS กรองกล่องซ้ำ ก่อนได้ผลลัพธ์ 4 คลาส", "caption"))

    story.append(P("ฟังก์ชันสูญเสีย (Loss)", "h2"))
    story.append(P(
        "ใช้ loss มาตรฐานของ Ultralytics YOLOv8 ซึ่งรวม 3 ส่วน: box regression loss (CIoU) สำหรับตำแหน่งกรอบ, "
        "classification loss (binary cross-entropy) สำหรับจำแนกคลาส และ distribution focal loss (DFL) "
        "เพื่อเพิ่มความแม่นยำของขอบกล่อง", "body"))

    story.append(P("Optimizer", "h2"))
    story.append(P(
        "ใช้ optimizer='auto' ของ Ultralytics ซึ่งเลือก AdamW โดยอัตโนมัติเมื่อชุดข้อมูลมีขนาดเล็กเช่นนี้ "
        "พร้อม weight decay เริ่มต้น (~0.0005) และ cosine learning-rate schedule ค่าที่ใช้จริงถูกบันทึกไว้ใน "
        "args.yaml ของผลการเทรนแต่ละรอบบน Kaggle เพื่อให้ตรวจสอบย้อนหลังได้", "body"))

    story.append(P("Regularization", "h2"))
    story.append(bullets([
        "Transfer learning จาก COCO pretrained weights — ลดความเสี่ยง overfitting กับชุดข้อมูลขนาดเล็ก",
        "Early stopping: patience=25 epoch (เพดานสูงสุด 100 epoch) หยุดเทรนเมื่อ validation ไม่ดีขึ้น",
        "Data augmentation ค่าเริ่มต้นของ Ultralytics: mosaic, random HSV color jitter, flip, scale",
        "Weight decay ในตัว optimizer",
    ]))

    story.append(P("Hyperparameters (fixed seed เพื่อ reproducibility)", "h2"))
    story.append(table(
        [["พารามิเตอร์", "ค่า"],
         ["epochs สูงสุด", "100"],
         ["patience (early stopping)", "25"],
         ["batch size", "8"],
         ["image size", "640 x 640"],
         ["random seed", "42 (เท่ากันทุกการเทรน รวมทั้ง baseline และโมเดลหลัก)"]],
        col_widths=[6 * cm, 10 * cm],
    ))
    story.append(Spacer(1, 6))

    # --- 3. Evaluation ---
    story.append(P("3. การประเมินผล (Evaluation)", "h1"))
    story.append(P(
        "Metric หลักที่ใช้คือ mAP50 และ mAP50-95 (มาตรฐานของงาน object detection) ร่วมกับ precision และ recall "
        "ทั้งแบบรวมและแยกตามคลาส", "body"))
    story.append(P("Baseline", "h2"))
    story.append(P(
        "ใช้ YOLOv8n (โมเดลเล็กกว่า พารามิเตอร์น้อยกว่าประมาณ 3 เท่า) เป็น baseline โดยเทรนด้วยชุดข้อมูล, "
        "ไฮเปอร์พารามิเตอร์ และ seed เดียวกันทุกประการกับโมเดลหลัก YOLOv8m ต่างกันเฉพาะขนาด backbone เท่านั้น "
        "วิธีนี้ทำให้เปรียบเทียบได้ตรงไปตรงมาว่าโมเดลที่ใหญ่และซับซ้อนกว่าให้ผลลัพธ์ดีขึ้นจริงหรือไม่ "
        "คุ้มกับต้นทุนการคำนวณที่เพิ่มขึ้นหรือไม่ (สคริปต์ compare_models.py ในโค้ดใช้สร้างตารางเปรียบเทียบนี้)", "body"))
    story.append(P("ป้องกันการรั่วไหลของ Test set (no leakage)", "h2"))
    story.append(P(
        "เลือกจุดเทรนที่ดีที่สุดด้วย Validation set เท่านั้น (ใช้กำหนด early stopping และเลือก checkpoint) "
        "ส่วน Test set จะถูกแตะเพียงครั้งเดียวหลังเลือกโมเดลเสร็จสิ้นแล้ว ไม่มีการย้อนกลับไปปรับโมเดลตามคะแนน Test", "body"))

    # --- 4. Results ---
    story.append(P("4. ผลลัพธ์ (Results)", "h1"))
    story.append(P(
        "ตารางที่ 1 เปรียบเทียบ baseline (YOLOv8n) กับโมเดลหลัก (YOLOv8m) บน Test set เดียวกัน "
        "(dataset v3, 24 ภาพ / 25 วัตถุ)", "body"))
    story.append(table(
        [["Metric", "YOLOv8n (baseline)", "YOLOv8m (main model)"],
         ["Precision", "77.3%", "[รอผลจาก GPU run]"],
         ["Recall", "79.3%", "[รอผลจาก GPU run]"],
         ["mAP50", "79.7%", "[รอผลจาก GPU run]"],
         ["mAP50-95", "64.9%", "[รอผลจาก GPU run]"]],
        col_widths=[4.5 * cm, 5.5 * cm, 6 * cm],
    ))
    story.append(P(
        "[TODO ก่อนส่งจริง] ตัวเลขคอลัมน์ YOLOv8m ยังไม่มีเพราะต้องรันบน GPU — รัน "
        "kaggle_train_waste_real_v3_yolov8m.ipynb บน Kaggle/Colab แล้วใช้ compare_models.py "
        "สร้างตารางนี้ใหม่ด้วยค่าจริง (ดูขั้นตอนใน README หัวข้อ \"Baseline comparison\")", "todo"))

    img2 = HERE / "per_class_results.png"
    if img2.exists():
        story.append(Image(str(img2), width=15 * cm, height=15 * cm * 0.56))
        story.append(P("ภาพที่ 2: ผลลัพธ์ของ baseline (YOLOv8n) แยกตามคลาสบน Test set — Recyclable แม่นยำสูงสุด "
                        "ขณะที่ Hazardous ต่ำสุดในทุก metric", "caption"))

    story.append(P("Learning curves", "h2"))
    story.append(P(
        "[TODO ก่อนส่งจริง] แนบกราฟ train/validation loss และ mAP ต่อ epoch ของทั้งสองโมเดล ซึ่ง Ultralytics "
        "สร้างให้อัตโนมัติเป็นไฟล์ results.png ในโฟลเดอร์ output ของ Kaggle "
        "(runs/detect/waste_real_v3_hazard_single/results.png และ runs/detect/waste_real_v3_yolov8m/results.png) "
        "หลังรันทั้งสอง notebook ให้ดาวน์โหลดไฟล์นี้มาวางแทนย่อหน้านี้", "todo"))

    story.append(P("ผลที่ไม่เป็นไปตามคาด (Honest Failure Case)", "h2"))
    story.append(P(
        "จุดอ่อนที่ชัดเจนที่สุดของโมเดลคือคลาส Hazardous — mAP50 เพียง 58.2% และ recall เพียง 50% "
        "(ตรวจพบวัตถุอันตรายจริงได้เพียงครึ่งหนึ่งของ Test set) สาเหตุที่น่าจะเป็นไปได้มีสองประการ: "
        "(1) จำนวนตัวอย่างในชุดข้อมูลน้อยมาก ทั้งหมดรวมกันหลักสิบภาพเท่านั้น และ (2) วัตถุอันตราย "
        "(เช่น แบตเตอรี่ ของมีคม) มีรูปร่างและพื้นผิวหลากหลายกว่าขยะรีไซเคิล (ขวด/กระป๋องมีรูปทรงสม่ำเสมอกว่ามาก) "
        "ทำให้โมเดลเรียนรู้ pattern ที่สรุปทั่วไปได้ยากกว่าด้วยข้อมูลปริมาณเท่านี้ นอกจากนี้จากการตรวจผลเชิงคุณภาพ "
        "ยังพบกรณีที่โมเดลให้ bounding box ซ้ำซ้อนบนวัตถุชิ้นเดียวกัน (เช่น ขวดพลาสติกหนึ่งขวดถูกล้อมกรอบ Recyclable "
        "สองกรอบซ้อนกัน) ซึ่งบ่งชี้ว่าอาจต้องปรับ NMS (non-max suppression) threshold เพิ่มเติม", "body"))

    # --- 5. Limitations ---
    story.append(P("5. ข้อจำกัดและแนวทางพัฒนาต่อ (Limitations &amp; Next Steps)", "h1"))
    story.append(bullets([
        "ชุดข้อมูลเล็กมาก (200 ภาพ) โดยเฉพาะคลาส Hazardous ที่มีตัวอย่าง Test เพียง 4 ชิ้น ทำให้ตัวเลขต่อคลาส "
        "มีความแปรปรวนสูง ไม่ควรตีความว่าเป็นค่าความแม่นยำระดับใช้งานจริง (production-grade)",
        "พบกรณี duplicate bounding box จากการตรวจผลเชิงคุณภาพ แต่ยังไม่ได้วัดผลเชิงปริมาณอย่างเป็นระบบ "
        "(เช่น อัตรา duplicate detection ต่อภาพ)",
        "ยังไม่ได้ทดลองปรับความเข้ม augmentation หรือ hyperparameter อื่นนอกจากค่าเริ่มต้นของ Ultralytics",
        "แนวทางพัฒนาต่อ: (1) เก็บภาพคลาส Hazardous เพิ่มให้สมดุลกับคลาสอื่น (2) ทดลองปรับ confidence/NMS "
        "threshold แยกตามคลาส โดยให้ Hazardous มี threshold ต่ำกว่าเพื่อลด false negative เพราะผลกระทบด้าน "
        "ความปลอดภัยสูงกว่าขยะทั่วไป (3) เพิ่มกลไกตรวจทานโดยมนุษย์ (human-in-the-loop) เมื่อความมั่นใจของโมเดลต่ำ "
        "ก่อนนำไปสั่งการถังขยะจริง",
    ]))

    doc = SimpleDocTemplate(
        str(HERE / "SortSense_Capstone_Report.pdf"),
        pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        leftMargin=2.0 * cm, rightMargin=2.0 * cm,
        title="SortSense Capstone Report",
    )
    doc.build(story)
    print("written: report/SortSense_Capstone_Report.pdf")


if __name__ == "__main__":
    build()
