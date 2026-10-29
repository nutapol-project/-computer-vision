const $=id=>document.getElementById(id);
const names={Recyclable:'รีไซเคิล',Organic:'อินทรีย์',General:'ทั่วไป',Hazardous:'อันตราย'};
const descriptions={Recyclable:'แยกลงถังรีไซเคิล ตามเกณฑ์ของพื้นที่ใช้งาน',Organic:'แยกลงถังอินทรีย์ ตามเกณฑ์ของพื้นที่ใช้งาน',General:'แยกลงถังทั่วไป ตามเกณฑ์ของพื้นที่ใช้งาน',Hazardous:'แยกลงถังขยะอันตราย ตามเกณฑ์ของพื้นที่ใช้งาน'};
const statuses={idle:'พร้อมเริ่มใช้งาน',starting:'กำลังเริ่มระบบ',running:'กำลังตรวจจับ',stopping:'กำลังหยุด',stopped:'หยุดการตรวจจับ',error:'ระบบขัดข้อง'};
const binColors={Recyclable:'#eab308',Organic:'#22c55e',General:'#3b82f6',Hazardous:'#ef4444'};
let soundEnabled=false,spokenSession=null,lastSpoken=0,batchStarted=0,cardSignature='';
const spoken=new Set();
const speechAvailable='speechSynthesis' in window&&'SpeechSynthesisUtterance' in window;
function say(text){
  if(!speechAvailable)return;
  window.speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(text);utterance.lang='th-TH';utterance.rate=0.95;
  const voice=window.speechSynthesis.getVoices().find(v=>v.lang.toLowerCase().startsWith('th'));
  if(voice)utterance.voice=voice;
  utterance.onerror=()=>{$('sound-status').textContent='เล่นเสียงไม่ได้ กรุณาตรวจเสียงภาษาไทยและระดับเสียงของอุปกรณ์';};
  window.speechSynthesis.speak(utterance);lastSpoken=Date.now();
}
$('sound-toggle').disabled=!speechAvailable;
if(!speechAvailable)$('sound-status').textContent='เบราว์เซอร์นี้ไม่รองรับเสียงอ่าน';
$('sound-toggle').onclick=()=>{
  soundEnabled=!soundEnabled;$('sound-toggle').setAttribute('aria-pressed',String(soundEnabled));
  $('sound-toggle').textContent=soundEnabled?'🔊 ปิดเสียง':'🔇 เปิดเสียง';
  if(soundEnabled){spoken.clear();say('เปิดเสียงแนะนำถังขยะแล้ว');}
  else window.speechSynthesis.cancel();
};
function renderCards(s){
  if(spokenSession!==s.session){spokenSession=s.session;spoken.clear();batchStarted=0;cardSignature='';if(speechAvailable)window.speechSynthesis.cancel();}
  const items=s.mode==='waste'&&s.status==='running'?s.detections.filter(d=>names[d.class]):[];
  const signature=JSON.stringify(items.map(d=>[d.id,d.class,d.confirmed]));
  if(signature!==cardSignature){
    cardSignature=signature;
    const fragment=document.createDocumentFragment();
    items.forEach(d=>{
      const card=document.createElement('article');card.className='detection-card';card.style.setProperty('--bin-color',binColors[d.class]);
      const bin=document.createElement('span');bin.className='card-bin';bin.setAttribute('role','img');bin.setAttribute('aria-label',`ถังขยะ${names[d.class]}`);
      bin.style.backgroundPosition=({Organic:'0%',Recyclable:'33.333333%',General:'66.666667%',Hazardous:'100%'})[d.class]+' center';
      const content=document.createElement('div');content.className='card-content';
      const title=document.createElement('h3');title.textContent=`ID ${d.id??'—'} · ขยะ${names[d.class]}`;
      const detail=document.createElement('p');detail.textContent=d.confirmed?`แนะนำถัง${names[d.class]}`:'รอยืนยันต่อเนื่อง 5 เฟรม';
      const confidence=document.createElement('p');confidence.className='card-confidence';
      const listen=document.createElement('button');listen.textContent='🔊 ฟังชิ้นนี้';listen.disabled=!speechAvailable||!d.confirmed;
      listen.onclick=()=>say(`ชิ้นหมายเลข ${d.id} ขยะ${names[d.class]} แนะนำถัง${names[d.class]}`);
      const correct=document.createElement('button');correct.textContent='ทายผิด';
      correct.onclick=()=>{$('feedback').scrollIntoView({behavior:'smooth'});$('feedback-class').value='';$('feedback-status').textContent=`เลือกภาพสำหรับแก้ไข ID ${d.id??'—'} แล้วระบุประเภทที่ถูกต้อง`;$('feedback-image').focus();};
      content.append(title,detail,confidence,listen,correct);card.append(bin,content);fragment.append(card);
    });
    $('detection-cards').replaceChildren(fragment);
  }
  document.querySelectorAll('.card-confidence').forEach((node,i)=>{node.textContent=`ความมั่นใจ ${Math.round(items[i].confidence*100)}%`;});
  document.querySelector('.recommend-body').hidden=items.length>0;
  if(!soundEnabled||!speechAvailable||document.hidden)return;
  if(s.status!=='running'){window.speechSynthesis.cancel();batchStarted=0;return;}
  const fresh=items.filter(d=>d.confirmed&&d.id!==null&&!spoken.has(`${d.id}:${d.class}`));
  if(!fresh.length){batchStarted=0;return;}
  if(!batchStarted)batchStarted=Date.now();
  if(Date.now()-batchStarted<1200||Date.now()-lastSpoken<6000||window.speechSynthesis.speaking)return;
  const counts={};fresh.forEach(d=>{counts[d.class]=(counts[d.class]||0)+1;spoken.add(`${d.id}:${d.class}`);});
  const message=Object.entries(counts).map(([cls,n])=>`ขยะ${names[cls]} ${n} ชิ้น แนะนำถัง${names[cls]}`).join(' และ ');
  say(`พบขยะที่ยืนยันใหม่ ${fresh.length} ชิ้น ${message}`);batchStarted=0;
}
let version=-1, frameUrl=null, session=null, busy=false, polling=false;
let cameraStream=null, cameraSession=null;
const cameraVideo=document.createElement('video'), cameraCanvas=document.createElement('canvas');
cameraVideo.muted=true;cameraVideo.autoplay=true;cameraVideo.playsInline=true;
cameraVideo.style.cssText='position:fixed;width:1px;height:1px;opacity:0;pointer-events:none';
document.body.append(cameraVideo);
function releaseCamera(){cameraSession=null;if(cameraStream)cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null;cameraVideo.srcObject=null;}
async function openCamera(){
  if(!window.isSecureContext||!navigator.mediaDevices)throw Error('กล้อง iPad ต้องเปิดผ่าน HTTPS และติดตั้งใบรับรองตามคู่มือก่อน');
  releaseCamera();
  cameraStream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:$('camera-facing').value},width:{ideal:960},height:{ideal:720}}});
  cameraVideo.srcObject=cameraStream;await cameraVideo.play();
}
async function sendCameraFrames(id){
  try{
    while(cameraSession===id&&cameraStream){
      const cycleStarted=performance.now();
      const w=cameraVideo.videoWidth,h=cameraVideo.videoHeight;
      if(w&&h){
        const scale=Math.min(1,960/Math.max(w,h));cameraCanvas.width=Math.round(w*scale);cameraCanvas.height=Math.round(h*scale);
        cameraCanvas.getContext('2d').drawImage(cameraVideo,0,0,cameraCanvas.width,cameraCanvas.height);
        const blob=await new Promise(resolve=>cameraCanvas.toBlob(resolve,'image/jpeg',0.75));
        if(cameraSession!==id)return;
        if(!blob)throw Error('สร้างภาพจากกล้องไม่ได้');
        const response=await fetch('/api/browser-frame',{method:'POST',headers:{'Content-Type':'image/jpeg','X-Camera-Session':id},body:blob,signal:AbortSignal.timeout(10000)});
        if(!response.ok)throw Error((await response.json()).error);
      }
      // One upload at a time, at most 10 FPS; slow networks never build a backlog.
      await new Promise(resolve=>setTimeout(resolve,Math.max(0,100-(performance.now()-cycleStarted))));
    }
  }catch(e){if(cameraSession===id){releaseCamera();error('ส่งภาพจากกล้องไม่ได้: '+e.message);}}
}
document.addEventListener('visibilitychange',()=>{if(document.hidden){releaseCamera();if(speechAvailable)window.speechSynthesis.cancel();}});
window.addEventListener('pagehide',releaseCamera);
$('date').textContent=new Date().toLocaleDateString('th-TH',{day:'numeric',month:'long',year:'numeric'});
function error(message){$('error').textContent=message||'';$('error').hidden=!message;}
async function command(action){
  busy=true;$('start').disabled=true;$('stop').disabled=true;error('');
  try{
    if(action==='stop')releaseCamera();
    if(action==='start')await openCamera();
    const response=await fetch('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:$('mode').value,source:'browser'})});
    const data=await response.json();if(!response.ok)throw Error(data.error);render(data);
    if(action==='start'&&cameraStream){cameraSession=data.session;sendCameraFrames(cameraSession);}
  }
  catch(e){releaseCamera();error(e.message);}finally{busy=false;poll();}
}
$('start').onclick=()=>command('start');$('stop').onclick=()=>command('stop');
function render(s){
  renderCards(s);
  const active=['starting','running','stopping'].includes(s.status), real=s.mode==='waste';
  if(cameraSession&&(!active||s.session!==cameraSession))releaseCamera();
  $('status').textContent='● '+statuses[s.status];
  $('start').disabled=active||busy;$('stop').disabled=!active||s.status==='stopping'||busy;
  for(const id of ['mode','camera-facing'])$(id).disabled=active||busy;
  $('waste-option').disabled=!s.model_ready;$('waste-option').textContent=s.model_ready?'ขยะ 4 ประเภท':'ขยะ 4 ประเภท · ยังไม่มีโมเดล';
  $('mode-note').hidden=real;$('mode-pill').textContent=real?'WASTE':'DEMO';
  $('feed-label').textContent=s.status==='running'?'LIVE':s.status==='starting'?'LOADING':'OFFLINE';
  $('fps').textContent=s.fps+' FPS';$('source-label').textContent=s.source==='sample'?'ภาพนิ่งตัวอย่างสำหรับทดสอบระบบ ไม่ใช่ภาพจากกล้อง':s.source==='browser'?'กล้อง iPad / อุปกรณ์ที่เปิดเว็บ · ส่งภาพให้คอมประมวลผล':'กล้องที่เชื่อมต่อกับเครื่องรันระบบ';
  $('frame-status').textContent=s.status==='running'?'กำลังประมวลผล':s.frames?'ภาพล่าสุด · หยุดแล้ว':'ยังไม่มีภาพ';
  $('live-dot').style.background=s.status==='running'?'#75c892':'#89968c';
  for(const name in names)$('count-'+name).textContent=real?(s.counts[name]||0):'—';
  $('total').replaceChildren(document.createTextNode(s.total+' '),Object.assign(document.createElement('small'),{textContent:real?'ชิ้น (ตาม ID)':'วัตถุทดลอง'}));
  if(s.error)error(s.error);
  let title='รอผลตรวจจับ',text='เริ่มตรวจจับเพื่อให้ระบบช่วยแนะนำถังที่เหมาะสม',label='WAITING FOR DETECTION',confidence=0;
  if(!real){title='โหมดทดลอง';text='ตรวจจับวัตถุทั่วไปเท่านั้น ยังไม่ใช้ผลนี้แนะนำถังขยะ';label='GENERAL OBJECT DETECTION';}
  else if(s.status==='running'){
    const candidates=s.detections.filter(d=>d.confirmed&&names[d.class]).sort((a,b)=>b.confidence-a.confidence);
    if(candidates.length){const d=candidates[0];title='ถัง'+names[d.class];text=descriptions[d.class]+' · ID '+d.id;label='เลือกวัตถุที่ยืนยันแล้วและมั่นใจสูงสุด';confidence=d.confidence;}
    else{text='กำลังรอให้พบประเภทเดิมต่อเนื่อง 5 เฟรม';}
  }
  $('recommend-title').textContent=title;$('recommend-text').textContent=text;$('recommend-label').textContent=label;
  $('confidence').textContent=confidence?Math.round(confidence*100)+'%':'—';$('confidence-bar').style.width=confidence*100+'%';
  if(session!==s.session){session=s.session;version=-1;$('frame').hidden=true;$('empty').hidden=false;if(frameUrl){URL.revokeObjectURL(frameUrl);frameUrl=null;}}
}
async function poll(){
  if(polling)return;polling=true;
  try{
    const response=await fetch('/api/state');if(!response.ok)throw Error('เชื่อมต่อระบบไม่ได้');const s=await response.json();
    if($('error').textContent.startsWith('เชื่อมต่อระบบไม่ได้:'))error('');
    render(s);
    if(s.frame_version!==version&&s.frames){
      const r=await fetch('/api/frame');
      if(r.status===200){
        const blob=await r.blob(),nextUrl=URL.createObjectURL(blob),image=new Image();
        try{
          image.src=nextUrl;await image.decode();
          if(session!==s.session){URL.revokeObjectURL(nextUrl);return;}
          const old=frameUrl;frameUrl=nextUrl;$('frame').src=nextUrl;
          $('frame').hidden=false;$('empty').hidden=true;
          if(old)URL.revokeObjectURL(old);version=s.frame_version;
        }catch(e){URL.revokeObjectURL(nextUrl);throw e;}
      }
    }
  }catch(e){$('status').textContent='● ขาดการเชื่อมต่อ';error('เชื่อมต่อระบบไม่ได้: '+e.message);}finally{polling=false;}
}
async function history(){
  try{const r=await fetch('/api/events');if(!r.ok)return;const rows=await r.json();if(!rows.length)return;
    const fragment=document.createDocumentFragment();for(const row of rows){const tr=document.createElement('tr');const values=[new Date(row.time).toLocaleString('th-TH'),String(row.track_id),names[row.class]||row.class,Math.round(row.confidence*100)+'%'];for(const value of values){const td=document.createElement('td');td.textContent=value;tr.append(td);}const td=document.createElement('td'),tag=document.createElement('span');tag.className='tag'+(row.mode==='waste'?' real':'');tag.textContent=row.mode==='waste'?'ขยะ 4 ประเภท':'ทดลอง';td.append(tag);tr.append(td);fragment.append(tr);}$('events').replaceChildren(fragment);
  }catch(e){/* State polling provides the connection status. */}
}
let feedbackPreview=null;
$('feedback-image').onchange=()=>{
  if(feedbackPreview)URL.revokeObjectURL(feedbackPreview);
  const file=$('feedback-image').files[0];$('feedback-preview').hidden=!file;
  if(file){feedbackPreview=URL.createObjectURL(file);$('feedback-preview').src=feedbackPreview;}
  $('feedback-status').textContent='';
};
$('feedback-form').onsubmit=async event=>{
  event.preventDefault();
  const file=$('feedback-image').files[0],category=$('feedback-class').value;
  if(!file||!names[category])return;
  if(file.size>12000000){$('feedback-status').textContent='ไฟล์ใหญ่เกิน 12 MB กรุณาเลือกรูปขนาดเล็กลง';return;}
  const controls=[$('feedback-submit'),$('feedback-image'),$('feedback-class')];controls.forEach(el=>el.disabled=true);
  $('feedback-status').textContent='กำลังบันทึก…';
  try{
    const response=await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream','X-Waste-Class':category},body:file});
    if(response.status===404)throw Error('กรุณาปิดแล้วเปิดโปรแกรมบนคอมใหม่ เพื่อใช้งานปุ่มทายผิด');
    const data=await response.json();if(!response.ok)throw Error(data.error);
    $('feedback-status').textContent=`บันทึกภาพเป็นขยะ${names[category]}แล้ว รอตรวจทานก่อนนำไปเทรน`;
    $('feedback-form').reset();$('feedback-preview').hidden=true;
    if(feedbackPreview){URL.revokeObjectURL(feedbackPreview);feedbackPreview=null;}
  }catch(e){$('feedback-status').textContent='บันทึกไม่สำเร็จ: '+e.message;}
  finally{controls.forEach(el=>el.disabled=false);}
};
poll();history();setInterval(poll,100);setInterval(history,2000);

const guideSteps=[
  ['#mode','เลือกโมเดล','เลือก “ขยะ 4 ประเภท” เพื่อแนะนำถัง ส่วนโหมดทดลองใช้ตรวจจับวัตถุทั่วไป หากตัวเลือกเปลี่ยนไม่ได้ ให้กดหยุดรอบปัจจุบันก่อน'],
  ['#camera-facing','กล้องของอุปกรณ์นี้','ระบบใช้กล้องของอุปกรณ์ที่เปิดเว็บโดยอัตโนมัติ เลือกกล้องหน้าหรือกล้องหลัง แล้วกดเริ่มตรวจจับและอนุญาตกล้อง'],
  ['.controls','เตรียมกล้อง','เลือกกล้องหน้าหรือกล้องหลังตามต้องการ ระบบจะใช้กล้องของอุปกรณ์ที่เปิดเว็บ ไม่ต้องเลือกแหล่งภาพหรือหมายเลขกล้อง'],
  ['#start','เริ่มตรวจจับ','กด “เริ่มตรวจจับ” และอนุญาตกล้องเมื่อมีข้อความถาม วางขยะให้เห็นชัด แสงเพียงพอ และเปิดหน้าเว็บค้างไว้ ปุ่มถัดไปในไกด์จะไม่เปิดกล้องให้เอง'],
  ['.recommendation','อ่านการ์ดผลตรวจจับ','แต่ละชิ้นมี ID ประเภท ความมั่นใจ และรูปถัง รอผลประเภทเดิมต่อเนื่อง 5 เฟรมเพื่อยืนยัน สีการ์ดตรงกับสีกรอบ คะแนนสูงไม่ได้รับประกันว่าทายถูกเสมอ'],
  ['#sound-toggle','เปิดเสียงแนะนำ','กด “เปิดเสียง” เพื่อฟังสรุปหลายประเภทเรียงกัน หรือกด “ฟังชิ้นนี้” บนการ์ดเพื่อฟังเฉพาะชิ้น กดปิดเสียงได้ทุกเมื่อ'],
  ['#feedback','ถ้าทายผิด ส่งภาพแก้ไข','กด “ทายผิด” บนการ์ด หรือใช้แบบฟอร์มนี้ อัปโหลด JPG, PNG หรือ WebP ไม่เกิน 12 MB เลือกประเภทที่ถูกต้อง แล้วกดบันทึก ใช้ภาพชิ้นเดียวหรือประเภทเดียวกัน ข้อมูลจะรอตรวจทาน ยังไม่เปลี่ยนโมเดลทันที'],
  ['#history','ดูประวัติและดาวน์โหลด','ดูรายการที่ยืนยันแล้วและกดส่งออก CSV ได้ จำนวนนี้นับตาม Tracking ID หาก ID เปลี่ยนอาจนับซ้ำ ไม่ใช่จำนวนขยะที่ทิ้งจริง'],
  ['#stop','หยุดเมื่อใช้เสร็จ','กด “หยุด” เพื่อจบการตรวจจับ หากต้องการเปลี่ยนโมเดลหรือกล้อง ให้หยุดก่อนแล้วเริ่มใหม่ สถิติรอบใหม่จะเริ่มนับใหม่ เปิดไกด์นี้ซ้ำได้จากเมนู “วิธีใช้”']
];
let guideIndex=0,guideTarget=null,guideReturn=null;
const guideSpotlight=document.createElement('div');
guideSpotlight.className='guide-spotlight';guideSpotlight.hidden=true;
guideSpotlight.setAttribute('aria-hidden','true');document.body.append(guideSpotlight);
let guideSpotlightFrame=null;
function updateGuideSpotlight(){
  if($('guide').hidden)return;
  if(guideTarget){
    const r=guideTarget.getBoundingClientRect(),pad=8;
    guideSpotlight.hidden=false;
    Object.assign(guideSpotlight.style,{left:(r.left-pad)+'px',top:(r.top-pad)+'px',
      width:(r.width+pad*2)+'px',height:(r.height+pad*2)+'px'});
  }
  guideSpotlightFrame=requestAnimationFrame(updateGuideSpotlight);
}
function showGuideStep(){
  if(guideTarget)guideTarget.classList.remove('guide-target');
  const [selector,title,text]=guideSteps[guideIndex];
  $('guide-progress').textContent=`ขั้นตอน ${guideIndex+1} / ${guideSteps.length}`;
  $('guide-title').textContent=title;$('guide-text').textContent=text;
  $('guide-back').disabled=guideIndex===0;
  $('guide-next').textContent=guideIndex===guideSteps.length-1?'เสร็จสิ้น ✓':'ถัดไป →';
  guideTarget=document.querySelector(selector);
  if(guideTarget){guideTarget.classList.add('guide-target');guideTarget.scrollIntoView({behavior:'smooth',block:'start'});}
}
function closeGuide(){
  cancelAnimationFrame(guideSpotlightFrame);guideSpotlightFrame=null;guideSpotlight.hidden=true;
  $('guide').hidden=true;document.body.classList.remove('guide-active');
  if(guideTarget)guideTarget.classList.remove('guide-target');guideTarget=null;
  if(guideReturn)guideReturn.focus({preventScroll:true});
}
$('guide-open').onclick=()=>{
  guideReturn=document.activeElement;guideIndex=0;$('guide').hidden=false;
  document.body.classList.add('guide-active');showGuideStep();$('guide-next').focus({preventScroll:true});
  cancelAnimationFrame(guideSpotlightFrame);updateGuideSpotlight();
};
$('guide-back').onclick=()=>{if(guideIndex>0){guideIndex--;showGuideStep();}};
$('guide-next').onclick=()=>{if(guideIndex<guideSteps.length-1){guideIndex++;showGuideStep();}else closeGuide();};
$('guide-skip').onclick=closeGuide;
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('guide').hidden)closeGuide();});
