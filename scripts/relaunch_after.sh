#!/usr/bin/env bash
# 等指定进程退出后重新执行 run_all.sh(日志追加)
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 30; done
echo "=== relaunch $(date) ===" >> logs/run_all.log
exec ./run_all.sh >> logs/run_all.log 2>&1
