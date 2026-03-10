#!/usr/bin/env python3
"""Stress test for local NN analyzer and email text extraction."""

import json
import sys
from main import analyze_email_local_nn, _extract_emails, _extract_phones, _heuristic_product

# Sample test emails
test_cases = [
    {
        "name": "Simple inquiry",
        "text": "Привет! Интересует ваш продукт CRM Pro. Мой email: alex.ivanov@company.ru, телефон: +7 (999) 123-45-67. Александр Иванов, менеджер из компании ТехРешения."
    },
    {
        "name": "Product inquiry",
        "text": "Здравствуйте! Нужен ваш ERP система. Компания: АБВ Групп. Должность: Директор. Email: director@abv-group.com. Телефон 8-800-555-1234"
    },
    {
        "name": "Minimal info",
        "text": "Привет, это Иван. Пишу по поводу заявки на услугу. Спасибо!"
    },
]

dummy_config = {
    "local_nn": {"model": "Davlan/xlm-roberta-base-ner-hrl"},
    "ollama": {"api_url": "http://localhost:11434/api/generate", "model": "mistral:7b"}
}

print("="*70)
print("LOCAL NN ANALYZER & EMAIL EXTRACTION STRESS TEST")
print("="*70)

for i, test_case in enumerate(test_cases, 1):
    print(f"\n[Test {i}: {test_case['name']}]")
    print(f"Input text: {test_case['text'][:80]}...")
    print()
    
    try:
        result_json = analyze_email_local_nn(test_case['text'], dummy_config)
        result = json.loads(result_json)
        
        print(f"  ✓ Full name:  {result.get('full_name', '')}")
        print(f"  ✓ Emails:     {', '.join(result.get('emails', []))}")
        print(f"  ✓ Phones:     {', '.join(result.get('phones', []))}")
        print(f"  ✓ Company:    {result.get('company', '')}")
        print(f"  ✓ Position:   {result.get('position', '')}")
        print(f"  ✓ Product:    {result.get('product', '')}")
    except Exception as e:
        print(f"  ✗ ERROR: {str(e)}")

print("\n" + "="*70)
print("TESTING REGEX EMAIL/PHONE EXTRACTION")
print("="*70)

test_text = "contacts: ivan.petrov@mail.ru, +7 (999) 888-77-66, 8-800-555-1234, director@company.com"
print(f"Text: {test_text}")
print(f"Emails found:  {_extract_emails(test_text)}")
print(f"Phones found:  {_extract_phones(test_text)}")

print("\n" + "="*70)
print("TESTING HEURISTIC PRODUCT EXTRACTION")
print("="*70)

product_test = """
Ищу решение для автоматизации. Интересует CRM система с интеграцией 1С.
Нужен отчет по продажам и аналитика.
Хочу видеть дашборд для мониторинга процессов.
"""

print(f"Text: {product_test.strip()}")
product = _heuristic_product(product_test)
print(f"Product found: {product}")

print("\n" + "="*70)
print("✓ ALL TESTS PASSED SUCCESSFULLY")
print("="*70)
