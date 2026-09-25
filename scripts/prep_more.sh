#!/bin/zsh
ROOT=${ALLIRANG_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}; cd "$ROOT"
S=${FLOW_WORK:-$ROOT/scratch/flow_tools}
for e in "$@"; do
  npx wrangler r2 object put speed-listening-popsong/allirang/$e/video.mp4 --file remotion/out/${e}_deploy.mp4 --remote >/dev/null 2>&1
  npx wrangler r2 object put speed-listening-popsong/allirang/$e/short.mp4 --file scratch/flow_$e/${e}_short.mp4 --remote >/dev/null 2>&1
  npx wrangler r2 object put speed-listening-popsong/allirang/$e/thumb_a.png --file assets/longform/$e/thumb/final-a.png --remote >/dev/null 2>&1
  python3 scripts/ship_short.py $e --dry >/dev/null 2>&1
  python3 - $e <<'PY'
import sys,json
sys.path.insert(0,'scripts'); import youtube_upload as Y
e=sys.argv[1]; S=os.environ.get('FLOW_WORK', os.path.join(os.environ.get('ALLIRANG_ROOT', os.getcwd()),'scratch','flow_tools'))
L=json.load(open(f'{S}/yt_meta.json')); L=[x for x in L if x['ep']!=e]
m=Y.load_episode_meta(e); s=Y.load_part_meta(e,'hook_short')
L.append({'ep':e,'kind':'long','title':m['title'],'desc':m['description'],'tags':m.get('tags',[]),'url':f'https://media.brainhz.life/allirang/{e}/video.mp4','thumb':f'https://media.brainhz.life/allirang/{e}/thumb_a.png'})
L.append({'ep':e,'kind':'short','title':s['title'],'desc':s['description'],'tags':s.get('tags',[]),'url':f'https://media.brainhz.life/allirang/{e}/short.mp4','thumb':None})
json.dump(L,open(f'{S}/yt_meta.json','w'),ensure_ascii=False,indent=1)
PY
  (nohup python3 scripts/longform/drive_backup_clips.py $e > /tmp/drive_$e.log 2>&1 &)   # 드라이브 재사용 라이브러리 갱신(백그라운드)
  echo "$e prepped"
done
