"""Workspace Cleanup Utility — Safe Removal of Temporary/Transitive Artifacts.

This script sweeps through the workspace root to remove temporary files and
folders generated during testing and browser subagent executions (e.g. .chrome_user_data_*).
"""

from __future__ import annotations

import os
import shutil
import sys

# Color formatting
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def get_dir_size(path: str) -> int:
    """Calculate total size of a directory in bytes."""
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if link
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
    return total_size

def clean_workspace() -> int:
    print("=" * 70)
    print(f"{BOLD}🧹 GDT INVOICE HUB — WORKSPACE ARTIFACT CLEANUP{RESET}")
    print("=" * 70)
    
    root_dir = "."
    items_removed = 0
    bytes_reclaimed = 0
    errors = 0

    # Targets list: exact names or patterns
    targets = []
    
    # 1. Scan for .chrome_user_data_*
    try:
        for entry in os.listdir(root_dir):
            if entry.startswith(".chrome_user_data_"):
                path = os.path.join(root_dir, entry)
                if os.path.isdir(path):
                    targets.append(path)
    except Exception as e:
        print(f"{RED}Error scanning workspace root: {e}{RESET}")
        return 1

    # 2. Add other temporary cache directories
    standard_caches = [
        ".pytest_cache",
        ".cache",
        ".coverage",
        "pytest_failure.txt",
    ]
    for cache in standard_caches:
        path = os.path.join(root_dir, cache)
        if os.path.exists(path):
            targets.append(path)

    if not targets:
        print(f"{GREEN}✨ No temporary artifacts or user profiles found. Workspace is already clean!{RESET}")
        print("=" * 70)
        return 0

    print(f"Found {len(targets)} targets to remove:")
    for path in targets:
        if os.path.isdir(path):
            size = get_dir_size(path)
            print(f"  📂 {path} ({size / (1024*1024):.2f} MB)")
        else:
            size = os.path.getsize(path)
            print(f"  📄 {path} ({size / 1024:.2f} KB)")

    confirm = True  # Auto-run in execution mode
    
    print("\nStarting deletion process...")
    for path in targets:
        try:
            if os.path.isdir(path):
                size = get_dir_size(path)
                shutil.rmtree(path)
                bytes_reclaimed += size
            else:
                size = os.path.getsize(path)
                os.remove(path)
                bytes_reclaimed += size
            print(f"  {GREEN}✓ Removed{RESET} {path}")
            items_removed += 1
        except Exception as e:
            print(f"  {RED}✗ Failed to remove {path}: {e}{RESET}")
            errors += 1

    print("\n" + "=" * 70)
    print(f"{BOLD}📊 CLEANUP REPORT{RESET}")
    print("=" * 70)
    print(f"  Items Removed:     {items_removed}")
    print(f"  Reclaimed Space:   {bytes_reclaimed / (1024*1024):.2f} MB")
    print(f"  Locked/Skipped:    {errors}")
    print("=" * 70)
    
    # Return 0 to prevent pipeline failures from transient OS locks on Windows
    return 0

if __name__ == "__main__":
    sys.exit(clean_workspace())
