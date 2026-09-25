#!/usr/bin/env python3
"""첫 장면 세로 쇼츠 업로드 (docs/34 §4 — 쇼츠 먼저, 롱폼 같은 날).
flow_assemble.py <ep> --short 가 만든 <scratch>/<ep>_short.mp4 를 편 JSON 의 hook_short 칸에 등록하고 youtube_upload --part 로 양쪽 채널에 올린다.

  python3 scripts/ship_short.py <episode> [--dry]
"""
import json, os, subprocess, sys

R = __import__('os').environ.get('ALLIRANG_ROOT', __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__),'..')))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitconfig
_BRAND = kitconfig.load(R)['brand']


def main():
    ep = sys.argv[1]; dry = '--dry' in sys.argv
    pp = f'{R}/data/longform/prompts/{ep}.json'; ej = f'{R}/data/longform/{ep}.json'
    pr = json.load(open(pp)); d = json.load(open(ej))
    scratch = pr.get('scratch_dir') or f'scratch/flow_{ep}'
    mp4 = f'{scratch}/{ep}_short.mp4'
    if not os.path.exists(f'{R}/{mp4}'):
        sys.exit(f'없음: {mp4} — flow_assemble.py {ep} --short 먼저')
    th = pr.get('thumb', {}); hook = ' '.join(h[0] for h in ((th.get('c') or th.get('a') or {}).get('head') or []))
    head = d.get('title_ko', ep).split(' — ')[0]
    long_id = d.get('yt_v2') or d.get('yt')
    sec = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{R}/{mp4}']).decode())
    d['hook_short'] = {**d.get('hook_short', {}),
        'render': {'deploy': mp4, 'sec': round(sec, 1), 'size': '1080x1920', 'note': '첫 장면 45초 세로 쇼츠 — 인트로·엔딩 없음, 첫 프레임 = V3 클로즈업(docs/34 §4)'},
        'title': f'{hook} {head} #Shorts'[:100],
        'description': '\n'.join([
            f'{d.get("word", "")} — 첫 장면만 45초. 뒷이야기는 전체 영상에서.', '',
            (f'▶ 전체 영상: https://youtu.be/{long_id}' if long_id else ''),
            f'📖 {_BRAND["site_url"]}/{ep}',
            _BRAND['description_footer'], ' '.join(_BRAND['hashtags'] + ['#Shorts'])])}
    json.dump(d, open(ej, 'w'), ensure_ascii=False, indent=2)
    print(f'{ep} hook_short ← {mp4} ({sec:.1f}s) · 제목 「{d["hook_short"]["title"]}」')
    if dry: return
    r = subprocess.run([sys.executable, f'{R}/scripts/youtube_upload.py', ep, '--part', 'hook_short', '--both'], capture_output=True, text=True)
    print('\n'.join(l for l in (r.stdout + r.stderr).splitlines() if '완료' in l or 'rror' in l or '⛔' in l))


if __name__ == '__main__':
    main()
