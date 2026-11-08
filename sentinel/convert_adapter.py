"""Adaption trains on Qwen3.5's full vision-language model, where the text layers live under
model.language_model.layers; the text-only model we serve names them model.layers. Same weights, different
path: rename the adapter's keys so PEFT can load it, and drop the vision-tower exclusions.

  .venv-sentinel\\Scripts\\python.exe sentinel/convert_adapter.py
Writes sentinel/artifact_text/.
"""
import json
import shutil
import sys
from pathlib import Path

from safetensors.torch import load_file, save_file

HERE = Path(__file__).resolve().parent
# usage: convert_adapter.py [src_dir dst_dir]  (defaults: the v1 artifact)
SRC, DST = (HERE / sys.argv[1], HERE / sys.argv[2]) if len(sys.argv) == 3 else (HERE / "artifact", HERE / "artifact_text")
DST.mkdir(exist_ok=True)
w = load_file(SRC / "adapter_model.safetensors")
renamed = {k.replace("model.language_model.layers.", "model.layers."): v for k, v in w.items()}
assert len(renamed) == len(w) and all(".language_model." not in k for k in renamed)
save_file(renamed, DST / "adapter_model.safetensors")
cfg = json.loads((SRC / "adapter_config.json").read_text(encoding="utf-8"))
cfg["exclude_modules"] = None
(DST / "adapter_config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
for name in ("chat_template.jinja", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"):
    if (SRC / name).exists():
        shutil.copy(SRC / name, DST / name)
nonzero_b = sum(int(v.abs().sum() > 0) for k, v in renamed.items() if "lora_B" in k)
print(f"{len(renamed)} tensors renamed; {nonzero_b} non-zero lora_B; written to {DST}")
