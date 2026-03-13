"""Seed script — loads 1000 xlarge timeseries (~40 320 points each) as fast as possible.

Usage:
    python -m benchmarks.seed_xlarge --host http://localhost:8000 --concurrency 30
"""

import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import httpx

BENCHMARK_USER = "benchmark_user"
BENCHMARK_EMAIL = "benchmark@test.com"
BENCHMARK_PASSWORD = "benchmark_password_123"

XLARGE_POINTS = 14 * 30 * 24 * 4  # ~40 320 points
XLARGE_COUNT = 1000
DEFAULT_CONCURRENCY = 30


def generate_data_points(n: int) -> list[dict]:
    base = datetime(2024, 1, 1, 0, 0)
    statuses = ["V", "E", "W"]
    return [
        {
            "timestamp": (base + timedelta(minutes=15 * i)).isoformat(),
            "value": round(random.uniform(0.0, 100.0), 4),
            "status": statuses[i % 3],
        }
        for i in range(n)
    ]


async def create_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    i: int,
    headers: dict,
    data: list[dict],
) -> int:
    async with sem:
        resp = await client.post(
            "/timeseries/",
            json={"name": f"xlarge_{i}", "data": data},
            headers=headers,
            timeout=300,
        )
        resp.raise_for_status()
        ts_id = resp.json()["id"]
        print(f"  {i + 1}/{XLARGE_COUNT} -> id={ts_id}")
        return ts_id


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help="Max parallel requests")
    args = parser.parse_args()
    host = args.host.rstrip("/")

    # Pre-generate all payloads up front so CPU work doesn't block the event loop
    print(f"Pre-generating {XLARGE_COUNT} payloads ({XLARGE_POINTS} points each)...")
    payloads = [generate_data_points(XLARGE_POINTS) for _ in range(XLARGE_COUNT)]
    print("Done. Starting upload...\n")

    async with httpx.AsyncClient(base_url=host, timeout=120) as client:
        # Register (ignore 400 if already exists)
        resp = await client.post(
            "/auth/register",
            json={
                "username": BENCHMARK_USER,
                "email": BENCHMARK_EMAIL,
                "password": BENCHMARK_PASSWORD,
            },
        )
        if resp.status_code not in (201, 400):
            resp.raise_for_status()

        # Authenticate
        resp = await client.post(
            "/auth/token",
            data={"username": BENCHMARK_USER, "password": BENCHMARK_PASSWORD},
        )
        resp.raise_for_status()
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        print(f"Uploading {XLARGE_COUNT} xlarge timeseries (concurrency={args.concurrency})...")
        sem = asyncio.Semaphore(args.concurrency)
        tasks = [create_one(client, sem, i, headers, payloads[i]) for i in range(XLARGE_COUNT)]
        ids: list[int] = await asyncio.gather(*tasks)

    output = Path(__file__).parent / "seed_xlarge_data.json"
    output.write_text(
        json.dumps(
            {
                "host": host,
                "credentials": {"username": BENCHMARK_USER, "password": BENCHMARK_PASSWORD},
                "xlarge_ids": list(ids),
            },
            indent=2,
        )
    )
    print(f"\nDone. {XLARGE_COUNT} timeseries created. IDs written to {output}")


if __name__ == "__main__":
    asyncio.run(main())
