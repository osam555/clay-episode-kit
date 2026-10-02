#!/usr/bin/env python3
"""유튜브 업로드 큐 처리기 — 한 줄에 한 건: `<편> <long|short> <채널>`

  python3 scripts/yt_queue.py queue.txt            # 큐를 순서대로 올린다
  python3 scripts/yt_queue.py queue.txt --dry      # 올리지 않고 순서·검사만

규칙(실제로 겪은 사고에서 나온 것이다):
  - **한 번에 하나만 돈다.** 큐 옆에 `<큐>.lock` 을 만들고, 이미 있으면 거절한다.
    예전 처리기가 몇 시간 뒤 살아 있다가 같은 큐를 같이 읽어 같은 영상이 두 번 올라간 적이 있다.
  - 채널의 일일 한도(quotaExceeded / uploadLimitExceeded)가 나오면 그 채널은 그날 건너뛰고,
    못 올린 줄은 `<큐>.deferred` 로 옮긴다. 다음 날 그 파일을 큐로 다시 쓰면 된다.
  - 이미 올린 편은 편 JSON 의 yt 칸을 보고 건너뛴다(youtube_upload.py 가 한다).
  - 업로드 자체는 youtube_upload.py 가 한다 — 이 스크립트는 순서와 한도·중복 방지만 맡는다.
쇼츠는 `--part hook_short`(세로 쇼츠 칸)로 올린다.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT_MARKS = ('quotaExceeded', 'uploadLimitExceeded', 'exceeded the number of videos')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    queue, dry = sys.argv[1], '--dry' in sys.argv
    lock = queue + '.lock'
    if os.path.exists(lock):
        sys.exit(f'이미 처리 중이거나 비정상 종료 흔적이 있다: {lock} (다른 처리기가 없는지 확인한 뒤 지운다)')
    lines = [l.split() for l in open(queue, encoding='utf-8') if l.strip() and not l.startswith('#')]
    open(lock, 'w').write(str(os.getpid()))
    capped, deferred, done = set(), [], 0
    try:
        for ep, kind, ch in lines:
            if ch in capped:
                deferred.append(f'{ep} {kind} {ch}'); continue
            cmd = [sys.executable, f'{HERE}/youtube_upload.py', ep, '--channel', ch]
            if kind == 'short': cmd += ['--part', 'hook_short']
            if dry: cmd.append('--dry')
            p = subprocess.run(cmd, capture_output=True, text=True)
            out = p.stdout + p.stderr
            if p.returncode == 0:
                done += 1; print('OK  ', ep, kind, ch)
            elif any(m in out for m in LIMIT_MARKS):
                capped.add(ch); deferred.append(f'{ep} {kind} {ch}'); print('한도', ch, '— 이 채널은 오늘 건너뜀')
            else:
                deferred.append(f'{ep} {kind} {ch}'); print('실패', ep, kind, ch, out.strip().splitlines()[-1:] )
    finally:
        os.remove(lock)
    if deferred and not dry:
        open(queue + '.deferred', 'w', encoding='utf-8').write('\n'.join(deferred) + '\n')
    print(f'완료 {done} · 이월 {len(deferred)}' + (f' → {queue}.deferred' if deferred and not dry else ''))


main()
