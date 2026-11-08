"""Train the sentinel with Adaption's AutoScientist, one step at a time. State is kept in sentinel/adaption_state.json.

  uv run python sentinel/train_adaption.py upload      # upload data/adaption_train.jsonl as a raw dataset
  uv run python sentinel/train_adaption.py recommend   # show the hyperparameters AutoScientist would use (free)
  uv run python sentinel/train_adaption.py launch      # start the training run
  uv run python sentinel/train_adaption.py status
  uv run python sentinel/train_adaption.py download    # fetch the best trained artifact into sentinel/artifact/
"""
import json
import os
import sys
import tarfile
from pathlib import Path

from adaption import Adaption
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
STATE = HERE / "adaption_state.json"
BASE = "Qwen/Qwen3.5-2B"
load_dotenv(HERE.parent / ".env")
client = Adaption(api_key=os.environ["ADAPTION_API_KEY"])


def state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save(**kw):
    s = state()
    s.update(kw)
    STATE.write_text(json.dumps(s, indent=1, default=str), encoding="utf-8")


def show(obj):
    d = obj.model_dump(exclude_none=True) if hasattr(obj, "model_dump") else obj
    print(json.dumps(d, indent=1, default=str)[:3000])


step = sys.argv[1]
if step == "upload":
    r = client.datasets.upload_file(HERE / "data" / "adaption_train.jsonl", name="backchannel-sentinel-v1",
                                    processing_mode="raw", column_mapping={"prompt": "prompt", "completion": "completion"})
    show(r)
    ds = getattr(r, "dataset_id", None) or getattr(r, "id", None)
    save(dataset_id=ds)
    show(client.datasets.wait_for_completion(ds, timeout=1800))
elif step == "recommend":
    show(client.autoscientist.recommend_hyperparams(dataset_id=state()["dataset_id"], model=BASE))
elif step == "launch":
    s = state()
    # the raw upload already canonicalised the prompt and completion columns, so the mapping is inferred
    run = client.autoscientist.create(dataset_id=s["dataset_id"], model=BASE, training_method="instruction",
                                      idempotency_key="backchannel-sentinel-v1")
    save(experiment_id=run.id)
    show(run)
elif step == "status":
    show(client.autoscientist.get(state()["experiment_id"]))
elif step == "download":
    s = state()
    out = HERE / "artifact"
    out.mkdir(exist_ok=True)
    path = out / "artifact.tar.gz"
    client.autoscientist.download(s["experiment_id"]).write_to_file(path)
    print("saved", path, path.stat().st_size, "bytes")
    with tarfile.open(path) as t:
        names = t.getnames()
        print(names[:40])
        t.extractall(out, filter="data")
else:
    raise SystemExit(__doc__)
