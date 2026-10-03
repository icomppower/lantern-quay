#!/bin/zsh
# Usage: scripts/run_step.sh <label> <build.py args...>
# Runs one Blender build step in a fresh process and logs peak memory to milestones/memory.log
set -e
cd "$(dirname "$0")/.."
LABEL=$1; shift
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
mkdir -p milestones
LOG=milestones/${LABEL}.stdout.log
/usr/bin/time -l perl -e "alarm shift; exec @ARGV" ${STEP_TIMEOUT:-1500} $BLENDER -b --python scripts/build.py -- "$@" > $LOG 2> milestones/${LABEL}.time.log || { tail -40 $LOG; tail -5 milestones/${LABEL}.time.log; exit 1; }
RSS=$(grep "maximum resident set size" milestones/${LABEL}.time.log | awk '{print $1}')
PEAK=$(grep "peak memory footprint" milestones/${LABEL}.time.log | awk '{print $1}')
REAL=$(grep " real " milestones/${LABEL}.time.log | awk '{print $1}')
printf "%s  %-14s peak_footprint=%.2fGB max_rss=%.2fGB wall=%ss args=%s\n" "$(date '+%F %T')" "$LABEL" \
  $(echo "$PEAK/1073741824" | bc -l) $(echo "$RSS/1073741824" | bc -l) "$REAL" "$*" >> milestones/memory.log
grep -E "STATS|RENDER|Error|Traceback" $LOG | head -20
tail -1 milestones/memory.log
