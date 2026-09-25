"""aside 로 Flow 새 프로젝트 만들고 프롬프트 전부 제출 — python3 aside_flow_submit.py <ep> [--thumbs]
   기본: data/longform/prompts/<ep>.json new_prompts 를 영상 모드로 제출. --thumbs: thumb a/b/c 를 이미지 모드로 제출(끝나면 영상 모드로 되돌림).
   프로젝트 URL 을 scratchpad/flow_projects.txt 에 기록하고 stdout 에 URL 출력."""
import os
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from browser import repl as _browser_repl
S=os.environ.get('FLOW_WORK', os.path.join(R,'scratch','flow_tools'))
import os
TAB=os.environ.get("FLOW_TAB","")
ep=sys.argv[1]; thumbs='--thumbs' in sys.argv
p=json.load(open(f'{R}/data/longform/prompts/{ep}.json'))
P=[p['thumb'][x]['flow'] for x in 'abc'] if thumbs else list(p['new_prompts'].values())
def repl(js):
    return _browser_repl(js, timeout=600)
MODE_JS = '''await pg.evaluate(()=>{const m=[...document.querySelectorAll('button')].find(b=>/Video \\u00b7|Nano Banana/.test(b.textContent)); m.click();}); await sleep(1500);
await pg.evaluate((w)=>{const r=[...document.querySelectorAll('[role=radio]')].find(e=>new RegExp(w).test(e.textContent)); r&&r.click();}, %s); await sleep(1500); await pg.keyboard.press('Escape'); await sleep(800);'''
NEW = f'''const pg=await attachBrowserTab("{TAB}"); await pg.goto("https://flow.google.com/"); await sleep(5000);
await pg.evaluate(()=>{{const b=[...document.querySelectorAll('button')].find(b=>/New project/.test(b.textContent)); b.click();}}); await sleep(4000); for(let k=0;k<20&&!/\/project\//.test(pg.url());k++) await sleep(1000); await sleep(3000);
const url=pg.url(); {MODE_JS % ('"Image"' if thumbs else '"Video"')}
const mode=await pg.evaluate(()=>[...document.querySelectorAll('button')].map(b=>b.textContent.trim()).find(t=>/Video \\u00b7|Nano/.test(t)));
console.log("URL "+url+" MODE "+mode);'''
out=repl(NEW); line=[l for l in out.splitlines() if l.startswith('URL ')]
if not line: sys.exit('project create failed: '+out[-500:])
url=line[0].split()[1]; print(line[0])
SUB = '''const pg=await attachBrowserTab("%s"); const T=%s; const res=[];
for (const t of T) {
  await pg.evaluate((t)=>{const e=document.querySelector('.ProseMirror');e.focus();document.execCommand('selectAll');document.execCommand('delete');document.execCommand('insertText',false,t);},t); await sleep(1200);
  await pg.locator('button[aria-label="Start generation"], button:has-text("arrow_forward")').first().click().catch(()=>{});
  await sleep(2500);
  let left=await pg.evaluate(()=>document.querySelector('.ProseMirror').textContent.length);
  if(left>0){ await pg.locator('button[aria-label="Start generation"], button:has-text("arrow_forward")').first().click().catch(()=>{}); await sleep(2500); left=await pg.evaluate(()=>document.querySelector('.ProseMirror').textContent.length); }
  res.push(left); await sleep(5000);
}
console.log("RES "+JSON.stringify(res));'''
for i in range(0,len(P),4):
    out=repl(SUB % (TAB, json.dumps(P[i:i+4],ensure_ascii=False))); print([l for l in out.splitlines() if l.startswith('RES ')] or out[-300:])
if thumbs:
    out=repl(f'const pg=await attachBrowserTab("{TAB}"); '+(MODE_JS % '"Video"')+' const mode=await pg.evaluate(()=>[...document.querySelectorAll("button")].map(b=>b.textContent.trim()).find(t=>/Video \\u00b7|Nano/.test(t))); console.log("MODE "+mode);')
    print([l for l in out.splitlines() if l.startswith('MODE ')])
open(f'{S}/flow_projects.txt','a').write(f'{ep}{"_thumbs" if thumbs else ""} {url}\n')
