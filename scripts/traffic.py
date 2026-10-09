r"""Поток запросов к сервису из строк датасета, чтобы на дашборде Grafana было что смотреть.

  uv run python scripts/traffic.py --url http://churn-service.localhost \
    --rps 5 --bad 0.05 --batch 0.2

Через Ingress запросы делятся между подами и переживают rollout. Через port-forward нет:
он привязан к одному поду и обрывается, когда этот под удаляют.
--bad   доля заведомо плохих запросов (Age = -1), они дают 422 на графике.
--batch доля запросов к /v1/predict/batch, остальные идут к /v1/predict
--batch-max максимальный размер батча, по умолчанию 100
"""
import argparse
import json
import random
import time
import urllib.error
import urllib.request

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://churn-service.localhost")
parser.add_argument("--rps", type=float, default=5)
parser.add_argument("--bad", type=float, default=0.0)
parser.add_argument("--batch", type=float, default=0.0,
                    help="доля запросов к /v1/predict/batch")
parser.add_argument("--batch-max", type=int, default=100,
                    help="максимальный размер батча")
args = parser.parse_args()

def send(path: str, payload) -> int:
    req = urllib.request.Request(f"{args.url}{path}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        if codes.get(e.code, 0) < 3:
            print(e.code, e.read()[:300], flush=True)
        return e.code
    except (urllib.error.URLError, OSError):
        return 0

df = pd.read_csv("data/train.csv").drop(columns=["id", "CustomerId", "Exited"])
rows = [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in df.to_dict("records")]

codes: dict[int, int] = {}
start = time.time()
while True:
    if random.random() < args.batch:
        size = random.choice([1, 5, 10, 25, 50, args.batch_max])
        items = [dict(random.choice(rows)) for _ in range(size)]
        code = send("/v1/predict/batch", {"rows": items})
    else:
        row = dict(random.choice(rows))
        if random.random() < args.bad:
            row["Age"] = -1
        code = send("/v1/predict", row)
    codes[code] = codes.get(code, 0) + 1
    total = sum(codes.values())
    if total <= 5 or total % 50 == 0:
        print(f"{total} запросов за {time.time() - start:.0f} с, коды {codes}", flush=True)
    time.sleep(1 / args.rps)