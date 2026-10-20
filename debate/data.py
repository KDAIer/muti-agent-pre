"""数据准备:从原始 GSM8K / MMLU 测试集中固定种子抽样,统一成 {id, question, answer} 格式。"""
import json
import random
import re

import pandas as pd

from .config import DATA_DIR

RAW = DATA_DIR / "raw"


def prepare(n=200, seed=0):
    rng = random.Random(seed)

    gsm = [json.loads(l) for l in open(RAW / "gsm8k_test.jsonl", encoding="utf-8") if l.strip()]
    rng.shuffle(gsm)
    with open(DATA_DIR / "gsm8k.jsonl", "w", encoding="utf-8") as f:
        for i, d in enumerate(gsm[:n]):
            gt = d["answer"].split("####")[-1].strip().replace(",", "")
            f.write(json.dumps({"id": f"gsm-{i}", "question": d["question"], "answer": gt,
                                "solution": d["answer"]}, ensure_ascii=False) + "\n")

    math = [json.loads(l) for l in open(RAW / "math500_test.jsonl", encoding="utf-8") if l.strip()]
    math = [d for d in math if d["level"] >= 4 and re.fullmatch(r"-?\d+", d["answer"].strip())]
    with open(DATA_DIR / "math.jsonl", "w", encoding="utf-8") as f:
        for i, d in enumerate(math):
            f.write(json.dumps({"id": f"math-{i}", "question": d["problem"], "answer": d["answer"].strip(),
                                "level": d["level"], "subject": d["subject"]}, ensure_ascii=False) + "\n")

    a24 = pd.read_parquet(RAW / "dl_Maxwell-Jia_AIME_2024_resolve_main_aime_2024_problems.parquet")
    a25 = pd.read_parquet(RAW / "dl_MathArena_aime_2025_resolve_main_data_train-00000-of-00001.parquet")
    aime = [(r["ID"], r["Problem"], r["Answer"]) for _, r in a24.iterrows()] + \
           [(f"2025-{r['problem_idx']}", r["problem"], r["answer"]) for _, r in a25.iterrows()]
    with open(DATA_DIR / "aime.jsonl", "w", encoding="utf-8") as f:
        for i, (src, q, ans) in enumerate(aime):
            f.write(json.dumps({"id": f"aime-{i}", "question": q, "answer": str(int(ans)), "source": src},
                               ensure_ascii=False) + "\n")

    df = pd.read_parquet(RAW / "mmlu_test.parquet")
    idx = list(range(len(df)))
    rng.shuffle(idx)
    with open(DATA_DIR / "mmlu.jsonl", "w", encoding="utf-8") as f:
        for i, j in enumerate(idx[:n]):
            row = df.iloc[j]
            f.write(json.dumps({"id": f"mmlu-{i}", "question": row["question"],
                                "choices": [str(c) for c in row["choices"]],
                                "answer": "ABCD"[int(row["answer"])],
                                "subject": row["subject"]}, ensure_ascii=False) + "\n")
    print(f"wrote {n} GSM8K + {len(math)} MATH + {len(aime)} AIME + {n} MMLU samples to {DATA_DIR}")


def load(dataset, n=None):
    rows = [json.loads(l) for l in open(DATA_DIR / f"{dataset}.jsonl", encoding="utf-8")]
    return rows[:n] if n else rows


if __name__ == "__main__":
    prepare()
