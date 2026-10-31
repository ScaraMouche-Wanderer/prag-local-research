#!/usr/bin/env python3
"""
Response parser module for extracting structured metadata from model answer text.
Parses confidence level, reasoning, cited sources, thinking process (<think>),
UNKNOWN status, and actual reported conflicts.
"""

import re

# Phrases indicating that the model actively noted a conflict or contradiction between sources
CONFLICT_INDICATOR_PATTERNS = [
    r'\bconflicts?\b',
    r'\bdisagrees?\b',
    r'\bdiscrepanc(?:y|ies)\b',
    r'\bcontradict(?:s|ion|ory)?\b',
    r'\bdiffers?\s+from\b',
    r'\bdiffers?\s+between\b',
    r'\bmore\s+authoritative\b',
    r'\bin\s+contrast\s+to\b',
    r'\bdisputed\b',
    r'\binconsistent\b'
]


def detect_actual_conflict(answer_text: str, reason: str = "", potential_conflict: bool = False) -> dict:
    """
    Evaluates whether the LLM's actual answer or reason explicitly states a conflict/disagreement.
    Eliminates alert fatigue by only flagging conflict when sources actually disagree in the answer.
    """
    if not potential_conflict:
        return {"has_conflict": False, "reason": "Single tier / coherent sources"}

    combined_text = f"{answer_text}\n{reason}".lower()
    
    for pat in CONFLICT_INDICATOR_PATTERNS:
        if re.search(pat, combined_text):
            return {
                "has_conflict": True,
                "reason": "Model explicitly reported contradiction/disagreement between retrieved tiers."
            }

    return {"has_conflict": False, "reason": "Multi-tier sources retrieved, but no contradiction reported."}


def parse_answer_metadata(raw_answer: str, potential_conflict: bool = False) -> dict:
    """
    Extracts structured metadata from model response and strips all metadata lines from answer_text.
    """
    if not raw_answer or not raw_answer.strip():
        return {
            "answer_text": "",
            "thinking_process": "",
            "confidence": "Unknown",
            "confidence_level": 0,
            "reason": "Empty response from model",
            "sources": [],
            "is_unknown": True,
            "has_conflict": False
        }

    working_text = raw_answer.strip()
    thinking_process = ""

    # Extract <think>...</think> block if present
    if "<think>" in working_text:
        think_match = re.search(r'<think>(.*?)(?:</think>|$)', working_text, flags=re.DOTALL)
        if think_match:
            thinking_process = think_match.group(1).strip()
            working_text = re.sub(r'<think>.*?</think>', '', working_text, flags=re.DOTALL).strip()
            if "<think>" in working_text:
                working_text = working_text.split("<think>")[0].strip()

    lines = working_text.strip().split("\n")
    
    confidence = "Unknown"
    reason = ""
    sources = []
    metadata_line_indices = set()

    for idx, line in enumerate(lines):
        stripped = line.strip()
        
        # Match Confidence line across all markdown formats (#, ##, ###, ####, -, *, **, >, 1., etc.)
        conf_match = re.match(
            r'^(?:[#\-\*•\>\d\.\s]*)(?:\*\*)?Confidence(?:\*\*)?:\s*(?:\*\*)?(.+?)(?:\*\*)?$',
            stripped,
            re.IGNORECASE
        )
        if conf_match:
            conf_raw = conf_match.group(1).strip().strip('*_`').strip()
            if 'high' in conf_raw.lower():
                confidence = "High"
            elif 'medium' in conf_raw.lower():
                confidence = "Medium"
            elif 'low' in conf_raw.lower():
                confidence = "Low"
            else:
                confidence = conf_raw.capitalize()
            metadata_line_indices.add(idx)
            continue
        
        # Match Reason line across markdown formats
        reason_match = re.match(
            r'^(?:[#\-\*•\>\d\.\s]*)(?:\*\*)?Reason(?:\*\*)?:\s*(.+)$',
            stripped,
            re.IGNORECASE
        )
        if reason_match:
            reason = reason_match.group(1).strip().strip('*_`').strip()
            metadata_line_indices.add(idx)
            continue
        
        # Match Sources line across markdown formats
        sources_match = re.match(
            r'^(?:[#\-\*•\>\d\.\s]*)(?:\*\*)?Sources?(?:\*\*)?:\s*(.+)$',
            stripped,
            re.IGNORECASE
        )
        if sources_match:
            sources_raw = sources_match.group(1).strip().strip('*_`').strip()
            bracket_refs = re.findall(r'\[(\d+)\]', sources_raw)
            if bracket_refs:
                sources = [f"[{r}]" for r in bracket_refs]
            else:
                sources = [
                    s.strip().strip('"\'`')
                    for s in sources_raw.split(",")
                    if s.strip() and s.strip().lower() not in ('none', 'n/a', 'general reasoning')
                ]
            metadata_line_indices.add(idx)
            continue

    # Build clean answer text without metadata lines
    answer_lines = []
    for idx, line in enumerate(lines):
        if idx not in metadata_line_indices:
            # Extra safety check for lines that only contain metadata variations
            clean_line = re.sub(
                r'^(?:[#\-\*•\>\d\.\s]*)(?:\*\*)?(?:Confidence|Reason|Sources?)(?:\*\*)?:.*$',
                '',
                line.strip(),
                flags=re.IGNORECASE
            )
            if clean_line != line.strip():
                continue
            answer_lines.append(line)
    
    # Strip trailing empty lines
    while answer_lines and not answer_lines[-1].strip():
        answer_lines.pop()
    
    answer_text = "\n".join(answer_lines).strip()
    
    # If answer_text is empty but we have thinking_process, extract any final response from thinking
    if not answer_text and thinking_process:
        answer_text = thinking_process
    
    # If confidence wasn't explicitly output by the model but a comprehensive answer was provided
    if confidence == "Unknown" and len(answer_text) > 40:
        if "unknown" not in answer_text[:60].lower():
            confidence = "High" if len(answer_text) > 120 else "Medium"

    # Check if the answer is UNKNOWN
    is_unknown = False
    if not answer_text or not answer_text.strip():
        is_unknown = True
    else:
        first_line = answer_text.split('\n')[0].strip()
        if first_line.upper().startswith("UNKNOWN") and len(first_line) < 30:
            is_unknown = True

    conf_levels = {"High": 3, "Medium": 2, "Low": 1, "Unknown": 0}
    confidence_level = conf_levels.get(confidence, 0)

    conflict_info = detect_actual_conflict(answer_text, reason=reason, potential_conflict=potential_conflict)

    return {
        "answer_text": answer_text,
        "thinking_process": thinking_process,
        "confidence": confidence,
        "confidence_level": confidence_level,
        "reason": reason,
        "sources": sources,
        "is_unknown": is_unknown,
        "has_conflict": conflict_info["has_conflict"],
        "conflict_reason": conflict_info["reason"]
    }
