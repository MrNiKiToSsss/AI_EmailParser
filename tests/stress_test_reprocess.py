#!/usr/bin/env python3
"""Stress test: reprocess 100 emails locally and measure performance."""

import json
import os
import time
import sys
from pathlib import Path
from main import analyze_email_local_nn

# Config
DATA_DIR = Path(__file__).parent / "data"
EMAILS_DIR = DATA_DIR / "emails"
RESULTS_DIR = DATA_DIR / "test_results_stress"
NUM_EMAILS = 100

# Ensure test dir exists
RESULTS_DIR.mkdir(exist_ok=True)

dummy_config = {
    "local_nn": {"model": "Davlan/xlm-roberta-base-ner-hrl"},
}

print("="*70)
print(f"STRESS TEST: REPROCESS UP TO {NUM_EMAILS} EMAILS")
print("="*70)

if not EMAILS_DIR.exists():
    print(f"❌ ERROR: {EMAILS_DIR} does not exist")
    sys.exit(1)

eml_files = sorted([f for f in EMAILS_DIR.glob("*.eml")])[:NUM_EMAILS]
print(f"\nFound {len(eml_files)} .eml files to process\n")

if not eml_files:
    print("❌ No .eml files found")
    sys.exit(1)

start_total = time.time()
success_count = 0
error_count = 0
response_times = []

for i, eml_file in enumerate(eml_files, 1):
    try:
        # Read email
        with open(eml_file, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        
        # Extract plain text (simple approach)
        lines = []
        for line in text.split('\n'):
            if line.startswith('Subject:') or line.startswith('From:') or line.startswith('To:'):
                lines.append(line)
            elif not line.startswith('Content-') and not line.startswith('MIME') and line.strip():
                if not line.startswith('--') and '=' not in line[:20]:
                    lines.append(line)
        
        body = '\n'.join(lines[-50:])[:1000]  # Last 50 lines, max 1000 chars
        
        # Analyze
        t0 = time.time()
        result_json = analyze_email_local_nn(body, dummy_config)
        elapsed = time.time() - t0
        response_times.append(elapsed)
        
        # Save result
        result_path = RESULTS_DIR / f"{eml_file.stem}.json"
        with open(result_path, 'w') as f:
            f.write(result_json)
        
        success_count += 1
        if i % 10 == 0:
            print(f"[{i:3d}/{len(eml_files)}] OK Processed in {elapsed:.2f}s")
        
    except Exception as e:
        error_count += 1
        if i % 10 == 0:
            print(f"[{i:3d}/{len(eml_files)}] ERROR: {str(e)[:50]}")

total_time = time.time() - start_total

print("\n" + "="*70)
print("STRESS TEST RESULTS")
print("="*70)
print(f"Total emails processed:  {len(eml_files)}")
print(f"Successful:              {success_count}")
print(f"Errors:                  {error_count}")
print(f"Total time:              {total_time:.2f}s")
print(f"Avg time per email:      {total_time/len(eml_files):.3f}s")
if response_times:
    print(f"Min response time:       {min(response_times):.4f}s")
    print(f"Max response time:       {max(response_times):.4f}s")
    print(f"Throughput:              {len(eml_files)/total_time:.1f} emails/sec")
print("="*70)

print(f"\nResults saved to: {RESULTS_DIR}")
