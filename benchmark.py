import json
import statistics

import requests

URL = "http://localhost:8000"

def benchmark(endpoint, filename):
    with open(filename, encoding="utf-8") as f:
        payload = json.load(f)

    latencies = []

    for _ in range(10):
        response = requests.post(
            f"{URL}{endpoint}",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            latency = data[0]["latency_ms"]
        else:
            latency = data["latency_ms"]

        latencies.append(latency)

    return latencies, statistics.median(latencies)


single, single_median = benchmark("/v1/predict", "good.json")
batch, batch_median = benchmark("/v1/predict/batch", "good_batch.json")

print("1 строка:")
print(single)
print(f"Медиана: {single_median} ms")

print("\n500 строк:")
print(batch)
print(f"Медиана: {batch_median} ms")