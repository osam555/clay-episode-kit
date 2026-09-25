#!/usr/bin/env python3
"""알리랑 썸네일 정본 — 유명 유튜브(EBS·헉깨비·건축사전) 대조로 확정한 타이포 + **요소 bbox 자동 기록**.
bbox 를 meta.json 으로 남겨 `visual_check.py thumb` 가 잘림·크기·겹침을 자동 검사한다.
(오쌤 2026-09-20 「리뷰 시스템이 제대로 작동하지 않는 문제 해결」)"""
import json, os, sys
from PIL import Image, ImageChops, ImageDraw, ImageFont
W,H=1280,720
MARGIN=28
R = __import__('os').environ.get('ALLIRANG_ROOT', __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__),'..')))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitconfig
_CFG = kitconfig.load(R)
_TH = _CFG['thumbnail']
BHS=f'{R}/{_TH["headline_font"]}'
FB=f'{R}/{_TH["fallback_font"]}'
WM=f'{R}/{_CFG["brand"]["wordmark_png"]}'
YEL=(255,214,0,255); WHT=(255,255,255,255); NAVY=(24,34,62,255); CYAN=(14,116,144,255)

def stroke_text(d, xy, text, f, fill, stroke, stroke_fill):
    """외곽선 글자. PIL stroke_width(FreeType stroker)는 BlackHanSans 일부 글자(구눠는뒤뭐아안야양임입하히 — ㅇ·속 윤곽)에서
    테두리를 빠뜨린다 → 글자 마스크를 원판으로 팽창시켜 외곽선을 직접 만든다(둥근 이음 = stroker 와 같은 모양)."""
    size=d.im.size; m=Image.new('L',size,0); ImageDraw.Draw(m).text(xy,text,font=f,fill=255)
    bb=m.getbbox()
    if bb and stroke>0:
        x0,y0,x1,y1=max(0,bb[0]-stroke),max(0,bb[1]-stroke),min(size[0],bb[2]+stroke),min(size[1],bb[3]+stroke)
        g=m.crop(bb); o=Image.new('L',(x1-x0,y1-y0),0)
        for dy in range(-stroke,stroke+1):
            for dx in range(-stroke,stroke+1):
                if dx*dx+dy*dy<=stroke*stroke+stroke:
                    sh=Image.new('L',o.size,0); sh.paste(g,(bb[0]-x0+dx,bb[1]-y0+dy)); o=ImageChops.lighter(o,sh)
        sm=Image.new('L',size,0); sm.paste(o,(x0,y0))
        d.bitmap((0,0),sm,fill=stroke_fill)
    d.text(xy,text,font=f,fill=fill)

class Thumb:
    def __init__(self, bg_path):
        self.im=Image.open(bg_path).convert('RGBA'); self.d=ImageDraw.Draw(self.im); self.els=[]
    def _rec(self,name,bbox,**kw): self.els.append(dict(name=name,bbox=[int(v) for v in bbox],**kw))

    def _stext(self, xy, text, f, fill, stroke, stroke_fill): stroke_text(self.d, xy, text, f, fill, stroke, stroke_fill)

    def scrim(self, frac=0.55, alpha=165):
        g=Image.new('L',(1,H),0)
        for y in range(H):
            t=max(0.0,(y-H*(1-frac))/(H*frac)); g.putpixel((0,y),int(alpha*(t**1.3)))
        ov=Image.new('RGBA',(W,H),(0,0,0,255)); ov.putalpha(g.resize((W,H)))
        self.im=Image.alpha_composite(self.im,ov); self.d=ImageDraw.Draw(self.im)

    def fit(self,text,size,maxw,font=BHS):
        while size>48 and self.d.textlength(text,font=ImageFont.truetype(font,size))>maxw: size-=4
        return size

    def hlbox(self, x, bottom, text, size, boxfill=(230,32,42,255), textfill=(255,255,255,255), stroke=6, name=None, font=BHS):
        """펀치 낱말에 색 박스(콩나물샘·헉스쿨 식) — 대비·시선을 확 끈다. 박스 위 흰 글자."""
        size=self.fit(text,size,W-x-MARGIN-40,font); f=ImageFont.truetype(font,size); bb=f.getbbox(text)
        gh=bb[3]-bb[1]; tw=self.d.textlength(text,font=f); pad=int(size*0.16); y=bottom-gh-bb[1]-pad
        self.d.rounded_rectangle((x-pad,y+bb[1]-pad,x+tw+pad,y+bb[3]+pad),radius=int(pad*0.7),fill=boxfill)
        self._stext((x,y),text,f,textfill,stroke,(0,0,0,110))
        self._rec(name or text,(x-pad,y+bb[1]-pad,x+tw+pad,y+bb[3]+pad),role='headline',size=size,stroke=stroke,box=True)
        return size

    def head(self, x, bottom, text, size, fill, stroke=15, name=None, font=BHS):
        """bottom 기준 배치(하단 잘림 방지). 실제 bbox 를 기록."""
        size=self.fit(text,size,W-x-MARGIN-10,font)
        f=ImageFont.truetype(font,size); bb=f.getbbox(text)
        gh=bb[3]-bb[1]; y=bottom-gh-bb[1]-stroke
        self._stext((x+7,y+8),text,f,(0,0,0,140),stroke,(0,0,0,140))
        self._stext((x,y),text,f,fill,stroke,(0,0,0,255))
        w=self.d.textlength(text,font=f)
        self._rec(name or text,(x-stroke,y+bb[1]-stroke,x+w+stroke+7,y+bb[3]+stroke+8),role='headline',size=size,stroke=stroke)
        return size

    def panel(self, hanja, reading, right=None, x=None, y=40, hs=100, rs=44, pad=22, name='hanja'):
        """한자판(한자 위·음 아래 2줄). right=True 면 우측 정렬로 폭 계산 후 배치."""
        fh=ImageFont.truetype(FB,hs); fr=ImageFont.truetype(FB,rs)
        hb=fh.getbbox(hanja); rb=fr.getbbox(reading)
        hw=self.d.textlength(hanja,font=fh); rw=self.d.textlength(reading,font=fr)
        hh=hb[3]-hb[1]; rh=rb[3]-rb[1]; gap=int(hh*0.26)
        w=max(hw,rw)+pad*2; h=hh+gap+rh+pad*2
        if x is None: x = W-w-44 if right else 44
        self.d.rounded_rectangle((x,y,x+w,y+h),radius=20,fill=(24,34,62,238))
        self.d.text((x+(w-hw)/2,y+pad-hb[1]),hanja,font=fh,fill=WHT)
        self.d.text((x+(w-rw)/2,y+pad+hh+gap-rb[1]),reading,font=fr,fill=YEL)
        self._rec(name,(x,y,x+w,y+h),role='panel')
        return w,h

    def card(self, hanja, reading, x, y, cs=330, hs=236, rs=54, name='card'):
        self.d.rounded_rectangle((x,y,x+cs,y+cs),radius=38,fill=(255,255,255,252))
        fh=ImageFont.truetype(FB,hs); hb=fh.getbbox(hanja)
        self.d.text((x+cs/2-self.d.textlength(hanja,font=fh)/2, y+cs/2-(hb[3]+hb[1])/2-20),hanja,font=fh,fill=NAVY)
        self.d.text((x+cs/2, y+cs-72),reading,font=ImageFont.truetype(FB,rs),fill=CYAN,anchor='ma')
        self._rec(name,(x,y,x+cs,y+cs),role='card')

    def doc(self, spec, name='doc'):
        """V2 실물(docs/34) — 통지표·학교 문자·신청서·간판을 **읽히는 글자**로 그린다. 장면 글자는 Flow 가 못 쓰니 여기서.
        spec: {style: paper|phone|sign, title, rows:[str|[k,v]], hl: 강조할 줄의 부분 문자열, x, y, w, rot}"""
        FM=f'{R}/remotion/public/fonts/NotoSansCJKkr-Medium.otf'
        st=spec.get('style','paper'); w=spec.get('w',500); rows=spec.get('rows',[]); hl=spec.get('hl','')
        ft=ImageFont.truetype(FB,spec.get('ts',40)); fr=ImageFont.truetype(FM,spec.get('rs',40)); fh=ImageFont.truetype(FB,spec.get('hs',56))
        pad=34; lh=[]
        for r in rows:
            s=' '.join(r) if isinstance(r,list) else r
            lh.append(fh.size+30 if hl and hl in s else fr.size+22)
        th=ft.size+40 if spec.get('title') else 0
        h=pad*2+th+sum(lh)+(40 if st=='phone' else 0)
        L=Image.new('RGBA',(w+40,h+40),(0,0,0,0)); d=ImageDraw.Draw(L)
        d.rounded_rectangle((14,18,w+14,h+18),radius=30,fill=(0,0,0,70))
        body={'paper':(253,250,240,255),'phone':(255,255,255,255),'sign':(255,236,214,255)}[st]
        d.rounded_rectangle((0,0,w,h),radius=30,fill=body,outline=(190,196,210,255),width=4)
        y=pad
        if spec.get('title'):
            band={'paper':(214,232,246,255),'phone':(236,240,246,255),'sign':(240,112,96,255)}[st]
            d.rounded_rectangle((pad-10,y-10,w-pad+10,y+ft.size+14),radius=14,fill=band)
            d.text((w/2,y-2),spec['title'],font=ft,fill=(255,255,255,255) if st=='sign' else NAVY,anchor='ma'); y+=th
        if st=='phone': y+=10
        for r,hh in zip(rows,lh):
            s=' '.join(r) if isinstance(r,list) else r
            if hl and hl in s:
                tw=d.textlength(s,font=fh); x0=(w-tw)/2 if st!='paper' else pad
                d.rounded_rectangle((x0-12,y-4,x0+tw+12,y+fh.size+14),radius=10,fill=(255,226,64,255))
                d.text((x0,y),s,font=fh,fill=(214,28,38,255))
            elif isinstance(r,list):
                d.text((pad,y),r[0],font=fr,fill=(40,46,60,255)); d.text((w-pad,y),r[1],font=fr,fill=(40,46,60,255),anchor='ra')
            else:
                d.text((w/2 if st!='paper' else pad,y),s,font=fr,fill=(90,96,110,255) if st=='phone' else (40,46,60,255),anchor='ma' if st!='paper' else 'la')
            y+=hh
        L=L.rotate(spec.get('rot',0),resample=Image.BICUBIC,expand=True)
        x=spec.get('x',W-L.width-40); y0=spec.get('y',40)
        self.im.alpha_composite(L,(int(x),int(y0))); self.d=ImageDraw.Draw(self.im)
        bb=L.getbbox(); self._rec(name,(x+bb[0],y0+bb[1],x+bb[2],y0+bb[3]),role='panel')

    def wordmark(self, size=210, margin=(24,18), corner=None):
        """워드마크. corner 없으면 배지(우하단 재생시간)와 다른 요소를 피하는 첫 모서리: tl → bl → tr → br.
        (thumb_review 2026-09-20: 우하단은 유튜브 재생시간 배지가 덮는다)"""
        w=Image.open(WM).convert('RGBA'); s=size/w.width; w=w.resize((size,int(w.height*s)))
        pos={'tl':(margin[0],margin[1]),'bl':(margin[0],H-w.height-margin[1]),'tr':(W-w.width-margin[0],margin[1]),'br':(W-w.width-margin[0],H-w.height-margin[1])}
        def free(c):
            x,y=pos[c]; B=(x,y,x+w.width,y+w.height)
            return all(B[2]<=e['bbox'][0] or e['bbox'][2]<=B[0] or B[3]<=e['bbox'][1] or e['bbox'][3]<=B[1] for e in self.els)
        if corner is None: corner=next((c for c in ('tl','bl','tr') if free(c)),'tl')
        x,y=pos[corner]
        # 흰 워드마크가 크림 배경에 묻힌다(오쌤 2026-09-25) → 남색 알약 판 위에
        pad=int(size*0.08); pill=Image.new('RGBA',self.im.size,(0,0,0,0))
        ImageDraw.Draw(pill).rounded_rectangle((x-pad,y-pad//2,x+w.width+pad,y+w.height+pad//2),radius=int(w.height*0.35),fill=(24,34,62,225))
        self.im.alpha_composite(pill)
        self.im.alpha_composite(w,(x,y)); self.d=ImageDraw.Draw(self.im)
        self._rec('wordmark',(x,y,x+w.width,y+w.height),role='brand',may_overlap=True,corner=corner)

    def save(self, path, quality=95, check=True):
        """저장 + meta.json + **즉시 검사**(visual_check thumb: 잘림·크기·겹침 / thumb_review: 모바일 가독·대비·배지·면적·글자수·대각).
        검사를 사람이 부르지 않아도 돌게 한다(오쌤 2026-09-20 「썸네일 리뷰시스템을 작동해야지」)."""
        self.im.convert('RGB').save(path,quality=quality)
        import os, subprocess, sys
        json.dump({'size':[W,H],'elements':self.els}, open(os.path.splitext(path)[0]+'.meta.json','w'), ensure_ascii=False, indent=1)
        if not check: return True
        ok=True
        for tool,args in (('visual_check.py',['thumb',path]),('thumb_review.py',[path])):
            r=subprocess.run([sys.executable,f'{R}/scripts/{tool}',*args],capture_output=True,text=True)
            tail=[l for l in r.stdout.splitlines() if l.strip()]
            print('   '+('\n   '.join(tail[-6:]) if tool=='thumb_review.py' else (tail[-1] if tail else '')))
            ok = ok and r.returncode==0
        print(f"   → {os.path.basename(path)} 썸네일 검사 {'PASS' if ok else 'FAIL'}")
        return ok
