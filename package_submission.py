from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, ast

root=Path(__file__).resolve().parent
out=root/'submission-separated'
out.mkdir(exist_ok=True)
common=['web_app.py','public_app.py','start_public.py','start_public.cmd','stop_public.cmd','start_ipad.py','start_ipad.cmd','requirements.txt','requirements-lock.txt','PUBLIC_LINK.md','IPAD_CAMERA.md']
web=[p.relative_to(root).as_posix() for p in (root/'web').rglob('*') if p.is_file() and p.suffix in {'.html','.js','.css','.png','.jpg'}]
source=common+web+['train.py','detect_realtime.py','validate_dataset.py','test_web_app.py','test_public_app.py','data.yaml','kaggle_train_waste_real_v3_hazard_single.ipynb','DATASET_STATUS.md']
runtime=common+web+['best.pt','yolov8n.pt','tools/cloudflared.exe']
dataset=root/'dataset_waste_real_v3_hazard_single'
resources=[p.relative_to(root).as_posix() for p in dataset.rglob('*') if p.is_file() and (('images' in p.relative_to(dataset).parts or 'labels' in p.relative_to(dataset).parts) and p.suffix.lower() in {'.jpg','.jpeg','.png','.txt'} or p.name in {'classes.txt','summary.json','datasetreal-v3-hazard-single.marker'})]
setup=r'''@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Setup complete. Run START_LOCAL.cmd
pause
exit /b 0
:fail
echo Setup failed. Install Python 3.12 and check internet access.
pause
exit /b 1
'''
start=r'''@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set YOLO_CONFIG_DIR=outputs\ultralytics-config
if not exist ".venv\Scripts\python.exe" (
echo Run SETUP_WINDOWS.cmd first.
pause
exit /b 1
)
echo Open http://127.0.0.1:8080 in your browser.
".venv\Scripts\python.exe" web_app.py
pause
'''
readme='''ชุดส่งงานระบบแยกขยะ 4 ประเภทด้วย YOLO

01_SourceCode.zip: โค้ดเว็บ เซิร์ฟเวอร์ สคริปต์ฝึก Notebook และการทดสอบ
02_Application.zip: โค้ดที่ใช้รัน โมเดล best.pt โมเดลทดลอง yolov8n.pt และ cloudflared.exe
03_Resources.zip: ชุดข้อมูลล่าสุด 200 ภาพ / 229 กรอบ Train 151, Validation 25, Test 24

ชุด Application เป็นแอป Python ไม่ใช่ executable แบบ standalone
ต้องติดตั้ง Python 3.12 และเชื่อมอินเทอร์เน็ตในการติดตั้ง dependencies
แตก 02_Application.zip แล้วเปิด SETUP_WINDOWS.cmd รอจนติดตั้งสำเร็จ
เปิด START_LOCAL.cmd แล้วเข้า http://127.0.0.1:8080 เลือกโมเดลขยะ
ถ้าต้องการลิงก์สาธารณะ เปิด start_public.cmd หลังติดตั้ง เปิดคอมค้างไว้
หยุดลิงก์สาธารณะด้วย stop_public.cmd
requirements.txt ระบุ dependencies ที่ต้องติดตั้ง ไม่ได้แนบแพ็กเกจ Python แบบออฟไลน์
requirements-lock.txt เป็นรายการเวอร์ชันเครื่องพัฒนาเพื่ออ้างอิง ไม่รับประกันติดตั้งได้ทุกเครื่อง

สำหรับฝึก: แตก SourceCode และ Resources ไว้ที่เดียวกัน จะได้โฟลเดอร์ dataset_waste_real_v3_hazard_single ข้าง data.yaml
Notebook บน Kaggle ใช้ชุดข้อมูล Resources ตามขั้นตอนใน Notebook
หากต้องการรัน SourceCode ให้คัดลอก best.pt และ yolov8n.pt จากชุด Application มาไว้ข้าง web_app.py

ไม่รวม .venv ประวัติผู้ใช้ ภาพ feedback ใบรับรอง กุญแจส่วนตัว ลิงก์ชั่วคราว และข้อมูลรุ่นเก่า
ยังไม่ได้ทดสอบติดตั้ง dependencies บนเครื่องใหม่ จึงควรทดลองก่อนส่งมอบ
ข้อ (ii) ของโจทย์เป็น IF APPLICABLE ชุดนี้เป็นทางเลือกสำหรับติดตั้งแอป Python ไม่อ้างว่าเป็น .exe ของระบบ
'''
manifest=[]
def pack(name,files,extras):
    path=out/name
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for f in sorted(set(files)):
            p=root/f
            assert p.is_file(),f
            if p.suffix=='.py': ast.parse(p.read_text(encoding='utf-8-sig'))
            z.write(p,f)
        for f,content in extras.items():z.writestr(f,content.encode('utf-8'))
    with ZipFile(path) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert not any('/feedback/' in n or n.startswith(('outputs/','.venv/')) or n.endswith(('.key','.pem','.sqlite3')) for n in names)
    manifest.append({'file':name,'entries':len(names),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
pack('01_SourceCode.zip',source,{'README_SUBMISSION.txt':readme,'SETUP_WINDOWS.cmd':setup,'START_LOCAL.cmd':start})
pack('02_Application.zip',runtime,{'README_SUBMISSION.txt':readme,'SETUP_WINDOWS.cmd':setup,'START_LOCAL.cmd':start})
pack('03_Resources.zip',resources,{'README_SUBMISSION.txt':readme,'data.yaml':(root/'data.yaml').read_text(encoding='utf-8'),'dataset_waste_real_v3_hazard_single/data.yaml':(root/'data.yaml').read_text(encoding='utf-8')})
counts={s:len([p for p in (dataset/'images'/s).iterdir() if p.suffix.lower() in {'.jpg','.jpeg','.png'}]) for s in ['train','val','test']}
assert counts=={'train':151,'val':25,'test':24},counts
boxes=0
for split in counts:
    for p in (dataset/'images'/split).iterdir():
        if p.suffix.lower() not in {'.jpg','.jpeg','.png'}:continue
        label=dataset/'labels'/split/(p.stem+'.txt')
        assert label.is_file(),str(label)
        boxes+=sum(bool(l.strip()) for l in label.read_text().splitlines())
assert boxes==229,boxes
(out/'README_SUBMISSION.txt').write_text(readme,encoding='utf-8')
(out/'manifest.json').write_text(json.dumps({'archives':manifest,'images':counts,'boxes':boxes,'checks':'ZIP integrity, allowlist, Python syntax, image-label pairs; no clean-machine install test'},indent=2),encoding='utf-8')
print(json.dumps({'archives':[{'file':x['file'],'MB':round(x['bytes']/1048576,2)} for x in manifest],'images':counts,'boxes':boxes}))
