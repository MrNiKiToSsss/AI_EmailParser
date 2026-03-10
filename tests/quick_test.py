#!/usr/bin/env python3
"""Quick bug detection test"""

import json
import os
import sys
from pathlib import Path

print("=" * 70)
print("QUICK BUG DETECTION TEST")
print("=" * 70)

# Test 1: Model loading
print("\n[Test 1] Testing model loading...")
try:
    from main import analyze_email_local_nn
    test_email = "Привет! Интересует ваш CRM. Иван Петров. Email: ivan@mail.ru, телефон +7-999-123-45-67."
    test_config = {"local_nn": {"model": "Davlan/xlm-roberta-base-ner-hrl"}}
    result_json = analyze_email_local_nn(test_email, test_config)
    result = json.loads(result_json)
    print(f"  OK: Model loaded and working")
    print(f"    - emails: {result.get('emails')}")
    print(f"    - product: {result.get('product')}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Web app
print("\n[Test 2] Testing Flask app...")
try:
    os.environ["RESULTS_DIR"] = "o:/programing/email_parser20/data/results"
    from data.app import app, scan_folder
    files = scan_folder(force=True)
    print(f"  OK: Flask app loaded")
    print(f"    - Scanned {len(files)} sufficient files")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: IMAP client
print("\n[Test 3] Testing IMAP client imports...")
try:
    from scr.imap_client import process_emails, reprocess_local_emails
    print(f"  OK: IMAP client loaded")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
