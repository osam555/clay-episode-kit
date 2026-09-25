#!/usr/bin/env python3
"""썸네일 벤치마크 평가기 — 「유명 유튜브 썸네일 수준」을 재는 항목을 수치로, 나머지는 모바일 시트로 에이전트가 판정.
오쌤 2026-09-20 「썸네일 리뷰시스템을 작동해야지 나한테 하라고 하지 말고」.

수치 항목(자동 FAIL/WARN):
  1 모바일 가독  펀치라인 글자 높이 ≥ 25px @320×180(=원본 ≥100px), 보조줄 ≥ 20px
  2 대비        헤드라인 bbox 안 휘도 미켈슨 대비 ≥ 0.55 (흰/노랑 글자 vs 외곽선·배경)
  3 배지 겹침   유튜브 재생시간 배지(우하단 ~ x>1160, y>676) 와 겹치는 요소 → WARN(브랜드/글자 가림)
  4 글자 면적   헤드라인 bbox 합 ≤ 42% 화면 (이미지가 보여야 한다)
  5 글자 수     헤드라인 총 ≤ 14자, 줄 ≤ 2
  6 대각 균형   헤드라인 무게중심과 한자판/카드 무게중심이 서로 다른 좌우·상하 사분면
시트: <thumb>_review.png — 원본 · 320×180(피드) · 168×94(사이드바) 나란히 → 에이전트가 「한눈에 읽힘·호기심·감정·이미지 가림」을 보고 review_log 에 남긴다.

사용: python3 scripts/thumb_review.py <thumb.png> [...]   (meta.json 필요)   종료코드 1=FAIL
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw

BADGE=(1160,676,1280,720)   # 1280×720 기준 재생시간 배지 대략 영역

def deadspace(im):
    """죽은(빈 배경) 공간 비율과 상단 절반 빔 — 유명 채널 18~37%, 낙제(작은 피사체+빈 배경) 60%+ (2026-09-20 실측).
    **배경색**과 비슷하면서 평평한 칸만 센다: 매끈한 클레이 얼굴(피사체)은 평평해도 배경색이 아니라 안 센다."""
    import numpy as np
    rgb=np.asarray(im.convert('RGB').resize((640,360))).astype(float); g=rgb.mean(2)
    # 배경색 = 네 모서리 20x20 평균(피사체가 모서리까지 차면 죽은 공간이 낮게 나와 옳다)
    corners=np.vstack([rgb[:20,:20].reshape(-1,3),rgb[:20,-20:].reshape(-1,3),rgb[-20:,:20].reshape(-1,3),rgb[-20:,-20:].reshape(-1,3)])
    bg=corners.mean(0); flat=np.zeros((18,32))
    for r in range(18):
        for c in range(32):
            blk=rgb[r*20:r*20+20,c*20:c*20+20]
            if g[r*20:r*20+20,c*20:c*20+20].std()<12 and np.abs(blk.reshape(-1,3).mean(0)-bg).sum()<45: flat[r,c]=1
    return flat.mean()*100, flat[:9].mean()*100

def lum(a): return 0.2126*a[...,0]+0.7152*a[...,1]+0.0722*a[...,2]
def inter(A,B): return not (A[2]<=B[0] or B[2]<=A[0] or A[3]<=B[1] or B[3]<=A[1])

def review(p):
    meta_p=p[:-4]+'.meta.json'
    if not os.path.exists(meta_p): return [f'meta 없음 {os.path.basename(meta_p)}'], [], None
    m=json.load(open(meta_p)); im=Image.open(p).convert('RGB'); W,H=im.size; a=np.asarray(im).astype(float); L=lum(a)
    fails=[]; warns=[]; rows=[]
    # 0 구도 — 죽은 공간(유명 채널 기준). 45%↑ FAIL, 38~45% WARN
    dead,topempty=deadspace(im)
    rows.append(f"구도 죽은공간 {dead:.0f}% · 상단빔 {topempty:.0f}% (유명 채널 18~37%, 기준 <45%)")
    if dead>=45: fails.append(f"죽은 공간 {dead:.0f}% ≥45% — 피사체가 프레임을 못 채움(줌/구도)")
    elif dead>=38: warns.append(f"죽은 공간 {dead:.0f}% (38~45% 경계, 더 채우면 좋음)")
    if topempty>=60: warns.append(f"상단 절반 {topempty:.0f}% 빔 — 피사체를 위로 키우거나 요소 배치")
    heads=[e for e in m['elements'] if e.get('role')=='headline']
    others=[e for e in m['elements'] if e.get('role') in ('panel','card')]
    # 1 모바일 가독
    big=max(heads,key=lambda e:e.get('size',0)) if heads else None
    for e in heads:
        mob=e.get('size',0)*180/H
        need=25 if e is big else 20
        rows.append(f"가독 '{e['name']}' {e.get('size')}px → 모바일 {mob:.0f}px (기준 {need})")
        if mob<need: fails.append(f"모바일 가독 '{e['name']}' {mob:.0f}px < {need}px")
    # 2 대비
    for e in heads:
        x0,y0,x1,y1=[max(0,v) for v in e['bbox']]; reg=L[y0:min(H,y1), x0:min(W,x1)]
        if reg.size==0: continue
        p5,p95=np.percentile(reg,5),np.percentile(reg,95); c=(p95-p5)/(p95+p5+1e-6)
        rows.append(f"대비 '{e['name']}' {c:.2f} (기준 ≥0.55)")
        if c<0.55: fails.append(f"대비 부족 '{e['name']}' {c:.2f}")
    # 3 배지 겹침
    for e in m['elements']:
        if inter(e['bbox'],BADGE): warns.append(f"재생시간 배지에 가림: '{e['name']}' bbox={e['bbox']}")
    # 4 면적
    area=sum(max(0,e['bbox'][2]-e['bbox'][0])*max(0,e['bbox'][3]-e['bbox'][1]) for e in heads)/(W*H)
    rows.append(f"글자 면적 {area*100:.0f}% (기준 ≤42%)")
    if area>0.42: fails.append(f"글자 면적 {area*100:.0f}% > 42%")
    # 5 글자 수
    chars=sum(len(e['name'].replace(' ','')) for e in heads)
    rows.append(f"글자 {chars}자 / {len(heads)}줄 (기준 ≤14자·2줄)")
    if chars>14: fails.append(f"헤드라인 {chars}자 > 14")
    if len(heads)>2: fails.append(f"헤드라인 {len(heads)}줄 > 2")
    # 6 대각 균형
    def com(es):
        xs=[(e['bbox'][0]+e['bbox'][2])/2 for e in es]; ys=[(e['bbox'][1]+e['bbox'][3])/2 for e in es]; return sum(xs)/len(xs), sum(ys)/len(ys)
    if heads and others:
        hx,hy=com(heads); ox,oy=com(others)
        diag=((hx<W/2)!=(ox<W/2)) and ((hy<H/2)!=(oy<H/2))
        rows.append(f"대각 균형 {'✓' if diag else '✗'} (헤드라인 {hx:.0f},{hy:.0f} / 판 {ox:.0f},{oy:.0f})")
        if not diag: warns.append("헤드라인과 한자판이 대각이 아님(한쪽 쏠림)")
    # 시트
    sheet=Image.new('RGB',(W+340+20*3, H+40),(30,30,30)); d=ImageDraw.Draw(sheet)
    sheet.paste(im,(10,30)); sheet.paste(im.resize((320,180),Image.LANCZOS),(W+30,30)); sheet.paste(im.resize((168,94),Image.LANCZOS),(W+30,230))
    d.text((10,8),os.path.relpath(p),fill=(255,255,255)); d.text((W+30,8),'320×180 피드',fill=(255,255,255)); d.text((W+30,215),'168×94 사이드바',fill=(255,255,255))
    out=p[:-4]+'_review.png'; sheet.save(out)
    return fails, warns, (rows,out)

def score_of(fails,warns):
    """점수제(오쌤 2026-09-20): 10점 만점, hard -3, warn -1. RUBRIC thumbnail.pass(기본 8.0) 이상 PASS."""
    return max(0.0, 10.0-3*len(fails)-1*len(warns))

def threshold():
    p=os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))+'/data/longform/reviews/RUBRIC.json'
    try: rb=json.load(open(p)); return rb['stages']['thumbnail'].get('pass', rb.get('pass',8.0))
    except Exception: return 8.0

if __name__=='__main__':
    bad=0; thr=threshold()
    for p in sys.argv[1:]:
        fails,warns,info=review(p)
        print(f"=== thumb_review: {os.path.relpath(p)} ===")
        if info:
            for r in info[0]: print('  ',r)
            print('   시트 →',os.path.relpath(info[1]))
        for w in warns: print('  ⚠',w)
        for f in fails: print('  -',f)
        sc=score_of(fails,warns); ok=sc>=thr
        print(f"  점수 {sc:.1f}/10 (임계 {thr}) → {'✅ PASS' if ok else '❌ FAIL'} (자동 항목; 호기심·이미지·감정은 시트 보고 review_log --score)")
        bad+=(not ok)
    sys.exit(1 if bad else 0)
