"""One JSON-returning call to Adaption's hosted models or OpenAI, with a disk cache, retries and a spend cap.

The cache is keyed by model, prompt and a sample key (run seed, agent, round). Re-running a swarm with the
same seed replays every call whose prompt is unchanged, so a counterfactual run (one message deleted)
only pays for the calls that diverge, and every result can be reproduced from the cache.
"""
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)
BUDGET_USD = float(os.environ.get("BACKCHANNEL_BUDGET_USD", "15"))
OPENAI_PRICES = {"gpt-6-luna": (0.10, 0.50), "gpt-5.6-luna": (0.10, 0.50), "gpt-6-sol": (2.0, 10.0)}

_lock = threading.Lock()
spent = {"usd": 0.0, "calls": 0, "cached": 0}
_adaption = None
_openai = None


class BudgetExceeded(RuntimeError):
    pass


def _clients():
    global _adaption, _openai
    if _adaption is None:
        from adaption import Adaption
        from openai import OpenAI
        _adaption = Adaption(max_retries=4, timeout=120)
        _openai = OpenAI(max_retries=4, timeout=120)
    return _adaption, _openai


def parse_json(text: str):
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise json.JSONDecodeError("no object", text, 0)
    return json.loads(text[start:end + 1])


def _raw(model: str, system: str, user: str):
    adaption, openai = _clients()
    if model.startswith("gpt-"):
        r = openai.chat.completions.create(
            model=model, max_completion_tokens=1500, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        u = r.usage
        p_in, p_out = OPENAI_PRICES.get(model, (2.0, 10.0))
        return r.choices[0].message.content or "", (u.prompt_tokens * p_in + u.completion_tokens * p_out) / 1e6
    r = adaption.responses.create(model=model, instructions=system, input=user)
    cost = getattr(getattr(r, "usage", None), "cost", None) or 0.0
    return r.output_text or "", float(cost)


def chat_json(model: str, system: str, user: str, sample_key: str = "") -> dict:
    key = hashlib.sha256(json.dumps([model, system, user, sample_key]).encode()).hexdigest()
    path = CACHE / key[:2] / f"{key}.json"
    if path.exists():
        with _lock:
            spent["cached"] += 1
        return json.loads(path.read_text(encoding="utf-8"))
    if spent["usd"] >= BUDGET_USD:
        raise BudgetExceeded(f"spent ${spent['usd']:.2f} of ${BUDGET_USD:.2f}")
    err = None
    for attempt in range(4):
        try:
            text, cost = _raw(model, system, user)
            with _lock:
                spent["usd"] += cost
                spent["calls"] += 1
            try:
                parsed = parse_json(text)
            except json.JSONDecodeError as e:
                err = e
                user = user + "\n\n(Your last reply was not valid JSON. Reply with one JSON object only.)"
                continue
            out = {"raw": text, "parsed": parsed, "cost": cost}
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(out), encoding="utf-8")
            return out
        except BudgetExceeded:
            raise
        except Exception as e:  # transient API errors: back off and retry
            err = e
            time.sleep(2 * (attempt + 1))
    return {"raw": f"ERROR: {type(err).__name__}: {str(err)[:200]}", "parsed": {}, "cost": 0.0, "error": True}
