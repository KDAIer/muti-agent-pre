"""汇总实验结果:主对比表、轮数/agent 数消融、动态终止、从众分析、案例抽取与作图。

用法: python -m debate.analyze   → 生成 results/summary.md、results/cases_<dataset>.md、figures/*.png
"""
import json
import math
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .config import DATA_DIR, FIG_DIR, RESULTS_DIR
from .tasks import TASKS, majority, weighted_vote

# 参考调色板(dataviz skill references/palette.md,浅色模式,按固定顺序取色)
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
    "font.sans-serif": ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
})


def load(dataset, method):
    p = RESULTS_DIR / dataset / f"{method}.jsonl"
    if not p.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, open(p, encoding="utf-8")) if r}


def load_judges(dataset):
    """读取 add_judge.py 生成的离线裁判结果:{method: {kind: {id: rec}}}。"""
    J = {}
    for m in ("debate", "roles", "anticonf"):
        p = RESULTS_DIR / dataset / f"judge_{m}.jsonl"
        if p.exists():
            for r in map(json.loads, open(p, encoding="utf-8")):
                J.setdefault(m, {}).setdefault(r["kind"], {})[r["id"]] = r
    return J


def _judge_full(R, J, k, n_rounds):
    """读前 k 轮完整记录的裁判结果;只有覆盖该方法全部题目时才返回,避免部分结果缩小主表的公共题集。"""
    got = dict(J.get(f"full_r{k}", {}))
    if k == n_rounds:   # 新代码跑辩论时会把 judge_full 直接写进记录
        got.update({i: r["judge_full"] for i, r in R.items() if "judge_full" in r})
    return got if set(R) <= set(got) else {}


# ---------------------------------------------------------------- 由原始记录派生各"变体"的 (pred, cost)

def variants(dataset, recs, judges=None):
    """返回 {变体名: {id: (pred, usage)}};辩论的轮数/动态终止/裁判/置信度投票都离线派生。"""
    judges = judges or {}
    V = {}
    add = lambda name, d: V.__setitem__(name, d) if d else None
    add("Single", {i: (r["pred"], r["usage"]) for i, r in recs.get("single", {}).items()})
    add("CoT", {i: (r["pred"], r["usage"]) for i, r in recs.get("cot", {}).items()})
    sc = recs.get("sc", {})
    for k in (3, 6):
        add(f"SC@{k}", {i: (majority(r["preds"][:k]), _sum(r["sample_usage"][:k])) for i, r in sc.items()})

    labels = {"debate": "Debate", "roles": "Roles", "anticonf": "AntiConf"}
    for m, lab in labels.items():
        R = recs.get(m, {})
        if not R:
            continue
        n_rounds = len(next(iter(R.values()))["rounds"])
        for k in range(1, n_rounds + 1):
            add(f"{lab} 3x{k}", {i: (r["rounds"][k - 1]["majority"], r["rounds"][k - 1]["usage"]) for i, r in R.items()})
        # 裁判:+Judge 读各辩手最终发言后裁决;+JudgeFull(实验性,默认不跑)读前 k 轮完整记录。成本 = 前 k 轮辩论 + 裁判调用
        add(f"{lab} 3x{n_rounds} +Judge",
            {i: (r["judge"]["pred"], _sum([r["usage"], r["judge"]["usage"]])) for i, r in R.items() if "judge" in r})
        for k in range(1, n_rounds + 1):
            jf = _judge_full(R, judges.get(m, {}), k, n_rounds)
            add(f"{lab} 3x{k} +JudgeFull",
                {i: (j["pred"], _sum([R[i]["rounds"][k - 1]["usage"], j["usage"]])) for i, j in jf.items() if i in R})
        if m != "debate":
            add(f"{lab} 3x{n_rounds} ConfVote",
                {i: (weighted_vote(r["rounds"][-1]["preds"], r["rounds"][-1]["confs"]), r["usage"]) for i, r in R.items()})
        add(f"{lab} DynStop", {i: _dyn_stop(r) for i, r in R.items()})

    for m, n in (("debate_a1", 1), ("debate_a5", 5)):
        R = recs.get(m, {})
        if R:
            n_rounds = len(next(iter(R.values()))["rounds"])
            for k in range(1, n_rounds + 1):
                add(f"Debate {n}x{k}", {i: (r["rounds"][k - 1]["majority"], r["rounds"][k - 1]["usage"]) for i, r in R.items()})
    return V


def _dyn_stop(r):
    """动态终止:某轮所有 agent 答案一致即停,取该轮答案与截至该轮的成本。"""
    for rd in r["rounds"]:
        p = rd["preds"]
        if p[0] is not None and all(x == p[0] for x in p):
            return p[0], rd["usage"]
    return r["rounds"][-1]["majority"], r["rounds"][-1]["usage"]


def _sum(us):
    keys = ["calls", "prompt_tokens", "completion_tokens", "total_tokens", "latency", "truncated"]
    return {k: sum(u.get(k, 0) for u in us) for k in keys}


# ---------------------------------------------------------------- 统计

def score(task, var, gts, ids):
    c = [task.correct(var[i][0], gts[i]) for i in ids]
    n = len(c)
    acc = sum(c) / n
    se = math.sqrt(acc * (1 - acc) / n)
    mean = lambda k: sum(var[i][1][k] for i in ids) / n
    calls = sum(var[i][1]["calls"] for i in ids)
    trunc = sum(var[i][1].get("truncated", 0) for i in ids) / calls if calls else 0
    return {"acc": acc, "ci": 1.96 * se, "calls": mean("calls"), "tokens": mean("total_tokens"), "trunc": trunc,
            "out_tokens": mean("completion_tokens"), "latency": mean("latency"), "vec": c}


def mcnemar(a, b):
    """精确 McNemar 检验(双侧),a/b 为同一批题的对错向量。"""
    b01 = sum(1 for x, y in zip(a, b) if not x and y)
    b10 = sum(1 for x, y in zip(a, b) if x and not y)
    n = b01 + b10
    if n == 0:
        return b01, b10, 1.0
    k = min(b01, b10)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return b01, b10, min(p, 1.0)


def transitions(task, R, gts):
    """逐轮统计每个 agent 的答案迁移:错→对 / 对→错 / 改了答案的比例 —— 用于分析"从众"。"""
    rows = []
    n_rounds = len(next(iter(R.values()))["rounds"])
    for k in range(1, n_rounds):
        w2r = r2w = changed = total = 0
        for i, r in R.items():
            a, b = r["rounds"][k - 1]["preds"], r["rounds"][k]["preds"]
            for x, y in zip(a, b):
                total += 1
                cx, cy = task.correct(x, gts[i]), task.correct(y, gts[i])
                w2r += (not cx) and cy
                r2w += cx and not cy
                changed += x != y
        rows.append({"from": k, "to": k + 1, "w2r": w2r, "r2w": r2w, "changed": changed / total, "total": total})
    return rows


def consensus_stats(task, R, gts):
    """最终轮一致率,以及"一致但错"(集体从众到错误答案)的题数。"""
    unanimous = wrong_unanimous = minority_right_lost = 0
    for i, r in R.items():
        rd0, rd = r["rounds"][0], r["rounds"][-1]
        p = rd["preds"]
        if p[0] is not None and all(x == p[0] for x in p):
            unanimous += 1
            wrong_unanimous += not task.correct(p[0], gts[i])
        # 首轮有人答对、最终多数却错了:正确的少数派被说服
        if any(task.correct(x, gts[i]) for x in rd0["preds"]) and not task.correct(rd["majority"], gts[i]):
            minority_right_lost += 1
    n = len(R)
    return {"unanimous": unanimous / n, "wrong_unanimous": wrong_unanimous, "minority_right_lost": minority_right_lost}


# ---------------------------------------------------------------- 作图

def _place_labels(ax, pts, fontsize=7.5):
    """简单的贪心防重叠:标签默认放在点右上,与已放标签重叠时向下错位。"""
    fig = ax.figure
    fig.canvas.draw()
    placed = []
    for x, y, text in sorted(pts, key=lambda p: -p[1]):
        for dy in (4, -10, 14, -20, 24, -30, 34, -40):
            t = ax.annotate(text, (x, y), xytext=(6, dy), textcoords="offset points", fontsize=fontsize, color=INK2)
            bb = t.get_window_extent(fig.canvas.get_renderer()).expanded(1.05, 1.15)
            if not any(bb.overlaps(o) for o in placed):
                placed.append(bb)
                break
            t.remove()
        else:
            placed.append(ax.annotate(text, (x, y), xytext=(6, 4), textcoords="offset points",
                                      fontsize=fontsize, color=INK2).get_window_extent(fig.canvas.get_renderer()))


# 只画关键点,完整数字见表格;Single 准确率过低会压扁纵轴,不画
TRADEOFF_POINTS = ["CoT", "SC@3", "SC@6", "Debate 3x2", "Debate 3x3", "Debate DynStop",
                   "Debate 3x1 +JudgeFull", "Debate 3x3 +JudgeFull",
                   "Roles 3x3 ConfVote", "AntiConf DynStop"]


def fig_tradeoff(dataset, S, order):
    fig, ax = plt.subplots(figsize=(8, 5))
    improved = lambda n: n.startswith(("Roles", "AntiConf")) or "+Judge" in n or "DynStop" in n
    fams = (("单模型基线", C1, lambda n: n in ("Single", "CoT") or n.startswith("SC")),
            ("原版辩论", C2, lambda n: n.startswith("Debate") and not improved(n)),
            ("改进版辩论", C3, improved))
    color = lambda n: next(c for _, c, f in fams if f(n))
    pts = [n for n in TRADEOFF_POINTS if n in S]
    for n in pts:
        s = S[n]
        ax.errorbar(s["tokens"], s["acc"] * 100, yerr=s["ci"] * 100, fmt="o", ms=7, color=color(n),
                    ecolor=color(n), elinewidth=1, alpha=0.9, capsize=0, mec="white", mew=1.5, zorder=3)
    ax.set_xscale("log")
    ax.set_xlabel("平均每题 token 消耗(log)")
    ax.set_ylabel("准确率 (%)")
    ax.set_title(f"{dataset.upper()}:准确率 vs 成本(误差线为 95% CI)", loc="left", color=INK)
    for lab, c, f in fams:
        if any(f(n) for n in pts):
            ax.plot([], [], "o", color=c, label=lab)
    ax.legend(frameon=False, loc="lower right")
    ax.set_xlim(right=ax.get_xlim()[1] * 2.2)   # 给最右侧标签留位置
    _place_labels(ax, [(S[n]["tokens"], S[n]["acc"] * 100, n) for n in pts])
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{dataset}_tradeoff.png")
    plt.close(fig)


def fig_rounds(dataset, S):
    fig, ax = plt.subplots(figsize=(6, 4))
    for lab, c in (("Debate", C1), ("Roles", C2), ("AntiConf", C3)):
        xs = [k for k in range(1, 6) if f"{lab} 3x{k}" in S]
        if xs:
            ys = [S[f"{lab} 3x{k}"]["acc"] * 100 for k in xs]
            ax.plot(xs, ys, "-o", lw=2, ms=7, color=c, mec="white", mew=1.5, label=lab)
    xs = [k for k in range(1, 6) if f"Debate 3x{k} +JudgeFull" in S]
    if xs:   # 同色虚线 + 空心点:原版辩论在第 k 轮后改由裁判裁决
        ys = [S[f"Debate 3x{k} +JudgeFull"]["acc"] * 100 for k in xs]
        ax.plot(xs, ys, "--o", lw=1.5, ms=6, color=C1, mfc="white", mew=1.5, label="Debate +JudgeFull")
    for ref, ls, dy, va in (("SC@3", ":", -3, "top"), ("SC@6", "--", 3, "bottom"), ("CoT", "-.", 3, "bottom")):
        if ref in S:
            ax.axhline(S[ref]["acc"] * 100, color=INK2, lw=1, ls=ls)
            ax.annotate(ref, (1, S[ref]["acc"] * 100), xycoords=("axes fraction", "data"), xytext=(-2, dy),
                        textcoords="offset points", ha="right", va=va, fontsize=7.5, color=INK2)
    ax.set_xticks([1, 2, 3])
    ax.set_xlabel("辩论轮数(第 1 轮 = 各自独立作答)")
    ax.set_ylabel("准确率 (%)(实线:多数投票;虚线:裁判)")
    ax.set_title(f"{dataset.upper()}:准确率随轮数变化(3 agents)", loc="left", color=INK)
    ax.set_xlim(0.85, 3.3)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{dataset}_rounds.png")
    plt.close(fig)


def fig_agents(dataset, S):
    if not any(k.startswith("Debate 5x") or k.startswith("Debate 1x") for k in S):
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for n, c in ((1, C1), (3, C2), (5, C3)):
        xs = [k for k in range(1, 6) if f"Debate {n}x{k}" in S]
        if xs:
            ys = [S[f"Debate {n}x{k}"]["acc"] * 100 for k in xs]
            ax.plot(xs, ys, "-o", lw=2, ms=7, color=c, mec="white", mew=1.5, label=f"{n} agent(s)")
    ax.set_xticks([1, 2, 3])
    ax.set_xlabel("轮数(1 agent 时后续轮为自我反思)")
    ax.set_ylabel("准确率 (%)")
    ax.set_title(f"{dataset.upper()}:agent 数量消融", loc="left", color=INK)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{dataset}_agents.png")
    plt.close(fig)


def fig_transitions(dataset, T):
    if not T:
        return
    labs = list(T)
    fig, ax = plt.subplots(figsize=(6.4, 4))
    w = 0.3
    ax.set_xlim(-0.7, max(len(labs) - 1, 1) + 0.7)
    for j, lab in enumerate(labs):
        w2r = sum(t["w2r"] for t in T[lab])
        r2w = sum(t["r2w"] for t in T[lab])
        b1 = ax.bar(j - w / 2 - 0.01, w2r, w, color=C1, label="错→对" if j == 0 else None)
        b2 = ax.bar(j + w / 2 + 0.01, r2w, w, color=C2, label="对→错" if j == 0 else None)
        ax.bar_label(b1, padding=2, fontsize=8, color=INK2)
        ax.bar_label(b2, padding=2, fontsize=8, color=INK2)
    ax.set_xticks(range(len(labs)), labs)
    ax.set_ylabel("agent 答案迁移次数(所有轮次累计)")
    ax.set_title(f"{dataset.upper()}:辩论中的纠错与从众", loc="left", color=INK)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{dataset}_transitions.png")
    plt.close(fig)


# ---------------------------------------------------------------- 案例

def cases(task, dataset, R, gts, items, k=2):
    """抽取典型案例:多数答案"从错改对"与"从对变错"。"""
    good, bad = [], []
    for i, r in R.items():
        first, last = r["rounds"][0]["majority"], r["rounds"][-1]["majority"]
        if not task.correct(first, gts[i]) and task.correct(last, gts[i]):
            good.append(i)
        if task.correct(first, gts[i]) and not task.correct(last, gts[i]):
            bad.append(i)
    out = [f"# {dataset.upper()} 辩论案例(原版 Debate 3x3)\n",
           f"多数答案 从错改对: {len(good)} 题;从对变错: {len(bad)} 题\n"]
    for title, ids in (("从错改对", good[:k]), ("从对变错(从众/被误导)", bad[:k])):
        for i in ids:
            r = R[i]
            out.append(f"\n## {title} — {i}\n\n**题目**:{task.question_text(items[i])}\n\n**标准答案**:{gts[i]}\n")
            for n, rd in enumerate(r["rounds"]):
                out.append(f"\n### 第 {n + 1} 轮  预测={rd['preds']}  多数={rd['majority']}\n")
                for a, resp in enumerate(rd["responses"]):
                    txt = resp if len(resp) < 1500 else resp[:700] + "\n...\n" + resp[-700:]
                    out.append(f"\n<details><summary>Agent {a + 1}</summary>\n\n{txt}\n\n</details>\n")
    (RESULTS_DIR / f"cases_{dataset}.md").write_text("".join(out), encoding="utf-8")


# ---------------------------------------------------------------- 主流程

ORDER = ["Single", "CoT", "SC@3", "SC@6",
         "Debate 3x1", "Debate 3x1 +JudgeFull", "Debate 3x2", "Debate 3x2 +JudgeFull",
         "Debate 3x3", "Debate 3x3 +Judge", "Debate 3x3 +JudgeFull", "Debate DynStop",
         "Roles 3x1", "Roles 3x2", "Roles 3x3", "Roles 3x3 ConfVote", "Roles 3x3 +Judge", "Roles 3x3 +JudgeFull",
         "Roles DynStop",
         "AntiConf 3x1", "AntiConf 3x2", "AntiConf 3x3", "AntiConf 3x3 ConfVote", "AntiConf 3x3 +Judge",
         "AntiConf 3x3 +JudgeFull", "AntiConf DynStop",
         "Debate 1x1", "Debate 1x2", "Debate 1x3", "Debate 5x1", "Debate 5x2", "Debate 5x3"]

PAIRS = [("Debate 3x3", "SC@6"), ("Debate 3x2", "SC@6"), ("Debate 3x3", "CoT"),
         ("Debate 3x3 +Judge", "Debate 3x3"), ("Debate 3x3 +JudgeFull", "Debate 3x3"),
         ("Debate 3x3 +JudgeFull", "Debate 3x3 +Judge"), ("Debate 3x1 +JudgeFull", "Debate 3x1"),
         ("Debate 3x1 +JudgeFull", "SC@3"), ("Debate 3x2 +JudgeFull", "Debate 3x2"),
         ("Roles 3x3 +JudgeFull", "Roles 3x3"), ("AntiConf 3x3 +JudgeFull", "AntiConf 3x3"),
         ("Roles 3x3", "Debate 3x3"), ("Roles 3x3 ConfVote", "Roles 3x3"), ("AntiConf 3x3", "Debate 3x3"),
         ("AntiConf 3x3 ConfVote", "AntiConf 3x3"), ("Debate DynStop", "Debate 3x3"), ("Debate DynStop", "SC@6"),
         ("Roles 3x3", "SC@6"), ("AntiConf 3x3", "SC@6"), ("Roles 3x3 ConfVote", "Debate 3x3")]

ABL_PAIRS = [("Debate 3x3", "Debate 1x3"), ("Debate 5x3", "Debate 3x3"), ("Debate 1x3", "Debate 1x1")]


def analyze(dataset, md):
    task = TASKS[dataset]
    names = ["single", "cot", "sc", "debate", "roles", "anticonf", "debate_a1", "debate_a5"]
    recs = {m: load(dataset, m) for m in names}
    recs = {m: r for m, r in recs.items() if r}
    if not recs:
        return
    items = {json.loads(l)["id"]: json.loads(l) for l in open(DATA_DIR / f"{dataset}.jsonl", encoding="utf-8")}
    gts = {i: it["answer"] for i, it in items.items()}
    V = variants(dataset, recs, load_judges(dataset))

    # 主表只在所有主方法都完成的公共题目上比较;消融(1/5 agent)单独取其与 Debate 3x 的交集
    main = {k: v for k, v in V.items() if not k.startswith(("Debate 1x", "Debate 5x"))}
    ids = sorted(set.intersection(*[set(v) for v in main.values()]))
    S = {n: score(task, main[n], gts, ids) for n in ORDER if n in main}
    abl = {k: v for k, v in V.items() if k.startswith(("Debate 1x", "Debate 5x", "Debate 3x")) and "Judge" not in k}
    if not any(k.startswith(("Debate 1x", "Debate 5x")) for k in abl):
        abl = {}
    abl_ids = sorted(set.intersection(*[set(v) for v in abl.values()])) if abl else []
    SA = {n: score(task, abl[n], gts, abl_ids) for n in ORDER if n in abl} if abl_ids else {}

    md.append(f"\n## {dataset.upper()}(n = {len(ids)})\n\n")
    md.append("| 方法 | 准确率 | 95% CI | 平均调用次数 | 平均 token | 平均输出 token | 平均耗时(s) | 截断率 |\n|---|---|---|---|---|---|---|---|\n")
    for n, s in S.items():
        md.append(f"| {n} | {s['acc'] * 100:.1f}% | ±{s['ci'] * 100:.1f} | {s['calls']:.1f} | {s['tokens']:.0f} | "
                  f"{s['out_tokens']:.0f} | {s['latency']:.1f} | {s['trunc'] * 100:.1f}% |\n")

    md.append("\n**显著性(精确 McNemar 检验)**\n\n| A vs B | 仅 A 对 | 仅 B 对 | p 值 |\n|---|---|---|---|\n")
    for a, b in PAIRS:
        if a in S and b in S:
            b01, b10, p = mcnemar(S[b]["vec"], S[a]["vec"])
            md.append(f"| {a} vs {b} | {b01} | {b10} | {p:.3f} |\n")

    # 裁判是否真的"推翻多数":统计裁判结论与对应多数投票不同的题,以及推翻后是改对还是改错
    JP = [(j, j.split(" +Judge")[0]) for j in S if " +Judge" in j]
    if JP:
        md.append("\n**裁判 agent vs 多数投票**(只看裁判结论与多数投票不同的题)\n\n"
                  "| 裁判变体 | 准确率 | 对应多数投票 | 准确率 | 推翻多数 | 推翻后改对 | 推翻后改错 | 额外 token |\n"
                  "|---|---|---|---|---|---|---|---|\n")
        for j, b in JP:
            if b not in S:
                continue
            over = [i for i in ids if main[j][i][0] != main[b][i][0]]
            fix = sum(task.correct(main[j][i][0], gts[i]) and not task.correct(main[b][i][0], gts[i]) for i in over)
            brk = sum(not task.correct(main[j][i][0], gts[i]) and task.correct(main[b][i][0], gts[i]) for i in over)
            md.append(f"| {j} | {S[j]['acc'] * 100:.1f}% | {b} | {S[b]['acc'] * 100:.1f}% | {len(over)} | {fix} | {brk} | "
                      f"{S[j]['tokens'] - S[b]['tokens']:.0f} |\n")

    if "Debate DynStop" in S and "Debate 3x3" in S:
        md.append("\n**动态终止**(全员一致即提前停止)\n\n")
        for lab in ("Debate", "Roles", "AntiConf"):
            d, f = S.get(f"{lab} DynStop"), S.get(f"{lab} 3x3")
            if d and f:
                md.append(f"- {lab}: 准确率 {f['acc'] * 100:.1f}% → {d['acc'] * 100:.1f}%,"
                          f"token {f['tokens']:.0f} → {d['tokens']:.0f}(节省 {(1 - d['tokens'] / f['tokens']) * 100:.0f}%)\n")

    T = {}
    md.append("\n**从众 / 纠错分析**(逐 agent 答案迁移,所有轮次累计)\n\n"
              "| 辩论版本 | 错→对 | 对→错 | 改答案比例 | 最终全票一致率 | 全票一致但错 | 首轮有人对但最终多数错 |\n|---|---|---|---|---|---|---|\n")
    for m, lab in (("debate", "Debate"), ("roles", "Roles"), ("anticonf", "AntiConf")):
        if m in recs:
            R = {i: recs[m][i] for i in ids}
            T[lab] = transitions(task, R, gts)
            cs = consensus_stats(task, R, gts)
            md.append(f"| {lab} | {sum(t['w2r'] for t in T[lab])} | {sum(t['r2w'] for t in T[lab])} | "
                      f"{sum(t['changed'] for t in T[lab]) / len(T[lab]) * 100:.1f}% | {cs['unanimous'] * 100:.1f}% | "
                      f"{cs['wrong_unanimous']} | {cs['minority_right_lost']} |\n")

    if SA:
        md.append(f"\n**agent 数量消融**(n = {len(abl_ids)})\n\n| 配置 | 准确率 | 平均 token |\n|---|---|---|\n")
        for n, s in SA.items():
            md.append(f"| {n} | {s['acc'] * 100:.1f}% | {s['tokens']:.0f} |\n")
        md.append("\n| A vs B | 仅 A 对 | 仅 B 对 | p 值 |\n|---|---|---|---|\n")
        for a, b in ABL_PAIRS:
            if a in SA and b in SA:
                b01, b10, p = mcnemar(SA[b]["vec"], SA[a]["vec"])
                md.append(f"| {a} vs {b} | {b01} | {b10} | {p:.3f} |\n")

    md.append(f"\n![tradeoff](../figures/{dataset}_tradeoff.png)\n![rounds](../figures/{dataset}_rounds.png)\n"
              f"![transitions](../figures/{dataset}_transitions.png)\n")
    if SA:
        md.append(f"![agents](../figures/{dataset}_agents.png)\n")

    fig_tradeoff(dataset, S, ORDER)
    fig_rounds(dataset, S)
    fig_transitions(dataset, T)
    if SA:
        fig_agents(dataset, SA)
    if "debate" in recs:
        cases(task, dataset, {i: recs["debate"][i] for i in ids}, gts, items)


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    md = ["# 实验结果汇总\n"]
    for d in TASKS:
        analyze(d, md)
    (RESULTS_DIR / "summary.md").write_text("".join(md), encoding="utf-8")
    print("".join(md))


if __name__ == "__main__":
    main()
