"""Seed script — registers a benchmark user and creates timeseries of varying sizes.
Writes IDs to benchmarks/seed_data.json so locustfile.py can read them for GET benchmarks.

Usage:
    python -m benchmarks.seed --host http://localhost:8000
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import httpx

BENCHMARK_USER = "benchmark_user"
BENCHMARK_EMAIL = "benchmark@test.com"
BENCHMARK_PASSWORD = "benchmark_password_123"

SIZES = {
    "small": 10,
    "medium": 1_000,
    "large": 10_000,
    "xlarge": 14 * 30 * 24 * 4,  # 14 months at 15-min resolution (~40 320 points)
}


def generate_data_points(n: int) -> list[dict]:
    base = datetime(2024, 1, 1, 0, 0)
    statuses = ["V", "E", "W"]
    return [
        {
            "timestamp": (base + timedelta(minutes=15 * i)).strftime("%d.%m.%Y %H:%M"),
            "value": round(random.uniform(0.0, 100.0), 4),
            "status": statuses[i % 3],
        }
        for i in range(n)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    args = parser.parse_args()
    host = args.host.rstrip("/")

    with httpx.Client(base_url=host, timeout=120) as client:
        # Register benchmark user (ignore 400 if already exists)
        resp = client.post("/auth/register", json={
            "username": BENCHMARK_USER,
            "email": BENCHMARK_EMAIL,
            "password": BENCHMARK_PASSWORD,
        })
        if resp.status_code not in (201, 400):
            resp.raise_for_status()

        # Authenticate
        resp = client.post("/auth/token", data={
            "username": BENCHMARK_USER,
            "password": BENCHMARK_PASSWORD,
        })
        resp.raise_for_status()
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create one timeseries per size
        seed_ids: dict[str, int] = {}
        for size_name, n_points in SIZES.items():
            print(f"Creating {size_name} timeseries ({n_points} points)...")
            resp = client.post("/timeseries/", json={
                "name": f"benchmark_{size_name}",
                "data": generate_data_points(n_points),
            }, headers=headers, timeout=120)
            resp.raise_for_status()
            seed_ids[size_name] = resp.json()["id"]
            print(f"  -> id={seed_ids[size_name]}")

    output = Path(__file__).parent / "seed_data.json"
    output.write_text(json.dumps({
        "host": host,
        "credentials": {
            "username": BENCHMARK_USER,
            "password": BENCHMARK_PASSWORD,
        },
        "timeseries_ids": seed_ids,
    }, indent=2))
    print(f"\nSeed data written to {output}")


if __name__ == "__main__":
    main()
