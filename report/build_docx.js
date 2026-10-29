// Build the capstone report as a .docx (Word) file.
// Run: node report/build_docx.js
// Produces: report/SortSense_Capstone_Report.docx
// Mirrors the content of build_report.py (the PDF version).

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, LevelFormat, Numbering, convertInchesToTwip,
} = require("docx");

const HERE = __dirname;
const FONT = "Tahoma";
const GREEN = "1A3C1A";
const AMBER = "8A4B00";
const GREY = "555555";

const bodyRun = (text, opts = {}) => new TextRun({ text, font: FONT, size: 21, ...opts });
const body = (text, opts = {}) => new Paragraph({
  children: [bodyRun(text, opts)],
  alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 160 },
});
const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 320, after: 160 },
  children: [new TextRun({ text, font: FONT, size: 28, bold: true, color: GREEN })],
});
const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 200, after: 100 },
  children: [new TextRun({ text, font: FONT, size: 23, bold: true, color: "000000" })],
});
const todo = (text) => new Paragraph({
  spacing: { before: 80, after: 160 },
  shading: { type: ShadingType.CLEAR, fill: "FFF3E0" },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: AMBER, space: 6 } },
  children: [new TextRun({ text, font: FONT, size: 20, bold: true, color: AMBER })],
});
const caption = (text) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 240 },
  children: [new TextRun({ text, font: FONT, size: 18, color: GREY, italics: true })],
});
const bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 60 },
  children: [bodyRun(text)],
});

function image(file, widthPx, heightPx) {
  const data = fs.readFileSync(path.join(HERE, file));
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 80 },
    children: [new ImageRun({ type: "png", data, transformation: { width: widthPx, height: heightPx } })],
  });
}

function cell(text, { header = false, width } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: header ? { type: ShadingType.CLEAR, fill: GREEN } : undefined,
    margins: { top: 100, bottom: 100, left: 100, right: 100 },
    children: [new Paragraph({
      children: [new TextRun({
        text, font: FONT, size: 19, bold: header,
        color: header ? "FFFFFF" : "000000",
      })],
    })],
  });
}

function table(rows, widths) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({
      children: r.map((c, j) => cell(c, { header: i === 0, width: widths[j] })),
    })),
  });
}

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "●", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: convertInchesToTwip(0.3), hanging: convertInchesToTwip(0.2) } } } }],
    }],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 } } }, // A4 in twips
    children: [
      new Paragraph({
        spacing: { after: 40 },
        children: [new TextRun({
          text: "SortSense: ระบบตรวจจับและแยกประเภทขยะด้วย YOLOv8",
          font: FONT, size: 34, bold: true,
        })],
      }),
      new Paragraph({
        spacing: { after: 40 },
        children: [new TextRun({ text: "รายงานโครงงาน Capstone — Deep Learning", font: FONT, size: 22, color: "444444" })],
      }),
      new Paragraph({
        spacing: { after: 200 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC", space: 8 } },
        children: [new TextRun({
          text: "ผู้จัดทำ: [กรอกชื่อ-นามสกุล / รหัสนักศึกษา]   |   วันที่: 29 ตุลาคม 2026   |   Repo: [กรอกลิงก์ GitHub]",
          font: FONT, size: 19, color: GREY,
        })],
      }),

      // 1. Problem & Data
      h1("1. ปัญหาและข้อมูล (Problem & Data)"),
      body(
        "โจทย์ของโครงงานคือการตรวจจับและจำแนกประเภทขยะจากภาพ/วิดีโอกล้องแบบเรียลไทม์ ออกเป็น 4 ประเภท " +
        "ได้แก่ Recyclable (รีไซเคิล), Organic (อินทรีย์), General (ทั่วไป) และ Hazardous (อันตราย) " +
        "เพื่อแนะนำถังขยะที่ถูกต้องให้ผู้ใช้งานแบบอัตโนมัติ งานนี้เป็น object detection ไม่ใช่เพียง " +
        "image classification เพราะต้องระบุตำแหน่ง (bounding box) ของขยะแต่ละชิ้นในภาพ รองรับหลายวัตถุ " +
        "ต่อเฟรม และต้องประมวลผลได้เร็วพอสำหรับกล้องสด (webcam / กล้อง iPad)"
      ),
      h2("ข้อมูล (Data)"),
      bullet("แหล่งที่มา: ภาพถ่ายขยะจริงที่เก็บและติดป้ายกำกับ (bounding box) เอง ไม่ใช่ชุดข้อมูลสาธารณะ (self-collected & manually annotated)"),
      bullet("ขนาดชุดข้อมูล: 200 ภาพ / 229 bounding boxes (ชุด dataset_waste_real_v3_hazard_single)"),
      bullet("การแบ่งชุดข้อมูล: Train 151 ภาพ / Validation 25 ภาพ / Test 24 ภาพ แบ่งแบบ fixed split ไม่ใช่ random split ใหม่ทุกครั้งที่รัน เพื่อให้ผล reproducible"),
      bullet("ป้องกัน test leakage: ก่อนเทรนทุกครั้งมีขั้นตอนคำนวณ SHA256 hash ของไฟล์ภาพทุกไฟล์ และตรวจว่าไม่มีภาพใดซ้ำกันข้าม split"),
      body(
        "ข้อจำกัดสำคัญของข้อมูล: ชุดข้อมูลมีขนาดเล็กมากเมื่อเทียบกับงาน object detection ทั่วไป " +
        "โดยเฉพาะคลาส Hazardous ที่มีตัวอย่างใน Test เพียง 4 วัตถุ ทำให้ตัวเลขผลลัพธ์ต่อคลาสของ Hazardous " +
        "มีความแปรปรวนสูงและควรตีความอย่างระมัดระวัง"
      ),

      // 2. Architecture & training
      h1("2. สถาปัตยกรรมโมเดลและการเทรน (Architecture & Training Choices)"),
      body(
        "โมเดลที่ใช้คือ YOLOv8 (Ultralytics) ซึ่งเป็น CNN แบบ single-stage object detector เลือกใช้ด้วยเหตุผล 3 ข้อ: " +
        "(1) งานต้องตรวจจับหลายวัตถุพร้อมตำแหน่งในภาพเดียว เหมาะกับสถาปัตยกรรม detector มากกว่า classifier ธรรมดา " +
        "(2) ต้องประมวลผลแบบเรียลไทม์บนกล้องเว็บ/iPad ซึ่ง YOLO ออกแบบมาเพื่อความเร็วโดยเฉพาะ " +
        "(3) มี pretrained weights บน COCO ให้ทำ transfer learning ได้ทันที ซึ่งจำเป็นมากเมื่อชุดข้อมูลมีเพียง 200 ภาพ"
      ),
      image("architecture_diagram.png", 580, 215),
      caption("ภาพที่ 1: สถาปัตยกรรม YOLOv8 — backbone แบบ CNN, neck รวม feature หลายขนาด, detection head 3 scale และ NMS กรองกล่องซ้ำ ก่อนได้ผลลัพธ์ 4 คลาส"),

      h2("ฟังก์ชันสูญเสีย (Loss)"),
      body(
        "ใช้ loss มาตรฐานของ Ultralytics YOLOv8 ซึ่งรวม 3 ส่วน: box regression loss (CIoU) สำหรับตำแหน่งกรอบ, " +
        "classification loss (binary cross-entropy) สำหรับจำแนกคลาส และ distribution focal loss (DFL) เพื่อเพิ่มความแม่นยำของขอบกล่อง"
      ),
      h2("Optimizer"),
      body(
        "ใช้ optimizer='auto' ของ Ultralytics ซึ่งเลือก AdamW โดยอัตโนมัติเมื่อชุดข้อมูลมีขนาดเล็กเช่นนี้ " +
        "พร้อม weight decay เริ่มต้น (~0.0005) และ cosine learning-rate schedule ค่าที่ใช้จริงถูกบันทึกไว้ใน " +
        "args.yaml ของผลการเทรนแต่ละรอบบน Kaggle เพื่อให้ตรวจสอบย้อนหลังได้"
      ),
      h2("Regularization"),
      bullet("Transfer learning จาก COCO pretrained weights — ลดความเสี่ยง overfitting กับชุดข้อมูลขนาดเล็ก"),
      bullet("Early stopping: patience=25 epoch (เพดานสูงสุด 100 epoch) หยุดเทรนเมื่อ validation ไม่ดีขึ้น"),
      bullet("Data augmentation ค่าเริ่มต้นของ Ultralytics: mosaic, random HSV color jitter, flip, scale"),
      bullet("Weight decay ในตัว optimizer"),
      h2("Hyperparameters (fixed seed เพื่อ reproducibility)"),
      table([
        ["พารามิเตอร์", "ค่า"],
        ["epochs สูงสุด", "100"],
        ["patience (early stopping)", "25"],
        ["batch size", "8"],
        ["image size", "640 x 640"],
        ["random seed", "42 (เท่ากันทุกการเทรน รวมทั้ง baseline และโมเดลหลัก)"],
      ], [3400, 6000]),
      new Paragraph({ spacing: { after: 200 }, children: [] }),

      // 3. Evaluation
      h1("3. การประเมินผล (Evaluation)"),
      body("Metric หลักที่ใช้คือ mAP50 และ mAP50-95 (มาตรฐานของงาน object detection) ร่วมกับ precision และ recall ทั้งแบบรวมและแยกตามคลาส"),
      h2("Baseline"),
      body(
        "ใช้ YOLOv8n (โมเดลเล็กกว่า พารามิเตอร์น้อยกว่าประมาณ 3 เท่า) เป็น baseline โดยเทรนด้วยชุดข้อมูล, " +
        "ไฮเปอร์พารามิเตอร์ และ seed เดียวกันทุกประการกับโมเดลหลัก YOLOv8m ต่างกันเฉพาะขนาด backbone เท่านั้น " +
        "วิธีนี้ทำให้เปรียบเทียบได้ตรงไปตรงมาว่าโมเดลที่ใหญ่และซับซ้อนกว่าให้ผลลัพธ์ดีขึ้นจริงหรือไม่ " +
        "คุ้มกับต้นทุนการคำนวณที่เพิ่มขึ้นหรือไม่ (สคริปต์ compare_models.py ในโค้ดใช้สร้างตารางเปรียบเทียบนี้)"
      ),
      h2("ป้องกันการรั่วไหลของ Test set (no leakage)"),
      body(
        "เลือกจุดเทรนที่ดีที่สุดด้วย Validation set เท่านั้น (ใช้กำหนด early stopping และเลือก checkpoint) " +
        "ส่วน Test set จะถูกแตะเพียงครั้งเดียวหลังเลือกโมเดลเสร็จสิ้นแล้ว ไม่มีการย้อนกลับไปปรับโมเดลตามคะแนน Test"
      ),

      // 4. Results
      h1("4. ผลลัพธ์ (Results)"),
      body("ตารางที่ 1 เปรียบเทียบ baseline (YOLOv8n) กับโมเดลหลัก (YOLOv8m) บน Test set เดียวกัน (dataset v3, 24 ภาพ / 25 วัตถุ)"),
      table([
        ["Metric", "YOLOv8n (baseline)", "YOLOv8m (main model)"],
        ["Precision", "77.3%", "[รอผลจาก GPU run]"],
        ["Recall", "79.3%", "[รอผลจาก GPU run]"],
        ["mAP50", "79.7%", "[รอผลจาก GPU run]"],
        ["mAP50-95", "64.9%", "[รอผลจาก GPU run]"],
      ], [2500, 3400, 3500]),
      new Paragraph({ spacing: { after: 120 }, children: [] }),
      todo(
        "[TODO ก่อนส่งจริง] ตัวเลขคอลัมน์ YOLOv8m ยังไม่มีเพราะต้องรันบน GPU — รัน " +
        "kaggle_train_waste_real_v3_yolov8m.ipynb บน Kaggle/Colab แล้วใช้ compare_models.py " +
        "สร้างตารางนี้ใหม่ด้วยค่าจริง (ดูขั้นตอนใน README หัวข้อ \"Baseline comparison\")"
      ),
      image("per_class_results.png", 560, 315),
      caption("ภาพที่ 2: ผลลัพธ์ของ baseline (YOLOv8n) แยกตามคลาสบน Test set — Recyclable แม่นยำสูงสุด ขณะที่ Hazardous ต่ำสุดในทุก metric"),

      h2("Learning curves"),
      todo(
        "[TODO ก่อนส่งจริง] แนบกราฟ train/validation loss และ mAP ต่อ epoch ของทั้งสองโมเดล ซึ่ง Ultralytics " +
        "สร้างให้อัตโนมัติเป็นไฟล์ results.png ในโฟลเดอร์ output ของ Kaggle " +
        "(runs/detect/waste_real_v3_hazard_single/results.png และ runs/detect/waste_real_v3_yolov8m/results.png) " +
        "หลังรันทั้งสอง notebook ให้ดาวน์โหลดไฟล์นี้มาวางแทนย่อหน้านี้"
      ),

      h2("ผลที่ไม่เป็นไปตามคาด (Honest Failure Case)"),
      body(
        "จุดอ่อนที่ชัดเจนที่สุดของโมเดลคือคลาส Hazardous — mAP50 เพียง 58.2% และ recall เพียง 50% " +
        "(ตรวจพบวัตถุอันตรายจริงได้เพียงครึ่งหนึ่งของ Test set) สาเหตุที่น่าจะเป็นไปได้มีสองประการ: " +
        "(1) จำนวนตัวอย่างในชุดข้อมูลน้อยมาก ทั้งหมดรวมกันหลักสิบภาพเท่านั้น และ (2) วัตถุอันตราย " +
        "(เช่น แบตเตอรี่ ของมีคม) มีรูปร่างและพื้นผิวหลากหลายกว่าขยะรีไซเคิล (ขวด/กระป๋องมีรูปทรงสม่ำเสมอกว่ามาก) " +
        "ทำให้โมเดลเรียนรู้ pattern ที่สรุปทั่วไปได้ยากกว่าด้วยข้อมูลปริมาณเท่านี้ นอกจากนี้จากการตรวจผลเชิงคุณภาพ " +
        "ยังพบกรณีที่โมเดลให้ bounding box ซ้ำซ้อนบนวัตถุชิ้นเดียวกัน (เช่น ขวดพลาสติกหนึ่งขวดถูกล้อมกรอบ Recyclable " +
        "สองกรอบซ้อนกัน) ซึ่งบ่งชี้ว่าอาจต้องปรับ NMS (non-max suppression) threshold เพิ่มเติม"
      ),

      // 5. Limitations
      h1("5. ข้อจำกัดและแนวทางพัฒนาต่อ (Limitations & Next Steps)"),
      bullet(
        "ชุดข้อมูลเล็กมาก (200 ภาพ) โดยเฉพาะคลาส Hazardous ที่มีตัวอย่าง Test เพียง 4 ชิ้น ทำให้ตัวเลขต่อคลาส " +
        "มีความแปรปรวนสูง ไม่ควรตีความว่าเป็นค่าความแม่นยำระดับใช้งานจริง (production-grade)"
      ),
      bullet(
        "พบกรณี duplicate bounding box จากการตรวจผลเชิงคุณภาพ แต่ยังไม่ได้วัดผลเชิงปริมาณอย่างเป็นระบบ " +
        "(เช่น อัตรา duplicate detection ต่อภาพ)"
      ),
      bullet("ยังไม่ได้ทดลองปรับความเข้ม augmentation หรือ hyperparameter อื่นนอกจากค่าเริ่มต้นของ Ultralytics"),
      bullet(
        "แนวทางพัฒนาต่อ: (1) เก็บภาพคลาส Hazardous เพิ่มให้สมดุลกับคลาสอื่น (2) ทดลองปรับ confidence/NMS " +
        "threshold แยกตามคลาส โดยให้ Hazardous มี threshold ต่ำกว่าเพื่อลด false negative เพราะผลกระทบด้าน " +
        "ความปลอดภัยสูงกว่าขยะทั่วไป (3) เพิ่มกลไกตรวจทานโดยมนุษย์ (human-in-the-loop) เมื่อความมั่นใจของโมเดลต่ำ " +
        "ก่อนนำไปสั่งการถังขยะจริง"
      ),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(HERE, "SortSense_Capstone_Report.docx"), buf);
  console.log("written: report/SortSense_Capstone_Report.docx");
});
