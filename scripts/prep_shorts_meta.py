import os
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..')))
import sys,json,subprocess
sys.path.insert(0,'scripts'); import youtube_upload as Y
S=os.environ.get('FLOW_WORK', os.path.join(R,'scratch','flow_tools'))
L=json.load(open(f'{S}/yt_meta.json'))
for e in sys.argv[1:]:
    p=json.load(open(f'data/longform/prompts/{e}.json')); sd=p.get('scratch_dir') or f'scratch/flow_{e}'
    subprocess.run(['npx','wrangler','r2','object','put',f'speed-listening-popsong/allirang/{e}/short.mp4','--file',f'{sd}/{e}_short.mp4','--remote'],capture_output=True)
    L=[x for x in L if not (x['ep']==e and x['kind']=='short')]
    s=Y.load_part_meta(e,'hook_short')
    L.append({'ep':e,'kind':'short','title':s['title'],'desc':s['description'],'tags':s.get('tags',[]),'url':f'https://media.brainhz.life/allirang/{e}/short.mp4','thumb':None})
    print(e,'short meta+R2 ok')
json.dump(L,open(f'{S}/yt_meta.json','w'),ensure_ascii=False,indent=1)
