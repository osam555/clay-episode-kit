#!/usr/bin/env python3
"""drain_uploads.sh 의 크로스플랫폼(Windows 포함, sed 의존 없음) 파이썬 판.

큐 파일(FLOW_WORK/aside_queue.txt, 줄마다 "<ep> <long|short> <channel>")을 순서대로
aside_up.py 로 올린다. 채널이 한도(A 실패)에 걸리면 그 채널은 이번 실행 동안 건너뛴다.

  python3 scripts/drain_uploads.py
"""
import os
import subprocess
import sys
import time

ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
FLOW_WORK = os.environ.get('FLOW_WORK', os.path.join(ROOT, 'scratch', 'flow_tools'))
os.makedirs(FLOW_WORK, exist_ok=True)

QUEUE = os.path.join(FLOW_WORK, 'aside_queue.txt')
LOG = os.path.join(FLOW_WORK, 'aside_drain.log')
CAPPED_CHANNELS = os.path.join(FLOW_WORK, 'aside_capped.txt')
CAPPED_QUEUE = os.path.join(FLOW_WORK, 'aside_queue_capped.txt')


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return [ln.rstrip('\n') for ln in f]


def write_lines(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
        for ln in lines:
            f.write(ln + '\n')


def append_line(path, line):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def pop_first(path, line):
    lines = read_lines(path)
    if line in lines:
        lines.remove(line)
        write_lines(path, lines)


def main():
    open(CAPPED_CHANNELS, 'w').close()
    while True:
        lines = [ln for ln in read_lines(QUEUE) if ln.strip() and not ln.strip().startswith('#')]
        if not lines:
            time.sleep(60)
            continue
        line = lines[0]
        parts = line.split()
        if len(parts) != 3:
            pop_first(QUEUE, line)
            continue
        ep, kind, ch = parts

        capped = set(read_lines(CAPPED_CHANNELS))
        if ch in capped:
            pop_first(QUEUE, line)
            append_line(LOG, f'SKIP(capped) {line}')
            append_line(CAPPED_QUEUE, line)
            continue

        ok = False
        for _attempt in range(2):
            log_path = os.path.join(FLOW_WORK, f'up_{ep}_{kind}_{ch}.log')
            with open(log_path, 'w') as lf:
                res = subprocess.run(
                    [sys.executable, os.path.join(ROOT, 'scripts', 'aside_up.py'), ep, kind, ch],
                    stdout=lf, stderr=subprocess.STDOUT,
                )
            out = open(log_path, encoding='utf-8', errors='replace').read()
            if res.returncode == 0:
                ok = True
                break
            if 'A 실패' in out:
                append_line(CAPPED_CHANNELS, ch)
                break
            time.sleep(15)

        if ok:
            for ln in out.splitlines():
                if 'DONE' in ln:
                    append_line(LOG, ln)
        else:
            append_line(LOG, f'FAIL {line}')
            append_line(CAPPED_QUEUE, line)

        pop_first(QUEUE, line)


if __name__ == '__main__':
    main()
