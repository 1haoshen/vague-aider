# MobileWorld L1/L2/L3 评测 Runbook

把 `Vague-ins-expanded.json` 里 50 条 MobileWorld 指令，按 L1(模糊)/L2(agent-bench)/L3(agent-friendly)
三个层级分别注入 MobileWorld 任务、各跑一轮 `mw eval`、汇总三组 success rate，验证
"模糊→精确改写有效"。

## 0. 机器前提（必须有 KVM）

Android emulator 需要 KVM 硬件加速。**云上普通 VM（如阿里云普通 ECS）拿不到 `/dev/kvm`**，
必须用：原生 Linux 物理机（BIOS 开 VT-x/AMD-V）、阿里云神龙裸金属、或支持嵌套虚拟化的实例。

换机器后先体检：
```bash
bash Mobile-Agent-E/instr_rewrite/mw_setup_check.sh
```
要点：`grep -Ec '(vmx|svm)' /proc/cpuinfo` > 0，且 `ls /dev/kvm` 存在。

## 1. 安装 MobileWorld

```bash
cd MobileWorld/MobileWorld
uv sync                      # 建 .venv，装 mobile_world + mw CLI
.venv/bin/mw env check       # 应全部 ✓（KVM 这项必须过）
```

## 2. 配 `.env`（MobileWorld/MobileWorld/.env）

```bash
# agent 模型(GPT-5.5)的 key；base_url+model 走命令行不在这
API_KEY=sk-<apiyi-key>
# 高德 Amap MCP（9 条任务）；阿里云百炼 key，注意是 sk- 开头
DASHSCOPE_API_KEY=sk-<bailian-key>
MODELSCOPE_API_KEY=                       # 用不到，留空
# ask_user 交互(14 条)：复用 apiyi
USER_AGENT_API_KEY=sk-<apiyi-key>
USER_AGENT_BASE_URL=https://api.apiyi.com/v1
USER_AGENT_MODEL=gpt-4.1
```

各字段依赖的任务（重排后的 Task_id）：
- 仅 `API_KEY`：27 条 → 55,56,57,58,64,66,67,73,75,77,78,79,83,85,86,88,89,90,91,92,93,96,97,98,99,101,102
- 需 `DASHSCOPE_API_KEY`（高德 MCP）：9 条 → 59,60,61,65,80,81,87,94,95
- 需 `USER_AGENT_*`（ask_user）：14 条 → 51,52,53,54,62,63,68,72,74,76,82,84,100,103

## 3. 起 emulator（终端 A，保持运行）

```bash
cd MobileWorld/MobileWorld
.venv/bin/mw env run --count 5 --launch-interval 20
# docker 要 root 就：sudo .venv/bin/mw env run ...
```

## 4. 跑评测（终端 B）

runner 默认 `--mw-cmd` 自动用 `.venv/bin/mw`（绝对路径，免 PATH/sudo 坑）。

```bash
cd <repo-root>

# 阶段 1：先验证管线 —— 27 条零依赖任务 × L1
python Mobile-Agent-E/instr_rewrite/mw_eval_runner.py \
    --agent general_e2e --model-name gpt-5.5 \
    --llm-base-url https://api.apiyi.com/v1 \
    --api-key sk-<apiyi-key> \
    --no-enable-mcp --no-enable-user-interaction \
    --levels L1 --max-concurrency 5 \
    --task-ids 55,56,57,58,64,66,67,73,75,77,78,79,83,85,86,88,89,90,91,92,93,96,97,98,99,101,102

# 阶段 2：加 MCP + 交互，全部 50 条 × L1/L2/L3
python Mobile-Agent-E/instr_rewrite/mw_eval_runner.py \
    --agent general_e2e --model-name gpt-5.5 \
    --llm-base-url https://api.apiyi.com/v1 \
    --api-key sk-<apiyi-key> \
    --enable-mcp --enable-user-interaction \
    --levels L1,L2,L3 --max-concurrency 5
```

docker 要 root 时给 runner 加：`--mw-cmd "sudo <repo>/MobileWorld/MobileWorld/.venv/bin/mw"`

## 5. 看结果

`app-data/Ins-bench/mw_eval_results/`:
- `mw_eval_summary.csv` — 50 行 × (L1/L2/L3 score + pass)
- `mw_eval_success_rates.csv` — 三级 SR 汇总
- `mw_eval_L1/L2/L3.json` — per-task 原始分

stdout 末尾的表（SR 应随 L1→L3 上升）：
```
level  total  scored  passed     SR%
   L1     50     50      18    36.0%
   L2     50     50      33    66.0%
   L3     50     50      43    86.0%
```

## 安全网

- 改写靠 AST 注入 `goal`，patch 前备份 `.vagueaider_backup`，跑完/中断(SIGINT/SIGTERM)/异常都自动还原，不污染 git。
- 跑前有 preflight 实测 `<mw-cmd> --help`，命令找不到立即失败、绝不动文件。
- `--dry-run` 只 patch+还原不真跑，用于验证。
