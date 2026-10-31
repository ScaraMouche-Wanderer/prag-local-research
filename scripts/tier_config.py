#!/usr/bin/env python3
"""
Centralized Source Tier Configuration & Resolution Module.
Single source of truth for source trust levels and authority ranking.
"""

TIER_DEFINITIONS = {
    1.0: {
        "name": "Primary",
        "source_types": ["local_file", "kali_docs"],
        "doc_versions": ["man", "help"],
        "description": "Your local files, official man pages, live --help output"
    },
    1.5: {
        "name": "Primary (static fallback)",
        "source_types": ["kali_docs"],
        "doc_versions": ["fallback"],
        "description": "Hardcoded fallback tool docs — tool not installed, unverified live"
    },
    2.0: {
        "name": "Secondary",
        "source_types": ["web_fallback"],
        "sources": ["Wikipedia"],
        "description": "Wikipedia, established technical references"
    },
    3.0: {
        "name": "Community",
        "source_types": ["web_fallback"],
        "sources": ["DuckDuckGo Web Search"],
        "description": "General web search, forums, unverified web snippets"
    }
}

def get_tier(source_type: str, doc_version: str = None, source_name: str = None) -> float:
    """
    Single function every script calls to determine source tier rating.
    Returns float (1.0, 1.5, 2.0, or 3.0).
    """
    if source_type == "local_file":
        return 1.0

    if source_type == "kali_docs":
        if doc_version in ("man", "help"):
            return 1.0
        elif doc_version == "fallback":
            return 1.5
        else:
            return 1.0  # Default for live docs

    if source_type == "web_fallback":
        if source_name and "wikipedia" in source_name.lower():
            return 2.0
        return 3.0

    return 3.0  # Unknown source type = safe default least trusted

def get_tier_label(tier: float) -> str:
    """Returns human-readable label for prompt excerpts and citations."""
    if tier == 1.0:
        return "tier 1.0 — Primary verified"
    elif tier == 1.5:
        return "tier 1.5 — static fallback, unverified live"
    elif tier == 2.0:
        return "tier 2.0 — Secondary Wikipedia"
    elif tier == 3.0:
        return "tier 3.0 — Community web"
    else:
        return f"tier {tier}"

if __name__ == "__main__":
    print("Testing tier_config.py:")
    print("  local_file ->", get_tier("local_file"))
    print("  kali_docs (man) ->", get_tier("kali_docs", doc_version="man"))
    print("  kali_docs (fallback) ->", get_tier("kali_docs", doc_version="fallback"))
    print("  web_fallback (Wikipedia) ->", get_tier("web_fallback", source_name="Wikipedia"))
    print("  web_fallback (DuckDuckGo) ->", get_tier("web_fallback", source_name="DuckDuckGo Web Search"))
