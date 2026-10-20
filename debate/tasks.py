"""任务相关的提示格式、答案解析与判分(GSM8K 数字题 / MMLU 选择题)。"""
import re
from collections import Counter, defaultdict


class Task:
    name = ""
    fmt = ""          # 最终答案格式要求

    def question_text(self, item):
        raise NotImplementedError

    def parse(self, text):
        raise NotImplementedError

    def correct(self, pred, gt):
        raise NotImplementedError


class GSM8K(Task):
    name = "gsm8k"
    fmt = "Your final answer should be a single numerical number, in the form \\boxed{answer}, at the end of your response."

    def question_text(self, item):
        return item["question"]

    def parse(self, text):
        if not text:
            return None
        for m in reversed(re.findall(r"\\boxed\{([^{}]*)\}", text)):
            v = _num(m)
            if v is not None:
                return v
        m = re.findall(r"-?\d[\d,]*\.?\d*", text.split("Confidence")[0])
        return _num(m[-1]) if m else None

    def correct(self, pred, gt):
        return pred is not None and abs(float(pred) - float(gt)) < 1e-4


class MMLU(Task):
    name = "mmlu"
    fmt = "Put your final answer in the form (X) at the end of your response, where X is one of A, B, C, D."

    def question_text(self, item):
        c = item["choices"]
        return f"{item['question']}\nA) {c[0]}\nB) {c[1]}\nC) {c[2]}\nD) {c[3]}"

    def parse(self, text):
        if not text:
            return None
        body = text.split("Confidence")[0]
        m = re.findall(r"\(([ABCD])\)", body)
        if m:
            return m[-1]
        m = re.findall(r"(?:answer is|Answer:)\s*\**\s*\(?([ABCD])\b", body, re.I)
        return m[-1].upper() if m else None

    def correct(self, pred, gt):
        return pred == gt


def _num(s):
    s = s.replace(",", "").replace("$", "").replace("\\%", "").replace("%", "").strip()
    m = re.search(r"-?\d+\.?\d*", s)
    if not m:
        return None
    v = float(m.group())
    return int(v) if v == int(v) else v


class MATH(GSM8K):
    """MATH-500 中 Level 4-5 且答案为整数的难题,沿用数字解析与判分。"""
    name = "math"
    fmt = "Your final answer should be a single integer, in the form \\boxed{answer}, at the end of your response."


class AIME(MATH):
    """AIME 2024 + 2025 共 60 题,答案为 0-999 的整数;难度远高于 MATH,用于检验辩论在模型能力边界上的作用。"""
    name = "aime"


TASKS = {"gsm8k": GSM8K(), "math": MATH(), "aime": AIME(), "mmlu": MMLU()}


def parse_confidence(text):
    m = re.findall(r"Confidence\W{0,3}(\d{1,3})", text or "", re.I)
    return min(int(m[-1]), 100) if m else 50


def majority(preds):
    """多数投票;平票时取最先出现者(与原论文 most_frequent 一致)。"""
    valid = [p for p in preds if p is not None]
    if not valid:
        return None
    return Counter(valid).most_common(1)[0][0]


def weighted_vote(preds, confs):
    score = defaultdict(float)
    for p, c in zip(preds, confs):
        if p is not None:
            score[p] += c
    return max(score, key=score.get) if score else None
