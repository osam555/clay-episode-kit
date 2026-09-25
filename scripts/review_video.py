#!/usr/bin/env python3
"""자동 리뷰 게이트 — 영상 전 구간을 촘촘히 훑어 '빈 중앙' 구간(span)을 잡는다.
사람 눈 스팟체크·합리화 금지. **1.5초 이상 빈 중앙 span 이 하나라도 있으면 실패(exit 1).**
usage: python3 scratch/review_video.py <video.mp4> [detect_step=0.5]
출력: 컨택트시트 PNG(2초 간격) + 빈-중앙 span 목록[start~end dur].
"""
import sys, subprocess, os, tempfile
from PIL import Image, ImageDraw, ImageFont

video = sys.argv[1]
step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
MIN_SPAN = 1.5          # 이 이상 빈 중앙이 이어지면 실패
BX0,BX1,BY0,BY1 = 0.18,0.82,0.24,0.72   # 중앙 콘텐츠 박스(상단 헤더·하단 자막 제외)
BRIGHT = 165           # 텍스트(밝은 분필/금빛) 임계 — 배경 라디얼 최대 ~116
MIN_FRAC = 0.006       # 중앙 밝은 픽셀 비율 최소치(0.6%)

def dur(f):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]).decode().strip())
D = dur(video)
tmp = tempfile.mkdtemp()

def center_frac(t):
    fp = f'{tmp}/d_{t}.png'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',video,'-frames:v','1','-vf','scale=480:270',fp],check=True)
    im = Image.open(fp).convert('RGB'); W,H = im.size
    raw = im.crop((int(W*BX0),int(H*BY0),int(W*BX1),int(H*BY1))).tobytes(); n=len(raw)//3
    bright = sum(1 for i in range(0,len(raw),3) if (0.299*raw[i]+0.587*raw[i+1]+0.114*raw[i+2])>BRIGHT)
    os.remove(fp)
    return bright/n

# 촘촘 검출
ts, empties = [], []
t = 0.2
while t < D-0.1:
    ts.append(round(t,2)); t += step
flags = [(round(t,2), center_frac(round(t,2))<MIN_FRAC) for t in ts]
# 연속 빈 구간 병합
spans, run = [], None
for t,empty in flags:
    if empty and run is None: run=[t,t]
    elif empty: run[1]=t
    elif run is not None: spans.append(run); run=None
if run: spans.append(run)
spans = [(a,b,round(b-a+step,2)) for a,b in spans]
bad = [s for s in spans if s[2] >= MIN_SPAN]

# 컨택트시트(2초 간격)
sheet_ts = []
t=0.3
while t<D-0.1: sheet_ts.append(round(t,2)); t+=2.0
cols,cw,ch,pad=6,300,169,6
rows=(len(sheet_ts)+cols-1)//cols
sheet=Image.new('RGB',(cols*(cw+pad)+pad,rows*(ch+pad)+pad),(24,28,24))
drw=ImageDraw.Draw(sheet)
try: fnt=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',16)
except: fnt=ImageFont.load_default()
for i,t in enumerate(sheet_ts):
    fp=f'{tmp}/s_{t}.png'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',video,'-frames:v','1','-vf','scale=300:169',fp],check=True)
    th=Image.open(fp); r,c=divmod(i,cols); x,y=pad+c*(cw+pad),pad+r*(ch+pad)
    frac=center_frac(t); ok=frac>=MIN_FRAC
    sheet.paste(th,(x,y)); col=(120,220,120) if ok else (240,80,80)
    drw.rectangle([x,y,x+cw,y+ch],outline=col,width=3)
    drw.text((x+5,y+3),f'{t}s {frac*100:.1f}%'+('' if ok else ' EMPTY'),fill=col,font=fnt)
out=os.path.splitext(video)[0]+'_review.png'; sheet.save(out)

print(f'sampled {len(flags)} @ {step}s · sheet → {out}')
if spans:
    print('빈 중앙 구간:')
    for a,b,d in spans:
        mark = '❌' if d>=MIN_SPAN else '·'
        print(f'   {mark} {a}s ~ {b}s  ({d}s)')
if bad:
    print(f'❌ FAIL — {len(bad)}개 구간이 {MIN_SPAN}s 이상 빈 중앙'); sys.exit(1)
print('✅ PASS — 1.5s 이상 빈 중앙 없음')
