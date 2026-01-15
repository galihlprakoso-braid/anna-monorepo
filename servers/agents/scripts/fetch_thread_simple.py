#!/usr/bin/env python3
"""
Fetch all runs from a LangSmith thread for debugging - Simple version.

This script uses a simple approach: fetch recent runs and filter by thread_id locally.

Usage:
    python scripts/fetch_thread_simple.py --thread-id bce8227d-301e-4465-909d-ea8a4100864a

Environment Variables:
    LANGSMITH_API_KEY: Your LangSmith API key (required)
    LANGSMITH_PROJECT: Default project name (optional)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

try:
    from langsmith import Client
except ImportError:
    print("Error: langsmith package not found", file=sys.stderr)
    sys.exit(1)


def fetch_thread_runs(thread_id: str, project_name: str, lookback_hours: int = 24) -> dict[str, Any]:
    """Fetch all runs belonging to a thread.

    Args:
        thread_id: Thread ID to search for
        project_name: Project name
        lookback_hours: How many hours back to search (default: 24)

    Returns:
        Thread data with all matching runs
    """
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("Error: LANGSMITH_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = Client(api_key=api_key)

    print(f"Fetching runs from thread: {thread_id}", file=sys.stderr)
    print(f"Project: {project_name}", file=sys.stderr)
    print(f"Lookback: {lookback_hours} hours", file=sys.stderr)

    # Calculate time range
    from datetime import datetime, timedelta, timezone
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=lookback_hours)

    print(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}", file=sys.stderr)

    # Fetch recent runs from the project
    print("Fetching runs from LangSmith...", file=sys.stderr)
    all_runs = list(client.list_runs(
        project_name=project_name,
        start_time=start_time,
        limit=100  # Adjust if needed
    ))

    print(f"Fetched {len(all_runs)} total runs", file=sys.stderr)

    # Filter runs that belong to this thread
    # In LangGraph, the thread_id is typically in:
    #   1. run.session_id
    #   2. run.extra['metadata']['thread_id']
    #   3. run.reference_example_id
    print("Filtering runs by thread_id...", file=sys.stderr)

    thread_runs = []
    for run in all_runs:
        matches_thread = False

        # Check session_id
        if hasattr(run, 'session_id') and run.session_id == thread_id:
            matches_thread = True

        # Check metadata
        if hasattr(run, 'extra') and run.extra:
            metadata = run.extra.get('metadata', {})
            if metadata.get('thread_id') == thread_id:
                matches_thread = True

        # Check reference_example_id
        if hasattr(run, 'reference_example_id') and run.reference_example_id == thread_id:
            matches_thread = True

        if matches_thread:
            thread_runs.append(run)

    if not thread_runs:
        print(f"❌ No runs found for thread {thread_id}", file=sys.stderr)
        print(f"   Searched {len(all_runs)} runs in the last {lookback_hours} hours", file=sys.stderr)
        print(f"   Try increasing --lookback-hours or check the thread_id", file=sys.stderr)
        sys.exit(1)

    # Sort by start time
    thread_runs.sort(key=lambda r: r.start_time if r.start_time else datetime.min)

    print(f"✓ Found {len(thread_runs)} runs in thread", file=sys.stderr)

    # Build output structure
    thread_data = {
        "thread_id": thread_id,
        "project_name": project_name,
        "total_runs": len(thread_runs),
        "runs": []
    }

    for idx, run in enumerate(thread_runs, 1):
        print(f"  [{idx}/{len(thread_runs)}] {run.name} ({run.run_type}) - {run.status}", file=sys.stderr)

        run_data = {
            "run_id": str(run.id),
            "name": run.name,
            "run_type": run.run_type,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "status": run.status,
            "error": run.error,
            "inputs": run.inputs,
            "outputs": run.outputs,
            "metadata": run.extra.get("metadata", {}) if hasattr(run, 'extra') and run.extra else {},
            "tags": run.tags if hasattr(run, 'tags') else [],
        }

        thread_data["runs"].append(run_data)

    return thread_data


def main():
    parser = argparse.ArgumentParser(description="Fetch thread runs from LangSmith")
    parser.add_argument("--thread-id", required=True, help="Thread ID")
    parser.add_argument("--project-name", default=os.getenv("LANGSMITH_PROJECT", "anna-v3"), help="Project name")
    parser.add_argument("--lookback-hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout")

    args = parser.parse_args()

    # Fetch thread data
    thread_data = fetch_thread_runs(args.thread_id, args.project_name, args.lookback_hours)

    # Output
    if args.stdout:
        print(json.dumps(thread_data, indent=2, ensure_ascii=False))
    else:
        if args.output:
            output_path = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(__file__).parent.parent / "tmp" / "threads" / f"thread_{args.thread_id}_{timestamp}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(thread_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Saved to: {output_path}", file=sys.stderr)
        print(f"\nTo analyze:", file=sys.stderr)
        print(f"  cat {output_path} | python -m json.tool | less", file=sys.stderr)
        print(f"  cat {output_path} | jq '.runs[] | {{name, status, run_type}}'", file=sys.stderr)


if __name__ == "__main__":
    main()
