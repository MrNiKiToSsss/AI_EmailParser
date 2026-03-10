#!/usr/bin/env python3
"""Final verification test"""

print("=" * 70)
print("FINAL VERIFICATION TEST")
print("=" * 70)

# Test 1: Imports
print("\n[Test 1] Checking all imports...")
try:
    from main import load_config, analyze_email_local_nn, _extract_emails, _extract_phones, _heuristic_product
    from scr.imap_client import process_emails, reprocess_local_emails
    import os
    os.environ["RESULTS_DIR"] = "o:/programing/email_parser20/data/results"
    from data.app import app, scan_folder, group_files_by_attribute
    print("  OK: All modules imported successfully")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Test 2: Load config
print("\n[Test 2] Checking config loading...")
try:
    from pathlib import Path
    config = load_config(Path("config.yaml"))
    server = config.get("imap", {}).get("server", "unknown")
    print(f"  OK: Config loaded (IMAP server: {server})")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Test 3: Regex functions
print("\n[Test 3] Checking regex functions...")
try:
    test_text = "Contact: ivan@mail.ru, +7 (999) 123-45-67"
    emails = _extract_emails(test_text)
    phones = _extract_phones(test_text)
    assert len(emails) > 0 and len(phones) > 0
    print(f"  OK: Email and phone extraction working")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Test 4: File scanning
print("\n[Test 4] Checking file scanning...")
try:
    files = scan_folder(force=True)
    assert len(files) > 0
    print(f"  OK: Found {len(files)} sufficient files")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Test 5: Grouping
print("\n[Test 5] Checking grouping...")
try:
    groups = group_files_by_attribute(files)
    assert len(groups) > 0
    print(f"  OK: Created {len(groups)} groups")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

print("\n" + "=" * 70)
print("ALL TESTS PASSED - SYSTEM IS OPERATIONAL")
print("=" * 70)
