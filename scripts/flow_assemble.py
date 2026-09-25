#!/usr/bin/env python3
"""알리랑 flow 편 정본 조립기 — 편 id 하나로 본편+배포본을 만든다 (sed 파생 복사본 7개를 이것 하나로 통합, 2026-09-20).
입력: data/longform/prompts/<id>.json (save_prompts 가 남긴 map·new_prompts·lines_full·cards_full) — 없으면 scratch/flow_<id>/{lines,cards}.json
      scratch/flow_<id>/n##.wav (Typecast 나레이션) · assets/flow/<id>/<key>.mp4 (신규) · map 의 'R:dir/Cxx' (재사용)
출력: scratch/flow_<id>/<id>_body.mp4 → --deploy 면 인트로+본편+엔딩(음성) PCM concat → remotion/out/<id>_deploy.mp4
규칙(전부 스킬 §5): 자막 72px+금색 핵심어 · 무손실 문장 상하중앙 배너 · 카드 solo-big(1.8s)→소형, SPAN 설명구간 유지, SIDE(心L/力R/C) 또는 busy-map 자동배치 · 정지PNG fade 금지
사용: python3 scripts/flow_assemble.py <id> [--deploy | --clean | --short[=45]]
"""
import subprocess, os, sys, re as _re, json as _json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitconfig
_CFG = kitconfig.load()
if len(sys.argv)<2: sys.exit("사용법: flow_assemble.py <id> [--deploy]")
VID=sys.argv[1]; DEPLOY='--deploy' in sys.argv
# --clean: 자막·카드 없는 본편(재사용 라이브러리용) → <scratch>/clean/ 에 조각, <scratch>/<id>_clean.mp4. 배포본은 건드리지 않는다.
CLEAN='--clean' in sys.argv
if CLEAN: DEPLOY=False
# --short[=45]: 첫 장면 세로 쇼츠(docs/34 §4) — 앞 문장부터 약 45초(문장 경계), 1080×1920 흐린 배경 위 정사각 크롭. → <scratch>/<id>_short.mp4
_sa=next((a for a in sys.argv if a.startswith('--short')),None)
SHORT=(float(_sa.split('=')[1]) if '=' in _sa else 45.0) if _sa else None
if SHORT: DEPLOY=False; CLEAN=False
if DEPLOY:
    # 배포본은 대본 게이트(qa_gate pre) 통과 대본으로만 만든다 — 2026-09-23 고아 편이 대본 검사 없이 배포됨
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import script_source; script_source.require(VID)
ROOT = __import__('os').environ.get('ALLIRANG_ROOT', __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__),'..'))); W,H=1920,1080
_pp0=f'{ROOT}/data/longform/prompts/{VID}.json'
_p0=_json.load(open(_pp0)) if os.path.exists(_pp0) else {}
# 세로 쇼츠(1080×1920) — prompts/<id>.json 에 "vertical": true (2026-09-23 hangawi 인사 쇼츠).
# 쇼츠 화면은 위 ~200px(검색·채널)과 아래 ~380px(제목·버튼)을 앱이 가린다 → 카드는 TOPY 아래, 자막은 화면 73% 선(얼굴은 보통 가운데).
VERT=bool(_p0.get('vertical')) or bool(SHORT)
if VERT: W,H=1080,1920
TOPY=230 if VERT else 44
if SHORT: TOPY=450   # 쇼츠는 위 띠에 훅 제목 → 카드는 정사각 화면 안 위쪽
OUT=f"{ROOT}/{_p0.get('scratch_dir') or 'scratch/flow_'+VID}"; CLIPS=f"{ROOT}/assets/flow/{_p0.get('clips_dir') or VID}"
os.makedirs(OUT,exist_ok=True)
PD=f'{OUT}/short' if SHORT else OUT   # 쇼츠 조각·그림은 따로 — 가로 본편 그림을 덮어쓰지 않게
os.makedirs(PD,exist_ok=True)
TP=None
if SHORT:
    # 위 띠 훅 제목 = V3 두 어절(thumb.c) → 없으면 thumb.a. 앱 상단 UI(~200px) 아래에 둔다.
    _th=_p0.get('thumb',{}); _hd=(_p0.get('short_title') or (_th.get('c') or _th.get('a') or {}).get('head') or [])
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from thumb_lib import stroke_text, BHS
    TP=f'{PD}/title.png'; _ti=Image.new('RGBA',(W,H),(0,0,0,0)); _td=ImageDraw.Draw(_ti)
    _lg=f'{ROOT}/{_CFG["brand"]["logo_png"]}'
    if os.path.exists(_lg):   # 좌상단 로고 (오쌤 2026-09-25) — 쇼츠 UI 아이콘은 우상단이라 왼쪽 위는 비어 있다
        _li=Image.open(_lg).convert('RGBA'); _li.thumbnail((150,150)); _ti.alpha_composite(_li,(44,44))
    _y=190 if len(_hd)>1 else 250
    for _txt,_sz,_col in _hd:
        _f=ImageFont.truetype(BHS,min(int(_sz*1.3),172))   # 폰 화면 기준 크게 (오쌤 2026-09-25 재검토)
        while _td.textlength(_txt,font=_f)>W-120: _f=ImageFont.truetype(BHS,_f.size-6)
        _w=_td.textlength(_txt,font=_f); _bb=_f.getbbox(_txt); _x=(W-_w)/2
        if _col=='BOX':
            _pd=int(_f.size*0.16); _td.rounded_rectangle((_x-_pd,_y+_bb[1]-_pd,_x+_w+_pd,_y+_bb[3]+_pd),radius=int(_pd*0.7),fill=(230,32,42,255))
            stroke_text(_td,(_x,_y),_txt,_f,(255,255,255,255),6,(0,0,0,110))
        else: stroke_text(_td,(_x,_y),_txt,_f,(255,255,255,255),10,(0,0,0,255))
        _y+=_bb[3]+30
    _ti.save(TP)
    TOPY=max(TOPY,int(_y)+20)   # 제목이 커진 뒤 카드가 띠 밑에 깔렸다(bisang 2026-09-25) → 카드는 제목 아래부터
FB=f'{ROOT}/remotion/public/fonts/NotoSansCJKkr-Black.otf'; FM=f'{ROOT}/remotion/public/fonts/NotoSansCJKkr-Medium.otf'
_pp=f'{ROOT}/data/longform/prompts/{VID}.json'
_plan=_json.load(open(_pp)) if os.path.exists(_pp) else {}
_lines=_plan.get('lines_full') or _json.load(open(f'{OUT}/lines.json'))
_cards=_plan.get('cards_full') or _json.load(open(f'{OUT}/cards.json'))
_M=_plan.get('map') or {}
if not _M: sys.exit(f"map 없음 — save_prompts.py {VID} 로 컷 계획을 먼저 저장하라")
# 화자 태그 [[child]] · [[adult:sad]] 는 **더빙이 목소리를 고르는 표시**이지 자막이 아니다.
# bakeTypecast 는 떼고 읽지만 자막은 그대로 그렸다 — 금일 편이 「[[child]] 엄마, …」로 배포됐다(2026-09-22).
_TAG=_re.compile(r'^\s*\[\[[^\]]+\]\]\s*')
def _say(t): return _TAG.sub('', t)
S=[_say(l['text']) for l in _lines]
# 실제로 그린 자막을 남긴다 — qa_gate 가 이걸 보고 태그 유출을 잡는다(믿지 말고 확인)
_json.dump([{'g':l['g'],'sub':t} for l,t in zip(_lines,S)],
           open(f'{OUT}/subs.json','w'), ensure_ascii=False, indent=1)
def clip_for(g):
    v=_M[str(g)]
    return f'{ROOT}/assets/flow/{v[2:]}.mp4' if v.startswith('R:') else f'{CLIPS}/{v}.mp4'
CARD={int(k):tuple(v) for k,v in _cards['CARD'].items()}
HILITE={int(k):v for k,v in _cards['HILITE'].items()}
SPAN={int(k):int(v) for k,v in _cards.get('SPAN',{}).items()}
SIDE={int(k):v for k,v in _cards.get('SIDE',{}).items()}
COMPARE={int(k):[int(x) for x in v] for k,v in _cards.get('COMPARE',{}).items()}  # 대비 카드(2026-09-24 sim_hurt 상심) — 그 줄만 두 카드를 나란히
HL=(255,206,58,255)  # 핵심어 강조색(밝은 금색, 검은 외곽선과 대비)
GAP=0.30; LEAD=0.25; BIG_T=1.8   # 카드 중앙 크게 유지 시간(오쌤 2026-09-20 「조금 더 길게」)
MIN_CARD=5.0   # 한자 카드 최소 표시 시간(초) — 짧은 컷이면 다음 컷까지 소형 카드를 이어 유지
def ff(*a): subprocess.run(['ffmpeg','-y','-loglevel','error',*a],check=True)
def dur(f): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]).decode())

_MOTION_CACHE={}
def _motion_profile(clip):
    """clip 전체를 motion_density.py 와 같은 10fps·24x14 격자 화면변화율로 훑어, 프레임쌍별 변화율 배열을 반환(클립당 1회, 캐시).
    같은 클립을 여러 줄이 나눠 쓸 때 항상 0초부터 트림하면 그 클립의 정지 구간만 반복 노출돼 motion_density 「정지」가 뛴다
    (2026-09-24 su_hand Psh2_4 겪음 — 팬이 클립 앞쪽에만 있고 뒤는 멈춤, Psh2_9 는 반대로 뒤쪽에만 있어 고정 오프셋으론 둘 다 못 맞춘다).
    그래서 실제로 어디가 가장 움직이는지 스캔해서 그 구간을 고른다."""
    if clip in _MOTION_CACHE: return _MOTION_CACHE[clip]
    import tempfile, glob as _glob
    d=tempfile.mkdtemp(); FPS=10
    try:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',clip,'-vf',f'fps={FPS},scale=240:135','-pix_fmt','gray',f'{d}/f%05d.png'],check=True)
        fr=[np.asarray(Image.open(f),dtype=np.float32) for f in sorted(_glob.glob(f'{d}/*.png'))]
        if len(fr)<2: prof=np.array([0.0])
        else:
            GY,GX=14,24; H,W=fr[0].shape; ch,cw=H//GY,W//GX
            change=[]
            for a,b in zip(fr,fr[1:]):
                diff=np.abs(b-a); g=diff[:GY*ch,:GX*cw].reshape(GY,ch,GX,cw).mean(axis=(1,3))
                change.append((g>6.0).mean())
            prof=np.array(change)
    finally:
        for f in _glob.glob(f'{d}/*.png'): os.remove(f)
        os.rmdir(d)
    _MOTION_CACHE[clip]=(prof,FPS)
    return _MOTION_CACHE[clip]

def best_ss(clip,need,raw):
    """need 초짜리 연속 구간 중 화면변화율 평균이 가장 높은 시작 시각(초)을 돌려준다. 못 찾으면 0.0."""
    span=raw-need
    if span<=0.05: return 0.0
    prof,fps=_motion_profile(clip)
    win=max(1,round(need*fps))
    if win>=len(prof): return 0.0
    csum=np.concatenate(([0.0],np.cumsum(prof)))
    sums=csum[win:]-csum[:-win]   # 각 시작 프레임의 창 합
    best=int(np.argmax(sums))
    return min(span, best/fps)
def fit(draw,text,font_path,size,maxw):
    while size>28:
        f=ImageFont.truetype(font_path,size)
        if draw.textlength(text,font=f)<=maxw: return f
        size-=4
    return ImageFont.truetype(font_path,size)

def _segs(line,key):
    """line 을 (텍스트,색) 조각으로. key 가 있으면 그 부분만 강조색."""
    if key and key in line:
        i=line.index(key)
        return [(line[:i],(255,255,255,255)),(key,HL),(line[i+len(key):],(255,255,255,255))]
    return [(line,(255,255,255,255))]

FOOT={int(k):v for k,v in _cards.get('FOOT',{}).items()}   # 💡 각주 (2026-09-23 gae) — 그 줄 자막 위에 작은 글씨로

def sub_png(text,path,key=None,center=False,foot=None):
    """하단 자막 — 모바일 크게(72), 1줄(길면 쉼표에서 2줄), 박스는 글자 완전 덮음, 핵심어 강조색.
    center=True 면 무손실 안내 배너 스타일 — 상하 중앙, 배경 띠 넓게(다른 편과 통일)."""
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    FS=72; f=ImageFont.truetype(FB,FS); OL=4; PADX=40; PADY=22; maxw=W-180
    lines=[text]
    if VERT:
        FS=66; f=ImageFont.truetype(FB,FS); maxw=W-120
        # 쉼표·마침표에서 먼저 끊는다(「한가위만 / 같아라」처럼 말 중간에서 끊기지 않게), 그래도 길면 낱말 단위로
        import re as _r
        chunks=[c.strip() for c in _r.split(r'(?<=[,.!?])\s+', text) if c.strip()]
        lines=[]
        for ck in chunks:
            if lines and d.textlength(lines[-1]+' '+ck,font=f)<=maxw and len(chunks)>3: lines[-1]+=' '+ck; continue
            cur=''
            for wd in ck.split(' '):
                t2=(cur+' '+wd).strip()
                if cur and d.textlength(t2,font=f)>maxw: lines.append(cur); cur=wd
                else: cur=t2
            if cur: lines.append(cur)
    elif d.textlength(text,font=f)>maxw:
        # 가운데에 가장 가까운 「, 」·「. 」에서 끊는다(±12자) — 옛 방식(가운데+6 안의 마지막 쉼표, 없으면 공백)은
        # 「비행은 날 / 비, 다닐 행」「넷째, / 애용…」처럼 말 중간에서 끊었다(2026-09-24 bisang).
        mid=len(text)//2
        cands=[i for i,ch in enumerate(text[:-1]) if ch in ',.' and text[i+1]==' ' and abs(i-mid)<=12]
        cut=min(cands,key=lambda i:abs(i-mid)) if cands else text.rfind(' ',0,mid+6)
        if cut>0: lines=[text[:cut+1].strip(),text[cut+1:].strip()]
        # 2줄로 끊어도 한쪽이 화면 밖으로 넘치면([[teacher]] 회상처럼 긴 한 덩어리, 2026-09-24 allirang 겪음) —
        # 절(,.) 단위로 모으다 넘치면 낱말 단위로 마저 접는 일반 줄바꿈으로 다시 짠다(VERT 방식과 같은 원리).
        if any(d.textlength(ln,font=f)>maxw for ln in lines):
            import re as _r2
            chunks=[c.strip() for c in _r2.split(r'(?<=[,.!?])\s+', text) if c.strip()]
            lines=[]
            for ck in chunks:
                if lines and d.textlength(lines[-1]+' '+ck,font=f)<=maxw: lines[-1]+=' '+ck; continue
                cur=''
                for wd in ck.split(' '):
                    t2=(cur+' '+wd).strip()
                    if cur and d.textlength(t2,font=f)>maxw: lines.append(cur); cur=wd
                    else: cur=t2
                if cur: lines.append(cur)
    asc,desc=f.getmetrics(); lh=asc+desc+12
    widths=[d.textlength(ln,font=f) for ln in lines]
    bw=max(widths); bh=lh*len(lines); bx=(W-bw)/2
    if center:
        by=(H-bh)/2
        d.rectangle((0,by-PADY-14,W,by+bh+PADY+14),fill=(0,0,0,160))   # 상하중앙 가로 띠
    else:
        by=(int(H*0.73)-bh//2) if VERT else H-64-bh
        d.rounded_rectangle((bx-PADX-OL,by-PADY,bx+bw+PADX+OL,by+bh+PADY),radius=22,fill=(0,0,0,180))
    y=by
    for ln,w in zip(lines,widths):
        x=(W-w)/2
        for seg,col in _segs(ln,key):
            if not seg: continue
            for dx in range(-OL,OL+1):
                for dy in range(-OL,OL+1):
                    if dx*dx+dy*dy<=OL*OL: d.text((x+dx,y+dy),seg,font=f,fill=(0,0,0,235))
            d.text((x,y),seg,font=f,fill=col); x+=d.textlength(seg,font=f)
        y+=lh
    if foot:
        # 각주는 이야기 뒤에 붙는 한 줄이다(CLAUDE.md 어원 규칙) — 자막보다 작게, 자막 박스 바로 위 가운데.
        # 폰트에 이모지가 없어 💡 는 노란 점으로 대신 그린다.
        # 📖 사전·문헌 근거는 파란 점, 💡 풀이는 노란 점, 표시 없는 줄(예: 「대충영어 오쌤 × 알리랑」)은 점 없이
        dotcol=(96,165,250,255) if '📖' in foot else ((255,214,64,255) if '💡' in foot else None)
        ft=foot.replace('💡','').replace('📖','').strip(); f2=ImageFont.truetype(FM,38); a2,d2=f2.getmetrics()
        tw=d.textlength(ft,font=f2); dot=22 if dotcol else 0; gap=14 if dotcol else 0; fw=dot+gap+tw
        fy=(by-PADY if not center else H-64-a2-d2)-24-(a2+d2); fx=(W-fw)/2
        d.rounded_rectangle((fx-24,fy-12,fx+fw+24,fy+a2+d2+12),radius=18,fill=(0,0,0,150))
        cy=fy+(a2+d2)/2
        if dotcol: d.ellipse((fx,cy-dot/2,fx+dot,cy+dot/2),fill=dotcol)
        d.text((fx+dot+gap,fy),ft,font=f2,fill=(255,255,255,235))
    im.save(path)

def card_geom(hanja,reading,big):
    """카드 크기·폰트 계산(그리기와 배치가 같은 값 쓰게)."""
    d=ImageDraw.Draw(Image.new('RGBA',(10,10)))
    if big:
        maxw=W-360; hs=230 if len(hanja)==1 else (195 if len(hanja)==2 else 150)
        fh=fit(d,hanja,FB,hs,maxw); fr=fit(d,reading,FM,74,maxw)
    else:
        maxw=760; hs=120 if len(hanja)<=2 else 92
        fh=fit(d,hanja,FB,hs,maxw); fr=fit(d,reading,FM,46,maxw)
    hb=fh.getbbox(hanja); rb=fr.getbbox(reading)
    hw,hh=d.textlength(hanja,font=fh),hb[3]-hb[1]; rw,rh=d.textlength(reading,font=fr),rb[3]-rb[1]
    gap=int(hh*0.34); pad=int(hh*0.30)
    cw=max(hw,rw)+pad*2; ch=hh+gap+rh+pad*2
    return dict(fh=fh,fr=fr,hb=hb,rb=rb,hw=hw,hh=hh,rw=rw,rh=rh,gap=gap,pad=pad,cw=cw,ch=ch)

def busy_map(clip,ts=None,gw=192,gh=108,n=8):
    """피사체가 한 번이라도 지나가는 곳의 맵. 낮을수록 한산.
    오쌤 2026-09-23 「단어가 이미지를 가린다」(사랑 愛情·家族愛 카드가 엄마 얼굴을 덮음) — 옛 방식은 앞 3초 평균의 그라디언트만 봐서
    ①카메라 push-in 으로 뒤에 커지는 얼굴을 못 보고 ②매끈한 클레이 얼굴(그라디언트 낮음)을 빈 곳으로 읽었다.
    → 클립 전 구간 n점을 보고, 그라디언트 + 배경색(위·좌·우 테두리 중앙값)에서 먼 픽셀(피사체) 마스크의 **최대값**을 쓴다. ts 는 호환용(무시)."""
    d=dur(clip); acc=None
    for i in range(n):
        t=0.15+max(d-0.3,0)*i/max(n-1,1); f=f'{OUT}/_bm{i}.png'
        try: ff('-ss',f'{t:.2f}','-i',clip,'-frames:v','1','-vf',f'scale={gw}:{gh}',f)
        except Exception: continue
        a=np.asarray(Image.open(f).convert('RGB'),dtype=np.float32); g=a.mean(2)
        b=np.zeros_like(g); b[:,:-1]+=np.abs(np.diff(g,axis=1)); b[:-1,:]+=np.abs(np.diff(g,axis=0))
        border=np.concatenate([a[:4].reshape(-1,3),a[:,:4].reshape(-1,3),a[:,-4:].reshape(-1,3)])
        subj=(np.sqrt(((a-np.median(border,axis=0))**2).sum(2))>38).astype(np.float32)
        m=b/(b.max()+1e-6)+subj
        acc=m if acc is None else np.maximum(acc,m)
    return acc if acc is not None else np.zeros((gh,gw))

def place(cw,ch,busy,y_hi_frac=0.60,gw=192,gh=108):
    """카드가 들어갈 가장 한산한 (x0,y0). 하단(자막)·화면밖 제외, 슬라이딩 윈도로 busy 최소 위치."""
    best=None; sx,sy=gw/W,gh/H
    xs=list(range(40,int(W-cw-40),90)) or [40]
    y_lo=TOPY if SHORT else 40   # 쇼츠는 위 띠(로고·훅 제목) 아래부터 — 자동배치가 40 에서 시작해 제목을 덮었다(bisang 2026-09-25)
    ys=list(range(y_lo,max(y_lo+1,int(H*y_hi_frac-ch)),64)) or [y_lo]
    for y0 in ys:
        for x0 in xs:
            gx0,gy0=int(x0*sx),int(y0*sy); gx1,gy1=int((x0+cw)*sx),int((y0+ch)*sy)
            score=float(busy[gy0:gy1,gx0:gx1].sum())
            # 중앙 근처 약간 감점(겹치면 더 나쁨) — 가장자리 선호
            cx=(x0+cw/2)/W; score+= (1-abs(cx-0.5)*2)*busy.sum()*0.02
            if best is None or score<best[0]: best=(score,x0,y0)
    gx0,gy0=int(best[1]*sx),int(best[2]*sy); ov=float(busy[gy0:int((best[2]+ch)*sy),gx0:int((best[1]+cw)*sx)].mean())
    if ov>0.9: print(f'   ⚠ 카드가 피사체를 덮는다(겹침 {ov:.2f}) — 빈 자리 없는 클로즈업, 컷 교체 검토')
    return best[1],best[2]

def draw_card(hanja,reading,path,big,x0,y0):
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im); g=card_geom(hanja,reading,big)
    pad=g['pad']; d.rounded_rectangle((x0,y0,x0+g['cw'],y0+g['ch']),radius=int(pad*0.9),fill=(255,255,255,238))
    hx=x0+(g['cw']-g['hw'])/2; hy=y0+pad-g['hb'][1]
    d.text((hx,hy),hanja,font=g['fh'],fill=(28,38,66,255))
    rx=x0+(g['cw']-g['rw'])/2; ry=y0+pad+g['hh']+g['gap']-g['rb'][1]
    d.text((rx,ry),reading,font=g['fr'],fill=(14,116,144,255)); im.save(path)

def draw_strip(words,path,gapx=22,y0=None):
    y0=TOPY if y0 is None else y0
    """복습 카드 줄: [(hanja,reading),…] 소형 카드를 가로로 이어 상단 중앙에. 폭이 넘치면 글자를 줄인다."""
    geos=[card_geom(h,r,False) for h,r in words]
    tot=sum(g['cw'] for g in geos)+gapx*(len(geos)-1)
    scale=min(1.0,(W-88)/tot)
    im=Image.new('RGBA',(W,H),(0,0,0,0))
    x=(W-tot*scale)/2; maxh=max(g['ch'] for g in geos)*scale
    for (h,r),g in zip(words,geos):
        tmp=f'{path}.tmp.png'; draw_card(h,r,tmp,False,0,0)
        card=Image.open(tmp).crop((0,0,int(g['cw'])+1,int(g['ch'])+1))
        if scale<1: card=card.resize((int(card.width*scale),int(card.height*scale)),Image.LANCZOS)
        im.alpha_composite(card,(int(x),int(y0+(maxh-card.height)/2))); x+=g['cw']*scale+gapx*scale   # 높이 다른 카드(3자)는 세로 중앙 정렬
    os.remove(tmp); im.save(path)
REVIEW={int(k):[tuple(w) for w in v] for k,v in _cards.get('REVIEW',{}).items()}
for n,ws in REVIEW.items():
    for h,r in ws:
        if r not in S[n-1]: sys.exit(f'REVIEW {n}: 카드 낱말 「{r}」 이 자막에 없음: 「{S[n-1]}」')

# ── Pass 1: 컷별 필요 시간 계산 후, 카드가 짧으면 다음 컷까지 이어 유지할 carry 결정 ──
NEED={};
for n,text in enumerate(S,1):
    nr=f'{OUT}/n{n:02d}.wav'
    NEED[n]=(LEAD+dur(nr)+GAP) if os.path.exists(nr) else 0
CARRY={}   # 컷 n 에 이어 표시할 (hanja,reading) 소형 카드 — 카드 설명 구간(SPAN) 내내 유지
for n in list(CARD):
    end=SPAN.get(n, n)                      # SPAN 없으면 최소 MIN_CARD 만큼(다음 카드 전까지)
    m=n+1
    if n not in SPAN:
        remain=MIN_CARD-NEED.get(n,0)
        while remain>0 and m<=len(S) and m not in CARD:
            CARRY[m]=CARD[n]; remain-=NEED.get(m,0); m+=1
    else:
        while m<=end and m<=len(S) and m not in CARD:
            CARRY[m]=CARD[n]; m+=1

parts=[]
# 같은 클립을 여러 줄이 나눠 쓸 때 항상 0초부터 다시 트림하면 그 구간 전체가 같은 오프닝만 반복해 motion_density 「정지」가 뛴다
# (2026-09-24 su_hand Psh2_4·Psh2_9 겪음). 클립마다 움직임이 몰린 위치가 다르다 — Psh2_4 는 앞 2초에 팬이 끝나고 뒤는 멈추고,
# Psh2_9 는 반대로 앞이 멈춰 있다가 뒤에서 손모양이 바뀐다. 고정 오프셋(끝쪽으로 민다 등)은 둘 중 하나에서 반드시 틀린다 —
# best_ss() 가 클립을 실제로 훑어 화면변화율이 가장 높은 need초 구간을 찾아준다(등속 k=1 트림에 한해서만 의미 있다).
_tot=0.0
for n,text in enumerate(S,1):
    if SHORT and _tot>=SHORT: break
    clip=clip_for(n); narr=f'{OUT}/n{n:02d}.wav'
    if not os.path.exists(clip): print('skip C%02d'%n); continue
    # 배속 상한 1.7 → 2.6: minterpolate 로 중간 프레임을 합성하게 된 뒤로 더 늘려도 뭉개지지 않는다.
    # 예전 1.7 상한은 남는 시간을 tpad 정지 프레임(최대 4초)으로 메꿔, 그 구간이 motion_density 「정지프레임」을 크게 끌어올렸다
    # (2026-09-24 아리랑 오쌤 육성 줄 14.8초 대 클립 6초 — 정지 34%로 밀도 FAIL). 2.6 로 올리면 이 줄도 거의 안 멈추고 다 늘어난다.
    need=LEAD+dur(narr)+GAP; raw=dur(clip); k=min(need/raw,2.6) if need>raw else 1.0
    ss_off=best_ss(clip,need,raw) if k==1.0 and raw>need else 0.0
    if CLEAN:
        os.makedirs(f'{OUT}/clean',exist_ok=True)
        spng=f'{OUT}/clean/blank.png'
        if not os.path.exists(spng): Image.new('RGBA',(W,H),(0,0,0,0)).save(spng)
        seg=f'{OUT}/clean/seg{n:02d}.mp4'
    else:
        spng=f'{PD}/s{n:02d}.png'; sub_png(text,spng,HILITE.get(n),center=('무손실' in text and '원음' in text),foot=FOOT.get(n)); seg=f'{PD}/seg{n:02d}.mp4'
    # k>1(슬로모션 늘리기)일 때 setpts 는 프레임을 그냥 복제한다 — 긴 오쌤 육성 줄처럼 6초 클립을 1.7배 늘리면
    # 연속 출력 프레임이 같은 원본 프레임을 여러 번 가리켜 motion_density 「정지프레임」이 급증한다(2026-09-24 아리랑 겪음).
    # minterpolate 로 중간 프레임을 합성해 복제 정지를 없앤다 — 등속(k=1) 컷은 비용·화질 리스크 없이 그대로 둔다.
    slowmo = f",minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1" if k>1.0 else ",fps=30"
    base=f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts={k:.4f}*PTS{slowmo},tpad=stop_mode=clone:stop_duration=4"
    if SHORT:   # 가로 클립 → 가운데 정사각(1080) + 위아래는 같은 컷을 흐리게 채움
        base=(f"setpts={k:.4f}*PTS{slowmo},tpad=stop_mode=clone:stop_duration=4,split[_b][_f];"
              f"[_b]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:2,eq=brightness=0.05[_bb];"
              f"[_f]scale=-2:{W},crop={W}:{W}[_ff];[_bb][_ff]overlay=0:{(H-W)//2}[_sq];movie={TP}[_t];[_sq][_t]overlay=0:0")
    _tot+=need
    adelay=f"[2:a]aformat=sample_rates=48000:channel_layouts=mono,adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad[a]"
    if CLEAN:
        fc=f"[0:v]{base}[v0];[v0][1:v]overlay=0:0[v];{adelay}"
        ff('-ss',f'{ss_off:.2f}','-i',clip,'-i',spng,'-i',narr,'-filter_complex',fc,
           '-map','[v]','-map','[a]','-t',f'{need:.2f}','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le',seg)
    elif n in CARD:
        hanja,reading=CARD[n]; bp=f'{PD}/cb{n:02d}.png'; sp=f'{PD}/cs{n:02d}.png'
        busy=busy_map(clip,[0.3,0.8,1.3,2.2,3.0])
        gb=card_geom(hanja,reading,True); gs=card_geom(hanja,reading,False)
        sd=SIDE.get(n)
        # SIDE 끝의 's'(Ls/Rs/Cs) = 큰 카드 없이 처음부터 소형 — 피사체가 화면 중간까지 차서 큰 카드 자리가 없는 컷 (2026-09-23 원방각 원형·사각형·삼각형)
        small_only=bool(sd) and sd.endswith('s'); sd=sd[:-1] if small_only else sd
        def _pos(g):
            if sd=='L': return 44,TOPY
            if sd=='R': return W-g['cw']-44,TOPY
            if sd=='C': return (W-g['cw'])//2,TOPY
            return place(g['cw'],g['ch'],busy)
        bx,by=_pos(gb); sxp,syp=_pos(gs)
        draw_card(hanja,reading,bp,not small_only,*( (sxp,syp) if small_only else (bx,by) )); draw_card(hanja,reading,sp,False,sxp,syp)
        print(f'   card pos big=({bx},{by}) small=({sxp},{syp})')
        # 정지 PNG + enable 로 하드 전환(카드 stills 는 -loop 1 로 전 구간 유지). fade 는 단일프레임이라 못 씀.
        fc=(f"[0:v]{base}[v0];"
            f"[v0][1:v]overlay=0:0[v1];"
            f"[v1][3:v]overlay=0:0:enable='lt(t,{BIG_T:.2f})'[v2];"
            f"[v2][4:v]overlay=0:0:enable='gte(t,{BIG_T:.2f})'[v];{adelay}")
        ff('-ss',f'{ss_off:.2f}','-i',clip,'-loop','1','-t',f'{need:.2f}','-i',spng,'-i',narr,
           '-loop','1','-t',f'{need:.2f}','-i',bp,'-loop','1','-t',f'{need:.2f}','-i',sp,'-filter_complex',fc,
           '-map','[v]','-map','[a]','-t',f'{need:.2f}','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le',seg)
    elif n in COMPARE:
        # 대비 카드: 두 카드를 각자 SIDE(L/R/C) 위치에 소형으로 함께 그린다 — 「같은 소리, 다른 글자」를 한 화면에.
        keys=COMPARE[n]; sp=f'{PD}/cp{n:02d}.png'
        im=Image.new('RGBA',(W,H),(0,0,0,0))
        for ck in keys:   # ck (card-key), 절대 k 를 쓰지 않는다 — k 는 위의 배속 배율, 재사용하면 로그가 그걸 덮어쓴다(값 자체는 base 에 이미 굳어 있어 영상은 안전하지만 진단 로그가 틀려 보인다, 2026-09-24 겪음)
            hanja,reading=CARD[ck]; g=card_geom(hanja,reading,False)
            sd=SIDE.get(ck); sd=sd[:-1] if sd and sd.endswith('s') else sd
            if sd=='L': sxp,syp=44,TOPY
            elif sd=='R': sxp,syp=W-g['cw']-44,TOPY
            elif sd=='C': sxp,syp=(W-g['cw'])//2,TOPY
            else: sxp,syp=44,TOPY
            tmp=f'{sp}.tmp{ck}.png'; draw_card(hanja,reading,tmp,False,0,0)
            card=Image.open(tmp).crop((0,0,int(g['cw'])+1,int(g['ch'])+1))
            im.alpha_composite(card,(int(sxp),int(syp))); os.remove(tmp)
        im.save(sp)
        fc=f"[0:v]{base}[v0];[v0][1:v]overlay=0:0[v1];[v1][3:v]overlay=0:0[v];{adelay}"
        ff('-ss',f'{ss_off:.2f}','-i',clip,'-loop','1','-t',f'{need:.2f}','-i',spng,'-i',narr,'-loop','1','-t',f'{need:.2f}','-i',sp,'-filter_complex',fc,
           '-map','[v]','-map','[a]','-t',f'{need:.2f}','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le',seg)
    elif n in REVIEW:
        # 복습 문장(낱말 나열)에도 단어카드 — 오쌤 2026-09-20 「복습에도 단어카드 사용 원칙」: 낱말마다 소형 카드를 한 줄로 상단 중앙
        sp=f'{PD}/cr{n:02d}.png'; draw_strip(REVIEW[n],sp)
        fc=f"[0:v]{base}[v0];[v0][1:v]overlay=0:0[v1];[v1][3:v]overlay=0:0[v];{adelay}"
        ff('-ss',f'{ss_off:.2f}','-i',clip,'-loop','1','-t',f'{need:.2f}','-i',spng,'-i',narr,'-loop','1','-t',f'{need:.2f}','-i',sp,'-filter_complex',fc,
           '-map','[v]','-map','[a]','-t',f'{need:.2f}','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le',seg)
    elif n in CARRY:
        # 이전 카드의 소형 카드를 이 컷 전체에 이어 유지(짧은 컷 보정)
        hanja,reading=CARRY[n]; sp=f'{PD}/cc{n:02d}.png'
        gs=card_geom(hanja,reading,False)
        # 이 소형카드가 어느 카드의 연장인지 찾아 SIDE 적용
        _src=[k for k in CARD if k in SPAN and k<n<=SPAN[k]]
        _sd=SIDE.get(_src[0]) if _src else None
        _sd=_sd[:-1] if _sd and _sd.endswith('s') else _sd
        if _sd=='L': sxp,syp=44,TOPY
        elif _sd=='R': sxp,syp=W-gs['cw']-44,TOPY
        elif _sd=='C': sxp,syp=(W-gs['cw'])//2,TOPY
        else:
            busy=busy_map(clip,[0.3,1.0,2.0]); sxp,syp=place(gs['cw'],gs['ch'],busy)
        draw_card(hanja,reading,sp,False,sxp,syp)
        fc=f"[0:v]{base}[v0];[v0][1:v]overlay=0:0[v1];[v1][3:v]overlay=0:0[v];{adelay}"
        ff('-ss',f'{ss_off:.2f}','-i',clip,'-loop','1','-t',f'{need:.2f}','-i',spng,'-i',narr,'-loop','1','-t',f'{need:.2f}','-i',sp,'-filter_complex',fc,
           '-map','[v]','-map','[a]','-t',f'{need:.2f}','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le',seg)
    else:
        fc=f"[0:v]{base}[v0];[v0][1:v]overlay=0:0[v];{adelay}"
        ff('-ss',f'{ss_off:.2f}','-i',clip,'-i',spng,'-i',narr,'-filter_complex',fc,
           '-map','[v]','-map','[a]','-t',f'{need:.2f}','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le',seg)
    print(f'C{n:02d} {raw:.1f}s→{need:.1f}s (×{k:.2f}){" [card]" if n in CARD else ""}'); parts.append(seg)
if SHORT:
    # 첫 프레임 = V3 클로즈업 + 두 어절(docs/34 §4) — 히어로 c 이미지를 0.5초 앞에 둔다
    _hc=next((f'{CLIPS}/thumb/c{e}' for e in ('.png','.jpg','.jpeg','.webp') if os.path.exists(f'{CLIPS}/thumb/c{e}')),None)
    if _hc:
        _s0=f'{PD}/seg00.mp4'
        fc=(f"[0:v]split[_b][_f];[_b]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:2[_bb];"
            f"[_f]scale=-2:{W},crop={W}:{W}:iw-{W}:0[_ff];[_bb][_ff]overlay=0:{(H-W)//2}[_sq];[_sq][1:v]overlay=0:0,fps=30,format=yuv420p[v]")
        ff('-loop','1','-t','0.5','-i',_hc,'-i',TP,'-f','lavfi','-t','0.5','-i','anullsrc=r=48000:cl=mono','-filter_complex',fc,
           '-map','[v]','-map','2:a','-t','0.5','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le',_s0)
        parts.insert(0,_s0)
lst=f'{OUT}/clean/list.txt' if CLEAN else f'{PD}/list.txt'; open(lst,'w').write(''.join(f"file '{p}'\n" for p in parts))
final=f'{OUT}/{VID}_clean.mp4' if CLEAN else f'{OUT}/{VID}_short.mp4' if SHORT else f'{OUT}/{VID}_body.mp4'
ff('-f','concat','-safe','0','-i',lst,'-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le','-movflags','+faststart',final)
print('→',final,f'{dur(final):.1f}s')

if DEPLOY:
    # 인트로+본편+엔딩 concat 은 deploy_concat.py 한 곳 — 에셋만 바뀌면 `deploy_concat.py <id>` 로 본편 재조립 없이 재배포본
    sys.path.insert(0,f'{ROOT}/scripts'); from deploy_concat import concat
    concat(final, f'{ROOT}/remotion/out/{VID}_deploy.mp4')
