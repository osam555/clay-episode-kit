import os
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
#!/usr/bin/env python3
"""Studio 업로드를 aside repl 로 — python3 aside_up.py <ep> <long|short> <allirang|daechung>"""
import json, re, sys, time
sys.path.insert(0, os.path.join(R,'scripts'))
import youtube_upload as Y
from browser import repl as _browser_repl
S = os.environ.get('FLOW_WORK', os.path.join(R,'scratch','flow_tools'))
import kitconfig
_CH_CFG = kitconfig.load(R)['channels']
CH = json.loads(os.environ.get('YT_CHANNELS', '{}'))   # {'<채널키>': ['<aside Studio 탭 id>', '<채널 ID UC…>', '<재생목록 이름>']}
if not CH:  # env 가 없으면 kit.config.json 의 channels 로 (studio_tab_hint·channel_id·playlist)
    CH = {k: [v.get('studio_tab_hint'), v.get('channel_id'), v.get('playlist')] for k, v in _CH_CFG.items()}
ep, kind, chn = sys.argv[1:4]
tab, cid, pl = CH[chn]
meta = [m for m in json.load(open(f'{S}/yt_meta.json')) if m['ep'] == ep and m['kind'] == kind][0]
d = json.load(open(f'{R}/data/longform/{ep}.json'))
if kind == 'short':
    pl = None
    lk = 'yt_daechung' if chn == 'daechung' else 'yt'
    lid = d.get(lk + '_v2') or d.get(lk)
    desc = re.sub(r'▶ 전체 영상: https://youtu.be/\S+\n?', '', meta['desc'])
    if lid: desc = desc.replace('\n\n', f'\n\n▶ 전체 영상: https://youtu.be/{lid}\n', 1)
    meta['desc'] = desc
A = f'''const M={json.dumps(meta, ensure_ascii=False)};const PL={json.dumps(pl, ensure_ascii=False)};
const pg=await attachBrowserTab("{tab}");
await pg.goto("https://studio.youtube.com/channel/{cid}/videos/upload?d=ud"); await sleep(4000);
const r=await fetch(M.url); const buf=Buffer.from(await r.arrayBuffer()); if(buf.length<1e6) throw new Error("small file "+buf.length);
await fs.writeFile("v.mp4",buf);
await pg.locator("input[type=file]").first().setInputFiles(await fs.resolvePath("v.mp4"));
for(let i=0;i<40;i++){{ if(await pg.evaluate(()=>!!document.querySelector("ytcp-social-suggestions-textbox#title-textarea #textbox"))) break; await sleep(1000);}}
await sleep(2500);
const setBox=async(sel,val)=>{{await pg.evaluate(([s,v])=>{{const e=document.querySelector(s);e.focus();document.execCommand("selectAll");document.execCommand("insertText",false,v);}},[sel,val]);}};
await setBox("ytcp-social-suggestions-textbox#title-textarea #textbox", M.title); await sleep(500);
await setBox("ytcp-social-suggestions-textbox#description-textarea #textbox", M.desc); await sleep(500);
if(M.thumb){{ const t=await fetch(M.thumb); await fs.writeFile("t.png",Buffer.from(await t.arrayBuffer())); await pg.locator("input#file-loader").first().setInputFiles(await fs.resolvePath("t.png")); await sleep(2500); }}
if(PL){{ await pg.evaluate(()=>{{const d=document.querySelector("ytcp-uploads-dialog"); const t=d.querySelector("ytcp-video-metadata-playlists ytcp-dropdown-trigger")||d.querySelector("ytcp-dropdown-trigger"); if(t) t.click();}}); await sleep(2000);
  const c=await pg.evaluate((n)=>{{const el=[...document.querySelectorAll("span, .checkbox-label, ytcp-checkbox-lit")].find(e=>e.innerText&&e.innerText.trim()===n&&e.offsetParent); if(!el) return "none"; const li=el.closest("li,ytcp-ve,label")||el; (li.querySelector("ytcp-checkbox-lit,#checkbox,[role=checkbox]")||li).click(); return "ok";}},PL); await sleep(800);
  await pg.evaluate(()=>{{const b=[...document.querySelectorAll("ytcp-button, button")].find(b=>b.innerText.trim()==="Done"&&b.offsetParent); if(b) b.click();}}); await sleep(1200); console.log("PL",c); }}
await pg.evaluate(()=>{{const b=[...document.querySelectorAll("ytcp-button#toggle-button, ytcp-button")].find(b=>/Show more/.test(b.innerText)&&b.offsetParent); if(b) b.click();}}); await sleep(1500);
await pg.getByRole("radio",{{name:"No, AI wasn’t used"}}).first().click().catch(e=>console.log("noAI",e.message));
const tg=pg.getByRole("textbox",{{name:"Tags"}}).first(); await tg.click().catch(()=>{{}}); await pg.keyboard.type(M.tags.slice(0,12).join(",")+","); await sleep(800);
let info=null; for(let i=0;i<25;i++){{ info=await pg.evaluate(()=>[document.querySelector("ytcp-social-suggestions-textbox#title-textarea #textbox")?.textContent, ((document.querySelector("ytcp-uploads-dialog")||document.body).innerText.match(/Video link\\s*(https?:\\/\\/(?:youtu\\.be\\/|youtube\\.com\\/shorts\\/)[\\w-]{{11}})/)||[null,null])[1]]); if(info[1]) break; await sleep(1500);}}
console.log("INFO", JSON.stringify(info));'''
B = f'''const pg=await attachBrowserTab("{tab}");
for(let i=0;i<3;i++){{ await pg.getByRole("button",{{name:"Next"}}).first().click(); await sleep(2000); }}
await pg.getByRole("radio",{{name:"Public"}}).first().click(); await sleep(1000);
const b=await pg.evaluate(()=>{{const x=[...document.querySelectorAll("ytcp-button#done-button, ytcp-button")].find(b=>/^(Publish|Save)$/.test(b.innerText.trim())&&b.offsetParent); if(x){{x.click();return x.innerText.trim()}} return "none"}});
await sleep(5000);
const st=await pg.evaluate(()=>document.body.innerText.match(/Video (published|processing)|Checking|Processing[^\\n]*/g));
console.log("PUB",b,JSON.stringify(st));
await pg.evaluate(()=>{{const x=[...document.querySelectorAll("ytcp-button, button")].find(b=>b.innerText.trim()==="Close"&&b.offsetParent); if(x) x.click();}});'''
def run(js):
    return _browser_repl(js, timeout=170)
if os.environ.get('VID'):
    oa='youtu.be/'+os.environ['VID']
else:
    oa = run(A); print(oa[-2500:])
m = re.search(r'(?:youtu\.be/|shorts/)([\w-]{11})', oa)
if not m or 'error' in oa.lower().split('info')[0][-200:]:
    sys.exit('A 실패')
vid = m.group(1)
ob = run(B); print(ob[-400:])
if 'PUB Publish' not in ob and 'PUB Save' not in ob: sys.exit('B 실패 ' + vid)
Y.record_id(ep, chn, vid, part=('hook_short' if kind == 'short' else None))
print('DONE', ep, kind, chn, vid)
