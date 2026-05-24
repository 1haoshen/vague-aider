# 附录：指令改写成本、知识库构成与指令词云

本附录对应三件交付物（脚本可复现、图表与 `.tex` 为英文，叙述为中文）。所有脚本、数据与产物均位于 `app-data/appendix/`。

| 部分 | 数据源 | 脚本 | 产物 |
|---|---|---|---|
| A 改写成本 | `Ins-bench/Vague-ins-rewritten50.json` | `rewrite_token_stats.py` | `rewrite_token_stats.{json,_overall.csv,_by_type.csv}`、`rewrite_prompt.txt` |
| B 知识库桑基图 | `knowledge-base/AppUi-final.json` | `kb_sankey.py` | `kb_sankey.png`、`kb_sankey.html` |
| C 指令词云 | `Ins-bench/Vague-ins.json` | `instruction_wordcloud.py` | `wordcloud_cn.png`、`wordcloud_en.png` |

英文论文段落与表/图的 LaTeX 源码统一见 `appendix.tex`（含改写 prompt 原文）。

---

## A. 指令改写流程与 token 成本

### A.1 流程
每条 VagueBench 任务以一条刻意"模糊"的一级指令（L1）为种子，经一次**检索增强的单次 LLM 调用**扩写为两种更具体的形式：

- **L2（agent-benchmark 风格）**：点名每个 app 及其承担的子任务，但不含 UI 控件级动作；
- **L3（agent-friendly）**：逐 app 给出显式 GUI 操作步骤。

检索为本地确定性逻辑（不耗 token）：先把杂乱的 `Invovled_App_Name` 归一化（分隔符、缩写、中英别名、常见拼写错误），解析到合并后的知识库；对每个命中 app 仅注入一份**精简切片**——`scenario` 标签、≤80 字简介、以及与 L1 词元重叠度最高的 2–3 条 `action_object_str` 动作链——而非整库。随后一次 Qwen3-8B 调用即返回 L2、L3、引用的 app 列表与一句理由（单个 JSON 对象）。

完整的 system prompt、user-message 模板（含一条 in-context 示例）与解码参数已逐字收录于 `rewrite_prompt.txt`，并在 `appendix.tex` 的 Listing 1 中原样展示。注：本次 50 条的批跑使用 `lang=None`，未启用语言锁定行（`{LANG_LINE}` 为空）；脚本仍保留 en/cn 两种可选变体。

> KB 切片实例（任务 #1，命中"美图秀秀 + 微信"，1030 字符）已在脚本中可复现，形如：
> `## 美图秀秀 / scenario: 修图软件 / intro: … / - 一键美颜人像: Tap … → Tap … → save`。

### A.2 成本统计
对全部 **N=50** 条改写逐条记录了 OpenRouter 的 token 计数与挂钟耗时（**50 条全部成功，无解析失败**）。

**表 A.1　50 条 L1→L2+L3 改写成本（Qwen3-8B，每任务一次调用）**

| 指标 | 总计 | 均值 | 中位数 | 标准差 | 最小 | 最大 |
|---|---:|---:|---:|---:|---:|---:|
| 输入 token | 38,347 | 766.9 | 722.5 | 271.9 | 455 | 2,285 |
| 输出 token | 7,261 | 145.2 | 139.0 | 37.4 | 86 | 246 |
| 总 token | 45,608 | 912.2 | 873.5 | 295.0 | 552 | 2,478 |
| 耗时（秒） | 186.5 | 3.73 | 3.55 | 0.76 | 2.44 | 6.04 |
| KB 切片（字符） | 50,529 | 1010.6 | 814.5 | 1036.2 | 47 | 6,973 |

### A.3 分析
- **总量。** 改写整个 50 条种子集合共耗 **45,608 token**（输入 38,347 / 输出 7,261），挂钟约 **186.5 s**。
- **单任务。** 平均 **767 输入 + 145 输出 = 912 token / 3.7 s**；输出/输入比仅 **0.19**，说明成本由注入上下文而非生成主导。
- **检索的作用。** 因为只注入少量 KB 切片（平均约 1,011 字符），单任务输入维持在 ~767 token——比整库注入低约一个数量级——这正是整套流程在全集仍能控制在"不到一分钱、不到三分钟"的原因。
- 按任务类型的细分见 `rewrite_token_stats_by_type.csv`（27 条未标注类型，其余按社交媒体/生活/旅游/购物等分布）。

---

## B. 知识库构成（桑基图）

VagueBench 的改写以人工策划的 **115 个 app 知识库**为支撑。其中 **57 个**带有 `action_object_str` 字段（为每个常用功能给出显式、GUI-grounded 的动作链），L3 的操作步骤即来自这 57 个 app。

图 B.1（`kb_sankey.png`）以三级桑基图呈现其构成：粗粒度**领域（Domain，4）→ 场景（Scenario，11）→ App（57）**。**流带宽度 = 该 app 已记录的功能数**，越粗代表动作库越丰富；app 名后括号内即功能数。

- 11 个场景归并为 4 个领域：Tools & Productivity（系统应用/办公协助/搜索引擎/修图软件，18 app）、Social & Entertainment（社交媒体/视频播放/音乐电台，17 app）、Life Services（生活购物/外卖平台/健康与教育，14 app）、Travel & Mobility（旅游出行，8 app）。
- 57 个 app 共记录 **421 个功能 / 2,542 个动作步**，平均每 app 7.4 个功能、每条动作链 6.0 步。
- 按约定，结构层标签（领域/场景）译为英文，**app 名保留原文**（专有名词，含中英文，经测试 CJK 在 PNG 中正常渲染）；同时输出可交互的 `kb_sankey.html`。

> 备选层级（场景→App→功能，叶子=421 个具体功能名）亦可由脚本调整得到，但叶子过密、标签难读，故采用领域→场景→App。

---

## C. 指令词云（中/英）

VagueBench 为双语基准：50 条 L1 种子指令中**中文 24 条、英文 26 条**。图 C.1 按语言各出一张词云，取自 **L1（最模糊、headline）指令**，并裁剪为手机轮廓以呼应数据集总览图。中文用 `jieba` 分词、英文用词边界正则，去除功能词后让"动作意图"与"app/实体名"凸显。

- **中文高频**：查看、推荐、记录、添加、分享，及购物车、广州、电影、航空公司、最新等具体对象。
- **英文高频**：check / search / share / add / record，及 cart、weather、latest、platforms 等对象，并含命名实体（Kai Chen、Elon Musk 等）。
- 结论：L1 表层以**开放式动作动词 + 具体对象/实体**为主，而**省略了 agent 必须自行推断的 app 与 UI 步骤**——这正是该基准刻意制造的"模糊性"。

---

## 复现方式

```bash
cd app-data/appendix
pip install wordcloud jieba plotly kaleido pandas   # matplotlib/numpy/PIL 已具备
plotly_get_chrome -y                                # kaleido 导出 PNG 需要

python3 rewrite_token_stats.py        # → 表 A.1 的 CSV/JSON
python3 kb_sankey.py                  # → kb_sankey.png / .html（需中文字体 Noto Sans CJK SC）
python3 instruction_wordcloud.py      # → wordcloud_cn.png / wordcloud_en.png
```

LaTeX 编译：`appendix.tex` 因含 CJK（prompt 与桑基图），请用 **XeLaTeX/LuaLaTeX** 编译，并加载 `fontspec + xeCJK`、`booktabs`、`graphicx`、`fancyvrb`、`tcolorbox`（详见文件头注释）。
