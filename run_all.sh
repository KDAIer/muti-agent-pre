#!/usr/bin/env bash
# 按优先级跑全套实验(可断点续跑:重复执行会跳过已完成的题目)
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
W=${WORKERS:-16}
MAIN=single,cot,sc,debate,roles,anticonf

# v1(2048 上限)记录精确修复为 16k 上限:未截断的直接复用,截断处续写
[ -d results_v1_max2048 ] && $PY -m debate.repair --workers $W
$PY -m debate.analyze > /dev/null

$PY -m debate.run --dataset math  --methods $MAIN --n 156 --workers $W
$PY -m debate.run --dataset gsm8k --methods $MAIN --n 100 --workers $W
$PY -m debate.run --dataset mmlu  --methods $MAIN --n 100 --workers $W
$PY -m debate.run --dataset math  --methods debate_a1,debate_a5 --n 80 --workers $W
$PY -m debate.analyze > /dev/null
$PY -m debate.run --dataset aime  --methods $MAIN --n 60 --workers $W
$PY -m debate.analyze > /dev/null && echo "analysis written to results/summary.md"
