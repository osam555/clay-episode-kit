#!/usr/bin/env python3
"""편 교체 때 옛 영상을 비공개로 돌린다 — m12 순서 ⑤ (삭제가 아니라 비공개: 되돌릴 수 있고 댓글·반응 데이터가 남는다).

  python3 scripts/youtube_privacy.py <video_id> --channel allirang [--status private|unlisted|public]
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtube_upload import get_credentials, CHANNELS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video_id')
    ap.add_argument('--channel', choices=list(CHANNELS), required=True)
    ap.add_argument('--status', choices=['private', 'unlisted', 'public'], default='private')
    args = ap.parse_args()

    from googleapiclient.discovery import build
    yt = build('youtube', 'v3', credentials=get_credentials(args.channel))
    cur = yt.videos().list(part='status,snippet', id=args.video_id).execute().get('items', [])
    if not cur:
        sys.exit(f'영상 없음: {args.video_id} ({CHANNELS[args.channel]["label"]})')
    st = cur[0]['status']
    st['privacyStatus'] = args.status
    yt.videos().update(part='status', body={'id': args.video_id, 'status': st}).execute()
    print(f'✅ {args.video_id} → {args.status} · 「{cur[0]["snippet"]["title"]}」 ({CHANNELS[args.channel]["label"]})')


if __name__ == '__main__':
    main()
