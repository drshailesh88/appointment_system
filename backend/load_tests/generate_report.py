"""
Generate performance summary report from Locust CSV stats.

Usage:
    python generate_report.py <reports_directory>
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from config import CONFIG


def read_stats_csv(csv_path: Path) -> List[Dict]:
    """Read Locust stats CSV file."""
    stats = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip aggregated rows
            if row["Name"] != "Aggregated":
                stats.append(row)
    return stats


def read_failures_csv(csv_path: Path) -> List[Dict]:
    """Read Locust failures CSV file."""
    failures = []
    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                failures.append(row)
    except FileNotFoundError:
        pass
    return failures


def calculate_metrics(stats: List[Dict]) -> Dict:
    """Calculate aggregate metrics."""
    total_requests = sum(int(s["Request Count"]) for s in stats if s["Request Count"])
    total_failures = sum(int(s["Failure Count"]) for s in stats if s["Failure Count"])

    # Response times
    response_times = []
    for stat in stats:
        if stat["Average Response Time"]:
            response_times.append(float(stat["Average Response Time"]))

    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

    # RPS
    total_rps = sum(float(s["Requests/s"]) for s in stats if s["Requests/s"])

    # Error rate
    error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0

    return {
        "total_requests": total_requests,
        "total_failures": total_failures,
        "avg_response_time_ms": round(avg_response_time, 2),
        "total_rps": round(total_rps, 2),
        "error_rate_percent": round(error_rate, 4),
    }


def analyze_endpoints(stats: List[Dict]) -> List[Dict]:
    """Analyze individual endpoint performance."""
    endpoints = []

    for stat in stats:
        if not stat["Name"]:
            continue

        endpoint = {
            "name": stat["Name"],
            "method": stat["Type"],
            "requests": int(stat["Request Count"]) if stat["Request Count"] else 0,
            "failures": int(stat["Failure Count"]) if stat["Failure Count"] else 0,
            "avg_ms": float(stat["Average Response Time"]) if stat["Average Response Time"] else 0,
            "min_ms": float(stat["Min Response Time"]) if stat["Min Response Time"] else 0,
            "max_ms": float(stat["Max Response Time"]) if stat["Max Response Time"] else 0,
            "p50_ms": float(stat["50%"]) if stat.get("50%") else 0,
            "p95_ms": float(stat["95%"]) if stat.get("95%") else 0,
            "p99_ms": float(stat["99%"]) if stat.get("99%") else 0,
            "rps": float(stat["Requests/s"]) if stat["Requests/s"] else 0,
        }

        # Calculate error rate
        if endpoint["requests"] > 0:
            endpoint["error_rate"] = round((endpoint["failures"] / endpoint["requests"]) * 100, 2)
        else:
            endpoint["error_rate"] = 0

        endpoints.append(endpoint)

    # Sort by number of requests
    endpoints.sort(key=lambda x: x["requests"], reverse=True)

    return endpoints


def check_performance_targets(metrics: Dict, endpoints: List[Dict]) -> Dict[str, bool]:
    """Check if performance targets are met."""
    results = {
        "error_rate": metrics["error_rate_percent"] <= CONFIG.target_error_rate * 100,
        "rps": metrics["total_rps"] >= CONFIG.target_rps,
    }

    # Check p95 response time for each endpoint
    slow_endpoints = [
        e for e in endpoints if e["p95_ms"] > CONFIG.target_response_time_ms
    ]

    results["response_time"] = len(slow_endpoints) == 0
    results["slow_endpoints"] = slow_endpoints

    return results


def generate_html_summary(
    reports_dir: Path,
    metrics: Dict,
    endpoints: List[Dict],
    failures: List[Dict],
    targets: Dict[str, bool],
) -> None:
    """Generate HTML summary report."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>DocAssist Load Test Summary</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .status {{
            padding: 5px 10px;
            border-radius: 3px;
            font-weight: bold;
        }}
        .status-pass {{
            background: #2ecc71;
            color: white;
        }}
        .status-fail {{
            background: #e74c3c;
            color: white;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #3498db;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .good {{ color: #27ae60; font-weight: bold; }}
        .warning {{ color: #f39c12; font-weight: bold; }}
        .bad {{ color: #e74c3c; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DocAssist Practice Manager - Load Test Summary</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>Overall Metrics</h2>
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{metrics['total_requests']:,}</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['total_failures']:,}</div>
                <div class="metric-label">Failures</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['avg_response_time_ms']:.0f}ms</div>
                <div class="metric-label">Avg Response Time</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['total_rps']:.1f}</div>
                <div class="metric-label">Requests/Second</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['error_rate_percent']:.2f}%</div>
                <div class="metric-label">Error Rate</div>
            </div>
        </div>

        <h2>Performance Targets</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Target</th>
                <th>Actual</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Response Time (p95)</td>
                <td>&lt; {CONFIG.target_response_time_ms}ms</td>
                <td>{'PASS' if targets['response_time'] else 'FAIL - See slow endpoints'}</td>
                <td><span class="status {'status-pass' if targets['response_time'] else 'status-fail'}">
                    {'✓ PASS' if targets['response_time'] else '✗ FAIL'}
                </span></td>
            </tr>
            <tr>
                <td>Requests/Second</td>
                <td>&gt; {CONFIG.target_rps}</td>
                <td>{metrics['total_rps']:.1f}</td>
                <td><span class="status {'status-pass' if targets['rps'] else 'status-fail'}">
                    {'✓ PASS' if targets['rps'] else '✗ FAIL'}
                </span></td>
            </tr>
            <tr>
                <td>Error Rate</td>
                <td>&lt; {CONFIG.target_error_rate * 100}%</td>
                <td>{metrics['error_rate_percent']:.4f}%</td>
                <td><span class="status {'status-pass' if targets['error_rate'] else 'status-fail'}">
                    {'✓ PASS' if targets['error_rate'] else '✗ FAIL'}
                </span></td>
            </tr>
        </table>

        <h2>Endpoint Performance</h2>
        <table>
            <tr>
                <th>Endpoint</th>
                <th>Requests</th>
                <th>Failures</th>
                <th>Avg (ms)</th>
                <th>p50 (ms)</th>
                <th>p95 (ms)</th>
                <th>p99 (ms)</th>
                <th>RPS</th>
            </tr>
    """

    for endpoint in endpoints[:20]:  # Top 20 endpoints
        p95_class = "good" if endpoint["p95_ms"] < 200 else "warning" if endpoint["p95_ms"] < 500 else "bad"

        html += f"""
            <tr>
                <td>{endpoint['name']}</td>
                <td>{endpoint['requests']:,}</td>
                <td class="{'bad' if endpoint['failures'] > 0 else 'good'}">{endpoint['failures']}</td>
                <td>{endpoint['avg_ms']:.0f}</td>
                <td>{endpoint['p50_ms']:.0f}</td>
                <td class="{p95_class}">{endpoint['p95_ms']:.0f}</td>
                <td>{endpoint['p99_ms']:.0f}</td>
                <td>{endpoint['rps']:.1f}</td>
            </tr>
        """

    html += """
        </table>
    """

    # Slow endpoints warning
    if targets["slow_endpoints"]:
        html += """
        <h2 style="color: #e74c3c;">⚠️ Slow Endpoints (p95 > target)</h2>
        <table>
            <tr>
                <th>Endpoint</th>
                <th>p95 (ms)</th>
                <th>Target (ms)</th>
            </tr>
        """
        for endpoint in targets["slow_endpoints"]:
            html += f"""
            <tr>
                <td>{endpoint['name']}</td>
                <td class="bad">{endpoint['p95_ms']:.0f}</td>
                <td>{CONFIG.target_response_time_ms}</td>
            </tr>
            """
        html += "</table>"

    # Failures
    if failures:
        html += """
        <h2 style="color: #e74c3c;">❌ Failures</h2>
        <table>
            <tr>
                <th>Method</th>
                <th>Name</th>
                <th>Error</th>
                <th>Occurrences</th>
            </tr>
        """
        for failure in failures[:10]:  # Show first 10 failures
            html += f"""
            <tr>
                <td>{failure.get('Method', 'N/A')}</td>
                <td>{failure.get('Name', 'N/A')}</td>
                <td>{failure.get('Error', 'N/A')}</td>
                <td>{failure.get('Occurrences', 'N/A')}</td>
            </tr>
            """
        html += "</table>"

    html += """
    </div>
</body>
</html>
    """

    # Write HTML file
    summary_path = reports_dir / "summary.html"
    with open(summary_path, "w") as f:
        f.write(html)

    print(f"✓ HTML summary generated: {summary_path}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python generate_report.py <reports_directory>")
        sys.exit(1)

    reports_dir = Path(sys.argv[1])

    if not reports_dir.exists():
        print(f"Error: Reports directory not found: {reports_dir}")
        sys.exit(1)

    # Read CSV files
    stats_csv = reports_dir / "stats_stats.csv"
    failures_csv = reports_dir / "stats_failures.csv"

    if not stats_csv.exists():
        print(f"Error: Stats CSV not found: {stats_csv}")
        sys.exit(1)

    print("Reading load test results...")
    stats = read_stats_csv(stats_csv)
    failures = read_failures_csv(failures_csv)

    print("Calculating metrics...")
    metrics = calculate_metrics(stats)
    endpoints = analyze_endpoints(stats)
    targets = check_performance_targets(metrics, endpoints)

    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total Requests:      {metrics['total_requests']:,}")
    print(f"Total Failures:      {metrics['total_failures']:,}")
    print(f"Avg Response Time:   {metrics['avg_response_time_ms']:.2f}ms")
    print(f"Requests/Second:     {metrics['total_rps']:.2f}")
    print(f"Error Rate:          {metrics['error_rate_percent']:.4f}%")
    print("=" * 60)

    print("\nPERFORMANCE TARGETS:")
    print(f"  Response Time: {'✓ PASS' if targets['response_time'] else '✗ FAIL'}")
    print(f"  RPS:           {'✓ PASS' if targets['rps'] else '✗ FAIL'}")
    print(f"  Error Rate:    {'✓ PASS' if targets['error_rate'] else '✗ FAIL'}")

    if targets["slow_endpoints"]:
        print(f"\n⚠️  {len(targets['slow_endpoints'])} endpoints exceeded p95 target")

    if failures:
        print(f"\n❌ {len(failures)} failure types detected")

    print("\nGenerating HTML summary...")
    generate_html_summary(reports_dir, metrics, endpoints, failures, targets)

    # Save JSON summary
    summary_json = {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "endpoints": endpoints,
        "failures": failures,
        "targets": {k: v for k, v in targets.items() if k != "slow_endpoints"},
    }

    json_path = reports_dir / "summary.json"
    with open(json_path, "w") as f:
        json.dump(summary_json, f, indent=2)

    print(f"✓ JSON summary generated: {json_path}")
    print("\nDone!")


if __name__ == "__main__":
    main()
