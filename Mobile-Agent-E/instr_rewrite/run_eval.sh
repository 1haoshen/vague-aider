#!/usr/bin/env bash
# run_eval.sh —— 一键批跑 + 出指标(Open-AutoGLM phone_agent 真机评测)
#
# 用法:
#   export PHONE_AGENT_API_KEY=<智谱key>          # 必填
#   bash run_eval.sh [lang] [exp] [task_ids]
#     lang     : cn | en | all      (默认 cn)
#     exp      : 实验名(日志目录)   (默认 full112_<时间戳>)
#     task_ids : 56,57,60-65 形式    (默认 51-112,跳过前50条原始指令;传 1-112 跑全部)
#
# 例:
#   bash run_eval.sh cn                         # 跑全部中文任务
#   bash run_eval.sh all full112_all            # 跑全部 112 条
#   bash run_eval.sh cn smoke 99-112            # 只跑新增的 14 条
#
# 可选环境变量:
#   PHONE_AGENT_DEVICE_ID   多设备时指定 adb 序列号
#   MAX_STEPS               单任务最大步数(默认 50)
#   REPEATS                 每级重复次数(默认 2)

set -euo pipefail

LANG_FILTER="${1:-cn}"
EXP="${2:-full112_$(date +%Y%m%d_%H%M%S)}"
TASK_IDS="${3:-51-112}"   # 默认跳过前50条原始指令,只跑扩充的 51-112
MAX_STEPS="${MAX_STEPS:-50}"
REPEATS="${REPEATS:-2}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
RB="Mobile-Agent-E/instr_rewrite"
BENCH="app-data/Ins-bench/Vague-ins-full-112.json"
LOGROOT="app-data/Ins-bench/phoneagent_logs"

echo "================ 前置检查 ================"
command -v adb >/dev/null 2>&1 || { echo "❌ 未找到 adb,请先装 platform-tools"; exit 1; }
NDEV=$(adb devices | awk 'NR>1 && $2=="device"' | wc -l | tr -d ' ')
[ "$NDEV" -ge 1 ] || { echo "❌ 没有已连接设备(adb devices 里要有 device)"; exit 1; }
echo "✅ adb 设备: $NDEV 台"
if adb shell ime list -s 2>/dev/null | grep -qi adbkeyboard; then
    echo "✅ ADB Keyboard 已装"
else
    echo "⚠️  未检测到 ADB Keyboard —— 需要输入文字的任务可能失败"
    echo "    安装: https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk"
fi
[ -n "${PHONE_AGENT_API_KEY:-}" ] || { echo "❌ 请先: export PHONE_AGENT_API_KEY=<智谱key>"; exit 1; }
echo "✅ 模型 key 已设置"
echo "bench=$BENCH | lang=$LANG_FILTER | exp=$EXP | levels=L1,L3 x$REPEATS | max_steps=$MAX_STEPS"

TASK_ARG=()
[ -n "$TASK_IDS" ] && TASK_ARG=(--task-ids "$TASK_IDS")

echo ""
echo "================ 跑批计划(dry-run) ================"
python "$RB/run_phoneagent_batch.py" --bench "$BENCH" \
    --levels L1,L3 --repeats "$REPEATS" --lang-filter "$LANG_FILTER" \
    --exp "$EXP" "${TASK_ARG[@]}" --dry-run

echo ""
read -r -p "以上计划确认开跑? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "已取消。"; exit 0; }

echo ""
echo "================ 批跑(可中断,重跑同 exp 加 --resume 续) ================"
python "$RB/run_phoneagent_batch.py" --bench "$BENCH" \
    --levels L1,L3 --repeats "$REPEATS" --lang-filter "$LANG_FILTER" \
    --exp "$EXP" "${TASK_ARG[@]}" --max-steps "$MAX_STEPS"

echo ""
echo "================ 出指标 ================"
python "$RB/analyze_phoneagent_logs.py" --exp-dir "$LOGROOT/$EXP"

echo ""
echo "✅ 完成。逐 run 明细 / 可人工标注: $LOGROOT/$EXP/runs.csv"
echo "   人工标完 manual_correct 列后,重算真实成功率:"
echo "   python $RB/analyze_phoneagent_logs.py --exp-dir $LOGROOT/$EXP --use-manual"
