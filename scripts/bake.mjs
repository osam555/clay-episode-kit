/**
 * 카드 이야기 → 소리 굽기 (3단계).
 *   node scripts/bake.mjs --card jeomsim --voice ko-KR-JiMinNeural --preset kid --speeds 1,2,3
 *
 * DSP 는 **brainhz-dsp V4.0**(네 앱 공용 단일 출처)을 번들해 쓴다 — 복사하지 않는다(CLAUDE.md).
 * 번들은 scratch/dsp/brainhzDsp.mjs 에 생기며 매번 다시 만든다. 원본이 바뀌면 자동으로 따라온다.
 *
 * 배속: Azure prosody 는 2.0x 까지만 안정 → 2.0x 로 합성한 뒤 DSP 의 finalSpeed(WSOLA, 피치 보존)로 늘린다.
 * 쉼: 문장 사이 <break> 를 목표 배속만큼 늘려 넣는다 — WSOLA 로 압축되면 어느 배속에서나 같은 길이로 착지한다.
 */
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { synth } from './tts.mjs'

// ── TTS 발음 규칙 정본 사전 (scripts/pronunciation.json) ──
// 화면 자막·타임라인은 원문, 소리(synth)만 실제 발음으로 치환한다. 문장부호는 안 바꾸므로 문장 수(자막 짝)는 그대로.
const PRON = JSON.parse(readFileSync(new URL('./longform/pronunciation.json', import.meta.url)))
function applyPron(text) {
  let t = text
  for (const r of PRON.rules) {
    if (r.kind === 'tense') {
      // 표준 발음법 24항 — 어간(받침 ㄴ·ㅁ) + 어미 첫소리 ㄱㄷㅅㅈ 된소리. 어간 뒤에 바로 어미가 올 때만(공백·조사 없이).
      for (const stem of r.stems) {
        const base = (r.fold && r.fold[stem]) || stem
        for (const [e, te] of Object.entries(r.endings)) {
          if (r.exclude && r.exclude[stem] && r.exclude[stem].includes(e)) continue
          t = t.replace(new RegExp(stem + e, 'g'), base + te)
        }
      }
      continue
    }
    if (r.regex) t = t.replace(new RegExp(r.regex, 'g'), r.to)
    else t = t.split(r.from).join(r.to)
  }
  return t
}

// esbuild 는 C12 것을 먼저 쓰고, 없으면 이 저장소의 devDependency 를 쓴다 —
// 클라우드 세션은 allirang 폴더만 보여서 C12 경로가 안 잡힌다(2026-09-14). ESBUILD 로 덮어쓸 수도 있다.
const ESBUILD = process.env.ESBUILD
  || [new URL('../node_modules/.bin/esbuild', import.meta.url).pathname,
      new URL('../node_modules/@esbuild/win32-x64/esbuild.exe', import.meta.url).pathname].find((p) => existsSync(p))
  || 'esbuild'
// 정본은 이제 brainhz-dsp 다. 옛 speed-bible/lib/brainhzDsp.ts 는 그 앱이 옮겨 갈 때까지만 남는다.
// 정본 DSP 원본. 절대 경로를 먼저 보고, 없으면 **형제 폴더**로 찾는다 —
// 클라우드 세션의 마운트에서는 /Users/... 가 아니라 ../brainhz-dsp 다. 두 곳 다 형제 배치라 같은 상대 경로가 맞는다.
// brainhz-dsp 는 별도 정본 저장소다(이 kit 에는 번들되어 있지 않다) — DSP_SRC 로 경로를 주거나
// 이 kit 저장소와 형제 폴더에 brainhz-dsp 를 clone 해 둔다.
const DSP_SRC = process.env.DSP_SRC
  || new URL('../../brainhz-dsp/src/brainhzDsp.ts', import.meta.url).pathname
const DSP_OUT = new URL('../scratch/dsp/brainhzDsp.mjs', import.meta.url)

/** 강도 프리셋. 초등은 어른과 다르다 — 14-19kHz 를 다 듣기 때문에 같은 값이 훨씬 세게 들린다. */
/* ⚠️ 진단용 프리셋(kidAudit·kidAudit12·kidAudit18·kidAuditGated)이 여기 있었다.
   12·13kHz 를 더해 오쌤이 톤을 들을 수 있게 한 것들인데, V4.0 에서 그 층 자체가 사라져
   뜻이 없어졌다. 무엇을 듣고 무엇을 정했는지는 docs/05-sound.md 2-1·2-2절에 남아 있다. */

export const PRESETS = {
  /** 속청성경 성인 기본값 (비교용) */
  adult: { intensity: 100, clarity: 100, consonant: true, gating: false, laterality: false },
  /** 초등 기본 — 토마티스를 적극 반영한다(게이팅 켬). 강도만 아이 귀에 맞춰 낮춘다. 근거 docs/05-sound.md
   *
   *  **brain 0 — 14-19kHz 층을 뺐다** (오쌤, 2026-09-11).
   *  그 층은 Brain HZ 최초 정의에 없던 것이다. 정의는 세 값(문턱 0.01 · 어택 10ms · Bessel Q=0.5)과
   *  「Tomatis Effect(Dynamic Gating)」뿐이고, 없던 사인파를 더한다는 말은 어디에도 없었다.
   *  이력: BrainHZ/docs/9-14-BRAINHZ-14-19K-FORENSICS.md
   *
   *  빼도 잃는 것이 없다 — 게이팅·자음 강조·clarity 가 남고 그게 원래 팔던 것이다.
   *  다이얼은 남겨 둔다(0 이 아닌 값을 주면 도로 켜진다). 지우지 않는 이유는 되돌릴 길을 막지 않으려고. */
  kid: { intensity: 45, clarity: 50, consonant: true, gating: true, laterality: false },
  /** 초등 + 우이 편측 — 이어폰 전제(스테레오 출력). 토마티스 우이 우세 */
  kidPlus: { intensity: 45, clarity: 50, consonant: true, gating: true, laterality: true },
  /** 초등 약하게 — 소리가 거슬린다는 아이용. 게이팅은 그대로 켠다 */
  kidSoft: { intensity: 30, clarity: 40, consonant: true, gating: true, laterality: false },
  /** 게이팅만 끈 것 — 말이 뭉개지는지 견주기용 */
  kidNoGating: { intensity: 45, clarity: 50, consonant: true, gating: false, laterality: false },
  /** ⚠️ **진단용이다. 제품 음원에 쓰지 않는다.**
   *  오쌤 가청 상한이 13kHz 라 14-19k 여섯 톤이 한 톤도 안 들린다.
   *  12·13k 를 **더해서** 톤의 성격(말과 무관한 상수 순음, 쉼에서 홀로 남는 것)을 귀로 확인한다.
   *  ⚠️ 여기서 듣는 크기는 아이가 14-19k 에서 듣는 크기와 다르다 — 성격만 판단할 수 있다.
   *  ⚠️ speed-bible/lib/dsp/personalize.ts 에 적힌 대로, 톤을 가청대로 **옮기는** 것은
   *     제품에서 이미 한 번 해 보고 거둔 길이다(말과 무관한 삐소리가 된다). 이건 옮기는 게 아니라 더하는 것이고,
   *     듣고 판단하려는 목적에만 쓴다. */
  /** ⚠️ **진단용 세기 사다리.** 12·13kHz 를 더해 오쌤이 들을 수 있게 한 것 — 제품에 쓰지 않는다.
   *  brain 40 = 예전 세기 · 20 = -6dB(「마」) · 10 = -12dB · 5 = -18dB.
   *  `kidAuditGated` 는 말 게이팅을 켠 것(「라」) — 더 거슬린다는 확인이 났지만 기록으로 남긴다. */
  /** DSP 없음 (맨소리) */
  none: null,
}

/**
 * ⚠️ 브레인 톤을 우리가 얹던 코드가 여기 있었다. **V4.0 에서 그 층 자체를 뺐다**(2026-09-11).
 * 왜 뺐는지는 brainhz-dsp/README.md 와 docs/05-sound.md 2-0절.
 * 말 게이팅 실험(쉼에서 톤을 닫기)도 함께 사라졌다 — 오쌤이 「거슬린다」고 했고,
 * 답은 껐다 켜는 것이 아니라 그 층을 빼는 것이었다.
 */

export function bundleDsp() {
  mkdirSync(new URL('.', DSP_OUT), { recursive: true })
  execFileSync(ESBUILD, [DSP_SRC, '--bundle', '--format=esm', '--platform=node', `--outfile=${DSP_OUT.pathname}`, '--log-level=error'])
  return import(DSP_OUT.href + `?t=${Date.now()}`)
}

/**
 * 문장 끝마다 쉼을 넣는다. **쉼은 배속과 무관하게 항상 pauseMs 로 들려야 한다**
 * (포털 koreanSpeed.ts 의 결정 — 재생속도로 때우면 쉼이 같이 줄어 절벽이 된다).
 *
 * Azure 의 <break time> 은 **절대 시간**이라 prosody rate 에 안 줄어든다.
 *  - 2.0배까지(합성만): 그대로 pauseMs 를 넣는다. 늘리면 배속을 올려도 쉼만 길어진다.
 *  - 2.05배 위(합성 2.0배 + WSOLA 로 finalSpeed/2.0 배 압축): 압축될 만큼 미리 늘려 넣는다.
 */
function withBreaks(text, pauseMs, speed) {
  const shrink = speed > 2.05 ? speed / 2.0 : 1      // WSOLA 가 나중에 이만큼 줄인다
  const ms = Math.round(pauseMs * shrink)
  return text.replace(/([.!?])\s+/g, `$1<break time="${ms}ms"/>`)
}

/** WAV 바이트에서 data 청크만 꺼낸다 — Azure 가 여분 청크를 넣어도 안전하게. */
export function parseWav(buf) {
  if (buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WAVE')
    throw new Error('WAV 가 아니다')
  let off = 12, sampleRate = 48000, channels = 1, bits = 16, data = null
  while (off + 8 <= buf.length) {
    const id = buf.toString('ascii', off, off + 4)
    const size = buf.readUInt32LE(off + 4)
    const body = off + 8
    if (id === 'fmt ') {
      channels = buf.readUInt16LE(body + 2)
      sampleRate = buf.readUInt32LE(body + 4)
      bits = buf.readUInt16LE(body + 14)
    } else if (id === 'data') {
      data = buf.subarray(body, body + size)
      break
    }
    off = body + size + (size % 2)
  }
  if (!data) throw new Error('data 청크를 못 찾았다')
  if (bits !== 16 || channels !== 1) throw new Error(`16bit mono 가 아니다 (${bits}bit ${channels}ch)`)
  return { data, sampleRate }
}

/**
 * 문장 시작 시각을 찾는다 — **DSP 전 원본 TTS**에서. SSML <break> 는 진짜 무음이라 또렷이 잡힌다.
 * (DSP 뒤에는 브레인 톤이 계속 울려 무음 구간이 없어진다.)
 * 돌려주는 것: 문장마다 [시작초, 끝초].
 */
function findCues(pcm, sampleRate, sentenceCount, minGapMs = 200) {
  const n = pcm.length >> 1
  const win = Math.round(sampleRate * 0.01)          // 10ms
  const frames = Math.floor(n / win)
  const peak = new Float32Array(frames)
  const dv = new DataView(pcm.buffer, pcm.byteOffset, n * 2)
  for (let f = 0; f < frames; f++) {
    let m = 0
    for (let i = 0; i < win; i++) {
      const v = Math.abs(dv.getInt16((f * win + i) * 2, true)) / 32768
      if (v > m) m = v
    }
    peak[f] = m
  }
  let max = 0
  for (const v of peak) if (v > max) max = v
  const thr = max * 0.02
  const gaps = []
  let run = 0
  for (let f = 0; f < frames; f++) {
    if (peak[f] < thr) run++
    else { if (run * 10 >= minGapMs) gaps.push([(f - run) * 0.01, f * 0.01]); run = 0 }
  }
  const dur = n / sampleRate
  // 맨 앞·뒤 무음은 버리고, 가운데 것만 문장 경계로 쓴다
  const inner = gaps.filter(([a, b]) => a > 0.15 && b < dur - 0.15)
  // 문장 수보다 많으면 긴 것부터 남긴다
  inner.sort((x, y) => (y[1] - y[0]) - (x[1] - x[0]))
  const keep = inner.slice(0, Math.max(0, sentenceCount - 1)).sort((x, y) => x[0] - y[0])
  const cues = []
  let from = gaps.length && gaps[0][0] < 0.15 ? gaps[0][1] : 0
  for (const [a, b] of keep) { cues.push([+from.toFixed(2), +a.toFixed(2)]); from = b }
  cues.push([+from.toFixed(2), +dur.toFixed(2)])
  return cues
}

/** 이야기를 문장으로 쪼갠다 — 자막 한 줄 단위. withBreaks 와 같은 기준이라야 짝이 맞는다. */
export function splitSentences(text) {
  return text.split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean)
}

// ── Typecast 제공자 (오쌤 2026-09-20 「타입캐스트 사용 · 최고 음질 · 이야기에 맞는 여러 목소리」) ──────────────
//  · 문장마다 따로 합성한다(Typecast 는 SSML break 가 없다) → 쉼은 우리가 무음으로 붙인다 → 큐는 붙인 자리에서 정확히 나온다.
//  · 배속: audio_tempo 로 2.0x 까지(피치 유지), 그 위는 Azure 와 같이 2.0x + WSOLA(finalSpeed). 쉼 길이는 배속과 무관.
//  · 최고 음질 = ssfm-v30 · WAV 44.1kHz 16bit mono (sample_rate 48000 요청은 무시된다 — 2026-09-20 실측).
//  · 문장 앞 태그 `[[child]]` / `[[adult:happy]]` 로 목소리·감정을 바꾼다. 자막·타임라인엔 태그를 뺀 문장을 준다.
//  · 키는 .env.local 의 TYPECAST_API_KEY 만. 로그·에러에 키를 절대 싣지 않는다.
import { readFileSync as _rfs } from 'node:fs'
const TC_KEY = (() => {
  try { const m = _rfs(new URL('../.env.local', import.meta.url), 'utf8').match(/TYPECAST_API_KEY=([^\n\r]+)/); if (m) return m[1].trim() } catch {}
  return process.env.TYPECAST_API_KEY
})()
const TC_TAG = /^\s*\[\[([A-Za-z_]+)(?::([a-z]+))?\]\]\s*/
export const TC_EMOTIONS = ['normal', 'happy', 'sad', 'angry', 'whisper', 'toneup', 'tonedown']
/** 문장에서 `[[voice:emotion]]` 태그를 떼어 {key, emotion, text} 로. 태그가 없으면 narrator/normal. */
export function parseVoiceTag(sentence, fallbackKey = 'narrator') {
  const m = sentence.match(TC_TAG)
  if (!m) return { key: fallbackKey, emotion: 'normal', text: sentence.trim() }
  return { key: m[1], emotion: TC_EMOTIONS.includes(m[2]) ? m[2] : 'normal', text: sentence.slice(m[0].length).trim() }
}
export function stripVoiceTags(text) { return splitSentences(text).map((s) => parseVoiceTag(s).text).join(' ') }
async function synthTypecast({ text, voiceId, model = 'ssfm-v30', emotion = 'normal', tempo = 1 }) {
  if (!TC_KEY) throw new Error('TYPECAST_API_KEY 가 .env.local 에 없다')
  const r = await fetch('https://api.typecast.ai/v1/text-to-speech', {
    method: 'POST', headers: { 'X-API-KEY': TC_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice_id: voiceId, text, model, language: 'kor',
      prompt: { emotion_preset: emotion, emotion_intensity: 1 },
      output: { volume: 100, audio_pitch: 0, audio_tempo: tempo, audio_format: 'wav' } }),
  })
  if (r.status !== 200) throw new Error(`Typecast ${r.status}: ${(await r.text()).slice(0, 200)}`)
  return Buffer.from(await r.arrayBuffer())
}
function wavHeader(dataBytes, sampleRate, channels = 1, bits = 16) {
  const h = Buffer.alloc(44); const ba = channels * bits / 8
  h.write('RIFF', 0); h.writeUInt32LE(36 + dataBytes, 4); h.write('WAVE', 8); h.write('fmt ', 12)
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(channels, 22); h.writeUInt32LE(sampleRate, 24)
  h.writeUInt32LE(sampleRate * ba, 28); h.writeUInt16LE(ba, 32); h.writeUInt16LE(bits, 34); h.write('data', 36); h.writeUInt32LE(dataBytes, 40)
  return h
}
/**
 * Typecast 로 굽는다. bake() 와 같은 반환({cues, sentences} 붙은 WAV Buffer) — dsp_bake.mjs 가 그대로 쓴다.
 *   voices: { narrator: 'tc_…', child: 'tc_…', adult: 'tc_…' }  (키는 태그 이름과 같다)
 */
export async function bakeTypecast({ text, voices, speed = 1, preset = 'kid', pauseMs = 350, model = 'ssfm-v30' }) {
  if (!voices || !voices.narrator) throw new Error('voices.narrator 가 필요하다')
  const p = PRESETS[preset]
  const tempo = Math.min(speed, 2.0)
  const finalSpeed = speed > 2.05 ? speed : undefined
  if (finalSpeed && finalSpeed > 5.2) throw new Error(`배속 ${speed} 는 DSP finalSpeed 상한(5.2) 밖이다`)
  const gapMs = Math.round(pauseMs * (finalSpeed ? speed / 2.0 : 1))   // withBreaks 와 같은 셈: WSOLA 가 줄일 만큼 미리 늘린다
  const raws = splitSentences(text)
  const sentences = [], parts = []
  let sampleRate = 0
  for (const raw of raws) {
    const { key, emotion, text: plain } = parseVoiceTag(raw)
    const voiceId = voices[key] || voices.narrator
    const wav = await synthTypecast({ text: applyPron(plain), voiceId, model, emotion, tempo })
    const w = parseWav(wav)   // Typecast: 16bit mono (2026-09-20 실측). parseWav 는 sampleRate·data 만 준다
    if (!sampleRate) sampleRate = w.sampleRate
    if (w.sampleRate !== sampleRate) throw new Error(`샘플레이트가 문장마다 다르다 ${w.sampleRate} vs ${sampleRate}`)
    sentences.push(plain); parts.push(w.data)
  }
  // 문장 + 쉼 이어 붙이기, 큐는 붙인 자리 그대로(무음 검출 불필요)
  const gap = Buffer.alloc(Math.round(sampleRate * gapMs / 1000) * 2)
  const chunks = [], cues = []; let pos = 0
  parts.forEach((d, i) => {
    const a = pos / (sampleRate * 2); chunks.push(d); pos += d.length
    cues.push([+a.toFixed(2), +(pos / (sampleRate * 2)).toFixed(2)])
    if (i < parts.length - 1) { chunks.push(gap); pos += gap.length }
  })
  const pcm = Buffer.concat(chunks)
  const wav = Buffer.concat([wavHeader(pcm.length, sampleRate), pcm])
  let scaled = cues
  if (p && finalSpeed) { const k = 2.0 / finalSpeed; scaled = cues.map(([a, b]) => [+(a * k).toFixed(2), +(b * k).toFixed(2)]) }
  if (!p) return Object.assign(wav, { cues: scaled, sentences })
  const { processServerDsp, pcm16ToFloat32, float32ChannelsToWav } = await bundleDsp()
  const mono = pcm16ToFloat32(new Uint8Array(pcm.buffer, pcm.byteOffset, pcm.byteLength))
  const channels = processServerDsp(mono, sampleRate, {
    intensity: p.intensity, language: 'ko', gating: !!p.gating, koreanGating: !!p.gating, laterality: !!p.laterality,
    gamma: null, consonant: p.consonant, clarity: p.clarity, ...(finalSpeed ? { finalSpeed } : {}),
  })
  const out = Buffer.from(float32ChannelsToWav(channels, sampleRate))
  return Object.assign(out, { cues: scaled, sentences })
}

export async function bake({ text, voice, speed = 1, preset = 'kid', pauseMs = 350 }) {
  const p = PRESETS[preset]
  // 2.0x 까지는 합성으로, 그 위는 2.0x 합성 + WSOLA
  const synthSpeed = Math.min(speed, 2.0)
  const finalSpeed = speed > 2.05 ? speed : undefined
  // ⚠ 위쪽 DSP 는 범위 밖 finalSpeed 를 **조용히 무시한다** — 신축 없이 2배 길이가 나온다(5배라 이름 붙은 2배 파일).
  //   그래서 여기서 막는다. 상한은 brainhzDsp.ts 의 cActive 조건과 같아야 한다.
  if (finalSpeed && finalSpeed > 5.2) throw new Error(`배속 ${speed} 는 DSP finalSpeed 상한(5.2) 밖이다`)
  const wav = await synth({ text: withBreaks(applyPron(text), pauseMs, speed), voice, speed: synthSpeed, ssml: true })
  const raw = parseWav(wav)
  const sentences = splitSentences(text)
  let cues = findCues(raw.data, raw.sampleRate, sentences.length)
  if (p) {
    // WSOLA 로 늘릴 것이면 시각도 같은 비율로 줄여 준다
    const k = finalSpeed ? 2.0 / finalSpeed : 1
    if (k !== 1) cues = cues.map(([a, b]) => [+(a * k).toFixed(2), +(b * k).toFixed(2)])
  }
  if (!p) return Object.assign(wav, { cues, sentences })

  const { processServerDsp, pcm16ToFloat32, float32ChannelsToWav } = await bundleDsp()
  const { data, sampleRate } = parseWav(wav)
  const mono = pcm16ToFloat32(new Uint8Array(data.buffer, data.byteOffset, data.byteLength))
  const channels = processServerDsp(mono, sampleRate, {
    intensity: p.intensity,
    language: 'ko',
    gating: !!p.gating,
    koreanGating: !!p.gating,
    laterality: !!p.laterality,
    gamma: null,
    consonant: p.consonant,
    clarity: p.clarity,
    ...(finalSpeed ? { finalSpeed } : {}),
  })
  const out = Buffer.from(float32ChannelsToWav(channels, sampleRate))
  return Object.assign(out, { cues, sentences })
}

/** 이미 합성된 WAV(48k 16bit mono)에 DSP 만 건다 — 쇼츠(scripts/shorts)가 문장 단위로 쓴다. 배속 신축 없음. */
export async function applyDsp(wav, { preset = 'kid', language = 'ko' } = {}) {
  const p = PRESETS[preset]
  if (!p) throw new Error(`프리셋 없음: ${preset}`)
  const { processServerDsp, pcm16ToFloat32, float32ChannelsToWav } = await bundleDsp()
  const { data, sampleRate } = parseWav(wav)
  const mono = pcm16ToFloat32(new Uint8Array(data.buffer, data.byteOffset, data.byteLength))
  const channels = processServerDsp(mono, sampleRate, {
    intensity: p.intensity, language, gating: !!p.gating, koreanGating: !!p.gating,
    laterality: !!p.laterality, gamma: null, consonant: p.consonant, clarity: p.clarity,
  })
  return Buffer.from(float32ChannelsToWav(channels, sampleRate))
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const a = Object.fromEntries(process.argv.slice(2).reduce((m, x, i, arr) => (x.startsWith('--') ? [...m, [x.slice(2), arr[i + 1]]] : m), []))
  const cards = JSON.parse(readFileSync(new URL('../data/cards.json', import.meta.url), 'utf8'))
  const card = cards.find((c) => c.id === a.card)
  if (!card) throw new Error(`카드 없음: ${a.card}`)
  const dir = a.dir || 'scratch/samples'
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
  for (const s of (a.speeds || '1').split(',').map(Number)) {
    const buf = await bake({ text: card.story, voice: a.voice, speed: s, preset: a.preset || 'kid' })
    const f = `${dir}/${a.card}-${a.preset || 'kid'}-${s}x.wav`
    writeFileSync(f, buf)
    console.log(`${f}  ${((buf.length - 44) / 96000).toFixed(1)}초`)
  }
}
