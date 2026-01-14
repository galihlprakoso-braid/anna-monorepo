#!/usr/bin/env python3
"""
Fetch full trace data from LangSmith for debugging.

This script downloads complete trace data without truncation, including:
- All messages with full content
- Tool calls and arguments
- Screenshots (base64 images)
- Model responses

Usage:
    # Fetch specific trace by ID
    python scripts/fetch_trace.py --trace-id 019bbb3d-53f3-7c90-be38-81cee3e18cfd
    
    # Fetch latest trace from project
    python scripts/fetch_trace.py --latest
    
    # Fetch and save to specific file
    python scripts/fetch_trace.py --trace-id <id> --output /path/to/output.json
    
    # Fetch from specific project
    python scripts/fetch_trace.py --latest --project-name "browser_agent"

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
from typing import Any, Optional

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


def fetch_trace_by_id(client: Client, trace_id: str, project_name: Optional[str] = None) -> dict[str, Any]:
    """Fetch a specific trace by ID.
    
    Args:
        client: LangSmith client
        trace_id: The trace ID to fetch
        project_name: Optional project name (for context, not strictly required for trace fetch)
    
    Returns:
        Complete trace data as a dictionary
    """
    print(f"Fetching trace: {trace_id}", file=sys.stderr)
    
    try:
        # Get the run (trace) from LangSmith
        run = client.read_run(trace_id)
        
        # Convert to dict and extract the messages/conversation
        trace_data = {
            "trace_id": str(run.id),
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
        
        # If this is a chat/agent run, try to extract the full conversation
        if run.inputs:
            trace_data["full_inputs"] = run.inputs
        if run.outputs:
            trace_data["full_outputs"] = run.outputs
            
        print(f"✓ Successfully fetched trace: {trace_id}", file=sys.stderr)
        print(f"  Name: {run.name}", file=sys.stderr)
        print(f"  Type: {run.run_type}", file=sys.stderr)
        print(f"  Status: {run.status}", file=sys.stderr)
        
        return trace_data
        
    except Exception as e:
        print(f"Error fetching trace {trace_id}: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_latest_trace(client: Client, project_name: str) -> dict[str, Any]:
    """Fetch the most recent trace from a project.
    
    Args:
        client: LangSmith client
        project_name: Name of the project
    
    Returns:
        Complete trace data as a dictionary
    """
    print(f"Fetching latest trace from project: {project_name}", file=sys.stderr)
    
    try:
        # List runs from the project, get the most recent one
        runs = list(client.list_runs(project_name=project_name, limit=1))
        
        if not runs:
            print(f"Error: No traces found in project '{project_name}'", file=sys.stderr)
            sys.exit(1)
        
        latest_run = runs[0]
        trace_id = str(latest_run.id)
        
        print(f"Found latest trace: {trace_id}", file=sys.stderr)
        
        # Fetch the full trace data
        return fetch_trace_by_id(client, trace_id, project_name)
        
    except Exception as e:
        print(f"Error fetching latest trace: {e}", file=sys.stderr)
        sys.exit(1)


def save_trace(trace_data: dict[str, Any], output_path: Optional[Path] = None) -> Path:
    """Save trace data to a JSON file.
    
    Args:
        trace_data: The trace data to save
        output_path: Optional output file path. If not provided, generates one.
    
    Returns:
        Path to the saved file
    """
    if output_path is None:
        # Generate filename from trace ID and timestamp
        trace_id = trace_data.get("trace_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent.parent / "tmp" / "traces" / f"trace_{trace_id}_{timestamp}.json"
    
    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save with pretty printing and ensure no truncation
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Trace saved to: {output_path}", file=sys.stderr)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Fetch full trace data from LangSmith for debugging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Trace selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--trace-id",
        help="Specific trace ID to fetch"
    )
    group.add_argument(
        "--latest",
        action="store_true",
        help="Fetch the latest trace from the project"
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
        help="Output file path (default: auto-generated in tmp/traces/)"
    )
    
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print trace to stdout instead of saving to file"
    )
    
    args = parser.parse_args()
    
    # Initialize LangSmith client
    client = get_langsmith_client()
    
    # Fetch trace
    if args.trace_id:
        trace_data = fetch_trace_by_id(client, args.trace_id, args.project_name)
    else:  # --latest
        trace_data = fetch_latest_trace(client, args.project_name)
    
    # Output trace
    if args.stdout:
        # Print to stdout for piping
        print(json.dumps(trace_data, indent=2, ensure_ascii=False))
    else:
        # Save to file
        output_path = save_trace(trace_data, args.output)
        print(f"\nTo view the trace:", file=sys.stderr)
        print(f"  cat {output_path} | python -m json.tool | less", file=sys.stderr)
        print(f"  or open it in your editor", file=sys.stderr)


if __name__ == "__main__":
    main()
