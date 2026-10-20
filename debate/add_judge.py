"""对已保存的辩论记录离线补跑"完整版裁判"(JudgeFull),不需要重跑辩论本身。

每条结果写入 results/<dataset>/judge_<method>.jsonl:{id, kind, pred, correct, usage, response}
kind = "full_r{k}":裁判读前 k 轮完整记录后裁决。默认:
  - 三种辩论(debate / roles / anticonf)都做最终轮 full_r3;
  - 原版 debate 额外做 full_r1、full_r2,用于画"裁判 vs 多数投票"随轮数的曲线。
可断点续跑:已存在的 (id, kind) 跳过。辩论记录里已带 judge_full 的(新代码跑出的)直接沿用,不重复调用。

用法: python -m debate.add_judge [--datasets gsm8k,math,mmlu] [--workers 8]
"""
import argparse
import json
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config
from .methods import judge_full
from .tasks import TASKS

PLAN = {"debate": [3, 1, 2], "roles": [3], "anticonf": [3]}   # 先跑最终轮,再跑消融轮次


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="gsm8k,math,mmlu,aime")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="每个方法只处理前 N 条辩论记录(小规模试跑用)")
    args = ap.parse_args()

    jobs = []
    for ds in args.datasets.split(","):
        items = {json.loads(l)["id"]: json.loads(l) for l in open(config.DATA_DIR / f"{ds}.jsonl", encoding="utf-8")}
        for method, ks in PLAN.items():
            src = config.RESULTS_DIR / ds / f"{method}.jsonl"
            if not src.exists():
                continue
            out = config.RESULTS_DIR / ds / f"judge_{method}.jsonl"
            have = set()
            if out.exists():
                have = {(r["id"], r["kind"]) for r in map(json.loads, open(out, encoding="utf-8"))}
            recs = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
            if args.limit:
                recs = recs[:args.limit]
            n = 0
            for k in ks:
                for r in recs:
                    if (r["id"], f"full_r{k}") not in have and k <= len(r["rounds"]):
                        jobs.append((ds, method, k, r, items[r["id"]], out))
                        n += 1
            print(f"{ds}/{method}: {len(recs)} 条辩论记录, 待裁决 {n}", flush=True)

    locks = {}
    done = 0

    def work(ds, method, k, r, item):
        task = TASKS[ds]
        if k == len(r["rounds"]) and "judge_full" in r:   # 新代码跑辩论时已顺带裁决
            j = r["judge_full"]
        else:
            j = judge_full(task, item, [rd["responses"] for rd in r["rounds"][:k]])
        return {"id": r["id"], "kind": f"full_r{k}", "pred": j["pred"],
                "correct": task.correct(j["pred"], r["gt"]), "usage": j["usage"], "response": j["response"]}

    with ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(work, ds, m, k, r, it): (ds, m, k, r["id"], out) for ds, m, k, r, it, out in jobs}
        for fut in as_completed(futs):
            ds, m, k, i, out = futs[fut]
            try:
                rec = fut.result()
            except Exception:
                print(f"[error] {ds}/{m}/{i}/r{k}:\n{traceback.format_exc()}", flush=True)
                continue
            with locks.setdefault(str(out), threading.Lock()), open(out, "a", encoding="utf-8") as fo:
                fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}", flush=True)


if __name__ == "__main__":
    main()
