/**
 * Azure TTS 호출 — 목소리·배속 샘플 만들기. 3단계(소리)의 도구.
 *   node scripts/tts.mjs --voice ko-KR-JiMinNeural --speed 1 --text "..." --out scratch/samples/a.wav
 *   node scripts/tts.mjs --voice ... --card jeomsim --out ...
 * 키는 .env.local (git 제외). **48kHz 16bit mono WAV** 로 받는다 — Azure 가 내주는 최대 비트깊이가 16bit 다(24bit 선택지가 없다).
 *   48kHz 가 필요한 이유는 DSP 의 자음 강조 대역이 8-12kHz 라서다. 44.1kHz(나이키스트 22.05k)로도 담기지만
 *   형제 앱들과 파이프라인을 한 갈래로 두려고 48k 로 통일한다.
 *   (2026-09-11 고침: 예전엔 「DSP 가 14-19kHz 를 쓰므로」라고 적혀 있었다. 그 층은 V4.0 에서 빠졌다.)
 */
import { readFileSync, writeFileSync } from 'node:fs'

const env = Object.fromEntries(
  readFileSync(new URL('../.env.local', import.meta.url), 'utf8')
    .split('\n')
    .map((l) => l.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$/))
    .filter(Boolean)
    .map((m) => [m[1], m[2].trim()])
)
const KEY = env.AZURE_SPEECH_KEY
const REGION = env.AZURE_SPEECH_REGION || 'koreacentral'

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, arr) => (a.startsWith('--') ? [...acc, [a.slice(2), arr[i + 1]]] : acc), [])
)

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export async function synth({ text, voice, speed = 1, pitch = null, ssml = false, lang = 'ko-KR' }) {
  // Azure prosody rate 는 2.0 까지 안정. 그 위는 WSOLA 로 늘린다(3단계).
  const rate = Math.min(Math.max(Number(speed), 0.5), 2.0).toFixed(2)
  const prosody = pitch ? `<prosody rate="${rate}" pitch="${pitch}">` : `<prosody rate="${rate}">`
  const payload = `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="${lang}"><voice name="${voice}">${prosody}${ssml ? text : esc(text)}</prosody></voice></speak>`
  const res = await fetch(`https://${REGION}.tts.speech.microsoft.com/cognitiveservices/v1`, {
    method: 'POST',
    headers: {
      'Ocp-Apim-Subscription-Key': KEY,
      'Content-Type': 'application/ssml+xml',
      'X-Microsoft-OutputFormat': 'riff-48khz-16bit-mono-pcm',
      'User-Agent': 'allirang',
    },
    body: payload,
  })
  if (!res.ok) throw new Error(`Azure ${res.status} ${await res.text()}`)
  return Buffer.from(await res.arrayBuffer())
}

if (import.meta.url === `file://${process.argv[1]}`) {
  let text = args.text
  if (args.card) {
    const cards = JSON.parse(readFileSync(new URL('../data/cards.json', import.meta.url), 'utf8'))
    const c = cards.find((x) => x.id === args.card)
    if (!c) throw new Error(`카드 없음: ${args.card}`)
    text = args.field === 'lastLine' ? c.lastLine : c.story
  }
  const buf = await synth({ text, voice: args.voice, speed: args.speed ?? 1, pitch: args.pitch })
  writeFileSync(args.out, buf)
  const sec = (buf.length - 44) / (48000 * 2)
  console.log(`${args.out}  ${(buf.length / 1024 / 1024).toFixed(2)}MB  ${sec.toFixed(1)}초`)
}
