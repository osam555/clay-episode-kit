#!/usr/bin/env python3
"""썸네일만 다시 올린다 — 영상은 그대로 두고 thumbnails().set 만. (2026-09-24 A 리뷰로 final-b 문구를 고친 편)

  python3 scripts/youtube_thumb.py <episode> [--which a|b|c]   # 기본 a. 편 JSON 의 yt_v2(있으면)·yt / yt_daechung_v2·yt_daechung 에 올린다
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtube_upload import get_credentials

R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode')
    ap.add_argument('--which', default='a', choices=['a', 'b', 'c'])
    a = ap.parse_args()
    d = json.load(open(f'{R}/data/longform/{a.episode}.json'))
    path = f'{R}/assets/longform/{a.episode}/thumb/final-{a.which}.png'
    if not os.path.exists(path):
        sys.exit(f'없음: {path}')
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    targets = [('allirang', d.get('yt_v2') or d.get('yt')), ('daechung', d.get('yt_daechung_v2') or d.get('yt_daechung'))]
    for channel, vid in targets:
        if not vid:
            continue
        yt = build('youtube', 'v3', credentials=get_credentials(channel))
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(path, mimetype='image/png')).execute()
        print(f'  ✅ {channel} {vid} ← final-{a.which}.png')


if __name__ == '__main__':
    main()
