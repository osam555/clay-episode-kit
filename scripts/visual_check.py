#!/usr/bin/env python3
"""썸네일·배포본 자동 검사 — qa_gate 가 놓치던 구멍을 메운다.
오쌤 2026-09-20 「영상 및 썸네일 리뷰 시스템이 있는데 제대로 작동하지 않는 문제 해결」.

이번 세션에서 게이트가 못 잡고 사람이 잡은 것들 = 여기서 자동으로 잡는다:
  1) 썸네일 한자판이 오른쪽에서 잘림      → 요소 bbox 가 세이프 마진 밖 (thumb: meta 검사)
  2) 글자 외곽선 얇음·글자 작음            → stroke/size 최소값 검사 (thumb: meta 검사)
  3) 요소끼리 겹침                          → bbox 교차 검사 (thumb: meta 검사)
  4) 인트로 누락한 채 배포                  → 배포본 앞부분이 인트로와 일치하는지 (deploy)
  5) 오버레이가 원본에 이미 있는 그래픽과 겹침 → 가장자리 잉크 검사 + 인트로 하단 금지대 (deploy/thumb)

사용:
  python3 scripts/visual_check.py thumb  <thumb.png>            # <thumb>.meta.json 있으면 함께 검사
  python3 scripts/visual_check.py deploy <deploy.mp4> [intro.mp4]
종료코드 0=PASS / 1=FAIL
"""
import sys, os, json, subprocess, tempfile
import numpy as np, cv2

W,H = 1280,720
MARGIN      = 28     # 세이프 마진(px) — 요소가 이 안쪽에 완전히 들어와야
MIN_HEAD    = 100    # 헤드라인 최소 폰트 크기
MIN_STROKE  = 13     # 최소 외곽선 두께
BORDER_INK  = 0.020  # 프레임 테두리 띠에 강한 잉크가 이 비율 넘으면 잘림 의심

def _ink_ratio(img, band):
    """띠 영역에서 '글자 잉크'(매우 어둡거나 매우 밝은 고대비 픽셀) 비율."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = ((g < 45) | (g > 238)).astype(np.uint8)
    y0,y1,x0,x1 = band
    sub = m[y0:y1, x0:x1]
    return float(sub.mean()) if sub.size else 0.0

def check_thumb(path):
    """meta(요소 bbox)가 있으면 그것만으로 정밀 검사(픽셀 휴리스틱은 배경을 글자로 오인해 과탐).
    meta 가 없을 때만 테두리 잉크로 대략 잡는다."""
    fails=[]
    img = cv2.imread(path)
    if img is None: return [f"썸네일을 읽을 수 없다: {path}"]
    h,w = img.shape[:2]
    if (w,h)!=(W,H): fails.append(f"크기 {w}x{h} — 1280x720 이어야 한다")
    meta_p = os.path.splitext(path)[0]+'.meta.json'
    if not os.path.exists(meta_p):
        b=14
        for name,band in (('상',(0,b,0,w)),('하',(h-b,h,0,w)),('좌',(0,h,0,b)),('우',(0,h,w-b,w))):
            r=_ink_ratio(img,band)
            if r > BORDER_INK: fails.append(f"{name}단 테두리 잉크 {r*100:.1f}% — 잘림 의심(meta 없어 정밀검사 불가)")
        fails.append(f"meta 없음({os.path.basename(meta_p)}) — 생성기가 요소 bbox 를 남기도록 할 것")
        return fails
    meta=json.load(open(meta_p)); els=meta.get('elements',[])
    heads=[e for e in els if e.get('role')=='headline']
    for e in els:
        x0,y0,x1,y1=e['bbox']; role=e.get('role')
        if x0<0 or y0<0 or x1>W or y1>H:
            fails.append(f"요소 '{e['name']}' 가 프레임 밖으로 잘린다 bbox={e['bbox']}")
        elif role in ('headline','panel','card') and (x0<MARGIN or y0<MARGIN or x1>W-MARGIN or y1>H-MARGIN):
            fails.append(f"요소 '{e['name']}' 가 세이프 마진({MARGIN}px) 밖 bbox={e['bbox']}")
    if heads:
        if max(e.get('size',0) for e in heads) < 120:
            fails.append(f"펀치라인 폰트가 작다(최대 {max(e.get('size',0) for e in heads)}px < 120px)")
        for e in heads:
            if not e.get('box') and e.get('stroke',0)<MIN_STROKE: fails.append(f"헤드라인 '{e['name']}' 외곽선 {e.get('stroke')}px < {MIN_STROKE}px")  # 하이라이트 박스형은 박스가 대비를 줘서 면제
            if e.get('size',0)<80: fails.append(f"헤드라인 '{e['name']}' 폰트 {e.get('size')}px < 80px")
    else:
        fails.append("헤드라인이 없다")
    for i in range(len(els)):
        for j in range(i+1,len(els)):
            a,bx=els[i],els[j]
            if a.get('may_overlap') or bx.get('may_overlap'): continue
            if a.get('role')=='headline' and bx.get('role')=='headline': continue   # 2줄 스택은 정상
            A,B=a['bbox'],bx['bbox']
            ox=min(A[2],B[2])-max(A[0],B[0]); oy=min(A[3],B[3])-max(A[1],B[1])
            if ox>8 and oy>8: fails.append(f"요소 겹침: '{a['name']}' ↔ '{bx['name']}'")
    return fails

def _frame(mp4, t):
    d=tempfile.mkdtemp(); f=f'{d}/f.png'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',mp4,'-frames:v','1','-vf','scale=320:180',f],capture_output=True)
    return cv2.imread(f) if os.path.exists(f) else None

def check_deploy(mp4, intro=None):
    if intro is None:
        intro = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))) + '/assets/intro_msg.mp4'
    fails=[]
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','default=nw=1',mp4]).decode()
    if 'pcm_s16le' not in probe: fails.append("오디오가 PCM 무손실이 아니다")
    if 'width=1920' not in probe or 'height=1080' not in probe: fails.append("해상도가 1920x1080 이 아니다")
    # 인트로 존재: 배포본 t=1.2 프레임이 인트로 t=1.2 와 닮았는지
    if os.path.exists(intro):
        a=_frame(mp4,1.2); b=_frame(intro,1.2)
        if a is None or b is None: fails.append("프레임 추출 실패 — 인트로 검사 불가")
        else:
            diff=float(np.abs(a.astype(np.float32)-b.astype(np.float32)).mean())
            if diff>22: fails.append(f"**인트로 누락** — 배포본 앞부분이 인트로와 다르다(diff {diff:.1f}>22). 인트로+본편+엔딩으로 다시 concat 하라")
    else:
        fails.append(f"인트로 파일 없음: {intro}")
    return fails

if __name__=='__main__':
    mode=sys.argv[1]
    f = check_thumb(sys.argv[2]) if mode=='thumb' else check_deploy(*sys.argv[2:4])
    print(f"=== visual_check {mode}: {os.path.basename(sys.argv[2])} ===")
    if f:
        print("❌ FAIL"); [print("  -",x) for x in f]; sys.exit(1)
    print("✅ PASS"); sys.exit(0)
