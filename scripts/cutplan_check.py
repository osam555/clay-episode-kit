#!/usr/bin/env python3
"""컷 설계안 검사 — 다른 세션이 만든 초안을 받을 때 통과시킬 기준 (분업 게이트).

  python3 scripts/cutplan_check.py <key> [<key> ...]      # <key>_draft.json 을 본다
  python3 scripts/cutplan_check.py --all                  # prompts/*_draft.json 전부
  python3 scripts/cutplan_check.py <key> --promote        # 통과하면 _draft 를 벗겨 정본으로

검사하는 것 — 사람이 눈으로 못 잡는 것만:
  1) 문장을 다 덮었나          map 이 lines.json 의 모든 g 를 갖고 있나, 없는 문장·헛문장 번호
  2) 크레딧                    신규 컷 수 (편당 10~13, 컷당 10 크레딧(Veo 3.1 Fast))
  3) 재사용이 실제로 있나       R:폴더/이름 이 assets/flow 에 진짜 있나
  4) 그림체가 한 판인가         모든 프롬프트 꼬리에 style tail 이 그대로 붙었나
  5) 캐릭터가 안 튀나           사람이 나오는데 CHARACTERS.json 문구를 안 쓴 컷
  6) 규칙                      어두운 이미지 금지, 장면에 글자 금지
  7) 안 쓰는 컷                 new_prompts 에 있는데 map 이 한 번도 안 부르는 컷
  8) 썸네일 스펙                thumb.a/b 의 프롬프트·헤드라인 줄수·글자수·글자높이·대각 재료

점수는 qa_gate 와 같은 셈이다 — 10 − 3×실패 − 1×주의. RUBRIC 의 script 임계(8.0)를 쓴다.
"""
import json, os, re, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import script_source
import kitconfig

import os
ROOT = os.environ.get('ALLIRANG_ROOT', os.getcwd())
PROMPTS = f'{ROOT}/data/longform/prompts'
FLOW = f'{ROOT}/assets/flow'
BUDGET = (10, 13)          # 편당 신규 컷
CREDIT = 10                # Veo 3.1 Fast 클립당 10 크레딧 (flow-shorts SKILL 4절). 실사 Veo 는 100 이라 헷갈리기 쉽다
THRESHOLD = 8.0

# 장면 자체에 글자가 나오게 설계하면 안 된다 (한자·자막은 오버레이 몫)
TEXT_WORDS = ['sign reading', 'written word', 'letters spelling', 'text saying', 'word written', 'chalkboard with the word']
DARK_WORDS = ['dark ', 'night', 'gloomy', 'shadowy', 'dimly lit', 'moody lighting', 'ominous']
PERSON_WORDS = ['child', 'children', 'parent', 'boy', 'girl', 'mother', 'father', 'person', 'people', 'figure', 'teacher', 'friend']


def load(p):
    return json.load(open(p, encoding='utf-8'))


def style_tail():
    """스타일 꼬리 정본 — kit.config.json 의 style.tail (모든 편이 같은 그림체여야 한다).
    day.json 같은 특정 편 파일이 있으면(옛 알리랑 레이아웃) 그쪽을 우선한다 — 없으면 config 값 그대로."""
    dayp = f'{PROMPTS}/day.json'
    if os.path.exists(dayp):
        d = load(dayp)
        one = next(iter(d['new_prompts'].values()))
        i = one.find('Bright colorful low-poly')
        if i >= 0:
            return one[i:]
    return kitconfig.load(ROOT)['style']['tail']


def characters():
    d = load(f'{PROMPTS}/CHARACTERS.json')
    return {k: v['prompt'] for k, v in d['characters'].items()}


def reusable():
    out = set()
    for folder in sorted(glob.glob(f'{FLOW}/*/')):
        name = os.path.basename(folder.rstrip('/'))
        for mp4 in glob.glob(f'{folder}*.mp4'):
            out.add(f"{name}/{os.path.basename(mp4)[:-4]}")
    return out


def check(key, tail, chars, reuse):
    fails, warns = [], []
    # 정본(<key>.json)이 있으면 그쪽이 먼저다 — promote 한 뒤 정본만 고치면 초안과 어긋난다.
    # 2026-09-22: parent 편 정본을 고쳤는데 검사기가 옛 초안을 읽어 이미 고친 것을 계속 잡았다.
    canon0, draft0 = f'{PROMPTS}/{key}.json', f'{PROMPTS}/{key}_draft.json'
    p = canon0 if os.path.exists(canon0) else draft0
    if not os.path.exists(p):
        return [f'{key}: 컷 계획 없음 ({key}.json · {key}_draft.json 둘 다 없다)'], [], None
    d = load(p)
    prompts = d.get('new_prompts') or {}
    cmap = {str(k): v for k, v in (d.get('map') or {}).items()}

    # 1) 문장을 다 덮었나
    lp = f'{ROOT}/scratch/flow_{key}/lines.json'
    if not os.path.exists(lp):
        fails.append(f'{key}: 대본 {lp} 없음 — 문장 대조를 못 한다')
        gs = set()
    else:
        gs = {str(l['g']) for l in load(lp)}
        missing = sorted(gs - set(cmap), key=int)
        extra = sorted(set(cmap) - gs, key=int)
        if missing:
            fails.append(f'{key}: 컷이 안 붙은 문장 {len(missing)}개 — {missing[:12]}')
        if extra:
            fails.append(f'{key}: 대본에 없는 문장 번호 {extra[:12]}')

    # 2) 크레딧
    n = len(prompts)
    lo, hi = BUDGET
    if n > hi:
        fails.append(f'{key}: 신규 컷 {n}개 — 예산 {hi}개 초과, {CREDIT * (n - hi)} 크레딧 더 든다')
    elif n < lo:
        warns.append(f'{key}: 신규 컷 {n}개 — {lo}개보다 적다. 같은 컷이 너무 자주 나오지 않는지 본다')

    # 3) 재사용이 실제로 있나 + 쓰면 안 되는 컷인가 (REUSE.json 의 avoid — 실사 컷 등)
    avoid = {}
    rp = f'{PROMPTS}/REUSE.json'
    if os.path.exists(rp):
        avoid = {k: v for k, v in load(rp)['clips'].items() if v.get('avoid')}
    for g, clip in cmap.items():
        if clip.startswith('R:'):
            ref = clip[2:]
            if ref not in reuse:
                fails.append(f'{key}: 문장 {g} 이 없는 컷을 가리킨다 — {ref}')
            elif ref in avoid:
                fails.append(f"{key}: 문장 {g} 이 쓰면 안 되는 컷 — {ref} ({avoid[ref]['why']})")
        elif clip not in prompts:
            fails.append(f'{key}: 문장 {g} 의 컷 「{clip}」 이 new_prompts 에 없다')

    # 4) 그림체 5) 캐릭터 6) 규칙
    #   검사는 **장면 묘사**에만 한다. 스타일 꼬리("…for children…")와 캐릭터 정본("two small dark eyes")은
    #   모든 프롬프트에 똑같이 들어가는 붙박이라, 떼지 않고 훑으면 정본 편도 떨어진다 (2026-09-22 자기검사에서 잡힘).
    for name, text in prompts.items():
        if tail and not text.rstrip().endswith(tail.rstrip()):
            fails.append(f'{key}/{name}: 스타일 꼬리가 정본과 다르다 — day.json 것을 그대로 붙인다')
        scene = text[:-len(tail)] if tail and text.rstrip().endswith(tail.rstrip()) else text
        used_char = sorted([c for c in chars.values() if c in scene], key=len, reverse=True)   # 긴 문구부터 — parent 가 mom 문구 안에 들어 있다
        bare = scene
        for c in used_char:
            bare = bare.replace(c, ' ')
        low = bare.lower()
        if any(re.search(rf'\b{w}\b', low) for w in PERSON_WORDS) and not used_char:
            fails.append(f'{key}/{name}: 사람이 나오는데 CHARACTERS 문구를 안 썼다 — 편마다 딴 캐릭터가 된다')
        for w in DARK_WORDS:
            if w in low:
                warns.append(f'{key}/{name}: 어두운 낱말 「{w.strip()}」 — 밝은 톤 규칙')
        for w in TEXT_WORDS:
            if w in low:
                fails.append(f'{key}/{name}: 장면에 글자를 넣었다 「{w}」 — 한자·자막은 오버레이 몫')

    # 8) 썸네일 스펙 — 있어야 Flow 히어로 이미지를 뽑을 수 있다 (2026-09-22: 7편이 통째로 빠져 있었다)
    # 썸네일 스펙은 정본(<key>.json)에 붙는다 — 초안이 정본으로 올라간 뒤에는 그쪽을 본다
    canon = f'{PROMPTS}/{key}.json'
    th = d.get('thumb') or (load(canon).get('thumb') if os.path.exists(canon) else None) or {}
    if not th:
        warns.append(f'{key}: 썸네일 스펙(thumb.a/b) 없음 — 이대로는 히어로 이미지를 못 뽑는다')
    else:
        for w in [x for x in ('a', 'b', 'c') if x in th or x in ('a', 'b')]:
            t = th.get(w)
            if not t:
                warns.append(f'{key}/thumb.{w}: 없음 — A/B 두 장이 있어야 고를 수 있다'); continue
            if not t.get('flow'):
                fails.append(f'{key}/thumb.{w}: flow 프롬프트 없음')
            head = t.get('head') or []
            chars = sum(len(h[0]) for h in head)
            if len(head) > 2:
                fails.append(f'{key}/thumb.{w}: 헤드라인 {len(head)}줄 — 2줄까지 (thumb_review 기준 5)')
            if chars > 14:
                fails.append(f'{key}/thumb.{w}: 헤드라인 {chars}자 — 14자까지 (thumb_review 기준 5)')
            # thumb_review 기준 1 — 펀치라인 ≥100px, 보조줄 ≥80px (320×180 피드에서 25px/20px)
            if head:
                punch, sub = max(h[1] for h in head), min(h[1] for h in head)
                if punch < 100:
                    fails.append(f'{key}/thumb.{w}: 펀치라인 {punch}px — 모바일 피드에서 안 읽힌다 (100px 이상)')
                if sub < 80:
                    fails.append(f'{key}/thumb.{w}: 보조줄 {sub}px — 80px 이상')
            # 대각 균형(thumb_review 기준 6)을 **이미지 뽑기 전에** 잡는다.
            # 헤드라인은 늘 좌하단(make_thumb x=58, y=H-206/H-46)이다. 그러니 한자판은 우측이어야 한다.
            #   panel right=False → (44, 40) 좌상단 · card → (44, H-372) 좌중하단 — 둘 다 헤드라인과 같은 왼쪽이다.
            # 2026-09-22 금일 b 가 card 로 겹쳐 FAIL 났고, J 파일럿도 panel 'left' 로 같은 데 걸릴 뻔했다.
            pan, crd = t.get('panel'), t.get('card')
            if t.get('doc') or t.get('closeup'):
                pass   # V2 실물 doc(우상단) · V3 얼굴 클로즈업이 대각 재료 (docs/34)
            elif not (pan or crd):
                warns.append(f'{key}/thumb.{w}: 한자판도 카드도 없다 — 대각 균형을 못 만든다 (기준 6)')
            elif crd:
                fails.append(f'{key}/thumb.{w}: card 는 좌하단 고정이라 헤드라인과 겹친다 — panel [한자, 음, "right"] 로')
            elif len(pan) < 3 or pan[2] != 'right':
                fails.append(f'{key}/thumb.{w}: 한자판이 왼쪽이다 — 헤드라인(좌하단)과 같은 쪽. panel 세 번째를 "right" 로')

    # 10) 주인공 대사에 얼굴 다른 재사용 컷을 걸었나.
    #     [[child]]·[[adult]] 로 시작하는 줄은 **이 편 주인공이 말하는 자리**다.
    #     REUSE.json 의 cast='other' 는 마음 시리즈에서 온 컷이라 아이 얼굴·옷이 다르다 → 딴 아이가 말하는 것처럼 보인다.
    #     2026-09-22 금일 편이 부모 한마디 구간에서 이걸로 재생성했고, parent 편도 사람이 짚어서 알았다.
    #     사람이 두 번 찾아낸 문제라 검사에 넣는다.
    if os.path.exists(f'{ROOT}/scratch/flow_{key}/lines.json'):
        cast = {}
        rp2 = f'{PROMPTS}/REUSE.json'
        if os.path.exists(rp2):
            cast = {k: v.get('cast') for k, v in load(rp2)['clips'].items()}
        for l in load(f'{ROOT}/scratch/flow_{key}/lines.json'):
            clip = cmap.get(str(l['g']), '')
            if re.match(r'^\s*\[\[(child|adult)', l.get('text', '')) and clip.startswith('R:'):
                if cast.get(clip[2:]) == 'other':
                    fails.append(f"{key}: 문장 {l['g']} 은 주인공 대사인데 얼굴 다른 재사용 컷 — {clip[2:]} (딴 아이가 말하는 것처럼 보인다)")

    # 9) 재사용이 한 컷에 몰리나 — 같은 장면이 되풀이되면 한 편 안에서도, 시리즈로 이어 봐도 지루하다.
    #    2026-09-22 J 10편이 전부 같은 세 컷(C03 나열·C05/C07 반응)만 써서 편끼리 구별이 안 됐다.
    #    REUSE.json 에 사람 없는 컷이 17개인데 5개만 쓰이고 있었다.
    rcnt = {}
    for c in cmap.values():
        if c.startswith('R:'):
            rcnt[c[2:]] = rcnt.get(c[2:], 0) + 1
    total_reuse = sum(rcnt.values())
    if rcnt:
        top, topn = max(rcnt.items(), key=lambda kv: kv[1])
        if topn > 5:
            warns.append(f'{key}: 「{top}」 를 {topn}번 쓴다 — 같은 장면이 너무 자주 나온다 (REUSE.json 에서 다른 컷을 섞는다)')
        if total_reuse >= 6 and len(rcnt) < 3:
            warns.append(f'{key}: 재사용 {total_reuse}번을 {len(rcnt)}종류로만 채웠다 — 장면이 단조롭다')

    # 7) 안 쓰는 컷
    used = {c for c in cmap.values() if not c.startswith('R:')}
    for name in prompts:
        if name not in used:
            warns.append(f'{key}/{name}: 만들어 놓고 한 번도 안 쓴다 — 10 크레딧 낭비')

    stat = {'lines': len(gs), 'new': n, 'reuse': sum(1 for c in cmap.values() if c.startswith('R:'))}
    return fails, warns, stat


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    promote = '--promote' in sys.argv
    if '--all' in sys.argv:
        args = sorted(os.path.basename(p)[:-len('_draft.json')] for p in glob.glob(f'{PROMPTS}/*_draft.json'))
    if not args:
        raise SystemExit('사용: cutplan_check.py <key> [...] | --all [--promote]')

    tail, chars, reuse = style_tail(), characters(), reusable()
    allpass = True
    for key in args:
        fails, warns, stat = check(key, tail, chars, reuse)
        score = max(0.0, 10 - 3 * len(fails) - 1 * len(warns))
        ok = score >= THRESHOLD and not fails
        allpass &= ok
        head = f'{key:12s} {score:4.1f}점 {"통과" if ok else "재작업"}'
        if stat:
            head += f'  (문장 {stat["lines"]} · 신규 {stat["new"]}컷 {stat["new"] * CREDIT}크레딧 · 재사용 {stat["reuse"]})'
        print(head)
        for f in fails:
            print(f'   ✗ {f}')
        for w in warns:
            print(f'   · {w}')
        if ok and promote:
            # 컷은 대본 게이트를 통과한 대본에만 쓴다(Flow 크레딧) — 2026-09-23 고아 편이 대본 검사 없이 컷까지 갔다
            gok, why = script_source.gate(key)
            if not gok:
                print(f'   ⛔ 승격 보류 — {why}. 먼저 python3 scripts/qa_gate.py pre {key}')
                allpass = False
                continue
            src, dst = f'{PROMPTS}/{key}_draft.json', f'{PROMPTS}/{key}.json'
            os.replace(src, dst)
            print(f'   → 정본으로 올림: {dst}')
    print(f'\n임계 {THRESHOLD}점. 통과해야 Flow 로 넘긴다 — 컷 하나가 10 크레딧이다 — 재생성이 쌓이면 커진다.')
    sys.exit(0 if allpass else 1)


if __name__ == '__main__':
    main()
