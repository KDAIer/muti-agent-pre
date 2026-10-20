"""所有对比方法:Single / CoT / Self-Consistency / 多智能体辩论(原版 + 改进版)。

每个方法输入一道题,返回一条可 JSON 序列化的记录(预测、逐轮预测、成本、对话记录)。
"""
from .llm import Usage, chat
from .tasks import Task, majority, parse_confidence

CONF_FMT = "On the last line, write 'Confidence: N' where N (0-100) is how confident you are that your final answer is correct."

# ---------------------------------------------------------------- 单模型基线

PREFILL = {"gsm8k": "The final answer is $\\boxed{", "math": "The final answer is $\\boxed{",
           "aime": "The final answer is $\\boxed{", "mmlu": "The answer is ("}


def single(task: Task, item):
    """直答基线:预填充答案开头,迫使模型不经推理直接给出答案。"""
    u = Usage()
    msg = [{"role": "user", "content": f"{task.question_text(item)}\n\n{task.fmt}"}]
    prefill = PREFILL[task.name]
    cont = chat(msg, u, temperature=0, max_tokens=32, prefill=prefill)
    close = ")" if task.name == "mmlu" else "}"
    out = prefill + cont.split(close)[0] + close   # 只取第一个答案,忽略之后的解释
    return {"pred": task.parse(out), "usage": u.to_dict(), "response": out}


def cot_prompt(task: Task, item):
    return (f"Can you solve the following problem? {task.question_text(item)}\n\n"
            f"Let's think step by step and explain your reasoning. {task.fmt}")


def cot(task: Task, item):
    u = Usage()
    out = chat([{"role": "user", "content": cot_prompt(task, item)}], u, temperature=0)
    return {"pred": task.parse(out), "usage": u.to_dict(), "response": out}


def self_consistency(task: Task, item, n=6):
    """采样 n 条 CoT 再多数投票;分析时取前 k 条即得 SC@k(k≤n)。"""
    preds, usages, outs = [], [], []
    for _ in range(n):
        u = Usage()
        out = chat([{"role": "user", "content": cot_prompt(task, item)}], u, temperature=0.7)
        preds.append(task.parse(out))
        usages.append(u.to_dict())
        outs.append(out)
    return {"pred": majority(preds), "preds": preds, "sample_usage": usages,
            "usage": _sum_usage(usages), "responses": outs}


# ---------------------------------------------------------------- 多智能体辩论

ROLES = [
    ("Solver", "You are a careful problem solver. Solve problems rigorously, step by step."),
    ("Skeptic", "You are a critical reviewer. Your job is to find mistakes: question every assumption and "
                "re-check every calculation, in your own work and in other agents' solutions."),
    ("Verifier", "You are a verifier. Solve the problem with an approach different from the obvious one if "
                 "possible, and verify the final answer by checking it against all conditions of the problem."),
]

ANTI_CONFORMITY = ("Note: other agents may be wrong, even if they agree with each other. Do not change your answer "
                   "just because it is the majority view. Change it only if you find a concrete error in your own "
                   "reasoning; adopt another answer only after verifying its reasoning step by step. ")


def _first_prompt(task: Task, item, style):
    p = (f"Can you solve the following problem? {task.question_text(item)}\n\n"
         f"Explain your reasoning. {task.fmt}")
    if style in ("roles", "anticonf"):
        p += " " + CONF_FMT
    return p


def _debate_prompt(task: Task, item, others, style):
    """原论文 construct_message 的忠实实现;others 为其他 agent 上一轮回答。"""
    if not others:  # 单 agent:退化为自我反思
        p = f"Can you double check that your answer is correct? Please reiterate your answer. {task.fmt}"
    else:
        p = "These are the solutions to the problem from other agents: "
        for a in others:
            p += f"\n\n One agent solution: ```{a}```"
        p += ("\n\n Using the solutions from other agents as additional information, can you provide an updated "
              f"answer? Examine your solution and those of other agents step by step. ")
        if style == "anticonf":
            p += ANTI_CONFORMITY
        if style == "roles":
            p += "Stay in your role. "
        p += f"The original problem is: {task.question_text(item)}\n {task.fmt}"
    if style in ("roles", "anticonf"):
        p += " " + CONF_FMT
    return p


def debate(task: Task, item, n_agents=3, n_rounds=3, style="orig", use_judge=True, use_judge_full=False):
    """style: orig(原版同质辩论) / roles(异质角色) / anticonf(防从众提示)。

    逐轮记录每个 agent 的预测、置信度和累计成本,
    因此 R 轮的一次运行即可离线得到 1..R 轮、以及动态终止的结果。
    """
    contexts = []
    for i in range(n_agents):
        ctx = []
        if style == "roles":
            ctx.append({"role": "system", "content": ROLES[i % len(ROLES)][1]})
        ctx.append({"role": "user", "content": _first_prompt(task, item, style)})
        contexts.append(ctx)

    u = Usage()
    rounds = []
    last = []
    for r in range(n_rounds):
        if r > 0:
            for i, ctx in enumerate(contexts):
                others = last[:i] + last[i + 1:]
                ctx.append({"role": "user", "content": _debate_prompt(task, item, others, style)})
        outs = []
        for ctx in contexts:
            out = chat(ctx, u, temperature=0.7)
            ctx.append({"role": "assistant", "content": out})
            outs.append(out)
        last = outs
        preds = [task.parse(o) for o in outs]
        rounds.append({"preds": preds, "confs": [parse_confidence(o) for o in outs],
                       "majority": majority(preds), "usage": u.to_dict(), "responses": outs})

    rec = {"pred": rounds[-1]["majority"], "rounds": rounds, "usage": u.to_dict(),
           "roles": [ROLES[i % len(ROLES)][0] for i in range(n_agents)] if style == "roles" else None}
    if use_judge and n_agents > 1:
        rec["judge"] = judge(task, item, last)
    if use_judge_full and n_agents > 1:   # 实验性的完整记录裁判,默认关闭,未纳入本次实验
        rec["judge_full"] = judge_full(task, item, [rd["responses"] for rd in rounds])
    return rec


def judge(task: Task, item, final_answers):
    """裁判 agent:读完各辩手最终发言后独立裁决,替代多数投票。"""
    u = Usage()
    p = f"You are the judge of a debate among {len(final_answers)} agents on the following problem:\n\n" \
        f"{task.question_text(item)}\n\n"
    for i, a in enumerate(final_answers):
        p += f"[Agent {i + 1}'s final solution]\n{a}\n\n"
    p += ("Carefully evaluate the reasoning of each agent, identify any errors, and decide which answer is "
          "correct. Do not simply count votes: the majority can be wrong. You may also derive the answer "
          f"yourself if all agents are wrong. {task.fmt}")
    out = chat([{"role": "user", "content": p}], u, temperature=0)
    return {"pred": task.parse(out), "usage": u.to_dict(), "response": out}


def judge_full(task: Task, item, round_responses):
    """实验性(未纳入本次实验):裁判 agent 完整版:读完整场辩论记录(每轮每个辩手的发言)后做总结裁决。

    round_responses: [[第 1 轮各 agent 回答], [第 2 轮 ...], ...],可只传前 k 轮,得到"k 轮后裁决"。
    与 judge() 的区别:能看到立场如何演变——有理有据的改判是强证据,无理由地向多数靠拢是弱证据。
    """
    u = Usage()
    n_agents, n_rounds = len(round_responses[0]), len(round_responses)
    if n_rounds == 1:
        p = f"You are an impartial judge. {n_agents} agents independently solved the following problem.\n\n"
    else:
        p = (f"You are an impartial judge. {n_agents} agents debated the following problem over {n_rounds} rounds. "
             "In round 1 each agent solved it independently; in each later round every agent read the others' "
             "previous answers and gave an updated answer.\n\n")
    p += f"Problem: {task.question_text(item)}\n\n"
    for k, outs in enumerate(round_responses):
        if n_rounds > 1:
            p += f"=== Round {k + 1} ===\n\n"
        for i, a in enumerate(outs):
            p += f"[Agent {i + 1}]\n{a}\n\n"
    p += "=== Your verdict ===\n"
    p += "1. List the distinct final answers proposed, and check the key steps of the reasoning behind each for errors.\n"
    if n_rounds > 1:
        p += ("2. Consider how positions changed across rounds: an agent switching answers because it found a "
              "concrete error is strong evidence; switching to the majority without identifying any error is weak "
              "evidence.\n")
    p += ("Do not decide by counting votes: the majority can be wrong. If every agent is wrong, solve the problem "
          f"yourself. Give a concise justification, then state the verdict. {task.fmt}")
    out = chat([{"role": "user", "content": p}], u, temperature=0)
    return {"pred": task.parse(out), "usage": u.to_dict(), "response": out}


def _sum_usage(us):
    keys = ["calls", "prompt_tokens", "completion_tokens", "total_tokens", "latency", "truncated"]
    return {k: round(sum(x.get(k, 0) for x in us), 2) for k in keys}


METHODS = {
    "single": single,
    "cot": cot,
    "sc": self_consistency,
    "debate": lambda t, it: debate(t, it, 3, 3, "orig"),
    "roles": lambda t, it: debate(t, it, 3, 3, "roles"),
    "anticonf": lambda t, it: debate(t, it, 3, 3, "anticonf"),
    # agent 数量消融
    "debate_a1": lambda t, it: debate(t, it, 1, 3, "orig", use_judge=False),
    "debate_a5": lambda t, it: debate(t, it, 5, 3, "orig", use_judge=False),
}
