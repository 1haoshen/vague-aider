# 本地真机批跑 Runbook —— 59 条扩充指令(Vague-ins-expanded-local.json)

用 Open-AutoGLM phone_agent 在真机上跑这 59 条扩充指令(Task_id 56–114),
每条按 **L1(模糊)/ L3(详细)** 两个级别 **各跑 2 次**,再用分析脚本出
**完成率 / 平均步长 / 耗时 / token 消耗**(对应论文指标)。

涉及 3 个脚本(都在 `Mobile-Agent-E/instr_rewrite/`):
- `run_phoneagent_batch.py` —— 批跑
- `analyze_phoneagent_logs.py` —— 出指标
- bench 文件:`app-data/Ins-bench/Vague-ins-expanded-local.json`

---

## 0. 前置条件(跑之前确认)

1. **adb 能连上手机**:`adb devices` 有一台 `device`(USB 调试已开、已授权)。
2. **装了 ADB Keyboard**(agent 输入文字要用):
   `adb shell ime list -s | grep adbkeyboard`,没有就装
   https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk
3. **模型 key**(autoglm-phone,走智谱 open.bigmodel.cn)。用环境变量传:
   ```bash
   export PHONE_AGENT_API_KEY=<你的智谱key>      # main.py 里那个 ef4ddb... 也可用
   ```
4. **手机装好涉及的 app**(没装的任务必败):
   - CN:携程旅行、去哪儿旅行、美团、小红书、抖音、哔哩哔哩、爱奇艺、大众点评、
     淘宝、京东、拼多多、知乎、猫眼、大麦、夸克、微信、网易云音乐、天气、备忘录/笔记
   - EN:Weather、Notes、Google Maps、YouTube、Gmail、X、Facebook、Amazon、
     Walmart、eBay、agoda、Booking、Tripadvisor、Chrome、rednote、网易云音乐

> 手机若只装国内 app,就只跑 cn 那批(加 `--lang-filter cn`,34 条);
> 只装 Google 生态就 `--lang-filter en`(25 条)。

---

## 1. 先 dry-run 看跑批计划(不碰设备)

```bash
cd <repo-root>     # /root/Source/vague-aider 或你本地的路径
python Mobile-Agent-E/instr_rewrite/run_phoneagent_batch.py \
    --levels L1,L3 --repeats 2 --exp expand59_run1 --dry-run
```
应显示 `tasks=59 ... -> 236 runs`(只 cn 是 136,只 en 是 100)。

---

## 2. 正式批跑

```bash
# 全部 59 条(cn+en)
python Mobile-Agent-E/instr_rewrite/run_phoneagent_batch.py \
    --levels L1,L3 --repeats 2 \
    --exp expand59_run1 \
    --max-steps 50

# 只跑中文 34 条(推荐:国内 app 生态)
python Mobile-Agent-E/instr_rewrite/run_phoneagent_batch.py \
    --levels L1,L3 --repeats 2 --lang-filter cn \
    --exp expand59_cn --max-steps 50

# 指定某几条先试(冒烟)
python ... --task-ids 56,57,110 --levels L1,L3 --repeats 1 --exp smoke
```

常用参数:
- `--device-id <serial>` 多设备时指定(`adb devices` 里的序列号)
- `--max-steps 50` 单任务最大步数(默认 50)
- `--lang-filter cn|en|all`(默认 all);`--agent-lang auto` 跟随每条 lang
- `--sleep 2` 两次运行之间停顿秒数;`--press-home` 每次跑前回桌面(默认开)
- 模型可改:`--base-url / --model / --apikey`(默认智谱 autoglm-phone)

**中断了怎么办**:加 `--resume` 重跑同一个 `--exp`,已完成的 (task,level,repeat) 会跳过:
```bash
python ... --exp expand59_run1 --levels L1,L3 --repeats 2 --resume
```

日志落在:`app-data/Ins-bench/phoneagent_logs/<exp>/`
每个 run 一个 `steps.json`,外加一个 `manifest.jsonl`(逐 run 记录)。

---

## 3. 出指标

```bash
python Mobile-Agent-E/instr_rewrite/analyze_phoneagent_logs.py \
    --exp-dir app-data/Ins-bench/phoneagent_logs/expand59_run1
```
输出(写在该 exp 目录下):
- `summary_by_level.csv` —— 每级(L1/L3)**完成率 / 平均步长 / 平均耗时 / 平均&总 token**
- `summary_by_level_repeat.csv` —— 分次(r1/r2)breakdown
- `runs.csv` —— 逐 run 明细,含空的 `manual_correct` 列

终端会打印一张表(完成率随 L1→L3 上升即符合预期)。

### ⚠️ 关于"完成率"
真机没有 MobileWorld 那种自动判分器,脚本默认的"完成率"= agent 自己报
`finish`(`finish_flag==success`),**不等于任务真做对**。要真实成功率:
1. 打开 `runs.csv`,在 `manual_correct` 列给每行人工标 `1`/`0`;
2. 重新出指标(用人工标签重算):
   ```bash
   python Mobile-Agent-E/instr_rewrite/analyze_phoneagent_logs.py \
       --exp-dir app-data/Ins-bench/phoneagent_logs/expand59_run1 --use-manual
   ```

---

## 速查(最常用三行)

```bash
export PHONE_AGENT_API_KEY=<智谱key>
python Mobile-Agent-E/instr_rewrite/run_phoneagent_batch.py --levels L1,L3 --repeats 2 --lang-filter cn --exp expand59_cn
python Mobile-Agent-E/instr_rewrite/analyze_phoneagent_logs.py --exp-dir app-data/Ins-bench/phoneagent_logs/expand59_cn
```
