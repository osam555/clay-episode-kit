#!/usr/bin/env python3
"""알리랑 영상 재사용 라이브러리를 구글 드라이브에 만든다(오쌤 2026-09-24 「재활용 가능하게, 충분한 인덱스, 원본·자막없는·자막 후로 구별」).

  python3 scripts/drive_backup_clips.py            # 전 편
  python3 scripts/drive_backup_clips.py gan day     # 몇 편만(색인은 늘 전체를 다시 쓴다)

My Drive/allirang-library/
  01_flow-originals/<편>/<클립>.mp4   Flow 에서 받은 원본 클립(이름 = 컷 키), thumb/ = 썸네일용 히어로 컷
  02_no-subtitle/<편>_clean.mp4       자막·카드 없는 본편(나레이션 있음) — flow_assemble.py <편> --clean
  03_subtitled/<편>_deploy.mp4        배포본(인트로+본편+엔딩, 자막·카드)
  04_thumbnails/<편>_final-a.png …    유튜브 썸네일
  05_audio/<편>/nNN.wav               문장별 나레이션 원본(무손실)
  INDEX.csv      클립 한 줄씩 — 분류 태그(인물·장소·유형·소재·감정)·장면 프롬프트·쓰인 문장
  EPISODES.csv   편 한 줄씩 — 낱말·제목·한자 카드·유튜브·어떤 판이 있는지
  README.md      쓰는 법
옛 버전(_v1_…)·검수 시트는 옮기지 않는다.
"""
import csv, glob, json, os, re, subprocess, sys

import os
ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
LIB = os.environ.get('DRIVE_LIB', os.path.expanduser('~/My Drive/allirang-library'))   # Windows: G:\My Drive\allirang-library
TAIL = ' Bright colorful low-poly'

CAST = [('mom', r'mint green cardigan|clay mother'), ('two_parents', r'two taller clay parent'),
        ('parent', r'taller clay parent figure'), ('child', r'round clay child'), ('friend', r'classmate|two small round clay children|another clay child'),
        ('toddler', r'toddler'), ('figures', r'clay figures?|little clay figures')]
SETTING = [('kitchen', r'kitchen|stove|dinner table|rice bowl'), ('classroom', r'classroom|school|chalkboard|desk'),
           ('living_room', r'living room|sofa'), ('bedroom', r'bedroom|\bbed\b'), ('garden_yard', r'garden|yard|backyard|porch'),
           ('outdoor', r'park|playground|track|hill|path|crosswalk|street|river|stream|sea|sky'), ('shop', r'shop|store|counter'),
           ('studio', r'studio background')]
MOTIF = [('tiles_recap', r'blank clay tiles?'), ('book', r'\bbooks?\b'), ('heart', r'heart'), ('clock_time', r'clock|calendar|ribbon'),
         ('moon_sky', r'moon|sun|sky'), ('house', r'house|home'), ('tree_plant', r'tree|sprout|flower|leaf|leaves'),
         ('water', r'river|stream|sea|rain|water'), ('fire', r'fire|flame'), ('food', r'rice|cookie|lunch|meal|cake|snack|plate'),
         ('drawing', r'drawing|paint|easel|canvas'), ('pencil_eraser', r'pencil|eraser'), ('ball_sport', r'\bball\b|running|race|jump rope|kite'),
         ('bricks_build', r'brick|stack'), ('eye_ear', r'\beye\b|\bear\b'), ('light_glow', r'glow|sparkle|light')]
EMO = [('happy', r'smil|laugh|happ|cheer|grin|joy'), ('sad_worried', r'sad|worried|guilty|pout|hurt|droop'),
       ('curious_surprised', r'curious|surpris|puzzl|wonder|amaz'), ('proud', r'proud'), ('calm', r'calm|gentle|peaceful')]


def tags(text, table, multi=True):
    t = text.lower()
    hit = [k for k, rx in table if re.search(rx, t)]
    return '|'.join(hit if multi else hit[:1])


def load_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def plans():
    """clips_dir → dict(prompts={clip: scene}, uses={clip: [(ep,g,text)]}, ep=id, scratch=dir)."""
    out, uses = {}, {}
    for p in sorted(glob.glob(f'{ROOT}/data/longform/prompts/*.json')):
        d = load_json(p)
        if not isinstance(d, dict) or not d.get('map'):
            continue
        ep = d.get('id') or os.path.basename(p)[:-5]
        cd = d.get('clips_dir') or ep
        o = out.setdefault(cd, {'prompts': {}, 'ep': ep, 'scratch': d.get('scratch_dir') or f'scratch/flow_{ep}'})
        for k, v in (d.get('new_prompts') or {}).items():
            t = v if isinstance(v, str) else (v or {}).get('prompt', '')
            o['prompts'][k] = t.split(TAIL)[0].strip()
        for w, spec in (d.get('thumb') or {}).items():
            if isinstance(spec, dict) and spec.get('flow'):
                o['prompts'][f'thumb/{w}'] = spec['flow'].split(TAIL)[0].strip()
        lines = {str(l.get('g')): re.sub(r'^\s*\[\[[^\]]+\]\]\s*', '', l.get('text', '')) for l in (d.get('lines_full') or [])}
        for g, clip in d['map'].items():
            key = (clip[2:].split('/')[0], clip[2:].split('/', 1)[1]) if clip.startswith('R:') else (cd, clip)
            uses.setdefault(key, []).append((ep, g, lines.get(g, '')))
    return out, uses


def rsync(src, dst, *ex):
    os.makedirs(dst, exist_ok=True)
    args = ['rsync', '-a', '--exclude', '.DS_Store']
    for e in ex:
        args += ['--exclude', e]
    subprocess.run(args + [src, dst], check=True)


def duration(f):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 1)
    except ValueError:
        return ''


def main():
    only = set(sys.argv[1:])
    P, USES = plans()
    REUSE = (load_json(f'{ROOT}/data/longform/prompts/REUSE.json') or {}).get('clips', {})
    eps = sorted(e for e in os.listdir(f'{ROOT}/assets/flow') if os.path.isdir(f'{ROOT}/assets/flow/{e}'))
    for cd in eps:
        if only and cd not in only and P.get(cd, {}).get('ep') not in only:
            continue
        ep = P.get(cd, {}).get('ep', cd)
        rsync(f'{ROOT}/assets/flow/{cd}/', f'{LIB}/01_flow-originals/{cd}/', '_v[0-9]*', '_anatomy_review.png')
        sd = f"{ROOT}/{P.get(cd, {}).get('scratch', 'scratch/flow_' + ep)}"
        clean = f'{sd}/{ep}_clean.mp4'
        if os.path.exists(clean):
            rsync(clean, f'{LIB}/02_no-subtitle/')
        dep = f'{ROOT}/remotion/out/{ep}_deploy.mp4'
        if os.path.exists(dep):
            rsync(dep, f'{LIB}/03_subtitled/')
        for w in 'ab':
            t = f'{ROOT}/assets/longform/{ep}/thumb/final-{w}.png'
            if os.path.exists(t):
                os.makedirs(f'{LIB}/04_thumbnails', exist_ok=True)
                subprocess.run(['cp', '-p', t, f'{LIB}/04_thumbnails/{ep}_final-{w}.png'], check=True)
        wavs = sorted(glob.glob(f'{sd}/n[0-9]*.wav'))
        if wavs:
            os.makedirs(f'{LIB}/05_audio/{ep}', exist_ok=True)
            subprocess.run(['rsync', '-a'] + wavs + [f'{LIB}/05_audio/{ep}/'], check=True)

    rows = []
    for cd in sorted(os.listdir(f'{LIB}/01_flow-originals')):
        d = f'{LIB}/01_flow-originals/{cd}'
        if not os.path.isdir(d):
            continue
        meta = P.get(cd, {})
        for f in sorted(glob.glob(f'{d}/*.mp4') + glob.glob(f'{d}/thumb/*.mp4') + glob.glob(f'{d}/thumb/*.png')):
            rel = os.path.relpath(f, d)
            name = rel.rsplit('.', 1)[0]
            scene = meta.get('prompts', {}).get(name, '')
            ru = REUSE.get(f'{cd}/{name}', {})
            if not scene and ru.get('desc_en'):
                scene = 'Clean 3D CG ' + ('scene of ' if ru.get('chars') else 'diagram of ') + ru['desc_en']
            kind = 'thumbnail_hero' if name.startswith('thumb/') else ('scene' if ' scene of ' in scene else ('diagram' if ' diagram of ' in scene else ''))
            used = USES.get((cd, name), [])
            rows.append({'episode': meta.get('ep', cd), 'clips_dir': cd, 'file': f'01_flow-originals/{cd}/{rel}', 'clip': name, 'type': kind,
                         'cast': tags(scene, CAST), 'setting': tags(scene, SETTING, False) or ('studio' if scene else ''), 'motifs': tags(scene, MOTIF), 'emotion': tags(scene, EMO),
                         'character_consistency': ru.get('cast') or ('canon' if 'round clay child with a simple round face' in scene or 'mint green cardigan' in scene else ('none' if scene and not tags(scene, CAST) else '')),
                         'seconds': duration(f) if f.endswith('.mp4') else '',
                         'used_count': len(used), 'used_in': ' / '.join(sorted({u[0] for u in used})),
                         'sample_line': used[0][2] if used else '', 'scene_prompt': scene})
    cols = ['episode', 'clips_dir', 'clip', 'type', 'cast', 'character_consistency', 'setting', 'motifs', 'emotion', 'seconds', 'used_count', 'used_in', 'sample_line', 'scene_prompt', 'file']
    with open(f'{LIB}/INDEX.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

    erows = []
    for p in sorted(glob.glob(f'{ROOT}/data/longform/*.json')):
        e = load_json(p)
        if not isinstance(e, dict) or 'chapters' not in e:
            continue
        ep = e.get('id') or os.path.basename(p)[:-5]
        pr = load_json(f'{ROOT}/data/longform/prompts/{ep}.json') or {}
        cd = pr.get('clips_dir') or ep
        cards = (pr.get('cards_full') or {}).get('CARD') or {}
        erows.append({'episode': ep, 'word': e.get('word', ''), 'title_ko': e.get('title_ko', ''), 'title_en': e.get('title_en', ''),
                      'status': e.get('status', ''), 'hanja_cards': ' '.join(v[0] for v in cards.values()),
                      'youtube': f"https://youtu.be/{e['yt']}" if e.get('yt') else '', 'youtube_daechung': f"https://youtu.be/{e['yt_daechung']}" if e.get('yt_daechung') else '',
                      'site': f'https://allirang.com/word/{ep}',
                      'flow_originals': os.path.isdir(f'{LIB}/01_flow-originals/{cd}'),
                      'no_subtitle': os.path.exists(f'{LIB}/02_no-subtitle/{ep}_clean.mp4'),
                      'subtitled': os.path.exists(f'{LIB}/03_subtitled/{ep}_deploy.mp4'),
                      'audio_lines': len(glob.glob(f'{LIB}/05_audio/{ep}/*.wav'))})
    ecols = list(erows[0].keys()) if erows else []
    with open(f'{LIB}/EPISODES.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=ecols); w.writeheader(); w.writerows(erows)

    open(f'{LIB}/README.md', 'w').write(README)
    print(f'라이브러리 → {LIB} · 클립 색인 {len(rows)} · 편 {len(erows)}')


README = """# 알리랑 영상 재사용 라이브러리

| 폴더 | 무엇 | 언제 쓰나 |
|---|---|---|
| 01_flow-originals/<편>/ | Flow 원본 클립(6초, 720p). 파일 이름 = 컷 키. thumb/ 는 썸네일용 히어로 컷 | 새 편·쇼츠에 장면을 다시 쓸 때 |
| 02_no-subtitle/ | 자막·한자 카드 없는 본편(나레이션만) | 다른 언어 자막·다른 편집·쇼츠 재가공 |
| 03_subtitled/ | 유튜브에 올린 배포본(인트로·엔딩·자막·카드) | 그대로 다시 올리기·발췌 |
| 04_thumbnails/ | 썸네일 A/B | 홍보·블로그 |
| 05_audio/<편>/ | 문장별 나레이션 WAV(무손실, nNN = 대본 문장 번호) | 다시 조립·속청 앱 |

## 찾는 법
- **INDEX.csv** 를 구글 시트로 열고 필터: `cast`(mom·child·friend·toddler·two_parents), `setting`(kitchen·classroom·living_room·outdoor…), `type`(scene·diagram·thumbnail_hero), `motifs`(book·heart·moon_sky·tiles_recap…), `emotion`.
- `used_in` = 이 클립이 쓰인 편, `sample_line` = 처음 쓰인 대사 한 줄, `scene_prompt` = Flow 에 넣은 장면 문장(다시 뽑을 때 그대로 쓰면 비슷한 그림이 나온다).
- **EPISODES.csv** = 편마다 낱말·제목·한자 카드·유튜브 링크와 어떤 판(원본·자막없음·자막·음성)이 있는지.

## 규칙
- `character_consistency`: canon = 정본 아이·엄마 얼굴(주인공 자리에 재사용 가능), other = 마음 시리즈 친구 컷(얼굴이 다름 — 주인공 대사엔 쓰지 말 것), none = 사람 없음(어디든).
- 주인공 아이(파란 셔츠)·엄마(민트 가디건·단발)는 CHARACTERS 정본 문구로 뽑은 컷이 `cast` 에 child·mom 으로 잡힌다 — 주인공 대사 자리에 다시 쓸 수 있다.
- 새 편을 만들면 `python3 scripts/drive_backup_clips.py <편>` 한 번이면 이 폴더와 색인이 갱신된다(자막없는 판은 `flow_assemble.py <편> --clean` 먼저).
"""

if __name__ == '__main__':
    main()
