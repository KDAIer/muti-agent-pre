# 多智能体辩论(Multi-Agent Debate)实验代码

复现 Du et al. 2023 *Improving Factuality and Reasoning in Language Models through Multiagent Debate*,
在自部署 Qwen 上与 Single / CoT / Self-Consistency 对比,并实现 3 个改进(异质角色、裁判、置信度投票)+ 防从众提示、动态终止、agent 数量消融。

## 目录

```
debate/
  config.py    读取 .env(模型名 / 地址 / 密钥 / 是否开启思考模式)
  llm.py       chat() 封装:重试、token 与耗时统计、绕过本机代理
  data.py      数据抽样 → data/{gsm8k,math,mmlu}.jsonl
  tasks.py     各数据集的提示格式、答案解析、判分、投票
  methods.py   所有方法(Single / CoT / SC / Debate 及改进版)
  run.py       并发跑实验,逐题写 results/<dataset>/<method>.jsonl,可断点续跑
  analyze.py   汇总表、显著性检验、从众分析、案例、作图
run_all.sh     按优先级跑全套实验
third_party/llm_multiagent_debate   原论文官方代码(参考)
results/summary.md                  结果汇总(自动生成)
results_v1_max2048/                 第一版结果(输出上限 2048,存在截断偏差,仅作对照)
results/cases_<dataset>.md          典型辩论案例(从错改对 / 从对变错)
figures/                            图表
```

## 运行

```bash
python3 -m venv .venv && .venv/bin/pip install openai httpx pandas pyarrow matplotlib
.venv/bin/python -m debate.data                 # 生成抽样数据(已生成可跳过)
./run_all.sh                                    # 全套实验,可中断后重跑续上
.venv/bin/python -m debate.analyze              # 任何时候都可以基于已完成部分出表出图

# 单独跑某个方法 / 数据集
.venv/bin/python -m debate.run --dataset math --methods debate,roles --n 50 --workers 16
# 不调 API 的离线自测(假模型,只验证流水线)
MOCK=1 RESULTS_DIR=/tmp/mock .venv/bin/python -m debate.run --dataset gsm8k --n 10
```

模型配置在 `.env`(当前:`Qwen/Qwen3.8-27B` @ `http://172.18.162.10:8006/v1`,关闭思考模式,每次调用输出上限 `MAX_TOKENS=16384`)。

## 实验设置

| 数据集 | 样本 | 说明 |
|---|---|---|
| MATH-hard | 156 | MATH-500 中 Level 4–5 且答案为整数的全部题目(主实验,区分度最高) |
| GSM8K | 100 | 测试集固定种子(0)随机抽样;Qwen3.8 在其上接近饱和 |
| MMLU | 100 | 测试集全学科固定种子随机抽样(factuality) |

| 方法 | 调用次数/题 | 说明 |
|---|---|---|
| Single | 1 | 预填充 `The final answer is $\boxed{` 强制直答,不推理(temperature 0) |
| CoT | 1 | 逐步推理(temperature 0) |
| SC@3 / SC@6 | 3 / 6 | CoT 采样(temperature 0.7)多数投票 |
| Debate 3×R | 3R | 原论文提示的忠实复现,3 agent,R = 1/2/3 轮(一次 3 轮运行离线得到各轮结果) |
| +Judge | +1 | 改进:裁判 agent 读各辩手最终发言后裁决,替代多数投票 |
| Roles | 3R | 改进:异质角色(求解者 / 质疑者 / 验证者),并输出置信度 |
| AntiConf | 3R | 改进:同质辩手 + "不要盲从多数"约束,并输出置信度 |
| ConfVote | 0 | 改进:按置信度加权投票(用 Roles / AntiConf 的输出离线计算) |
| DynStop | ≤3R | 改进:某轮全员答案一致即停(离线精确模拟,后续轮不影响前面轮) |
| Debate 1×R / 5×R | R / 5R | agent 数量消融(1 agent 时退化为自我反思) |

指标:准确率(95% 正态近似 CI)、平均调用次数、平均 token(输入+输出)、调用耗时总和;方法间用精确 McNemar 检验。

## 与原论文代码的差异

- 原 `eval_gsm.py` 在无法解析答案时 `return 1`(记为答对),会虚高准确率;本实现记为答错。
- 原代码 MMLU 每次随机选学科文件、GSM8K 只取 100 题;本实现固定种子抽样,所有方法在同一批题上比较。
- Qwen3.8 在 GSM8K 上 CoT 已接近 100%(天花板效应),因此额外加入 MATH-hard 作为主实验,
  这本身也是一个发现:**任务越难,辩论的收益空间越大**。

## 输出长度上限与 v1 结果

第一版(`results_v1_max2048/`)每次调用输出上限为 2048 token,结果显示 MATH 上 Debate 3×3 = 95.5%,远超 CoT 76.3% / SC@6 81.4%。
复查发现这在很大程度上是**截断造成的偏差**:CoT / SC 约 21–24% 的调用被截断(还没写出答案就被判错),
而辩论后续轮次主要是核对他人解答、回复更短(截断率降到 8.8%),被截断的 agent 还能从别人的完整解答里"借到"答案。
把 33 道被截断的 CoT 题用 16k 上限重跑,其中 30 道答对(最长一题需 11.7k token)。
因此正式实验统一使用 `MAX_TOKENS=16384`;v1 结果可作为"低 token 预算下辩论对截断更鲁棒"的补充讨论。
另外,v1 的 Single 基线会无视"直答"指令自发推理,v2 改为预填充答案开头来强制直答。
