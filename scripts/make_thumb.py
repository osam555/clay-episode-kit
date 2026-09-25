#!/usr/bin/env python3
"""편별 썸네일 — **Flow 전용 히어로 컷**에서 A/B 생성 + 즉시 평가.
오쌤 2026-09-20 「플로우를 이용해서 별도로 썸네일 생성하고 평가하는 걸로」 — 본편 프레임을 자르지 않고
얼굴 크게·화면 꽉 찬 전용 컷(prompts/<id>.json 의 thumb.a/b.flow)을 따로 생성해 죽은 공간을 없앤다.

  python3 scripts/make_thumb.py <id> [a|b|c]  (부모 탑10: a=V1 기준 · b=V2 실물 doc · c=V3 클로즈업, docs/34)     생성(+검사). 히어로 컷 없으면 aside 브리프를 출력.
  python3 scripts/make_thumb.py <id> --brief   4개(있으면 부족분) 히어로 컷 Flow 브리프만 출력.

thumb 스펙(prompts/<id>.json):
  { "a": {"flow":"<프롬프트>","clip":"thumb/a.mp4","t":2.0,
          "head":[["점심도",104,"WHT"],["한자였어?",150,"BOX"]], "panel":["點心","점심","right"] | "card":["心·力","마음·힘"]},
    "b": {...} }
히어로 컷은 assets/flow/<clips_dir>/thumb/{a,b}.mp4 에 둔다(aside 가 생성). 색: WHT 흰 / YEL 노랑 / BOX 빨간 하이라이트 박스.
"""
import sys, os, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thumb_lib import Thumb, W, H, WHT, YEL
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
def ff(*a): subprocess.run(['ffmpeg','-y','-loglevel','error',*a],check=True)

def frame(src,t,out):
    ff('-ss',str(t),'-i',src,'-frames:v','1','-vf',f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}',out)

def build(vid, which, spec, clips_dir, td):
    # 히어로: 이미지(png/jpg) 우선 — 오쌤 2026-09-20 「영상이 아닌 이미지로 직접 생성」. 없으면 옛 방식(영상 프레임).
    base=f'{R}/assets/flow/{clips_dir}/thumb/{which}'
    img=next((f'{base}{e}' for e in ('.png','.jpg','.jpeg','.webp') if os.path.exists(f'{base}{e}')),None)
    bg=f'{R}/scratch/thumb_{vid}_{which}.png'
    if img:
        ff('-i',img,'-vf',f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}',bg)
    elif os.path.exists(f'{base}.mp4'):
        frame(f'{base}.mp4', spec.get('t',2.0), bg)
    else: return None
    t=Thumb(bg); t.scrim(0.5,150)
    if spec.get('panel'):
        h,r,*rest=spec['panel']; t.panel(h,r,right=(rest and rest[0]=='right'))
    if spec.get('card'):
        h,r=spec['card']; t.card(h,r,44,H-372,cs=330,hs=(236 if len(h)==1 else 150))
    if spec.get('doc'): t.doc(spec['doc'])
    # 헤드라인: 좌하단 2줄(한자판은 우상단 → 대각). 마지막 줄을 하단 기준.
    lines=spec['head']; ys=[H-206, H-46] if len(lines)==2 else [H-46]
    for (txt,size,color),y in zip(lines,ys):
        if color=='BOX': t.hlbox(58,y,txt,size,name=txt)
        else: t.head(58,y,txt,size, YEL if color=='YEL' else WHT, name=txt)
    t.wordmark(); return t.save(f'{td}/final-{which}.png')

def brief(vid, spec_all, clips_dir):
    def has(w): return any(os.path.exists(f'{R}/assets/flow/{clips_dir}/thumb/{w}{e}') for e in ('.png','.jpg','.jpeg','.webp','.mp4'))
    need=[w for w in spec_all if w in ('a','b','c') and not has(w)]
    if not need: print('썸네일 히어로 이미지 A/B 모두 있음'); return
    print(f"# {vid} 썸네일 전용 히어로 **이미지** 생성 브리프 (구글 이미지 생성, 16:9)")
    print(f"저장 위치: ~/dev/allirang/assets/flow/{clips_dir}/thumb/<이름>.png\n")
    for w in need:
        print(f"## {w}.png"); print(spec_all[w]['flow']); print()

def main():
    vid=sys.argv[1]; pj=f'{R}/data/longform/prompts/{vid}.json'
    j=json.load(open(pj)); tb=j.get('thumb')
    if not tb: sys.exit(f'{vid}: prompts/{vid}.json 에 thumb 스펙 없음')
    clips_dir=j.get('clips_dir',vid); tdir=f"{R}/assets/longform/{j.get('thumb_dir',vid)}/thumb"; os.makedirs(tdir,exist_ok=True)
    if '--brief' in sys.argv: return brief(vid, tb, clips_dir)
    which=[a for a in sys.argv[2:] if a in ('a','b','c')] or [w for w in ('a','b','c') if w in tb]
    missing=[]
    for w in which:
        r=build(vid, w, tb[w], clips_dir, tdir)
        if r is None: missing.append(w); print(f'대기: assets/flow/{clips_dir}/thumb/{w}.mp4 없음 — --brief 로 프롬프트 확인')
    if missing: print('\n생성할 히어로 컷:', missing, '→ make_thumb.py', vid, '--brief')

if __name__=='__main__': main()
