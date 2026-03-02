import json
import random
import argparse
from datetime import datetime, timedelta

START = datetime(2024, 1, 1, 0, 15)
STATUSES = ["W", "V", "E"]


def generate(name: str, n: int) -> dict:
    data = []
    for i in range(n):
        ts = START + timedelta(minutes=15 * i)
        data.append({
            "timestamp": ts.strftime("%d.%m.%Y %H:%M"),
            "value": str(random.randint(0, 100)),
            "status": random.choice(STATUSES),
        })
    return {"name": name, "data": data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int, help="Number of data points")
    parser.add_argument("--name", default="timeseries_data", help="Timeseries name")
    parser.add_argument("--out", default="output.json", help="Output file")
    args = parser.parse_args()

    payload = generate(args.name, args.n)

    with open(args.out, "w") as f:
        json.dump(payload, f, indent=4)

    print(f"Written {args.n} entries to {args.out}")