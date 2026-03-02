import time
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any


@dataclass
class RequestResult:
    method: str
    url: str
    status_code: int
    elapsed_ms: float
    response: Any = None
    error: str | None = None

    def __str__(self) -> str:
        status = f"{self.status_code}" if not self.error else f"ERROR: {self.error}"
        return f"{self.method} {self.url} -> {status} ({self.elapsed_ms:.1f} ms)"


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.history: list[RequestResult] = []

    def _request(self, method: str, path: str, body: Any = None) -> RequestResult:
        url = f"{self.base_url}/{path.lstrip('/')}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                response = json.loads(resp.read())
                result = RequestResult(method, url, resp.status, elapsed_ms, response)
        except urllib.error.HTTPError as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            result = RequestResult(method, url, e.code, elapsed_ms, error=e.reason)
        except urllib.error.URLError as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            result = RequestResult(method, url, -1, elapsed_ms, error=str(e.reason))

        self.history.append(result)
        return result

    def get(self, path: str) -> RequestResult:
        return self._request("GET", path)

    def post(self, path: str, body: Any) -> RequestResult:
        return self._request("POST", path, body)

    def put(self, path: str, body: Any) -> RequestResult:
        return self._request("PUT", path, body)

    def delete(self, path: str) -> RequestResult:
        return self._request("DELETE", path)

    def print_history(self) -> None:
        for r in self.history:
            print(r)
            if r.response is not None:
                print(json.dumps(r.response, indent=2, default=str))
        if self.history:
            times = [r.elapsed_ms for r in self.history]
            print(
                f"\n{len(times)} requests | avg {sum(times)/len(times):.1f} ms "
                f"| min {min(times):.1f} ms | max {max(times):.1f} ms"
            )


if __name__ == "__main__":
    import sys
    from generate_timeseries import generate

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5  # 14 months of 15-min intervals
    name = sys.argv[3] if len(sys.argv) > 3 else "timeseries_data"

    client = ApiClient(base_url)
    body = generate(name=name, n=n)

    r = client.post("/timeseries/", body)

    if r.status_code == 201:
        ts_id = r.response["id"]
        client.get(f"/timeseries/{ts_id}")

    client.print_history()
