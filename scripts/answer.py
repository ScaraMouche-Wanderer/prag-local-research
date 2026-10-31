#!/usr/bin/env python3
"""
Answer generation module querying Qwen / Llama models via Ollama.
Supports hybrid execution: strict fact grounding in retrieved excerpts
combined with advanced step-by-step logical reasoning, math calculation,
coding, and multi-domain problem solving.
Features robust chunk extraction, streaming thinking (<think>) events,
and error handling with exponential backoff.
"""

import os
import re
import sys
import time
import ollama

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from tier_config import get_tier_label
from context_manager import get_user_context_prompt, detect_and_apply_preference_update

PROMPT_TEMPLATE = """You are an advanced reasoning and research engine. Answer the user's question accurately, thoughtfully, and with rigorous logic.

--- CONTEXT EXCERPTS (IF APPLICABLE) ---
{excerpts_text}

--- QUESTION / PROBLEM ---
{user_question}

--- INSTRUCTIONS ---
1. EVIDENCE GROUNDING: If the question refers to specific facts, tools, or local files and excerpts are provided above, ground your claims in those excerpts and cite them using bracketed numbers like [1], [2].{conflict_notice}
2. LOGICAL REASONING & SYNTHESIS: If the question requires logical reasoning, deduction, mathematics, programming/code, comparative analysis, or general problem solving, provide a clear, structured, step-by-step solution.
3. CLARITY & STRUCTURE:
   - Start with a direct 1-2 sentence core conclusion/summary.
   - Use clear sections, bullet points, and bold key terms.
   - Format any code or commands in markdown code blocks with clear explanations.
   - Show mathematical derivations or logical steps clearly.
   - Be concise and focused; avoid unnecessary conversational filler.
4. HONESTY: If a specific factual query cannot be answered or deduced from the provided excerpts and is not a general reasoning question, state what is unknown clearly.

After your complete answer, on separate lines at the very end, provide:
Confidence: High / Medium / Low
Reason: <one sentence summarizing evidence quality or logical deduction>
Sources: <list excerpt numbers used like [1], [2] or 'General Reasoning' / 'None'>
"""

# Domain-specific system prompt extensions for expert-level answers
DOMAIN_SYSTEM_PROMPTS = {
    "electronics": (
        "You are an expert electronics engineer with deep knowledge of circuit design, "
        "embedded systems, PCB layout, and signal processing. Use precise technical terminology. "
        "When discussing circuits, include component values, pin configurations, and operating conditions. "
        "For embedded systems, include register-level details, timing constraints, and power considerations. "
        "Reference relevant standards (IEEE, IPC) and include practical design rules of thumb."
    ),
    "software_eng": (
        "You are a senior software architect with expertise in system design, design patterns, "
        "distributed systems, and DevOps. Discuss trade-offs, scalability, and maintainability. "
        "Include code examples in the most appropriate language. Reference established patterns, "
        "principles (SOLID, DRY, KISS), and industry best practices. Address performance implications."
    ),
    "economics": (
        "You are an economics analyst with expertise in both micro and macroeconomics, financial markets, "
        "and quantitative finance. Use precise economic terminology and mathematical formulations. "
        "Distinguish between micro and macroeconomic perspectives. Include quantitative analysis, "
        "graphs descriptions, and real-world examples. Reference established economic theories and models."
    ),
    "kali_docs": (
        "You are a cybersecurity specialist and Linux systems expert. Provide precise command syntax, "
        "explain security implications, and include practical examples. Reference tool documentation "
        "and security best practices."
    ),
}

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert research and reasoning assistant. Provide logical, well-structured, "
    "and accurate answers with step-by-step reasoning when appropriate."
)


def detect_potential_conflict(chunks: list[dict]) -> dict:
    """
    Detects if retrieved excerpts draw from multiple trust tiers or source types.
    """
    if not chunks:
        return {"has_conflict": False, "higher_tier": 1.0, "lower_tier": 1.0}

    tiers = set(c.get('tier', 1.0) for c in chunks)
    sources = set(c.get('source_type', 'local_file') for c in chunks)

    if len(tiers) > 1 and len(sources) > 1:
        return {"has_conflict": True, "higher_tier": min(tiers), "lower_tier": max(tiers)}
    return {"has_conflict": False, "higher_tier": min(tiers) if tiers else 1.0, "lower_tier": max(tiers) if tiers else 1.0}


# Compact tier labels for LLM prompt context (saves tokens vs verbose labels)
PROMPT_TIER_LABELS = {
    1.0: "T1-Primary",
    1.5: "T1.5-Fallback",
    2.0: "T2-Wikipedia",
    3.0: "T3-Web"
}


def _extract_chunk_text(chunk) -> tuple[str, str]:
    """Robustly extracts response and thinking text from dict or Pydantic object (supports both generate and chat formats)."""
    resp = ""
    thinking = ""

    # Check for chat format message
    if hasattr(chunk, 'message') and chunk.message:
        msg = chunk.message
        if hasattr(msg, 'content') and msg.content:
            resp = str(msg.content)
        elif isinstance(msg, dict) and msg.get('content'):
            resp = str(msg['content'])
        if hasattr(msg, 'thinking') and msg.thinking:
            thinking = str(msg.thinking)
        elif isinstance(msg, dict) and msg.get('thinking'):
            thinking = str(msg['thinking'])

    # Check for generate format
    if not resp and hasattr(chunk, 'response') and chunk.response:
        resp = str(chunk.response)
    elif not resp and isinstance(chunk, dict) and chunk.get('response'):
        resp = str(chunk['response'])

    if not thinking and hasattr(chunk, 'thinking') and chunk.thinking:
        thinking = str(chunk.thinking)
    elif not thinking and isinstance(chunk, dict) and chunk.get('thinking'):
        thinking = str(chunk['thinking'])

    return resp, thinking


def _classify_ollama_error(error: Exception) -> dict:
    """Classifies Ollama errors into user-friendly categories."""
    err_str = str(error).lower()
    
    if "connection refused" in err_str or "connect" in err_str:
        return {
            "category": "connection",
            "title": "Ollama Not Running",
            "message": "Cannot connect to Ollama. Start it with: ollama serve",
            "retryable": True
        }
    elif "not found" in err_str or "404" in err_str:
        return {
            "category": "model_missing",
            "title": "Model Not Found",
            "message": "Model not installed. Run: ollama pull qwen3:8b",
            "retryable": False
        }
    elif "timeout" in err_str or "timed out" in err_str:
        return {
            "category": "timeout",
            "title": "Model Loading",
            "message": "Ollama is loading the model into memory. Retrying...",
            "retryable": True
        }
    elif "busy" in err_str or "overloaded" in err_str:
        return {
            "category": "busy",
            "title": "Model Busy",
            "message": "Ollama is processing another request. Retrying...",
            "retryable": True
        }
    else:
        return {
            "category": "unknown",
            "title": "Ollama Error",
            "message": f"Unexpected error: {error}",
            "retryable": False
        }


def get_best_available_model(preferred: str = None) -> str:
    """
    Auto-detects the best available Ollama model.
    Prioritizes high-capacity reasoning models:
    qwen3:8b > qwen2.5:3b > llama3.2:latest > llama3.2
    """
    if preferred:
        return preferred

    env_model = os.getenv("RAG_MODEL")
    if env_model:
        return env_model

    try:
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        client = ollama.Client(host=host)
        models_info = client.list()
        installed = []
        if hasattr(models_info, 'models'):
            installed = [m.model for m in models_info.models]
        elif isinstance(models_info, dict) and 'models' in models_info:
            installed = [m.get('name') or m.get('model') for m in models_info['models']]

        candidates = ["qwen3:8b", "qwen2.5:3b", "llama3.2:latest", "llama3.2"]
        for cand in candidates:
            for inst in installed:
                if cand in inst:
                    return inst
    except Exception:
        pass

    return "qwen3:8b"


INSUFFICIENT_EVIDENCE = (
    "UNKNOWN\n\n"
    "Confidence: Low\n"
    "Reason: No usable source excerpts were retrieved for this factual question.\n"
    "Sources: None"
)


def lookup_option_definition(question: str, chunks: list[dict]) -> str | None:
    """Answer a single CLI-option lookup directly when sources agree on its definition."""
    flags = list(dict.fromkeys(re.findall(r"(?<!\w)--?[A-Za-z][A-Za-z0-9-]*", question)))
    if len(flags) != 1 or not re.search(r"\b(what|meaning|explain|define|does|option|flag)\b", question, re.I):
        return None
    flag = flags[0]
    pattern = re.compile(r"^\s*" + re.escape(flag) + r"(?:\s*:\s*|\s{2,})(.+)$", re.M)
    definitions = {}
    for index, chunk in enumerate(chunks, start=1):
        match = pattern.search(chunk.get("chunk_text", ""))
        if match:
            definition = match.group(1).strip()
            definitions.setdefault(definition.casefold(), (definition, index))
    if len(definitions) != 1:
        return None
    definition, index = next(iter(definitions.values()))
    return (
        f"`{flag}`: {definition} [{index}]\n\n"
        "Confidence: High\n"
        "Reason: Exact option definition read directly from the retrieved documentation.\n"
        f"Sources: [{index}]"
    )


def select_evidence_window(text: str, question: str = "", limit: int = 500) -> str:
    """Keep the requested option/term visible instead of always truncating the document header."""
    text = text.strip()
    if len(text) <= limit:
        return text
    # CLI option spelling is case-sensitive: -sV and -sv are not interchangeable.
    flags = re.findall(r"(?<!\w)--?[A-Za-z][A-Za-z0-9-]*", question)
    position = next((text.find(flag) for flag in flags if flag in text), -1)
    if position < 0:
        terms = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", question)), key=len, reverse=True)
        position = next((text.lower().find(term.lower()) for term in terms if term.lower() in text.lower()), 0)
    start = max(0, position - limit // 3)
    # Prefer a complete line, while retaining enough room for the matched term.
    boundary = text.rfind("\n", max(0, start - 80), start)
    if boundary >= 0 and position - boundary < limit - 80:
        start = boundary + 1
    prefix = "[…] " if start else ""
    end = min(len(text), start + limit - len(prefix) - 4)
    suffix = " […]" if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def format_excerpts_block(retrieved_chunks: list[dict], question: str = "") -> str:
    """Formats retrieved chunks into clean numbered reference blocks."""
    if not retrieved_chunks:
        return "No specific database excerpts retrieved. Factual answers must be UNKNOWN without supporting evidence."

    excerpts_list = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        filename = chunk.get('file_name', 'Unknown')
        page = chunk.get('page_number', 1)
        text = select_evidence_window(chunk.get('chunk_text', ''), question)
        doc_ver = chunk.get('doc_version')
        tier = chunk.get('tier', 1.0)
        tier_label = PROMPT_TIER_LABELS.get(tier, f"T{tier}")
        version_str = f", v:{doc_ver}" if doc_ver else ""
        excerpts_list.append(f"[{idx}] {filename} ({tier_label}{version_str}), p{page}\n{text}\n")

    return "\n".join(excerpts_list)


def _clean_assistant_content(text: str) -> str:
    """Removes thinking blocks from previous assistant turns to keep context window compact."""
    if not text:
        return ""
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
    return cleaned


def build_chat_messages(user_question: str, retrieved_chunks: list[dict] = None,
                        route: str = None, history: list[dict] = None) -> tuple[list[dict], str]:
    """
    Builds the messages array for Ollama client.chat and returns (messages, raw_prompt_fallback).
    """
    retrieved_chunks = retrieved_chunks or []
    excerpts_text = format_excerpts_block(retrieved_chunks, user_question)
    
    conflict_info = detect_potential_conflict(retrieved_chunks)
    conflict_notice = ""
    if conflict_info["has_conflict"]:
        conflict_notice = (
            f"\nNOTICE: This answer draws from BOTH a Tier {conflict_info['higher_tier']} source and a Tier {conflict_info['lower_tier']} source. "
            "If they disagree on any fact, state both versions explicitly and explain which is more authoritative."
        )

    # Check for self-updating user preferences
    detect_and_apply_preference_update(user_question)
    user_context = get_user_context_prompt()

    base_system = DOMAIN_SYSTEM_PROMPTS.get(route, DEFAULT_SYSTEM_PROMPT)
    system_instruction = (
        f"{base_system}\n\n"
        f"{user_context}\n"
        "You are an advanced reasoning and research engine. Answer the user's questions accurately, thoughtfully, and with rigorous logic.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. CONVERSATION CONTINUITY & CONTEXT: Maintain continuity with the prior conversation. "
        "When the user asks follow-up questions, refers to previous answers, or uses pronouns ('it', 'that', 'the tool', 'the first scan'), "
        "always use the preceding conversation context to understand what they are referring to and answer accurately.\n"
        "2. EVIDENCE GROUNDING: If context excerpts are provided for the question, ground your claims in those excerpts and cite them using bracketed numbers like [1], [2]."
        " Cite only excerpt numbers that actually support the claim. Never invent quotations or section names."
        " If the excerpts omit the requested fact, answer UNKNOWN and explain the evidence gap."
        " Keep the answer focused; do not repeat whole source excerpts."
        " For a single command-option question, quote its matching definition and explain only that definition."
        " Do not add alternate options or extra command examples unless the user asks for them."
        f"{conflict_notice}\n"
        "3. LOGICAL REASONING: If the question requires problem solving, code, linux commands, or mathematics, show step-by-step logic.\n"
        "4. CLARITY & STRUCTURE: Start with a clear direct conclusion. Use clear sections, bullet points, and code blocks.\n"
        "5. HONESTY: If something cannot be deduced from excerpts or foundational knowledge, state what is unknown clearly.\n\n"
        "After your complete answer, on separate lines at the very end, provide:\n"
        "Confidence: High / Medium / Low\n"
        "Reason: <one sentence summarizing evidence quality or logical deduction>\n"
        "Sources: <list excerpt numbers used like [1], [2] or 'Conversation Context' / 'General Reasoning' / 'None'>"
    )

    messages = [{"role": "system", "content": system_instruction}]

    # Include sanitized recent history (up to last 10 messages)
    if history:
        recent_history = history[-10:]
        for item in recent_history:
            role = item.get("role", "user")
            content = item.get("content", "")
            if not content:
                continue
            if role == "assistant":
                content = _clean_assistant_content(content)
            messages.append({"role": role, "content": content})

    # Build current user turn content with excerpts
    current_content = ""
    if excerpts_text and "No specific database excerpts retrieved" not in excerpts_text:
        current_content += f"--- CONTEXT EXCERPTS (IF APPLICABLE) ---\n{excerpts_text}\n\n"
    current_content += f"--- QUESTION / PROBLEM ---\n{user_question}"

    messages.append({"role": "user", "content": current_content})

    # Fallback raw prompt for client.generate
    history_str = ""
    if history:
        hist_parts = []
        for h in history[-6:]:
            r = "User" if h.get("role") == "user" else "Assistant"
            c = _clean_assistant_content(h.get("content", ""))
            if c:
                hist_parts.append(f"{r}: {c}")
        if hist_parts:
            history_str = "\n--- PREVIOUS CONVERSATION CONTEXT ---\n" + "\n".join(hist_parts) + "\n"

    fallback_prompt = (
        f"{system_instruction}\n"
        f"{history_str}\n"
        f"--- CONTEXT EXCERPTS (IF APPLICABLE) ---\n{excerpts_text}\n\n"
        f"--- CURRENT QUESTION / FOLLOW-UP ---\n{user_question}\n"
    )

    return messages, fallback_prompt


def generate_answer(user_question: str, retrieved_chunks: list[dict] = None,
                    model_name: str = None, max_retries: int = 2, route: str = None,
                    history: list[dict] = None) -> str:
    """Generates a complete answer using Qwen/Ollama with multi-turn conversation memory, retry logic, and reasoning support."""
    retrieved_chunks = retrieved_chunks or []
    if route not in ("reasoning_general", "math_code") and not any(
        chunk.get("chunk_text", "").strip() for chunk in retrieved_chunks
    ):
        return INSUFFICIENT_EVIDENCE
    definition = lookup_option_definition(user_question, retrieved_chunks)
    if definition:
        return definition
    model_name = get_best_available_model(model_name)

    messages, fallback_prompt = build_chat_messages(user_question, retrieved_chunks, route=route, history=history)

    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    client = ollama.Client(host=host)
    
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            # First attempt client.chat
            try:
                response = client.chat(
                    model=model_name,
                    messages=messages,
                    keep_alive="30m",
                    options={
                        "num_predict": 2048,
                        "temperature": 0.2,
                        "top_k": 40
                    }
                )
            except Exception as chat_err:
                # Fallback to client.generate if chat is not supported
                response = client.generate(
                    model=model_name,
                    prompt=fallback_prompt,
                    keep_alive="30m",
                    options={
                        "num_predict": 2048,
                        "temperature": 0.2,
                        "top_k": 40
                    }
                )
            
            raw_text, thinking = _extract_chunk_text(response)

            if not raw_text and not thinking:
                raw_text = "Unable to generate answer."

            # Preserve thinking block if present or format cleanly
            if thinking and "<think>" not in raw_text:
                full_output = f"<think>\n{thinking.strip()}\n</think>\n\n{raw_text.strip()}"
            else:
                full_output = raw_text.strip()

            return full_output
        except Exception as e:
            last_error = e
            error_info = _classify_ollama_error(e)
            
            if not error_info["retryable"] or attempt >= max_retries:
                break
            
            wait_time = (attempt + 1) * 1.0
            print(f"[RETRY] {error_info['title']} — retrying in {wait_time:.0f}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait_time)
    
    error_info = _classify_ollama_error(last_error)
    return (
        f"⚠️ {error_info['title']}\n\n"
        f"{error_info['message']}\n\n"
        "Confidence: Low\n"
        "Reason: Could not reach the reasoning model.\n"
        "Sources: None"
    )


def generate_answer_streaming(user_question: str, retrieved_chunks: list[dict] = None,
                              model_name: str = None, route: str = None,
                              history: list[dict] = None):
    """
    Generator that yields tuples of (event_type, text_chunk) with multi-turn conversation memory:
      - ("think", thinking_token) : Chain-of-thought tokens inside <think>...</think>
      - ("token", response_token) : Main response tokens
    """
    retrieved_chunks = retrieved_chunks or []
    if route not in ("reasoning_general", "math_code") and not any(
        chunk.get("chunk_text", "").strip() for chunk in retrieved_chunks
    ):
        yield ("token", INSUFFICIENT_EVIDENCE)
        return
    definition = lookup_option_definition(user_question, retrieved_chunks)
    if definition:
        yield ("token", definition)
        return
    model_name = get_best_available_model(model_name)

    messages, fallback_prompt = build_chat_messages(user_question, retrieved_chunks, route=route, history=history)

    try:
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        client = ollama.Client(host=host)
        
        in_think_tag = False
        buffer = ""

        # Stream via client.chat
        stream_iter = None
        try:
            stream_iter = client.chat(
                model=model_name,
                messages=messages,
                stream=True,
                keep_alive="30m",
                options={
                    "num_predict": 2048,
                    "temperature": 0.2,
                    "top_k": 40
                }
            )
        except Exception:
            # Fallback to generate if client.chat fails
            stream_iter = client.generate(
                model=model_name,
                prompt=fallback_prompt,
                stream=True,
                keep_alive="30m",
                options={
                    "num_predict": 2048,
                    "temperature": 0.2,
                    "top_k": 40
                }
            )

        for chunk in stream_iter:
            resp, thinking = _extract_chunk_text(chunk)
            
            if thinking:
                yield ("think", thinking)

            if resp:
                # Detect inline <think> tags in response stream
                combined = buffer + resp
                if "<think>" in combined and "</think>" not in combined:
                    in_think_tag = True
                    clean_chunk = combined.replace("<think>", "")
                    if clean_chunk:
                        yield ("think", clean_chunk)
                    buffer = ""
                elif "</think>" in combined:
                    in_think_tag = False
                    parts = combined.split("</think>", 1)
                    if parts[0].replace("<think>", ""):
                        yield ("think", parts[0].replace("<think>", ""))
                    if parts[1]:
                        yield ("token", parts[1])
                    buffer = ""
                else:
                    if in_think_tag:
                        yield ("think", resp)
                    else:
                        yield ("token", resp)
                    buffer = ""
    except Exception as e:
        error_info = _classify_ollama_error(e)
        yield ("token", f"\n\n⚠️ {error_info['title']}: {error_info['message']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python answer.py <question>")
        sys.exit(1)

    question = sys.argv[1]
    print(f"Generating answer for: {question} ...\n")
    print(generate_answer(question))
