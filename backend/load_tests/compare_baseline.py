"""
Compare load test results against performance baselines.

Usage:
    python compare_baseline.py <reports_directory> [baseline_key]

Example:
    python compare_baseline.py reports/20260105_143022_mixed_100users dev.mixed_100_users
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional


def load_baselines() -> Dict:
    """Load performance baselines."""
    baselines_path = Path(__file__).parent / "baselines.json"
    with open(baselines_path, "r") as f:
        return json.load(f)


def load_test_results(reports_dir: Path) -> Dict:
    """Load test results."""
    summary_path = reports_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary not found: {summary_path}")

    with open(summary_path, "r") as f:
        return json.load(f)


def compare_metrics(current: Dict, baseline: Dict, thresholds: Dict) -> Dict:
    """Compare current metrics against baseline."""
    results = {
        "avg_response_time": {
            "current": current.get("avg_response_time_ms", 0),
            "baseline": baseline.get("avg_response_time_ms", 0),
            "status": "unknown",
            "change_percent": 0,
        },
        "p95_response_time": {
            "current": current.get("p95_response_time_ms", 0),
            "baseline": baseline.get("p95_response_time_ms", 0),
            "status": "unknown",
            "change_percent": 0,
        },
        "rps": {
            "current": current.get("total_rps", 0),
            "baseline": baseline.get("total_rps", 0),
            "status": "unknown",
            "change_percent": 0,
        },
        "error_rate": {
            "current": current.get("error_rate_percent", 0),
            "baseline": baseline.get("error_rate_percent", 0),
            "status": "unknown",
            "change_percent": 0,
        },
    }

    # Calculate changes and statuses
    for metric, data in results.items():
        if data["baseline"] == 0:
            continue

        # Calculate change
        if metric in ["avg_response_time", "p95_response_time", "error_rate"]:
            # Lower is better
            ratio = data["current"] / data["baseline"]
            change = ((data["current"] - data["baseline"]) / data["baseline"]) * 100

            if ratio <= 1.0:
                data["status"] = "improved"
            elif ratio <= thresholds[metric]["warning"]:
                data["status"] = "pass"
            elif ratio <= thresholds[metric]["critical"]:
                data["status"] = "warning"
            else:
                data["status"] = "critical"

        else:  # rps
            # Higher is better
            ratio = data["current"] / data["baseline"]
            change = ((data["current"] - data["baseline"]) / data["baseline"]) * 100

            if ratio >= 1.0:
                data["status"] = "improved"
            elif ratio >= thresholds[metric]["warning"]:
                data["status"] = "pass"
            elif ratio >= thresholds[metric]["critical"]:
                data["status"] = "warning"
            else:
                data["status"] = "critical"

        data["change_percent"] = round(change, 2)

    return results


def print_comparison(comparison: Dict, baseline_key: str) -> None:
    """Print comparison results."""
    print("=" * 80)
    print(f"PERFORMANCE COMPARISON vs {baseline_key}")
    print("=" * 80)
    print()

    # Status symbols
    symbols = {
        "improved": "✓",
        "pass": "✓",
        "warning": "⚠",
        "critical": "✗",
        "unknown": "?",
    }

    # Colors (ANSI)
    colors = {
        "improved": "\033[92m",  # Green
        "pass": "\033[92m",  # Green
        "warning": "\033[93m",  # Yellow
        "critical": "\033[91m",  # Red
        "unknown": "\033[90m",  # Gray
        "reset": "\033[0m",
    }

    # Print each metric
    for metric, data in comparison.items():
        status = data["status"]
        symbol = symbols[status]
        color = colors[status]
        reset = colors["reset"]

        metric_name = metric.replace("_", " ").title()

        print(f"{color}{symbol} {metric_name}{reset}")
        print(f"  Current:  {data['current']:.2f}")
        print(f"  Baseline: {data['baseline']:.2f}")

        if data["change_percent"] > 0:
            print(f"  Change:   +{data['change_percent']:.2f}%")
        else:
            print(f"  Change:   {data['change_percent']:.2f}%")

        print(f"  Status:   {color}{status.upper()}{reset}")
        print()

    # Overall status
    critical_count = sum(1 for d in comparison.values() if d["status"] == "critical")
    warning_count = sum(1 for d in comparison.values() if d["status"] == "warning")

    print("=" * 80)
    if critical_count > 0:
        print(f"{colors['critical']}✗ CRITICAL: {critical_count} metric(s) degraded significantly{colors['reset']}")
        return_code = 2
    elif warning_count > 0:
        print(f"{colors['warning']}⚠ WARNING: {warning_count} metric(s) showing regression{colors['reset']}")
        return_code = 1
    else:
        print(f"{colors['improved']}✓ PASS: All metrics within acceptable range{colors['reset']}")
        return_code = 0

    print("=" * 80)

    sys.exit(return_code)


def get_baseline_value(baselines: Dict, key: str) -> Optional[Dict]:
    """Get baseline value from nested dict using dot notation."""
    keys = key.split(".")
    value = baselines["baselines"]

    for k in keys:
        if k in value:
            value = value[k]
        else:
            return None

    return value


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python compare_baseline.py <reports_directory> [baseline_key]")
        print()
        print("Example:")
        print("  python compare_baseline.py reports/latest dev.mixed_100_users")
        sys.exit(1)

    reports_dir = Path(sys.argv[1])
    baseline_key = sys.argv[2] if len(sys.argv) > 2 else "dev.mixed_100_users"

    # Load data
    try:
        baselines = load_baselines()
        test_results = load_test_results(reports_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Get baseline
    baseline = get_baseline_value(baselines, baseline_key)
    if not baseline:
        print(f"Error: Baseline '{baseline_key}' not found")
        print()
        print("Available baselines:")
        for env, tests in baselines["baselines"].items():
            for test_name in tests.keys():
                print(f"  - {env}.{test_name}")
        sys.exit(1)

    # Get thresholds
    thresholds = baselines["regression_thresholds"]

    # Compare
    comparison = compare_metrics(test_results["metrics"], baseline, thresholds)

    # Print results
    print_comparison(comparison, baseline_key)


if __name__ == "__main__":
    main()
