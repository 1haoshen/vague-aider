# 附录：用户研究（User Study）——用户友好性、模糊性与指令习惯

> 配套素材：问卷英文翻译见本文 §C.5；原始数据 [`survey_results.csv`](survey_results.csv)；复现脚本 [`plot_survey.py`](plot_survey.py)；图 [`fig_survey_problems.png`](fig_survey_problems.png)、[`fig_survey_spectrum.png`](fig_survey_spectrum.png)。

## C.1 动机与设计

VagueAider 的核心命题是：**真实用户以"用户友好型的模糊意图"（user-friendly vague intent）表达需求，而 Agent 需要的是"Agent 友好型的可执行指令"（agent-friendly executable instruction），二者之间存在语义鸿沟（semantic gap）。** 为了验证这一命题并非基准构造产物、而是用户真实感受到的痛点，我们发放了一份关于"手机 AI 助手使用习惯与指令习惯"的问卷，共回收 **28 份有效问卷（n = 28）**，含 7 道题（2 道背景题、2 道多选诊断题、3 道单选的指令粒度题）。

### 两个关键定义

- **用户友好性（user-friendliness）：** 指令贴近人类自然表达的程度——用户只需付出最小的措辞/认知成本即可发出请求。用户友好性高的指令往往**只陈述最终目标**，把"用哪个 App、点哪一步"的推断交给系统（例：*"帮我买个最便宜的 Switch 摇杆。"*）。
- **Agent 友好性（agent-friendliness）：** 指令对 Agent 可直接执行的程度——显式给出目标 App、原子级 UI 步骤，无需任何推断（例：*"打开淘宝，点击搜索框，输入 Switch 摇杆，按价格升序排序，选第一个……"*）。

二者构成一条连续轴。VagueBench 据此把模糊性划分为三级（数据集定义）：

| 等级 | 名称 | 缺失信息 | 示例 |
|---|---|---|---|
| **L1** | Implicit App | 操作明确，但未指定 App | "Order a spicy pizza." |
| **L2** | Implicit Op | 指定了 App，但未给出操作步骤 | "Use Uber to go to the airport." |
| **L3** | Fully Vague | 仅表达核心需求 | "I want to watch a movie." |

问卷第 5 题用同一个"选购性价比电子产品"的任务把这条轴**实例化**为三种表达：A=用户友好型（只说模糊目标）、B=中间档（点名 App 比价、但把搜索/筛选/下单等操作交给 Agent）、C=Agent 友好型（精确到每一次点击）。第 6、7 题则进一步追问"Agent 友好型表达是否符合人类习惯"。

## C.2 样本背景（Q1–Q2）

- **使用频率（Q1）：** 每周若干次 46.4%（13）、每天多次 21.4%（6）、每天 1–2 次 7.1%（2）、几乎从不 25.0%（7）。样本覆盖了高频与低频用户，非单一极端人群。
- **对下一代 Agent 的认知（Q2）：** 64.3%（18）"听说过但未深入使用"，17.9%（5）"经常关注/体验过"，17.9%（5）"完全不了解"。即多数受访者**了解"直接代操作屏幕"这一概念但尚未被现有产品的交互范式固化**，因此其偏好更多反映对"理想 Agent"的期待，而非对某款现有工具的习惯性迁就。

## C.3 痛点与期待：问题被用户证实（Q3, Q4）

图 C.1（[`fig_survey_problems.png`](fig_survey_problems.png)）并列展示了现有助手的痛点（Q3，多选）与对未来 Agent 的核心期待（Q4，多选）。

**Q3 痛点排序的前两位，恰好是 VagueAider 所针对的两类能力缺口：**

- **无法完成跨 App 复杂任务 71.4%（20）** —— 排名第一；
- **无法理解抽象想法、必须像指挥机器人一样逐步下达死板指令 64.3%（18）** —— 排名第二。

二者均显著高于"执行慢/反应迟钝"（28.6%）、"耗电/占资源"（32.1%），甚至高于"隐私安全"（42.9%）。也就是说，用户最大的不满并非性能或安全，而是**助手"听不懂模糊话、做不了跨 App"**。

**Q4 期待排序与 Q3 互为镜像：**

- **丝滑的跨 App 协同 82.1%（23）** —— 排名第一；
- **超强的抽象指令理解力（"我饿了"→自动挑选并操作合适 App）64.3%（18）** —— 与"严格的隐私/凭证安全"（64.3%）并列第二。

> **结论 1（问题真实性）：** 跨 App 协同与抽象意图理解，既是用户当下最大的痛点（Q3 第 1、2 名），又是用户对未来最强的诉求（Q4 第 1、2 名）。这正是 VagueAider"意图扩展 + 计划精炼"两阶段所要补齐的语义信息，说明 VagueBench 所刻画的模糊性问题是**用户真实感知到的**，而非人为设定。

## C.4 指令粒度偏好：用户友好 ↔ Agent 友好（Q5–Q7）

图 C.2（[`fig_survey_spectrum.png`](fig_survey_spectrum.png)）把 Q5/Q6/Q7 统一投影到同一条"用户友好 ↔ Agent 友好"的立场轴上：绿色=最偏用户友好（陈述模糊意图、期待 Agent 弥合鸿沟），灰色=中间档（给出部分信息、但仍把操作交给 Agent），红色=最偏 Agent 友好（愿意把每个 App 和点击都说清楚）。虚线标出"**不**给出全显式指令"的人群占比。

- **Q5 表达粒度（注意解读方式）：** 题目设定"让助手选购一款性价比高的电子产品（如头戴耳机/Switch 手柄），日常最贴合习惯、最自然顺口的表述是哪种"。三档分布为——用户友好型（A，只说模糊目标，如"帮我选一款性价比高、最实惠的手柄"）32.1%（9）、中间档（B，点名淘宝/京东比价、但把搜索/筛选/下单的操作留给 Agent）50.0%（14）、Agent 友好型（C，精确到每一步点击）仅 17.9%（5）。**这里关键的不是把三档当作"满意度排名"。** 首先，中间档对应的正是**现有 benchmark 常见的指令形式**（点名 App、却不给操作细节），而**恰有约 50%（A+C=14 人）的受访者并未选它**——即约一半的人不把这种 benchmark 式指令当作自己更倾向输入的表达。其次，在这"偏离 benchmark 式"的一半人中，倒向**更模糊、更 user-friendly**一端（A，32.1%）的人数接近倒向**更显式**一端（C，17.9%）的 **1.8 倍**：唯一具有明显拉力的方向是朝向用户友好，而非朝向显式化。最后，从论文动机最关心的分界看，**{A,B} 合计 82.1% 都把"操作"留给了 Agent 去补全（指令在 App 或操作维度上欠定）**，只有 **{C} 17.9%** 给出了可被 Agent 直接执行的全显式指令——换言之，连"中间档"本身相对 Agent 的执行需求都是欠定的。
  > ⚠️ **方法学说明：** 三点量表的"中间档"天然吸纳折中选择（central-tendency bias），且 Q5 以"最习惯/最自然顺口"为锚点，测到的是受访者**在现有受限 Agent 约束下的保守行为**，会**低估**其真实的 user-friendly 期望。因此我们不据 Q5 断言"benchmark 式最受欢迎"，而是结合 Q6/Q7 与上述偏移方向，得出"用户更想用 user-friendly 指令"的结论。
- **Q6 保姆级指令是否符合习惯：** "完全不符合，太繁琐"50.0%（14）、"部分符合，仅在极复杂/系统易错时才多解释"39.3%（11）、"完全符合，应提供所有严谨细节"仅 10.7%（3）。即 **89.3% 不把 Agent 友好型表达当作默认**。
- **Q7 如何评价"必须逐步告知"的 Agent：** "不够聪明，语义鸿沟太大，违背智能初衷"50.0%（14）、"可以接受，是当前技术上限"39.3%（11）、"挺好，喜欢完全掌控执行路径"仅 10.7%（3）。即 **89.3% 不满足于一个需要全显式步骤的 Agent。**

> **结论 2（鸿沟真实性与方向）：** 三道题一致显示，仅约 **11%–18%** 的用户会主动给出 Agent 友好型的全显式指令；**约 89% 的用户既不以全显式表达为习惯（Q6），也不接受一个强迫他们这样做的 Agent（Q7）**，且 Q5 中约半数受访者并不把 benchmark 式的中间粒度当作首选、其偏移明显倒向更 user-friendly 的一端。综合来看，用户的自然落点在轴的"用户友好"一端，而 Agent 的可执行需求在"Agent 友好"一端——语义鸿沟由此被双向证实。**这恰好印证研究动机：现有 benchmark 所采用的指令粒度对用户并不够友好，用户期待的是比之更模糊、更接近自然意图的表达。**

> **结论 3（对设计的启示）：** Q6/Q7 中约 **39%** 的"有条件/可接受"人群表明：用户愿意把显式化作为**复杂或易错场景下的回退手段**，但仍将其视为智能不足的表现。因此正确的设计目标不是要求用户写得更清楚，而是**由系统自动把模糊意图扩展为可执行计划、把所需显式化降到最低**——这正是 VagueAider 的定位。

## C.5 问卷英文翻译（附录用）

> 原问卷为中文；以下为问卷英文版，**仅列题干与选项**（问卷原件不含统计）。各选项占比见正文 §C.2–C.4 与图 C.1 / C.2，原始计数见 [`survey_results.csv`](survey_results.csv)；多选题已标注 (multi-select)。

**Title:** *Survey on Smartphone AI-Assistant (Mobile Agent) Usage and Instruction Habits*

**Q1 (single).** How often do you use a phone AI assistant (e.g. Siri, Google Assistant, Doubao assistant)?

- A. Multiple times a day
- B. 1–2 times a day
- C. Several times a week
- D. Almost never

**Q2 (single).** Have you tried or heard of next-generation phone Agent systems that "directly operate the screen/apps for you" (auto-tap, swipe, cross-app food ordering or ticketing; e.g. the Doubao AI phone)?

- A. Yes — I often follow or have tried such cutting-edge features
- B. I've heard of it, but never used it in depth
- C. Completely unaware

**Q3 (multi-select).** When using today's phone assistants, what frustrates or dissatisfies you most?

- A. Slow execution, sluggish response
- B. Cannot understand complex abstract ideas; I must command it like a robot, spelling out every rigid, concrete step
- C. Cannot complete complex cross-app tasks (e.g. it can't "check flights for me and create the trip as a calendar notification")
- D. Drains the battery fast or consumes heavy system resources
- E. Privacy and account/password security cannot be guaranteed
- F. Overall satisfied; no obvious inconvenience

**Q4 (multi-select).** In a future phone Agent system, which core capabilities do you most look forward to?

- A. Strong abstract-instruction understanding: I only state a vague final goal (e.g. "I'm hungry") and it automatically picks and operates the right app
- B. Smooth cross-app coordination (e.g. extract an address from a WeChat chat → navigate in Maps → sync to the car head-unit)
- C. Strict privacy and account-credential security protection
- D. Very fast response and low system-resource consumption
- E. Other

**Q5 (single).** To get an AI assistant to help you pick a good-value electronics item (e.g. a headset), which way of phrasing the request best fits your habits and feels most natural in everyday use?

- A. "Help me pick a good-value Switch controller — the most affordable one." (state the goal only; the assistant chooses the apps and does the comparison)
- B. "Check the Switch-controller price on Taobao and JD, compare the prices, and pick a relatively cheap one." (names the apps, but leaves the searching, filtering and checkout to the assistant)
- C. "Open Taobao, tap the search box, type 'Switch controller', sort by price low-to-high, select the first item; then open JD and repeat, compare, and stay on the payment page of whichever is cheaper." (every app and tap spelled out)

**Q6 (single).** Following Q5: do you think requiring users to give option-C-style "babysitter-level instructions, precise to every app and click" in daily life matches how humans really use such tools?

- A. Doesn't match at all. It's far too tedious — if I had to spell out that much, I'd rather just tap it myself.
- B. Partially matches. Only for extremely complex tasks, or when the system keeps making mistakes, would I bother explaining more.
- C. Fully matches. I think talking to an AI should mean providing all the rigorous operation details.

**Q7 (single).** If a phone Agent cannot understand your vague intent (e.g. "I want an iced americano") and instead needs you to manually tell it "open Meituan → select Starbucks → choose iced americano → place order", how would you rate this Agent?

- A. Not smart enough — the semantic gap is too large; this betrays the very purpose of "intelligence".
- B. Acceptable — current technology may only be able to go this far.
- C. Pretty good — I like having full control over its execution path.

## C.6 局限性

本研究为**动机性证据**而非有统计功效的实验：(1) 样本为便利抽样，n = 28，规模小；(2) 测量的是**陈述偏好**而非真实行为；(3) 单一 7 题量表、以中文语境受访者为主，可能存在文化与语言偏置。因此我们将其定位为对 VagueBench 模糊性分级与 VagueAider 设计取向的**用户侧佐证**，而非充分性证明。

---

*图 C.1 = [`fig_survey_problems.png`](fig_survey_problems.png)；图 C.2 = [`fig_survey_spectrum.png`](fig_survey_spectrum.png)。重跑：`python app-data/UserStudy/plot_survey.py`。LaTeX 版本（含可直接编译的图表与附录问卷）见 [`user_study.tex`](user_study.tex)。*
