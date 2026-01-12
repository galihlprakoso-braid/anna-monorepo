"""Skill management tools for the browser agent.

Skills are specialized prompts that provide domain-specific knowledge
and instructions for interacting with specific websites or performing
specific tasks.
"""

from pathlib import Path

from langchain_core.tools import tool

from agents.browser_agent.models import LoadSkillArgs
from agents.shared.prompt_loader import PromptLoadError, list_skills, load_prompt

# Path to skills directory (relative to this file)
SKILLS_DIR = Path(__file__).parent.parent / "prompts" / "skills"


def _get_available_skills() -> str:
    """Get formatted list of available skills for tool description.

    This function is called once when the module loads to build
    the tool description with current available skills.
    """
    skills = list_skills(SKILLS_DIR)

    if not skills:
        return "  No skills currently available."

    # Format as bullet list
    return "\n".join(f"  - {skill}" for skill in sorted(skills))


def _load_skill_impl(skill_name: str) -> str:
    """Implementation of load_skill tool."""
    # Construct skill file path
    skill_file = SKILLS_DIR / f"{skill_name}.skill.prompt.md"

    try:
        # Load skill content
        content = load_prompt(skill_file)
        return content
    except PromptLoadError as e:
        # Return helpful error message
        available = list_skills(SKILLS_DIR)
        available_str = ", ".join(sorted(available)) if available else "none"

        return (
            f"Error: Skill '{skill_name}' not found.\n\n"
            f"Available skills: {available_str}\n\n"
            f"Skills are located in: {SKILLS_DIR}"
        )


# Build description with available skills
_available_skills = _get_available_skills()
_description = f"""Load a specialized skill prompt for domain-specific browser automation.

Skills provide detailed instructions and context for interacting with
specific websites or performing specialized tasks. Use this tool when
you encounter a website or task that requires domain-specific knowledge.

Available skills:
{_available_skills}

Examples:
    - load_skill("whatsapp-web") - Instructions for WhatsApp Web automation
    - load_skill("linkedin-automation") - LinkedIn interaction patterns
"""

# Create tool with dynamic description
load_skill = tool(
    _load_skill_impl,
    name="load_skill",
    description=_description,
    args_schema=LoadSkillArgs,
)


# Export tool
skill_tools = [load_skill]
