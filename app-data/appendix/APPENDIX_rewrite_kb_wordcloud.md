# 附录：指令改写成本、知识库构成与指令词云

本附录对应三件交付物（脚本可复现、图表与 `.tex` 为英文，叙述为中文）。所有脚本、数据与产物均位于 `app-data/appendix/`。

| 部分 | 数据源 | 脚本 | 产物 |
|---|---|---|---|
| A 改写成本 | `Ins-bench/Vague-ins-expanded-rewritten-fresh.json`（103 条） | `rewrite_token_stats.py` | `rewrite_token_stats_expanded-rewritten-fresh.{json,_overall.csv,_by_type.csv}`、`rewrite_prompt.txt` |
| B 知识库桑基图 | `knowledge-base/AppUi-final.json` | `kb_sankey.py` | `kb_sankey.png`、`kb_sankey.html` |
| C 指令词云 | `Ins-bench/Vague-ins-expanded.json`（103 条） | `instruction_wordcloud.py` | `wordcloud_cn.png`、`wordcloud_en.png` |

> 50 条种子集（`Vague-ins-rewritten50.json`）的成本统计仍可由 `python3 rewrite_token_stats.py`（默认）复现，产物为 `rewrite_token_stats*.csv`。英文论文段落与表/图源码统一见 `appendix.tex`（含改写 prompt 原文）。

---

## A. 指令改写流程与 token 成本（扩充集 103 条）

### A.1 流程
每条 VagueBench 任务以一条刻意"模糊"的一级指令（L1）为种子，经一次**检索增强的单次 LLM 调用**扩写为两种更具体的形式：

- **L2（agent-benchmark 风格）**：点名每个 app 及其承担的子任务，不含 UI 控件级动作；
- **L3（agent-friendly）**：逐 app 给出显式 GUI 操作步骤。

检索为本地确定性逻辑（不耗 token）：先把杂乱的 `Invovled_App_Name` 归一化（分隔符、缩写、中英别名、常见拼写错误），解析到合并后的知识库；对每个命中 app 仅注入一份**精简切片**（`scenario` 标签、≤80 字简介、与 L1 词元重叠度最高的 2–3 条 `action_object_str` 动作链）。一次 Qwen3-8B 调用即返回 L2、L3、引用的 app 列表与一句理由（单个 JSON）。完整 prompt 见 `rewrite_prompt.txt` 与 `appendix.tex` 的 Listing 1。

### A.2 成本统计
对全部 **103 条**改写逐条记录 OpenRouter 的 token 计数与挂钟耗时（**103 条全部成功，无解析失败**）。

**表 A.1　扩充集 103 条 L1→L2+L3 改写成本（Qwen3-8B，每任务一次调用）**

| 指标 | 总计 | 均值 | 中位数 | 标准差 | 最小 | 最大 |
|---|---:|---:|---:|---:|---:|---:|
| 输入 token | 74,224 | 720.6 | 707.0 | 208.3 | 453 | 2,262 |
| 输出 token | 14,544 | 141.2 | 137.0 | 38.7 | 71 | 281 |
| 总 token | 88,768 | 861.8 | 847.0 | 232.3 | 562 | 2,464 |
| 耗时（秒） | 420.3 | 4.08 | 3.64 | 1.72 | 2.47 | 16.49 |
| 改写 app 数/任务 | 161（次） | 1.56 | 1.00 | 0.66 | 0 | 4 |
| KB 切片（字符） | 91,539 | 888.7 | 784.0 | 789.1 | 47 | 6,973 |

### A.3 分析
- **总量。** 改写整个 103 条扩充集共耗 **88,768 token**（输入 74,224 / 输出 14,544），挂钟约 **420.3 s（≈7 分钟）**。
- **单任务。** 平均 **721 输入 + 141 输出 = 862 token / 4.08 s**，平均引用 **1.56 个 app**；全集共触及 **43 个去重 app**。
- **检索的作用。** 输出/输入比仅 **0.20**，成本由注入上下文而非生成主导；因只注入少量 KB 切片（平均约 889 字符），单任务输入维持在 ~721 token，比整库注入低约一个数量级。
- 按任务类型细分见 `rewrite_token_stats_expanded-rewritten-fresh_by_type.csv`（办公协助 18、生活 17、社交媒体 11 等）。

> 注：仓库原有的 `Vague-ins-expanded-rewritten.json`（87 条）基于**旧版**扩充集、与当前 103 条几乎不重合，已弃用；本次输出写入新文件 `Vague-ins-expanded-rewritten-fresh.json`，未覆盖旧文件。

---

## B. 知识库构成（桑基图）

VagueBench 的改写以人工策划的 **115 个 app 知识库**为支撑，其中 **57 个**带有 `action_object_str`（为每个常用功能给出显式 GUI 动作链），L3 的操作步骤即来自这 57 个。

图 B.1（`kb_sankey.png`）以三级桑基图呈现其构成：**语言（CN/EN）→ 8 个 app 类别 → 具体 app（全英文名）**。**流带宽度 = 该 app 已记录的功能数**，越粗代表动作库越丰富；app 名后括号内即功能数。

- **双语构成：** 36 个中文系 app（CN，共 278 个功能）+ 21 个国际 app（EN，共 143 个功能）。
- **8 个类别**（由 11 个原始 scenario 归并）：System Tool、Search & Browser、Productivity、Social Media、Video & Music、Shopping、Travel、Lifestyle。
- 57 个 app 共记录 **421 个功能 / 2,542 个动作步**，平均每 app 7.4 功能、每链 6.0 步。
- **配色**参考给定示例图：每个类别一种鲜亮主色，流带为同色半透明；左侧 CN/EN 用深色节点。app 名全部译为英文（如 微信→WeChat、爱奇艺→iQIYI、高德地图→Amap、网易云音乐→NetEase Music）。同时输出可交互的 `kb_sankey.html`。

---

## C. 指令词云（中/英，扩充集）

VagueBench 扩充集为双语：103 条 L1 中**中文 40 条、英文 63 条**。图 C.1 按语言各出一张词云，取自 **L1（最模糊、headline）指令**，裁剪为手机轮廓以呼应数据集总览图。

**本轮针对反馈的改进：**
1. **字体改细。** 由 Bold 改为 **Regular** 字重（中文 Noto Sans CJK Regular / 英文 DejaVu Sans Regular），笔画更轻。
2. **剔除实体名与 user 信息。** 在常规停用词之外，额外去除"个别指令的对象名/收件人名/占位符"——如 `xxoo`、`Kai Chen`、`Elon Musk`、`LeBron James`、`clock`、`zyy`、`rickandmorty` 等，以及"用户/agent"等元词；地名（广州、杭州、西溪等）作为任务内容保留。这样凸显的是**可复用的共享动作词汇**，而非一次性的 user 专属 token。

- **中文高频**：发给、推荐、购物车、查看、记录、添加、整理，及电影、餐厅、机票、航空公司、天气等对象。
- **英文高频**：email、cart、add、text、search、share、calendar、weather、note、record、shopping 等动作与对象。
- 结论：L1 表层以**开放式动作动词 + 具体对象**为主，**省略了 agent 必须自行推断的 app 与 UI 步骤**——这正是该基准刻意制造的"模糊性"。

---

## 复现方式

```bash
cd app-data/appendix
pip install wordcloud jieba plotly kaleido pandas   # matplotlib/numpy/PIL 已具备
plotly_get_chrome -y                                # kaleido 导出 PNG 需要

# 任务2：先对扩充集跑改写（调用 OpenRouter，约7分钟、~0.02美元），再统计
python3 ../../Mobile-Agent-E/instr_rewrite/instruction_rewrite_v2.py \
        --in ../Ins-bench/Vague-ins-expanded.json \
        --out ../Ins-bench/Vague-ins-expanded-rewritten-fresh.json
python3 rewrite_token_stats.py --in ../Ins-bench/Vague-ins-expanded-rewritten-fresh.json

python3 kb_sankey.py                  # → kb_sankey.png / .html（cn/en→8类→英文app）
python3 instruction_wordcloud.py      # → wordcloud_cn.png / wordcloud_en.png
```

LaTeX 编译：`appendix.tex` 因含 CJK（prompt 与词云段内联中文），请用 **XeLaTeX/LuaLaTeX** 编译，并加载 `fontspec + xeCJK`、`booktabs`、`graphicx`、`fancyvrb`、`tcolorbox`（详见文件头注释）。
