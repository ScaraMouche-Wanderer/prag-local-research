#!/usr/bin/env python3
"""
PRAG — Linux, Cybersecurity & Software Research Engine.
Fact-grounded research & technical intelligence system with indexed Kali Linux tools, sysadmin manuals, and offline AI reasoning.
Features:
  - 🛡️ Interactive Linux & Cybersecurity Tool Arsenal Hub (72+ indexed tools with instant cheat sheets and copyable command templates)
  - 🐧 Deep Linux Sysadmin, Kernel, Networking, and DevSecOps research
  - 🌐 Web & API Security, Penetration Testing & Recon tactics
  - 🧠 Advanced reasoning & high-precision math solver as secondary capabilities
  - ⚡ Real-time SSE streaming with instant stop/cancel state management
  - 📄 Multi-format export (Markdown, JSON, Print/PDF)
  - 🔊 Text-to-Speech audio narration with live equalizer visualizer
  - 🎨 4 Curated Themes (Light Clean, Cyber Dark, Mint Fresh, Warm Paper)
"""

import os
import sys
import json
import time
import sqlite3
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from router import classify_query_detailed, evaluate_retrieval_confidence
from retrieve import retrieve_top_k
from web_fallback import fetch_web_fallback
from answer import generate_answer, generate_answer_streaming, detect_potential_conflict, get_best_available_model
from tier_config import get_tier_label
from response_parser import parse_answer_metadata
from query_log import log_query, save_feedback, get_recent_queries, get_query_stats, init_query_log
from pipeline import run_pipeline, sort_key, contextualize_query_from_history
from embed_store import get_embedder, get_reranker
from math_solver import evaluate_math_query
from context_manager import read_context_raw, write_context_raw, detect_and_apply_preference_update

DB_PATH = os.path.join(BASE_DIR, "data", "vectors.db")

# Initialize query log table on import
try:
    init_query_log(DB_PATH)
except Exception:
    pass

# Curated Linux & Security Tool Arsenal Metadata (All 72+ Indexed Tools)
SECURITY_TOOLS_CATALOG = [
    # ─── Network & Scanning (18) ───
    {
        "name": "nmap", "category": "network", "label": "Network Scanner", "icon": "🛡️",
        "synopsis": "Network exploration tool and security / port scanner.",
        "cmd": "nmap -sS -sV -sC -p- -T4 <target>",
        "query": "How does Nmap perform stealth SYN scanning with service version detection (-sS -sV)?"
    },
    {
        "name": "masscan", "category": "network", "label": "Async Port Scanner", "icon": "⚡",
        "synopsis": "Ultra-fast TCP port scanner capable of scanning the entire Internet in under 6 minutes.",
        "cmd": "masscan -p1-65535 192.168.1.0/24 --rate=10000",
        "query": "How does masscan achieve high-speed asynchronous port scanning?"
    },
    {
        "name": "wireshark", "category": "network", "label": "Packet Analyzer", "icon": "🦈",
        "synopsis": "Interactive network protocol analyzer and packet capture visualizer.",
        "cmd": "wireshark -i eth0 -k -f 'tcp port 80 or tcp port 443'",
        "query": "How to filter HTTP and TLS handshakes in Wireshark?"
    },
    {
        "name": "tshark", "category": "network", "label": "CLI Packet Analyzer", "icon": "🦈",
        "synopsis": "Terminal-based network packet analyzer and pcap dissector.",
        "cmd": "tshark -r capture.pcap -Y 'http.request or dns' -T fields -e ip.src -e http.host",
        "query": "How to extract DNS queries and HTTP hosts from pcap files using tshark?"
    },
    {
        "name": "tcpdump", "category": "network", "label": "Packet Sniffer", "icon": "📡",
        "synopsis": "Command-line packet analyzer and network traffic capture utility.",
        "cmd": "tcpdump -i any -nn -vvv -s0 -w capture.pcap 'port 80 or port 443'",
        "query": "How to capture full payload packets with tcpdump and write to pcap?"
    },
    {
        "name": "netcat", "category": "network", "label": "TCP/IP Swiss Army Knife", "icon": "🔌",
        "synopsis": "Reads and writes data across network connections using TCP or UDP.",
        "cmd": "nc -lvnp 4444",
        "query": "How to use netcat for port scanning, banner grabbing, and reverse shells?"
    },
    {
        "name": "nc", "category": "network", "label": "Netcat Alias", "icon": "🔌",
        "synopsis": "Standard netcat utility for arbitrary TCP/UDP connections and listens.",
        "cmd": "nc -zv 192.168.1.1 20-100",
        "query": "How to perform quick port sweeps using nc with zero-I/O mode (-z)?"
    },
    {
        "name": "ncat", "category": "network", "label": "Nmap Netcat", "icon": "🛡️",
        "synopsis": "Modern reimplementation of Netcat with SSL/TLS support and IPv6.",
        "cmd": "ncat --ssl -lvnp 4443",
        "query": "How to establish encrypted reverse shells and SSL listeners using ncat?"
    },
    {
        "name": "socat", "category": "network", "label": "Multipurpose Relay", "icon": "🔀",
        "synopsis": "Bidirectional relay for two independent byte streams with PTY and SSL support.",
        "cmd": "socat TCP-LISTEN:4444,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid,sigint,sane",
        "query": "How to establish fully interactive TTY reverse shells using socat?"
    },
    {
        "name": "dig", "category": "network", "label": "DNS Lookup Utility", "icon": "🔎",
        "synopsis": "Flexible DNS lookup tool for interrogating DNS name servers.",
        "cmd": "dig @8.8.8.8 target.com ANY +noall +answer",
        "query": "How to perform DNS zone transfers (AXFR) and query specific record types with dig?"
    },
    {
        "name": "traceroute", "category": "network", "label": "Packet Route Tracer", "icon": "🗺️",
        "synopsis": "Prints the route and transit delays of packets across IP networks.",
        "cmd": "traceroute -T -p 443 target.com",
        "query": "How does TCP SYN traceroute (-T -p 443) bypass ICMP firewall filters?"
    },
    {
        "name": "ping", "category": "network", "label": "ICMP Echo Utility", "icon": "📶",
        "synopsis": "Sends ICMP ECHO_REQUEST packets to network hosts to test reachability.",
        "cmd": "ping -c 4 -s 1024 192.168.1.1",
        "query": "How to use ping for MTU discovery and packet loss diagnostics?"
    },
    {
        "name": "whois", "category": "network", "label": "Domain Registration Client", "icon": "📋",
        "synopsis": "Client for WHOIS directory service providing domain ownership & IP blocks.",
        "cmd": "whois target.com",
        "query": "How to query ARIN/RIPE/APNIC registry records and ASN ranges using whois?"
    },
    {
        "name": "dnsrecon", "category": "network", "label": "DNS Enumeration Tool", "icon": "🌐",
        "synopsis": "DNS reconnaissance tool for zone transfers, reverse lookups, and brute force.",
        "cmd": "dnsrecon -d target.com -t std,axfr,brt -D /usr/share/wordlists/dnsmap.txt",
        "query": "How to discover subdomains, SRV records, and SPF records using dnsrecon?"
    },
    {
        "name": "host", "category": "network", "label": "Simple DNS Lookup", "icon": "🔍",
        "synopsis": "Simple DNS lookup utility for resolving hostnames to IP addresses.",
        "cmd": "host -t ns target.com",
        "query": "How to perform forward, reverse, and MX lookups using host?"
    },
    {
        "name": "amass", "category": "network", "label": "In-Depth Recon Engine", "icon": "🛰️",
        "synopsis": "In-depth Attack Surface Mapping and Asset Discovery tool using OSINT.",
        "cmd": "amass enum -d target.com -active -brute -w subdomains.txt",
        "query": "How to perform attack surface mapping and active ASN discovery with OWASP Amass?"
    },
    {
        "name": "subfinder", "category": "network", "label": "Fast Subdomain Hunter", "icon": "🎯",
        "synopsis": "Fast passive subdomain discovery tool designed for security researchers.",
        "cmd": "subfinder -d target.com -all -silent -o subdomains.txt",
        "query": "How does subfinder passively discover subdomains across OSINT sources?"
    },
    {
        "name": "sublist3r", "category": "network", "label": "OSINT Subdomain Tool", "icon": "📜",
        "synopsis": "Python tool to enumerate subdomains of websites using multiple search engines.",
        "cmd": "sublist3r -d target.com -t 20 -b",
        "query": "How does Sublist3r leverage search engine scrapers and Netcraft for recon?"
    },

    # ─── Web Application & Proxies (13) ───
    {
        "name": "burpsuite", "category": "web", "label": "Web App Sec Testing", "icon": "🌐",
        "synopsis": "Integrated platform for security testing of web applications and APIs.",
        "cmd": "burpsuite &",
        "query": "How to configure Burp Suite proxy, Repeater, and Intruder for web app pentesting?"
    },
    {
        "name": "burp", "category": "web", "label": "Burp Proxy Suite", "icon": "🌐",
        "synopsis": "Interception proxy and web vulnerability assessment suite.",
        "cmd": "burpsuite --project-file=audit.burp",
        "query": "How to automate Burp Scanner and API security testing?"
    },
    {
        "name": "zap", "category": "web", "label": "OWASP ZAP", "icon": "⚡",
        "synopsis": "Open-source web application security scanner and dynamic testing proxy.",
        "cmd": "zaproxy -cmd -quickurl http://target.local -quickout report.html",
        "query": "How to configure OWASP ZAP automated baseline scans and API fuzzing?"
    },
    {
        "name": "nikto", "category": "web", "label": "Web Server Scanner", "icon": "🔎",
        "synopsis": "Web server scanner testing for dangerous files, outdated software, and misconfigs.",
        "cmd": "nikto -h http://target.local -C all",
        "query": "What vulnerabilities and misconfigurations does Nikto test for?"
    },
    {
        "name": "gobuster", "category": "web", "label": "URI / DNS Bruteforcer", "icon": "🔍",
        "synopsis": "Fast directory, DNS subdomain, and virtual host brute-forcing tool written in Go.",
        "cmd": "gobuster dir -u http://target.local -w /usr/share/wordlists/dirb/common.txt -t 40",
        "query": "How to brute force directories, vhosts, and subdomains using gobuster?"
    },
    {
        "name": "dirb", "category": "web", "label": "Web Content Scanner", "icon": "📁",
        "synopsis": "Web Content Scanner that launches dictionary-based attacks against web servers.",
        "cmd": "dirb http://target.local /usr/share/wordlists/dirb/common.txt -r",
        "query": "How does dirb perform recursive web directory crawling and status filtering?"
    },
    {
        "name": "ffuf", "category": "web", "label": "Fast Web Fuzzer", "icon": "🎯",
        "synopsis": "High-performance web fuzzer for parameter discovery and endpoint hunting.",
        "cmd": "ffuf -u http://target/FUZZ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
        "query": "How to use ffuf with custom filters (fc, fs, fr) for web fuzzing?"
    },
    {
        "name": "wpscan", "category": "web", "label": "WordPress Sec Scanner", "icon": "📰",
        "synopsis": "Black box WordPress vulnerability scanner for themes, plugins, and users.",
        "cmd": "wpscan --url http://target.local --enumerate u,vp,vt --api-token <token>",
        "query": "How to enumerate WordPress users, vulnerable plugins, and theme CVEs with WPScan?"
    },
    {
        "name": "whatweb", "category": "web", "label": "Web Tech Identifier", "icon": "💡",
        "synopsis": "Web scanner identifying CMS, blogging platforms, JS libraries, and web servers.",
        "cmd": "whatweb -a 3 http://target.local -v",
        "query": "How does WhatWeb identify backend web technologies and CMS versions?"
    },
    {
        "name": "wfuzz", "category": "web", "label": "Web App Fuzzer", "icon": "🔀",
        "synopsis": "Tool designed for brute forcing Web Applications, parameters, and HTTP headers.",
        "cmd": "wfuzz -c -z file,/usr/share/wordlists/rockyou.txt --hc 404 http://target.local/page?id=FUZZ",
        "query": "How to fuzz HTTP headers, POST bodies, and cookies using wfuzz?"
    },
    {
        "name": "sqlmap", "category": "web", "label": "SQL Injection Engine", "icon": "💉",
        "synopsis": "Automatic SQL injection and database takeover tool.",
        "cmd": "sqlmap -u 'http://target/page.php?id=1' --batch --dbs",
        "query": "How to detect and exploit SQL injection vulnerabilities with sqlmap?"
    },
    {
        "name": "nuclei", "category": "web", "label": "Vulnerability Scanner", "icon": "🚀",
        "synopsis": "Fast and customizable vulnerability scanner based on simple YAML templates.",
        "cmd": "nuclei -u https://target.local -t cves/ -severity critical,high",
        "query": "How to write and execute Nuclei YAML templates for CVE scanning?"
    },
    {
        "name": "nessus", "category": "web", "label": "Enterprise Vuln Scanner", "icon": "🏢",
        "synopsis": "Comprehensive vulnerability assessment solution for networks and cloud infrastructure.",
        "cmd": "nessuscli update",
        "query": "How does Nessus perform credentialed compliance and vulnerability scanning?"
    },

    # ─── Exploitation & Password Cracking (6) ───
    {
        "name": "metasploit", "category": "exploit", "label": "Exploitation Framework", "icon": "💥",
        "synopsis": "World's most used penetration testing and exploit development framework.",
        "cmd": "msfconsole -q",
        "query": "How does Metasploit handle payloads, encoders, multi-handlers, and sessions?"
    },
    {
        "name": "msfconsole", "category": "exploit", "label": "Metasploit Console", "icon": "💥",
        "synopsis": "Command-line interface to the Metasploit Framework.",
        "cmd": "msfconsole -x 'use exploit/multi/handler; set payload linux/x64/meterpreter/reverse_tcp; run'",
        "query": "How to configure Meterpreter handlers and automated resource scripts in msfconsole?"
    },
    {
        "name": "searchsploit", "category": "exploit", "label": "Exploit-DB CLI", "icon": "📑",
        "synopsis": "Command line search tool for Exploit-DB archive.",
        "cmd": "searchsploit apache 2.4.49 -w -m 50383",
        "query": "How to search Exploit-DB offline and mirror exploit code with searchsploit?"
    },
    {
        "name": "hydra", "category": "exploit", "label": "Online Login Cracker", "icon": "🔓",
        "synopsis": "Fast network authentication cracker supporting numerous protocols (SSH, FTP, HTTP, RDP).",
        "cmd": "hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://192.168.1.10 -t 4",
        "query": "How to execute multi-threaded online password attacks using hydra?"
    },
    {
        "name": "john", "category": "exploit", "label": "Offline Password Cracker", "icon": "🔨",
        "synopsis": "John the Ripper — password security auditing and hash recovery tool.",
        "cmd": "john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt --format=sha512crypt",
        "query": "How to crack Linux shadow hashes and format types with John the Ripper?"
    },
    {
        "name": "hashcat", "category": "exploit", "label": "GPU Hash Recovery", "icon": "🔥",
        "synopsis": "Advanced password recovery utility and GPU-accelerated hash cracker.",
        "cmd": "hashcat -m 0 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt",
        "query": "What are the common hashcat attack modes (-a 0, -a 3) and hash modes (-m 1000, 1800)?"
    },

    # ─── Wireless Security (8) ───
    {
        "name": "aircrack-ng", "category": "wireless", "label": "802.11 WEP/WPA Cracker", "icon": "📶",
        "synopsis": "Complete suite of tools to assess WiFi network security (airodump, aireplay, aircrack).",
        "cmd": "aircrack-ng -w /usr/share/wordlists/rockyou.txt -b 00:11:22:33:44:55 wpa.cap",
        "query": "How to capture WPA 4-way handshakes with airodump-ng and crack with aircrack-ng?"
    },
    {
        "name": "airmon-ng", "category": "wireless", "label": "Wireless Monitor Mode", "icon": "📡",
        "synopsis": "Bash script to enable monitor mode on wireless network interfaces.",
        "cmd": "airmon-ng start wlan0",
        "query": "How to enable monitor mode and terminate interfering processes using airmon-ng?"
    },
    {
        "name": "aireplay-ng", "category": "wireless", "label": "802.11 Packet Injector", "icon": "⚡",
        "synopsis": "Tool to generate wireless traffic and deauthenticate clients for handshake capture.",
        "cmd": "aireplay-ng --deauth 10 -a 00:11:22:33:44:55 -c AA:BB:CC:DD:EE:FF wlan0mon",
        "query": "How to perform targeted 802.11 deauthentication attacks with aireplay-ng?"
    },
    {
        "name": "airodump-ng", "category": "wireless", "label": "802.11 Packet Capturer", "icon": "🛰️",
        "synopsis": "Captures raw 802.11 frames and displays APs, clients, and captured WPA handshakes.",
        "cmd": "airodump-ng -c 6 --bssid 00:11:22:33:44:55 -w capture wlan0mon",
        "query": "How to capture WPA2/WPA3 handshakes and filter specific BSSIDs with airodump-ng?"
    },
    {
        "name": "airbase-ng", "category": "wireless", "label": "Fake AP Engine", "icon": "📡",
        "synopsis": "Multipurpose tool aimed at attacking clients by hosting Rogue APs.",
        "cmd": "airbase-ng -e 'FreeWiFi' -c 1 wlan0mon",
        "query": "How to host evil twin rogue access points with airbase-ng?"
    },
    {
        "name": "wash", "category": "wireless", "label": "WPS Enabled AP Scanner", "icon": "🔎",
        "synopsis": "Scans for WPS-enabled wireless access points on monitored interfaces.",
        "cmd": "wash -i wlan0mon",
        "query": "How to identify access points vulnerable to WPS PIN brute forcing with wash?"
    },
    {
        "name": "reaver", "category": "wireless", "label": "WPS PIN Attack Tool", "icon": "🔓",
        "synopsis": "Performs brute force attacks against Wifi Protected Setup (WPS) registrar PINs.",
        "cmd": "reaver -i wlan0mon -b 00:11:22:33:44:55 -vv -K 1",
        "query": "How to exploit WPS Pixie Dust vulnerabilities using reaver?"
    },
    {
        "name": "wifite", "category": "wireless", "label": "Automated WiFi Auditor", "icon": "🤖",
        "synopsis": "Automated wireless attack tool that orchestrates aircrack, reaver, and bully.",
        "cmd": "wifite --wpa --pmkid",
        "query": "How to capture PMKID and WPA handshakes automatically using wifite?"
    },

    # ─── Linux Sysadmin & Kernel (23) ───
    {
        "name": "iptables", "category": "linux", "label": "Linux Packet Filtering", "icon": "🧱",
        "synopsis": "Administration tool for IPv4/IPv6 packet filtering and NAT firewall in Linux kernel.",
        "cmd": "iptables -A INPUT -p tcp --dport 22 -s 192.168.1.0/24 -j ACCEPT",
        "query": "How to configure stateful Linux firewall rules, NAT, and port forwarding with iptables?"
    },
    {
        "name": "ufw", "category": "linux", "label": "Uncomplicated Firewall", "icon": "🛡️",
        "synopsis": "Program for managing netfilter firewall designed to be easy to use.",
        "cmd": "ufw default deny incoming && ufw allow 22/tcp && ufw enable",
        "query": "How to configure default-deny firewall policies and rate-limiting with ufw?"
    },
    {
        "name": "ssh", "category": "linux", "label": "Secure Shell Client", "icon": "🔐",
        "synopsis": "OpenSSH remote login client with key-based authentication and port forwarding.",
        "cmd": "ssh -N -L 8080:127.0.0.1:80 user@remote.host -i ~/.ssh/id_ed25519",
        "query": "How to configure local (-L), remote (-R), and dynamic SOCKS (-D) tunnels with SSH?"
    },
    {
        "name": "systemctl", "category": "linux", "label": "Systemd Controller", "icon": "🐧",
        "synopsis": "Control the systemd system and service manager in Linux.",
        "cmd": "systemctl status sshd.service --no-pager",
        "query": "How to manage, secure, and sandbox systemd services using systemctl and unit files?"
    },
    {
        "name": "journalctl", "category": "linux", "label": "Systemd Log Forensics", "icon": "📜",
        "synopsis": "Query and inspect logs generated by the systemd-journald service.",
        "cmd": "journalctl -u sshd.service -n 100 --no-pager",
        "query": "How to filter authentication logs, boot cycles, and kernel panics with journalctl?"
    },
    {
        "name": "dmesg", "category": "linux", "label": "Kernel Ring Buffer", "icon": "🖥️",
        "synopsis": "Print or control the kernel ring buffer for hardware and memory errors.",
        "cmd": "dmesg -T --level=err,warn",
        "query": "How to inspect kernel device initialization, hardware faults, and segfaults with dmesg?"
    },
    {
        "name": "chmod", "category": "linux", "label": "File Permissions", "icon": "🔑",
        "synopsis": "Changes file mode bits (permissions) for Owner, Group, and Others.",
        "cmd": "chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_rsa",
        "query": "Explain standard and octal Linux file permissions, SUID, SGID, and sticky bits."
    },
    {
        "name": "chown", "category": "linux", "label": "File Ownership", "icon": "👤",
        "synopsis": "Changes file owner and group in Unix-like operating systems.",
        "cmd": "chown -R www-data:www-data /var/www/html",
        "query": "How to manage file ownership and recursion safely with chown?"
    },
    {
        "name": "grep", "category": "linux", "label": "Pattern Search Utility", "icon": "🔍",
        "synopsis": "Prints lines matching a regular expression pattern across files.",
        "cmd": "grep -rnIE 'password|secret|api_key' /etc/",
        "query": "How to search recursively for regex patterns and ignore binary files with grep?"
    },
    {
        "name": "sed", "category": "linux", "label": "Stream Editor", "icon": "✂️",
        "synopsis": "Stream editor for filtering and transforming text in pipelines.",
        "cmd": "sed -i 's/PermitRootLogin yes/PermitRootLogin no/g' /etc/ssh/sshd_config",
        "query": "How to perform inline regex replacements, deletions, and transformations with sed?"
    },
    {
        "name": "awk", "category": "linux", "label": "Pattern Processing Language", "icon": "📊",
        "synopsis": "Pattern scanning and processing language for structured text reports.",
        "cmd": "awk -F: '$3 >= 1000 {print $1, $3, $6}' /etc/passwd",
        "query": "How to extract specific CSV or whitespace-delimited columns using awk?"
    },
    {
        "name": "find", "category": "linux", "label": "Filesystem Search Engine", "icon": "📂",
        "synopsis": "Searches for files in directory hierarchy matching complex criteria.",
        "cmd": "find / -perm -4000 -type f -exec ls -la {} + 2>/dev/null",
        "query": "How to find SUID root binaries, world-writable files, and modified configs with find?"
    },
    {
        "name": "bash", "category": "linux", "label": "Bourne-Again Shell", "icon": "🐚",
        "synopsis": "Standard Unix command language and interactive scripting interpreter.",
        "cmd": "bash -x script.sh",
        "query": "What are best practices for defensive Bash scripting, error traps, and debugging?"
    },
    {
        "name": "python3", "category": "linux", "label": "Python Interpreter", "icon": "🐍",
        "synopsis": "Interactive high-level object-oriented programming language runtime.",
        "cmd": "python3 -m http.server 8080",
        "query": "How to start one-liner Python web servers, test sockets, and execute automation scripts?"
    },
    {
        "name": "lsof", "category": "linux", "label": "List Open Files & Sockets", "icon": "📋",
        "synopsis": "Lists information about files and active network sockets opened by processes.",
        "cmd": "lsof -iTCP -sTCP:LISTEN -n -P",
        "query": "How to inspect listening TCP ports, open sockets, and unlinked files with lsof?"
    },
    {
        "name": "ss", "category": "linux", "label": "Socket Statistics", "icon": "⚡",
        "synopsis": "Modern utility to dump socket statistics, replacing netstat.",
        "cmd": "ss -tulpn",
        "query": "How to inspect active TCP/UDP sockets, timers, and process bindings with ss?"
    },
    {
        "name": "ip", "category": "linux", "label": "IP Routing & Devices", "icon": "🌐",
        "synopsis": "Show / manipulate routing, network devices, interfaces, and tunnels.",
        "cmd": "ip addr show && ip route show",
        "query": "How to manage network interfaces, IP aliases, and static routes using iproute2?"
    },
    {
        "name": "strace", "category": "linux", "label": "Syscall Tracer", "icon": "🔬",
        "synopsis": "Diagnostic, debugging utility for Linux to trace process system calls.",
        "cmd": "strace -f -e trace=openat,read,write,connect -p <pid>",
        "query": "How to use strace to analyze process system calls, network connects, and file opens?"
    },
    {
        "name": "ltrace", "category": "linux", "label": "Library Call Tracer", "icon": "🧪",
        "synopsis": "Intercepts and records dynamic library calls called by executed processes.",
        "cmd": "ltrace -s 100 ./binary",
        "query": "How to trace libc calls (strcmp, malloc, printf) in compiled binaries with ltrace?"
    },
    {
        "name": "nmcli", "category": "linux", "label": "NetworkManager CLI", "icon": "📶",
        "synopsis": "Command-line tool for controlling NetworkManager and WiFi connections.",
        "cmd": "nmcli device wifi list",
        "query": "How to manage VPN connections, static IPs, and WiFi networks with nmcli?"
    },
    {
        "name": "tmux", "category": "linux", "label": "Terminal Multiplexer", "icon": "🪟",
        "synopsis": "Terminal multiplexer allowing multiple sessions and persistent detached windows.",
        "cmd": "tmux new -s pentest",
        "query": "How to manage persistent background sessions and split panes with tmux?"
    },
    {
        "name": "screen", "category": "linux", "label": "Virtual Terminal Manager", "icon": "📺",
        "synopsis": "Full-screen window manager that multiplexes physical terminals.",
        "cmd": "screen -S session1",
        "query": "How to detach and reattach background terminal sessions with screen?"
    },
    {
        "name": "curl", "category": "linux", "label": "HTTP Transfer Utility", "icon": "🌐",
        "synopsis": "Command line tool for transferring data with URLs supporting all protocols.",
        "cmd": "curl -Iv -k https://target.local -H 'User-Agent: SecAudit'",
        "query": "How to test REST APIs, inspect response headers, and send custom payloads with curl?"
    },

    # ─── DevSecOps, Binaries & Forensics (10) ───
    {
        "name": "docker", "category": "devops", "label": "Container Engine", "icon": "🐳",
        "synopsis": "Pack, ship and run applications as isolated lightweight Linux containers.",
        "cmd": "docker run --rm -it --security-opt=no-new-privileges --cap-drop=ALL alpine sh",
        "query": "How to harden Docker containers with capability dropping, read-only rootfs, and user namespaces?"
    },
    {
        "name": "openssl", "category": "devops", "label": "Cryptography & TLS", "icon": "🔐",
        "synopsis": "Cryptography toolkit implementing SSL and TLS protocols with full cipher suite control.",
        "cmd": "openssl s_client -connect target.com:443 -tls1_3",
        "query": "How to inspect SSL/TLS certificates, verify cipher suites, and generate keys with openssl?"
    },
    {
        "name": "gdb", "category": "devops", "label": "GNU Debugger", "icon": "🐞",
        "synopsis": "Portable debugger that runs on many Unix-like systems for binary and memory analysis.",
        "cmd": "gdb -q ./binary -ex 'break main' -ex 'run'",
        "query": "How to analyze binary crashes, registers, and disassemble functions with gdb?"
    },
    {
        "name": "radare2", "category": "devops", "label": "Reverse Engineering Suite", "icon": "⚔️",
        "synopsis": "Advanced command-line hexadecimal editor, disassembler, and assembler.",
        "cmd": "r2 -A ./binary",
        "query": "How to analyze binary functions, control flow graphs, and xrefs in radare2?"
    },
    {
        "name": "ghidra", "category": "devops", "label": "Software Reverse Eng", "icon": "🐉",
        "synopsis": "NSA software reverse engineering (SRE) suite including decompiler and disassembler.",
        "cmd": "ghidra &",
        "query": "How to decompile x86_64 binaries, analyze cross-references, and rename symbols in Ghidra?"
    },
    {
        "name": "binwalk", "category": "devops", "label": "Firmware Analysis Tool", "icon": "📦",
        "synopsis": "Fast tool for analyzing, reverse engineering, and extracting firmware images.",
        "cmd": "binwalk -Me firmware.bin",
        "query": "How to extract embedded file systems and compressed payloads with binwalk?"
    },
    {
        "name": "foremost", "category": "devops", "label": "File Carving Forensics", "icon": "🔍",
        "synopsis": "Forensic program to recover lost files based on headers, footers, and structures.",
        "cmd": "foremost -v -t png,jpg,pdf -i disk.img -o /tmp/recovered",
        "query": "How to carve deleted files from disk images using foremost?"
    },
    {
        "name": "steghide", "category": "devops", "label": "Steganography Tool", "icon": "🕵️",
        "synopsis": "Steganography program able to hide data in various color- and audio-files.",
        "cmd": "steghide extract -sf secret.jpg",
        "query": "How to embed and extract hidden encrypted data in JPEG/WAV files using steghide?"
    },
    {
        "name": "strings", "category": "devops", "label": "Binary Strings Extractor", "icon": "🧵",
        "synopsis": "Finds and prints printable strings in files or compiled binary objects.",
        "cmd": "strings -n 8 -t x ./binary",
        "query": "How to discover hardcoded API keys, URLs, and function names with strings?"
    },
    {
        "name": "xxd", "category": "devops", "label": "Hexdump Utility", "icon": "🔢",
        "synopsis": "Creates a hex dump of a given file or standard input, and converts hex back to binary.",
        "cmd": "xxd -p binary.bin | tr -d '\\n'",
        "query": "How to create hexadecimal dumps and patch binary bytes with xxd?"
    },
    {
        "name": "file", "category": "devops", "label": "File Type Identifier", "icon": "📄",
        "synopsis": "Determines file type and MIME headers based on magic bytes.",
        "cmd": "file -i mystery_payload",
        "query": "How does the file command identify ELF binaries, compressed archives, and magic bytes?"
    }
]

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PRAG — Linux, Cybersecurity & Software Research Engine</title>
    <meta name="description" content="Offline-first Linux, DevSecOps, and Cybersecurity intelligence platform powered by Qwen3:8B & SQLite-vec.">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* ═══════════════════════════════════════════════════════
           PRAG Design System — Premium Theme System
           ═══════════════════════════════════════════════════════ */

        :root {
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --radius-xl: 20px;
            --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
            --transition-fast: 0.15s ease;
            --transition-normal: 0.25s ease;

            /* Light Theme Tokens (Default) */
            --bg-void: #f8fafc;
            --bg-deep: #f1f5f9;
            --bg-panel: rgba(255, 255, 255, 0.96);
            --bg-card: #ffffff;
            --bg-card-hover: #f8fafc;
            --glass-border: rgba(226, 232, 240, 0.95);
            --glass-border-hover: #94a3b8;
            --glass-glow: rgba(2, 132, 199, 0.08);
            --accent-cyan: #0284c7;
            --accent-blue: #2563eb;
            --accent-indigo: #4f46e5;
            --accent-purple: #7c3aed;
            --accent-green: #16a34a;
            --accent-emerald: #059669;
            --accent-amber: #d97706;
            --accent-red: #dc2626;
            --text-primary: #0f172a;
            --text-secondary: #334155;
            --text-muted: #64748b;
            --text-dim: #94a3b8;
            --gradient-brand: linear-gradient(135deg, #0284c7, #4f46e5, #7c3aed);
            --gradient-btn: linear-gradient(135deg, #0284c7, #4f46e5);
            --gradient-btn-hover: linear-gradient(135deg, #0369a1, #4338ca);
            --shadow-glow: 0 4px 20px rgba(2, 132, 199, 0.15);
            --user-bubble-bg: #f0f7ff;
            --user-bubble-border: #bfdbfe;
            --code-bg: #090d16;
            --code-header-bg: #111827;
            --code-text: #f8fafc;
            --code-accent: #38bdf8;
            --search-bg: #ffffff;
            --sticky-gradient: linear-gradient(180deg, rgba(248, 250, 252, 0) 0%, rgba(248, 250, 252, 0.85) 30%, var(--bg-void) 100%);
        }

        /* ── Dark Theme ── */
        [data-theme="dark"] {
            --bg-void: #0f1117;
            --bg-deep: #161922;
            --bg-panel: rgba(22, 25, 34, 0.96);
            --bg-card: #1c1f2e;
            --bg-card-hover: #232738;
            --glass-border: rgba(55, 65, 81, 0.8);
            --glass-border-hover: #6b7280;
            --glass-glow: rgba(56, 189, 248, 0.1);
            --accent-cyan: #38bdf8;
            --accent-blue: #60a5fa;
            --accent-indigo: #818cf8;
            --accent-purple: #a78bfa;
            --accent-green: #34d399;
            --accent-emerald: #10b981;
            --accent-amber: #fbbf24;
            --accent-red: #f87171;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --gradient-brand: linear-gradient(135deg, #38bdf8, #818cf8, #a78bfa);
            --gradient-btn: linear-gradient(135deg, #0ea5e9, #6366f1);
            --gradient-btn-hover: linear-gradient(135deg, #0284c7, #4f46e5);
            --shadow-glow: 0 4px 20px rgba(56, 189, 248, 0.2);
            --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            --user-bubble-bg: rgba(14, 165, 233, 0.1);
            --user-bubble-border: rgba(56, 189, 248, 0.3);
            --code-bg: #0a0e1a;
            --code-header-bg: #0f1420;
            --code-text: #e2e8f0;
            --code-accent: #38bdf8;
            --search-bg: #1c1f2e;
            --sticky-gradient: linear-gradient(180deg, rgba(15, 17, 23, 0) 0%, rgba(15, 17, 23, 0.85) 30%, var(--bg-void) 100%);
        }

        [data-theme="dark"] ::-webkit-scrollbar-track { background: var(--bg-void); }
        [data-theme="dark"] ::-webkit-scrollbar-thumb { background: #374151; }
        [data-theme="dark"] ::-webkit-scrollbar-thumb:hover { background: #4b5563; }

        /* Clean Scrollbars */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-void);
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
            font-family: var(--font-sans);
            background: var(--bg-void);
            color: var(--text-primary);
            line-height: 1.6;
            transition: background var(--transition-normal), color var(--transition-normal);
        }

        .app-layout {
            display: grid;
            grid-template-columns: 310px 1fr;
            grid-template-rows: 64px calc(100vh - 64px);
            height: 100vh;
            max-height: 100vh;
            overflow: hidden;
        }

        .header {
            grid-column: 1 / -1;
            background: var(--bg-panel);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--glass-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 1.5rem;
            z-index: 50;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            cursor: pointer;
        }

        .brand-icon {
            width: 38px;
            height: 38px;
            background: var(--gradient-brand);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            color: white;
            box-shadow: var(--shadow-sm);
        }

        .brand-text h1 {
            font-size: 1.12rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: var(--gradient-brand);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-text p {
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 600;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .arsenal-btn-header {
            background: rgba(2, 132, 199, 0.08);
            color: var(--accent-cyan);
            border: 1px solid rgba(2, 132, 199, 0.25);
            padding: 0.4rem 0.85rem;
            border-radius: var(--radius-md);
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            transition: all var(--transition-fast);
        }

        .arsenal-btn-header:hover {
            background: var(--accent-cyan);
            color: #ffffff;
            box-shadow: 0 2px 10px rgba(2, 132, 199, 0.3);
            transform: translateY(-1px);
        }

        .model-select {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            padding: 0.4rem 0.75rem;
            border-radius: var(--radius-md);
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-secondary);
            outline: none;
            cursor: pointer;
            font-family: inherit;
        }

        .model-select:focus { border-color: var(--accent-cyan); }

        .status-pill {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.35rem 0.75rem;
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-amber);
        }

        .status-dot.connected { background: var(--accent-green); box-shadow: 0 0 8px rgba(22, 163, 74, 0.3); }
        .status-dot.disconnected { background: var(--accent-red); }

        /* ── Sidebar ── */
        .sidebar {
            background: var(--bg-panel);
            backdrop-filter: blur(12px);
            border-right: 1px solid var(--glass-border);
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            overflow-y: auto;
        }

        .sidebar-section h3 {
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .tool-quick-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.4rem;
            margin-bottom: 0.5rem;
        }

        .tool-pill-btn {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            padding: 0.45rem 0.6rem;
            border-radius: var(--radius-md);
            font-size: 0.75rem;
            font-weight: 700;
            font-family: var(--font-mono);
            color: var(--text-secondary);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            transition: all var(--transition-fast);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .tool-pill-btn:hover {
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            background: var(--bg-card-hover);
            transform: translateY(-1px);
        }

        .history-list {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .history-item {
            padding: 0.6rem 0.75rem;
            border-radius: var(--radius-md);
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .history-item:hover {
            border-color: var(--glass-border-hover);
            background: var(--bg-card-hover);
            transform: translateX(2px);
        }

        .history-q {
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .history-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 0.25rem;
            font-size: 0.7rem;
            color: var(--text-muted);
        }

        .suggested-prompts {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .prompt-chip {
            padding: 0.5rem 0.75rem;
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            font-size: 0.75rem;
            color: var(--text-secondary);
            cursor: pointer;
            text-align: left;
            transition: all var(--transition-fast);
        }

        .prompt-chip:hover {
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            background: var(--bg-card-hover);
        }

        /* ── Main Workspace Architecture ── */
        .workspace {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 64px);
            max-height: calc(100vh - 64px);
            overflow: hidden;
            position: relative;
            background: var(--bg-void);
            padding: 0;
            width: 100%;
        }

        .workspace-scroll {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem 2rem 1rem 2rem;
            scroll-behavior: smooth;
            display: flex;
            flex-direction: column;
        }

        .workspace-inner {
            max-width: 920px;
            width: 100%;
            margin: 0 auto;
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .search-container {
            background: var(--search-bg);
            border: 1.5px solid var(--glass-border);
            border-radius: var(--radius-xl);
            padding: 0.65rem 0.85rem 0.65rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            box-shadow: 0 4px 24px -2px rgba(0, 0, 0, 0.08), 0 2px 6px -1px rgba(0, 0, 0, 0.04);
            transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
        }

        .search-container:focus-within {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 0 3px var(--glass-glow), 0 4px 24px -2px rgba(0, 0, 0, 0.08);
        }

        .search-input {
            flex: 1;
            border: none;
            background: transparent;
            font-size: 0.95rem;
            font-family: inherit;
            color: var(--text-primary);
            outline: none;
            resize: none;
            min-height: 24px;
            max-height: 180px;
            line-height: 1.5;
            padding: 0.35rem 0;
        }

        .search-input::placeholder { color: var(--text-dim); }

        .submit-btn {
            background: var(--gradient-btn);
            color: white;
            border: none;
            padding: 0.7rem 1.4rem;
            border-radius: var(--radius-lg);
            font-weight: 700;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all var(--transition-fast);
            display: flex;
            align-items: center;
            gap: 0.4rem;
            flex-shrink: 0;
        }

        .submit-btn:hover { background: var(--gradient-btn-hover); transform: translateY(-1px); }
        .submit-btn:disabled { opacity: 0.85; cursor: not-allowed; }

        .spinner {
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255, 255, 255, 0.35);
            border-radius: 50%;
            border-top-color: #ffffff;
            animation: spin 0.7s linear infinite;
            display: inline-block;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .cancel-btn {
            background: rgba(220, 38, 38, 0.12);
            color: var(--accent-red);
            border: 1px solid rgba(220, 38, 38, 0.3);
            padding: 0.75rem 1.25rem;
            border-radius: var(--radius-lg);
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all var(--transition-fast);
            display: none;
            align-items: center;
            gap: 0.4rem;
        }

        .cancel-btn:hover { background: rgba(220, 38, 38, 0.2); transform: translateY(-1px); }

        /* ── New Chat & Multi-turn Thread Buttons ── */
        .new-chat-btn-header {
            background: #ffffff;
            color: var(--text-primary);
            border: 1px solid var(--glass-border);
            padding: 0.45rem 0.85rem;
            border-radius: var(--radius-md);
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            transition: all var(--transition-fast);
            box-shadow: var(--shadow-sm);
        }

        .new-chat-btn-header:hover {
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            background: #f0f7ff;
            transform: translateY(-1px);
        }

        .new-chat-sidebar-btn {
            width: 100%;
            background: #ffffff;
            color: var(--text-primary);
            border: 1px solid var(--glass-border);
            padding: 0.65rem 1rem;
            border-radius: var(--radius-md);
            font-size: 0.84rem;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all var(--transition-fast);
            box-shadow: var(--shadow-sm);
        }

        .new-chat-sidebar-btn:hover {
            border-color: var(--accent-cyan);
            background: #f0f7ff;
            color: var(--accent-cyan);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.12);
        }

        /* ── Multi-turn Conversation Stream ── */
        .conversation-thread {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            margin-bottom: 2rem;
            width: 100%;
        }

        .user-turn-row {
            display: flex;
            justify-content: flex-end;
            margin: 1.25rem 0 0.5rem 0;
            animation: fadeIn 0.25s ease;
            width: 100%;
        }

        .user-turn-bubble {
            max-width: 82%;
            background: var(--user-bubble-bg);
            border: 1px solid var(--user-bubble-border);
            border-radius: var(--radius-xl) var(--radius-xl) 4px var(--radius-xl);
            padding: 0.85rem 1.25rem;
            box-shadow: var(--shadow-sm);
            position: relative;
        }

        .user-turn-header {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.72rem;
            color: var(--accent-cyan);
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        .user-turn-text {
            font-size: 0.95rem;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.5;
        }

        .assistant-turn-card {
            animation: fadeIn 0.3s ease;
        }

        /* ── Sticky Chat Input Bar (Permanently Anchored to Viewport Bottom) ── */
        .chat-input-sticky {
            flex-shrink: 0;
            width: 100%;
            background: var(--sticky-gradient);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            padding: 0.75rem 2rem 1.15rem 2rem;
            z-index: 40;
            border-top: 1px solid rgba(226, 232, 240, 0.5);
        }

        [data-theme="dark"] .chat-input-sticky {
            border-top: 1px solid rgba(55, 65, 81, 0.4);
        }

        .chat-input-inner {
            max-width: 920px;
            width: 100%;
            margin: 0 auto;
        }

        .chat-input-subtext {
            font-size: 0.72rem;
            color: var(--text-muted);
            text-align: center;
            margin-top: 0.45rem;
        }

        .chat-input-subtext kbd {
            background: var(--bg-deep);
            border: 1px solid var(--glass-border);
            color: var(--text-secondary);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            font-size: 0.65rem;
            font-family: var(--font-mono);
        }

        /* ── Modern Minimal Streaming Status ── */
        .streaming-status {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.55rem 0.9rem;
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: var(--radius-md);
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--accent-cyan);
            margin: 0.75rem 0 1rem 0;
            animation: fadeIn 0.2s ease;
        }

        .status-pulse-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--accent-cyan);
            animation: pulseDot 1.2s infinite ease-in-out;
        }

        @keyframes pulseDot {
            0%, 100% { opacity: 0.3; transform: scale(0.85); }
            50% { opacity: 1; transform: scale(1.25); }
        }

        /* ── Response Card ── */
        .response-card {
            background: #ffffff;
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-xl);
            padding: 1.5rem 1.75rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
            margin-bottom: 1.5rem;
            position: relative;
        }

        /* ── Response Header & Intelligence Insights ── */
        .response-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.85rem;
            flex-wrap: wrap;
            gap: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--glass-border);
        }

        .header-badges {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            flex-wrap: wrap;
        }

        .route-badge {
            background: var(--bg-deep);
            color: var(--accent-cyan);
            border: 1px solid var(--glass-border);
            padding: 0.3rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }

        .route-badge.ambiguous {
            background: rgba(217, 119, 6, 0.12);
            color: var(--accent-amber);
            border-color: rgba(217, 119, 6, 0.3);
        }

        .confidence-badge {
            padding: 0.3rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .confidence-badge.high { background: rgba(22, 163, 74, 0.12); color: var(--accent-green); border: 1px solid rgba(22, 163, 74, 0.3); }
        .confidence-badge.medium { background: rgba(217, 119, 6, 0.12); color: var(--accent-amber); border: 1px solid rgba(217, 119, 6, 0.3); }
        .confidence-badge.low { background: rgba(220, 38, 38, 0.12); color: var(--accent-red); border: 1px solid rgba(220, 38, 38, 0.3); }

        .model-badge {
            background: rgba(124, 58, 237, 0.1);
            color: var(--accent-purple);
            border: 1px solid rgba(124, 58, 237, 0.25);
            padding: 0.3rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            font-family: var(--font-mono);
        }

        .insights-bar {
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: var(--font-mono);
            flex-wrap: wrap;
        }

        /* ── Collapsible Reasoning / Thought Box ── */
        .reasoning-box {
            background: var(--bg-deep);
            border: 1px solid rgba(124, 58, 237, 0.25);
            border-radius: var(--radius-lg);
            margin-bottom: 1.25rem;
            overflow: hidden;
            display: none;
        }

        .reasoning-header {
            padding: 0.75rem 1rem;
            background: rgba(124, 58, 237, 0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
        }

        .reasoning-title {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--accent-purple);
        }

        .reasoning-stats {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .reasoning-toggle-icon {
            font-size: 0.75rem;
            transition: transform var(--transition-fast);
        }

        .reasoning-box.expanded .reasoning-toggle-icon { transform: rotate(180deg); }

        .reasoning-body {
            padding: 1rem;
            font-family: var(--font-mono);
            font-size: 0.82rem;
            color: var(--text-secondary);
            line-height: 1.6;
            max-height: 280px;
            overflow-y: auto;
            white-space: pre-wrap;
            display: none;
            border-top: 1px solid rgba(124, 58, 237, 0.15);
        }

        .reasoning-box.expanded .reasoning-body { display: block; }

        /* ── Conflict Banner ── */
        .conflict-banner {
            display: none;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            background: rgba(220, 38, 38, 0.1);
            border: 1px solid rgba(220, 38, 38, 0.3);
            border-radius: var(--radius-md);
            color: var(--accent-red);
            font-size: 0.85rem;
            margin-bottom: 1.25rem;
        }

        /* ── Main Answer Presentation ── */
        .answer-container {
            margin: 0.5rem 0;
        }

        .answer-text {
            font-size: 0.98rem;
            line-height: 1.75;
            color: var(--text-primary);
        }

        /* ── Interactive Citation Pill ── */
        .citation-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: #f0f9ff;
            color: var(--accent-cyan);
            border: 1px solid #bae6fd;
            border-radius: 4px;
            padding: 0.05rem 0.45rem;
            font-size: 0.72rem;
            font-weight: 700;
            font-family: var(--font-mono);
            cursor: pointer;
            margin: 0 0.15rem;
            transition: all var(--transition-fast);
            vertical-align: middle;
        }

        .citation-pill:hover {
            background: var(--accent-cyan);
            color: #ffffff;
            border-color: var(--accent-cyan);
            transform: scale(1.06);
        }

        .answer-reason {
            margin-top: 1rem;
            padding: 0.75rem 1rem;
            background: #f8fafc;
            border-left: 3px solid var(--accent-cyan);
            border-radius: 0 var(--radius-md) var(--radius-md) 0;
            font-size: 0.82rem;
            color: var(--text-secondary);
        }

        /* ── Grounding Sources Drawer (Collapsible Accordion) ── */
        .sources-drawer {
            margin-top: 1.25rem;
            border-top: 1px solid var(--glass-border);
            padding-top: 0.75rem;
        }

        .sources-drawer-btn {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            padding: 0.55rem 0.85rem;
            background: var(--bg-deep);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .sources-drawer-btn:hover {
            background: var(--bg-card-hover);
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }

        .sources-drawer-title {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .sources-drawer-arrow {
            font-size: 0.75rem;
            transition: transform var(--transition-fast);
        }

        .sources-drawer.open .sources-drawer-arrow {
            transform: rotate(180deg);
        }

        .sources-drawer-body {
            display: none;
            margin-top: 0.75rem;
            animation: fadeIn 0.2s ease;
        }

        .sources-drawer.open .sources-drawer-body {
            display: block;
        }

        /* ── Post-Response Action Toolbar ── */
        .action-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 1rem;
            padding-top: 0.85rem;
            border-top: 1px solid var(--glass-border);
        }

        .toolbar-left, .toolbar-right {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .tool-action-btn {
            background: #ffffff;
            border: 1px solid var(--glass-border);
            padding: 0.35rem 0.75rem;
            border-radius: var(--radius-md);
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            transition: all var(--transition-fast);
        }

        .tool-action-btn:hover {
            background: var(--bg-deep);
            border-color: var(--glass-border-hover);
            color: var(--text-primary);
            transform: translateY(-1px);
        }

        .tool-action-btn.icon-only {
            padding: 0.35rem 0.55rem;
        }

        .tool-action-btn.active {
            color: var(--accent-cyan);
            border-color: var(--accent-cyan);
            background: rgba(2, 132, 199, 0.08);
        }

        /* ── Smart Follow-up Suggestions ── */
        .followup-section {
            margin-top: 1.25rem;
            display: none;
        }

        .followup-title {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .followup-chips {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .followup-chip {
            padding: 0.45rem 0.85rem;
            background: #ffffff;
            border: 1px solid var(--glass-border);
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 500;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        }

        .followup-chip:hover {
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            background: #f0f9ff;
            transform: translateY(-1px);
        }

        /* ── Evidence Cards ── */
        .chunk-card {
            background: var(--bg-deep);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            margin-bottom: 0.75rem;
            overflow: hidden;
            transition: all var(--transition-fast);
        }

        .chunk-card:hover { border-color: var(--glass-border-hover); }

        .chunk-card.highlighted {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
        }

        .chunk-header {
            padding: 0.75rem 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
        }

        .chunk-header-left {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .chunk-index {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--accent-cyan);
            background: rgba(56, 189, 248, 0.12);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
        }

        .chunk-filename {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .chunk-header-right {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .tier-badge {
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }

        .tier-1 { background: rgba(34, 197, 94, 0.15); color: var(--accent-green); }
        .tier-1-5 { background: rgba(251, 191, 36, 0.15); color: var(--accent-amber); }
        .tier-2 { background: rgba(192, 132, 252, 0.15); color: var(--accent-purple); }
        .tier-3 { background: rgba(248, 113, 113, 0.15); color: var(--accent-red); }

        .score-bar-container {
            width: 60px;
            height: 6px;
            background: var(--glass-border);
            border-radius: 3px;
            overflow: hidden;
        }

        .score-bar {
            height: 100%;
            background: var(--accent-cyan);
            border-radius: 3px;
        }

        .chunk-expand-icon {
            font-size: 0.7rem;
            color: var(--text-muted);
            transition: transform var(--transition-fast);
        }

        .chunk-card.expanded .chunk-expand-icon { transform: rotate(180deg); }

        .chunk-body {
            padding: 1rem;
            font-size: 0.85rem;
            line-height: 1.6;
            color: var(--text-secondary);
            border-top: 1px solid var(--glass-border);
            display: none;
            background: var(--bg-card);
        }

        .chunk-card.expanded .chunk-body { display: block; }

        /* ── Code Blocks ── */
        .code-block-box {
            background: #090d16;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: var(--radius-md);
            margin: 1rem 0;
            overflow: hidden;
        }

        .code-block-header {
            background: #111827;
            padding: 0.4rem 0.85rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #94a3b8;
            font-family: var(--font-mono);
            font-weight: 600;
        }

        .code-block-box pre {
            padding: 1rem;
            overflow-x: auto;
            color: #f8fafc;
            font-family: var(--font-mono);
            font-size: 0.88rem;
            line-height: 1.5;
        }

        .copy-cmd-btn {
            background: rgba(255, 255, 255, 0.1);
            color: #e2e8f0;
            border: none;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.7rem;
            cursor: pointer;
            transition: background var(--transition-fast);
        }

        .copy-cmd-btn:hover { background: rgba(255, 255, 255, 0.2); }

        /* ── Markdown Tables & Blockquotes ── */
        .table-wrapper {
            width: 100%;
            overflow-x: auto;
            margin: 1.25rem 0;
            border-radius: var(--radius-md);
            border: 1px solid var(--glass-border);
            background: var(--bg-deep);
        }

        .markdown-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            text-align: left;
        }

        .markdown-table th {
            background: var(--bg-card);
            color: var(--accent-cyan);
            font-weight: 700;
            padding: 0.65rem 1rem;
            border-bottom: 1px solid var(--glass-border);
            font-family: var(--font-mono);
        }

        .markdown-table td {
            padding: 0.6rem 1rem;
            border-bottom: 1px solid var(--glass-border);
            color: var(--text-secondary);
        }

        .markdown-table tr:last-child td { border-bottom: none; }
        .markdown-table tr:hover td { background: var(--bg-card-hover); }

        .markdown-quote {
            border-left: 3px solid var(--accent-cyan);
            background: var(--bg-deep);
            padding: 0.6rem 1rem;
            margin: 1rem 0;
            border-radius: 0 var(--radius-md) var(--radius-md) 0;
            color: var(--text-secondary);
            font-style: italic;
        }

        /* ── Welcome Hero & Tool Arsenal Launchpad ── */
        .welcome-hero {
            padding: 2.5rem 0.5rem;
        }

        .welcome-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            color: var(--accent-cyan);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-bottom: 1rem;
        }

        .welcome-hero h2 {
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.75rem;
            color: var(--text-primary);
            line-height: 1.25;
        }

        .welcome-hero h2 .brand-gradient-text {
            background: var(--gradient-brand);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-prompt-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin: 1.25rem 0 1.75rem 0;
        }

        .hero-chip {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: 9999px;
            padding: 0.45rem 0.95rem;
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            box-shadow: var(--shadow-sm);
        }

        .hero-chip:hover {
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            transform: translateY(-1px);
            box-shadow: var(--shadow-glow);
        }

        .welcome-hero p {
            font-size: 0.98rem;
            color: var(--text-muted);
            max-width: 720px;
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }

        .arsenal-category-title {
            font-size: 0.85rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin: 1.5rem 0 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .arsenal-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
        }

        .tool-card {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-lg);
            padding: 1.15rem;
            cursor: pointer;
            transition: all var(--transition-fast);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .tool-card:hover {
            border-color: var(--accent-cyan);
            transform: translateY(-2px);
            box-shadow: var(--shadow-glow);
        }

        .tool-card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }

        .tool-card-name {
            font-family: var(--font-mono);
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .tool-card-badge {
            font-size: 0.68rem;
            font-weight: 700;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            background: var(--bg-deep);
            color: var(--accent-cyan);
            border: 1px solid var(--glass-border);
        }

        .tool-card-desc {
            font-size: 0.78rem;
            color: var(--text-muted);
            line-height: 1.4;
            margin-bottom: 0.75rem;
        }

        .tool-card-cmd {
            background: #090d16;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 6px;
            padding: 0.4rem 0.6rem;
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: #38bdf8;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* ── Modal / Arsenal Drawer ── */
        .modal-backdrop {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            z-index: 200;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }

        .modal-backdrop.active { display: flex; }

        .modal-box {
            background: var(--bg-panel);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-xl);
            max-width: 860px;
            width: 100%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 0 40px rgba(0, 0, 0, 0.5);
        }

        .modal-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--glass-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .modal-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .modal-close {
            background: transparent;
            border: none;
            font-size: 1.25rem;
            color: var(--text-muted);
            cursor: pointer;
            padding: 0.25rem;
        }

        .modal-close:hover { color: var(--text-primary); }

        .modal-body {
            padding: 1.5rem;
            overflow-y: auto;
            flex: 1;
        }

        .modal-filter-bar {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.25rem;
            flex-wrap: wrap;
        }

        .modal-filter-btn {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .modal-filter-btn:hover, .modal-filter-btn.active {
            background: var(--accent-cyan);
            color: #ffffff;
            border-color: var(--accent-cyan);
        }

        /* ── Toast ── */
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--text-primary);
            color: var(--bg-card);
            padding: 0.75rem 1.25rem;
            border-radius: var(--radius-md);
            font-size: 0.85rem;
            font-weight: 700;
            box-shadow: var(--shadow-lg);
            opacity: 0;
            transform: translateY(10px);
            transition: all var(--transition-fast);
            pointer-events: none;
            z-index: 1000;
        }

        .toast.visible { opacity: 1; transform: translateY(0); }

        @media print {
            .header, .sidebar, .search-container, .action-toolbar, .view-tabs, .followup-section, .modal-backdrop { display: none !important; }
            .workspace { padding: 0 !important; max-width: 100% !important; }
            .response-card { border: none !important; box-shadow: none !important; padding: 0 !important; }
            body { background: white !important; color: black !important; font-size: 12pt; }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .welcome-hero { animation: fadeIn 0.5s ease; }
        .welcome-hero h2 { animation: fadeIn 0.6s ease 0.1s both; }
        .welcome-hero p { animation: fadeIn 0.6s ease 0.2s both; }

        .sidebar-toggle {
            display: none;
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            padding: 0.35rem 0.55rem;
            border-radius: var(--radius-md);
            font-size: 1.1rem;
            cursor: pointer;
            color: var(--text-secondary);
            transition: all var(--transition-fast);
            line-height: 1;
        }
        .sidebar-toggle:hover { border-color: var(--accent-cyan); color: var(--accent-cyan); }

        .theme-toggle {
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            padding: 0.35rem 0.55rem;
            border-radius: var(--radius-md);
            font-size: 1rem;
            cursor: pointer;
            color: var(--text-secondary);
            transition: all var(--transition-fast);
            line-height: 1;
            display: flex;
            align-items: center;
        }
        .theme-toggle:hover { border-color: var(--accent-cyan); color: var(--accent-cyan); transform: translateY(-1px); }

        .shortcuts-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(8px);
            z-index: 300;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }
        .shortcuts-overlay.active { display: flex; }
        .shortcuts-box {
            background: var(--bg-panel);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-xl);
            padding: 2rem;
            max-width: 520px;
            width: 100%;
            box-shadow: 0 0 40px rgba(0, 0, 0, 0.3);
            animation: fadeIn 0.2s ease;
        }
        .shortcuts-title { font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem; }
        .shortcut-row { display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--glass-border); }
        .shortcut-row:last-child { border-bottom: none; }
        .shortcut-label { font-size: 0.88rem; color: var(--text-secondary); }
        .shortcut-keys { display: flex; gap: 0.3rem; }
        .shortcut-keys kbd { background: var(--bg-deep); border: 1px solid var(--glass-border); padding: 0.2rem 0.5rem; border-radius: 5px; font-size: 0.75rem; font-family: var(--font-mono); font-weight: 600; color: var(--text-primary); min-width: 28px; text-align: center; }

        .settings-section { padding: 0.75rem 0; }
        .settings-row { display: flex; align-items: center; justify-content: space-between; padding: 0.45rem 0; }
        .settings-label { font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }
        .settings-select { background: var(--bg-card); border: 1px solid var(--glass-border); padding: 0.3rem 0.5rem; border-radius: var(--radius-sm); font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); outline: none; cursor: pointer; font-family: inherit; }
        .settings-select:focus { border-color: var(--accent-cyan); }
        .settings-range-group { display: flex; align-items: center; gap: 0.5rem; }
        .settings-range { width: 80px; accent-color: var(--accent-cyan); }
        .settings-range-val { font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; color: var(--accent-cyan); min-width: 28px; text-align: right; }

        .export-btn {
            width: 100%;
            background: var(--bg-card);
            color: var(--text-secondary);
            border: 1px solid var(--glass-border);
            padding: 0.5rem 0.75rem;
            border-radius: var(--radius-md);
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.4rem;
            transition: all var(--transition-fast);
        }
        .export-btn:hover { border-color: var(--accent-cyan); color: var(--accent-cyan); transform: translateY(-1px); }

        .footer-status {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1.25rem;
            padding: 0.5rem 0;
            font-size: 0.68rem;
            color: var(--text-dim);
            font-family: var(--font-mono);
            border-top: 1px solid var(--glass-border);
            margin-top: 0.5rem;
        }
        .footer-status span { display: flex; align-items: center; gap: 0.25rem; }

        /* ── Mobile Sidebar Backdrop ── */
        .sidebar-backdrop {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(4px);
            z-index: 95;
            display: none;
        }
        .sidebar-backdrop.active { display: block; }

        @media (max-width: 900px) {
            .app-layout { grid-template-columns: 1fr; }
            .sidebar {
                position: fixed;
                top: 64px; left: 0; bottom: 0;
                width: 300px;
                z-index: 100;
                transform: translateX(-100%);
                transition: transform var(--transition-normal);
                box-shadow: 4px 0 20px rgba(0, 0, 0, 0.15);
            }
            .sidebar.active, .sidebar.mobile-open { transform: translateX(0); }
            .sidebar-toggle { display: block; }
            .workspace-scroll { padding: 1rem 1rem 0.5rem 1rem; }
            .chat-input-sticky { padding: 0.5rem 1rem 0.75rem 1rem; }
            .welcome-hero h2 { font-size: 1.5rem; }
            .arsenal-grid { grid-template-columns: 1fr; }
            .header-controls .arsenal-btn-header span:last-child { display: none; }
        }

        @media (max-width: 480px) {
            .header { padding: 0 0.75rem; }
            .brand-text p { display: none; }
            .header-controls { gap: 0.4rem; }
            .model-select { max-width: 120px; font-size: 0.7rem; }
            .search-container { padding: 0.45rem 0.6rem 0.45rem 0.85rem; }
            .submit-btn { padding: 0.6rem 1rem; font-size: 0.8rem; }
            .response-card { padding: 1rem; }
            .workspace-scroll { padding: 0.75rem 0.5rem; }
        }
    </style>
</head>
<body>
    <div class="sidebar-backdrop" id="sidebarBackdrop" onclick="closeSidebar()"></div>
    <div class="app-layout">
        <!-- Header -->
        <header class="header">
            <div style="display:flex;align-items:center;gap:0.75rem;">
                <button class="sidebar-toggle" id="sidebarToggle" onclick="toggleSidebar()" title="Toggle Sidebar">&#9776;</button>
                <div class="brand" onclick="resetToHome()">
                    <div class="brand-icon">⚡</div>
                    <div class="brand-text">
                        <h1>PRAG</h1>
                        <p>Linux, Cybersecurity &amp; Software Research Engine</p>
                    </div>
                </div>
            </div>

            <div class="header-controls">
                <button class="new-chat-btn-header" onclick="startNewChat()" title="Start New Conversation">
                    <span>✨</span>
                    <span>New Chat</span>
                </button>

                <button class="arsenal-btn-header" onclick="openArsenalModal()">
                    <span>🛡️</span>
                    <span>Security Arsenal (72)</span>
                </button>

                <button class="header-btn" onclick="openContextModal()" title="AI Memory &amp; User Preferences (CONTEXT.md)" style="background:var(--bg-deep);border:1px solid var(--glass-border);color:var(--text-secondary);padding:0.45rem 0.8rem;border-radius:var(--radius-sm);font-size:0.8rem;font-weight:600;display:inline-flex;align-items:center;gap:0.35rem;cursor:pointer;">
                    <span>🧠</span>
                    <span>AI Context</span>
                </button>

                <button class="header-btn" onclick="openShortcutsModal()" title="Keyboard Shortcuts (?)" style="background:var(--bg-deep);border:1px solid var(--glass-border);color:var(--text-secondary);padding:0.45rem 0.6rem;border-radius:var(--radius-sm);font-size:0.8rem;font-weight:600;display:inline-flex;align-items:center;gap:0.25rem;cursor:pointer;">
                    <span>⌨️</span>
                </button>

                <select id="modelSelect" class="model-select" title="Choose Inference Model">
                    <option value="qwen2.5:3b">⚡ Qwen 2.5 (3B - Fast · 1s)</option>
                    <option value="qwen3:8b" selected>🧠 Qwen 3 (8B - Deep Reasoning)</option>
                    <option value="llama3.2:latest">🦙 Llama 3.2 (3B - Balanced)</option>
                </select>

                <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" title="Toggle Dark/Light Mode">🌙</button>

                <div class="status-pill" id="statusPill" title="Ollama Model Connectivity">
                    <div class="status-dot" id="statusDot"></div>
                    <span id="statusText">Connecting...</span>
                </div>
            </div>
        </header>

        <!-- Sidebar -->
        <aside class="sidebar" id="sidebarPanel">
            <button class="new-chat-sidebar-btn" onclick="startNewChat()">
                <span>✨</span>
                <span>Start New Conversation</span>
            </button>

            <div class="sidebar-section">
                <h3>
                    <span>🛡️ Linux & Security Tools</span>
                    <span style="font-size:0.68rem;color:var(--accent-cyan);cursor:pointer;" onclick="openArsenalModal()">All 72 →</span>
                </h3>
                <div class="tool-quick-grid">
                    <div class="tool-pill-btn" onclick="researchTool('nmap')">🛡️ nmap</div>
                    <div class="tool-pill-btn" onclick="researchTool('burpsuite')">🌐 burpsuite</div>
                    <div class="tool-pill-btn" onclick="researchTool('sqlmap')">💉 sqlmap</div>
                    <div class="tool-pill-btn" onclick="researchTool('iptables')">🧱 iptables</div>
                    <div class="tool-pill-btn" onclick="researchTool('wireshark')">🦈 wireshark</div>
                    <div class="tool-pill-btn" onclick="researchTool('hydra')">🔓 hydra</div>
                    <div class="tool-pill-btn" onclick="researchTool('docker')">🐳 docker</div>
                    <div class="tool-pill-btn" onclick="researchTool('strace')">🔬 strace</div>
                </div>
            </div>

            <div class="sidebar-section">
                <h3>🎯 Curated TTPs & Queries</h3>
                <div class="suggested-prompts">
                    <div class="prompt-chip" onclick="fillQuery('How do I run a stealth SYN scan with OS and version detection using nmap?')">🛡️ Nmap Stealth SYN Scan</div>
                    <div class="prompt-chip" onclick="fillQuery('What are the core flags to dump a MySQL database using sqlmap?')">💉 SQLMap Automated DB Injection</div>
                    <div class="prompt-chip" onclick="fillQuery('How to drop incoming traffic on port 22 except from a specific IP using iptables?')">🧱 Linux Firewall Packet Rules</div>
                    <div class="prompt-chip" onclick="fillQuery('What are the essential Linux capabilities and security flags for docker run?')">🐳 Docker Container Hardening</div>
                    <div class="prompt-chip" onclick="fillQuery('How to trace active network sockets and open files for a PID using lsof and ss?')">🔍 Process & Socket Forensics</div>
                </div>
            </div>

            <div class="sidebar-section">
                <h3>⚙️ Settings</h3>
                <div class="settings-section">
                    <div class="settings-row">
                        <span class="settings-label">Source Filter</span>
                        <select id="sourceFilter" class="settings-select" title="Filter retrieval source">
                            <option value="">Auto-Route</option>
                            <option value="kali_docs">Kali Docs</option>
                            <option value="local_file">Local Files</option>
                            <option value="all">All Sources</option>
                        </select>
                    </div>
                    <div class="settings-row">
                        <span class="settings-label">Top-K Chunks</span>
                        <div class="settings-range-group">
                            <input type="range" class="settings-range" id="topKRange" min="1" max="8" value="3" oninput="document.getElementById('topKVal').textContent = this.value">
                            <span class="settings-range-val" id="topKVal">3</span>
                        </div>
                    </div>
                </div>
                <button class="export-btn" onclick="exportConversation()" title="Export current conversation as Markdown">
                    <span>📄</span>
                    <span>Export Conversation</span>
                </button>
            </div>

            <div class="sidebar-section" style="flex:1;">
                <h3>Recent Queries</h3>
                <div class="history-list" id="historyList">
                    <p style="font-size:0.75rem;color:var(--text-muted);font-style:italic;">No recent queries yet</p>
                </div>
            </div>

            <div class="footer-status" id="footerStatus">
                <span>📦 <span id="footerChunks">0</span> chunks</span>
                <span>🛠️ <span id="footerTools">0</span> tools</span>
                <span>📊 <span id="footerQueries">0</span> queries</span>
            </div>
        </aside>

        <!-- Main Workspace -->
        <main class="workspace" id="workspaceMain">
            <div class="workspace-scroll" id="workspaceScroll">
                <div class="workspace-inner">
                    <!-- Welcome State with Security & Linux Arsenal Focus -->
                    <div class="welcome-hero" id="welcomeState">
                        <div class="welcome-badge">🛡️ Offline-Grounded Cybersecurity &amp; Systems Engine</div>
                        <h2>Fact-Grounded <span class="brand-gradient-text">Linux &amp; Security Intelligence</span></h2>
                        <p>Query verified documentation for 72+ Kali Linux offensive and defensive utilities, Linux kernel subsystems, DevSecOps pipelines, and technical reasoning with full multi-turn conversation memory.</p>

                        <!-- Instant Clickable Starter Prompts -->
                        <div class="hero-prompt-chips">
                            <button class="hero-chip" onclick="fillQuery('How do I run a stealth SYN scan with OS and version detection using nmap?')">🛡️ Nmap Stealth SYN Scan</button>
                            <button class="hero-chip" onclick="fillQuery('What are the core flags to dump a MySQL database using sqlmap?')">💉 SQLMap DB Injection</button>
                            <button class="hero-chip" onclick="fillQuery('How to drop incoming traffic on port 22 except from a specific IP using iptables?')">🧱 Linux Firewall Rules</button>
                            <button class="hero-chip" onclick="fillQuery('What are the essential Linux capabilities and security flags for docker run?')">🐳 Docker Hardening</button>
                        </div>

                        <!-- Core Tool Launchpads -->
                        <div class="arsenal-category-title">
                            <span>🛡️</span>
                            <span>Featured Security &amp; Systems Arsenal</span>
                            <span style="font-size:0.75rem;color:var(--accent-cyan);cursor:pointer;margin-left:auto;text-transform:none;letter-spacing:normal;" onclick="openArsenalModal()">View All 72 Tools →</span>
                        </div>
                        <div class="arsenal-grid" id="featuredArsenalGrid"></div>
                    </div>

                    <!-- Continuous Multi-turn Conversation Thread -->
                    <div class="conversation-thread" id="conversationThread"></div>
                </div>
            </div>

            <!-- Sticky Chat Input Bar (Permanently Anchored to Viewport Bottom) -->
            <div class="chat-input-sticky">
                <div class="chat-input-inner">
                    <div class="search-container">
                        <textarea id="queryInput" class="search-input" placeholder="Ask a question or continue conversation... (Shift+Enter for newline, / to focus)" rows="1" autocomplete="off"></textarea>
                        <button id="cancelBtn" class="cancel-btn" onclick="cancelQuery()">⏹ Stop</button>
                        <button id="submitBtn" class="submit-btn" onclick="submitQuery()">
                            <span>Research</span>
                            <span>→</span>
                        </button>
                    </div>
                    <div class="chat-input-subtext">Press <kbd>Enter</kbd> to submit · <kbd>Shift + Enter</kbd> for newline · <kbd>?</kbd> for shortcuts · Conversation memory active</div>
                </div>
            </div>
        </main>
    </div>

    <!-- Security Tool Arsenal Modal -->
    <div class="modal-backdrop" id="arsenalModal" onclick="if(event.target === this) closeArsenalModal()">
        <div class="modal-box">
            <div class="modal-header">
                <div class="modal-title">
                    <span>🛡️</span>
                    <span>Linux & Cybersecurity Tool Arsenal</span>
                </div>
                <button class="modal-close" onclick="closeArsenalModal()">✕</button>
            </div>
            <div class="modal-body">
                <div class="modal-filter-bar">
                    <button class="modal-filter-btn active" onclick="filterModalArsenal('all', this)">All Tools (72)</button>
                    <button class="modal-filter-btn" onclick="filterModalArsenal('network', this)">📡 Network & Recon</button>
                    <button class="modal-filter-btn" onclick="filterModalArsenal('web', this)">🌐 Web & APIs</button>
                    <button class="modal-filter-btn" onclick="filterModalArsenal('exploit', this)">⚡ Exploit & Cracking</button>
                    <button class="modal-filter-btn" onclick="filterModalArsenal('linux', this)">🐧 Linux & Kernel</button>
                    <button class="modal-filter-btn" onclick="filterModalArsenal('devops', this)">💻 DevSecOps & Binaries</button>
                </div>
                <div class="arsenal-grid" id="modalArsenalGrid"></div>
            </div>
        </div>
    </div>

    <!-- Keyboard Shortcuts Modal -->
    <div class="modal-backdrop" id="shortcutsModal" onclick="if(event.target === this) closeShortcutsModal()">
        <div class="modal-box" style="max-width: 540px;">
            <div class="modal-header">
                <div class="modal-title">
                    <span>⌨️</span>
                    <span>Keyboard Shortcuts</span>
                </div>
                <button class="modal-close" onclick="closeShortcutsModal()">✕</button>
            </div>
            <div class="modal-body" style="padding: 1.25rem 1.5rem;">
                <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                    <tbody>
                        <tr style="border-bottom:1px solid var(--glass-border);">
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">Enter</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">Send research query</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--glass-border);">
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">Shift + Enter</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">New line in query box</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--glass-border);">
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">/</kbd> or <kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">Ctrl + K</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">Focus search input</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--glass-border);">
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">Ctrl + Shift + D</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">Toggle Dark / Light theme</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--glass-border);">
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">Ctrl + Shift + S</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">Toggle sidebar</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--glass-border);">
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">Ctrl + Shift + E</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">Export conversation (.md)</td>
                        </tr>
                        <tr style="border-bottom:1px solid var(--glass-border);">
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">?</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">Open this shortcuts dialog</td>
                        </tr>
                        <tr>
                            <td style="padding:0.6rem 0;color:var(--text-secondary);"><kbd style="background:var(--bg-deep);padding:0.2rem 0.5rem;border-radius:4px;border:1px solid var(--glass-border);font-family:var(--font-mono);">Esc</kbd></td>
                            <td style="padding:0.6rem 0;color:var(--text-primary);">Close any active modal</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- AI Context & Memory Modal -->
    <div class="modal-backdrop" id="contextModal" onclick="if(event.target === this) closeContextModal()">
        <div class="modal-box" style="max-width: 820px; height: 80vh;">
            <div class="modal-header">
                <div class="modal-title">
                    <span>🧠</span>
                    <span>AI Context &amp; Memory (<code>CONTEXT.md</code>)</span>
                </div>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    <button class="modal-filter-btn active" id="contextPreviewTabBtn" onclick="switchContextTab('preview')">👁️ Preview</button>
                    <button class="modal-filter-btn" id="contextEditTabBtn" onclick="switchContextTab('edit')">✏️ Edit Raw</button>
                    <button class="modal-close" onclick="closeContextModal()">✕</button>
                </div>
            </div>
            <div class="modal-body" style="padding: 1.25rem 1.5rem; flex: 1; overflow-y: auto;">
                <div style="background:rgba(2,132,199,0.08);border:1px solid rgba(2,132,199,0.25);border-radius:var(--radius-md);padding:0.75rem 1rem;font-size:0.8rem;color:var(--text-secondary);margin-bottom:1rem;line-height:1.5;">
                    💡 <strong>Persistent Memory:</strong> This file is read by PRAG on every query to enforce your preferred answer style, tools, and technical focus. The model also self-edits this file when you state preferences like <em>"remember that I prefer Debian"</em> or <em>"always include bash flags"</em>.
                </div>
                <div id="contextPreviewContainer" style="font-size:0.88rem;line-height:1.6;color:var(--text-primary);">
                    <div style="text-align:center;padding:2rem;color:var(--text-muted);">Loading context...</div>
                </div>
                <div id="contextEditContainer" style="display:none;height:calc(100% - 90px);display:none;flex-direction:column;gap:0.75rem;">
                    <textarea id="contextRawTextarea" style="width:100%;height:320px;background:var(--bg-deep);border:1px solid var(--glass-border);border-radius:var(--radius-md);padding:0.75rem;font-family:var(--font-mono);font-size:0.82rem;color:var(--text-primary);resize:vertical;"></textarea>
                    <div style="display:flex;justify-content:flex-end;gap:0.5rem;">
                        <button onclick="loadContextContent()" style="background:var(--bg-deep);border:1px solid var(--glass-border);color:var(--text-secondary);padding:0.5rem 1rem;border-radius:var(--radius-sm);cursor:pointer;font-weight:600;">Revert</button>
                        <button onclick="saveContextContent()" style="background:var(--gradient-btn);color:#ffffff;border:none;padding:0.5rem 1.2rem;border-radius:var(--radius-sm);cursor:pointer;font-weight:700;">Save Context</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toast">Copied to clipboard</div>

    <script>
        const toolsCatalog = """ + json.dumps(SECURITY_TOOLS_CATALOG) + r""";

        let currentAnswer = '';
        let currentThinking = '';
        let currentChunks = [];
        let currentQuery = '';
        let lastFullPayload = null;
        let activeAbortController = null;
        let ttsSpeechInstance = null;
        let isSpeaking = false;

        // Render Tool Cards
        function renderFeaturedArsenal() {
            const grid = document.getElementById('featuredArsenalGrid');
            grid.innerHTML = '';
            toolsCatalog.slice(0, 9).forEach(t => {
                grid.appendChild(createToolCard(t));
            });
        }

        function renderModalArsenal(category = 'all') {
            const grid = document.getElementById('modalArsenalGrid');
            grid.innerHTML = '';
            const filtered = category === 'all' ? toolsCatalog : toolsCatalog.filter(t => t.category === category);
            filtered.forEach(t => {
                grid.appendChild(createToolCard(t));
            });
        }

        function createToolCard(tool) {
            const card = document.createElement('div');
            card.className = 'tool-card';
            card.innerHTML = `
                <div>
                    <div class="tool-card-top">
                        <div class="tool-card-name"><span>${tool.icon}</span> <span>${escapeHtml(tool.name)}</span></div>
                        <span class="tool-card-badge">${escapeHtml(tool.label)}</span>
                    </div>
                    <div class="tool-card-desc">${escapeHtml(tool.synopsis)}</div>
                </div>
                <div class="tool-card-cmd" title="Click to copy command" onclick="event.stopPropagation(); copyCommandText('${encodeURIComponent(tool.cmd)}')">
                    <span><code>${escapeHtml(tool.cmd)}</code></span>
                    <span style="font-size:0.65rem;color:var(--text-muted);">📋</span>
                </div>
            `;
            card.onclick = () => {
                closeArsenalModal();
                fillQuery(tool.query);
            };
            return card;
        }

        function filterModalArsenal(cat, btn) {
            document.querySelectorAll('.modal-filter-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            renderModalArsenal(cat);
        }

        function openArsenalModal() {
            renderModalArsenal('all');
            document.getElementById('arsenalModal').classList.add('active');
        }

        function closeArsenalModal() {
            document.getElementById('arsenalModal').classList.remove('active');
        }

        function researchTool(toolName) {
            const t = toolsCatalog.find(x => x.name === toolName);
            if (t) {
                fillQuery(t.query);
            } else {
                fillQuery(`Explain how to use ${toolName} with syntax and options.`);
            }
        }

        // Theme Management
        function initTheme() {
            const saved = localStorage.getItem('prag-theme') || 'light';
            setTheme(saved);
        }

        function setTheme(theme) {
            const btn = document.getElementById('themeToggle');
            if (theme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
                if (btn) { btn.textContent = '☀️'; btn.title = 'Switch to Light Mode (Ctrl+Shift+D)'; }
                localStorage.setItem('prag-theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
                if (btn) { btn.textContent = '🌙'; btn.title = 'Switch to Dark Mode (Ctrl+Shift+D)'; }
                localStorage.setItem('prag-theme', 'light');
            }
        }

        function toggleTheme() {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            setTheme(isDark ? 'light' : 'dark');
            showToast(isDark ? '☀️ Light Mode Activated' : '🌙 Dark Mode Activated');
        }

        // Sidebar Navigation
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebarPanel');
            const backdrop = document.getElementById('sidebarBackdrop');
            if (sidebar) sidebar.classList.toggle('active');
            if (backdrop) backdrop.classList.toggle('active');
        }

        function closeSidebar() {
            const sidebar = document.getElementById('sidebarPanel');
            const backdrop = document.getElementById('sidebarBackdrop');
            if (sidebar) sidebar.classList.remove('active');
            if (backdrop) backdrop.classList.remove('active');
        }

        // Keyboard Shortcuts Modal
        function openShortcutsModal() {
            document.getElementById('shortcutsModal').classList.add('active');
        }

        function closeShortcutsModal() {
            document.getElementById('shortcutsModal').classList.remove('active');
        }

        // AI Context & Preferences Modal
        function openContextModal() {
            loadContextContent();
            document.getElementById('contextModal').classList.add('active');
        }

        function closeContextModal() {
            document.getElementById('contextModal').classList.remove('active');
        }

        function switchContextTab(tab) {
            const prevBtn = document.getElementById('contextPreviewTabBtn');
            const editBtn = document.getElementById('contextEditTabBtn');
            const prevCont = document.getElementById('contextPreviewContainer');
            const editCont = document.getElementById('contextEditContainer');
            if (tab === 'preview') {
                prevBtn.classList.add('active');
                editBtn.classList.remove('active');
                prevCont.style.display = 'block';
                editCont.style.display = 'none';
                prevCont.innerHTML = renderMarkdown(document.getElementById('contextRawTextarea').value);
            } else {
                editBtn.classList.add('active');
                prevBtn.classList.remove('active');
                prevCont.style.display = 'none';
                editCont.style.display = 'flex';
            }
        }

        async function loadContextContent() {
            try {
                const res = await fetch('/api/context');
                if (res.ok) {
                    const data = await res.json();
                    const raw = data.content || '';
                    document.getElementById('contextRawTextarea').value = raw;
                    document.getElementById('contextPreviewContainer').innerHTML = renderMarkdown(raw);
                }
            } catch (e) {
                document.getElementById('contextPreviewContainer').innerHTML = '<p style="color:var(--accent-red)">Failed to load CONTEXT.md</p>';
            }
        }

        async function saveContextContent() {
            const content = document.getElementById('contextRawTextarea').value;
            try {
                const res = await fetch('/api/context', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
                if (res.ok) {
                    showToast('✓ CONTEXT.md saved successfully!');
                    switchContextTab('preview');
                } else {
                    showToast('⚠️ Failed to save CONTEXT.md');
                }
            } catch (e) {
                showToast('⚠️ Error saving context');
            }
        }

        // Export Conversation as Markdown
        function exportConversation() {
            if (!conversationHistory || conversationHistory.length === 0) {
                showToast('⚠️ No conversation to export');
                return;
            }
            let md = '# PRAG Research Session Export\\n\\n';
            md += `_Exported on ${new Date().toLocaleString()} · PRAG Cybersecurity & Systems Engine_\\n\\n---\\n\\n`;
            conversationHistory.forEach((turn, idx) => {
                if (turn.role === 'user') {
                    md += `### 👤 User Query\\n\\n${turn.content}\\n\\n`;
                } else if (turn.role === 'assistant') {
                    md += `### ⚡ PRAG Research Answer\\n\\n${turn.content}\\n\\n`;
                    if (turn.sources && turn.sources.length > 0) {
                        md += '**Verified Sources Cited:**\\n';
                        turn.sources.forEach((s, sIdx) => {
                            md += `- [${sIdx + 1}] ${s.file_name} (${s.tier_label || 'Verified Doc'})\\n`;
                        });
                        md += '\\n';
                    }
                    md += '---\\n\\n';
                }
            });
            const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            a.download = `prag-research-${ts}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('📄 Conversation exported as Markdown');
        }

        // Status Check
        async function checkStatus() {
            try {
                const res = await fetch('/api/status');
                if (res.ok) {
                    const data = await res.json();
                    const dot = document.getElementById('statusDot');
                    const text = document.getElementById('statusText');
                    if (data.ollama_status === 'connected') {
                        dot.className = 'status-dot connected';
                        text.textContent = 'Ollama Ready';
                    } else {
                        dot.className = 'status-dot disconnected';
                        text.textContent = 'Ollama Offline';
                    }

                    // Update footer stats
                    const fChunks = document.getElementById('footerChunks');
                    const fTools = document.getElementById('footerTools');
                    const fQueries = document.getElementById('footerQueries');
                    if (fChunks) fChunks.textContent = ((data.local_chunks || 0) + (data.kali_chunks || 0)).toLocaleString();
                    if (fTools) fTools.textContent = data.kali_tools_synced || 72;
                    if (fQueries) fQueries.textContent = (data.total_queries || 0).toLocaleString();

                    if (data.available_models && data.available_models.length > 0) {
                        const sel = document.getElementById('modelSelect');
                        const currentVal = sel.value;
                        const existingOpts = Array.from(sel.options).map(o => o.value);
                        data.available_models.forEach(m => {
                            if (!existingOpts.includes(m)) {
                                const opt = document.createElement('option');
                                opt.value = m;
                                opt.textContent = '⚡ ' + m;
                                sel.appendChild(opt);
                            }
                        });
                        if (currentVal) sel.value = currentVal;
                    }
                }
            } catch (e) {}
        }

        // Load History
        async function loadHistory() {
            try {
                const res = await fetch('/api/history');
                if (res.ok) {
                    const data = await res.json();
                    const list = document.getElementById('historyList');
                    if (!data.queries || data.queries.length === 0) {
                        list.innerHTML = '<p style="font-size:0.75rem;color:var(--text-muted);font-style:italic;">No queries logged yet</p>';
                        return;
                    }
                    list.innerHTML = '';
                    data.queries.slice(0, 15).forEach(q => {
                        const item = document.createElement('div');
                        item.className = 'history-item';
                        item.onclick = () => fillQuery(q.question);
                        const confClass = (q.confidence || 'unknown').toLowerCase();
                        item.innerHTML = `
                            <div class="history-q">${escapeHtml(q.question)}</div>
                            <div class="history-meta">
                                <span>${escapeHtml(q.route || 'all')}</span>
                                <span class="confidence-badge ${confClass}" style="padding:0.1rem 0.35rem;font-size:0.65rem;">${escapeHtml(q.confidence || '')}</span>
                            </div>`;
                        list.appendChild(item);
                    });
                }
            } catch (e) {}
        }

        // Pipeline Stages UI
        function setStage(id, status) {
            const el = document.getElementById(id);
            if (el) {
                el.classList.remove('active', 'done');
                if (status) el.classList.add(status);
            }
        }

        function setConn(id, done) {
            const el = document.getElementById(id);
            if (el) {
                if (done) el.classList.add('done');
                else el.classList.remove('done');
            }
        }

        let conversationHistory = []; // [{role: 'user', content: '...'}, {role: 'assistant', content: '...'}]
        let conversationTurns = {};   // turnId -> { question, answer, thinking, chunks, payload, latency_ms, ... }
        let activeTurnId = null;
        let activeSpeakingTurnId = null;

        // Start New Conversation (Clears Thread & Context Memory)
        function startNewChat() {
            if (activeAbortController) {
                try { activeAbortController.abort(); } catch (e) {}
            }
            if (isSpeaking && window.speechSynthesis) {
                window.speechSynthesis.cancel();
                isSpeaking = false;
                activeSpeakingTurnId = null;
            }
            conversationHistory = [];
            conversationTurns = {};
            activeTurnId = null;
            document.getElementById('conversationThread').innerHTML = '';
            document.getElementById('welcomeState').style.display = 'block';
            const input = document.getElementById('queryInput');
            if (input) {
                input.value = '';
                input.style.height = 'auto';
                input.focus();
            }
            showToast('✨ Started new conversation');
        }

        function resetToHome() {
            startNewChat();
        }

        // Fill Query or Submit directly
        function fillQuery(text) {
            const input = document.getElementById('queryInput');
            if (input) {
                input.value = text;
                input.style.height = 'auto';
                submitQuery();
            }
        }

        // Reasoning Toggle per Turn
        function toggleTurnReasoning(turnId) {
            const box = document.getElementById(`reasoningBox-${turnId}`);
            if (box) box.classList.toggle('expanded');
        }

        // Grounding Sources Drawer Toggle per Turn
        function toggleTurnSources(turnId) {
            const drawer = document.getElementById(`sourcesDrawer-${turnId}`);
            if (drawer) drawer.classList.toggle('open');
        }

        // Citation Jump per Turn
        function jumpToCitation(idx, turnId = null) {
            const tid = turnId || activeTurnId;
            if (!tid) return;
            const drawer = document.getElementById(`sourcesDrawer-${tid}`);
            if (drawer && !drawer.classList.contains('open')) {
                drawer.classList.add('open');
            }
            const card = document.getElementById(`chunk-card-${tid}-${idx}`);
            if (card) {
                card.classList.add('expanded', 'highlighted');
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                setTimeout(() => card.classList.remove('highlighted'), 2500);
            }
        }

        // Follow-ups Generator per Turn
        function generateFollowupsForTurn(turnId, question, answer) {
            const q = (question || '').toLowerCase();
            const suggestions = [];

            if (q.includes('nmap') || q.includes('scan') || q.includes('port')) {
                suggestions.push('How can defensive firewalls or IDS detect this scan?');
                suggestions.push('What is the difference between -sS (SYN) and -sT (Connect) scans?');
                suggestions.push('Show example NSE scripts for automated vulnerability detection.');
            } else if (q.includes('sqlmap') || q.includes('sql') || q.includes('injection')) {
                suggestions.push('How to prevent SQL injection using prepared statements in code?');
                suggestions.push('What are the flags to bypass WAF filters in sqlmap (--tamper)?');
                suggestions.push('Explain blind time-based SQL injection mechanics.');
            } else if (q.includes('iptables') || q.includes('firewall') || q.includes('ufw')) {
                suggestions.push('How to persist iptables rules across system reboots?');
                suggestions.push('How to rate-limit SYN flood attacks using iptables hashlimit?');
                suggestions.push('Explain the difference between INPUT, FORWARD, and PREROUTING chains.');
            } else if (q.includes('docker') || q.includes('container')) {
                suggestions.push('How to run Docker rootless to prevent privilege escalation?');
                suggestions.push('What are seccomp and AppArmor profiles in Docker?');
                suggestions.push('How to scan Docker container images for CVEs?');
            } else if (q.includes('lsof') || q.includes('strace') || q.includes('pid')) {
                suggestions.push('How to trace memory leaks or zombie processes in Linux?');
                suggestions.push('How to use perf or eBPF to trace kernel-level latency?');
                suggestions.push('What does lsof +L1 indicate for deleted open files?');
            } else {
                suggestions.push('What are the essential defensive hardening steps for this?');
                suggestions.push('Can you explain the previous answer in more depth?');
                suggestions.push('How to automate this workflow in a Bash or Python script?');
            }

            const container = document.getElementById(`followupChips-${turnId}`);
            if (!container) return;
            container.innerHTML = '';
            suggestions.slice(0, 3).forEach(s => {
                const chip = document.createElement('div');
                chip.className = 'followup-chip';
                chip.textContent = s;
                chip.onclick = () => fillQuery(s);
                container.appendChild(chip);
            });
            const sec = document.getElementById(`followupSection-${turnId}`);
            if (sec) sec.style.display = 'block';
        }

        // Cancel Active Query
        function cancelQuery() {
            if (activeAbortController) {
                try { activeAbortController.abort(); } catch (e) {}
            }
            const btn = document.getElementById('submitBtn');
            const cancelBtn = document.getElementById('cancelBtn');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span>Research</span><span>→</span>';
            }
            if (cancelBtn) cancelBtn.style.display = 'none';
            showToast('⏹ Generation stopped');
        }

        // Feedback per Turn
        function submitTurnFeedback(turnId, isPositive, btn) {
            const turn = conversationTurns[turnId];
            if (btn) btn.classList.add('active');
            if (turn && turn.question) {
                fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: turn.question,
                        feedback: isPositive ? 'positive' : 'negative'
                    })
                }).catch(() => {});
            }
            showToast(isPositive ? '👍 Helpful rating saved' : '👎 Feedback noted');
        }

        // Copy Clean Answer per Turn
        function copyTurnAnswer(turnId, btn) {
            const turn = conversationTurns[turnId];
            if (!turn || !turn.answer) return;
            navigator.clipboard.writeText(turn.answer).then(() => {
                if (btn) {
                    const label = btn.querySelector('.btn-copy-label') || btn;
                    const orig = label.innerHTML;
                    label.innerHTML = '✓ Copied';
                    setTimeout(() => { label.innerHTML = orig; }, 1800);
                }
                showToast('📋 Copied answer to clipboard');
            });
        }

        // Append User Message to Thread
        function appendUserMessage(turnId, question, timeStr) {
            const thread = document.getElementById('conversationThread');
            const row = document.createElement('div');
            row.className = 'user-turn-row';
            row.id = `user-row-${turnId}`;
            row.innerHTML = `
                <div class="user-turn-bubble">
                    <div class="user-turn-header">
                        <span class="user-avatar">👤</span>
                        <span class="user-name">You</span>
                        <span class="user-time">${timeStr}</span>
                    </div>
                    <div class="user-turn-text">${escapeHtml(question)}</div>
                </div>
            `;
            thread.appendChild(row);
        }

        // Append Assistant Card to Thread (Minimalist, Tab-Free, Clean)
        function appendAssistantCard(turnId, modelChoice) {
            const thread = document.getElementById('conversationThread');
            const card = document.createElement('div');
            card.className = 'response-card assistant-turn-card';
            card.id = `assistant-card-${turnId}`;
            card.innerHTML = `
                <div class="response-header">
                    <div class="header-badges">
                        <span class="route-badge" id="route-${turnId}">📡 Routing...</span>
                        <span class="confidence-badge high" id="conf-${turnId}">🟢 High</span>
                        <span class="model-badge">⚡ ${escapeHtml(modelChoice)}</span>
                    </div>
                    <div class="insights-bar">
                        <span id="insightTime-${turnId}">⏱ 0ms</span>
                        <span id="insightWords-${turnId}">📝 0 words</span>
                    </div>
                </div>

                <!-- Minimal Streaming Status Indicator -->
                <div class="streaming-status" id="streamingStatus-${turnId}">
                    <div class="status-pulse-dot"></div>
                    <span id="statusStageText-${turnId}">Analyzing query & retrieving technical documentation...</span>
                </div>

                <!-- Collapsible Reasoning Box -->
                <div class="reasoning-box" id="reasoningBox-${turnId}">
                    <div class="reasoning-header" onclick="toggleTurnReasoning('${turnId}')">
                        <div class="reasoning-title">
                            <span>🧠 Thought Process & Step-by-Step Reasoning</span>
                        </div>
                        <div class="reasoning-stats">
                            <span id="reasoningTokens-${turnId}">0 tokens</span>
                            <span class="reasoning-toggle-icon">▼</span>
                        </div>
                    </div>
                    <div class="reasoning-body" id="reasoningText-${turnId}"></div>
                </div>

                <!-- Conflict Warning Banner -->
                <div class="conflict-banner" id="conflictBanner-${turnId}" style="display:none;">
                    <span>⚠️</span>
                    <span><strong>Source Discrepancy Flagged:</strong> Retrieved multi-tier sources expressed conflicting information. See synthesis below.</span>
                </div>

                <!-- Main Formatted Answer -->
                <div class="answer-container" id="answerContainer-${turnId}">
                    <div class="answer-text" id="answerText-${turnId}"></div>
                    <div class="answer-reason" id="answerReason-${turnId}" style="display:none;"></div>
                </div>

                <!-- Grounding Sources Drawer (Collapsible Accordion) -->
                <div class="sources-drawer" id="sourcesDrawer-${turnId}" style="display:none;">
                    <button class="sources-drawer-btn" type="button" onclick="toggleTurnSources('${turnId}')">
                        <span class="sources-drawer-title">
                            <span>📚 Grounding Sources (<span id="evidenceCount-${turnId}">0</span>)</span>
                        </span>
                        <span class="sources-drawer-arrow" id="sourcesArrow-${turnId}">▾</span>
                    </button>
                    <div class="sources-drawer-body" id="sourcesBody-${turnId}">
                        <div class="evidence-list" id="chunksList-${turnId}"></div>
                    </div>
                </div>

                <!-- Clean Action Toolbar -->
                <div class="action-toolbar" id="actionToolbar-${turnId}">
                    <div class="toolbar-left">
                        <button class="tool-action-btn" onclick="copyTurnAnswer('${turnId}', this)" title="Copy answer">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                            <span class="btn-copy-label">Copy</span>
                        </button>
                    </div>
                    <div class="toolbar-right">
                        <button class="tool-action-btn icon-only" onclick="submitTurnFeedback('${turnId}', true, this)" title="Helpful answer">👍</button>
                        <button class="tool-action-btn icon-only" onclick="submitTurnFeedback('${turnId}', false, this)" title="Needs improvement">👎</button>
                    </div>
                </div>

                <!-- Smart Follow-up Suggestions -->
                <div class="followup-section" id="followupSection-${turnId}" style="display:none;">
                    <div class="followup-title">💡 Suggested Follow-up Questions</div>
                    <div class="followup-chips" id="followupChips-${turnId}"></div>
                </div>
            `;
            thread.appendChild(card);
        }

        // Scroll to Bottom Helper
        function scrollToBottom() {
            const scroller = document.getElementById('workspaceScroll') || document.getElementById('workspaceMain');
            if (scroller) {
                scroller.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' });
            }
        }

        // Submit Query with Multi-turn Memory & Contextual Conversation Thread
        async function submitQuery(overrideQuery = null) {
            const input = document.getElementById('queryInput');
            const q = (overrideQuery !== null ? overrideQuery : input.value).trim();
            if (!q) return;

            const modelChoice = document.getElementById('modelSelect').value;
            const btn = document.getElementById('submitBtn');
            const cancelBtn = document.getElementById('cancelBtn');
            const welcome = document.getElementById('welcomeState');

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span><span>Researching...</span>';
            cancelBtn.style.display = 'inline-flex';
            welcome.style.display = 'none';

            input.value = '';
            input.style.height = 'auto';

            const turnId = 'turn_' + Date.now();
            activeTurnId = turnId;
            const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            appendUserMessage(turnId, q, nowTime);
            appendAssistantCard(turnId, modelChoice);
            scrollToBottom();

            let streamedAnswer = '';
            let streamedThinking = '';
            let thinkTokensCount = 0;
            let currentChunks = [];
            let lastFullPayload = null;

            activeAbortController = new AbortController();
            const t0 = performance.now();

            try {
                // Send current question AND full conversation history so model remembers context
                const historyPayload = conversationHistory.map(m => ({
                    role: m.role,
                    content: m.content
                }));

                const topKVal = parseInt(document.getElementById('topKRange')?.value || 3);
                const sourceFilterVal = document.getElementById('sourceFilter')?.value || '';

                const response = await fetch('/api/ask-stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: q,
                        model: modelChoice,
                        top_k: topKVal,
                        source_type: sourceFilterVal,
                        history: historyPayload
                    }),
                    signal: activeAbortController.signal
                });

                if (!response.ok) throw new Error('Server returned status ' + response.status);

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    let boundary;
                    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
                        const message = buffer.substring(0, boundary);
                        buffer = buffer.substring(boundary + 2);

                        let eventType = 'message';
                        let eventData = '';
                        for (const line of message.split('\n')) {
                            if (line.startsWith('event: ')) eventType = line.substring(7).trim();
                            else if (line.startsWith('data: ')) eventData += line.substring(6);
                        }

                        if (eventType === 'stage') {
                            const stage = JSON.parse(eventData);
                            const statusTextEl = document.getElementById(`statusStageText-${turnId}`);
                            if (statusTextEl) {
                                const stageMessages = {
                                    'route': 'Classifying query intent & execution route...',
                                    'route_done': 'Route resolved. Searching verified documentation...',
                                    'retrieve': 'Retrieving knowledge chunks...',
                                    'retrieve_done': 'Retrieved chunks. Scoring technical relevance...',
                                    'rerank': 'Reranking & verifying source evidence...',
                                    'rerank_done': 'Sources verified. Synthesizing response...',
                                    'generate': 'Synthesizing verified answer...',
                                    'generate_done': 'Finalizing response...'
                                };
                                if (stageMessages[stage.name]) {
                                    statusTextEl.textContent = stageMessages[stage.name];
                                }
                            }
                        }

                        else if (eventType === 'think') {
                            const thinkData = JSON.parse(eventData);
                            thinkTokensCount += 1;
                            streamedThinking += thinkData.token;
                            const rBox = document.getElementById(`reasoningBox-${turnId}`);
                            const rText = document.getElementById(`reasoningText-${turnId}`);
                            const rTok = document.getElementById(`reasoningTokens-${turnId}`);
                            if (rBox) rBox.style.display = 'block';
                            if (rText) rText.textContent = streamedThinking;
                            if (rTok) rTok.textContent = `${thinkTokensCount} tokens`;
                        }

                        else if (eventType === 'meta') {
                            const meta = JSON.parse(eventData);
                            currentChunks = meta.chunks || [];
                            lastFullPayload = meta;

                            const confClass = (meta.confidence || 'high').toLowerCase();
                            const confIcon = { high: '🟢', medium: '🟡', low: '🔴' }[confClass] || '🟢';
                            const routeClass = meta.is_ambiguous ? 'route-badge ambiguous' : 'route-badge';
                            const routeLabel = `📡 ${meta.route || 'research'}`;

                            const rBadge = document.getElementById(`route-${turnId}`);
                            const cBadge = document.getElementById(`conf-${turnId}`);
                            if (rBadge) {
                                rBadge.className = routeClass;
                                rBadge.textContent = routeLabel;
                            }
                            if (cBadge) {
                                cBadge.className = `confidence-badge ${confClass}`;
                                cBadge.innerHTML = `${confIcon} ${meta.confidence || 'High'}`;
                            }

                            const confBanner = document.getElementById(`conflictBanner-${turnId}`);
                            if (confBanner) confBanner.style.display = meta.has_conflict ? 'flex' : 'none';

                            const evCount = document.getElementById(`evidenceCount-${turnId}`);
                            if (evCount) evCount.textContent = currentChunks.length;

                            const sDrawer = document.getElementById(`sourcesDrawer-${turnId}`);
                            if (sDrawer) {
                                sDrawer.style.display = currentChunks.length > 0 ? 'block' : 'none';
                            }

                            const cl = document.getElementById(`chunksList-${turnId}`);
                            if (cl) {
                                cl.innerHTML = '';
                                if (currentChunks.length === 0) {
                                    cl.innerHTML = '<p style="padding:1rem;color:var(--text-muted);font-style:italic;">Direct computation & logical deduction — zero external document dependencies.</p>';
                                } else {
                                    currentChunks.forEach((c, i) => {
                                        const tc = c.tier <= 1 ? 'tier-1' : c.tier <= 1.5 ? 'tier-1-5' : c.tier <= 2 ? 'tier-2' : 'tier-3';
                                        const sp = Math.round((c.rerank_score || 0) * 100);
                                        const d = document.createElement('div');
                                        d.className = 'chunk-card';
                                        d.id = `chunk-card-${turnId}-${i + 1}`;
                                        d.innerHTML = `
                                            <div class="chunk-header" onclick="this.parentElement.classList.toggle('expanded')">
                                                <div class="chunk-header-left">
                                                    <span class="chunk-index">[${i + 1}]</span>
                                                    <span class="chunk-filename">${escapeHtml(c.file_name)}</span>
                                                </div>
                                                <div class="chunk-header-right">
                                                    <span class="tier-badge ${tc}">${escapeHtml(c.tier_label)}</span>
                                                    <div class="score-bar-container"><div class="score-bar" style="width:${sp}%"></div></div>
                                                    <span class="chunk-expand-icon">▼</span>
                                                </div>
                                            </div>
                                            <div class="chunk-body">${escapeHtml(c.chunk_text)}</div>`;
                                        cl.appendChild(d);
                                    });
                                }
                            }
                        }

                        else if (eventType === 'token') {
                            const tokenData = JSON.parse(eventData);
                            streamedAnswer += tokenData.token;
                            const ansEl = document.getElementById(`answerText-${turnId}`);
                            if (ansEl) ansEl.innerHTML = renderMarkdown(streamedAnswer, turnId);
                            scrollToBottom();
                        }

                        else if (eventType === 'done') {
                            const final = JSON.parse(eventData);
                            const elapsed = Math.round(performance.now() - t0);

                            const statusEl = document.getElementById(`streamingStatus-${turnId}`);
                            if (statusEl) statusEl.style.display = 'none';

                            const finalAnswer = final.answer_text || streamedAnswer;
                            const finalThinking = final.thinking_process || streamedThinking;

                            const ansEl = document.getElementById(`answerText-${turnId}`);
                            if (ansEl) ansEl.innerHTML = renderMarkdown(finalAnswer, turnId);

                            if (finalThinking) {
                                const rBox = document.getElementById(`reasoningBox-${turnId}`);
                                const rText = document.getElementById(`reasoningText-${turnId}`);
                                if (rBox) rBox.style.display = 'block';
                                if (rText) rText.textContent = finalThinking;
                            }

                            const conf = final.confidence || 'High';
                            const confClass = conf.toLowerCase();
                            const confIcon = { high: '🟢', medium: '🟡', low: '🔴' }[confClass] || '🟢';
                            const routeClass = final.is_ambiguous ? 'route-badge ambiguous' : 'route-badge';
                            const routeLabel = `📡 ${final.route || 'research'}`;

                            const rBadge = document.getElementById(`route-${turnId}`);
                            const cBadge = document.getElementById(`conf-${turnId}`);
                            if (rBadge) {
                                rBadge.className = routeClass;
                                rBadge.textContent = routeLabel;
                            }
                            if (cBadge) {
                                cBadge.className = `confidence-badge ${confClass}`;
                                cBadge.innerHTML = `${confIcon} ${conf}`;
                            }

                            const confBanner = document.getElementById(`conflictBanner-${turnId}`);
                            if (confBanner) confBanner.style.display = final.has_conflict ? 'flex' : 'none';

                            const reasonEl = document.getElementById(`answerReason-${turnId}`);
                            if (reasonEl && final.reason) {
                                reasonEl.textContent = '💡 ' + final.reason;
                                reasonEl.style.display = 'block';
                            }

                            // Update insights for this turn
                            const words = finalAnswer.trim().split(/\s+/).filter(w => w.length > 0).length;
                            const timeEl = document.getElementById(`insightTime-${turnId}`);
                            const wordsEl = document.getElementById(`insightWords-${turnId}`);
                            if (timeEl) timeEl.textContent = `⏱ ${elapsed}ms`;
                            if (wordsEl) wordsEl.textContent = `📝 ${words} words`;

                            // Generate smart follow-up suggestions
                            generateFollowupsForTurn(turnId, q, finalAnswer);

                            // Store turn state
                            conversationTurns[turnId] = {
                                turnId,
                                question: q,
                                answer: finalAnswer,
                                thinking: finalThinking,
                                chunks: currentChunks,
                                payload: final,
                                latency_ms: elapsed
                            };

                            // Save to conversation history memory for subsequent turns
                            conversationHistory.push({ role: 'user', content: q });
                            conversationHistory.push({ role: 'assistant', content: finalAnswer });

                            loadHistory();
                            checkStatus();

                            btn.disabled = false;
                            btn.innerHTML = '<span>Research</span><span>→</span>';
                            cancelBtn.style.display = 'none';
                            scrollToBottom();
                            try { reader.cancel(); } catch (e) {}
                            break;
                        }
                    }
                }
            } catch (err) {
                if (err.name !== 'AbortError') {
                    showToast('⚠️ ' + (err.message || 'Error executing calculation'));
                }
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span>Research</span><span>→</span>';
                cancelBtn.style.display = 'none';
                activeAbortController = null;
            }
        }

        // Command Copy Helper
        function copyCommand(btn, codeB64) {
            try {
                const codeText = decodeURIComponent(atob(codeB64));
                navigator.clipboard.writeText(codeText).then(() => {
                    const orig = btn.innerHTML;
                    btn.innerHTML = '✓ Copied!';
                    setTimeout(() => { btn.innerHTML = orig; }, 1800);
                });
            } catch (e) {
                showToast('📋 Copied command');
            }
        }

        function copyCommandText(encoded) {
            const code = decodeURIComponent(encoded);
            navigator.clipboard.writeText(code).then(() => {
                showToast('📋 Copied: ' + code);
            });
        }

        function copyInlineCode(el) {
            const text = el.textContent || el.innerText;
            navigator.clipboard.writeText(text).then(() => showToast('📋 Copied: ' + text));
        }

        // Markdown Renderer with Tables, Quotes, Code Blocks, Lists, and Citation Links
        function renderMarkdown(md, turnId = null) {
            if (!md) return '';
            let text = md.trim();

            const codeBlocks = [];

            // 1. Extract closed code blocks
            text = text.replace(/```([a-z0-9_+-]*)\n([\s\S]*?)```/gi, function(match, lang, code) {
                const rawCode = code.trim();
                const cleanCode = escapeHtml(rawCode);
                const langLabel = lang ? escapeHtml(lang.toUpperCase()) : 'BASH';
                const codeB64 = btoa(encodeURIComponent(rawCode));

                const html = `<div class="code-block-box">
                    <div class="code-block-header">
                        <span>💻 ${langLabel}</span>
                        <button class="copy-cmd-btn" onclick="copyCommand(this, '${codeB64}')">📋 Copy</button>
                    </div>
                    <pre><code>${cleanCode}</code></pre>
                </div>`;
                codeBlocks.push(html);
                return `\n\n___CODEBLOCK_${codeBlocks.length - 1}___\n\n`;
            });

            // 2. Extract unclosed streaming code block at the end
            if (/```([a-z0-9_+-]*)\n([\s\S]*)$/i.test(text)) {
                text = text.replace(/```([a-z0-9_+-]*)\n([\s\S]*)$/i, function(match, lang, code) {
                    const rawCode = code.trim();
                    const cleanCode = escapeHtml(rawCode);
                    const langLabel = lang ? escapeHtml(lang.toUpperCase()) : 'STREAMING';
                    const codeB64 = btoa(encodeURIComponent(rawCode));

                    const html = `<div class="code-block-box">
                        <div class="code-block-header">
                            <span>💻 ${langLabel} <span class="spinner" style="width:10px;height:10px;margin-left:4px;"></span></span>
                            <button class="copy-cmd-btn" onclick="copyCommand(this, '${codeB64}')">📋 Copy</button>
                        </div>
                        <pre><code>${cleanCode}</code></pre>
                    </div>`;
                    codeBlocks.push(html);
                    return `\n\n___CODEBLOCK_${codeBlocks.length - 1}___\n\n`;
                });
            }

            // 3. Inline code
            text = text.replace(/`([^`]+)`/g, function(match, code) {
                return `<code class="inline-code" style="background:var(--bg-deep);padding:0.1rem 0.4rem;border-radius:4px;font-family:var(--font-mono);font-size:0.85em;cursor:pointer;" onclick="copyInlineCode(this)" title="Click to copy">${escapeHtml(code)}</code>`;
            });

            // 4. Citation pills
            const turnArg = turnId ? `'${turnId}'` : 'null';
            text = text.replace(/\[(\d+)\]/g, `<span class="citation-pill" onclick="jumpToCitation($1, ${turnArg})" title="Jump to citation #$1">[$1]</span>`);

            // 5. Markdown Tables
            text = text.replace(/(?:(?:^|\n)\|[^\n]+\|\r?\n(?:\|(?:\s*[:\-]+\s*\|)+\r?\n)(?:\|[^\n]+\|\r?\n?)+)/gm, function(tableMatch) {
                const lines = tableMatch.trim().split('\n').map(l => l.trim()).filter(l => l.startsWith('|') && l.endsWith('|'));
                if (lines.length < 3) return tableMatch;
                const headers = lines[0].slice(1, -1).split('|').map(h => h.trim());
                let tableHtml = '<div class="table-wrapper"><table class="markdown-table"><thead><tr>';
                headers.forEach(h => {
                    tableHtml += `<th>${renderInline(h)}</th>`;
                });
                tableHtml += '</tr></thead><tbody>';
                for (let i = 2; i < lines.length; i++) {
                    const cells = lines[i].slice(1, -1).split('|').map(c => c.trim());
                    tableHtml += '<tr>';
                    for (let c = 0; c < headers.length; c++) {
                        tableHtml += `<td>${renderInline(cells[c] || '')}</td>`;
                    }
                    tableHtml += '</tr>';
                }
                tableHtml += '</tbody></table></div>';
                return `\n\n${tableHtml}\n\n`;
            });

            function renderInline(str) {
                let s = str;
                s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
                s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');
                return s;
            }

            // 6. Blockquotes
            text = text.replace(/^\>\s+(.*$)/gim, '<blockquote class="markdown-quote">$1</blockquote>');

            // 7. Headings
            text = text.replace(/^#### (.*$)/gim, '<h5 style="font-size:0.95rem;margin:0.9rem 0 0.3rem;font-weight:700;">$1</h5>');
            text = text.replace(/^### (.*$)/gim, '<h4 style="font-size:1.05rem;margin:1rem 0 0.4rem;font-weight:700;">$1</h4>');
            text = text.replace(/^## (.*$)/gim, '<h3 style="font-size:1.2rem;margin:1.2rem 0 0.5rem;font-weight:700;">$1</h3>');
            text = text.replace(/^# (.*$)/gim, '<h2 style="font-size:1.35rem;margin:1.4rem 0 0.6rem;font-weight:800;">$1</h2>');

            // 8. Bold and Italics
            text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

            // 9. Horizontal rules
            text = text.replace(/^(?:---|\*\*\*|___)\s*$/gim, '<hr style="border:none;border-top:1px solid var(--glass-border);margin:1.2rem 0;">');

            // 10. Ordered Lists
            text = text.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li class="num-item" style="margin-left:1.5rem;margin-bottom:0.35rem;"><span style="color:var(--accent-cyan);font-weight:600;">$1.</span> $2</li>');
            text = text.replace(/(<li class="num-item"[^>]*>.*<\/li>\n?)+/g, '<ol style="margin:0.6rem 0;list-style:none;padding-left:0;">$&</ol>');

            // 11. Bullet Lists
            text = text.replace(/^\s*[\-\*•]\s+(.*$)/gim, '<li style="margin-left:1.5rem;margin-bottom:0.3rem;">$1</li>');
            text = text.replace(/(<li style="margin-left:1.5rem;margin-bottom:0.3rem;">.*<\/li>\n?)+/g, '<ul style="margin:0.6rem 0;">$&</ul>');

            // 12. Paragraphs
            let paragraphs = text.split(/\n\n+/);
            text = paragraphs.map(p => {
                p = p.trim();
                if (!p) return '';
                if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<div') || p.startsWith('<blockquote') || p.startsWith('<hr') || p.startsWith('___CODEBLOCK_')) {
                    return p;
                }
                return `<p style="margin-bottom:0.75rem;">${p.replace(/\n/g, '<br>')}</p>`;
            }).join('\n');

            // 13. Reinsert code blocks
            text = text.replace(/___CODEBLOCK_(\d+)___/g, function(match, idx) {
                return codeBlocks[parseInt(idx, 10)] || '';
            });

            return text;
        }

        function escapeHtml(s) {
            if (!s) return '';
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }

        function fillQuery(t) {
            document.getElementById('queryInput').value = t;
            document.getElementById('queryInput').focus();
            submitQuery();
        }

        function showToast(m, dur = 2500) {
            const t = document.getElementById('toast');
            t.textContent = m;
            t.classList.add('visible');
            setTimeout(() => t.classList.remove('visible'), dur);
        }

        function copyAnswer(btn) {
            if (!currentAnswer) {
                showToast('⚠️ No answer to copy');
                return;
            }
            navigator.clipboard.writeText(currentAnswer).then(() => {
                showToast('📋 Markdown copied to clipboard');
                if (btn) {
                    const orig = btn.innerHTML;
                    btn.innerHTML = '✓ Copied!';
                    setTimeout(() => { btn.innerHTML = orig; }, 1800);
                }
            }).catch(() => {
                showToast('📋 Markdown copied');
            });
        }

        function copyWithCitations(btn) {
            if (!currentAnswer) {
                showToast('⚠️ No answer to copy');
                return;
            }
            let t = currentAnswer + '\n\n--- Verified Sources ---\n';
            if (currentChunks.length === 0) {
                t += 'Fact-grounded technical intelligence\n';
            } else {
                currentChunks.forEach((c, i) => {
                    t += `[${i + 1}] ${c.file_name} (${c.tier_label})\n`;
                });
            }
            navigator.clipboard.writeText(t).then(() => {
                showToast('📎 Copied with sources');
                if (btn) {
                    const orig = btn.innerHTML;
                    btn.innerHTML = '✓ Copied with Sources!';
                    setTimeout(() => { btn.innerHTML = orig; }, 1800);
                }
            }).catch(() => {
                showToast('📎 Copied with sources');
            });
        }

        // Global Keybindings & Input Auto-resize
        const queryInputEl = document.getElementById('queryInput');
        if (queryInputEl) {
            queryInputEl.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 180) + 'px';
            });
        }

        document.addEventListener('keydown', function(e) {
            const isTyping = document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA';

            if (e.key === '?' && !isTyping) {
                e.preventDefault();
                openShortcutsModal();
            }
            if ((e.key === '/' || (e.ctrlKey && e.key.toLowerCase() === 'k')) && !isTyping) {
                e.preventDefault();
                const qEl = document.getElementById('queryInput');
                if (qEl) qEl.focus();
            }
            if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') {
                e.preventDefault();
                toggleTheme();
            }
            if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 's') {
                e.preventDefault();
                toggleSidebar();
            }
            if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'e') {
                e.preventDefault();
                exportConversation();
            }
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                submitQuery();
            }
            if (e.key === 'Enter' && document.activeElement.id === 'queryInput' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                submitQuery();
            }
            if (e.key === 'Escape') {
                closeArsenalModal();
                closeShortcutsModal();
                closeContextModal();
                closeSidebar();
            }
        });

        // Initialize on load
        initTheme();
        renderFeaturedArsenal();
        checkStatus();
        loadHistory();
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>"""


class RAGRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _safe_write(self, data: bytes):
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self._safe_write(HTML_PAGE.encode("utf-8"))

        elif self.path == "/api/status":
            self._handle_status()

        elif self.path == "/api/stats":
            self._handle_stats()

        elif self.path.startswith("/api/history"):
            self._handle_history()

        elif self.path == "/api/tools":
            self._handle_tools()

        elif self.path == "/api/context":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self._safe_write(json.dumps({"content": read_context_raw()}).encode("utf-8"))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self._safe_write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def _handle_tools(self):
        """Returns the full security & Linux tools catalog."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self._safe_write(json.dumps({"tools": SECURITY_TOOLS_CATALOG}).encode("utf-8"))

    def _handle_status(self):
        """Returns system status — Ollama connectivity, active model, DB stats, and model list."""
        active_model = get_best_available_model()
        status = {
            "ollama_status": "unknown",
            "model": active_model,
            "available_models": [],
            "db_exists": os.path.exists(DB_PATH),
            "local_chunks": 0,
            "kali_chunks": 0,
            "kali_tools_synced": 0,
            "last_kali_sync": None,
            "total_queries": 0
        }

        try:
            import ollama
            client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
            models_info = client.list()
            status["ollama_status"] = "connected"
            if hasattr(models_info, 'models'):
                status["available_models"] = [m.model for m in models_info.models]
            elif isinstance(models_info, dict) and 'models' in models_info:
                status["available_models"] = [m.get('name') or m.get('model') for m in models_info['models']]
        except Exception:
            status["ollama_status"] = "disconnected"

        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                try:
                    cursor.execute("SELECT source_type, COUNT(*) FROM chunks GROUP BY source_type")
                    for stype, count in cursor.fetchall():
                        if stype == "local_file":
                            status["local_chunks"] = count
                        elif stype == "kali_docs":
                            status["kali_chunks"] = count
                except Exception:
                    pass

                try:
                    cursor.execute("SELECT COUNT(*), MAX(last_synced) FROM kali_sources")
                    row = cursor.fetchone()
                    if row:
                        status["kali_tools_synced"] = row[0] or 0
                        status["last_kali_sync"] = row[1]
                except Exception:
                    pass

                try:
                    cursor.execute("SELECT COUNT(*) FROM query_log")
                    status["total_queries"] = cursor.fetchone()[0] or 0
                except Exception:
                    pass

                conn.close()
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self._safe_write(json.dumps(status).encode("utf-8"))

    def _handle_stats(self):
        """Returns aggregate query statistics."""
        stats = get_query_stats(DB_PATH)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self._safe_write(json.dumps(stats).encode("utf-8"))

    def _handle_history(self):
        """Returns recent query history."""
        queries = get_recent_queries(limit=20, db_path=DB_PATH)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self._safe_write(json.dumps({"queries": queries}).encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/ask":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(post_data)
                question = payload.get("question", "").strip()
                model_name = payload.get("model")
                history = payload.get("history", [])
                top_k = int(payload.get("top_k", 3))
                source_type = payload.get("source_type") or None

                if not question:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Empty question"}).encode('utf-8'))
                    return

                res = run_pipeline(
                    question=question,
                    base_dir=BASE_DIR,
                    db_path=DB_PATH,
                    source_type=source_type,
                    model_name=model_name,
                    top_k=top_k,
                    history=history
                )

                resp_data = {
                    "question": res["question"],
                    "route": res["route"],
                    "is_ambiguous": res.get("is_ambiguous", False),
                    "chunks": res["chunks"],
                    "has_conflict": res["has_conflict"],
                    "answer": res["parsed"]["answer_text"],
                    "thinking_process": res.get("thinking_process", ""),
                    "parsed": res["parsed"],
                    "latency_ms": res["latency_ms"]
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self._safe_write(json.dumps(resp_data).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self._safe_write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif self.path == "/api/ask-stream":
            self._handle_ask_stream()

        elif self.path == "/api/feedback":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(post_data)
                question = payload.get("question", "").strip()
                feedback = payload.get("feedback", "positive").strip()
                if question:
                    save_feedback(question, feedback, DB_PATH)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self._safe_write(json.dumps({"status": "ok", "feedback": feedback}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self._safe_write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif self.path == "/api/context":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(post_data)
                content = payload.get("content", "")
                success = write_context_raw(content)
                self.send_response(200 if success else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self._safe_write(json.dumps({"status": "ok" if success else "error"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self._safe_write(json.dumps({"error": str(e)}).encode('utf-8'))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self._safe_write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def _send_sse(self, event: str, data: dict):
        """Send a single SSE event."""
        msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        self.wfile.write(msg.encode("utf-8"))
        self.wfile.flush()

    def _handle_ask_stream(self):
        """SSE streaming endpoint with instant math solver, thinking events, model switching, and conversation memory."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')

        try:
            payload = json.loads(post_data)
            question = payload.get("question", "").strip()
            model_name = payload.get("model") or get_best_available_model()
            history = payload.get("history", [])
            top_k_req = int(payload.get("top_k", 3))
            source_filter = payload.get("source_type") or None

            if not question:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self._safe_write(json.dumps({"error": "Empty question"}).encode('utf-8'))
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            start_time = time.time()

            # Contextualize query for routing & retrieval if this is a follow-up
            retrieval_query = contextualize_query_from_history(question, history)

            # Check math solver pre-computation
            math_eval = evaluate_math_query(question)
            if math_eval and math_eval.get("is_math"):
                self._send_sse("stage", {"name": "route"})
                self._send_sse("stage", {"name": "route_done", "route": "math_code", "is_ambiguous": False})
                self._send_sse("stage", {"name": "retrieve_done"})
                self._send_sse("stage", {"name": "rerank_done"})
                self._send_sse("stage", {"name": "generate"})

                res_val = math_eval.get("formatted_result", "")
                steps_md = "\n".join([f"- {s}" for s in math_eval.get("steps", [])])
                raw_answer = (
                    f"### Result: **{res_val}**\n\n"
                    f"**Exact Calculation & Step-by-Step Derivation:**\n"
                    f"{steps_md}\n\n"
                    f"Confidence: High\n"
                    f"Reason: Evaluated with exact precision via symbolic arithmetic engine.\n"
                    f"Sources: Exact Math Engine"
                )

                elapsed_ms = int((time.time() - start_time) * 1000)
                thinking = "Evaluated formula deterministically using Python/SymPy arithmetic engine to eliminate rounding and LLM hallucination errors."
                parsed = parse_answer_metadata(raw_answer, potential_conflict=False)
                parsed["thinking_process"] = thinking
                parsed["confidence"] = "High"

                self._send_sse("meta", {
                    "route": "math_code",
                    "is_ambiguous": False,
                    "chunks": [],
                    "has_conflict": False,
                    "confidence": "High"
                })
                self._send_sse("think", {"token": thinking})
                self._send_sse("token", {"token": parsed.get("answer_text", raw_answer)})
                self._send_sse("stage", {"name": "generate_done"})

                self._send_sse("done", {
                    "answer_text": parsed.get("answer_text", raw_answer),
                    "thinking_process": thinking,
                    "confidence": "High",
                    "reason": "Evaluated with exact precision via symbolic arithmetic engine.",
                    "route": "math_code",
                    "is_ambiguous": False,
                    "latency_ms": elapsed_ms,
                    "has_conflict": False
                })

                try:
                    init_query_log(DB_PATH)
                    log_query(question=question, route="math_code", answer=parsed.get("answer_text", raw_answer),
                              confidence="High", chunk_count=0, has_conflict=False,
                              used_web_fallback=False, latency_ms=elapsed_ms, db_path=DB_PATH)
                except Exception:
                    pass
                return

            # Stage 1: Route
            self._send_sse("stage", {"name": "route"})
            route_info = classify_query_detailed(retrieval_query, DB_PATH)
            route = route_info["route"]
            is_ambiguous = route_info.get("is_ambiguous", False)
            self._send_sse("stage", {"name": "route_done", "route": route, "is_ambiguous": is_ambiguous})

            # Handle nonsense route
            if route == "nonsense":
                raw_answer = "UNKNOWN\n\nConfidence: Low\nReason: Query appears to be nonsensical or unrecognized text.\nSources: None"
                parsed = parse_answer_metadata(raw_answer, potential_conflict=False)
                elapsed_ms = int((time.time() - start_time) * 1000)
                self._send_sse("meta", {
                    "route": route, "is_ambiguous": False, "chunks": [], "has_conflict": False,
                    "confidence": parsed.get("confidence", "Unknown")
                })
                self._send_sse("token", {"token": parsed.get("answer_text", raw_answer)})
                self._send_sse("done", {
                    "answer_text": parsed.get("answer_text", ""),
                    "thinking_process": "",
                    "confidence": parsed.get("confidence", "Unknown"),
                    "reason": parsed.get("reason", ""),
                    "route": route, "is_ambiguous": False, "latency_ms": elapsed_ms, "has_conflict": False
                })
                try:
                    init_query_log(DB_PATH)
                    log_query(question=question, route=route, answer=raw_answer,
                              confidence=parsed.get("confidence", "Unknown"),
                              chunk_count=0, has_conflict=False,
                              used_web_fallback=False, latency_ms=elapsed_ms, db_path=DB_PATH)
                except Exception:
                    pass
                return

            # Stage 2: Context Retrieval
            chunks = []
            embedder = None
            reranker = None

            if route in ("kali_docs", "local_file", "all"):
                self._send_sse("stage", {"name": "retrieve"})
                embedder = get_embedder()
                reranker = get_reranker()

                actual_source = source_filter if (source_filter and source_filter != "all") else (route if route in ("local_file", "kali_docs") else "all")
                chunks = retrieve_top_k(retrieval_query, BASE_DIR, DB_PATH, top_k=top_k_req,
                                        source_type=actual_source,
                                        embedder=embedder, reranker=reranker)
                for c in chunks:
                    if 'tier' not in c:
                        c['tier'] = 1.0

            self._send_sse("stage", {"name": "retrieve_done"})

            # Stage 2b: Route-aware Web Fallback
            used_web_fallback = False
            if route not in ("reasoning_general", "math_code"):
                confidence_info = evaluate_retrieval_confidence(chunks, route=route, question=retrieval_query)
                if confidence_info.get('route_to_web_fallback'):
                    if embedder is None:
                        embedder = get_embedder()
                    fallback_chunks = fetch_web_fallback(retrieval_query, top_k=4, embedder=embedder)
                    if fallback_chunks:
                        relevant_local = [c for c in chunks if c.get('rerank_score', 0) >= 0.60]
                        chunks = relevant_local + fallback_chunks if relevant_local else fallback_chunks
                        used_web_fallback = True

            # Stage 3: Rerank & Score
            self._send_sse("stage", {"name": "rerank"})
            if chunks:
                chunks.sort(key=sort_key)
            self._send_sse("stage", {"name": "rerank_done"})

            # Format chunks for client
            formatted_chunks = []
            for c in chunks:
                tier_val = c.get('tier', 1.0)
                formatted_chunks.append({
                    "file_name": c.get("file_name", "Unknown"),
                    "source_type": c.get("source_type", "local_file"),
                    "tier": tier_val,
                    "tier_label": get_tier_label(tier_val),
                    "chunk_text": c.get("chunk_text", ""),
                    "rerank_score": c.get("rerank_score", 0.0),
                    "distance": c.get("distance", 0.0),
                    "page_number": c.get("page_number", 1)
                })

            potential_conflict_info = detect_potential_conflict(chunks)

            # Send metadata to client
            self._send_sse("meta", {
                "route": route,
                "is_ambiguous": is_ambiguous,
                "chunks": formatted_chunks,
                "has_conflict": False,
                "confidence": "High" if route in ("reasoning_general", "math_code") else "Medium"
            })

            # Stage 4: Generate (stream tokens + thinking events with multi-turn memory)
            self._send_sse("stage", {"name": "generate"})
            raw_answer = ""
            thinking_trace = ""
            generation_start = time.time()

            try:
                for event_type, chunk_val in generate_answer_streaming(question, chunks, model_name=model_name, route=route, history=history):
                    if event_type == "token":
                        raw_answer += chunk_val
                        self._send_sse("token", {"token": chunk_val})
                    elif event_type == "think":
                        thinking_trace += chunk_val
                        self._send_sse("think", {"token": chunk_val})
            except (BrokenPipeError, ConnectionResetError):
                return

            self._send_sse("stage", {"name": "generate_done"})

            elapsed_ms = int((time.time() - start_time) * 1000)
            parsed = parse_answer_metadata(raw_answer, potential_conflict=potential_conflict_info["has_conflict"])
            actual_has_conflict = parsed.get("has_conflict", False)
            final_thinking = thinking_trace or parsed.get("thinking_process", "")

            self._send_sse("done", {
                "answer_text": parsed.get("answer_text", raw_answer),
                "thinking_process": final_thinking,
                "confidence": parsed.get("confidence", "High"),
                "reason": parsed.get("reason", ""),
                "route": route,
                "is_ambiguous": is_ambiguous,
                "latency_ms": elapsed_ms,
                "has_conflict": actual_has_conflict
            })

            try:
                init_query_log(DB_PATH)
                log_query(
                    question=question, route=route, answer=parsed.get("answer_text", raw_answer),
                    confidence=parsed.get("confidence", "High"),
                    chunk_count=len(chunks),
                    has_conflict=actual_has_conflict,
                    used_web_fallback=used_web_fallback,
                    latency_ms=elapsed_ms, db_path=DB_PATH
                )
            except Exception:
                pass

        except Exception as e:
            try:
                self._send_sse("error", {"message": str(e)})
            except Exception:
                pass


def run_web_server(port: int = 8000):
    server_address = ('127.0.0.1', port)
    httpd = ThreadingHTTPServer(server_address, RAGRequestHandler)
    print(f"")
    print(f"  ⚡ PRAG Linux, Security & Software Research Engine")
    print(f"  ────────────────────────────────────────────────────")
    print(f"  🌐 Web UI:  http://127.0.0.1:{port}")
    print(f"  🛡️ Arsenal: http://127.0.0.1:{port}/api/tools")
    print(f"  📡 API:     http://127.0.0.1:{port}/api/ask")
    print(f"  📊 Stats:   http://127.0.0.1:{port}/api/stats")
    print(f"  ────────────────────────────────────────────────────")
    print(f"  Press Ctrl+C to stop")
    print(f"")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down PRAG server...")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_web_server(port_arg)
