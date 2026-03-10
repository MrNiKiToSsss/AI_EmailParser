#!/usr/bin/env python3
"""Comprehensive bug detection and testing script"""

import json
import os
import sys
from pathlib import Path

print("=" * 70)
print("COMPREHENSIVE BUG DETECTION TEST")
print("=" * 70)

# Test 1: Import all modules
print("\n[Test 1] Testing imports...")
try:
    from main import (
        load_config,
        _validate_config_for_parser,
        analyze_email_local_nn,
        _extract_emails,
        _extract_phones,
        _heuristic_product,
    )
    print("  OK: main.py imports successful")
except Exception as e:
    print(f"  ERROR in main.py imports: {e}")
    sys.exit(1)

try:
    from scr.imap_client import process_emails, reprocess_local_emails
    print("  OK: imap_client.py imports successful")
except Exception as e:
    print(f"  ERROR in imap_client.py imports: {e}")
    sys.exit(1)

try:
    os.environ["RESULTS_DIR"] = "o:/programing/email_parser20/data/results"
    from data.app import (
        app,
        get_file_info,
        is_sufficient,
        group_files_by_attribute,
        scan_folder,
    )
    print("  OK: app.py imports successful")
except Exception as e:
    print(f"  ERROR in app.py imports: {e}")
    sys.exit(1)

# Test 2: Config loading
print("\n[Test 2] Testing config loading...")
try:
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(config_path)
    print(f"  OK: Config loaded")
    print(f"    - IMAP server: {config['imap'].get('server')}")
    print(f"    - Storage emails_dir: {config['storage'].get('emails_dir')}")
    print(f"    - Storage results_dir: {config['storage'].get('results_dir')}")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Test 3: Extract emails/phones
print("\n[Test 3] Testing regex extraction...")
test_text = "Контактные данные: ivan.ivanov@mail.ru, +7 (999) 123-45-67, director@company.com"
emails = _extract_emails(test_text)
phones = _extract_phones(test_text)
print(f"  Text: {test_text}")
print(f"  Emails found: {emails}")
print(f"  Phones found: {phones}")
if len(emails) >= 2 and len(phones) >= 1:
    print("  OK: Regex extraction working")
else:
    print(f"  WARNING: Expected at least 2 emails and 1 phone, got {len(emails)} emails and {len(phones)} phones")

# Test 4: Heuristic product extraction
print("\n[Test 4] Testing heuristic product extraction...")
product_text = "Интересует CRM система с интеграцией. Нужен мобильное приложение."
product = _heuristic_product(product_text)
print(f"  Text: {product_text}")
print(f"  Product found: {product}")
if product:
    print("  OK: Heuristic extraction working")
else:
    print("  WARNING: No product found")

# Test 5: JSON file validation
print("\n[Test 5] Validating JSON result files...")
results_dir = config["storage"]["results_dir"]
if not os.path.exists(results_dir):
    print(f"  WARNING: Results directory does not exist: {results_dir}")
else:
    json_files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
    print(f"  Found {len(json_files)} JSON files")
    
    errors = []
    for i, filename in enumerate(json_files[:10]):  # Check first 10
        filepath = os.path.join(results_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Validation
            required_keys = ["full_name", "emails", "phones", "company", "position", "product"]
            missing = [k for k in required_keys if k not in data]
            if missing:
                errors.append(f"{filename}: Missing keys {missing}")
            
            if not isinstance(data.get("emails"), list):
                errors.append(f"{filename}: 'emails' is not a list (got {type(data.get('emails')).__name__})")
            if not isinstance(data.get("phones"), list):
                errors.append(f"{filename}: 'phones' is not a list (got {type(data.get('phones')).__name__})")
        
        except json.JSONDecodeError as e:
            errors.append(f"{filename}: Invalid JSON - {str(e)}")
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")
    
    if errors:
        print(f"  ERRORS found in JSON files:")
        for err in errors:
            print(f"    - {err}")
    else:
        print("  OK: All checked JSON files are valid")

# Test 6: File info parsing
print("\n[Test 6] Testing file info parsing...")
if os.path.exists(results_dir) and json_files:
    test_file = os.path.join(results_dir, json_files[0])
    try:
        file_info = get_file_info(test_file)
        print(f"  File: {json_files[0]}")
        print(f"    - full_name: {file_info.get('full_name')}")
        print(f"    - company: {file_info.get('company')}")
        print(f"    - emails: {file_info.get('emails')}")
        print(f"    - phones: {file_info.get('phones')}")
        print("  OK: File info parsing working")
    except Exception as e:
        print(f"  ERROR: {e}")

# Test 7: Folder scanning
print("\n[Test 7] Testing folder scanning...")
try:
    files = scan_folder(force=True)
    print(f"  Scanned {len(files)} sufficient files")
    if len(files) > 0:
        print(f"  Sample file: {files[0].get('company')} - {files[0].get('full_name')}")
        print("  OK: Folder scanning working")
    else:
        print("  WARNING: No sufficient files found")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 8: Grouping
print("\n[Test 8] Testing file grouping...")
try:
    files = scan_folder(force=True)
    groups = group_files_by_attribute(files)
    print(f"  Total groups: {len(groups)}")
    if len(groups) > 0:
        print(f"  Sample group: {groups[0].get('group_name')} ({len(groups[0].get('files'))} files)")
        print("  OK: Grouping working")
    else:
        print("  WARNING: No groups created")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 9: analyze_email_local_nn
print("\n[Test 9] Testing analyze_email_local_nn...")
try:
    test_email = "Привет! Интересует ваш CRM. Иван Петров. Email: ivan@mail.ru, телефон +7-999-123-45-67. Компания ООО Рога и копыта."
    test_config = {"local_nn": {"model": "Davlan/xlm-roberta-base-ner-hrl"}}
    result_json = analyze_email_local_nn(test_email, test_config)
    result = json.loads(result_json)
    print(f"  Result keys: {list(result.keys())}")
    print(f"    - full_name: {result.get('full_name')}")
    print(f"    - company: {result.get('company')}")
    print(f"    - emails: {result.get('emails')}")
    print(f"    - product: {result.get('product')}")
    print("  OK: analyze_email_local_nn working")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 70)
print("TESTING COMPLETE")
print("=" * 70)
