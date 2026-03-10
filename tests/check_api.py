#!/usr/bin/env python3
import requests
import json

r = requests.get('http://localhost:5555/files')
print(f"Status: {r.status_code}")
print(f"\nFirst group:")
data = r.json()
if data:
    group = data[0]
    print(f"  Name: {group.get('group_name')}")
    print(f"  Type: {group.get('group_type')}")
    print(f"  Files: {len(group.get('files', []))}")
    if group.get('files'):
        print(f"  First file: {group['files'][0]['filename']}")
else:
    print("No groups")
