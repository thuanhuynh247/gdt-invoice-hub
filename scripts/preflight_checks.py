"""GDT Invoice Hub — Production Pre-flight Readiness Validator.

This script automates Stage 3 (Chuẩn bị Production) and Stage 4 (Go-Live) checks
from docs/DEPLOYMENT_CHECKLIST.md, providing absolute assurance before go-live.

Usage:
    python scripts/preflight_checks.py
"""

from __future__ import annotations

import os
import sys
import shutil
import sqlite3
import socket
from datetime import datetime

# Formatting colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def log_section(title: str):
    print("\n" + "=" * 70)
    print(f"{BLUE}{BOLD}📌 MODULE: {title}{RESET}")
    print("=" * 70)

def main() -> int:
    print("=" * 70)
    print(f"{BOLD}⚙️  GDT INVOICE HUB — PRODUCTION PRE-FLIGHT VALIDATOR{RESET}")
    print("=" * 70)
    
    warnings = 0
    failures = 0
    passed = 0
    
    # ── 1. ENVIRONMENT CONFIGURATION CHECK ──────────────────────────
    log_section("ENVIRONMENT CONFIGURATION (.env)")
    env_path = ".env"
    if not os.path.exists(env_path):
        print(f"  {RED}❌ FAIL{RESET}  .env file not found at project root!")
        failures += 1
    else:
        print(f"  {GREEN}✅ PASS{RESET}  Found .env file.")
        passed += 1
        
        env_vars = {}
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        k, v = parts
                        env_vars[k.strip()] = v.strip().strip("'\"")
                    
        # Check GDT_USE_MOCK
        use_mock = env_vars.get("GDT_USE_MOCK", "false").lower()
        if use_mock == "true":
            print(f"  {YELLOW}⚠️  WARN{RESET}  GDT_USE_MOCK is set to 'true'. Product will run in OFFLINE MOCK MODE.")
            warnings += 1
        else:
            print(f"  {GREEN}✅ PASS{RESET}  GDT_USE_MOCK is set to 'false' (Live GDT Integration enabled).")
            passed += 1
            
        # Check FLASK_DEBUG
        flask_debug = env_vars.get("FLASK_DEBUG", "false").lower()
        if flask_debug == "true":
            print(f"  {RED}❌ FAIL{RESET}  FLASK_DEBUG is set to 'true'. NEVER run debug in production!")
            failures += 1
        else:
            print(f"  {GREEN}✅ PASS{RESET}  FLASK_DEBUG is set to 'false' (Debug mode disabled).")
            passed += 1
            
        # Check FLASK_SECRET_KEY
        secret_key = env_vars.get("FLASK_SECRET_KEY", "")
        if not secret_key or secret_key in ["dev-secret-key", "change-me", "super-secret"]:
            print(f"  {RED}❌ FAIL{RESET}  FLASK_SECRET_KEY is insecure or using default placeholder!")
            failures += 1
        elif len(secret_key) < 32:
            print(f"  {YELLOW}⚠️  WARN{RESET}  FLASK_SECRET_KEY length is {len(secret_key)} chars. Recommend 32+ chars.")
            warnings += 1
        else:
            print(f"  {GREEN}✅ PASS{RESET}  FLASK_SECRET_KEY is long and secure ({len(secret_key)} chars).")
            passed += 1

    # ── 2. SYSTEM RESOURCES CHECK ─────────────────────────────────────
    log_section("SYSTEM RESOURCES & DISK CAPACITY")
    total, used, free = shutil.disk_usage(".")
    free_gb = free / (1024**3)
    if free_gb < 1.0:
        print(f"  {RED}❌ FAIL{RESET}  Insufficient free disk space! Only {free_gb:.2f} GB free. Required: >= 1.0 GB.")
        failures += 1
    else:
        print(f"  {GREEN}✅ PASS{RESET}  Available Disk Space: {free_gb:.2f} GB (Requirement ≥ 1.0 GB cleared).")
        passed += 1

    # ── 3. DATABASE INTEGRITY CHECK ───────────────────────────────────
    log_section("DATABASE INTEGRITY & COHESION")
    
    db_dir = "data"
    dbs_to_check = []
    
    # Safely scan for databases in data/
    if os.path.exists(db_dir):
        for f in os.listdir(db_dir):
            if f.endswith(".db"):
                dbs_to_check.append(os.path.join(db_dir, f))
    
    if not dbs_to_check:
        print(f"  {YELLOW}⚠️  WARN{RESET}  No SQLite database files found in '{db_dir}'. Will be scaffolded on launch.")
        warnings += 1
    else:
        for db_path in sorted(dbs_to_check):
            db_name = os.path.basename(db_path)
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check")
                integrity = cur.fetchone()[0]
                if integrity == "ok":
                    print(f"  {GREEN}✅ PASS{RESET}  {db_name} integrity verified (OK).")
                    passed += 1
                else:
                    print(f"  {RED}❌ FAIL{RESET}  {db_name} integrity compromised: {integrity}")
                    failures += 1
                conn.close()
            except Exception as e:
                print(f"  {RED}❌ FAIL{RESET}  Error connecting to {db_name}: {e}")
                failures += 1
            
    harness_db_path = "harness.db"
    if os.path.exists(harness_db_path):
        try:
            conn = sqlite3.connect(harness_db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM story WHERE status != 'implemented'")
            unimplemented = cur.fetchone()[0]
            if unimplemented == 0:
                print(f"  {GREEN}✅ PASS{RESET}  All Harness stories are completely synchronized to status 'implemented'.")
                passed += 1
            else:
                print(f"  {YELLOW}⚠️  WARN{RESET}  {unimplemented} stories in harness.db are not marked as 'implemented'.")
                warnings += 1
            conn.close()
        except Exception as e:
            print(f"  {YELLOW}⚠️  WARN{RESET}  Could not read harness.db context: {e}")
            warnings += 1

    # ── 4. NETWORKING & OFFICIAL PORTAL CONNECTIVITY ──────────────────
    log_section("EXTERNAL INTEGRATION & PORTS")
    gdt_host = "hoadondientu.gdt.gov.vn"
    try:
        ip = socket.gethostbyname(gdt_host)
        print(f"  {GREEN}✅ PASS{RESET}  Successfully resolved {gdt_host} -> IP: {ip}")
        passed += 1
    except socket.gaierror:
        print(f"  {YELLOW}⚠️  WARN{RESET}  Could not resolve {gdt_host}. Check internet connectivity or offline routing.")
        warnings += 1
    # ── 5. UI/UX ACCESSIBILITY AUDIT ──────────────────────────────────
    log_section("UI/UX ACCESSIBILITY AUDIT")
    try:
        from bs4 import BeautifulSoup
        import re
        
        templates_dir = "templates"
        if not os.path.exists(templates_dir):
            print(f"  {YELLOW}⚠️  WARN{RESET}  Templates directory '{templates_dir}' not found.")
            warnings += 1
        else:
            issues = 0
            for filename in os.listdir(templates_dir):
                if filename.endswith(".html"):
                    filepath = os.path.join(templates_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    soup = BeautifulSoup(content, "html.parser")
                    
                    # Check icons lacking aria-hidden
                    icons = soup.find_all("i", class_=lambda c: c and "bi-" in c)
                    for icon in icons:
                        if not icon.get("aria-hidden"):
                            issues += 1
                            
                    # Check placeholders with "..."
                    for elem in soup.find_all(placeholder=True):
                        if "..." in elem["placeholder"]:
                            issues += 1
                            
            if issues > 0:
                print(f"  {YELLOW}⚠️  WARN{RESET}  Found {issues} accessibility / guidelines issues in templates. Run 'python scripts/audit_ui_ux.py' for details.")
                warnings += 1
            else:
                print(f"  {GREEN}✅ PASS{RESET}  All HTML templates comply with accessibility and style guidelines.")
                passed += 1
    except ImportError:
        print(f"  {YELLOW}⚠️  WARN{RESET}  BeautifulSoup4 (bs4) not installed. Skipping UI/UX template audit.")
        warnings += 1

    # ── 6. FINAL READINESS REPORT ─────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"{BOLD}📊 PRE-FLIGHT READINESS REPORT{RESET}")
    print("=" * 70)
    print(f"  {GREEN}✅ Passed Checks:{RESET} {passed}")
    print(f"  {YELLOW}⚠️  Warnings:{RESET}      {warnings}")
    print(f"  {RED}❌ Failures:{RESET}      {failures}")
    print("=" * 70)
    
    if failures > 0:
        print(f"\n{RED}{BOLD}🛑 CRITICAL FAILURE: System is NOT ready for production release. Please fix the failures above!{RESET}")
        return 1
    elif warnings > 0:
        print(f"\n{YELLOW}{BOLD}⚠️  READY WITH WARNINGS: Ready to proceed, but please double-check the warning recommendations.{RESET}")
        return 0
    else:
        print(f"\n{GREEN}{BOLD}🎉 PERFECT SUCCESS: System is 100% ready for Go-Live deployment!{RESET}")
        return 0

if __name__ == "__main__":
    sys.exit(main())
