"""Shared utilities for loading prompt files.

This module provides utilities for loading markdown prompt files
across all agents. Supports lazy loading and basic caching.
"""

from pathlib import Path
from typing import Dict

# Simple in-memory cache for loaded prompts
_prompt_cache: Dict[str, str] = {}


class PromptLoadError(Exception):
    """Raised when a prompt file cannot be loaded."""

    pass


def load_prompt(file_path: str | Path, use_cache: bool = True) -> str:
    """Load a markdown prompt file.

    Args:
        file_path: Absolute or relative path to .prompt.md or .md file
        use_cache: Whether to cache the loaded content (default: True)

    Returns:
        The prompt content as a string

    Raises:
        PromptLoadError: If file doesn't exist, isn't readable, or is empty

    Examples:
        >>> prompt = load_prompt("prompts/system.prompt.md")
        >>> skill = load_prompt("prompts/skills/whatsapp.skill.prompt.md")
    """
    path = Path(file_path)
    cache_key = str(path.resolve())

    # Check cache first
    if use_cache and cache_key in _prompt_cache:
        return _prompt_cache[cache_key]

    # Validate file exists
    if not path.exists():
        raise PromptLoadError(f"Prompt file not found: {path}")

    if not path.is_file():
        raise PromptLoadError(f"Path is not a file: {path}")

    # Read file content
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise PromptLoadError(f"Failed to read prompt file {path}: {e}")

    # Validate non-empty
    if not content.strip():
        raise PromptLoadError(f"Prompt file is empty: {path}")

    # Cache and return
    if use_cache:
        _prompt_cache[cache_key] = content

    return content


def list_skills(skills_dir: str | Path) -> list[str]:
    """List available skill files in a directory.

    Args:
        skills_dir: Path to directory containing .skill.prompt.md files

    Returns:
        List of skill names (without .skill.prompt.md extension)

    Examples:
        >>> skills = list_skills("prompts/skills")
        >>> # Returns: ["whatsapp-web", "linkedin-automation"]
    """
    path = Path(skills_dir)

    if not path.exists() or not path.is_dir():
        return []

    # Find all .skill.prompt.md files
    skill_files = path.glob("*.skill.prompt.md")

    # Extract skill names (remove .skill.prompt.md suffix)
    return [
        f.name.replace(".skill.prompt.md", "") for f in skill_files if f.is_file()
    ]


def clear_cache():
    """Clear the prompt cache. Useful for testing or hot-reloading."""
    _prompt_cache.clear()
