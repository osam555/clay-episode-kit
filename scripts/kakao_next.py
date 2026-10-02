#!/usr/bin/env python3
"""카톡 쇼츠 배달 — 다음에 보낼 쇼츠 한 편을 골라 메시지(200자 이내)를 출력한다.

  python3 scripts/kakao_next.py            다음 메시지 출력(보냄 기록 안 함)
  python3 scripts/kakao_next.py --commit   출력하고 '보냄'으로 기록(카톡 전송이 성공한 뒤에 친다)
  python3 scripts/kakao_next.py --status   남은 편수

전송은 PlayMCP 의 카카오톡 「나에게 보내기」 도구(KakaotalkChat-MemoChat)가 한다 — MCP 도구라 Claude 세션이 호출한다.
이 스크립트는 고르기·문구·중복 방지만 맡는다. 매일 보내려면 Claude 예약 작업에 이렇게 적는다:
  「python3 scripts/kakao_next.py 를 실행해 나온 문구를 카카오톡 나에게 보내기 도구로 그대로 보내고,
   성공했을 때만 python3 scripts/kakao_next.py --commit 을 실행해」
편 JSON(data/longform/<key>.json)에서 status=published 이고 hook_short.yt(쇼츠 유튜브 ID)가 있는 편을 순서대로 보낸다.
기록: scratch/kakao_sent.json. 문구 머리말은 kit.config.json 의 brand.name 를 쓴다.
"""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.environ.get('ALLIRANG_ROOT', os.getcwd())
STATE = os.path.join(ROOT, 'scratch', 'kakao_sent.json')


def brand():
    try:
        from kitconfig import load
        return (load().get('brand') or {}).get('name') or '쇼츠'
    except Exception:
        return '쇼츠'


def shorts():
    out = []
    for f in sorted(glob.glob(f'{ROOT}/data/longform/*.json')):
        try: d = json.load(open(f, encoding='utf-8'))
        except Exception: continue
        if not isinstance(d, dict) or d.get('status') != 'published': continue
        hs = d.get('hook_short')
        vid = hs.get('yt') if isinstance(hs, dict) else None
        if vid: out.append({'id': vid, 'title': (d.get('title_ko') or os.path.basename(f)[:-5]).strip()})
    return out


def sent():
    try: return set(json.load(open(STATE)))
    except Exception: return set()


def message(it):
    head = f'🎬 {brand()} 쇼츠\n'
    url = f"https://youtube.com/shorts/{it['id']}"
    room = 200 - len(head) - len(url) - 1
    t = it['title'] if len(it['title']) <= room else it['title'][:room - 1] + '…'
    return f'{head}{t}\n{url}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    s = sent(); left = [x for x in shorts() if x['id'] not in s]
    if a.status:
        print(f'남음 {len(left)} · 보낸 {len(s)}'); return
    if not left: sys.exit('보낼 쇼츠가 없습니다')
    print(message(left[0]))
    if a.commit:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(sorted(s | {left[0]['id']}), open(STATE, 'w'))


main()
