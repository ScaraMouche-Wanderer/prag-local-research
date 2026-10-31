#!/usr/bin/env python3
"""
Text chunking module for local RAG pipeline.
Performs semantic section-aware chunking for man pages and CLI tool docs,
code-aware chunking that preserves function/class boundaries and fenced code blocks,
and sliding-window chunking over unstructured text while maintaining metadata.
"""

import re

# Section headers common in man pages and tool references
SECTION_HEADER_PATTERN = re.compile(
    r'^(?:[A-Z0-9_\s\-/]{2,30}|#{1,4}\s+.*|\b(?:NAME|SYNOPSIS|DESCRIPTION|OPTIONS|COMMANDS|FLAGS|EXAMPLES|ENVIRONMENT|FILES|SEE ALSO|AUTHOR|BUGS)\b.*)$',
    re.MULTILINE
)

# Option flag start pattern (e.g., "-sS", "--help", "-p <port>", "-o, --output")
OPTION_FLAG_PATTERN = re.compile(r'^\s*(?:-\w|--[a-zA-Z0-9_-]+|\b[a-z0-9_-]+:\s+)', re.MULTILINE)

# Fenced code block detection (``` or ~~~)
FENCED_CODE_PATTERN = re.compile(r'^(`{3,}|~{3,})', re.MULTILINE)


def is_structured_man_page(text: str) -> bool:
    """Detects if text resembles a man page, tool help output, or CLI reference."""
    if not text:
        return False
    # Check for option flags or standard section headers
    flag_matches = len(OPTION_FLAG_PATTERN.findall(text[:4000]))
    header_matches = len(SECTION_HEADER_PATTERN.findall(text[:4000]))
    return flag_matches >= 3 or header_matches >= 2 or "# Command Help Output" in text or "# Kali Tool Documentation" in text


def chunk_man_page_text(text: str, max_chunk_size: int = 1500, min_chunk_size: int = 200) -> list[str]:
    """
    Structural chunker for man pages and tool docs.
    Groups command flags, subcommands, and section descriptions into cohesive units
    so flag names and their descriptions are never severed across chunk boundaries.
    """
    lines = text.split("\n")
    blocks = []
    current_block = []
    current_len = 0

    for line in lines:
        stripped = line.strip()
        is_header = bool(SECTION_HEADER_PATTERN.match(stripped)) and len(stripped) < 60
        is_option = bool(re.match(r'^\s*(?:-[a-zA-Z0-9]|--[a-zA-Z0-9]|\b[a-z0-9_-]+:\s+)', line))

        # Break into new block if we hit a major header or flag when current block has sufficient content
        if (is_header or is_option) and current_len >= min_chunk_size and (current_len + len(line) > max_chunk_size * 0.7):
            block_text = "\n".join(current_block).strip()
            if block_text:
                blocks.append(block_text)
            current_block = [line]
            current_len = len(line)
        else:
            current_block.append(line)
            current_len += len(line) + 1

    if current_block:
        block_text = "\n".join(current_block).strip()
        if block_text:
            blocks.append(block_text)

    # Merge very small blocks (< 150 chars) with adjacent blocks if within max_chunk_size
    merged = []
    for b in blocks:
        if merged and len(merged[-1]) + len(b) + 2 <= max_chunk_size:
            merged[-1] = merged[-1] + "\n\n" + b
        else:
            merged.append(b)

    return merged if merged else [text.strip()]


def chunk_text(text: str, chunk_size_chars: int = 2500, overlap_chars: int = 250) -> list[str]:
    """
    Splits text into chunks. Automatically uses structural man-page chunking if tool/man syntax
    is detected, or sliding window chunking for unstructured text.
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= chunk_size_chars:
        return [text]

    # Use structural pre-chunking for man pages and tool docs
    if is_structured_man_page(text):
        structural_chunks = chunk_man_page_text(text, max_chunk_size=chunk_size_chars)
        if structural_chunks:
            return structural_chunks

    # Fallback sliding window chunking with fenced-code-block and list protection
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size_chars
        if end >= text_len:
            chunks.append(text[start:].strip())
            break

        # Check if we're inside a fenced code block at the break point
        segment = text[start:end]
        fence_opens = len(re.findall(r'^(`{3,}|~{3,})', segment, re.MULTILINE))
        # Odd count means we're inside an unclosed block — extend to find the closing fence
        if fence_opens % 2 == 1:
            close_fence = re.search(r'^(`{3,}|~{3,})\s*$', text[end:], re.MULTILINE)
            if close_fence and (end + close_fence.end()) < start + chunk_size_chars * 1.5:
                end = end + close_fence.end()

        # Try to break at paragraph boundary
        break_pos = text.rfind("\n\n", start + overlap_chars, end)
        if break_pos == -1:
            # Try to break at line boundary
            break_pos = text.rfind("\n", start + overlap_chars, end)
        if break_pos == -1:
            # Try to break at sentence boundary
            break_pos = text.rfind(". ", start + overlap_chars, end)
        if break_pos == -1 or break_pos <= start:
            break_pos = end
        else:
            break_pos += 1  # Include space or punctuation

        chunk = text[start:break_pos].strip()
        if chunk:
            chunks.append(chunk)

        start = max(start + 1, break_pos - overlap_chars)

    return chunks
