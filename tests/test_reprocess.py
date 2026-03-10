#!/usr/bin/env python3
"""Test reprocess function"""

import os
import sys
from pathlib import Path
from main import load_config, analyze_email_local_nn, reprocess_local_emails, _setup_logging

# Enable logging first
_setup_logging()

print("\n" + "=" * 70, flush=True)
print("TESTING REPROCESS FUNCTION", flush=True)
print("=" * 70, flush=True)

# Load config
config_path = Path("config.yaml")
config = load_config(config_path)

print(f"\nConfig loaded:", flush=True)
print(f"  - emails_dir: {config['storage']['emails_dir']}", flush=True)
print(f"  - results_dir: {config['storage']['results_dir']}", flush=True)

# Check if emails directory exists
emails_dir = config["storage"]["emails_dir"]
if os.path.isdir(emails_dir):
    eml_files = [f for f in os.listdir(emails_dir) if f.endswith(".eml")]
    print(f"\nFound {len(eml_files)} .eml files in {emails_dir}", flush=True)
    if eml_files:
        print(f"  First 5 files: {eml_files[:5]}", flush=True)
else:
    print(f"\nERROR: emails_dir does not exist: {emails_dir}", flush=True)
    sys.exit(1)

print(f"\nStarting reprocess_local_emails()...", flush=True)
print("-" * 70, flush=True)

try:
    print("Calling reprocess_local_emails()...", flush=True)
    sys.stdout.flush()
    reprocess_local_emails(config, analyze_email_local_nn, only_missing=False)
    print("-" * 70, flush=True)
    print("\n✓ Reprocess completed successfully", flush=True)
except Exception as e:
    print("-" * 70, flush=True)
    print(f"\n✗ Reprocess failed with error:", flush=True)
    print(f"  {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Check results
    results_dir = config["storage"]["results_dir"]
    if os.path.isdir(results_dir):
        json_files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
        print(f"\nFound {len(json_files)} .json files in results_dir", flush=True)

print("\n" + "=" * 70, flush=True)
print("TEST COMPLETE", flush=True)
print("=" * 70, flush=True)
sys.exit(0)
