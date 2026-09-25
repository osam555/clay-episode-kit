#!/usr/bin/env python3
"""A/B 대본 비교(오쌤 2026-09-24): 새 대본 버전 영상 설명 첫 줄에 「2026-09 새 대본 버전」과 옛 영상 링크를 단다.
편 JSON 은 yt(옛것 유지) · yt_v2(새것) · yt_daechung · yt_daechung_v2 로 적는다.

  python3 scripts/youtube_ab_mark.py <episode>      # yt_v2 / yt_daechung_v2 영상의 설명을 고친다(이미 있으면 건너뜀)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtube_upload import get_credentials

MARK = '2026-09 새 대본 버전'


def mark(channel, new_id, old_id):
    from googleapiclient.discovery import build
    yt = build('youtube', 'v3', credentials=get_credentials(channel))
    it = yt.videos().list(part='snippet', id=new_id).execute()['items'][0]
    sn = it['snippet']
    if sn.get('description', '').startswith(MARK):
        print(f'  {new_id}: 이미 표시됨'); return
    sn['description'] = f'{MARK} · 이전 버전: https://youtu.be/{old_id}\n\n' + sn.get('description', '')
    body = {'id': new_id, 'snippet': {k: sn[k] for k in ('title', 'description', 'categoryId', 'tags', 'defaultLanguage') if k in sn}}
    yt.videos().update(part='snippet', body=body).execute()
    print(f'  ✅ {new_id} ({channel}) ← 이전 {old_id}')


def main():
    ep = sys.argv[1]
    ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
    d = json.load(open(f'{ROOT}/data/longform/{ep}.json'))
    if d.get('yt_v2') and d.get('yt'):
        mark('allirang', d['yt_v2'], d['yt'])
    if d.get('yt_daechung_v2') and d.get('yt_daechung'):
        mark('daechung', d['yt_daechung_v2'], d['yt_daechung'])


if __name__ == '__main__':
    main()
