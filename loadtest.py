"""Серия прогонов locust со сводной таблицей: пользователи, реплики, p95, CPU на под,
   requests до/после.

Запуск из корня репозитория (рядом с locustfile.py), kubectl должен смотреть на нужный кластер:

  uv run python loadtest.py
  uv run python loadtest.py --users 20 60 150 --duration 240 --host http://churn-service.localhost

Результат: results/runN_stats.csv, results/runN.html (из locust),
results/summary.md, results/summary.csv
"""
import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SAMPLE_EVERY = 15
TAIL_SECONDS = 60


def kubectl(*args: str) -> str:
    r = subprocess.run(["kubectl", *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"kubectl {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def cpu_to_m(value: str) -> int:
    return int(value[:-1]) if value.endswith("m") else int(float(value) * 1000)


def deploy_selector(deploy: str) -> str:
    labels = json.loads(
        kubectl("get", "deploy", deploy, "-o", "jsonpath={.spec.selector.matchLabels}")
    )
    return ",".join(f"{k}={v}" for k, v in labels.items())


def cpu_requests(deploy: str) -> str:
    res = json.loads(
        kubectl(
            "get",
            "deploy",
            deploy,
            "-o",
            "jsonpath={.spec.template.spec.containers[0].resources}"
        ) or "{}"
    )
    return res.get("requests", {}).get("cpu", "не задан")


def hpa_state(hpa: str) -> dict:
    d = json.loads(kubectl("get", "hpa", hpa, "-o", "json"))
    return {
        "current": d["status"].get("currentReplicas", 0), "min": d["spec"].get("minReplicas", 1)
    }


def pod_cpus(selector: str) -> list[int]:
    out = kubectl("top", "pods", "-l", selector, "--no-headers")
    return [cpu_to_m(line.split()[1]) for line in out.splitlines() if line.strip()]


def read_locust_stats(prefix: Path) -> dict:
    with open(f"{prefix}_stats.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = next((r for r in rows if r["Name"].endswith("/v1/predict")), None) \
        or next(r for r in rows if r["Name"] == "Aggregated")
    return {
        "p95": float(row["95%"]),
        "rps": float(row["Requests/s"]),
        "requests": int(row["Request Count"]),
        "failures": int(row["Failure Count"]),
    }


def run_locust(users: int, args, prefix: Path, deploy: str, hpa: str, selector: str) -> dict:
    cmd = [
        shutil.which("uv") or "uv", "run", "--with", "locust", "locust",
        "-f", args.locustfile, "--headless",
        "-u", str(users), "-r", str(args.spawn_rate), "-t", f"{args.duration}s",
        "--host", args.host, "--csv", str(prefix), "--html", f"{prefix}.html",
    ]
    print(f"\n=== {users} пользователей: {' '.join(cmd)}")
    req_before = cpu_requests(deploy)
    proc = subprocess.Popen(cmd)
    start = time.time()
    samples = []  # (прошло секунд, реплики, [CPU подов])
    while proc.poll() is None:
        time.sleep(SAMPLE_EVERY)
        try:
            elapsed = time.time() - start
            replicas = hpa_state(hpa)["current"]
            cpus = pod_cpus(selector)
            samples.append((elapsed, replicas, cpus))
            print(f"  t={elapsed:4.0f}s реплик={replicas} CPU подов (m)={cpus}")
        except Exception as e:  # metrics-server мог ещё не ответить
            print(f"  пропуск замера: {e}")
    proc.wait()
    req_after = cpu_requests(deploy)

    stats = read_locust_stats(prefix)
    tail = [c for t, _, cpus in samples if t >= args.duration - TAIL_SECONDS for c in cpus]
    stats.update({
        "users": users,
        "replicas": max((r for _, r, _ in samples), default=None),
        "cpu_per_pod": round(statistics.mean(tail)) if tail else None,
        "req_before": req_before,
        "req_after": req_after,
    })
    if stats["failures"]:
        print(
            f"  ВНИМАНИЕ: {stats['failures']} ошибок "
            f"из {stats['requests']} запросов, "
            f"прогон нечестный"
        )
    return stats


def wait_cooldown(hpa: str, timeout: int) -> None:
    print("  ждём, пока HPA вернёт реплики к минимуму...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = hpa_state(hpa)
        if s["current"] <= s["min"]:
            return
        time.sleep(SAMPLE_EVERY)
    print("  таймаут охлаждения, идём дальше")


def write_summary(results: list[dict], out: Path) -> None:
    header = ["Прогон", "Пользователи", "Реплики (макс)", "p95, мс", "CPU на под, m",
              "requests CPU до", "requests CPU после", "RPS", "Ошибки"]
    rows = [[i, r["users"], r["replicas"], round(r["p95"]), r["cpu_per_pod"],
             r["req_before"], r["req_after"], round(r["rps"], 1), r["failures"]]
            for i, r in enumerate(results, 1)]
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    md = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    md += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n" + "\n".join(md))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--users", type=int, nargs="+", default=[20, 60, 150])
    p.add_argument("--duration", type=int, default=240, help="секунд на прогон")
    p.add_argument("--spawn-rate", type=int, default=20)
    p.add_argument("--host", default="http://churn-service.localhost")
    p.add_argument("--locustfile", default="locustfile.py")
    p.add_argument("--deploy", default="churn-service")
    p.add_argument("--hpa", default="churn-service")
    p.add_argument("--out", default="results")
    p.add_argument("--cooldown-timeout", type=int, default=600)
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    selector = deploy_selector(args.deploy)

    results = []
    for i, users in enumerate(args.users, 1):
        results.append(run_locust(users, args, out / f"run{i}", args.deploy, args.hpa, selector))
        if i < len(args.users):
            wait_cooldown(args.hpa, args.cooldown_timeout)
    write_summary(results, out)


if __name__ == "__main__":
    main()