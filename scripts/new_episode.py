#!/usr/bin/env python3
"""새 편 뼈대 — data/longform/<key>.json 과 data/longform/prompts/<key>_draft.json 을 만든다.

  python3 scripts/new_episode.py <key> --word "<주제어>"
"""
import argparse, json, os, sys

R = os.environ.get('ALLIRANG_ROOT', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitconfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('key')
    ap.add_argument('--word', required=True, help='이 편의 주제어')
    ap.add_argument('--title', help='제목(없으면 주제어로 대체)')
    a = ap.parse_args()

    cfg = kitconfig.load(R)
    key, word = a.key, a.word
    title = a.title or word

    ep_path = f'{R}/data/longform/{key}.json'
    if os.path.exists(ep_path):
        sys.exit(f'이미 있음: {ep_path}')

    ep = {
        'id': key,
        'word': word,
        'track': 'sino',
        'status': 'draft',
        'title_ko': title,
        'title_en': '',
        'target_seconds': 150,
        'dictNote': 'TODO: 문증(사전·1차 출처) 채우기',
        'sources': [],
        'needs_verify': [],
        '_note': 'script_v2.lines 는 SKILL.md §A 의 8단 구조를 따른다 (23~28줄, ≤2:30). '
                 'script_v2.cards 는 기본이 generic 키워드 카드([{"line":<g>,"title":"..","subtitle":".."}]) — '
                 '한자 편으로 쓰려면 kit.config.json 의 topic.kind 를 "hanja" 로 바꾸고 title 에 한자, subtitle 에 훈음을 넣는다.',
        'tts': {
            'provider': cfg['tts']['provider'],
            'model': 'ssfm-v30',
            'voices': cfg['tts']['voices'] or {
                'narrator': 'tc_REPLACE_NARRATOR_VOICE_ID',
                'child': 'tc_REPLACE_CHILD_VOICE_ID',
                'adult': 'tc_REPLACE_ADULT_VOICE_ID',
                'friend': 'tc_REPLACE_FRIEND_VOICE_ID',
            },
        },
        'script_v2': {'note': 'SKILL.md §A 템플릿대로 채운다', 'lines': [], 'cards': []},
        'images': [],
        'yt_meta': {'titles': [], 'description': '', 'tags': []},
    }
    os.makedirs(os.path.dirname(ep_path), exist_ok=True)
    json.dump(ep, open(ep_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'만듦: {ep_path}')

    draft_path = f'{R}/data/longform/prompts/{key}_draft.json'
    draft = {
        'id': key,
        'scratch_dir': f'scratch/flow_{key}',
        'clips_dir': key,
        'new_prompts': {},
        'map': {},
        'thumb': {},
        '_note': '컷 설계는 top10_plan.py 의 PLANS 블록을 본떠 채우거나, 이 파일에 직접 new_prompts/map/thumb 을 채운다. '
                 'cutplan_check.py 로 검사 후 --promote 하면 _draft 가 벗겨져 정본이 된다.',
    }
    os.makedirs(os.path.dirname(draft_path), exist_ok=True)
    json.dump(draft, open(draft_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'만듦: {draft_path}')

    print('\n다음: 대본(script_v2.lines) 채우기 → top10_plan.py 에 컷 설계 추가 또는 draft 직접 편집 → '
          f'python3 scripts/cutplan_check.py {key}')


if __name__ == '__main__':
    main()
