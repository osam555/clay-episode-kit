#!/usr/bin/env python3
"""북극성 대본 검사 — 「초등학생 문해력 교재: 이게 한자였어 + 클레이 애니 + 스토리텔링, 기초 300자, 초등+엄마」(docs/12·31).
오쌤 2026-09-23 「북극성을 다시 확인하고 대본이 목표 및 기준에 부합하는지, 대본 리뷰 시스템 점검」.
사랑(한자 0자)·萬(manil 과 중복)·shock1(레버리지 없음)이 게이트를 통과한 뒤에 만든 검사다. RUBRIC 의 판정 항목 중 기계로 잴 수 있는 것을 자동화했다.

  실패(감점 3): 아이·엄마 대화 3줄 미만 · 한 글자가 여는 낱말 3개 미만 · 300자권 밖 글자 6자 이상 · 배포된 편과 낱말 40%↑ 겹침
  경고(감점 1): 첫 3문장에 질문 없음 · 첫 5문장에 문헌·시대 이야기

  python3 scripts/northstar_check.py <id> [...]     # 편별 결과
  python3 scripts/northstar_check.py --all          # 대본이 있는 전 편 보정용 표
"""
import os, sys, json, glob, re
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import script_source as ss
import hanja_check as hc

ROOT = ss.ROOT
MIN_DIALOG = 3
MIN_LEVERAGE = 3
MAX_OUT_TIER = 6
DUP_MIN, DUP_RATIO = 3, 0.4
# docs/12 「어려운 문헌·세기 안 앞세움」 — 훅 자리(첫 5문장)에만 본다. 본문 뒤쪽 각주성 언급은 괜찮다.
# 「세기」는 빼둔다 — 「온도 세기」「수 세기」(세다)와 겹친다(2026-09-23 count·number 오탐).
LIT = ['조선', '고려', '문헌', '훈민정음', '옛 책', '중세', '삼국', '고문']


def words_of(cards):
    ws = [h for h, _ in cards.get('CARD', {}).values()]
    for rv in cards.get('REVIEW', {}).values():
        ws += [h for h, _ in rv]
    return sorted(set(ws))


def base_id(vid):
    """sim_calm 과 calm, sim_student 와 sim_student_ext 는 같은 편."""
    return re.sub(r'_ext$', '', re.sub(r'^sim_', '', vid))


def remake_of(vid):
    p = f'{ROOT}/data/longform/{vid}.json'
    try:
        d = json.load(open(p))
        return ((d.get('ab_test') or {}).get('remake_of')) if isinstance(d, dict) else None
    except Exception:
        return None


def pub_at(vid):
    p = f'{ROOT}/data/longform/{vid}.json'
    try:
        d = json.load(open(p))
        return d.get('published_at') if isinstance(d, dict) else None
    except Exception:
        return None


def published():
    out = []
    for p in sorted(glob.glob(f'{ROOT}/data/longform/*.json')):
        d = json.load(open(p))
        if isinstance(d, dict) and (d.get('yt') or d.get('status') in ('rendered', 'published')):
            out.append(os.path.basename(p)[:-5])
    return out


def check(vid, lines=None, cards=None, pub=None, native_no_hanja=False):
    if lines is None:
        lines, cards, _ = ss.load(vid)
    fails, warns = [], []
    S = [ss.spoken(l) for l in lines]

    n_dialog = sum(1 for l in lines if ss.TAG.match(l['text']))
    if n_dialog < MIN_DIALOG:
        fails.append(f'스토리텔링: 아이·엄마 대화 {n_dialog}줄 < {MIN_DIALOG} — 내레이션만으로는 북극성(스토리텔링)이 아니다')

    if not any('?' in s for s in S[:3]):
        warns.append('훅: 첫 3문장에 질문이 없다')

    lit = sorted({w for s in S[:5] for w in LIT if w in s})
    if lit:
        warns.append(f"초등 눈높이: 첫 5문장이 문헌·시대 이야기로 연다({'·'.join(lit)}) — 각주로 내린다")

    ws = words_of(cards)
    cnt = Counter(g for w in ws for g in set(hc.hz(w)))
    lev_g, lev = (cnt.most_common(1)[0] if cnt else ('', 0))
    # 순우리말 편(카드에 한자 없음, 예: 채널 대표 아리랑) — 레버리지는 한자 글자 반복을 재는 척도라 애초에 0이 나온다.
    # 뿌리(알/얼처럼)는 문자열로 못 재니 WARN 으로만 내린다.
    if native_no_hanja:
        warns.append('레버리지: 순우리말 편이라 한자 글자 반복 척도가 적용되지 않는다 — 뿌리(알/얼 등) 반복은 사람이 본다')
    elif lev < MIN_LEVERAGE:
        fails.append(f"레버리지: 한 글자가 여는 낱말 {lev}개 < {MIN_LEVERAGE}{' (' + lev_g + ')' if lev_g else ''} — 「한 글자→여러 낱말」이 없다")

    h = hc.check_cards(cards) if ws else None
    if h and not native_no_hanja and len(h['by']['밖']) >= MAX_OUT_TIER:
        fails.append(f"기초한자: 300자권 밖 {len(h['by']['밖'])}자({' '.join(h['by']['밖'])}) ≥ {MAX_OUT_TIER} — 조연을 줄인다")

    mine = {w for w in ws if len(hc.hz(w)) >= 2}
    # 먼저 나간 편이 원본이다 (2026-09-24 day↔ryeok): 둘 다 published_at 이 있으면 나보다 늦게 나간 편과는 견주지 않는다.
    # 원본(day 9/21)이 나중에 낱말을 베낀 편(ryeok 9/23) 때문에 FAIL 나던 것. 베낀 쪽은 그대로 FAIL 이 난다.
    my_at = pub_at(vid)
    if mine:
        for other in (pub if pub is not None else published()):
            if base_id(other) == base_id(vid):
                continue
            o_at = pub_at(other)
            if my_at and o_at and o_at > my_at:
                continue
            # A/B 리메이크(2026-09-24 오쌤 「같은 에피소드를 새롭게 만들어 조회수 비교」): 편 JSON ab_test.remake_of 가 가리키는 원본과는 견주지 않는다.
            if remake_of(vid) == other or remake_of(other) == vid:
                continue
            _, oc, _ = ss.load(other)
            theirs = {w for w in words_of(oc) if len(hc.hz(w)) >= 2}
            both = mine & theirs
            if len(both) >= DUP_MIN and len(both) / len(mine) >= DUP_RATIO:
                fails.append(f"중복: 배포된 {other} 와 낱말 {len(both)}/{len(mine)} 겹침({' '.join(sorted(both))})")

    info = dict(dialog=n_dialog, leverage=lev, lev_glyph=lev_g, out=len(h['by']['밖']) if h else 0, words=len(ws))
    return fails, warns, info


if __name__ == '__main__':
    ids = sys.argv[1:]
    if ids == ['--all']:
        ids = sorted({os.path.basename(os.path.dirname(p))[len('flow_'):] for p in glob.glob(f'{ROOT}/scratch/flow_*/lines.json')}
                     | {os.path.basename(p)[:-5] for p in glob.glob(f'{ROOT}/data/longform/prompts/*.json') if not p.endswith('_draft.json')})
    pub = published()
    # 편성표에서 합친 편(status: merged) 은 표에서 뺀다 — 대본은 남아 있어도 만들지 않는 편이다.
    merged = {}
    try:
        sp = json.load(open(f'{ROOT}/data/longform/series_plan.json'))
        items = sp if isinstance(sp, list) else next(v for v in sp.values() if isinstance(v, list))
        merged = {i['key']: (i.get('review') or {}).get('merged_into', '?') for i in items if i.get('status') == 'merged'}
    except Exception:
        pass
    bad = 0
    for vid in ids:
        if vid in merged:
            print(f"⏭ {vid:16s} 합침 → {merged[vid]}")
            continue
        # 편 JSON 이 없는 것은 편이 아니다 — 옛 작업본(calm→sim_calm, simst2, sarang_v1), 썸네일·캐릭터 보조 파일(*_thumb, CHARACTERS, REUSE), 확장본(sim_student_ext). 견주지 않는다.
        if not os.path.exists(f'{ROOT}/data/longform/{vid}.json'):
            print(f"⏭ {vid:16s} 편 JSON 없음 — 작업본·보조 파일")
            continue
        lines, cards, src = ss.load(vid)
        if not lines:
            continue
        # 순우리말 편(카드에 한자 없음 — 예쁘다·어리다·고지식) 은 qa_gate 와 같은 잣대로 레버리지 검사를 뺀다
        native = hc.check_cards(cards)['n'] == 0 if cards else False
        f, w, i = check(vid, lines, cards, pub, native_no_hanja=native)
        bad += bool(f)
        tag = '❌' if f else ('⚠' if w else '✅')
        print(f"{tag} {vid:16s} 대화 {i['dialog']:2d} · 레버리지 {i['leverage']}{i['lev_glyph']:1s} · 밖 {i['out']} · 낱말 {i['words']:2d}  {'; '.join(f + w)}")
    sys.exit(1 if bad else 0)
