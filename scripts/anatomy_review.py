#!/usr/bin/env python3
"""자동 해부(손·손가락) 리뷰 게이트 — AI 영상 손 기형을 배포 전에 강제로 드러낸다.
오쌤 2026-09-20 「손등이 비정상적이다, 리뷰에서 자동으로 나오게」.

신뢰 가능한 2단계(스킨/텍스처 휴리스틱은 클레이·크림배경에 오탐이라 안 씀):
 1) 정책 자동 판정 — cuts.json 의 kind 가 real/hist(실사 사람) = 손 기형 고위험 → 자동 WARN + kid 교체 권장.
    이 파이프라인은 실사 사람 손/얼굴 클로즈업을 쓰지 않는다(스타일 clay 로). C14 실사 손 기형이 계기.
 2) 육안 강제 — 모든 컷의 하단 중앙(손이 자주 오는 자리)을 3배 확대해 contact sheet 로 저장.
    에이전트는 배포 전 이 시트를 반드시 열어 손등·손가락 개수·관절을 확인한다(자동으로 시트가 나오므로 놓칠 수 없음).

사용: python3 scripts/anatomy_review.py <clips_dir> [cuts.json]
"""
import sys, os, glob, subprocess, tempfile, json
import numpy as np, cv2

def zoom_bottom(clip, t=1.2):
    d=tempfile.mkdtemp(); f=f'{d}/f.png'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',clip,'-frames:v','1','-vf','scale=1280:720',f],capture_output=True)
    if not os.path.exists(f): return None
    im=cv2.imread(f)
    crop=im[360:720, 320:960]          # 하단 중앙(손·동작이 자주 오는 영역)
    return cv2.resize(crop,(480,480))

def main(clips, kinds):
    tiles=[]; warns=[]
    for clip in clips:
        n=os.path.basename(clip); k=kinds.get(n[:-4] if n.endswith('.mp4') else n) or kinds.get(n) or '?'
        risk = k in ('real','hist')
        print(f"{n}  kind={k}  {'⚠ 실사 사람 — 손 기형 고위험, kid 교체 권장' if risk else '(clay) 손 확대 검수'}")
        if risk: warns.append(n)
        z=zoom_bottom(clip)
        if z is not None:
            cv2.rectangle(z,(0,0),(480,34),(0,0,0),-1)
            cv2.putText(z,f"{n} {k}{' WARN' if risk else ''}",(6,25),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255) if risk else (200,255,200),2)
            tiles.append(z)
    if tiles:
        cols=5; rows=(len(tiles)+cols-1)//cols; sheet=np.full((rows*480,cols*480,3),40,np.uint8)
        for i,t in enumerate(tiles):
            r,c=divmod(i,cols); sheet[r*480:r*480+480,c*480:c*480+480]=t
        outp=os.path.join(base,'_anatomy_review.png'); cv2.imwrite(outp,sheet)
        print(f"\n손 확대 시트 → {outp}  (에이전트: 배포 전 반드시 열어 손가락 개수·손등·관절 확인)")
    print(f"\n실사 WARN {len(warns)}컷: {warns or '없음'} — 실사 사람 손 클로즈업 금지, kid 로 교체")

if __name__=='__main__':
    if len(sys.argv)<2: sys.exit('사용법: anatomy_review.py <clips_dir> [cuts.json]')
    p=sys.argv[1]; base=p if os.path.isdir(p) else (os.path.dirname(p) or '.')
    # 2026-09-20 버그: 'C*.mp4' 만 잡아 N*.mp4(simst2·day 신규 컷)를 0컷으로 통과시켰다 → 모든 mp4(밑줄 파일 제외)
    clips=sorted(f for f in glob.glob(f'{p}/*.mp4') if not os.path.basename(f).startswith('_')) if os.path.isdir(p) else [p]
    if '--extra' in sys.argv:   # 다른 편에서 재사용한 클립도 같이 검수 (qa_gate 가 prompts/<id>.json map 에서 넘긴다)
        i=sys.argv.index('--extra'); clips+= [c for c in sys.argv[i+1:] if os.path.exists(c)]; sys.argv=sys.argv[:i]
    if not clips: print(f"⚠ 검수할 클립 0개: {p}");
    kinds={}
    cj=sys.argv[2] if len(sys.argv)>2 else None
    if cj and os.path.exists(cj):
        for c in json.load(open(cj)): kinds[f"C{c['n']:02d}"]=c.get('kind')
    main(clips, kinds)
