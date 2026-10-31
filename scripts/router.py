#!/usr/bin/env python3
"""
Rule-based query router for Local Fact-Grounded RAG System.
Classifies user queries into source_types:
  kali_docs, local_file, electronics, software_eng, economics,
  reasoning_general, math_code, all.
Identifies ambiguous broad queries, and evaluates retrieval confidence
with route-aware thresholds for live web fallback triggering.
"""

import os
import re
import sys
import sqlite3

# Import CURATED_TOOLS from sync_kali_docs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from sync_kali_docs import CURATED_TOOLS

# Route-aware confidence thresholds
# Kali/man-page excerpts are dense command options with lower baseline cosine similarity (~0.45-0.55)
KALI_CONFIDENCE_THRESHOLD = 0.45
DEFAULT_CONFIDENCE_THRESHOLD = 0.60
DISTANCE_THRESHOLD = 0.45  # Cosine distance threshold (above 0.45 indicates poor similarity)

# Fuzzy keyword groups that suggest Kali/Linux domain queries
LINUX_SECURITY_KEYWORDS = [
    # Network & Scanning
    "port scan", "network scan", "service detection", "os detection",
    "host discovery", "packet capture", "packet sniff", "network sniff",
    "traffic analysis", "protocol analysis", "network enumeration",
    # Attack techniques & Binary Exploitation
    "brute force", "password crack", "hash crack", "dictionary attack",
    "sql injection", "sqli", "xss", "cross site", "command injection",
    "privilege escalation", "privesc", "reverse shell", "bind shell",
    "buffer overflow", "stack overflow", "heap overflow", "use after free", "use-after-free", "uaf",
    "double free", "format string", "type confusion", "integer overflow",
    "rop", "return oriented programming", "ret2libc", "gadget chain", "stack pivot",
    "shellcode", "payload", "exploit", "aslr", "stack canary", "relro", "cfi",
    # Code Execution Sources & Vectors
    "remote code execution", "rce", "arbitrary code execution", "code execution",
    "living off the land", "lolbin", "lolbins", "gtfobin", "gtfobins",
    "process hollowing", "process injection", "dll injection", "dll hijacking",
    "dll side-loading", "ld_preload", "memfd_create", "reflective dll", "fileless",
    "insecure deserialization", "pickle rce", "ysoserial", "container escape", "docker escape",
    # Web & Server-side security
    "directory brute", "dir bust", "web scan", "vulnerability scan",
    "subdomain enum", "web fuzzing", "ssrf", "server side request forgery",
    "xxe", "xml external entity", "ssti", "template injection", "request smuggling",
    "idor", "csrf", "jwt attack", "session fixation", "clickjacking",
    # Supply chain & Cryptographic attacks
    "dependency confusion", "typosquatting", "supply chain attack", "pipeline poisoning",
    "padding oracle", "replay attack", "redos",
    # Wireless
    "wifi", "wireless", "wpa", "wep", "deauth", "handshake capture",
    "monitor mode", "packet injection",
    # System admin
    "firewall rule", "iptable", "packet filter", "port forward",
    "systemd", "service management", "cron job", "process monitor",
    # General Linux
    "man page", "command line", "terminal command", "bash script",
    "shell script", "linux command", "kali", "penetration test",
    "pentest", "ethical hack", "security audit", "red team",
    "ctf", "capture the flag", "forensic"
]

# Tool aliases that should also trigger kali_docs routing
TOOL_ALIASES = {
    "netcat": "nc",
    "network mapper": "nmap",
    "wire shark": "wireshark",
    "john the ripper": "john",
    "metasploit": "msfconsole",
    "search sploit": "searchsploit",
    "burp suite": "burpsuite",
    "burp": "burpsuite",
    "owasp zap": "zap",
    "zed attack proxy": "zap",
    "r2": "radare2",
}

# ═══ Domain-Specific Keyword Sets ═══

# Electronics, Embedded Systems & Electrical Engineering
ELECTRONICS_KEYWORDS = [
    # Passive components
    "resistor", "capacitor", "inductor", "diode", "transistor", "relay",
    "potentiometer", "thermistor", "varistor", "ferrite", "crystal oscillator",
    # Active components & ICs
    "mosfet", "bjt", "jfet", "igbt", "op-amp", "op amp", "operational amplifier",
    "555 timer", "voltage regulator", "lm7805", "lm317", "comparator",
    "adc", "dac", "pll", "vco", "ldo", "shift register", "flip flop",
    # Microcontrollers & boards
    "arduino", "stm32", "esp32", "esp8266", "raspberry pi pico", "attiny",
    "atmega", "pic microcontroller", "msp430", "nrf52", "teensy",
    "microcontroller", "mcu", "soc", "fpga", "cpld", "asic",
    # HDL & firmware
    "vhdl", "verilog", "systemverilog", "hdl", "rtl", "synthesis",
    "bitstream", "testbench", "timing constraint", "clock domain",
    # Protocols & interfaces
    "i2c", "spi", "uart", "usart", "rs232", "rs485", "can bus", "lin bus",
    "usb", "jtag", "swd", "one wire", "1-wire", "modbus", "ethernet phy",
    "gpio", "pwm", "interrupt", "dma", "watchdog timer",
    # Circuit concepts
    "voltage divider", "current limiting", "pull-up resistor", "pull-down",
    "decoupling capacitor", "bypass capacitor", "impedance", "reactance",
    "kirchhoff", "thevenin", "norton", "ohm's law", "ohms law",
    "rc circuit", "rl circuit", "rlc circuit", "time constant", "cutoff frequency",
    "low pass filter", "high pass filter", "band pass filter", "notch filter",
    "amplifier gain", "feedback loop", "negative feedback", "oscillator",
    # Power electronics
    "buck converter", "boost converter", "flyback converter", "half bridge",
    "full bridge", "h-bridge", "inverter", "rectifier", "power supply",
    "switching regulator", "linear regulator", "power dissipation", "thermal",
    "heat sink", "junction temperature",
    # PCB & manufacturing
    "pcb", "printed circuit board", "smd", "through hole", "solder",
    "soldering", "reflow", "gerber", "drill file", "trace width",
    "copper pour", "ground plane", "via", "layer stack",
    # Signal & measurement
    "oscilloscope", "multimeter", "logic analyzer", "spectrum analyzer",
    "signal integrity", "emi", "emc", "rfi", "snr", "noise floor",
    "bandwidth", "slew rate", "rise time", "fall time",
    "ground loop", "common mode", "differential mode",
    # Sensors & actuators
    "accelerometer", "gyroscope", "magnetometer", "temperature sensor",
    "pressure sensor", "ultrasonic sensor", "lidar", "photodiode",
    "phototransistor", "hall effect", "strain gauge", "load cell",
    "stepper motor", "servo motor", "brushless motor", "dc motor", "solenoid",
    # EE general
    "datasheet", "schematic", "circuit diagram", "breadboard", "prototype",
    "embedded system", "firmware", "bare metal", "rtos", "freertos",
    "electrical engineering", "electronics", "analog", "digital",
    "cmos", "ttl", "3.3v", "5v logic", "level shifter",
]

# Software Engineering, Architecture & DevOps
SOFTWARE_ENGINEERING_KEYWORDS = [
    # Architecture & patterns
    "design pattern", "singleton", "factory pattern", "observer pattern",
    "strategy pattern", "decorator pattern", "adapter pattern", "facade pattern",
    "microservice", "monolith", "event driven", "event sourcing", "cqrs",
    "clean architecture", "hexagonal architecture", "domain driven",
    "solid principles", "dependency injection", "inversion of control",
    "separation of concerns", "coupling", "cohesion",
    # APIs & protocols
    "api design", "rest api", "restful", "graphql", "grpc", "protobuf",
    "websocket", "server sent events", "webhook", "openapi", "swagger",
    "rate limiting", "api gateway", "middleware",
    # Databases & storage
    "database schema", "orm", "sql query", "database index",
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "database migration", "database sharding", "replication",
    "nosql", "key value store", "time series database",
    # DevOps & infrastructure
    "docker", "dockerfile", "container", "kubernetes", "k8s", "helm",
    "terraform", "ansible", "ci cd", "ci/cd", "github actions",
    "jenkins", "gitlab ci", "deployment", "blue green deploy",
    "canary deploy", "rolling update", "infrastructure as code",
    "load balancer", "reverse proxy", "nginx", "caddy",
    # Testing & quality
    "unit test", "integration test", "end to end test", "e2e test",
    "test driven", "tdd", "bdd", "mocking", "stubbing",
    "code coverage", "static analysis", "linting", "code review",
    # Concurrency & performance
    "concurrency", "parallelism", "multithreading", "async await",
    "deadlock", "race condition", "mutex", "semaphore",
    "memory leak", "garbage collection", "profiling", "benchmarking",
    "caching strategy", "cache invalidation", "cdn",
    # Security & auth
    "authentication", "authorization", "oauth", "jwt", "saml",
    "cors", "csrf", "xss prevention", "sql injection prevention",
    "encryption", "hashing", "bcrypt", "ssl", "tls",
    # Version control & workflow
    "git workflow", "git branch", "merge conflict", "rebase",
    "conventional commit", "semantic versioning", "monorepo",
    # Message queues & streaming
    "message queue", "rabbitmq", "kafka", "celery", "pub sub",
    "event bus", "task queue", "worker",
    # General software eng
    "software architecture", "system design", "technical debt",
    "refactoring", "code smell", "anti pattern",
    "scalability", "high availability", "fault tolerance",
]

# Economics, Finance & Market Analysis
ECONOMICS_KEYWORDS = [
    # Macro economics
    "gdp", "gross domestic product", "inflation", "deflation", "stagflation",
    "monetary policy", "fiscal policy", "quantitative easing", "tapering",
    "central bank", "federal reserve", "interest rate", "prime rate",
    "money supply", "m1", "m2", "velocity of money",
    "recession", "depression", "business cycle", "economic growth",
    "unemployment", "phillips curve", "aggregate demand", "aggregate supply",
    "trade deficit", "trade surplus", "balance of payments", "current account",
    "exchange rate", "forex", "currency", "purchasing power parity",
    # Micro economics
    "supply and demand", "supply demand", "elasticity", "inelastic",
    "market equilibrium", "price ceiling", "price floor",
    "opportunity cost", "marginal cost", "marginal utility",
    "diminishing returns", "economies of scale", "diseconomies of scale",
    "comparative advantage", "absolute advantage",
    "consumer surplus", "producer surplus", "deadweight loss",
    "market failure", "externality", "public goods", "free rider",
    "monopoly", "oligopoly", "perfect competition", "monopolistic competition",
    "price discrimination", "market structure", "barrier to entry",
    # Finance & investment
    "npv", "net present value", "irr", "internal rate of return",
    "roi", "return on investment", "wacc", "cost of capital",
    "compound interest", "simple interest", "amortization", "depreciation",
    "present value", "future value", "discount rate", "cash flow",
    "stock market", "equity", "bond", "yield curve", "coupon rate",
    "dividend", "p/e ratio", "market cap", "portfolio", "diversification",
    "risk premium", "beta", "alpha", "sharpe ratio", "volatility",
    "hedge", "derivative", "options", "futures", "call option", "put option",
    # Economic theories & schools
    "keynesian", "monetarist", "austrian school", "supply side",
    "laissez faire", "mixed economy", "planned economy",
    # Game theory & behavioral
    "game theory", "nash equilibrium", "pareto efficiency", "pareto optimal",
    "prisoner dilemma", "dominant strategy", "zero sum",
    "behavioral economics", "rational choice", "bounded rationality",
    # Modern finance
    "cryptocurrency", "bitcoin", "blockchain", "defi",
    "fintech", "algorithmic trading", "high frequency trading",
]

# Reasoning, logic, math, and code indicator keywords
REASONING_LOGIC_KEYWORDS = [
    "logic", "logical", "puzzle", "riddle", "premise", "premises", "syllogism",
    "deduce", "deduction", "infer", "inference", "step by step", "prove", "proof",
    "fallacy", "paradox", "if all", "suppose", "assume", "truth table", "boolean",
    "counterexample", "validity", "soundness", "transitive", "contrapositive"
]

MATH_CODE_KEYWORDS = [
    "calculate", "computation", "equation", "derivative", "integral", "matrix",
    "algebra", "geometry", "trigonometry", "probability", "statistics", "polynomial",
    "algorithm", "function", "python", "javascript", "typescript", "c++", "rust",
    "golang", "java", "sql", "html", "css", "class", "async", "recursion",
    "binary tree", "graph", "dynamic programming", "time complexity", "big o",
    "refactor", "debug", "write a program", "write code", "code snippet"
]


def get_known_filenames(db_path: str, logger_func=None) -> list[str]:
    """Retrieve distinct local file paths and stems/basenames from DB."""
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT file_path FROM chunks WHERE source_type = 'local_file';")
        rows = cursor.fetchall()
        conn.close()
        
        filenames = []
        for r in rows:
            fp = r[0]
            basename = os.path.basename(fp)
            stem = os.path.splitext(basename)[0]
            filenames.append(basename)
            if stem and stem != basename:
                filenames.append(stem)
            space_stem = stem.replace('_', ' ').replace('-', ' ')
            if space_stem != stem:
                filenames.append(space_stem)
            space_base = basename.replace('_', ' ').replace('-', ' ')
            if space_base != basename:
                filenames.append(space_base)
        return list(set(filenames))
    except Exception as e:
        msg = f"[ROUTER WARN] Failed to retrieve known filenames from database: {e}"
        if logger_func:
            logger_func(msg)
        elif "-v" in sys.argv or "--verbose" in sys.argv:
            print(f"\033[2m{msg}\033[0m")
        return []


def _check_fuzzy_keywords(query_lower: str) -> bool:
    """Check if query matches any Linux/security domain keyword."""
    for keyword in LINUX_SECURITY_KEYWORDS:
        if keyword in query_lower:
            return True
    return False


def _check_tool_aliases(query_lower: str) -> bool:
    """Check if query matches any tool alias."""
    for alias in TOOL_ALIASES:
        if alias in query_lower:
            return True
    return False


KEYBOARD_MASH_PATTERNS = {
    "qwerty", "qwert", "asdfgh", "asdfg", "zxcvbn", "zxcvb",
    "lkjhg", "poiuy", "mnbvc", "jjnkl", "hjkl", "ghjkl", "dfgjh"
}

# Short valid CLI tools / shell commands / symbols / math variables (1-3 chars)
SHORT_VALID_TOKENS = {
    "ls", "cd", "cp", "mv", "rm", "ip", "ss", "ps", "dd", "df", "du", "sh",
    "nc", "id", "vi", "cat", "awk", "sed", "gdb", "git", "env", "top", "su",
    "tar", "zip", "dig", "man", "who", "pwd", "cut", "tee", "xxd", "ufw",
    "pip", "npm", "gcc", "g++", "make", "ld", "ar", "od", "nm", "tr", "wc",
    "sin", "cos", "tan", "log", "exp", "lim", "gcd", "lcm", "sum", "avg", "mod",
    "if", "for", "def", "let", "var", "val", "mut", "fn", "int", "str", "map", "set",
    "try", "and", "not", "xor", "nor", "nand", "eq", "ne", "lt", "gt", "le", "ge"
}

# Broad vocabulary of common words across general domains
COMMON_VOCABULARY = {
    "what", "where", "when", "why", "how", "who", "which", "whose", "whom",
    "is", "are", "was", "were", "be", "been", "being", "can", "could", "shall", "should",
    "will", "would", "may", "might", "must", "have", "has", "had", "having",
    "do", "does", "did", "done", "doing", "explain", "tell", "show", "list", "describe",
    "find", "get", "set", "run", "use", "using", "help", "check", "scan", "evaluate",
    "test", "file", "system", "code", "command", "tool", "script", "text", "solve",
    "note", "page", "man", "doc", "linux", "kali", "unix", "security", "calculate",
    "password", "user", "admin", "network", "port", "hash", "key", "flag", "compute",
    "server", "client", "service", "process", "rule", "traffic", "packet", "derive",
    "attack", "audit", "shell", "remote", "local", "bound", "open", "reason",
    "close", "start", "stop", "status", "info", "create", "delete", "remove", "compare",
    "view", "search", "read", "write", "dump", "crack", "forge", "spoof", "analyze",
    "logic", "math", "physics", "science", "biology", "history", "philosophy", "problem",
    "step", "steps", "question", "answer", "proof", "prove", "example", "difference",
    "meaning", "definition", "concept", "algorithm", "theory", "principle", "solution"
}


def is_nonsensical_query(question: str, known_tools: list[str] = None, known_filenames: list[str] = None) -> bool:
    """
    Fast check for truly nonsensical keyboard mash or uninterpretable input.
    Permits math equations, code fragments, reasoning questions, and multisyllabic technical terms.
    """
    q_clean = question.strip()
    if not q_clean or len(q_clean) < 2:
        return True

    # If query contains math operators, programming syntax, or logic symbols, it is NOT nonsense
    if any(c in q_clean for c in "+-*/=<>^%&|~()[]{}!?:;\\`$#@_"):
        # If it has at least some alphanumeric characters or valid formula syntax
        if re.search(r'[a-zA-Z0-9]', q_clean):
            return False

    q_lower = q_clean.lower()

    # If any known tool matches, valid
    if known_tools is None:
        known_tools = CURATED_TOOLS
    for tool in known_tools:
        pattern = r'\b' + re.escape(tool.lower()) + r'\b'
        if re.search(pattern, q_lower):
            return False

    # If tool aliases match, valid
    if _check_tool_aliases(q_lower):
        return False

    # If Linux/security keywords match, valid
    if _check_fuzzy_keywords(q_lower):
        return False

    # If reasoning or math keywords match, valid
    if any(kw in q_lower for kw in REASONING_LOGIC_KEYWORDS) or any(kw in q_lower for kw in MATH_CODE_KEYWORDS):
        return False

    # If known filename matches, valid
    if known_filenames is None:
        db_path = os.path.join(BASE_DIR, "data", "vectors.db")
        known_filenames = get_known_filenames(db_path)
    for fn in known_filenames:
        fn_lower = fn.lower()
        if fn_lower and len(fn_lower) >= 3 and fn_lower in q_lower:
            return False

    # Extract alphanumeric words
    words = re.findall(r'[a-z0-9]+', q_lower)
    if not words:
        return True

    # If query contains multiple words and ANY word is a common vocabulary word, valid
    for w in words:
        if w in COMMON_VOCABULARY or w in SHORT_VALID_TOKENS:
            return False

    # Check for obvious keyboard mash in single-word queries
    vowels = set("aeiouy")
    if len(words) == 1:
        w = words[0]
        # Repetitive single characters: e.g. "aaaaaa", "zzzz"
        if len(set(w)) == 1 and len(w) >= 3:
            return True
        # Specific known keyboard mash sequences
        if any(mash in w for mash in KEYBOARD_MASH_PATTERNS):
            return True
        # Completely devoid of vowels and length >= 5 (and not a recognized short token)
        w_vowels = [ch for ch in w if ch in vowels]
        if len(w) >= 5 and len(w_vowels) == 0 and w not in SHORT_VALID_TOKENS:
            return True

    # If all words in a multi-word query are keyboard mash patterns
    all_mash = True
    for w in words:
        if w not in KEYBOARD_MASH_PATTERNS and len(set(w)) > 1:
            all_mash = False
            break
    if all_mash:
        return True

    return False


def classify_query_detailed(question: str, db_path: str, known_tools: list[str] = None, known_filenames: list[str] = None, logger_func=None) -> dict:
    """
    Detailed query classification returning route and scope confidence metadata.
    Distinguishes targeted corpus routes (kali_docs, local_file), reasoning/logic/math,
    and ambiguous cross-domain queries.
    """
    if known_tools is None:
        known_tools = CURATED_TOOLS
    if known_filenames is None:
        known_filenames = get_known_filenames(db_path, logger_func=logger_func)

    # 0. Nonsense check
    if is_nonsensical_query(question, known_tools, known_filenames):
        return {
            "route": "nonsense",
            "is_ambiguous": False,
            "reason": "Query appears to be nonsensical or unrecognized gibberish."
        }

    q = question.lower()

    tool_matched = False
    matched_tool_name = None
    for tool in known_tools:
        pattern = r'\b' + re.escape(tool.lower()) + r'\b'
        if re.search(pattern, q):
            tool_matched = True
            matched_tool_name = tool
            break

    if not tool_matched:
        for alias in TOOL_ALIASES:
            if alias in q:
                tool_matched = True
                matched_tool_name = TOOL_ALIASES[alias]
                break

    fuzzy_security_matched = _check_fuzzy_keywords(q)

    file_matched = False
    matched_file_name = None
    for fn in known_filenames:
        fn_lower = fn.lower()
        if fn_lower and len(fn_lower) >= 3:
            pattern = r'\b' + re.escape(fn_lower) + r'\b'
            if re.search(pattern, q):
                file_matched = True
                matched_file_name = fn
                break

    # Domain detection
    is_electronics = any(kw in q for kw in ELECTRONICS_KEYWORDS)
    is_software_eng = any(kw in q for kw in SOFTWARE_ENGINEERING_KEYWORDS)
    is_economics = any(kw in q for kw in ECONOMICS_KEYWORDS)
    is_reasoning = any(kw in q for kw in REASONING_LOGIC_KEYWORDS)
    is_math_code = any(kw in q for kw in MATH_CODE_KEYWORDS) or any(c in question for c in "+-*/=<>^%\\`{}")

    # Count how many distinct domains matched (for cross-domain detection)
    domain_hits = sum([
        bool(tool_matched or fuzzy_security_matched),
        is_electronics, is_software_eng, is_economics
    ])

    # Routing logic — priority order: specific corpus matches > domain > reasoning > math > general
    if tool_matched and file_matched:
        return {
            "route": "all",
            "is_ambiguous": False,
            "reason": f"Cross-corpus query matching tool '{matched_tool_name}' and file '{matched_file_name}'."
        }
    elif tool_matched:
        return {
            "route": "kali_docs",
            "is_ambiguous": False,
            "reason": f"Matched tool/command '{matched_tool_name}'."
        }
    elif fuzzy_security_matched and not is_electronics:
        return {
            "route": "all",
            "is_ambiguous": False,
            "reason": "Matched security/attack domain keywords (searching local security knowledge base and Kali docs)."
        }
    elif fuzzy_security_matched and file_matched:
        return {
            "route": "all",
            "is_ambiguous": False,
            "reason": f"Matched security keywords and local file '{matched_file_name}'."
        }
    elif file_matched:
        return {
            "route": "local_file",
            "is_ambiguous": False,
            "reason": f"Matched local file reference '{matched_file_name}'."
        }
    # Domain-specific routing (electronics gets priority as user's primary field)
    elif is_electronics and domain_hits == 1:
        return {
            "route": "electronics",
            "is_ambiguous": False,
            "reason": "Electronics / embedded systems / electrical engineering query."
        }
    elif is_software_eng and domain_hits == 1:
        return {
            "route": "software_eng",
            "is_ambiguous": False,
            "reason": "Software engineering / architecture / DevOps query."
        }
    elif is_economics and domain_hits == 1:
        return {
            "route": "economics",
            "is_ambiguous": False,
            "reason": "Economics / finance / market analysis query."
        }
    elif domain_hits > 1:
        # Cross-domain query — search all corpora
        matched_domains = []
        if tool_matched or fuzzy_security_matched:
            matched_domains.append("security")
        if is_electronics:
            matched_domains.append("electronics")
        if is_software_eng:
            matched_domains.append("software")
        if is_economics:
            matched_domains.append("economics")
        return {
            "route": "all",
            "is_ambiguous": False,
            "reason": f"Cross-domain query spanning: {', '.join(matched_domains)}."
        }
    elif is_reasoning:
        return {
            "route": "reasoning_general",
            "is_ambiguous": False,
            "reason": "Logical reasoning / deduction / analytical thinking query."
        }
    elif is_math_code:
        return {
            "route": "math_code",
            "is_ambiguous": False,
            "reason": "Mathematical calculation, algorithmic, or programming inquiry."
        }
    else:
        # Ambiguous / General open domain query
        return {
            "route": "all",
            "is_ambiguous": True,
            "reason": "Open-domain / general research query — searching available corpora & knowledge."
        }


def classify_query(question: str, db_path: str, known_tools: list[str] = None, known_filenames: list[str] = None) -> str:
    """
    Standard classifier returning route string:
      - 'nonsense'
      - 'kali_docs'
      - 'local_file'
      - 'electronics'
      - 'software_eng'
      - 'economics'
      - 'reasoning_general'
      - 'math_code'
      - 'all'
    """
    detailed = classify_query_detailed(question, db_path, known_tools, known_filenames)
    return detailed["route"]


def evaluate_retrieval_confidence(chunks: list[dict], route: str = "all", threshold: float = None, question: str = None, logger_func=None) -> dict:
    """
    Evaluates top chunk's rerank score or distance using route-aware thresholds
    and checks multi-entity query coverage to trigger web fallback when needed.
    """
    if threshold is None:
        threshold = KALI_CONFIDENCE_THRESHOLD if route == "kali_docs" else DEFAULT_CONFIDENCE_THRESHOLD

    def _log(msg: str):
        if logger_func:
            logger_func(msg)
        elif "-v" in sys.argv or "--verbose" in sys.argv:
            print(f"\033[2m{msg}\033[0m")

    if not chunks:
        _log(f"[ROUTER] Low confidence — no relevant chunks found in database. Triggering web fallback.")
        return {"low_confidence": True, "route_to_web_fallback": True, "top_score": None, "threshold": threshold}

    # Entity coverage check: if query mentions multiple tools, verify chunks cover them
    if question:
        q_low = question.lower()
        matched_entities = []
        for tool in CURATED_TOOLS:
            pattern = r'\b' + re.escape(tool.lower()) + r'\b'
            if re.search(pattern, q_low):
                matched_entities.append(tool.lower())
        for alias, target in TOOL_ALIASES.items():
            if alias in q_low and target.lower() not in matched_entities:
                matched_entities.append(target.lower())

        if len(matched_entities) > 1:
            # Check if all matched tools have representation in retrieved chunks
            chunk_text_blob = " ".join([
                (c.get('file_name', '') + " " + c.get('chunk_text', '')).lower()
                for c in chunks
            ])
            missing_entities = [t for t in matched_entities if t not in chunk_text_blob]
            if missing_entities:
                _log(f"[ROUTER] Multi-entity query detected with missing local coverage for: {missing_entities} — triggering web fallback.")
                return {
                    "low_confidence": True,
                    "route_to_web_fallback": True,
                    "top_score": chunks[0].get('rerank_score'),
                    "threshold": threshold,
                    "missing_entities": missing_entities
                }

    # A literal definition for the requested tool/option is usable local
    # evidence even when dense help text has a low semantic reranker score.
    if any(chunk.get("exact_option_match") for chunk in chunks):
        _log("[ROUTER] Exact local option definition found; retaining local evidence.")
        return {
            "low_confidence": False,
            "route_to_web_fallback": False,
            "top_score": chunks[0].get("rerank_score"),
            "threshold": threshold,
            "exact_option_match": True
        }

    top_chunk = chunks[0]
    top_score = top_chunk.get('rerank_score')

    if top_score is not None:
        if top_score < threshold:
            _log(f"[ROUTER] Low confidence (top score {top_score:.4f} < {threshold:.2f} for route='{route}') — triggering web fallback.")
            return {"low_confidence": True, "route_to_web_fallback": True, "top_score": top_score, "threshold": threshold}
        else:
            _log(f"[ROUTER] High confidence (top score {top_score:.4f} >= {threshold:.2f} for route='{route}').")
            return {"low_confidence": False, "route_to_web_fallback": False, "top_score": top_score, "threshold": threshold}
    else:
        dist = top_chunk.get('distance', 999.0)
        if dist > DISTANCE_THRESHOLD:
            _log(f"[ROUTER] Low confidence (vector distance {dist:.4f} > {DISTANCE_THRESHOLD}) — triggering web fallback.")
            return {"low_confidence": True, "route_to_web_fallback": True, "top_score": dist, "threshold": threshold}
        else:
            _log(f"[ROUTER] High confidence (vector distance {dist:.4f} <= {DISTANCE_THRESHOLD}).")
            return {"low_confidence": False, "route_to_web_fallback": False, "top_score": dist, "threshold": threshold}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python router.py \"<question>\"")
        sys.exit(1)

    question = sys.argv[1]
    db_path = os.path.join(BASE_DIR, "data", "vectors.db")
    info = classify_query_detailed(question, db_path)
    print(f"Question: '{question}'")
    print(f"Route: {info['route']} (Ambiguous: {info['is_ambiguous']})")
    print(f"Reason: {info['reason']}")
