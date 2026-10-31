#!/usr/bin/env python3
"""
Resource Profiling & Measurement Module for Local PRAG System.
Captures system RAM, process RSS (Ollama & Python), and CPU utilization.
"""

import os
import sys
import psutil

def get_ollama_pid() -> int | None:
    """Finds the process ID of running Ollama daemon."""
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if 'ollama' in p.info['name'].lower():
                return p.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def snapshot(label: str) -> dict:
    """Captures and logs current resource metrics."""
    ollama_pid = get_ollama_pid()
    ollama_mem = 0.0
    if ollama_pid:
        try:
            ollama_proc = psutil.Process(ollama_pid)
            ollama_mem = ollama_proc.memory_info().rss / (1024 * 1024)
        except Exception:
            pass

    current_proc = psutil.Process(os.getpid())
    py_mem = current_proc.memory_info().rss / (1024 * 1024)

    total_mem = psutil.virtual_memory()
    sys_used_gb = total_mem.used / (1024 ** 3)
    sys_total_gb = total_mem.total / (1024 ** 3)
    cpu_pct = psutil.cpu_percent(interval=0.1)

    metrics = {
        "label": label,
        "ollama_rss_mb": ollama_mem,
        "python_rss_mb": py_mem,
        "sys_mem_pct": total_mem.percent,
        "sys_used_gb": sys_used_gb,
        "sys_total_gb": sys_total_gb,
        "cpu_pct": cpu_pct
    }

    print(f"[PROFILE] --- {label} ---")
    print(f"[PROFILE] Ollama RSS:   {ollama_mem:.1f} MB")
    print(f"[PROFILE] Python RSS:   {py_mem:.1f} MB")
    print(f"[PROFILE] System RAM:   {total_mem.percent}% ({sys_used_gb:.2f} / {sys_total_gb:.2f} GB)")
    print(f"[PROFILE] CPU Usage:    {cpu_pct}%\n")

    return metrics

if __name__ == "__main__":
    snapshot("Baseline Idle Measurement")
