# 本地真机批跑 Runbook —— Open-AutoGLM phone_agent

对 **Vague-ins-full-112.json(112 条)** 在真机上批跑,每条按 **L1(模糊)/ L3(详细)**
各跑 **2 次**,再出 **完成率 / 平均步长 / 耗时 / token 消耗**(对应论文指标)。

文件(都在 `Mobile-Agent-E/instr_rewrite/`):
| 文件 | 作用 |
|---|---|
| `run_eval.sh` | **一键执行**:前置检查 → dry-run → 批跑 → 出指标 |
| `run_phoneagent_batch.py` | 批跑(默认 bench 已设为 Vague-ins-full-112.json) |
| `analyze_phoneagent_logs.py` | 解析 steps.json 出指标 |
| `app-data/Ins-bench/Vague-ins-full-112.json` | bench(112 条) |

## bench 构成
- 112 条,Task_id 1–112;语言 **cn 64 / en 48**
- **批跑默认只跑 51–112(62 条扩充指令)**;前 50 条(原始 Vague-ins)默认跳过。要跑全部传 `1-112`
- 来源:原始 Vague-ins 50 + AndroidDaily 13 + MVISU 4 + 新造 45(Authored 31 + Authored2 14)
- 涉及 app(均在知识库,多数有 action_object_str):
  - **CN**:微信、夸克、京东、淘宝、拼多多、小红书、知乎、哔哩哔哩、抖音、猫眼、大麦、
    携程旅行、去哪儿旅行、美团、大众点评、网易云音乐、天气、高德地图、美图秀秀、
    备忘录/笔记、闹钟、应用商店、设置
  - **EN**:Weather、Notes、Google Maps、YouTube、Gmail、Edge、Chrome、X、Facebook、
    TikTok、rednote、NetEase Music、Amazon、Walmart、eBay、Fandango、agoda、Booking、Tripadvisor

## ⚠️ 安全:不会真扣钱
出行/票务/红包类指令的 L3 已统一改为 **"进入付款/确认页面后停留,不实际支付"**
(机票/火车/酒店/电影票/演唱会/微信红包 等)。仍建议用**测试账号**跑。

---

## 0. 前置条件
1. `adb devices` 有一台 `device`(USB 调试已开并授权)
2. 装了 **ADB Keyboard**(输入文字用):
   `adb shell ime list -s | grep adbkeyboard`,无则装
   https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk
3. 模型 key:`export PHONE_AGENT_API_KEY=<智谱key>`(main.py 里那个 ef4ddb… 也可用)
4. 手机装好上面涉及的 app(没装的任务必败)。国内 app 生态就只跑 cn,Google 生态就只跑 en。

---

## 1. 一键跑

### ▶ Windows(cmd + conda phone-agent)—— run_eval.bat
```cmd
conda activate phone-agent
set PHONE_AGENT_API_KEY=你的智谱key
cd /d <仓库根目录>

REM 默认:跑扩充 51-112 里的中文条(40 条;L1,L3 各 2 次)
Mobile-Agent-E\instr_rewrite\run_eval.bat cn

REM 跑全部扩充 51-112(62 条,含 en)
Mobile-Agent-E\instr_rewrite\run_eval.bat all full112_ext

REM 跑全部 112 条(含前 50 原始)
Mobile-Agent-E\instr_rewrite\run_eval.bat all full112_full 1-112

REM 只跑新增 14 条冒烟
Mobile-Agent-E\instr_rewrite\run_eval.bat cn smoke 99-112
```
可选:`set MAX_STEPS=40` / `set REPEATS=1`;多设备 `set PHONE_AGENT_DEVICE_ID=序列号`。
> `.bat` 里默认 `conda activate phone-agent`;环境名不同就改 .bat 里那一行。

### ▶ 不用 .bat,直接 python 调(和你习惯的 `python main.py "xxx"` 一样)
```cmd
REM 默认只跑 51-112;--apikey 不传会自动读环境变量 PHONE_AGENT_API_KEY
python Mobile-Agent-E\instr_rewrite\run_phoneagent_batch.py --lang-filter cn --exp full112_cn --dry-run
python Mobile-Agent-E\instr_rewrite\run_phoneagent_batch.py --lang-filter cn --exp full112_cn
python Mobile-Agent-E\instr_rewrite\analyze_phoneagent_logs.py --exp-dir app-data\Ins-bench\phoneagent_logs\full112_cn
```
要跑全部 112 条加 `--task-ids 1-112`;中断后重跑同一 `--exp` 加 `--resume` 续。

### ▶ Linux / macOS —— run_eval.sh
```bash
export PHONE_AGENT_API_KEY=<智谱key>
bash Mobile-Agent-E/instr_rewrite/run_eval.sh cn
```
三种方式都会先打印 dry-run 计划,确认后才真跑,跑完自动出指标。

---

## 2. 手动跑(等价命令)

```bash
# dry-run 看计划
python Mobile-Agent-E/instr_rewrite/run_phoneagent_batch.py \
    --levels L1,L3 --repeats 2 --lang-filter cn --exp full112_cn --dry-run

# 正式跑(默认 bench 就是 full-112)
python Mobile-Agent-E/instr_rewrite/run_phoneagent_batch.py \
    --levels L1,L3 --repeats 2 --lang-filter cn --exp full112_cn --max-steps 50

# 中断了续跑(同 exp 加 --resume,已完成的 task/level/repeat 自动跳过)
python Mobile-Agent-E/instr_rewrite/run_phoneagent_batch.py \
    --levels L1,L3 --repeats 2 --lang-filter cn --exp full112_cn --resume
```
日志:`app-data/Ins-bench/phoneagent_logs/<exp>/`(每 run 一个 steps.json + manifest.jsonl)。

---

## 3. 出指标

```bash
python Mobile-Agent-E/instr_rewrite/analyze_phoneagent_logs.py \
    --exp-dir app-data/Ins-bench/phoneagent_logs/full112_cn
```
产出(写在该 exp 目录):
- `summary_by_level.csv` — 每级 L1/L3 的 **完成率 / 平均步长 / 平均耗时 / 平均&总 token**
- `summary_by_level_repeat.csv` — 分次(r1/r2)breakdown
- `runs.csv` — 逐 run 明细,含空的 `manual_correct` 列

### ⚠️ 完成率口径
真机无自动判分器,默认"完成率"= agent 自报 `finish`(**不等于真做对**)。要真实成功率:
1. 在 `runs.csv` 的 `manual_correct` 列人工标 `1`/`0`;
2. `python .../analyze_phoneagent_logs.py --exp-dir <...> --use-manual` 重算。

---

## 速查
```bash
export PHONE_AGENT_API_KEY=<智谱key>
bash Mobile-Agent-E/instr_rewrite/run_eval.sh cn          # 一键:跑中文 + 出指标
```
