"""把 v1(输出上限 2048)中"从未触发截断"的记录合并进 v2 结果,只需重跑被截断的题。

依据:一次调用若没有达到 2048 上限,其输出与 16k 上限下的采样结果同分布,可以直接复用。
Single 的提示在 v2 改为预填充直答,不复用。缺少 truncated 字段的早期试跑记录也不复用。

用法: python -m scripts.merge_v1 [--dry-run]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V1, V2 = ROOT / "results_v1_max2048", ROOT / "results"
SKIP = {"single"}


def clean(r, method):
    """记录内所有调用都有 truncated 字段且均为 0 才算干净。"""
    if method == "sc":
        us = r.get("sample_usage", [])
        return bool(us) and all("truncated" in u and u["truncated"] == 0 for u in us)
    u = r["usage"]
    if u.get("truncated", None) != 0:
        return False
    j = r.get("judge")
    return j is None or j["usage"].get("truncated", None) == 0


def main(dry):
    for f in sorted(V1.glob("*/*.jsonl")):
        method = f.stem
        if method in SKIP:
            continue
        out = V2 / f.parent.name / f.name
        have = set()
        if out.exists():
            have = {json.loads(l)["id"] for l in open(out, encoding="utf-8") if l.strip()}
        recs = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        add = [r for r in recs if r["id"] not in have and clean(r, method)]
        print(f"{f.parent.name}/{method}: v1 {len(recs)}, v2 已有 {len(have)}, 复用 {len(add)}, "
              f"待重跑 {len(recs) - len(have) - len(add)}")
        if not dry and add:
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "a", encoding="utf-8") as fo:
                for r in add:
                    r["reused_from_v1"] = True
                    fo.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
