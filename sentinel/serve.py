"""Serve the sentinel locally: POST {"prompt": ...} to /base (untrained Qwen3.5-2B) or /sentinel (with the
adapter Adaption trained). One copy of the base weights sits on the GPU; the adapter is switched on or off.

  .venv-sentinel\\Scripts\\python.exe sentinel/serve.py [--no-adapter]
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import torch
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")  # HF_TOKEN for the base-model download
BASE = "Qwen/Qwen3.5-2B"
PORT = 8765
# the downloaded adapter after convert_adapter.py renamed its keys; --adapter-dir picks another version
ART = HERE / (sys.argv[sys.argv.index("--adapter-dir") + 1] if "--adapter-dir" in sys.argv else "artifact_text")

tok = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16, device_map="cuda")
has_adapter = False
tok_sentinel = tok
if "--no-adapter" not in sys.argv:
    cfgs = list(ART.rglob("adapter_config.json"))
    if cfgs:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(cfgs[0].parent))
        has_adapter = True
        lora = [n for n, _ in model.named_parameters() if "lora_" in n]
        nonzero = sum(int(p.abs().sum() > 0) for n, p in model.named_parameters() if "lora_B" in n)
        print(f"adapter loaded from {cfgs[0].parent}: {len(lora)} LoRA tensors, {nonzero} non-zero lora_B", flush=True)
        # the sentinel was trained with the chat template shipped in the artifact
        tok_sentinel = AutoTokenizer.from_pretrained(str(cfgs[0].parent))
    else:
        print("no adapter found under", ART, "- serving base only", flush=True)
model.eval()
lock = threading.Lock()


def generate(prompt, use_adapter):
    t = tok_sentinel if (has_adapter and use_adapter) else tok
    msgs = [{"role": "user", "content": prompt}]
    try:
        text = t.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        text = t.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = t(text, return_tensors="pt").to("cuda")
    with lock, torch.no_grad():
        if has_adapter and not use_adapter:
            with model.disable_adapter():
                out = model.generate(**ids, max_new_tokens=96, do_sample=False)
        else:
            out = model.generate(**ids, max_new_tokens=96, do_sample=False)
    return t.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        name = self.path.strip("/")
        if name not in ("base", "sentinel") or (name == "sentinel" and not has_adapter):
            self.send_error(404, "unknown or unavailable model")
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        text = generate(body["prompt"], use_adapter=(name == "sentinel"))
        data = json.dumps({"text": text}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


print(f"serving on http://127.0.0.1:{PORT} (adapter: {has_adapter})", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
