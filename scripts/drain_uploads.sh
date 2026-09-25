#!/bin/zsh
# 큐(/tmp/aside_queue.txt: "<ep> <long|short> <channel>")를 순서대로 어사이드로 올린다. 채널 한도(A 실패)면 그 채널은 건너뛴다.
ROOT=${ALLIRANG_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}; cd "$ROOT"
S=${FLOW_WORK:-$ROOT/scratch/flow_tools}
Q=/tmp/aside_queue.txt; L=/tmp/aside_drain.log; CAP=/tmp/aside_capped.txt; : > $CAP
while true; do
  line=$(grep -v '^#' $Q | grep -v '^$' | head -1); [ -z "$line" ] && { sleep 60; continue; }
  set -- ${=line}; ep=$1; kind=$2; ch=$3
  if grep -q "^$ch$" $CAP; then sed -i.bak "1,/^$line$/{/^$line$/d;}" $Q; echo "SKIP(capped) $line" >> $L; echo "$line" >> /tmp/aside_queue_capped.txt; continue; fi
  ok=0
  for t in 1 2; do
    python3 $S/aside_up.py $ep $kind $ch > /tmp/up_${ep}_${kind}_${ch}.log 2>&1 && { ok=1; break; }
    grep -q "A 실패" /tmp/up_${ep}_${kind}_${ch}.log && { echo "$ch" >> $CAP; break; }
    sleep 15
  done
  if [ $ok = 1 ]; then grep DONE /tmp/up_${ep}_${kind}_${ch}.log >> $L; else echo "FAIL $line" >> $L; echo "$line" >> /tmp/aside_queue_capped.txt; fi
  sed -i.bak "1,/^$line$/{/^$line$/d;}" $Q
done
