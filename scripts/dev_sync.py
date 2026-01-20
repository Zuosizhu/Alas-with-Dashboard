import shutil
import filecmp
import os
import sys
from pathlib import Path

# Paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = PROJECT_ROOT / "upstream_alas"
BASELINE_DIR = PROJECT_ROOT / "alas_baseline"
WRAPPED_DIR = PROJECT_ROOT / "alas_wrapped"

def log(msg):
    print(f"[SYNC] {msg}")

def error(msg):
    print(f"[ERROR] {msg}")
    sys.exit(1)

def ensure_upstream_exists():
    if not UPSTREAM_DIR.exists():
        error(f"Upstream directory not found at {UPSTREAM_DIR}. Please initialize the submodule.")
    if not (UPSTREAM_DIR / "alas.py").exists():
        error(f"Upstream directory seems empty or invalid. alas.py missing.")

def sync_baseline():
    """
    Wipes alas_baseline and re-copies from upstream_alas.
    """
    log("Syncing Baseline...")
    
    # 1. Validation
    ensure_upstream_exists()

    # 2. Clean Baseline
    if BASELINE_DIR.exists():
        log(f"Cleaning existing baseline at {BASELINE_DIR}...")
        # Use simple rmtree. In a git repo, this is safe as long as we don't delete .git folder
        # But alas_baseline is just a folder in our repo, so we can wipe it.
        # We might want to preserve .gitignore if it's specific, but plan says baseline is a copy.
        shutil.rmtree(BASELINE_DIR)
    
    # 3. Copy Upstream -> Baseline
    log(f"Copying {UPSTREAM_DIR} -> {BASELINE_DIR}...")
    
    # We ignore .git folder from the submodule if it exists
    shutil.copytree(UPSTREAM_DIR, BASELINE_DIR, ignore=shutil.ignore_patterns('.git', '.github'))
    
    # 4. Apply Patches (Placeholder)
    # logic to modify requirements.txt or config could go here
    log("Baseline synced successfully.")

def check_wrapped_drift():
    """
    Compares Baseline vs Wrapped to show what has changed.
    """
    log("Checking Wrapped drift...")
    
    if not WRAPPED_DIR.exists():
        log("alas_wrapped does not exist. Suggesting initial copy.")
        return

    # Compare directories
    # This is a shallow comparison for performance, or we can do deep.
    # dircmp is recursive.
    
    comparison = filecmp.dircmp(BASELINE_DIR, WRAPPED_DIR)
    
    def print_diff(dcmp):
        if dcmp.diff_files:
            print(f"Modified in Wrapped ({dcmp.left} vs {dcmp.right}):")
            for name in dcmp.diff_files:
                print(f"  - {name}")
        if dcmp.left_only:
            print(f"Missing in Wrapped (New in Upstream?):")
            for name in dcmp.left_only:
                print(f"  - {name}")
        if dcmp.right_only:
            print(f"Custom files in Wrapped:")
            for name in dcmp.right_only:
                print(f"  + {name}")
        
        # Recursion
        for sub_dir in dcmp.subdirs.values():
            print_diff(sub_dir)

    print("--- Drift Report ---")
    print_diff(comparison)
    print("--------------------")

def initialize_wrapped():
    """
    Copies Baseline -> Wrapped if Wrapped doesn't exist.
    """
    if WRAPPED_DIR.exists():
        log("alas_wrapped already exists. Skipping initialization.")
        return

    log(f"Initializing alas_wrapped from {BASELINE_DIR}...")
    shutil.copytree(BASELINE_DIR, WRAPPED_DIR)
    log("alas_wrapped initialized.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ALAS Monorepo Sync Tool")
    parser.add_argument("--sync-baseline", action="store_true", help="Reset baseline from upstream")
    parser.add_argument("--check", action="store_true", help="Check drift between baseline and wrapped")
    parser.add_argument("--init-wrapped", action="store_true", help="Initialize wrapped from baseline if missing")
    parser.add_argument("--all", action="store_true", help="Run sync-baseline, then init-wrapped, then check")

    args = parser.parse_args()

    if args.all:
        sync_baseline()
        initialize_wrapped()
        check_wrapped_drift()
    elif args.sync_baseline:
        sync_baseline()
    elif args.init_wrapped:
        initialize_wrapped()
    elif args.check:
        check_wrapped_drift()
    else:
        parser.print_help()
