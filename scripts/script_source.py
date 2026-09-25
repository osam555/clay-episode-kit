#!/usr/bin/env python3
"""편 대본의 정본 위치를 한 곳에서 푼다 — 대본 게이트·조립·업로드가 같은 대본을 본다.
오쌤 2026-09-23 「대본 리뷰 시스템 점검」: 고아 편(v1 내레이션)이 대본 게이트를 한 번도 안 거치고 배포됐다.
원인은 게이트를 건너뛰어도 컷 승격·조립·업로드가 막지 않은 것. 여기서 「최근 대본 게이트 PASS + 그때 본 대본 = 지금 대본」을 확인한다.

정본 순서는 flow_assemble 과 같다: prompts/<id>.json(lines_full·cards_full) → scratch/flow_<id>/(lines·cards.json) → 편 JSON script_v2.

v1 롱폼(고개 6칸 chapters[].script_ko)은 **편 JSON 에 "script_source": "chapters" 를 적었을 때만** 읽는다 (2026-09-24 오쌤 승인).
짐작으로 떨어지게 두지 않는다 — 같은 id 에 v2 클레이 초안이 따로 있을 수 있어서다(simjeong). 문장은 . ? ! 로 쪼개고 카드는 없다.
게이트를 건너뛰는 옵션이 아니다: 이렇게 읽은 대본도 qa_gate pre 를 PASS 해야 업로드가 풀린다.

  python3 scripts/script_source.py <id>     # 게이트 상태만 본다
"""
import os, sys, json, hashlib, re

ROOT = __import__('os').environ.get('ALLIRANG_ROOT', __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__),'..')))
TAG = re.compile(r'^\s*\[\[[^\]]+\]\]\s*')


SENT = re.compile(r'[^.?!]+[.?!]+["」』”]?|[^.?!]+$')


def chapters_lines(E):
    out = []
    for c in E.get('chapters') or []:
        for m in SENT.finditer(c.get('script_ko') or ''):
            t = m.group().strip()
            if t:
                out.append({'text': t, 'chapter': c.get('n')})
    return out


def load(vid):
    ep = f'{ROOT}/data/longform/{vid}.json'
    E = json.load(open(ep)) if os.path.exists(ep) else {}
    if isinstance(E, dict) and E.get('script_source') == 'chapters':
        return chapters_lines(E), {}, 'chapters'
    pj = f'{ROOT}/data/longform/prompts/{vid}.json'
    P = json.load(open(pj)) if os.path.exists(pj) else {}
    sd = f"{ROOT}/{P.get('scratch_dir') or 'scratch/flow_' + vid}"
    lines, cards, src = P.get('lines_full'), P.get('cards_full'), 'prompts'
    if not lines and os.path.exists(f'{sd}/lines.json'):
        lines, src = json.load(open(f'{sd}/lines.json')), 'scratch'
    if not cards and os.path.exists(f'{sd}/cards.json'):
        cards = json.load(open(f'{sd}/cards.json'))
    if not lines or not cards:
        sv = E.get('script_v2') if isinstance(E, dict) else None
        if sv:
            if not lines:
                lines, src = sv.get('lines'), 'script_v2'
            cards = cards or sv.get('cards')
    cards = _normalize_cards(cards)
    return lines or [], cards or {}, src


def _normalize_cards(cards):
    """generic 편은 script_v2.cards 를 [{"line":9,"title":"..","subtitle":".."}, ...] 배열로 쓴다(한자 아닌 키워드 카드).
    나머지 파이프라인(card_check·hanja_check·flow_assemble)은 {"CARD": {"<g>": [title, subtitle]}} 딕셔너리 모양을 기대하므로 여기서 바꿔 준다.
    한자 편의 cards.json({"CARD": {...}, ...})은 그대로 통과한다."""
    if isinstance(cards, list):
        return {'CARD': {str(c['line']): [c.get('title', ''), c.get('subtitle', '')] for c in cards}}
    return cards


def spoken(line):
    return TAG.sub('', line['text'])


def fingerprint(lines, cards):
    blob = json.dumps({'t': [l['text'] for l in lines], 'c': cards}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:12]


def gate(vid):
    lines, cards, _ = load(vid)
    if not lines:
        return False, '대본 없음'
    fp = fingerprint(lines, cards)
    p = f'{ROOT}/data/longform/reviews/{vid}.json'
    rounds = json.load(open(p)) if os.path.exists(p) else []
    pres = [r for r in rounds if r.get('stage') in ('pre', 'script')]
    if not pres:
        return False, '대본 게이트 기록 없음'
    last = pres[-1]
    if last.get('verdict') != 'PASS':
        return False, f"최근 대본 게이트 {last['verdict']} (차수 {last['round']})"
    if last.get('hash') != fp:
        return False, '대본 게이트 뒤에 대본이 바뀜' if last.get('hash') else '대본 게이트 기록에 대본 지문 없음(옛 기록)'
    return True, f"대본 게이트 PASS (차수 {last['round']}, {last['date']})"


def require(vid):
    ok, why = gate(vid)
    if not ok:
        sys.exit(f"⛔ {vid}: {why} — 먼저 python3 scripts/qa_gate.py pre {vid}")
    print(f"✓ {vid}: {why}")


if __name__ == '__main__':
    ok, why = gate(sys.argv[1])
    print(('✓ ' if ok else '⛔ ') + f"{sys.argv[1]}: {why}")
    sys.exit(0 if ok else 1)
