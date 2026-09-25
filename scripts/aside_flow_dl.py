"""aside 로 Flow 프로젝트의 타일 전부 다운로드 — python3 aside_flow_dl.py <project_url> <outdir>  (영상 720p, 이미지 1K; ~/Downloads 에 떨어진 뒤 outdir 로 옮김)"""
import os
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..')))
import subprocess, sys, json, os, glob, time, shutil
url, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
import os
TAB = os.environ.get("FLOW_TAB","")
LIST = f'''const pg=await attachBrowserTab("{TAB}"); await pg.goto("{url}"); await sleep(6000);
const t=await pg.evaluate(()=>[...new Set([...document.querySelectorAll('*')].filter(e=>e.children.length==0&&/^[A-Z0-9][a-z0-9A-Z]* /.test(e.textContent.trim())&&e.textContent.trim().length<60).map(e=>e.textContent.trim()))].filter(t=>!/^(All media|Start|Google|Videos|Images|Characters|Scenes|Tools|Trash|Collapse|What|Agent|Video|Tile|More|New|Sep|Prompt|Learn|No thanks|Skip|Add|View)/.test(t)));
console.log("TITLES"+JSON.stringify(t));'''
def repl(js):
    p = subprocess.run(['aside', 'repl', js], capture_output=True, text=True, timeout=300); return p.stdout + p.stderr
r = repl(LIST); titles = json.loads(r.split('TITLES')[1].split('\n')[0])
print(len(titles), 'tiles')
DL = '''const pg=await attachBrowserTab("%s"); const T=%s; const out=[];
for (const title of T) {
  await pg.goto("%s"); await sleep(5000);
  const dlp=pg.waitForEvent('download',{timeout:60000}).catch(()=>null);
  const r=await pg.evaluate(async(title)=>{const sl=ms=>new Promise(r=>setTimeout(r,ms));let el=[...document.querySelectorAll('*')].find(e=>e.children.length==0&&e.textContent.trim().startsWith(title));if(!el)return 'notile';let c=el;for(let i=0;i<6&&c;i++){if(c.tagName=='A'||c.tagName=='BUTTON'||c.onclick)break;c=c.parentElement}(c||el).click();await sl(1500);let d;for(let k=0;k<12&&!d;k++){d=[...document.querySelectorAll('button')].find(b=>/download/i.test(b.textContent+(b.getAttribute('aria-label')||'')));if(!d)await sl(1000)}if(!d)return 'nodl';d.click();await sl(1200);let m=[...document.querySelectorAll('[role=menuitem],button,li')].find(b=>b.textContent.includes('720p'))||[...document.querySelectorAll('[role=menuitem],button,li')].find(b=>b.textContent.includes('1K'));if(!m)return 'nomenu';m.click();return 'ok'},title);
  const dl=await dlp; out.push([title, r, dl?await dl.path():null]);
}
console.log("OUT"+JSON.stringify(out));'''
res = []
for i in range(0, len(titles), 4):
    chunk = [t.rstrip('…') for t in titles[i:i+4]]
    r = repl(DL % (TAB, json.dumps(chunk, ensure_ascii=False), url))
    try: res += json.loads(r.split('OUT')[1].split('\n')[0])
    except Exception: print('ERR', r[-400:])
for title, st, p in res:
    if p and os.path.exists(p):
        dst = os.path.join(out, os.path.basename(p)); shutil.move(p, dst); print('OK', title, '->', os.path.basename(dst))
    else: print('FAIL', title, st)
