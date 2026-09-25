// 편 전체 나레이션 굽기 — scratch_dir/lines.json 의 문장마다 Typecast → n01.wav … (44.1k WAV, DSP kid).
// 문장 앞 [[child]] / [[adult:sad]] 태그로 목소리·감정이 바뀐다(bakeTypecast 가 떼어 낸다). 보이스는 data/longform/<ep>.json tts.voices.
//   node scripts/bake_lines.mjs <id> [ep_json_name] [--only 3,7]   (id=scratch/flow_<id>, ep 기본 = id)
import { bakeTypecast } from '../bake.mjs';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
const ROOT = process.env.ALLIRANG_ROOT || new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const [id, epName] = process.argv.slice(2).filter(a=>!a.startsWith('--'));
const onlyArg=process.argv.find(a=>a.startsWith('--only=')); const only=onlyArg? new Set(onlyArg.slice(7).split(',').map(Number)) : null;
const sd=`${ROOT}/scratch/flow_${id}`;
const lines=JSON.parse(readFileSync(`${sd}/lines.json`,'utf8'));
const epP=[`${ROOT}/data/longform/${epName||id}.json`,`${ROOT}/data/scripts/${epName||id}.json`].find(p=>existsSync(p));
const ep=JSON.parse(readFileSync(epP,'utf8'));
const voices=ep.tts?.voices; if(!voices?.narrator){ console.error('tts.voices.narrator 없음'); process.exit(1); }
mkdirSync(sd,{recursive:true});
let total=0, n=0;
for(const l of lines){
  if(only && !only.has(l.g)) continue;
  const wav=`${sd}/n${String(l.g).padStart(2,'0')}.wav`;
  const buf=await bakeTypecast({ text:l.text, voices, preset:'kid' });
  writeFileSync(wav, buf);
  const d=+execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',wav]).toString();
  total+=d; n++; console.log(`n${String(l.g).padStart(2,'0')} ${d.toFixed(2)}s  ${l.text.slice(0,40)}`);
}
console.log(`\n${id}: ${n}문장 · 나레이션 합계 ${Math.floor(total/60)}:${String(Math.round(total%60)).padStart(2,'0')} (LEAD/GAP 제외)`);
