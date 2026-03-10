#!/usr/bin/env python3
"""Test web export endpoint."""

import requests
import time

print("="*70)
print("TESTING WEB EXPORT ENDPOINT")
print("="*70)

try:
    start = time.time()
    r = requests.get('http://localhost:5555/export?q=tech', timeout=30)
    elapsed = time.time() - start
    
    print(f"\nExport request completed in {elapsed:.2f}s")
    print(f"HTTP Status:    {r.status_code}")
    print(f"Response size:  {len(r.content)} bytes")
    content_type = r.headers.get("Content-Type", "unknown")
    print(f"Content-Type:   {content_type}")
    
    if r.status_code == 200 and "spreadsheet" in content_type.lower():
        print("\nSUCCESS: Excel file generated successfully")
    else:
        print(f"\nERROR: Unexpected response")
        
except Exception as e:
    print(f"ERROR: {e}")

print("="*70)
