"""读取 .env / 环境变量中的模型配置。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", ROOT / "results"))
FIG_DIR = Path(os.environ.get("FIG_DIR", ROOT / "figures"))


def _load_dotenv(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_dotenv(ROOT / ".env")

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen3.8-27B")
API_KEY = os.environ.get("QWEN_API_KEY", "EMPTY")
API_BASE = os.environ.get("QWEN_API_BASE", "http://localhost:8006/v1")
ENABLE_THINKING = os.environ.get("ENABLE_THINKING", "0") == "1"
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "8192"))   # 每次调用输出上限
READ_TIMEOUT = float(os.environ.get("READ_TIMEOUT", "600"))   # 流式输出最长"静默"秒数,超过则判定挂起并重试
MOCK = os.environ.get("MOCK", "0") == "1"   # 离线自测:不调真实 API
