#!/usr/bin/env python3
"""새 프로젝트 마법사 — kit.config.json 을 채우고 필요한 폴더를 만든다.

  python3 scripts/new_project.py              대화형
  python3 scripts/new_project.py --defaults    질문 없이 자리표시자 값으로 채움(테스트·스크립트용)
"""
import json, os, subprocess, sys

R = os.environ.get('ALLIRANG_ROOT', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitconfig

DIRS = [
    'data/longform', 'data/longform/prompts', 'scratch',
    'assets/flow', 'assets/brand', 'remotion/out',
]

ROLES = [
    ('CH', '아이(주인공)'), ('MOM', '엄마'), ('DAD', '아빠'), ('FR', '친구'),
    ('GRAND', '할아버지'), ('GRM', '할머니'), ('TEACH', '선생님'),
]


def ask(prompt, default=''):
    v = input(f'{prompt} [{default}]: ').strip()
    return v or default


def main():
    defaults_mode = '--defaults' in sys.argv
    print('=== 새 프로젝트 만들기 ===\n')

    if defaults_mode:
        name = '내 프로젝트'
        site_url = 'https://example.com/word'
        hashtags = ['#해시태그1', '#해시태그2']
        narration = 'ko'
        roles = {k: f'a clay {label}' for k, label in ROLES}
    else:
        name = ask('브랜드 이름(앱/채널 이름)', '내 프로젝트')
        site_url = ask('사이트 URL (영상 설명에 붙는다)', 'https://example.com/word')
        hashtags = ask('해시태그 (공백으로 구분)', '#해시태그1 #해시태그2').split()
        narration = ask('나레이션 언어 (ko/en/...)', 'ko')
        roles = {}
        print('\n캐릭터 역할마다 한 줄 시각 묘사 (영어 프롬프트 문구) — 비워두면 기본값을 쓴다.')
        for k, label in ROLES:
            roles[k] = ask(f'  {k} ({label})', f'a clay {label}')

    # ---- 폴더 ----
    for d in DIRS:
        os.makedirs(f'{R}/{d}', exist_ok=True)
    print(f'\n폴더 준비 완료: {", ".join(DIRS)}')

    # ---- kit.config.json ----
    cfg = kitconfig.load(R)
    cfg['brand']['name'] = name
    cfg['brand']['site_url'] = site_url
    cfg['brand']['hashtags'] = hashtags
    cfg['brand']['description_footer'] = f'📖 {name}'
    cfg['language']['narration'] = narration
    cfg['language']['on_screen'] = narration
    for k, v in roles.items():
        cfg['characters'][k] = v
        # 파생 문구(C2/F2/MP/DP)는 기본 역할 위에 얹는 조합이라 CH/FR/MOM/DAD 를 바꾸면 같이 갱신한다
    cfg['characters']['C2'] = cfg['characters']['CH'] + ', a small boy with light peach skin and a full head of short brown hair,'
    cfg['characters']['F2'] = cfg['characters']['FR']
    cfg['characters']['MP'] = cfg['characters']['MOM'] + ' with light peach skin'
    cfg['characters']['DP'] = cfg['characters']['DAD'] + ' with light peach skin'

    with open(f'{R}/kit.config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f'kit.config.json 저장됨 ({R}/kit.config.json)')

    # ---- 플레이스홀더 브랜드 에셋 ----
    wm_path = f'{R}/{cfg["brand"]["wordmark_png"]}'
    os.makedirs(os.path.dirname(wm_path), exist_ok=True)
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGBA', (600, 160), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 64)
        except Exception:
            font = ImageFont.load_default()
        d.text((20, 40), name, font=font, fill=(24, 34, 62, 255))
        img.save(wm_path)
        print(f'플레이스홀더 워드마크 생성: {wm_path}')
    except ImportError:
        print('⚠ Pillow 가 없어 워드마크 플레이스홀더를 건너뛴다 (pip install Pillow)')
    except Exception as e:
        print(f'⚠ 워드마크 생성 실패(계속 진행): {e}')

    intro_path = f'{R}/{cfg["brand"]["intro_mp4"]}'
    os.makedirs(os.path.dirname(intro_path), exist_ok=True)
    try:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error',
                         '-f', 'lavfi', '-i', 'color=c=0xFFF7E8:s=1920x1080:d=6',
                         '-i', wm_path,
                         '-filter_complex', '[0:v][1:v]overlay=(W-w)/2:(H-h)/2',
                         '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono',
                         '-c:v', 'libx264', '-t', '6', '-pix_fmt', 'yuv420p',
                         '-c:a', 'pcm_s16le', '-shortest', intro_path],
                        check=True, capture_output=True)
        print(f'플레이스홀더 인트로(6초) 생성: {intro_path}')
    except FileNotFoundError:
        print('⚠ ffmpeg 가 없어 인트로 플레이스홀더를 건너뛴다')
    except Exception as e:
        print(f'⚠ 인트로 생성 실패(계속 진행): {e}')

    print('\n=== 다음 단계 ===')
    print('1) kit.config.json 을 열어 channels(유튜브 채널 ID·토큰 경로)·tts.voices 를 채운다.')
    print('2) assets/brand 의 워드마크·로고를 실제 브랜드 이미지로 바꾼다(있으면).')
    print('3) python3 scripts/new_episode.py <key> --word "<주제어>" 로 편을 시작한다.')
    print('4) SKILL.md §A. 새 주제·캐릭터로 시작하기 를 읽고 대본을 쓴다.')


if __name__ == '__main__':
    main()
