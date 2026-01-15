#!/usr/bin/env python3
"""
Fetch all runs from a LangSmith thread for debugging.

This script downloads all runs (steps) within a thread, including:
- All messages with full content
- Tool calls and arguments
- AI reasoning and decisions
- Screenshots (base64 images)
- Model responses

Usage:
    # Fetch all runs from a specific thread
    python scripts/fetch_thread.py --thread-id bce8227d-301e-4465-909d-ea8a4100864a

    # Fetch and save to specific file
    python scripts/fetch_thread.py --thread-id <id> --output /path/to/output.json

    # Fetch from specific project
    python scripts/fetch_thread.py --thread-id <id> --project-name "browser_agent"

Environment Variables:
    LANGSMITH_API_KEY: Your LangSmith API key (required)
    LANGSMITH_PROJECT: Default project name (optional, can be overridden with --project-name)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Load .env file before importing anything else
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

try:
    from langsmith import Client
except ImportError:
    print("Error: langsmith package not found. Install it with: uv pip install langsmith", file=sys.stderr)
    sys.exit(1)


def get_langsmith_client() -> Client:
    """Initialize LangSmith client with API key from environment."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("Error: LANGSMITH_API_KEY environment variable not set", file=sys.stderr)
        print("Set it in your .env file or export it:", file=sys.stderr)
        print("  export LANGSMITH_API_KEY='lsv2_...'", file=sys.stderr)
        sys.exit(1)

    return Client(api_key=api_key)


def fetch_thread_runs(client: Client, thread_id: str, project_name: str) -> dict[str, Any]:
    """Fetch all runs from a specific thread.

    Args:
        client: LangSmith client
        thread_id: The thread ID to fetch runs from
        project_name: Name of the project

    Returns:
        Thread data with all runs
    """
    print(f"Fetching thread: {thread_id}", file=sys.stderr)
    print(f"Project: {project_name}", file=sys.stderr)

    try:
        # List all runs that belong to this thread
        # Note: LangSmith uses thread_id as metadata, so we filter by it
        runs_list = list(client.list_runs(
            project_name=project_name,
            filter=f'eq(metadata_key, "thread_id")' # Filter by thread_id in metadata
        ))

        # Filter runs that match our thread_id
        thread_runs = []
        for run in runs_list:
            # Check if this run belongs to our thread
            run_thread_id = None
            if hasattr(run, 'metadata') and run.metadata:
                run_thread_id = run.metadata.get('thread_id')
            elif hasattr(run, 'extra') and run.extra:
                metadata = run.extra.get('metadata', {})
                run_thread_id = metadata.get('thread_id')

            # Also check if the run ID itself matches patterns
            # In LangGraph, the thread_id is often stored in the run's session_id or thread_id field
            if hasattr(run, 'session_id') and run.session_id == thread_id:
                run_thread_id = thread_id

            if run_thread_id == thread_id:
                thread_runs.append(run)

        if not thread_runs:
            print(f"Warning: No runs found for thread {thread_id}", file=sys.stderr)
            print(f"Trying alternate method: searching by session_id...", file=sys.stderr)

            # Try alternate method: filter by session_id
            thread_runs = list(client.list_runs(
                project_name=project_name,
                filter=f'eq(session_id, "{thread_id}")'
            ))

        if not thread_runs:
            print(f"Error: No runs found for thread {thread_id} in project {project_name}", file=sys.stderr)
            print(f"Please check:", file=sys.stderr)
            print(f"  1. Thread ID is correct", file=sys.stderr)
            print(f"  2. Project name is correct", file=sys.stderr)
            print(f"  3. LANGSMITH_API_KEY has access to this project", file=sys.stderr)
            sys.exit(1)

        # Sort runs by start time (chronological order)
        thread_runs.sort(key=lambda r: r.start_time if r.start_time else datetime.min)

        print(f"✓ Found {len(thread_runs)} runs in thread", file=sys.stderr)

        # Build thread data structure
        thread_data = {
            "thread_id": thread_id,
            "project_name": project_name,
            "total_runs": len(thread_runs),
            "runs": []
        }

        # Process each run
        for idx, run in enumerate(thread_runs, 1):
            print(f"  Processing run {idx}/{len(thread_runs)}: {run.name} ({run.run_type})", file=sys.stderr)

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
                "metadata": run.extra.get("metadata", {}) if run.extra else {},
                "tags": run.tags,
            }

            thread_data["runs"].append(run_data)

        print(f"✓ Successfully fetched thread data", file=sys.stderr)
        return thread_data

    except Exception as e:
        print(f"Error fetching thread {thread_id}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def save_thread_data(thread_data: dict[str, Any], output_path: Path | None = None) -> Path:
    """Save thread data to a JSON file.

    Args:
        thread_data: The thread data to save
        output_path: Optional output file path. If not provided, generates one.

    Returns:
        Path to the saved file
    """
    if output_path is None:
        # Generate filename from thread ID and timestamp
        thread_id = thread_data.get("thread_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent.parent / "tmp" / "threads" / f"thread_{thread_id}_{timestamp}.json"

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save with pretty printing and ensure no truncation
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(thread_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Thread data saved to: {output_path}", file=sys.stderr)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Fetch all runs from a LangSmith thread for debugging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Thread selection
    parser.add_argument(
        "--thread-id",
        required=True,
        help="Thread ID to fetch runs from"
    )

    # Project configuration
    parser.add_argument(
        "--project-name",
        default=os.getenv("LANGSMITH_PROJECT", "anna-v3"),
        help="LangSmith project name (default: from LANGSMITH_PROJECT env or 'anna-v3')"
    )

    # Output configuration
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (default: auto-generated in tmp/threads/)"
    )

    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print thread data to stdout instead of saving to file"
    )

    args = parser.parse_args()

    # Initialize LangSmith client
    client = get_langsmith_client()

    # Fetch thread data
    thread_data = fetch_thread_runs(client, args.thread_id, args.project_name)

    # Output thread data
    if args.stdout:
        # Print to stdout for piping
        print(json.dumps(thread_data, indent=2, ensure_ascii=False))
    else:
        # Save to file
        output_path = save_thread_data(thread_data, args.output)
        print(f"\nTo view the thread:", file=sys.stderr)
        print(f"  cat {output_path} | python -m json.tool | less", file=sys.stderr)
        print(f"  or open it in your editor", file=sys.stderr)
        print(f"\nTo analyze specific runs:", file=sys.stderr)
        print(f"  cat {output_path} | jq '.runs[] | select(.name==\"model_node\")'", file=sys.stderr)


if __name__ == "__main__":
    main()
