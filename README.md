# SortSense — ระบบตรวจจับและแนะนำถังขยะ

## ติดตั้งบนเครื่องใหม่ (Windows)
ติดตั้ง Python 3.12 แล้วเปิด Terminal ในโฟลเดอร์โปรเจกต์ รัน:
```cmd
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
การติดตั้งต้องเชื่อมต่ออินเทอร์เน็ต ไฟล์ requirements-lock.txt เป็นรายการเวอร์ชันของเครื่องพัฒนา
เมื่อย้ายเครื่อง ให้สร้างสภาพแวดล้อมใหม่ตามคำสั่งนี้

## เปิดเว็บบนคอม
```cmd
.venv\Scripts\python.exe web_app.py
```
เปิด http://127.0.0.1:8080 เลือกโมเดลขยะและแหล่งภาพ แล้วเริ่มตรวจจับ
โมเดลที่ใช้: best.pt ที่โฟลเดอร์หลัก ส่วน yolov8n.pt ใช้โหมดทดลองและเป็นจุดเริ่มฝึก

## กล้อง iPad
ดับเบิลคลิก start_ipad.cmd แล้วทำตาม IPAD_CAMERA.md ใช้ HTTPS และอนุญาตกล้องบน iPad

## ลิงก์ใช้งานจากภายนอก
ดับเบิลคลิก start_public.cmd แล้วส่งลิงก์ HTTPS ที่แสดงให้ผู้ทดลอง เปิดคอมค้างไว้ระหว่างใช้
ตรวจจับพร้อมกันได้ 2 คน โดยแยกภาพและประวัติตามเบราว์เซอร์ หยุดด้วย stop_public.cmd
รายละเอียดและการติดตั้ง Cloudflare Tunnel บนเครื่องใหม่อยู่ใน PUBLIC_LINK.md

## ชุดข้อมูลที่เลือกใช้ล่าสุด
- dataset_waste_real_v3_hazard_single: 200 ภาพ / 229 กรอบ
- Train 151 / Validation 25 / Test 24
- เปลี่ยนเฉพาะ Validation Hazardous เป็นวัตถุเดียว 5 ภาพ
- ใช้ kaggle_waste_real_v3_hazard_single.zip และ kaggle_train_waste_real_v3_hazard_single.ipynb
- คะแนน Validation ใหม่เทียบตรงกับชุดเดิมไม่ได้

## ชุดข้อมูลเดิม v2 (เก็บไว้เทียบผล)
- dataset_waste_real_v2: 198 ภาพ / 242 กรอบ
- Train 151 / Validation 23 / Test 24
- kaggle_waste_real_v2.zip: ชุดข้อมูลสำหรับอัปโหลด Kaggle
- kaggle_train_waste_real_v2.ipynb: Notebook ฝึก
- เปิด review.html, review-new.html และ review-oct13.html ในโฟลเดอร์ข้อมูลเพื่อตรวจกรอบ
- data.yaml ที่โฟลเดอร์หลักปัจจุบันชี้ไป v3

## Baseline comparison (capstone evaluation)
เพื่อเทียบ "โมเดลหลัก" กับ "baseline" บน Test set เดียวกัน (dataset_waste_real_v3_hazard_single):
1. รัน `kaggle_train_waste_real_v3_hazard_single.ipynb` บน Kaggle/Colab GPU — นี่คือ baseline (YOLOv8n ขนาดเล็ก เริ่มจาก yolov8n.pt pretrained) ได้ `test-metrics.json`
2. รัน `kaggle_train_waste_real_v3_yolov8m.ipynb` — เหมือน notebook แรกทุกอย่าง (seed=42, epochs=100, patience=25, batch=8, imgsz=640) ต่างกันแค่เริ่มจาก yolov8m.pt (ใหญ่กว่า) ได้ `test-metrics-yolov8m.json`
3. ดาวน์โหลดทั้งสองไฟล์มาไว้เครื่องเดียวกัน แล้วรัน:
```cmd
.venv\Scripts\python.exe compare_models.py --baseline test-metrics.json --main test-metrics-yolov8m.json
```
ได้ตาราง precision/recall/mAP50/mAP50-95 เทียบ baseline กับโมเดลหลัก สำหรับใส่ในรายงาน Q2

หมายเหตุ: ตัวเลข YOLOv8n/v3 และ YOLOv8m/v2 ที่อ้างในสไลด์เดิม (presentation-images, presentation-v2) เทรนบนชุดข้อมูลคนละเวอร์ชัน เทียบตรงกันไม่ได้ — ให้ใช้ผลจากขั้นตอนด้านบนซึ่งเทรนบนชุด v3 เดียวกันทั้งคู่แทน

## ไฟล์สำคัญ
- web/: หน้าเว็บ ภาพตัวอย่าง และรูปถัง
- web_app.py: เซิร์ฟเวอร์และระบบตรวจจับ
- train.py / validate_dataset.py: ฝึกและตรวจป้ายกำกับ
- detect_realtime.py: ใช้กล้องผ่านโปรแกรม Python
- outputs/dashboard.sqlite3: ประวัติตรวจจับ
- outputs/ipad-tls/: ใบรับรอง HTTPS และกุญแจส่วนตัว ห้ามเผยแพร่กุญแจ
- outputs/feedback/: ภาพแจ้งทายผิด (สร้างเมื่อมีการส่งภาพ)
- outputs/model-diagnosis-real.json: ผลตรวจรุ่นก่อนสำหรับอ้างอิงรายงาน ไม่ใช่ผลชุด Test อิสระ
- .venv/: สภาพแวดล้อม Python ที่ใช้รันโปรแกรม

ระบบนับตาม Tracking ID หลังยืนยันประเภทเดิม 5 เฟรม ไม่ใช่จำนวนที่ทิ้งจริง
เสียงขึ้นกับอุปกรณ์ ภาพแจ้งทายผิดต้องตรวจทานและตีกรอบก่อนเทรน

## ตรวจสอบ
```cmd
.venv\Scripts\python.exe validate_dataset.py --data data.yaml
.venv\Scripts\python.exe -m unittest test_web_app -v
```

ชุดทดลอง 2000 รูปและชุดข้อมูลเก่าถูกลบเมื่อ 13 ตุลาคม 2026 ดูรายการใน outputs/cleanup-20261013.json
