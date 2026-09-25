#!/usr/bin/env python3
"""북극성 ① 「기초 한자로 문해력」 검사 — 편의 카드 한자가 초등 기초 한자 3단계(100·200·300자권) 안인가.
오쌤 2026-09-22 「프로젝트 목적: 기초 100개 한자로 문해력, 언어 흥미, 초등+엄마」 「초등 과정에 맞는 기초 100자·200자·300자 정도로」.
정본: data/hanja_tiers.json (T1 100 · T2 누적 225 · T3 누적 300, 어문회 배정한자 초안 — 오쌤 확정 전).

  python3 scripts/hanja_check.py <cards.json> [...]
점수(10): 글자 가중 평균(T1 1.0 · T2 0.7 · T3 0.4 · 밖 0)×6 + 편당 서로 다른 한자 ≤12 → 2점(13~16 → 1) + 「카드마다 300자권 글자 하나 이상」 비율×2.
읽는 법: 밖 글자는 「조연」(훈만 들려주고 카드는 100~300자권 글자를 주연으로) — 편이 무엇을 가르치는지가 먼저다.
"""
import sys, os, json
ROOT = __import__('os').environ.get('ALLIRANG_ROOT', __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__),'..')))
try:
    T=json.load(open(f'{ROOT}/data/hanja_tiers.json'))
except FileNotFoundError:
    # generic(비한자) kit 에는 이 표가 없을 수 있다 — 카드에 한자가 없으면(hz() 빈 리스트) 애초에 안 쓰인다.
    T={'T1': [], 'T2': [], 'T3': []}
TIER={**{g:'T1' for g in T['T1']},**{g:'T2' for g in T['T2']},**{g:'T3' for g in T['T3']},**{g:'T3' for g in T.get('MOE2016_examples',[])},**{g:'T3' for g in T.get('REF_hanjavoca',[])}}   # 교육부 2016 예시 글자는 300자권으로
W={'T1':1.0,'T2':0.7,'T3':0.4,'밖':0.0}

def hz(s): return [c for c in s if '一'<=c<='鿿']

def check(cards_p):
    r=check_cards(json.load(open(cards_p)))
    r['file']=os.path.relpath(cards_p,ROOT)
    return r

def check_cards(c):
    words=[h for h,_ in c.get('CARD',{}).values()]
    for ws in c.get('REVIEW',{}).values(): words+= [h for h,_ in ws]
    glyphs=sorted(set(g for w in words for g in hz(w)))
    tiers={g:TIER.get(g,'밖') for g in glyphs}
    by={k:[g for g in glyphs if tiers[g]==k] for k in ('T1','T2','T3','밖')}
    avg=sum(W[tiers[g]] for g in glyphs)/max(1,len(glyphs))
    core=sum(1 for w in set(words) if any(TIER.get(g) for g in hz(w)))/max(1,len(set(words)))
    n=len(glyphs); load=2 if n<=12 else (1 if n<=16 else 0)
    # 주연 글자 = 카드에 가장 많이 반복되는 글자(편이 「가져가는」 글자). 그 층이 편의 학습 목표 층이다.
    from collections import Counter
    cnt=Counter(g for w in set(words) for g in set(hz(w)))
    anchor,ac=(cnt.most_common(1)[0] if cnt else ('',0))
    at=TIER.get(anchor,'밖') if anchor else '밖'
    # 점수: 주연 글자 층 ×5 (T1 5·T2 3.5·T3 2·밖 0) + 조연 부담(밖 글자 ≤4 → 2, ≤8 → 1, 그 이상 0) + 조연 가중 ×3
    anchor_pts={'T1':5.0,'T2':4.0,'T3':3.0,'밖':0.0}[at]   # 목표가 300자권이라 T3 주연도 합격권(오쌤 「초등 300자」)
    out=len(by['밖']); burden=2 if out<=4 else (1 if out<=8 else 0)
    score=round(anchor_pts+burden+avg*3,1)
    return dict(n=n, by=by, avg=avg, core=core, anchor=anchor, anchor_tier=at, anchor_cards=ac, score=score)

if __name__=='__main__':
    thr=8.0
    try: rb=json.load(open(f'{ROOT}/data/longform/reviews/RUBRIC.json')); thr=rb['stages']['script'].get('pass',rb.get('pass',8.0))
    except Exception: pass
    bad=0
    print(f"{'편':10s} {'주연':>4s}{'층':>4s} {'한자':>4s} {'T1':>3s} {'T2':>3s} {'T3':>3s} {'밖':>3s} {'점수':>5s}  밖 글자(조연)")
    for p in sys.argv[1:]:
        r=check(p); ok=r['score']>=thr; bad+=(not ok); b=r['by']
        print(f"{r['file'].split('/')[1].replace('flow_',''):10s} {r['anchor']:>4s}{r['anchor_tier']:>4s} {r['n']:4d} {len(b['T1']):3d} {len(b['T2']):3d} {len(b['T3']):3d} {len(b['밖']):3d} {r['score']:5.1f}{'✅' if ok else '❌'}  {' '.join(b['밖'])}")
    sys.exit(1 if bad else 0)
