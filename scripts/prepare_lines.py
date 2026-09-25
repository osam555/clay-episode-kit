#!/usr/bin/env python3
"""편 JSON(script_v2)에서 작업 파일을 뽑는다 — python3 scripts/prepare_lines.py <key>
   → scratch/flow_<key>/lines.json (더빙·컷 계획 검사가 읽음) · cards.json (화면 카드). 더빙 전에 한 번 돌린다."""
import json, os, sys
ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.dirname(__file__)); import script_source
key = sys.argv[1]
lines, cards, src = script_source.load(key)
if not lines: sys.exit(f'{key}: 대본이 없다 — data/longform/{key}.json 의 script_v2.lines 를 채워라')
sd = f'{ROOT}/scratch/flow_{key}'; os.makedirs(sd, exist_ok=True)
out = [{'g': l.get('g', i + 1), 'text': l['text']} if isinstance(l, dict) else {'g': i + 1, 'text': l} for i, l in enumerate(lines)]
json.dump(out, open(f'{sd}/lines.json', 'w'), ensure_ascii=False, indent=1)
if not cards: cards = {'CARD': {}}
for k in ('SPAN', 'SIDE', 'HILITE', 'REVIEW', 'FOOT', 'COMPARE'): cards.setdefault(k, {})
json.dump(cards, open(f'{sd}/cards.json', 'w'), ensure_ascii=False, indent=1)
print(f'{key}: {len(out)}문장 · 카드 {len(cards["CARD"])}장 → {sd}/ (대본 출처: {src})')
