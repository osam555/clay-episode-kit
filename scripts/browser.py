#!/usr/bin/env python3
"""브라우저 자동화 추상화 — Flow(Veo)·YouTube Studio 를 미는 JS 스니펫을 aside 나 Playwright 로 돌린다.

  from browser import repl
  out = repl(js_snippet)

동작:
  - PATH 에 `aside` 가 있으면 `aside repl "<js>"` 로 그대로 넘긴다 (allirang 원본과 같은 방식).
  - 없으면 `node scripts/pw_runner.mjs` 를 스폰해 같은 JS 환경(attachBrowserTab/openTab/listBrowserTabs/
    sleep/fs)을 Playwright 로 흉내 낸다. 첫 실행은 로그인 창이 뜨니 수동으로 Google/Flow/YouTube Studio 에
    로그인해 둔다 — 세션은 FLOW_WORK/pw-profile 에 저장되어 다음 실행부터 재사용된다.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
FLOW_WORK = os.environ.get('FLOW_WORK', os.path.join(ROOT, 'scratch', 'flow_tools'))
PW_RUNNER = os.path.join(ROOT, 'scripts', 'pw_runner.mjs')


def _which_aside():
    return shutil.which('aside')


def repl(js: str, timeout: int = 170) -> str:
    """js 스니펫을 실행하고 stdout+stderr 텍스트를 합쳐 돌려준다 (aside_up.py 등 기존 코드와 같은 계약)."""
    aside = _which_aside()
    if aside:
        p = subprocess.run([aside, 'repl', js], capture_output=True, text=True, timeout=timeout)
        return p.stdout + p.stderr

    os.makedirs(FLOW_WORK, exist_ok=True)
    if not os.path.exists(PW_RUNNER):
        raise RuntimeError(
            f'aside 도 없고 {PW_RUNNER} 도 없다 — package.json 의 node_modules 를 설치했는지 확인'
        )
    p = subprocess.run(
        ['node', PW_RUNNER],
        input=js, capture_output=True, text=True, timeout=timeout,
        env={**os.environ, 'FLOW_WORK': FLOW_WORK},
    )
    return p.stdout + p.stderr


def list_tabs():
    """listBrowserTabs() 결과를 파이썬 리스트로 돌려준다(둘 다에서 동작)."""
    out = repl('console.log(JSON.stringify(await listBrowserTabs()))')
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('['):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return []


if __name__ == '__main__':
    # CLI 디버그: python3 scripts/browser.py 'console.log(1+1)'
    print(repl(sys.argv[1] if len(sys.argv) > 1 else 'console.log("browser.py ok")'))
