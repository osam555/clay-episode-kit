#!/usr/bin/env python3
"""알리랑 flow 편 통합 자동 점검 게이트 — 대본·컷·자막키워드·카드·이미지를 한 번에 검사.
오쌤 2026-09-20 「대본·이미지·자막 키워드 인포그래픽 등 자동 점검 시스템이 실제로 작동하게」.

두 단계:
  pre  (생성 전): 대본 오독·금지어·길이 + 컷 프롬프트(style.check) + 카드/핵심어 존재
  post (조립 후): 클립 해부(anatomy) + 밀도 + 빈중앙 + **배포본 시각검사(인트로 누락·PCM·해상도)** + **썸네일 검사(잘림·글자크기·겹침)**

사용:
  python3 scripts/qa_gate.py pre  <flowmaker_project_dir> [assemble.py]
  python3 scripts/qa_gate.py post <clips_dir> <cuts.json> <deploy.mp4> [thumb1.png thumb2.png ...]
종료코드 0=PASS, 1=FAIL. 실패 항목을 모두 나열한다(하나라도 있으면 배포 금지).
"""
import sys, os, re, json, subprocess, ast
ROOT = __import__('os').environ.get('ALLIRANG_ROOT', __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__),'..')))
WARNS=[]   # 감점 1 항목(밀도 LOW·워드마크 배지·대각 아님 등). fails 는 감점 3. 점수 = 10 - 3·fails - 1·warns, 임계값은 reviews/RUBRIC.json
def score_of(fails): return max(0.0, 10.0-3*len(fails)-1*len(WARNS))
def threshold(stage):
    try:
        rb=json.load(open(f'{ROOT}/data/longform/reviews/RUBRIC.json'))
        return rb['stages'].get({'pre':'script','post':'video','all':'video'}.get(stage,stage),{}).get('pass',rb.get('pass',8.0))
    except Exception: return 8.0

# ── 대본 오독(띄어읽기) 위험: 훈+음 뒤에 조사가 붙어 일상어가 되는 경우 ──
# 예: '작은'(作은→small), '밝은'(밝을?), 실제 사고: 지을 작은 사람이 → 작은 사람이
# 실증된 한자-오독만(과탐 방지): '작은'=作+은→small. 새 사례 나오면 여기 추가.
TRAP = [('작은','作+은 → 「작은」(small)로 오독')]
BAN = ['공부','학습','훈련']  # 앱/영상 금지어(.claude/rules.md)
# 효능·성적 약속 표현(.claude/rules.md 「성적·등급·의료 효능을 약속하지 않는다」). 2026-09-20 엔딩 「몸과 마음에 좋은」이 그대로 나감 → 게이트에 추가.
CLAIM = ['몸에 좋','마음에 좋','몸과 마음에 좋','건강에','치료','효능','효과가','성적이 오','똑똑해','머리가 좋아','IQ','기억력이 좋아','집중력이 좋아져','좋아집니다','좋아져요']

# 오쌤이 폐기한 문장(다시 쓰지 않는다). 2026-09-20 「뒷글자를 보세요 삭제하고 대체」 — 안내문 투·AI 티.
# 오쌤이 삭제를 지시한 문장·표현. 대본에도 사이트 문구에도 쓰지 않는다.
#   '눌러 담' — 2026-09-22 「눌러 담다는 말은 사용하지 말 것」. 압축은 「압축하지 않은」으로 쓴다.
RETIRED = ['뒷글자를 보세요','오늘 규칙은 딱 하나','몸과 마음에 좋은','눌러 담']

def text_check(label, ln):
    """한 문장의 금지어·효능 표현·폐기 문장 → 실패 메시지 목록."""
    out=[]
    for r in RETIRED:
        if r in ln: out.append(f"{label} 폐기 문장 '{r}'(오쌤 삭제 지시): 「{ln}」")
    for b in BAN:
        if b in ln: out.append(f"{label} 금지어 '{b}': 「{ln}」")
    for c in CLAIM:
        if c in ln: out.append(f"{label} 효능·성적 약속 '{c}': 「{ln}」")
    return out

def fixed_check():
    """고정 에셋 문구(assets/fixed_lines.json: 인트로·엔딩) — 대본 밖이라 놓치기 쉬워 pre/post 모두 검사."""
    p=f'{ROOT}/assets/fixed_lines.json'
    if not os.path.exists(p): return ['고정 문구 정본 assets/fixed_lines.json 없음']
    out=[]
    for k,v in json.load(open(p)).items():
        if k.startswith('_'): continue
        out+=text_check(f"고정문구 {k}", v['text'])
        if not os.path.exists(f"{ROOT}/{v['asset']}"): out.append(f"고정 에셋 없음: {v['asset']}")
    return out

def pre(proj, assemble=None, S=None, cuts=None):
    fails=fixed_check()
    scr=os.path.join(proj,'script.txt'); cj=os.path.join(proj,'cuts.json')
    if S is None: S=[l for l in open(scr,encoding='utf-8').read().split('\n') if l.strip()] if os.path.exists(scr) else []
    if cuts is None: cuts=json.load(open(cj)) if os.path.exists(cj) else []
    # 빈 입력 = 통과 금지(2026-09-20 원인: 하루 편 flowmaker 폴더가 비어 0문장 검사로 PASS 기록)
    if not S: fails.append(f'대본 0문장 — 검사 대상 없음({proj}) → prompts/<id>.json lines_full 또는 script.txt 필요')
    if not cuts:
        if os.path.exists(cj): fails.append('컷 프롬프트 0개 — style.check 대상 없음')
        else: WARNS.append('cuts.json 없음 — 대본 단계라면 정상, 컷 계획 후 다시')
    # 1) 대본 오독·금지어·길이
    for i,ln in enumerate(S,1):
        for w,why in TRAP:
            # 낱말 첫머리일 때만(「시작은」「제작은」 같은 안쪽 일치는 오독이 아님, 2026-09-22 과탐 수정)
            if re.search(rf'(^|\s){w}', ln) and not re.search(rf'[,\.] ?{w}|{w}[,\.]', ln):
                fails.append(f"대본 C{i:02d} 오독위험 '{w}' — {why}: 「{ln}」")
        fails+=text_check(f"대본 C{i:02d}", ln)
        if len(ln) > 45: fails.append(f"대본 C{i:02d} 너무 김({len(ln)}자>45): 「{ln}」")
    # 2) 컷 프롬프트 규칙 (flowmaker style.check)
    try:
        sys.path.insert(0,os.path.expanduser('~/dev/flowmaker_public'))
        from flowmaker.style import check as scheck
        chk=[c for c in cuts if c.get('prompt') and c['prompt']!='[REUSE]']
        for v in scheck(chk): fails.append(f"컷 프롬프트: {v}")
    except Exception as e:
        fails.append(f"style.check 실행 실패: {e}")
    # 3) 카드/핵심어 존재 (assemble.py 의 CARD/HILITE 파싱)
    if assemble and os.path.exists(assemble):
        src=open(assemble,encoding='utf-8').read()
        def grab(name):
            m=re.search(rf'^{name}=(\{{.*?\}})\n', src, re.S|re.M)
            try: return ast.literal_eval(m.group(1)) if m else {}
            except Exception: return {}   # 리터럴 아니면(컴프리헨션 등) card_check 에 위임
        HIL=grab('HILITE'); CARD=grab('CARD')
        for n,kw in HIL.items():
            if 1<=int(n)<=len(S) and kw not in S[int(n)-1]:
                fails.append(f"자막 핵심어 C{int(n):02d} '{kw}' 가 대본에 없음: 「{S[int(n)-1]}」")
        for n,(h,r) in CARD.items():
            if not h.strip(): fails.append(f"카드 C{int(n):02d} 한자 비어있음")
    # 5) 카드-자막 일치 (오쌤 2026-09-20: 단어카드는 핵심, 불일치를 게이트가 통과시킨 오류)
    cdir=os.path.dirname(assemble) if assemble else None
    if cdir and os.path.exists(os.path.join(cdir,'cards.json')) and os.path.exists(os.path.join(cdir,'lines.json')):
        r=subprocess.run(['python3',f'{ROOT}/scripts/card_check.py',os.path.join(cdir,'cards.json'),os.path.join(cdir,'lines.json')],capture_output=True,text=True)
        if r.returncode!=0:
            for ln in r.stdout.splitlines():
                if ln.strip().startswith('-'): fails.append('카드-자막'+ln.strip()[1:])
        # 6) 북극성 ①: 카드 한자가 초등 기초 한자(100·200·300자권) 안인가 — 주연 글자 층 + 조연 부담 (2026-09-22)
        sys.path.insert(0,f'{ROOT}/scripts'); import hanja_check as hc
        h=hc.check(os.path.join(cdir,'cards.json'))
        print(f"  기초한자: 주연 {h['anchor']}({h['anchor_tier']}) · 밖 {len(h['by']['밖'])}자 {' '.join(h['by']['밖'])} · 점수 {h['score']}")
        if h['anchor_tier']=='밖': fails.append(f"기초한자: 주연 글자 {h['anchor']} 가 300자권 밖 — 편이 무엇을 가르치는지 다시")
        elif h['score']<6.0: fails.append(f"기초한자 점수 {h['score']} < 6 (주연 {h['anchor']} {h['anchor_tier']}, 밖 {len(h['by']['밖'])}자)")
        elif h['score']<8.0: WARNS.append(f"기초한자 점수 {h['score']} (밖 {len(h['by']['밖'])}자 — 조연 줄이기)")
    print("=== QA pre ===")
    return fails

def pre_id(vid):
    """qa_gate pre <id> — 편 대본 정본(script_source)을 그대로 검사한다. 컷 설계 전에 돈다.
    2026-09-23: 고아 편이 이 단계를 건너뛰고 배포됐다 → 컷 승격·조립·업로드가 이 기록(대본 지문 포함)을 요구한다."""
    import tempfile
    sys.path.insert(0,f'{ROOT}/scripts')
    import script_source as ss, hanja_check as hc, northstar_check as ns
    fails=fixed_check()
    lines,cards,src=ss.load(vid)
    print(f"pre {vid}: 대본 {len(lines)}문장 · 카드 {len(cards.get('CARD',{}))}장 · 출처 {src}")
    if not lines:
        return fails+[f'대본 0문장 — {vid} 의 lines 가 없다'], None
    for i,l in enumerate(lines,1):
        ln=ss.spoken(l)
        for w,why in TRAP:
            if re.search(rf'(^|\s){w}', ln) and not re.search(rf'[,\.] ?{w}|{w}[,\.]', ln):
                fails.append(f"대본 C{i:02d} 오독위험 '{w}' — {why}: 「{ln}」")
        fails+=text_check(f"대본 C{i:02d}", ln)
        # [[teacher]] 태그 줄은 교사 육성 사전 녹음(Fish) 한 덩어리라 문장을 못 쪼갠다 — 자막은 화면에서 2줄로 자동 줄바꿈(sub_png)된다.
        is_teacher_tag = str(l.get('text','')).strip().startswith('[[teacher]]')
        if len(ln)>45 and not is_teacher_tag: fails.append(f"대본 C{i:02d} 너무 김({len(ln)}자>45): 「{ln}」")
    if cards.get('CARD'):
        d=tempfile.mkdtemp()
        json.dump(cards,open(f'{d}/cards.json','w'),ensure_ascii=False)
        json.dump([dict(l,text=ss.spoken(l)) for l in lines],open(f'{d}/lines.json','w'),ensure_ascii=False)
        r=subprocess.run(['python3',f'{ROOT}/scripts/card_check.py',f'{d}/cards.json',f'{d}/lines.json'],capture_output=True,text=True)
        for ln in r.stdout.splitlines():
            if ln.strip().startswith('-'): fails.append('카드-자막'+ln.strip()[1:])
    h=hc.check_cards(cards)
    # 순우리말 편(카드에 한자가 아예 없음, 예: 채널 대표 아리랑) — 이 채널의 북극성 ①은 「한자였어?」 발견이라 애초에 안 맞는 검사.
    native_no_hanja = h['n']==0
    print(f"  기초한자: 주연 {h['anchor'] or '-'}({h['anchor_tier']}) · 밖 {len(h['by']['밖'])}자 {' '.join(h['by']['밖'])} · 점수 {h['score']}" + (" — 순우리말 편, 검사 해당 없음" if native_no_hanja else ""))
    # 오해(shock) 시리즈 예외 — 오쌤 2026-09-24 「오해 시리즈 예외 허용」(비상 非·常).
    # 이 시리즈는 「익숙한 낱말의 오해」가 주제라 주연이 300자권 밖일 수 있다. 대신 밖 글자 수(북극성 ≥6 FAIL)는 그대로 막는다.
    shock=json.load(open(f'{ROOT}/data/longform/{vid}.json')).get('track')=='shock' if os.path.exists(f'{ROOT}/data/longform/{vid}.json') else False
    # 오해(shock) 시리즈는 「낯익은 낱말의 뜻밖 주연 글자」가 주제라 300자권 밖일 때가 많다(비상 非·常, 무궁화 無 모두 겪음).
    # 오쌤 2026-09-24 결정을 시리즈 전체로 확장 — anchor='밖' 뿐 아니라 점수<6 도 이 트랙에서는 WARN 으로 내린다.
    if native_no_hanja:
        WARNS.append("기초한자: 순우리말 편(카드에 한자 없음) — 이 검사 대상이 아니다")
    elif shock and (h['anchor_tier']=='밖' or h['score']<6.0):
        WARNS.append(f"기초한자: 주연 {h['anchor']}({h['anchor_tier']}) 점수 {h['score']} — 오해 시리즈 예외(2026-09-24)")
    elif h['anchor_tier']=='밖': fails.append(f"기초한자: 주연 글자 {h['anchor'] or '없음'} 가 300자권 밖 — 편이 무엇을 가르치는지 다시")
    elif h['score']<6.0: fails.append(f"기초한자 점수 {h['score']} < 6 (주연 {h['anchor']} {h['anchor_tier']}, 밖 {len(h['by']['밖'])}자)")
    elif h['score']<8.0:
        why='조연 줄이기' if h['by']['밖'] else f"주연 {h['anchor']}이 {h['anchor_tier']}층"
        WARNS.append(f"기초한자 점수 {h['score']} (밖 {len(h['by']['밖'])}자 — {why})")
    f,w,info=ns.check(vid,lines,cards,native_no_hanja=native_no_hanja)
    print(f"  북극성: 대화 {info['dialog']}줄 · 레버리지 {info['leverage']}{info['lev_glyph']} · 밖 {info['out']}자")
    fails+=f; WARNS.extend(w)
    # 편별 명시 예외 (오쌤 2026-09-24 「어리다 예외」) — 편 JSON gate_exception.waive 에 적은 규칙만 뺀다.
    # v1 롱폼(어른 내레이션 8~12분)은 45자·아이엄마 대화·훅 질문이 flow 클레이 형식 기준이라 안 맞는다.
    # 조용히 통과시키지 않는다: 뺀 건수와 사유를 찍고, 예외는 편마다 오쌤 결정으로만 단다.
    ex=(json.load(open(f'{ROOT}/data/longform/{vid}.json')).get('gate_exception') or {}) if os.path.exists(f'{ROOT}/data/longform/{vid}.json') else {}
    RULE={'long_line':lambda x:re.match(r'대본 C\d+ 너무 김',x),'dialog':lambda x:x.startswith('스토리텔링:'),'hook_question':lambda x:x.startswith('훅:')}
    waive=[r for r in ex.get('waive',[]) if r in RULE]
    if waive:
        hit=lambda x:any(RULE[r](x) for r in waive)
        nf=sum(1 for x in fails if hit(x)); nw=sum(1 for x in WARNS if hit(x))
        fails[:]=[x for x in fails if not hit(x)]; WARNS[:]=[x for x in WARNS if not hit(x)]
        print(f"  예외({ex.get('by','?')}): {','.join(waive)} — FAIL {nf}건·경고 {nw}건 제외. 사유: {ex.get('why','')}")
    print("=== QA pre ===")
    return fails, ss.fingerprint(lines,cards)

def subtitle_tag_check(vid):
    """**실제로 그린 자막**에 화자 태그가 남았나 (flow_assemble 이 남긴 subs.json).
    [[child]]·[[adult:sad]] 는 더빙이 목소리를 고르는 표시다. 자막에 그리면 안 된다.
    2026-09-22 금일 편이 「[[child]] 엄마, …」로 배포됐는데 이 게이트는 10.0 을 줬다 — 보는 항목이 없었다."""
    out = []
    # scratch_dir 는 편마다 flow_<id> 가 아닐 수 있다(예: sim_hurt → scratch/flow_hurt) — prompts/<id>.json 을 먼저 본다
    # (2026-09-24 sim_hurt 겪음 — subs.json 이 분명히 있는데 이 게이트만 못 찾아 FAIL).
    pp = f'{ROOT}/data/longform/prompts/{vid}.json'
    sd = (os.path.exists(pp) and json.load(open(pp)).get('scratch_dir')) or f'scratch/flow_{vid}'
    sp = f'{ROOT}/{sd}/subs.json'
    if not os.path.exists(sp):
        return ['자막 기록 subs.json 없음 — flow_assemble 로 다시 조립해야 태그 유출을 검사할 수 있다']
    for r in json.load(open(sp)):
        if re.search(r'\[\[', r.get('sub', '')):
            out.append(f"자막에 화자 태그가 찍혔다 g{r['g']}: 「{r['sub'][:34]}」")
    return out


def post(clips, cj, mp4, thumbs=None, extra=None, vid=None):
    fails=fixed_check()   # 인트로·엔딩 고정 문구도 매 배포본마다
    if vid: fails+=subtitle_tag_check(vid)
    print("=== QA post ===")
    # anatomy
    r=subprocess.run(['python3',f'{ROOT}/scripts/anatomy_review.py',clips,cj]+(['--extra']+extra if extra else []),capture_output=True,text=True)
    if '검수할 클립 0개' in r.stdout: fails.append('anatomy: 검수할 클립 0개 (clips_dir 확인)')
    print(r.stdout[-800:])
    if '실사 WARN' in r.stdout:
        m=re.search(r'실사 WARN (\d+)컷', r.stdout)
        if m and int(m.group(1))>0: fails.append(f"해부: 실사 사람 클로즈업 {m.group(1)}컷 — kid 교체 필요")
    # motion density (3 표본)
    # 첫 표본은 인트로(고정 6초, 조용한 구간)를 건너뛴 본편 시작에서 잰다.
    # 인트로 움직임은 편마다 같아 재도 뜻이 없다 — 인트로 자체는 fixed_check·visual_check 가 따로 본다.
    # (2026-09-22 parent 편이 0s 표본이 인트로에 걸려 FAIL → 본편은 정상인데 막혔다)
    import glob
    dur=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',mp4]).decode())
    intro=0
    if os.path.exists(f'{ROOT}/assets/intro_msg.mp4'):
        intro=int(float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f'{ROOT}/assets/intro_msg.mp4']).decode()))+1
    for t in (intro, int(dur*0.4), int(dur*0.75)):
        o=subprocess.run(['python3',f'{ROOT}/scripts/motion_density.py',mp4,str(t),'15'],capture_output=True,text=True).stdout
        m=re.search(r'평균 ([\d.]+).*?정지프레임\(블롭0\) (\d+)%', o)
        if m:
            b=float(m.group(1)); still=int(m.group(2))
            tag='ok' if (b>=3.0 and still<=15) else 'LOW'
            print(f"  밀도 {t}s: 블롭 {b} 정지 {still}% {tag}")
            if b<2.5 or still>25: fails.append(f"밀도 {t}s 미달(블롭{b}, 정지{still}%)")
            elif tag=='LOW': WARNS.append(f"밀도 {t}s 낮음(블롭{b}, 정지{still}%)")
    # empty center
    o=subprocess.run(['python3',f'{ROOT}/scripts/review_video.py',mp4],capture_output=True,text=True).stdout
    if 'FAIL' in o or '⛔' in o: fails.append("빈 중앙 게이트 FAIL")
    else: print("  빈중앙 PASS")
    # 시각 검사(썸네일·배포본) — 사람이 잡던 잘림/인트로누락을 자동으로
    r=subprocess.run(['python3',f'{ROOT}/scripts/visual_check.py','deploy',mp4],capture_output=True,text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout else '')
    if r.returncode!=0:
        for ln in r.stdout.splitlines():
            if ln.strip().startswith('-'): fails.append('배포본'+ln.strip()[1:])
    # 썸네일 검사(있으면)
    for th in (thumbs or []):
        rt=subprocess.run(['python3',f'{ROOT}/scripts/visual_check.py','thumb',th],capture_output=True,text=True)
        rv=subprocess.run(['python3',f'{ROOT}/scripts/thumb_review.py',th],capture_output=True,text=True)   # 벤치마크 수치(가독·대비·배지·면적·글자수·대각)
        warns=[ln.strip() for ln in rv.stdout.splitlines() if ln.strip().startswith('⚠')]
        print(f"  썸네일 {os.path.basename(th)}: {'PASS' if rt.returncode==0 and rv.returncode==0 else 'FAIL'}" + (f"  {' / '.join(warns)}" if warns else ''))
        for r_ in (rt,rv):
            if r_.returncode!=0:
                for ln in r_.stdout.splitlines():
                    if ln.strip().startswith('-'): fails.append(f"썸네일 {os.path.basename(th)}{ln.strip()[1:]}")
        for w in warns:
            if '배지에 가림' in w and 'wordmark' not in w: fails.append(f"썸네일 {os.path.basename(th)} {w}")   # 글자·한자판이 배지에 가리면 FAIL, 워드마크는 WARN
            else: WARNS.append(f"썸네일 {os.path.basename(th)} {w}")
    if not thumbs: fails.append('썸네일 0장 — 검사 대상 없음(assets/longform/<id>/thumb/final-*.png)')
    return fails

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='all':
        # qa_gate all <id> <proj_dir> <assemble.py> <clips_dir> <cuts.json> <deploy.mp4> [thumbs...]
        f=pre(sys.argv[3], sys.argv[4]) + post(sys.argv[5], sys.argv[6], sys.argv[7], [a for a in sys.argv[8:] if a.endswith('.png')])
        if '--id' not in sys.argv: sys.argv+=['--id',sys.argv[2]]
    elif mode=='pre' and '/' not in sys.argv[2]:
        # 축약형: qa_gate pre <id> — 대본 정본을 script_source 로 푼다
        f,fp=pre_id(sys.argv[2])
        if '--id' not in sys.argv: sys.argv+=['--id',sys.argv[2]]
        if fp: sys.argv+=['--hash',fp]
    elif mode=='pre':
        f=pre(sys.argv[2], sys.argv[3] if len(sys.argv)>3 else None)
    elif len(sys.argv)>=3 and '/' not in sys.argv[2] and not sys.argv[2].endswith('.mp4'):
        # 축약형: qa_gate post <id>  — prompts/<id>.json 의 clips_dir 로 경로를 푼다(2026-09-20, 인자 순서 실수 방지)
        vid=sys.argv[2]; pj=f'{ROOT}/data/longform/prompts/{vid}.json'
        PJ=json.load(open(pj)) if os.path.exists(pj) else {}
        cd=PJ.get('clips_dir',vid)
        # 재사용 클립('R:dir/Cxx')도 손 검수에 포함
        extra=sorted({f"{ROOT}/assets/flow/{v[2:]}.mp4" for v in PJ.get('map',{}).values() if str(v).startswith('R:')})
        clips=f'{ROOT}/assets/flow/{cd}'; cuts=os.path.expanduser(f'~/dev/flowmaker_public/projects/{vid}/cuts.json')
        dep=f'{ROOT}/remotion/out/{vid}_deploy.mp4'; tdir=f"{ROOT}/assets/longform/{PJ.get('thumb_dir',vid)}/thumb"   # 확장판(sim_student_ext)은 편 폴더(sim_student)를 쓴다
        thumbs=sorted(f'{tdir}/{t}' for t in os.listdir(tdir) if t.startswith('final-') and t.endswith('.png') and '_review' not in t) if os.path.isdir(tdir) else []
        print(f"post {vid}: clips={os.path.relpath(clips,ROOT)} cuts={'있음' if os.path.exists(cuts) else '없음'} deploy={os.path.relpath(dep,ROOT)} thumbs={len(thumbs)}")
        f=post(clips, cuts, dep, thumbs, extra, vid=vid)
        if '--id' not in sys.argv: sys.argv+=['--id',vid]
    else:
        f=post(sys.argv[2], sys.argv[3], sys.argv[4], [a for a in sys.argv[5:] if a.endswith('.png')])
    vid=None
    if '--id' in sys.argv: vid=sys.argv[sys.argv.index('--id')+1]
    sc=score_of(f); thr=threshold(mode)
    print(f"점수 {sc:.1f}/10 (임계 {thr}) — 감점3 {len(f)}건 · 감점1 {len(WARNS)}건" + (f" · 감점1: {'; '.join(WARNS)}" if WARNS else ''))
    if sc<thr and not f: f=[f'점수 {sc:.1f} < 임계 {thr} (감점1 누적)']
    if vid:
        fp=sys.argv[sys.argv.index('--hash')+1] if '--hash' in sys.argv else None
        subprocess.run(['python3',f'{ROOT}/scripts/review_log.py',vid,mode,'FAIL' if f else 'PASS','--score',f'{sc:.1f}']
                       +(['--hash',fp] if fp else [])+sum([['--find',x] for x in f[:8]],[]))
    if f:
        print("\n❌ FAIL — 배포 금지:"); [print("  -",x) for x in f]; sys.exit(1)
    print("\n✅ PASS — 모든 자동 점검 통과"); sys.exit(0)
