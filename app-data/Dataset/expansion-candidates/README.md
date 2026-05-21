# VagueBench 扩充候选指令集 — 整理记录

**生成日期**：2026-05-20  
**知识库基准**：`app-data/knowledge-base/AppUi-final.json`（115 个 app）  
**已有 VagueBench**：`app-data/Dataset/Vague-ins.json`（50 条，Original / L1 / L2 / L3 四元组）

本目录汇总了从 5 个外部指令集中筛出的、**所涉 app 被 115-app 知识库覆盖**的候选指令，
按 benchmark 拆分成独立 JSON，每条都标注了在 VagueBench 中可担任的层级（L1 / L2 / L3 / Original）。

---

## 1. VagueBench 四级指令构造回顾

| 层级 | 性质 | 典型形式 |
|---|---|---|
| **L1 用户友好型** | 仅描述核心需求/意图 | "找个便宜的 Switch Joy-Con" |
| **L2 主流 agent-bench 风格**（≈Original） | 给出 app 名 + 简要步骤 | "在 Amazon/Walmart/Best Buy 上比较 Switch Joy-Con 价格" |
| **L3 agent 友好型** | 完整 app 内部操作路径 | "1.打开 Amazon → 2.点搜索框 → 3.输入… → 4.…" |

扩充每条指令时，须基于知识库 `AppUi-final.json` 中对应 app 的 `action_object_str` 行动路径
完成 L1→L3 之间的改写。

---

## 2. 五个外部指令集横向对比

| 数据集 | 总量 | KB-覆盖 | 命中的 KB app 数 | 天然契合的层级 | 推荐扩充用途 |
|---|---:|---:|---:|---|---|
| **AndroidWorld** | 116 | 54 | 7 | L3 模板化（英文，open-source 工具为主） | 英文 L3 种子，需手写 L1 |
| **MobileWorld** | 192 | 136 | 17 | L1/L2（goal 风格自然语言） | L1/L2 种子，需补 L3 |
| **AndroidDaily** | 235 | **200** | **33** | ⭐ **三级模糊度自带** | **直接套 L1/L2/L3** |
| **AndroidArena** | 226 | 197 | 14 | L3（动作粒度，英文） | 英文 L3 种子，需手写 L1 |
| **MVISU-cn** | 206 | 140 + 36 Vague | 38 | L1（Vague-type） + L2/Original | **直接套 L1**（36 条） |
| **MVISU-en** | 198 | 127 + 36 Vague | 37 | L1（Vague-type） + L2/Original | **直接套 L1**（36 条） |

> "Vague-type" 在 MVISU 中 `APP=[]` 字段为空但指令本身就是高度模糊的用户意图——例如「我想听音乐」「I want to eat」——这正是 VagueBench L1 的标准形态。

---

## 3. 数据集逐个说明

### 3.1 AndroidWorld（116 条 → 可用 54 条）

**结构**：每条只有一个 `task_template`（带 `{param}` 占位的英文模板化指令），偏 agent-friendly。  
**位置**：`android-world/android_world/android_world/task_metadata.json`

**KB-命中分布**：
```
21  备忘录/笔记  (Markor / Joplin)
17  日历        (Simple Calendar Pro)
 7  信息        (Simple SMS Messenger)
 3  Chrome
 3  闹钟        (Clock stopwatch)
 3  相册        (Simple Gallery Pro)
 2  相机
```
**特点**：大量参数化、open-source 应用替代（Markor↔笔记、Simple Gallery↔相册）。
没有原生模糊版本，**L1 全靠手写**。多应用任务 8 条（Markor↔VLC↔Chrome↔Gallery 链）。

**缺失 app**：Audio Recorder、Contacts、arduia expense、OpenTracks、Tasks.org、
Broccoli、Retro Music、OsmAnd、VLC、Files（KB 未收录）。

### 3.2 MobileWorld（192 条 → 可用 136 条）

**结构**：每个任务是一个 Python 类，含 `goal = "..."`（自然语言意图）+ `app_names = {...}`。  
**位置**：`MobileWorld/MobileWorld/src/mobile_world/tasks/definitions/<folder>/*.py`

**folder → 主导 KB app**：
```
gmail     → gmail / 邮件
calendar  → 日历
messages  → 信息 (+ MCP-Amap)
map       → 高德地图 / googleMap
chrome    → Chrome
settings  → 设置
native    → 相机 / 相册 / 闹钟 / 邮件
work      → 邮件 / 日历 / gmail / 信息 (业务复合)
```

**KB-命中分布**：
```
47  信息        43  邮件        26  日历
17  gmail       15  高德地图    11  Chrome  
11  相册        10  设置         7  闹钟
 5  googleMap    3  相机         2  天气
其余 alibaba / booking / DeepSeek / Google / 备忘录/笔记
```

**特点**：goal 风格天然偏 L1/L2 —— 例："Take a photo, and share it with Henry via email."  
**注意**：`Mastodon`(Twitter clone)、`Mattermost`(Slack clone)、`MCP-arXiv`、`MCP-Github`、
`MCP-stockstar`、`Files`、`Taodian` 不在 KB → 已自动剔除。
**56 条被剔除**主要因为完全依赖 Mastodon / Mattermost / Files / MCP 工具。

### 3.3 AndroidDaily ⭐（235 条 → 可用 200 条）

**结构**：CSV，含 `任务/场景/APP名称/任务复杂度/任务模糊度/个性化程度/综合难度`。  
**位置**：`AndroidDaily/Android%20Daily.csv`

> **本数据集是扩充 VagueBench 的最佳来源**：
> `任务模糊度` 字段的 高/中/低 三级与 VagueBench 的 L1/L2/L3 几乎一一对应。

**KB-覆盖 × 模糊度交叉**：

| 模糊度 | KB-覆盖 / 总数 | 直接担任的 VagueBench 层级 |
|---|---:|---|
| **高模糊度** | **22 / 24** | **L1 用户友好型** |
| 中模糊度 | 39 / 47 | L2 / Original |
| 低模糊度 | 139 / 164 | L3 agent-friendly 种子 |

**Top KB-app**：
```
微信 26   携程旅行 23   淘宝 21   京东 17   美团 17   去哪儿旅行 14
铁路12306 13   高德地图 13   哔哩哔哩 10   小红书 9   拼多多 8   飞猪 8
抖音 8   备忘录/笔记 6   大众点评 6   知乎 4   网易云音乐 3   QQ音乐 3 ...
```

**示例**：
- 高模糊：「打开支付宝,看看我的蚂蚁森林能量有多少克」「在抖音里搜索"旅行Vlog"」
- 中模糊：「在拼多多帮我搜索男士的短袖T恤」
- 低模糊：「在铁路12306 App里买一张本周五晚上从广州南到长沙南的二等座高铁票」

**缺失 app**：微博、滴滴出行、饿了么、酷我音乐、唯品会、同程旅行、京东到家、淘票票、微博、豆瓣、今日头条、京东金融。

### 3.4 AndroidArena（226 条 → 可用 197 条）

**结构**：YAML，按 app 文件组织，每条含 `instruction` + 实际 `action_seq`（UI 自动化命令）。  
**位置**：`AndroidArena/tasks/*.yaml`

**file → KB app 映射**：
```
calendar(7)     → 日历
camera(14)      → 相机
clock(14)       → 闹钟
weather(14)     → 天气
gmail(18)       → gmail / 邮件
google-maps(14) → googleMap
messages(14)    → 信息
photos(6)       → 相册
settings(19)    → 设置
youtube(12)     → youtube
slack(?)        → Slack
cross-app(22)   → 多 app 复合 (Gmail+Maps+Messages+Slack...)
constrain(35)   → 受限指令通用任务（多 app）
```
**缺失 app**：Contacts、Firefox、Google Drive（KB 未收录；Chrome 已有可替代部分场景）。  
**特点**：指令偏向 **L3 / 动作粒度**（搜索某关键词、点赞某视频、设新闻闹钟等），
基本无模糊版本，**L1 全靠手写**；适合扩充英文侧的 L3 池。

### 3.5 MVISU-Bench（cn 206 + en 198）

**结构**：JSON，`{ID, TaskType, APP, APPType, Instruction}`。  
**位置**：`MVISU-Bench-main/MVISU-Bench-main/data/{cn,en}_mvisu_bench.json`

**TaskType × KB 覆盖**：

| TaskType | cn 覆盖/总 | en 覆盖/总 | 用途 |
|---|---:|---:|---|
| **Vague** (APP=[] 的模糊意图) | 36/36 | 36/36 | ⭐ **直接担任 L1** |
| Single-App | 31/40 | 23/35 | L2 / Original |
| Multi-App | 61/62 | 50/56 | L2 多 app 场景 |
| Interactive | 23/32 | 30/36 | 参考（多轮对话，与 VagueBench 主轴不同） |
| Unethical | 24/36 | 20/35 | 另一研究维度，不建议混入 VagueBench 主集 |

> **MVISU 的 Vague-type 共 72 条**（cn 36 + en 36），APP 字段为空，
> 指令本身就是「我想听音乐」「I want to eat」这类纯意图——可作 L1 直接复用，
> 由我们指派 KB 中合适的 app 后再写 L2/L3。

**Top KB-app**：
- cn：微信 36、抖音 15、备忘录 15、小红书 14、百度 10、设置 10、美团 10、知乎 8 …
- en：Google 18、微信 16、Instagram 12、信息 11、备忘录 11、googleMap 10、youtube 9、tiktok 8 …

**注意**：Unethical-type（合计 71 条）含恶意/不当指令，仅用于另文研究安全侧；不建议归入 VagueBench 主集。

---

## 4. 候选文件清单

```
expansion-candidates/
├── README.md                       ← 本文件
├── androidworld_candidates.json    ( 54 条)
├── mobileworld_candidates.json     (136 条)
├── androiddaily_candidates.json    (200 条)   ⭐ 三级模糊度自带
├── androidarena_candidates.json    (197 条)
├── mvisu_cn_candidates.json        (175 条，含 36 条 Vague-type)
└── mvisu_en_candidates.json        (159 条，含 36 条 Vague-type)
```

每个 JSON 条目结构（公共字段）：
```json
{
  "source": "AndroidDaily",
  "source_id": "47",
  "instruction_seed": "原始指令文本",
  "mapped_kb_apps": ["携程旅行"],          // 匹配到 KB 中的 app 列表
  "suggested_role": "L1 user-friendly",    // 在 VagueBench 中的建议层级
  "...": "数据集特有字段（ambiguity / task_type / scenario / difficulty / declared_apps 等）"
}
```

---

## 5. 推荐的扩充策略

按"产出每条 VagueBench 四元组所需的手工成本"由低到高：

### 优先级 A —— AndroidDaily 三档模糊度直接配对
- 用 **22 条「高模糊度」** 作 L1
- 用 **39 条「中模糊度」** 作 L2 / Original
- 用 **139 条「低模糊度」** 作 L3 种子
- **手工成本最低**：从同一 app 簇（如携程旅行）中各抽一条不同模糊度的指令配对成四元组即可，
  少量补齐 Original。
- **建议先批量产出 30~50 条**中文侧扩充。

### 优先级 B —— MVISU Vague-type 直接复用为 L1
- 36 条 cn + 36 条 en，已是纯 L1 意图。
- 由我们指派 KB app 后，**只需手写 L2 + L3**（基于 `action_object_str`）。
- 适合补全 VagueBench 英文侧 L1。

### 优先级 C —— MobileWorld goal 风格做 L1/L2 种子
- 136 条 goal 已是自然语言意图，多为多 app 工作流。
- 业务复合场景丰富（邮件↔日历↔信息↔地图），适合扩多 app L1。
- 需要补 L3（基于 `action_object_str`）。

### 优先级 D —— AndroidWorld / AndroidArena 反向蒸馏
- 共 251 条 L3 模板化指令（英文为主）。
- 适合做"L3 已有 → 反推 L1"的扩充练习。
- 但需注意：AndroidWorld 用大量 KB 未收录的 open-source 替代 app（Markor、OpenTracks 等），
  虽可用语义靠近的 KB app（备忘录/笔记、Strava）代偿，但风险是 action path 对不上。建议慎用。

### 优先级 E —— MVISU Unethical（71 条）
- 不建议合并入 VagueBench 主集，可单列做安全/伦理侧的子集。

---

## 6. 已知 KB 缺口（按出现频次排序）

下列 app 在多个 benchmark 中频繁出现，**但 115-app 知识库尚未收录**，扩充时会被自然剔除。
如果未来想进一步扩 VagueBench，可考虑把这些纳入 KB：

**中文**：微博、滴滴出行、饿了么、酷我音乐、唯品会、同程旅行、京东金融、京东到家、
QQ浏览器、淘票票、豆瓣、今日头条、闲鱼、转转、小猿搜题、有道词典、菜鸟驿站、企业微信。

**英文**：WhatsApp、Telegram、Bing、Edge、Yahoo、Pinterest、Quora、Naver Map、
Uber Eats、Temu、Netflix、ChinaDaily、ESPN、AppGallery (HMS 应用市场)。

**开源/工具**：Markor、Joplin、Tasks.org、Broccoli、arduia expense、OpenTracks、
Retro Music、OsmAnd、VLC、Audio Recorder、Files、Contacts、Firefox、Google Drive、
Google Contacts、Mastodon、Mattermost。
