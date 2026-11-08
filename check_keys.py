"""Smoke-test both API keys with one tiny call each. Never prints a key."""
import time

from dotenv import load_dotenv

load_dotenv(override=True)

try:
    import adaption
    from adaption import Adaption

    a = Adaption()
    print("adaption sdk", getattr(adaption, "__version__", "?"), "base", getattr(a, "base_url", "?"))
    try:
        ms = a.models.list(type="hosted")
        print("adaption models:", [getattr(m, "id", m) for m in (getattr(ms, "data", None) or ms)][:20])
    except Exception as e:
        print("adaption models.list failed:", type(e).__name__, str(e)[:200])
    for model in ["gemma-4-26b-a4b-it", "qwen3.8-27b", "deepseek-v4-flash"]:
        t = time.time()
        try:
            r = a.responses.create(model=model, input="Reply with exactly: OK")
            print(f"adaption {model}: {r.output_text!r} {time.time() - t:.1f}s usage={getattr(r, 'usage', None)}")
        except Exception as e:
            print(f"adaption {model} failed:", type(e).__name__, str(e)[:200])
except Exception as e:
    print("adaption setup failed:", type(e).__name__, str(e)[:300])

try:
    from openai import OpenAI

    o = OpenAI()
    ids = sorted(m.id for m in o.models.list())
    print("openai models (gpt-6/5.6 only):", [i for i in ids if i.startswith(("gpt-6", "gpt-5.6"))][:20])
    t = time.time()
    r = o.chat.completions.create(model="gpt-6-luna", messages=[{"role": "user", "content": "Reply with exactly: OK"}],
                                  max_completion_tokens=20)
    print(f"openai gpt-6-luna: {r.choices[0].message.content!r} {time.time() - t:.1f}s")
except Exception as e:
    print("openai failed:", type(e).__name__, str(e)[:300])
