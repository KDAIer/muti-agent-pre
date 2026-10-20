"""探针:验证 Single 预填充直答,以及 2048 截断的 CoT 题在大预算下能否答对。"""
import json, time
from concurrent.futures import ThreadPoolExecutor
import httpx
from debate import config
from debate.tasks import TASKS
from debate.methods import cot_prompt

c = httpx.Client(trust_env=False, timeout=900)
H = {"Authorization": f"Bearer {config.API_KEY}"}

def call(msgs, mt, **kw):
    return c.post(config.API_BASE + "/chat/completions", headers=H, json={
        "model": config.MODEL_NAME, "messages": msgs, "max_tokens": mt, "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False}, **kw}).json()

task = TASKS["math"]
items = [json.loads(l) for l in open("data/math.jsonl")]
for it in items[:3]:
    r = call([{"role": "user", "content": task.question_text(it) + "\n\n" + task.fmt},
              {"role": "assistant", "content": "The final answer is $\\boxed{"}], 20,
             add_generation_prompt=False, continue_final_message=True)
    print("prefill:", repr(r["choices"][0]["message"]["content"]), r["choices"][0]["finish_reason"], "gt", it["answer"], flush=True)

R = {json.loads(l)["id"]: json.loads(l) for l in open("results/math/cot.jsonl")}
trunc = [i for i in items if R[i["id"]]["usage"].get("truncated")]

def go(it):
    r = call([{"role": "user", "content": cot_prompt(task, it)}], 16384)
    out = r["choices"][0]["message"]["content"]
    return it["id"], r["usage"]["completion_tokens"], r["choices"][0]["finish_reason"], task.correct(task.parse(out), it["answer"])

t0 = time.time()
with ThreadPoolExecutor(16) as ex:
    res = list(ex.map(go, trunc))
print("time", round(time.time() - t0))
for x in sorted(res, key=lambda x: x[1]):
    print(x)
print("correct", sum(x[3] for x in res), "/", len(res), "still truncated", sum(x[2] == "length" for x in res))
