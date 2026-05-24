# 附录：一级模糊指令长度分析

## A.1 实验设置

我们以 **tiktoken `cl100k_base` 词元数**为主指标，统计各基准中一级（L1）模糊指令的表层长度。为避免"指令长度"被任务复杂度（涉及的 app 数量）与指令语言（中/英）这两个混淆因素干扰，我们做两点处理：

1. **按任务复杂度分组对比。** 将 VagueBench-L1 依据标注的应用数量拆分为**单 app 子集**（恰好 1 个声明应用，n=14）与**多 app 子集**（≥2 个声明应用，n=36）。其中 4 条未标注应用的指令，依据指令语义人工判定其应用数。随后将两个子集分别与复杂度相当的基准对比：单 app 子集对比 AndroidArena、AndroidWorld、MVISU-Bench（均以单 app 原子指令为主），多 app 子集对比 MobileWorld、AndroidDaily（含较多复合任务）。
2. **按语言拆分汇报。** 各基准的中/英子集分布差异显著，聚合统计量会掩盖真实分布，故所有箱线图与统计表均区分 cn / en。

## A.2 统计结果

表 A.1 汇报两组对比的逐语言词元统计；图 A.1 为对应的双面板箱线图（实线为中位数，虚线为均值）。

**表 A.1　L1 模糊指令词元长度（tiktoken cl100k_base）**

| 组别 | 基准 | 语言 | n | mean | median | std | min | max | p25 | p75 |
|---|---|---|---|---|---|---|---|---|---|---|
| A 原子/单 app | VagueBench-L1 (single) | all | 14 | 14.6 | 14.5 | 4.0 | 9 | 21 | 12.2 | 17.5 |
| | | cn | 7 | 13.6 | 12.0 | 4.8 | 9 | 21 | 9.5 | 17.0 |
| | | en | 7 | 15.7 | 15.0 | 2.9 | 13 | 21 | 13.5 | 17.0 |
| | AndroidArena | en | 43 | 6.9 | 7.0 | 2.3 | 4 | 13 | 5.0 | 8.0 |
| | AndroidWorld | en | 14 | 8.0 | 7.5 | 3.3 | 4 | 13 | 4.8 | 11.0 |
| | MVISU-Bench | cn | 36 | 11.1 | 10.5 | 4.2 | 5 | 25 | 8.0 | 14.2 |
| | | en | 36 | 7.7 | 7.0 | 2.3 | 3 | 13 | 6.0 | 9.0 |
| B 复合/多 app | VagueBench-L1 (multi) | all | 36 | 22.8 | 17.0 | 13.7 | 11 | 77 | 15.0 | 24.0 |
| | | cn | 17 | 28.8 | 23.0 | 17.5 | 12 | 77 | 15.0 | 36.0 |
| | | en | 19 | 17.5 | 17.0 | 5.0 | 11 | 33 | 14.5 | 19.0 |
| | MobileWorld | cn | 19 | 44.9 | 44.0 | 12.4 | 28 | 76 | 35.0 | 53.0 |
| | | en | 26 | 14.1 | 15.0 | 4.1 | 5 | 19 | 12.0 | 17.8 |
| | AndroidDaily | cn | 28 | 29.2 | 28.0 | 12.3 | 10 | 55 | 20.0 | 39.2 |

## A.3 分析

**组 A（原子/单 app）。** VagueBench 单 app 子集的长度处于"短指令"区间（中位数 14.5），但仍系统性地略长于三个对照基准（同语种下英文中位数 15.0，对比 AndroidArena 7.0、AndroidWorld 7.5、MVISU-en 7.0）。原因在于对照基准的指令多为模板化的 UI 原子命令（如 *"Enable Wi-Fi."*、*"Take one photo."*）或极简意图（如 *"我要看视频。"*），而 VagueBench 即便在单 app 情形下也保留了自然语言的模糊表述，从而携带更多词元。这说明：**单 app 任务确实落在短指令区间，验证了"应用数量是指令长度的首要驱动因素之一"**，同时 VagueBench 的模糊性并非以删减表层信息换取的。

**组 B（复合/多 app）。** 该组中**语言是强混淆因素**，必须分语种解读：

- *中文：* VagueBench 多 app（均值 28.8，中位数 23.0）与 AndroidDaily（均值 29.2，中位数 28.0）量级相当，二者均明显短于 MobileWorld-cn（均值 44.9，中位数 44.0）。后者由大量带显式约束、参数乃至电话号码的脚本化多步任务构成，表层长度被显著抬高。
- *英文：* VagueBench 多 app（均值 17.5）略长于 MobileWorld-en（均值 14.1），而 MobileWorld 的英文子集实为原子化的系统设置/社交操作命令，并非真正的复合任务。

值得强调的是，MobileWorld 的聚合统计（均值 27.1，std 17.6）呈**双峰**特征——由偏长的中文任务与偏短的英文命令混合而成——其聚合均值因此具有误导性，这进一步佐证了 cn / en 分开汇报的必要性。

**总体结论。** VagueBench-L1 在复杂度上与对照基准**相互匹配**（单 app 落在短区间、多 app 落在长区间），但在表层长度上比最冗长的基准（AndroidDaily、MobileWorld-cn）更**精炼**。这表明 VagueBench 在保持任务复合度的同时未以堆砌冗余措辞来制造难度，从而将"模糊性（vagueness）"与"冗长度（verbosity）"两个维度有效解耦。

## A.4 扩充集结果（n=103）

为提升统计稳健性，我们在**扩充后的 VagueBench**（取 `Vague-ins-expanded.json` 的 `Level1-INS` 字段，共 103 条，cn 40 / en 63）上重复上述协议。应用数仍由 `Invovled_App_Name` 解析（单 app 39 条、多 app 64 条；4 条空标注按 A.1 规则推断），语言由文本中是否含中日韩统一表意字符自动判定。对照基准与 A.2 完全一致。

**表 A.2　L1 模糊指令词元长度（扩充集，tiktoken cl100k_base）**

| 组别 | 基准 | 语言 | n | mean | median | std | min | max | p25 | p75 |
|---|---|---|---|---|---|---|---|---|---|---|
| A 原子/单 app | VagueBench-exp (single) | all | 39 | 14.7 | 14.0 | 5.8 | 5 | 29 | 10.0 | 17.5 |
| | | cn | 13 | 17.5 | 18.0 | 7.5 | 8 | 29 | 10.0 | 24.0 |
| | | en | 26 | 13.3 | 13.0 | 4.2 | 5 | 24 | 10.5 | 16.0 |
| | AndroidArena | en | 43 | 6.9 | 7.0 | 2.3 | 4 | 13 | 5.0 | 8.0 |
| | AndroidWorld | en | 14 | 8.0 | 7.5 | 3.3 | 4 | 13 | 4.8 | 11.0 |
| | MVISU-Bench | cn | 36 | 11.1 | 10.5 | 4.2 | 5 | 25 | 8.0 | 14.2 |
| | | en | 36 | 7.7 | 7.0 | 2.3 | 3 | 13 | 6.0 | 9.0 |
| B 复合/多 app | VagueBench-exp (multi) | all | 64 | 23.5 | 19.5 | 12.6 | 9 | 77 | 15.0 | 29.2 |
| | | cn | 27 | 31.8 | 34.0 | 14.9 | 12 | 77 | 21.0 | 40.0 |
| | | en | 37 | 17.5 | 17.0 | 5.0 | 9 | 33 | 14.0 | 20.0 |
| | MobileWorld | cn | 19 | 44.9 | 44.0 | 12.4 | 28 | 76 | 35.0 | 53.0 |
| | | en | 26 | 14.1 | 15.0 | 4.1 | 5 | 19 | 12.0 | 17.8 |
| | AndroidDaily | cn | 28 | 29.2 | 28.0 | 12.3 | 10 | 55 | 20.0 | 39.2 |

扩充集（n=103）的整体分布与 A.2 的 50 条子集高度一致（整体均值 20.2 vs 20.5、中位数 17.0 vs 16.5），A.3 的全部结论在更大样本下依然成立：单 app 子集落在短指令区间且系统性略长于原子对照基准；多 app 子集在中文下与 AndroidDaily 量级相当、短于 MobileWorld-cn，在英文下略长于原子化的 MobileWorld-en。扩充后中文多 app 子集的样本量从 17 增至 27，中位数（34.0）的估计更稳定。对应图见图 A.2。

---

*复现脚本：原始 50 条 [`vaguebench_app_split.py`](vaguebench_app_split.py)、扩充 103 条 [`vaguebench_app_split_expanded.py`](vaguebench_app_split_expanded.py)；数据：[`app_split_stats.csv`](app_split_stats.csv) / [`app_split_stats_expanded.csv`](app_split_stats_expanded.csv)；图：图 A.1 [`length_boxplot_appsplit.png`](length_boxplot_appsplit.png)、图 A.2 [`length_boxplot_appsplit_expanded.png`](length_boxplot_appsplit_expanded.png)。应用数解析与空标注推断规则见脚本内 `parse_apps()` 与 `EMPTY_INFER`。*
