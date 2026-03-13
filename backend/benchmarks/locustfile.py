"""Locust benchmark for the Timeseries API.

Prerequisites:
    pip install locust
    python -m benchmarks.seed --host http://localhost:8000

Run with web UI:
    locust -f backend/benchmarks/locustfile.py --host http://localhost:8000

Run headless (50 users, 5 min, save report):
    locust -f backend/benchmarks/locustfile.py --host http://localhost:8000 \
        --headless -u 50 -r 5 --run-time 5m \
        --html backend/benchmarks/results/report.html \
        --csv backend/benchmarks/results/results
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from locust import HttpUser, between, task

# Load seed data written by seed.py
_seed_file = Path(__file__).parent / "seed_data.json"
_seed = json.loads(_seed_file.read_text()) if _seed_file.exists() else {}
_ts_ids: dict[str, int] = _seed.get("timeseries_ids", {})
_credentials: dict[str, str] = _seed.get(
    "credentials",
    {"username": "benchmark_user", "password": "benchmark_password_123"},
)

# Load xlarge IDs written by seed_xlarge.py
_xlarge_seed_file = Path(__file__).parent / "seed_xlarge_data.json"
_xlarge_seed = json.loads(_xlarge_seed_file.read_text()) if _xlarge_seed_file.exists() else {}
_xlarge_ids: list[int] = _xlarge_seed.get("xlarge_ids", [])


def _generate_points(n: int) -> list[dict]:
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


class TimeseriesUser(HttpUser):
    """Simulates a user hitting the timeseries API with a realistic read-heavy mix.

    Task weight breakdown:
        read_small   3 ) 60% reads
        read_medium  2 )
        read_large   1 )
        write_small  2 ) 30% writes
        write_medium 1 )
    """

    wait_time = between(0.5, 2.0)
    token: str = ""

    def on_start(self):
        """Authenticate once per simulated user and store the JWT."""
        resp = self.client.post("/auth/token", data={
            "username": _credentials["username"],
            "password": _credentials["password"],
        })
        resp.raise_for_status()
        self.token = resp.json()["access_token"]

    @property
    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    # ── Read tasks ────────────────────────────────────────────────────────────

    @task(3)
    def read_small(self):
        ts_id = _ts_ids.get("small")
        if ts_id:
            self.client.get(
                f"/timeseries/{ts_id}",
                headers=self._auth,
                name="GET /timeseries/[small]",
            )

    @task(2)
    def read_medium(self):
        ts_id = _ts_ids.get("medium")
        if ts_id:
            self.client.get(
                f"/timeseries/{ts_id}",
                headers=self._auth,
                name="GET /timeseries/[medium]",
            )

    @task(1)
    def read_large(self):
        ts_id = _ts_ids.get("large")
        if ts_id:
            self.client.get(
                f"/timeseries/{ts_id}",
                headers=self._auth,
                name="GET /timeseries/[large]",
            )

    @task(1)
    def read_xlarge(self):
        ts_id = _ts_ids.get("xlarge")
        if ts_id:
            self.client.get(
                f"/timeseries/{ts_id}",
                headers=self._auth,
                name="GET /timeseries/[xlarge]",
                timeout=60,
            )

    @task(3)
    def read_xlarge_bulk(self):
        if not _xlarge_ids:
            return
        ts_id = random.choice(_xlarge_ids)
        self.client.get(
            f"/timeseries/{ts_id}",
            headers=self._auth,
            name="GET /timeseries/[xlarge-bulk]",
            timeout=60,
        )

    # ── Write tasks ───────────────────────────────────────────────────────────

    @task(2)
    def write_small(self):
        self.client.post(
            "/timeseries/",
            json={"name": "bench_write", "data": _generate_points(10)},
            headers=self._auth,
            name="POST /timeseries/[small]",
        )

    @task(1)
    def write_medium(self):
        self.client.post(
            "/timeseries/",
            json={"name": "bench_write", "data": _generate_points(1_000)},
            headers=self._auth,
            name="POST /timeseries/[medium]",
        )
