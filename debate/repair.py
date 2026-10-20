"""把 v1(输出上限 2048)的记录精确修复成 16k 上限下的记录,避免整套重跑。

- 一次调用的输出恰好 2048 token ⇒ 被截断。把截断文本作为助手回复的开头(prefill)从断点续写,
  得到的就是 16k 上限下同一次采样的完整输出(已验证续写时的模板渲染与原生成上下文逐 token 一致)。
- 辩论中某轮有截断时:该轮被截断的 agent 续写,同轮其他 agent 不受影响保持原样;
  之后所有轮次依赖了被改动的回答,全部重新生成;裁判随之重跑。
- 未触发截断的调用原样保留。这样修复后的记录与直接用 16k 上限跑出的记录同分布,
  不会像"截断就整题重抽"那样偏向短回答(短回答更常答对)。

用法: python -m debate.repair [--workers 16]
"""
import argparse
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from . import config
from .llm import Usage, chat
from .methods import ROLES, _debate_prompt, _first_prompt, cot_prompt, judge
from .tasks import TASKS, majority, parse_confidence

V1 = config.ROOT / "results_v1_max2048"
V1_LIMIT = 2048
DEBATE_CFG = {"debate": (3, "orig"), "roles": (3, "roles"), "anticonf": (3, "anticonf"),
              "debate_a1": (1, "orig"), "debate_a5": (5, "orig")}

_http = httpx.Client(trust_env=False, timeout=600)


def ntok(text, retries=5):
    if len(text) < 2500:   # 2048 token 至少对应数千字符,短文本必然未截断,省掉请求
        return 0
    for attempt in range(retries):
        try:
            r = _http.post(config.API_BASE.replace("/v1", "") + "/tokenize",
                           headers={"Authorization": f"Bearer {config.API_KEY}"},
                           json={"model": config.MODEL_NAME, "prompt": text, "add_special_tokens": False})
            return r.json()["count"]
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5 * 2 ** attempt)


def truncated(text):
    return ntok(text) >= V1_LIMIT


def resume(messages, partial, temperature):
    """从截断处续写;返回 (完整输出, 本次续写引入的 usage 增量)。"""
    u = Usage()
    n = ntok(partial)
    rest = chat(messages, u, temperature=temperature, max_tokens=config.MAX_TOKENS - n, prefill=partial)
    d = u.to_dict()
    # 续写请求的 prompt = 原 prompt + partial;原 prompt 已在 v1 usage 中计过,partial 属于输出
    delta = {"calls": 0, "prompt_tokens": 0, "completion_tokens": d["completion_tokens"],
             "latency": d["latency"], "truncated": d["truncated"] - 1}   # 原记的 1 次截断被消除
    return partial + rest, delta


def _add(usage, delta):
    out = dict(usage)
    out.setdefault("truncated", 0)
    for k, v in delta.items():
        out[k] = round(out.get(k, 0) + v, 2)
    out["truncated"] = max(0, out["truncated"])   # 早期试跑记录没有 truncated 字段
    out["total_tokens"] = out["prompt_tokens"] + out["completion_tokens"]
    return out


# ---------------------------------------------------------------- 各方法的修复

def repair_cot(task, item, r):
    n = 0
    if truncated(r["response"]):
        r["response"], d = resume([{"role": "user", "content": cot_prompt(task, item)}], r["response"], 0)
        r["usage"] = _add(r["usage"], d)
        r["pred"] = task.parse(r["response"])
        n = 1
    return r, n


def repair_sc(task, item, r):
    n = 0
    msgs = [{"role": "user", "content": cot_prompt(task, item)}]
    for i, out in enumerate(r["responses"]):
        if truncated(out):
            r["responses"][i], d = resume(msgs, out, 0.7)
            r["sample_usage"][i] = _add(r["sample_usage"][i], d)
            r["preds"][i] = task.parse(r["responses"][i])
            n += 1
    for su in r["sample_usage"]:
        su.setdefault("truncated", 0)
    r["pred"] = majority(r["preds"])
    keys = ["calls", "prompt_tokens", "completion_tokens", "total_tokens", "latency", "truncated"]
    r["usage"] = {k: round(sum(s.get(k, 0) for s in r["sample_usage"]), 2) for k in keys}
    return r, n


def repair_debate(task, item, r, n_agents, style):
    """按原 debate() 的上下文构造方式重放;找到第一处截断,续写后其下游全部重新生成。"""
    contexts = []
    for i in range(n_agents):
        ctx = []
        if style == "roles":
            ctx.append({"role": "system", "content": ROLES[i % len(ROLES)][1]})
        ctx.append({"role": "user", "content": _first_prompt(task, item, style)})
        contexts.append(ctx)

    n_rounds = len(r["rounds"])
    changed = False
    cum = None          # 修改发生后的累计 usage
    last, n_fix = [], 0
    for k in range(n_rounds):
        if k > 0:
            for i, ctx in enumerate(contexts):
                ctx.append({"role": "user", "content": _debate_prompt(task, item, last[:i] + last[i + 1:], style)})
        if not changed:
            outs, delta_round = [], {}
            for i, ctx in enumerate(contexts):
                out = r["rounds"][k]["responses"][i]
                if truncated(out):
                    out, d = resume(ctx, out, 0.7)
                    n_fix += 1
                    for kk, v in d.items():
                        delta_round[kk] = delta_round.get(kk, 0) + v
                outs.append(out)
            if delta_round:
                changed = True
                cum = _add(r["rounds"][k]["usage"], delta_round)
            round_usage = cum if changed else r["rounds"][k]["usage"]
        else:   # 上游已改动:本轮重新生成
            u = Usage()
            outs = [chat(ctx, u, temperature=0.7) for ctx in contexts]
            cum = _add(cum, {kk: v for kk, v in u.to_dict().items() if kk != "total_tokens"})
            round_usage = cum
        for ctx, out in zip(contexts, outs):
            ctx.append({"role": "assistant", "content": out})
        last = outs
        preds = [task.parse(o) for o in outs]
        r["rounds"][k] = {"preds": preds, "confs": [parse_confidence(o) for o in outs], "majority": majority(preds),
                          "usage": dict(round_usage, truncated=round_usage.get("truncated", 0)), "responses": outs}

    r["pred"] = r["rounds"][-1]["majority"]
    r["usage"] = r["rounds"][-1]["usage"]
    if "judge" in r:
        j = r["judge"]
        if changed:
            r["judge"] = judge(task, item, last)
        elif truncated(j["response"]):
            p = f"You are the judge of a debate among {len(last)} agents on the following problem:\n\n" \
                f"{task.question_text(item)}\n\n"
            for i, a in enumerate(last):
                p += f"[Agent {i + 1}'s final solution]\n{a}\n\n"
            p += ("Carefully evaluate the reasoning of each agent, identify any errors, and decide which answer is "
                  "correct. Do not simply count votes: the majority can be wrong. You may also derive the answer "
                  f"yourself if all agents are wrong. {task.fmt}")
            j["response"], d = resume([{"role": "user", "content": p}], j["response"], 0)
            j["usage"] = _add(j["usage"], d)
            j["pred"] = task.parse(j["response"])
            n_fix += 1
        r["judge"]["usage"].setdefault("truncated", 0)
    return r, n_fix


def repair(dataset, method, r, items):
    task = TASKS[dataset]
    item = items[r["id"]]
    if method == "cot":
        r, n = repair_cot(task, item, r)
    elif method == "sc":
        r, n = repair_sc(task, item, r)
    else:
        r, n = repair_debate(task, item, r, *DEBATE_CFG[method])
    r["usage"].setdefault("truncated", 0)
    r["correct"] = task.correct(r["pred"], r["gt"])
    r["repaired_from_v1"] = n
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--only", default="", help="只处理 dataset/method,如 math/debate")
    args = ap.parse_args()
    jobs = []
    for f in sorted(V1.glob("*/*.jsonl")):
        ds, method = f.parent.name, f.stem
        if method == "single" or (args.only and f"{ds}/{method}" != args.only):
            continue
        out = config.RESULTS_DIR / ds / f.name
        have = set()
        if out.exists():
            have = {json.loads(l)["id"] for l in open(out, encoding="utf-8") if l.strip()}
        recs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        todo = [x for x in recs if x["id"] not in have]
        print(f"{ds}/{method}: v1 {len(recs)}, 已有 {len(have)}, 待修复 {len(todo)}", flush=True)
        jobs += [(ds, method, x, out) for x in todo]

    items = {ds: {json.loads(l)["id"]: json.loads(l) for l in open(config.DATA_DIR / f"{ds}.jsonl", encoding="utf-8")}
             for ds in {j[0] for j in jobs}}
    locks = {}
    done = fixed = 0
    with ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(repair, ds, m, x, items[ds]): (ds, m, x["id"], out) for ds, m, x, out in jobs}
        for fut in as_completed(futs):
            ds, m, i, out = futs[fut]
            try:
                rec = fut.result()
            except Exception:
                print(f"[error] {ds}/{m}/{i}:\n{traceback.format_exc()}", flush=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with locks.setdefault(str(out), threading.Lock()), open(out, "a", encoding="utf-8") as fo:
                fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done += 1
            fixed += rec["repaired_from_v1"] > 0
            if done % 50 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} records, {fixed} needed continuation", flush=True)


if __name__ == "__main__":
    main()
