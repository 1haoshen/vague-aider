# MobileWorld L1/L2/L3 评测 Runbook

把 `Vague-ins-expanded.json` 里 50 条 MobileWorld 指令，按 L1(模糊)/L2(agent-bench)/L3(agent-friendly)
三个层级分别注入 MobileWorld 任务、各跑一轮 `mw eval`、汇总三组 success rate，验证
"模糊→精确改写有效"。

---

## 附：Windows 11 + WSL2 实测流程（含挪盘）

在 Win11 单机上跑（实测可行）。所有 Linux 操作在 WSL2 Ubuntu 里做；`wsl --*` 管理命令在
管理员 PowerShell 里做。

```
[A] 管理员 PowerShell: wsl --install -d Ubuntu-22.04（OOBE 报错就装预览版 WSL，或 -u root 进）
[B] WSL 内验 KVM（生死门）:  ls -l /dev/kvm ; grep -Ec '(vmx|svm)' /proc/cpuinfo  (>0 且有设备)
[C] WSL 内修权限:           sudo usermod -aG kvm $USER ; sudo chmod 666 /dev/kvm
[D] 项目放 ~（别放 /mnt/d）:  cd ~ ; git clone <你的repo> vague-aider
[E] clone MobileWorld:      git clone https://gh-proxy.com/https://github.com/Tongyi-MAI/MobileWorld.git MobileWorld/MobileWorld
                            cd MobileWorld/MobileWorld ; git checkout 9cb125b1...
[F] 装 docker(国内):        sudo apt install -y docker.io ; sudo usermod -aG docker $USER
                            sudo service docker start ; newgrp docker
[G] 配 docker hub 加速:     写 /etc/docker/daemon.json 的 registry-mirrors，重启 docker
[H] 验 KVM 透传:            docker run --rm --device /dev/kvm alpine ls -l /dev/kvm
[I] 装 uv + uv sync:        curl -LsSf https://astral.sh/uv/install.sh | sh ; uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple
[J] 写 .env（见第 2 节）
[K] 拉镜像(ghcr 国内代理):  docker pull ghcr.nju.edu.cn/tongyi-mai/mobile_world:latest
                            docker tag ghcr.nju.edu.cn/tongyi-mai/mobile_world:latest ghcr.io/tongyi-mai/mobile_world:latest
```

### ⭐ 挪盘（C 盘空间不足时必做，在 [K] 之后、[L] 之前）

WSL 默认整个系统(含 10G 镜像 + 5 个模拟器容器)都在 C 盘的 `ext4.vhdx`。C 盘 < ~40G 空闲就要
整体挪到大盘(如 D)。`wsl --export/--import` 搬的是**整个 Ubuntu**，所有项目+镜像+环境一锅端，
**Linux 内部路径不变**(`/home/<user>/vague-aider` 照旧)。

在**管理员 PowerShell**：
```powershell
wsl --shutdown
mkdir D:\wsl
wsl --export Ubuntu-22.04 D:\wsl\ubuntu-backup.tar     # 打包(~16G，几分钟)
wsl --unregister Ubuntu-22.04                          # 删 C 盘旧的，释放空间
wsl --import Ubuntu-22.04 D:\wsl\ubuntu D:\wsl\ubuntu-backup.tar --version 2
# 设回默认用户(import 后默认 root)
wsl -d Ubuntu-22.04 -u root bash -c "printf '[user]\ndefault=<你的用户名>\n' > /etc/wsl.conf"
wsl --shutdown
```
挪完进 WSL 验证(三样都对再删 backup.tar)：
```bash
whoami                          # 你的用户名
docker images | grep mobile     # 镜像还在
df -h /                         # / 在 D 盘的 vhdx 上
sudo service docker start       # import 后 docker 要重启一次
```

`[L]` 起就走下面通用流程（第 7 节 体检/起环境/跑评测），命令完全一样。

---

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
