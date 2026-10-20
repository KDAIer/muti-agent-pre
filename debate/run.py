"""实验入口:对指定数据集并发跑各方法,结果逐题追加写入 results/<dataset>/<method>.jsonl(可断点续跑)。

用法:
    python -m debate.run --dataset gsm8k --methods single,cot,sc,debate,roles,anticonf --n 200
"""
import argparse
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config
from .data import load
from .methods import METHODS
from .tasks import TASKS


def run_method(dataset, method, n, workers):
    task = TASKS[dataset]
    items = load(dataset, n)
    out_dir = config.RESULTS_DIR / dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{method}.jsonl"
    done = set()
    if path.exists():
        done = {json.loads(l)["id"] for l in open(path, encoding="utf-8") if l.strip()}
    todo = [it for it in items if it["id"] not in done]
    print(f"== {dataset}/{method}: {len(done)} done, {len(todo)} to run", flush=True)
    if not todo:
        return

    lock = threading.Lock()
    fn = METHODS[method]
    t0 = time.time()
    n_ok = n_correct = 0

    def work(item):
        rec = fn(task, item)
        rec = {"id": item["id"], "gt": item["answer"], **rec}
        rec["correct"] = task.correct(rec["pred"], item["answer"])
        return rec

    with ThreadPoolExecutor(workers) as ex, open(path, "a", encoding="utf-8") as f:
        futs = {ex.submit(work, it): it for it in todo}
        for fut in as_completed(futs):
            try:
                rec = fut.result()
            except Exception:
                print(f"[error] {futs[fut]['id']}:\n{traceback.format_exc()}", flush=True)
                continue
            with lock:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                n_ok += 1
                n_correct += rec["correct"]
                if n_ok % 10 == 0 or n_ok == len(todo):
                    print(f"  {method} {n_ok}/{len(todo)} acc={n_correct / n_ok:.3f} "
                          f"elapsed={time.time() - t0:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="gsm8k", choices=list(TASKS))
    ap.add_argument("--methods", default="single,cot,sc,debate,roles,anticonf")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    print(f"model={config.MODEL_NAME} base={config.API_BASE} thinking={config.ENABLE_THINKING} mock={config.MOCK}")
    for m in args.methods.split(","):
        run_method(args.dataset, m.strip(), args.n, args.workers)


if __name__ == "__main__":
    main()
