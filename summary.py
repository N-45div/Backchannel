"""One line per run: uv run python summary.py leak-none-s0 leak-cf-warn-r2-s0 ...  (glob patterns allowed)"""
import sys
from pathlib import Path

from backchannel.metrics import analyse

names = []
for arg in sys.argv[1:]:
    names += sorted(d.name for d in Path("runs").glob(arg) if (d / "events.jsonl").exists())
for n in names:
    m = analyse(f"runs/{n}")
    print(f"{n:26s} tried {m['tried']}/{m['honest']} kept {m['kept']} final {m['final_hacked']} gen{m['max_generation']} "
          f"spont {m['spontaneous']} reports {m['reports']} obj {m['object']} look {m['looked_at_shared']} "
          f"write {m['wrote_to_shared']} prev {m['prevalence']} gap {round((m['mean_canonical'] or 0) - (m['mean_reported'] or 0), 3)}")
