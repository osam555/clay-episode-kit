#!/usr/bin/env python3
"""시선 밀도 측정 — 초당 「움직이는 영역 수」(독립 움직임 블롭)와 화면 변화율.
사용: python3 motion_density.py <video> [start] [dur]
10fps 로 뽑아 연속 프레임 차이를 24x14 격자로 나누고, 변화 격자를 4-연결 블롭으로 묶어 개수를 센다.
'시선 1개' = 독립적으로 움직이는 블롭 1개. 컷 전환(전체 변화 >60%)은 별도로 센다."""
import subprocess, sys, numpy as np, tempfile, os, glob
from PIL import Image
v=sys.argv[1]; st=float(sys.argv[2]) if len(sys.argv)>2 else 0; du=float(sys.argv[3]) if len(sys.argv)>3 else 60
d=tempfile.mkdtemp(); FPS=10
subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(st),'-t',str(du),'-i',v,'-vf',f'fps={FPS},scale=240:135','-pix_fmt','gray',f'{d}/f%05d.png'],check=True)
fr=[np.asarray(Image.open(f),dtype=np.float32) for f in sorted(glob.glob(f'{d}/*.png'))]
GX,GY=24,14; H,W=fr[0].shape; ch,cw=H//GY,W//GX
blobs_per_frame=[]; cuts=0; change=[]
def label(mask):
    seen=np.zeros_like(mask,bool); n=0
    for y in range(GY):
        for x in range(GX):
            if mask[y,x] and not seen[y,x]:
                n+=1; stack=[(y,x)]; seen[y,x]=True
                while stack:
                    cy,cx=stack.pop()
                    for ny,nx in((cy+1,cx),(cy-1,cx),(cy,cx+1),(cy,cx-1)):
                        if 0<=ny<GY and 0<=nx<GX and mask[ny,nx] and not seen[ny,nx]: seen[ny,nx]=True; stack.append((ny,nx))
    return n
for a,b in zip(fr,fr[1:]):
    diff=np.abs(b-a)
    g=diff[:GY*ch,:GX*cw].reshape(GY,ch,GX,cw).mean(axis=(1,3))
    mask=g>6.0
    frac=mask.mean(); change.append(frac)
    if frac>0.6: cuts+=1; continue
    blobs_per_frame.append(label(mask))
bp=np.array(blobs_per_frame)
sec=len(fr)/FPS
print(f"{os.path.basename(v)}  {st:.0f}s+{sec:.0f}s  컷전환 {cuts}회({cuts/sec*60:.1f}/분)  움직임블롭/프레임 평균 {bp.mean():.2f}  중앙값 {np.median(bp):.1f}  정지프레임(블롭0) {100*(bp==0).mean():.0f}%  화면변화율 평균 {np.mean(change)*100:.1f}%")
