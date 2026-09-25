#!/usr/bin/env python3
"""prep_more.sh 의 크로스플랫폼(Windows 포함) 파이썬 판.

편을 R2 에 올리고(video/short/thumb) ship_short --dry 로 확인한 뒤 yt_meta 큐에 항목을 추가하고,
Drive 재사용 라이브러리 백업을 백그라운드로 돌린다.

  python3 scripts/prep_more.py <ep> [<ep> ...]

전제: `npx wrangler login` 을 한 번 해 둔다. R2 버킷/경로는 이 저장소의 배포 규약(브랜드 도메인 media.<자기도메인>)에
맞게 아래 BUCKET/PREFIX 를 자기 것으로 바꿔 쓴다.
"""
import json
import os
import subprocess
import sys

ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
FLOW_WORK = os.environ.get('FLOW_WORK', os.path.join(ROOT, 'scratch', 'flow_tools'))
os.makedirs(FLOW_WORK, exist_ok=True)

import sys as _s; _s.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kitconfig as _kc; _st = _kc.load().get('storage', {})
BUCKET = os.environ.get('R2_BUCKET', _st.get('r2_bucket', 'speed-listening-popsong'))
PREFIX = os.environ.get('R2_PREFIX', _st.get('r2_prefix', 'allirang'))
MEDIA_BASE = os.environ.get('MEDIA_BASE_URL', _st.get('media_base_url', 'https://media.brainhz.life/allirang'))

sys.path.insert(0, os.path.join(ROOT, 'scripts'))


def r2_put(local, remote):
    cmd = ['npx', 'wrangler', 'r2', 'object', 'put', f'{BUCKET}/{PREFIX}/{remote}',
           '--file', local, '--remote']
    subprocess.run(cmd, capture_output=True, text=True)


def prep_one(ep):
    r2_put(os.path.join(ROOT, 'remotion', 'out', f'{ep}_deploy.mp4'), f'{ep}/video.mp4')
    r2_put(os.path.join(ROOT, 'scratch', f'flow_{ep}', f'{ep}_short.mp4'), f'{ep}/short.mp4')
    r2_put(os.path.join(ROOT, 'assets', 'longform', ep, 'thumb', 'final-a.png'), f'{ep}/thumb_a.png')

    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'ship_short.py'), ep, '--dry'],
                    capture_output=True, text=True)

    import youtube_upload as Y  # noqa: E402  (needs sys.path set above)

    meta_path = os.path.join(FLOW_WORK, 'yt_meta.json')
    queue = []
    if os.path.exists(meta_path):
        queue = json.load(open(meta_path, encoding='utf-8'))
    queue = [x for x in queue if x.get('ep') != ep]

    m = Y.load_episode_meta(ep)
    s = Y.load_part_meta(ep, 'hook_short')
    queue.append({
        'ep': ep, 'kind': 'long', 'title': m['title'], 'desc': m['description'],
        'tags': m.get('tags', []), 'url': f'{MEDIA_BASE}/{ep}/video.mp4',
        'thumb': f'{MEDIA_BASE}/{ep}/thumb_a.png',
    })
    queue.append({
        'ep': ep, 'kind': 'short', 'title': s['title'], 'desc': s['description'],
        'tags': s.get('tags', []), 'url': f'{MEDIA_BASE}/{ep}/short.mp4', 'thumb': None,
    })
    json.dump(queue, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # 드라이브 재사용 라이브러리 갱신 — 백그라운드
    log_path = os.path.join(FLOW_WORK, f'drive_{ep}.log')
    with open(log_path, 'w') as lf:
        subprocess.Popen(
            [sys.executable, os.path.join(ROOT, 'scripts', 'drive_backup_clips.py'), ep],
            stdout=lf, stderr=subprocess.STDOUT,
            start_new_session=(os.name != 'nt'),
        )
    print(f'{ep} prepped')


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: prep_more.py <ep> [<ep> ...]')
    for ep in sys.argv[1:]:
        prep_one(ep)


if __name__ == '__main__':
    main()
