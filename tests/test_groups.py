#!/usr/bin/env python3
"""Проверка структуры групп в API"""

import requests
import json

try:
    r = requests.get('http://localhost:5555/files')
    data = r.json()
    
    print("=" * 70)
    print("ПРОВЕРКА СТРУКТУРЫ ГРУПП")
    print("=" * 70)
    
    if not data:
        print("Нет данных!")
    else:
        print(f"Всего групп: {len(data)}")
        print()
        
        for i, group in enumerate(data[:3], 1):
            print(f"Группа {i}:")
            print(f"  ├─ Имя: {group.get('group_name')}")
            print(f"  ├─ Тип: {group.get('group_type')}")
            print(f"  └─ Писем: {len(group.get('files', []))}")
            
            if group.get('files'):
                print(f"     └─ Первое письмо: {group['files'][0].get('filename')}")
            print()
        
        print(f"... и ещё {max(0, len(data)-3)} групп")
        
        # Проверить статистику
        total_files = sum(len(g.get('files', [])) for g in data)
        print()
        print("=" * 70)
        print(f"СТАТИСТИКА: {len(data)} групп, {total_files} писем")
        print("=" * 70)

except Exception as e:
    print(f"Ошибка: {e}")
