"""对接自部署 Qwen 的 OpenAI 兼容接口,统一封装 chat() 并统计 token / 耗时。"""
import random
import re
import time

import httpx
from openai import OpenAI

from . import config


class Usage:
    """累计一次方法调用(一道题)的成本。"""

    def __init__(self):
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.latency = 0.0
        self.truncated = 0

    def add(self, prompt_tokens, completion_tokens, latency, truncated=False):
        self.calls += 1
        self.truncated += truncated
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.latency += latency

    def to_dict(self):
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "latency": round(self.latency, 2),
            "truncated": self.truncated,
        }


# trust_env=False:绕过本机 HTTP 代理(内网地址走代理会 502)
# 流式输出 + 读超时:只要还在出 token 就不会超时(长输出可以跑很久),
# 但服务端丢掉请求、连接却没断开时,READ_TIMEOUT 秒内收不到任何数据就判定失败并重试,不会无限挂起;
# 长上下文在服务端被抢占时也会长时间静默,所以 AIME 辩论要调大(并降低并发)
_client = None if config.MOCK else OpenAI(
    base_url=config.API_BASE,
    api_key=config.API_KEY,
    http_client=httpx.Client(trust_env=False),
    timeout=httpx.Timeout(connect=30, read=config.READ_TIMEOUT, write=60, pool=60),
    max_retries=0,
)


def chat(messages, usage: Usage, temperature=0.7, max_tokens=None, retries=5, prefill=None):
    """prefill:预先写好助手回复的开头,模型从这里续写(用于强制直答)。返回值不含 prefill。"""
    if config.MOCK:
        return _mock_chat(messages, usage)
    max_tokens = max_tokens or config.MAX_TOKENS
    extra = {"chat_template_kwargs": {"enable_thinking": config.ENABLE_THINKING}}
    if prefill:
        messages = messages + [{"role": "assistant", "content": prefill}]
        extra.update(add_generation_prompt=False, continue_final_message=True)
    if temperature > 0:
        extra["top_p"] = 0.8 if not config.ENABLE_THINKING else 0.95
    for attempt in range(retries):
        try:
            t0 = time.time()
            stream = _client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body=extra,
                stream=True,
                stream_options={"include_usage": True},
            )
            parts, finish, u = [], None, None
            for chunk in stream:
                if chunk.choices:
                    parts.append(chunk.choices[0].delta.content or "")
                    finish = chunk.choices[0].finish_reason or finish
                if chunk.usage:
                    u = chunk.usage
            if u is None or finish is None:
                raise RuntimeError("stream ended without usage/finish_reason")
            usage.add(u.prompt_tokens, u.completion_tokens, time.time() - t0, finish == "length")
            return "".join(parts)
        except Exception as e:  # 网络抖动 / 服务过载 / 连接挂死时退避重试
            if attempt == retries - 1:
                raise
            wait = 5 * 2 ** attempt
            print(f"[chat] {type(e).__name__}: {e}; retry in {wait}s", flush=True)
            time.sleep(wait)


def _mock_chat(messages, usage: Usage):
    """离线假模型:随机给出带格式的答案,仅用于验证流水线。"""
    text = messages[-1]["content"]
    prompt_tokens = sum(len(m["content"]) for m in messages) // 4
    if "(A)" in text or "A)" in text:
        ans = f"The answer is ({random.choice('ABCD')})."
    else:
        nums = re.findall(r"\d+", text) or ["0"]
        ans = f"So the answer is \\boxed{{{random.choice(nums[:6])}}}."
    out = f"Let me think step by step. {ans}\nConfidence: {random.randint(40, 100)}"
    usage.add(prompt_tokens, len(out) // 4, 0.0)
    return out
