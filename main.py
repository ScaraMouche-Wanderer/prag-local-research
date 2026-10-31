#!/usr/bin/env python3
"""
Main CLI entry point for Local Fact-Grounded RAG System.
Commands:
  python main.py ask "<question>" [-v] [--source local|kali|electronics|software|economics|all] [--json] [--full-evidence]
  python main.py history [--limit 10]
  python main.py stats [--json]
  python main.py status
  python main.py sources
  python main.py seed
  python main.py ingest
  python main.py sync-kali
  python main.py serve [--port 8000]
"""

import os
import sys
import time
import json
import sqlite3
import argparse
import logging

# Cleanly suppress background library warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

# Ensure scripts directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from ingest import run_ingestion
from sync_kali_docs import sync_kali_docs
from tier_config import get_tier_label
from response_parser import parse_answer_metadata
from query_log import log_query, init_query_log, get_recent_queries, get_query_stats
from pipeline import run_pipeline

DB_PATH = os.path.join(BASE_DIR, "data", "vectors.db")
PROFILE = os.environ.get("PROFILE") == "1"


def format_latency(ms: float) -> str:
    """Format milliseconds into a clean, human-readable string."""
    if ms <= 0:
        return "0ms"
    if ms < 1000:
        return f"{int(ms)}ms"
    if ms < 60000:
        return f"{ms / 1000:.2f}s"
    return f"{ms / 60000:.1f}m"

# ═══ ANSI Color Codes ═══
class C:
    """ANSI color/style codes — no external dependency."""
    RESET    = "\033[0m"
    BOLD     = "\033[1m"
    DIM      = "\033[2m"
    ITALIC   = "\033[3m"
    CYAN     = "\033[38;5;81m"
    BLUE     = "\033[38;5;69m"
    GREEN    = "\033[38;5;78m"
    YELLOW   = "\033[38;5;221m"
    RED      = "\033[38;5;203m"
    PURPLE   = "\033[38;5;141m"
    GRAY     = "\033[38;5;245m"
    WHITE    = "\033[38;5;255m"
    BG_DARK  = "\033[48;5;235m"
    BG_PANEL = "\033[48;5;236m"

    @staticmethod
    def gradient(text: str) -> str:
        """Apply a cyan-to-purple gradient effect to text."""
        colors = [81, 75, 69, 105, 141]
        result = []
        for i, ch in enumerate(text):
            color = colors[i % len(colors)]
            result.append(f"\033[38;5;{color}m{ch}")
        result.append(C.RESET)
        return "".join(result)


def _box_line(char_l: str, char_m: str, char_r: str, width: int = 62) -> str:
    return f"{C.BLUE}{char_l}{char_m * width}{char_r}{C.RESET}"


def _box_text(text: str, width: int = 62) -> str:
    return f"{C.BLUE}│{C.RESET} {text}"


def format_terminal_answer(raw_answer: str, chunks: list[dict], route: str = "", elapsed_ms: int = 0,
                           is_ambiguous: bool = False, full_evidence: bool = False, verbose: bool = False,
                           thinking_process: str = "") -> str:
    """Formats model response with rich ANSI colors for terminal display."""
    parsed = parse_answer_metadata(raw_answer)
    thinking = thinking_process or parsed.get("thinking_process", "")
    lines = []

    # Header
    lines.append("")
    lines.append(_box_line("╭", "─", "╮"))
    lines.append(_box_text(f"{C.BOLD}{C.CYAN}⚡ PRAG Research Engine — Answer{C.RESET}"))
    lines.append(_box_line("├", "─", "┤"))

    # Route & confidence metadata
    conf = parsed["confidence"]
    if conf == "High":
        conf_color = C.GREEN
        conf_icon = "🟢"
    elif conf == "Medium":
        conf_color = C.YELLOW
        conf_icon = "🟡"
    elif conf == "Low":
        conf_color = C.RED
        conf_icon = "🔴"
    else:
        conf_color = C.GRAY
        conf_icon = "⚪"

    meta_parts = []
    if route:
        route_display = f"{C.CYAN}{route}{C.RESET}"
        if is_ambiguous:
            route_display += f" {C.YELLOW}(broad scope){C.RESET}"
        meta_parts.append(f"{C.GRAY}Route:{C.RESET} {route_display}")
    meta_parts.append(f"{C.GRAY}Confidence:{C.RESET} {conf_color}{conf_icon} {conf}{C.RESET}")
    if elapsed_ms > 0:
        meta_parts.append(f"{C.GRAY}Time:{C.RESET} {C.PURPLE}{format_latency(elapsed_ms)}{C.RESET}")
    meta_parts.append(f"{C.GRAY}Chunks:{C.RESET} {C.CYAN}{len(chunks)}{C.RESET}")

    lines.append(_box_text("  ".join(meta_parts)))

    # Thinking Process if present and in verbose/full mode
    if thinking and (verbose or full_evidence):
        lines.append(_box_line("├", "─", "┤"))
        lines.append(_box_text(f"{C.PURPLE}{C.BOLD}🧠 REASONING PROCESS / CHAIN OF THOUGHT{C.RESET}"))
        for tline in thinking.split("\n"):
            lines.append(_box_text(f"{C.DIM}{C.ITALIC}{tline}{C.RESET}"))

    # Conflict warning banner if actual conflict reported
    if parsed.get("has_conflict"):
        lines.append(_box_line("├", "─", "┤"))
        lines.append(_box_text(f"{C.RED}{C.BOLD}⚠️  SOURCE CONFLICT DETECTED{C.RESET}"))
        lines.append(_box_text(f"{C.DIM}Retrieved sources express conflicting information — see answer below.{C.RESET}"))

    lines.append(_box_line("├", "─", "┤"))

    # Answer body
    answer_text = parsed["answer_text"] if parsed["answer_text"] else raw_answer
    for line in answer_text.split("\n"):
        lines.append(_box_text(f"{C.WHITE}{line}{C.RESET}"))

    # Reason
    if parsed["reason"]:
        lines.append(_box_text(""))
        lines.append(_box_text(f"{C.DIM}{C.ITALIC}💡 {parsed['reason']}{C.RESET}"))

    lines.append(_box_line("╰", "─", "╯"))

    # Evidence audit trail
    if chunks:
        lines.append("")
        mode_label = "FULL EVIDENCE AUDIT" if full_evidence else "EVIDENCE TRAIL"
        lines.append(f"  {C.BOLD}{C.GRAY}{mode_label}{C.RESET}")
        lines.append(f"  {C.DIM}{'─' * 56}{C.RESET}")
        for idx, c in enumerate(chunks, start=1):
            tier_val = c.get('tier', 1.0)
            tier_label = get_tier_label(tier_val)

            # Tier color
            if tier_val <= 1.0:
                tier_color = C.GREEN
            elif tier_val <= 1.5:
                tier_color = C.YELLOW
            elif tier_val <= 2.0:
                tier_color = C.PURPLE
            else:
                tier_color = C.RED

            score_str = ""
            if 'rerank_score' in c:
                score = c['rerank_score']
                bar_filled = int(score * 20)
                bar_empty = 20 - bar_filled
                score_str = f" {C.CYAN}{'█' * bar_filled}{C.DIM}{'░' * bar_empty}{C.RESET} {score:.4f}"
            else:
                score_str = f" {C.GRAY}dist: {c.get('distance', 0.0):.4f}{C.RESET}"

            lines.append(f"  {C.CYAN}[{idx}]{C.RESET} {C.WHITE}{c.get('file_name', 'Unknown')}{C.RESET}")
            lines.append(f"      {tier_color}{tier_label}{C.RESET}{score_str}")

            chunk_text = c.get('chunk_text', '')
            if full_evidence:
                lines.append(f"      {C.DIM}┌─ Full Chunk Content ────────────────────────────────────────┐{C.RESET}")
                for chunk_line in chunk_text.split('\n'):
                    lines.append(f"      {C.DIM}│{C.RESET} {chunk_line}")
                lines.append(f"      {C.DIM}└─────────────────────────────────────────────────────────────┘{C.RESET}")
            elif verbose:
                preview = chunk_text[:120].replace('\n', ' ')
                lines.append(f"      {C.DIM}\"{preview}...\" {C.RESET}")

        lines.append("")

    return "\n".join(lines)


def print_status():
    """Prints database and knowledge base status summary with rich formatting."""
    print("")
    print(_box_line("╭", "─", "╮"))
    print(_box_text(f"{C.BOLD}{C.CYAN}⚡ PRAG Knowledge Base Status{C.RESET}"))
    print(_box_line("├", "─", "┤"))

    if not os.path.exists(DB_PATH):
        print(_box_text(f"{C.YELLOW}⚠ Database not found. Run 'ingest' or 'sync-kali' first.{C.RESET}"))
        print(_box_line("╰", "─", "╯"))
        return

    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(_box_text(f"{C.GRAY}Vector DB:{C.RESET}  {C.WHITE}{DB_PATH}{C.RESET}"))
    print(_box_text(f"{C.GRAY}DB Size:{C.RESET}    {C.CYAN}{db_size:.2f} MB{C.RESET}"))

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT source_type, COUNT(*) FROM chunks GROUP BY source_type;")
        counts = cursor.fetchall()
        print(_box_text(""))
        print(_box_text(f"{C.BOLD}Chunk Distribution:{C.RESET}"))
        for stype, count in counts:
            icon = "📄" if stype == "local_file" else "🛠️" if stype == "kali_docs" else "🌐"
            print(_box_text(f"  {icon} {C.WHITE}{stype:<15}{C.RESET} {C.CYAN}{count:>5}{C.RESET} chunks"))

        cursor.execute("SELECT COUNT(*), MAX(last_synced) FROM kali_sources;")
        kali_info = cursor.fetchone()
        if kali_info and kali_info[0] > 0:
            print(_box_text(""))
            print(_box_text(f"{C.GRAY}Kali Tools:{C.RESET}  {C.GREEN}{kali_info[0]} tools synced{C.RESET}"))
            print(_box_text(f"{C.GRAY}Last Sync:{C.RESET}   {C.WHITE}{kali_info[1]}{C.RESET}"))

        try:
            cursor.execute("SELECT COUNT(*) FROM query_log")
            q_count = cursor.fetchone()[0]
            if q_count > 0:
                cursor.execute("SELECT AVG(latency_ms) FROM query_log WHERE latency_ms > 0")
                avg_lat = cursor.fetchone()[0] or 0
                lat_formatted = format_latency(avg_lat)
                print(_box_text(""))
                print(_box_text(f"{C.GRAY}Queries:{C.RESET}     {C.PURPLE}{q_count} total{C.RESET} (avg {lat_formatted})"))
        except Exception:
            pass

        conn.close()
    except Exception as e:
        print(_box_text(f"{C.RED}Error querying database: {e}{C.RESET}"))

    print(_box_line("╰", "─", "╯"))
    print("")


def print_sources():
    """Lists indexed filenames and Kali tool manuals with rich formatting."""
    print("")
    print(_box_line("╭", "─", "╮"))
    print(_box_text(f"{C.BOLD}{C.CYAN}📚 Indexed Sources & Tool Manuals{C.RESET}"))
    print(_box_line("├", "─", "┤"))

    if not os.path.exists(DB_PATH):
        print(_box_text(f"{C.YELLOW}⚠ Database not found. Run 'ingest' or 'sync-kali' first.{C.RESET}"))
        print(_box_line("╰", "─", "╯"))
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT file_path FROM chunks WHERE source_type = 'local_file';")
        local_files = [os.path.basename(r[0]) for r in cursor.fetchall()]

        print(_box_text(f"{C.BOLD}Local Knowledge Base:{C.RESET}"))
        if local_files:
            for fn in local_files:
                print(_box_text(f"  {C.GREEN}📄{C.RESET} {C.WHITE}{fn}{C.RESET}"))
        else:
            print(_box_text(f"  {C.DIM}(No local files indexed){C.RESET}"))

        cursor.execute("SELECT tool_name, doc_version FROM kali_sources ORDER BY tool_name ASC;")
        kali_tools = cursor.fetchall()

        print(_box_text(""))
        print(_box_text(f"{C.BOLD}Kali & Linux Tool Manuals:{C.RESET}"))
        if kali_tools:
            for tool, ver in kali_tools:
                ver_color = C.GREEN if ver in ("man", "help") else C.YELLOW
                print(_box_text(f"  {C.CYAN}🛠️{C.RESET} {C.WHITE}{tool:<15}{C.RESET} {ver_color}({ver}){C.RESET}"))
        else:
            print(_box_text(f"  {C.DIM}(No Kali docs indexed){C.RESET}"))

        conn.close()
    except Exception as e:
        print(_box_text(f"{C.RED}Error querying sources: {e}{C.RESET}"))

    print(_box_line("╰", "─", "╯"))
    print("")


def print_history(limit: int = 10):
    """Displays recent queries formatted in a rich table."""
    queries = get_recent_queries(limit=limit, db_path=DB_PATH)
    print("")
    print(_box_line("╭", "─", "╮"))
    print(_box_text(f"{C.BOLD}{C.CYAN}📜 Recent Query History (Top {len(queries)}){C.RESET}"))
    print(_box_line("├", "─", "┤"))
    if not queries:
        print(_box_text(f"{C.DIM}(No queries logged yet){C.RESET}"))
    else:
        for q in queries:
            q_text = q['question']
            if len(q_text) > 55:
                q_text = q_text[:52] + "..."
            conf = q.get('confidence', 'Unknown')
            conf_color = C.GREEN if conf == "High" else C.YELLOW if conf == "Medium" else C.RED if conf == "Low" else C.GRAY
            rt = q.get('route', 'auto')
            lat = format_latency(q.get('latency_ms', 0))
            created = q.get('created_at', '')
            print(_box_text(f"{C.GRAY}[{created}]{C.RESET} {C.WHITE}{q_text}{C.RESET}"))
            flags = []
            if q.get('used_web_fallback'):
                flags.append(f"{C.YELLOW}🌐 fallback{C.RESET}")
            if q.get('has_conflict'):
                flags.append(f"{C.RED}⚠️ conflict{C.RESET}")
            flag_str = (" (" + ", ".join(flags) + ")") if flags else ""
            print(_box_text(f"    → {conf_color}{conf}{C.RESET} | {C.CYAN}{rt}{C.RESET} | {C.PURPLE}{lat}{C.RESET}{flag_str}"))
    print(_box_line("╰", "─", "╯"))
    print("")


def print_stats(json_output: bool = False):
    """Displays query analytics and system performance stats."""
    s = get_query_stats(DB_PATH)
    if json_output:
        print(json.dumps(s, indent=2))
        return

    print("")
    print(_box_line("╭", "─", "╮"))
    print(_box_text(f"{C.BOLD}{C.CYAN}📊 Query Analytics & System Statistics{C.RESET}"))
    print(_box_line("├", "─", "┤"))
    print(_box_text(f"{C.GRAY}Total Queries:{C.RESET}       {C.WHITE}{s['total_queries']}{C.RESET}"))
    print(_box_text(f"{C.GRAY}Avg Latency:{C.RESET}         {C.PURPLE}{format_latency(s['avg_latency_ms'])}{C.RESET}"))
    print(_box_text(f"{C.GRAY}Web Fallbacks:{C.RESET}       {C.YELLOW}{s['web_fallback_count']}{C.RESET}"))
    print(_box_text(f"{C.GRAY}Conflicts Flagged:{C.RESET}   {C.RED}{s['conflict_count']}{C.RESET}"))
    
    if s['confidence_distribution']:
        print(_box_text(""))
        print(_box_text(f"{C.BOLD}By Confidence Level:{C.RESET}"))
        for conf, count in s['confidence_distribution'].items():
            color = C.GREEN if conf == "High" else C.YELLOW if conf == "Medium" else C.RED if conf == "Low" else C.GRAY
            print(_box_text(f"  {color}● {conf:<10}{C.RESET} {C.CYAN}{count:>4}{C.RESET} queries"))
            
    if s['route_distribution']:
        print(_box_text(""))
        print(_box_text(f"{C.BOLD}By Route / Source:{C.RESET}"))
        for rt, count in s['route_distribution'].items():
            print(_box_text(f"  ⚡ {C.WHITE}{rt:<14}{C.RESET} {C.CYAN}{count:>4}{C.RESET} queries"))

    print(_box_line("╰", "─", "╯"))
    print("")


def build_parser() -> argparse.ArgumentParser:
    """Constructs the robust argparse command-line parser."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=f"{C.gradient('⚡ PRAG — Local Fact-Grounded Research Engine')}\nEvidence-first answers powered by Qwen3:8B & SQLite-vec.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: ask
    ask_parser = subparsers.add_parser("ask", help="Query the research engine")
    ask_parser.add_argument("question", help="The question or prompt to research")
    ask_parser.add_argument("-v", "--verbose", action="store_true", help="Show diagnostic logs and evidence preview")
    ask_parser.add_argument("--source", choices=["local", "kali", "electronics", "software", "economics", "all"], default=None, help="Force specific source corpus / domain")
    ask_parser.add_argument("--model", type=str, default=None, help="Specify LLM model (e.g. qwen2.5:3b, qwen3:8b, llama3.2:latest)")
    ask_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    ask_parser.add_argument("--full-evidence", action="store_true", help="Display full untruncated chunk text in evidence trail")

    # Command: chat
    chat_parser = subparsers.add_parser("chat", help="Start an interactive multi-turn conversation with memory")
    chat_parser.add_argument("-v", "--verbose", action="store_true", help="Show diagnostic logs and evidence preview")
    chat_parser.add_argument("--source", choices=["local", "kali", "electronics", "software", "economics", "all"], default=None, help="Force specific source corpus / domain")
    chat_parser.add_argument("--model", type=str, default=None, help="Specify LLM model (e.g. qwen2.5:3b, qwen3:8b, llama3.2:latest)")
    chat_parser.add_argument("--full-evidence", action="store_true", help="Display full untruncated chunk text in evidence trail")

    # Command: history
    hist_parser = subparsers.add_parser("history", help="Show recent query history")
    hist_parser.add_argument("--limit", type=int, default=10, help="Number of queries to display (default: 10)")

    # Command: stats
    stats_parser = subparsers.add_parser("stats", help="Show aggregate query analytics")
    stats_parser.add_argument("--json", action="store_true", help="Output statistics in JSON format")

    # Command: status
    subparsers.add_parser("status", help="Show knowledge base statistics")

    # Command: sources
    subparsers.add_parser("sources", help="List all indexed files and tools")

    # Command: seed
    subparsers.add_parser("seed", help="Seed multi-domain knowledge base (Electronics, Software Eng, Economics)")

    # Command: ingest
    subparsers.add_parser("ingest", help="Ingest local knowledge base files")

    security_parser = subparsers.add_parser("import-security", help="Download official security documentation")
    security_parser.add_argument("--all-kali", action="store_true", help="Include all linked Kali package pages")
    security_parser.add_argument("--refresh", action="store_true", help="Refresh cached documentation")
    security_parser.add_argument("--ingest", action="store_true", help="Back up and index downloaded sources")

    # Command: sync-kali
    subparsers.add_parser("sync-kali", help="Sync Kali/Linux tool documentation")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Launch web interface")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")

    # Command: context
    ctx_parser = subparsers.add_parser("context", help="View or update machine & human readable AI context (CONTEXT.md)")
    ctx_parser.add_argument("--update", "-u", type=str, help="Update or record a user preference in CONTEXT.md")
    ctx_parser.add_argument("--raw", "-r", action="store_true", help="Print raw CONTEXT.md contents")

    return parser


def run_chat_loop(args):
    """Interactive multi-turn conversation loop in terminal with conversation memory."""
    source_type = None
    if args.source == "local":
        source_type = "local_file"
    elif args.source == "kali":
        source_type = "kali_docs"
    elif args.source == "electronics":
        source_type = "electronics"
    elif args.source == "software":
        source_type = "software_eng"
    elif args.source == "economics":
        source_type = "economics"
    elif args.source == "all":
        source_type = "all"

    verbose_mode = args.verbose

    def _log(msg: str):
        if verbose_mode:
            print(f"{C.DIM}{msg}{C.RESET}")

    print("")
    print(_box_line("╭", "─", "╮"))
    print(_box_text(f"{C.BOLD}{C.CYAN}💬 PRAG Interactive Multi-Turn Chat Mode{C.RESET}"))
    print(_box_text(f"{C.DIM}Conversational memory enabled across questions.{C.RESET}"))
    print(_box_text(f"{C.GRAY}Commands: {C.YELLOW}'exit'{C.GRAY}, {C.YELLOW}'quit'{C.GRAY} to quit | {C.YELLOW}'clear'{C.GRAY}, {C.YELLOW}'reset'{C.GRAY} to reset memory{C.RESET}"))
    print(_box_line("╰", "─", "╯"))
    print("")

    history: list[dict] = []

    while True:
        try:
            prompt_str = f"{C.CYAN}{C.BOLD}You > {C.RESET}"
            user_input = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C.YELLOW}Exiting chat.{C.RESET}")
            break

        if not user_input:
            continue

        cmd_lower = user_input.lower()
        if cmd_lower in ["exit", "quit", "q"]:
            print(f"{C.GREEN}Goodbye!{C.RESET}")
            break

        if cmd_lower in ["clear", "reset", "new"]:
            history.clear()
            print(f"{C.GREEN}✓ Conversation history reset. Starting new thread.{C.RESET}\n")
            continue

        print(f"{C.DIM}⚡ Researching evidence & generating answer...{C.RESET}")
        try:
            res = run_pipeline(
                question=user_input,
                base_dir=BASE_DIR,
                db_path=DB_PATH,
                source_type=source_type,
                model_name=args.model,
                top_k=3,
                verbose=verbose_mode,
                profile=PROFILE,
                logger_func=_log,
                history=history
            )

            print(format_terminal_answer(
                res["raw_answer"],
                res["raw_chunks"],
                route=res["route"],
                elapsed_ms=res["latency_ms"],
                is_ambiguous=res.get("is_ambiguous", False),
                full_evidence=args.full_evidence,
                verbose=verbose_mode,
                thinking_process=res.get("thinking_process", "")
            ))

            final_text = res["parsed"]["answer_text"] if res["parsed"]["answer_text"] else res["raw_answer"]
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": final_text})
            print("")

        except Exception as e:
            print(f"{C.RED}Error executing query: {e}{C.RESET}\n")


def main():
    parser = build_parser()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if args.command == "chat":
        run_chat_loop(args)

    elif args.command == "ask":
        source_type = None
        if args.source == "local":
            source_type = "local_file"
        elif args.source == "kali":
            source_type = "kali_docs"
        elif args.source == "electronics":
            source_type = "electronics"
        elif args.source == "software":
            source_type = "software_eng"
        elif args.source == "economics":
            source_type = "economics"
        elif args.source == "all":
            source_type = "all"

        verbose_mode = args.verbose

        def _log(msg: str):
            if verbose_mode:
                print(f"{C.DIM}{msg}{C.RESET}")

        res = run_pipeline(
            question=args.question,
            base_dir=BASE_DIR,
            db_path=DB_PATH,
            source_type=source_type,
            model_name=args.model,
            top_k=3,
            verbose=verbose_mode,
            profile=PROFILE,
            logger_func=_log
        )

        if args.json:
            output = {
                "question": res["question"],
                "route": res["route"],
                "is_ambiguous": res.get("is_ambiguous", False),
                "answer": res["parsed"]["answer_text"],
                "thinking_process": res.get("thinking_process", ""),
                "confidence": res["parsed"]["confidence"],
                "reason": res["parsed"]["reason"],
                "has_conflict": res.get("has_conflict", False),
                "sources": res["parsed"]["sources"],
                "chunks": [{
                    "file_name": c.get("file_name"),
                    "tier": c.get("tier"),
                    "rerank_score": c.get("rerank_score", 0.0),
                    "source_type": c.get("source_type"),
                    "chunk_text": c.get("chunk_text") if args.full_evidence else None
                } for c in res["chunks"]],
                "latency_ms": res["latency_ms"]
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_terminal_answer(
                res["raw_answer"],
                res["raw_chunks"],
                route=res["route"],
                elapsed_ms=res["latency_ms"],
                is_ambiguous=res.get("is_ambiguous", False),
                full_evidence=args.full_evidence,
                verbose=verbose_mode,
                thinking_process=res.get("thinking_process", "")
            ))

    elif args.command == "history":
        print_history(limit=args.limit)

    elif args.command == "stats":
        print_stats(json_output=args.json)

    elif args.command == "status":
        print_status()

    elif args.command == "sources":
        print_sources()

    elif args.command == "seed":
        from seed_knowledge import seed_knowledge_base
        print(f"\n  {C.CYAN}⚡{C.RESET} {C.BOLD}Seeding Multi-Domain Knowledge Base{C.RESET}\n")
        seed_knowledge_base()
        print(f"\n  {C.CYAN}📥{C.RESET} Ingesting seeded knowledge base into vector DB...\n")
        run_ingestion(BASE_DIR, DB_PATH, target_sub_dir="knowledge_base", source_type="local_file")
        print(f"\n  {C.GREEN}✓{C.RESET} {C.BOLD}Knowledge Base Seeding & Ingestion Complete{C.RESET}\n")

    elif args.command == "ingest":
        print(f"\n  {C.CYAN}⚡{C.RESET} {C.BOLD}Starting Local Knowledge Base Ingestion{C.RESET}\n")
        run_ingestion(BASE_DIR, DB_PATH, target_sub_dir="knowledge_base", source_type="local_file")
        print(f"\n  {C.GREEN}✓{C.RESET} {C.BOLD}Ingestion Complete{C.RESET}\n")

    elif args.command == "import-security":
        from import_security_docs import import_documents, index_documents
        manifest = import_documents(BASE_DIR, args.all_kali, args.refresh)
        failed = sum(item.get("status") == "failed" for item in manifest.values())
        print(f"Downloaded: {sum(item.get('status') == 'downloaded' for item in manifest.values())}; failed: {failed}")
        if args.ingest:
            result = index_documents(BASE_DIR, manifest)
            if result["failed"]:
                raise SystemExit(1)

    elif args.command == "sync-kali":
        print(f"\n  {C.CYAN}⚡{C.RESET} {C.BOLD}Starting Kali & Linux Documentation Sync{C.RESET}\n")
        sync_kali_docs(BASE_DIR)
        print(f"\n  {C.CYAN}📥{C.RESET} Ingesting Kali docs into vector DB...\n")
        run_ingestion(BASE_DIR, DB_PATH, target_sub_dir="knowledge_base_kali/raw", source_type="kali_docs")
        print(f"\n  {C.GREEN}✓{C.RESET} {C.BOLD}Kali Docs Sync Complete{C.RESET}\n")

    elif args.command == "serve":
        from web_ui import run_web_server
        run_web_server(args.port)

    elif args.command == "context":
        from context_manager import read_context_raw, detect_and_apply_preference_update
        if args.update:
            updated, msg = detect_and_apply_preference_update(args.update)
            if updated:
                print(f"\n  {C.GREEN}✓{C.RESET} {C.BOLD}{msg}{C.RESET}\n")
            else:
                print(f"\n  {C.YELLOW}ℹ{C.RESET} {msg}\n")
        else:
            raw = read_context_raw()
            if args.raw:
                print(raw)
            else:
                print(f"\n  {C.CYAN}🧠{C.RESET} {C.BOLD}PRAG Persistent AI Context & User Preferences (CONTEXT.md){C.RESET}")
                print(f"  {C.DIM}Models read this context on every query to tailor responses to your preferences.{C.RESET}\n")
                print(raw)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
