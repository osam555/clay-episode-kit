#!/usr/bin/env node
// aside 가 없을 때 대신 쓰는 Playwright 러너. stdin 으로 JS 스니펫을 받아 실행하고 stdout 에 결과를 찍는다.
// browser.py 의 repl() 이 이걸 스폰한다: `node scripts/pw_runner.mjs < snippet.js` (실제로는 stdin 파이프).
//
// 첫 실행은 로그인 창이 뜬다 — Google 계정으로 Flow(flow.google.com)와 YouTube Studio 에 수동 로그인해 둔다.
// 세션은 FLOW_WORK/pw-profile (영속 프로필)에 저장되어 다음 실행부터 재사용된다.
//
// 주입되는 전역: attachBrowserTab(idOrUrlSubstring) -> Playwright Page, openTab(url) -> Page,
//   listBrowserTabs() -> [{targetId, url}], sleep(ms), fs (writeFile/resolvePath 미니멀 shim).
// 기존 aside_flow_submit.py / aside_flow_dl.py / aside_up.py 에 박힌 JS 스니펫이 거의 그대로 돌아가도록 맞췄다.

import { chromium } from 'playwright'
import { mkdirSync, promises as fsp } from 'node:fs'
import path from 'node:path'
import os from 'node:os'

const ROOT = process.env.ALLIRANG_ROOT || new URL('..', import.meta.url).pathname.replace(/\/$/, '')
const FLOW_WORK = process.env.FLOW_WORK || path.join(ROOT, 'scratch', 'flow_tools')
const PROFILE_DIR = path.join(FLOW_WORK, 'pw-profile')
const WORK_DIR = path.join(FLOW_WORK, 'pw-work')
mkdirSync(PROFILE_DIR, { recursive: true })
mkdirSync(WORK_DIR, { recursive: true })

function readStdin() {
  return new Promise((resolve) => {
    let data = ''
    process.stdin.setEncoding('utf8')
    process.stdin.on('data', (d) => { data += d })
    process.stdin.on('end', () => resolve(data))
  })
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// 스니펫이 상대경로로 파일을 쓰고 읽는 관례(v.mp4, t.png 등)라 WORK_DIR 을 cwd 처럼 쓴다.
const fs = {
  writeFile: (name, data) => fsp.writeFile(path.join(WORK_DIR, name), data),
  readFile: (name) => fsp.readFile(path.join(WORK_DIR, name)),
  resolvePath: async (name) => path.join(WORK_DIR, name),
}

async function main() {
  const js = await readStdin()
  if (!js.trim()) { console.log(''); return }

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: null,
  })

  async function listBrowserTabs() {
    return context.pages().map((p, i) => ({ targetId: String(i), url: p.url() }))
  }

  async function attachBrowserTab(idOrSubstring) {
    const pages = context.pages()
    // 숫자 인덱스로 준 경우
    if (/^\d+$/.test(String(idOrSubstring)) && pages[Number(idOrSubstring)]) {
      return pages[Number(idOrSubstring)]
    }
    // URL 부분 일치로 찾는다
    const found = pages.find((p) => p.url().includes(idOrSubstring))
    if (found) return found
    // 없으면 새 탭을 연다
    const p = await context.newPage()
    if (typeof idOrSubstring === 'string' && /^https?:\/\//.test(idOrSubstring)) {
      await p.goto(idOrSubstring)
    }
    return p
  }

  async function openTab(url) {
    const p = await context.newPage()
    await p.goto(url)
    return p
  }

  // 스니펫은 최상위 await 를 쓴다 — AsyncFunction 으로 감싸 실행한다.
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
  const runner = new AsyncFunction(
    'attachBrowserTab', 'openTab', 'listBrowserTabs', 'sleep', 'fs', 'console',
    'Buffer', 'fetch',
    js,
  )

  try {
    await runner(attachBrowserTab, openTab, listBrowserTabs, sleep, fs, console, Buffer, fetch)
  } catch (e) {
    console.error('pw_runner error:', e && e.stack || e)
    process.exitCode = 1
  } finally {
    // 로그인 세션은 PROFILE_DIR(영속 프로필)에 남으니 컨텍스트는 매번 닫아도 다음 호출에서 재사용된다.
    await context.close().catch(() => {})
    process.exit(process.exitCode || 0)
  }
}

main()
