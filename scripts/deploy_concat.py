#!/usr/bin/env python3
"""배포본 = 인트로(assets/intro_msg.mp4) + 본편 + 엔딩(assets/ending_narr.mp4) PCM concat.
flow_assemble.py --deploy 가 이걸 부른다. 인트로·엔딩 에셋만 바뀌었을 때는 본편 재조립 없이 이것만:
  python3 scripts/deploy_concat.py <id>        # scratch_dir/<id>_body.mp4 → remotion/out/<id>_deploy.mp4
"""
import sys, os, json, subprocess
ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
def ff(*a): subprocess.run(['ffmpeg','-y','-loglevel','error',*a],check=True)
def dur(f): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]))

def concat(body, out):
    intro=f'{ROOT}/assets/intro_msg.mp4'; ending=f'{ROOT}/assets/ending_narr.mp4'
    ff('-i',intro,'-i',body,'-i',ending,'-filter_complex',
       "[0:v]scale=1920:1080,fps=30,setsar=1[v0];[0:a]aformat=sample_rates=48000:channel_layouts=mono[a0];"
       "[1:v]scale=1920:1080,fps=30,setsar=1[v1];[1:a]aformat=sample_rates=48000:channel_layouts=mono[a1];"
       "[2:v]scale=1920:1080,fps=30,setsar=1[v2];[2:a]aformat=sample_rates=48000:channel_layouts=mono[a2];"
       "[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]",
       '-map','[v]','-map','[a]','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','pcm_s16le','-movflags','+faststart',out)
    print('→ 배포본', out, f'{dur(out):.1f}s (본편 {dur(body):.1f}s + 인트로 {dur(intro):.1f}s + 엔딩 {dur(ending):.1f}s)')
    return out

if __name__=='__main__':
    vid=sys.argv[1]
    pp=f'{ROOT}/data/longform/prompts/{vid}.json'
    sd=(json.load(open(pp)).get('scratch_dir') if os.path.exists(pp) else None) or f'scratch/flow_{vid}'
    body=f'{ROOT}/{sd}/{vid}_body.mp4'
    if not os.path.exists(body): sys.exit(f'본편 없음: {body} — flow_assemble.py {vid} 먼저')
    concat(body, f'{ROOT}/remotion/out/{vid}_deploy.mp4')
