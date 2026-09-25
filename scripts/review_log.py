#!/usr/bin/env python3
"""리뷰 차수 기록 — 대본·영상·썸네일 게이트 결과를 편별로 차수(round)와 함께 남긴다.
오쌤 2026-09-20 「리뷰시스템은 차수별 평가결과를 기록으로 유지」.

한 편이 여러 번 고쳐지므로(v1→v2→…), 매 게이트 실행 결과를 append 한다.
  data/longform/reviews/<id>.json  — [{round, date, stage, verdict, findings, note}]
  data/longform/reviews/<id>.md    — 차수별 표

사용:
  python3 scripts/review_log.py <id> <stage> <PASS|FAIL> [--note "..."] [--find "..." ...]
  stage: script | video | thumbnail | card | live | pre | post
qa_gate/visual_check/card_check/live_thumb_check 가 끝나고 이걸 호출해 결과를 남긴다.
"""
import sys, os, json, datetime

ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
OUT=f'{ROOT}/data/longform/reviews'

STAGE_ALIAS={'pre':'script','post':'video','all':'video','card':'script'}
def threshold(stage):
    rb=json.load(open(f'{OUT}/RUBRIC.json')) if os.path.exists(f'{OUT}/RUBRIC.json') else {'pass':8.0,'stages':{}}
    return rb['stages'].get(STAGE_ALIAS.get(stage,stage),{}).get('pass', rb.get('pass',8.0))

def log(vid, stage, verdict, note='', finds=None, score=None, fp=None):
    """점수제(오쌤 2026-09-20 「모든 평가는 점수로, 몇 점 이상 패스」): score 가 있으면 verdict 는 RUBRIC 임계값으로 자동 판정.
    score 없이 부르면 옛 방식(PASS/FAIL 문자열)이지만 점수 없음이 표에 드러난다."""
    os.makedirs(OUT, exist_ok=True)
    thr=threshold(stage)
    if score is not None:
        score=round(float(score),1); verdict='PASS' if score>=thr else 'FAIL'
    p=f'{OUT}/{vid}.json'
    rounds=json.load(open(p)) if os.path.exists(p) else []
    rnd=(rounds[-1]['round']+1) if rounds else 1
    entry={'round':rnd,'date':datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
           'stage':stage,'verdict':verdict,'score':score,'threshold':thr,'note':note,'findings':finds or []}
    if fp: entry['hash']=fp   # 대본 지문 — script_source.gate 가 「게이트 뒤에 대본이 바뀌었나」를 본다
    rounds.append(entry)
    json.dump(rounds, open(p,'w'), ensure_ascii=False, indent=1)
    # markdown
    md=[f"# {vid} — 리뷰 차수 기록 (점수제: 단계별 임계값 이상 PASS, RUBRIC.json)","",
        "| 차수 | 시각 | 단계 | 점수 | 결과 | 내용 |","|---|---|---|---|---|---|"]
    for r in rounds:
        f='; '.join(r['findings']) if r['findings'] else r['note']
        sc=f"{r['score']:.1f}/{r.get('threshold',8.0):.0f}" if r.get('score') is not None else '—'
        md.append(f"| {r['round']} | {r['date']} | {r['stage']} | {sc} | {'✅' if r['verdict']=='PASS' else '❌'} {r['verdict']} | {f} |")
    open(f'{OUT}/{vid}.md','w').write('\n'.join(md)+'\n')
    print(f"리뷰 기록: {vid} 차수 {rnd} · {stage} · {('%.1f점 ' % score) if score is not None else ''}{verdict}(임계 {thr}) → data/longform/reviews/{vid}.md")
    return verdict

if __name__=='__main__':
    a=sys.argv; vid,stage,verdict=a[1],a[2],a[3]
    note=''; finds=[]; score=None; fp=None
    i=4
    while i<len(a):
        if a[i]=='--note': note=a[i+1]; i+=2
        elif a[i]=='--find': finds.append(a[i+1]); i+=2
        elif a[i]=='--score': score=float(a[i+1]); i+=2
        elif a[i]=='--hash': fp=a[i+1]; i+=2
        else: i+=1
    v=log(vid,stage,verdict,note,finds,score,fp)
    sys.exit(0 if v=='PASS' else 1)
