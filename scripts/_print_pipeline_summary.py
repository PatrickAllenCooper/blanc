"""Print a one-line summary per scenario from real pipeline logs."""
from __future__ import annotations

import json
import pathlib

LOGS = pathlib.Path("paper/sc2_pipeline_captures/logs")
ORDER = [
    "exclusion_zone",
    "worker_protection",
    "engagement_authorized",
    "outnumbered_retreat",
]


def main() -> None:
    print(
        f"{'scenario':24} {'proposed':>8} {'admitted':>8} "
        f"{'reprompts':>9} {'lat_ms':>8}  expected  actual"
    )
    for sid in ORDER:
        d = json.loads((LOGS / f"{sid}.json").read_text())
        print(
            f"{sid:24} "
            f"{len(d['proposed_orders']):>8} "
            f"{len(d['admitted_orders']):>8} "
            f"{d['reprompts']:>9} "
            f"{d['model_latency_ms']:>8.0f}  "
            f"{d['expected_outcome']:>8}  "
            f"{d['actual_outcome']}"
        )


if __name__ == "__main__":
    main()
