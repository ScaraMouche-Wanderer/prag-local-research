#!/usr/bin/env python3
"""
Context Manager for PRAG RAG System.
Handles reading, injecting, and self-updating CONTEXT.md (machine & human readable user context).
Models read this context on every query to tailor responses to user preferences,
and can self-update CONTEXT.md when the user expresses new preferences or corrections.
"""

import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTEXT_FILE_PATH = os.path.join(BASE_DIR, "CONTEXT.md")


def get_context_path() -> str:
    """Returns absolute path to CONTEXT.md."""
    if os.path.exists(CONTEXT_FILE_PATH):
        return CONTEXT_FILE_PATH
    # Fallback to parent dir or current dir
    alt = os.path.join(os.getcwd(), "CONTEXT.md")
    if os.path.exists(alt):
        return alt
    return CONTEXT_FILE_PATH


def read_context_raw() -> str:
    """Reads raw contents of CONTEXT.md."""
    path = get_context_path()
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[CONTEXT] Error reading context file: {e}")
        return ""


def write_context_raw(content: str) -> bool:
    """Writes updated raw contents to CONTEXT.md."""
    path = get_context_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[CONTEXT] Error writing context file: {e}")
        return False


def get_user_context_prompt() -> str:
    """
    Parses key sections from CONTEXT.md and builds a compact, high-value prompt block
    to be included in the LLM's system instructions.
    """
    raw = read_context_raw()
    if not raw:
        return ""

    sections = []

    # Extract User Profile section
    profile_match = re.search(r'## User Profile\s*\n(.*?)(?=\n## |\Z)', raw, re.DOTALL)
    if profile_match:
        profile_text = profile_match.group(1).strip()
        if profile_text:
            sections.append(f"User Profile:\n{profile_text}")

    # Extract Learned Preferences section
    pref_match = re.search(r'## Learned Preferences\s*\n(.*?)(?=\n## |\Z)', raw, re.DOTALL)
    if pref_match:
        pref_text = pref_match.group(1).strip()
        if pref_text:
            sections.append(f"Learned User Preferences:\n{pref_text}")

    # Extract Custom Instructions section
    custom_match = re.search(r'## Custom Instructions for AI Assistants\s*\n(.*?)(?=\n## |\Z)', raw, re.DOTALL)
    if custom_match:
        custom_text = custom_match.group(1).strip()
        if custom_text:
            sections.append(f"Active Directives:\n{custom_text}")

    if not sections:
        # Fallback to first 1200 characters if no sections matched
        return f"\n--- USER CONTEXT & PREFERENCES (FROM CONTEXT.md) ---\n{raw[:1200]}\n"

    joined = "\n\n".join(sections)
    return (
        f"\n--- USER CONTEXT & PREFERENCES (PERSISTED IN CONTEXT.md) ---\n"
        f"You must strictly respect and adapt to the following user profile and learned preferences:\n"
        f"{joined}\n"
        f"-----------------------------------------------------------\n"
    )


def detect_and_apply_preference_update(user_prompt: str) -> tuple[bool, str]:
    """
    Scans the user's prompt for explicit preference statements or commands to remember,
    e.g.:
      - "remember that I prefer..."
      - "from now on always..."
      - "my default OS is..."
      - "note that I work on..."
      - "set my preferred theme to..."
    Updates CONTEXT.md dynamically and adds a Changelog entry.
    Returns (was_updated, change_description).
    """
    if not user_prompt:
        return False, ""

    prompt_clean = user_prompt.strip()
    lowered = prompt_clean.lower()

    # Trigger patterns
    patterns = [
        r'(?:please\s+)?remember\s+(?:that\s+)?(.+)',
        r'from\s+now\s+on(?:\s*,\s*|\s+)(?:always\s+)?(.+)',
        r'my\s+preferred\s+(?:tool|distro|os|language|style|model)\s+is\s+(.+)',
        r'(?:i\s+prefer|i\s+always\s+use)\s+(.+)',
        r'note\s+that\s+(?:i\s+)?(.+)',
        r'update\s+(?:my\s+)?preferences?\s+(?:to\s+|with\s+)?(.+)'
    ]

    matched_pref = None
    for pat in patterns:
        m = re.search(pat, prompt_clean, re.IGNORECASE)
        if m:
            matched_pref = m.group(1).strip().rstrip('.?!')
            break

    if not matched_pref:
        return False, ""

    # Clean matched preference
    matched_pref = re.sub(r'^(to\s+|that\s+)', '', matched_pref, flags=re.IGNORECASE).strip()
    if len(matched_pref) < 4 or len(matched_pref) > 200:
        return False, ""

    raw = read_context_raw()
    if not raw:
        return False, ""

    # Don't add duplicate
    if matched_pref.lower() in raw.lower():
        return False, f"Already recorded: {matched_pref}"

    # Inject into "Learned Preferences -> Answer Style" or general list
    today = datetime.now().strftime("%Y-%m-%d")
    bullet = f"- User specified ({today}): {matched_pref}"

    # Find insertion point under Learned Preferences
    pref_header = "## Learned Preferences"
    if pref_header in raw:
        # Insert bullet right after the header
        target = pref_header + "\n"
        replacement = f"{target}\n{bullet}"
        raw = raw.replace(target, replacement, 1)
    else:
        raw += f"\n\n## Learned Preferences\n\n{bullet}\n"

    # Add Changelog entry
    changelog_header = "## Changelog"
    table_row = f"| {today} | Learned preference: {matched_pref[:50]}... | PRAG Model Self-Edit |\n"
    if changelog_header in raw:
        lines = raw.split("\n")
        new_lines = []
        in_changelog = False
        inserted = False
        for line in lines:
            new_lines.append(line)
            if "## Changelog" in line:
                in_changelog = True
            elif in_changelog and line.startswith("|---|"):
                new_lines.append(f"| {today} | Learned preference: {matched_pref[:45]} | Model Self-Edit |")
                inserted = True
                in_changelog = False
        if not inserted:
            new_lines.append(f"| {today} | Learned preference: {matched_pref[:45]} | Model Self-Edit |")
        raw = "\n".join(new_lines)
    else:
        raw += f"\n\n## Changelog\n\n| Date | Change | Made By |\n|---|---|---|\n{table_row}"

    success = write_context_raw(raw)
    if success:
        return True, f"Learned and saved preference: {matched_pref}"
    return False, "Failed to write context update"
