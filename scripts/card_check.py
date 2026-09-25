#!/usr/bin/env python3
"""카드-자막 일치 검사 — 화면 한자 카드가 그 문장의 낱말과 맞는지 자동 확인.
오쌤 2026-09-20 계기: 복습 절 「초심」 문장에 직전 銘心(명심) 카드가 흘러넘쳐 떴는데 게이트가 통과시켰다.

방법: assemble 과 같은 규칙으로 문장별 '실제로 떠 있는 카드'를 계산(CARD + SPAN carry + MIN_CARD fallback).
각 카드의 한국어 낱말은 그 카드가 정의된 문장 자막에서 배운다(예: 61 「명심은…」 → 銘心=명심).
그다음 모든 문장에서, 자막에 카드 낱말(○심)이 나오는데 떠 있는 카드가 그 낱말과 다르면 FAIL.

사용: python3 scripts/card_check.py <cards.json> <lines.json>
종료코드 0=일치 / 1=불일치

예외(오쌤 2026-09-24 확정, m32·m79): 복습 자막 강조 글자는 원칙이 「끝글자」다(조심·안심·낙심·인내심·진심 등).
勞心焦思(노심초사)만 유일하게 心 이 끝글자가 아니다(2번째 글자) — 4자 통카드는 유지하되 강조만 心 에 준다.
이 예외는 여기서 기계로 막지 않는다(이 스크립트는 카드-자막 낱말 일치만 본다, 강조 위치는 HILITE 저작 몫) — 다음에 心 이 끝이
아닌 낱말을 복습에 또 넣고 싶으면 예외를 늘리지 말고 A(대본)에게 먼저 물을 것. 예외가 둘을 넘으면 「비밀은 낱말 끝에 있어요」
원칙 자체가 흔들린다.
"""
import sys, os, re, json

MIN_CARD_LINES = None  # need 기반이 아니라 문장수 기반 근사(카드 검사는 시간 없이): fallback 1문장

def learn_korean(CARD, S, REVIEW=None):
    """카드 hanja → 한국어 낱말. 카드 정의 문장 자막의 '○심/○심삼일' 토큰에서 학습.
    끝글자가 心 이 아닌 카드(落膽=낙담 등)는 정의 문장에 '○심' 패턴이 없어 여기서 못 배운다 —
    REVIEW(끝 복습, hanja→reading 명시 쌍)를 최우선 진실로 덧대 배운다(2026-09-24 sim_hurt 落膽/낙담 겪음)."""
    k={}
    for g,(h,r) in CARD.items():
        t=S.get(g,'')
        # 우선 '○심' 계열
        mm=re.findall(r'[가-힣]{1,3}심삼일|[가-힣]{1,3}심', t)
        if not mm: continue
        # 한자 글자 수와 음절 수가 같은 후보 우선(無關心 → '무관심', '변심의 끝은 무관심' 에서 첫 낱말 '변심' 을 잡던 오류, 2026-09-22)
        same=[w for w in mm if len(w)==len(h)]
        k[h]=(same or mm)[0]
    if REVIEW:
        for ws in REVIEW.values():
            for h,r in ws: k[h]=r
    return k

def effective_cards(CARD, SPAN, S):
    """문장별로 실제로 보이는 카드 hanja. assemble 의 CARD+CARRY 규칙 재현(시간 대신 문장수 근사)."""
    N=max(S); eff={}
    for g in CARD: eff[g]=CARD[g][0]
    for n in list(CARD):
        end=SPAN.get(n)
        if end:
            m=n+1
            while m<=end and m<=N and m not in CARD: eff[m]=CARD[n][0]; m+=1
        else:
            # SPAN 없으면 다음 1문장까지만(빠른 복습 카드는 인접이라 carry 안 됨). 보수적으로 검사.
            m=n+1
            if m<=N and m not in CARD: eff[m]=CARD[n][0]
    return eff

def main(cards_p, lines_p):
    c=json.load(open(cards_p)); lines=json.load(open(lines_p))
    S={l['g']:l['text'] for l in lines}
    CARD={int(k):tuple(v) for k,v in c['CARD'].items()}
    SPAN={int(k):int(v) for k,v in c.get('SPAN',{}).items()}
    REVIEW={int(k):v for k,v in c.get('REVIEW',{}).items()}
    COMPARE={int(k):[int(x) for x in v] for k,v in c.get('COMPARE',{}).items()}
    ko=learn_korean(CARD,S,REVIEW)       # hanja → 한국어
    words=set(ko.values())               # 카드 낱말 집합(작심/방심/명심/초심…)
    eff=effective_cards(CARD,SPAN,S)
    fails=[]
    # 복습 카드 줄(REVIEW): 낱말이 자막에 있어야 한다
    for g,ws in REVIEW.items():
        for h,r in ws:
            if r not in S.get(g,''): fails.append(f"문장 {g}: REVIEW 카드 '{h}({r})' 가 자막에 없다 — {S.get(g,'')}")
    for g,t in S.items():
        found=[w for w in words if w in t]        # 자막에 나오는 카드 낱말
        if not found: continue
        if g in REVIEW: continue                  # 복습 카드 줄이 그 문장의 카드다(조립기도 CARRY 보다 REVIEW 우선)
        if g in COMPARE:                          # 대비 카드(COMPARE) 줄 — 화면에 두 카드가 함께 뜬다, 둘 중 하나만 맞아도 OK
            pair_ko=[ko.get(CARD[k][0],CARD[k][0]) for k in COMPARE[g]]
            if any(pk in found for pk in pair_ko): continue
            fails.append(f"문장 {g}: COMPARE 카드 {pair_ko} 인데 자막은 '{'/'.join(found)}' — {t}")
            continue
        shown=eff.get(g)
        # 복습 원칙(오쌤 2026-09-20): 카드 낱말이 3개 이상 나열된 문장에 카드가 하나도 없으면 FAIL → cards.json REVIEW 로
        # 단, 아직 카드를 하나도 안 배운 훅 줄(도입부 「낙심, 낙담, 상심」 같은 예고)은 복습이 아니라 예고라 제외
        # (2026-09-24 sim_hurt 겪음 — learn_korean 이 落膽/낙담 을 못 배우던 버그를 고치자 문장5 훅이 새로 걸렸다).
        if shown is None and g not in REVIEW and len(found)>=3 and (not CARD or g>=min(CARD)):
            fails.append(f"문장 {g}: 복습 나열({'/'.join(found)})인데 단어카드 없음 — REVIEW 필요 — {t}")
            continue
        if shown is None: continue                 # 카드 안 뜨면 불일치 없음
        shown_ko=ko.get(shown, shown)
        # 자막 낱말 중 하나라도 떠 있는 카드와 맞으면 OK
        if shown_ko not in found:
            fails.append(f"문장 {g}: 자막은 '{'/'.join(found)}' 인데 카드는 '{shown}({shown_ko})' 가 떠 있다 — {t}")
    print("=== card_check ===")
    if fails:
        print("❌ FAIL — 카드-자막 불일치:"); [print("  -",x) for x in fails]; return 1
    print("✅ PASS — 모든 문장에서 카드와 자막 낱말이 일치"); return 0

if __name__=='__main__':
    if len(sys.argv)<3: sys.exit("사용법: card_check.py <cards.json> <lines.json>")
    sys.exit(main(sys.argv[1],sys.argv[2]))
