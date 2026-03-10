#!/usr/bin/env python3
"""
Проверка работоспособности и ошибок обновленной системы спам-фильтра
"""

import sys
import os
from pathlib import Path

print("\n" + "=" * 80)
print("ПРОВЕРКА ОБНОВЛЕННОЙ СИСТЕМЫ СПАМ-ФИЛЬТРА")
print("=" * 80)

# Test 1: Check imports
print("\n[1️⃣ ПРОВЕРКА ИМПОРТОВ]")
try:
    from scr.spam_filter import SpamFilter
    from scr.advanced_spam_filter import AdvancedSpamFilter
    from scr.imap_client import process_emails, reprocess_local_emails
    from main import load_config, analyze_email_local_nn
    print("  ✅ Все импорты успешны")
except ImportError as e:
    print(f"  ❌ Ошибка импорта: {e}")
    sys.exit(1)

# Test 2: Check config
print("\n[2️⃣ ПРОВЕРКА КОНФИГУРАЦИИ]")
try:
    config = load_config(Path("config.yaml"))
    
    # Проверка основных параметров
    assert config.get("spam_filters", {}).get("enabled"), "Spam filters disabled!"
    assert config.get("spam_filters", {}).get("ml_filter", {}).get("enabled"), "ML filter disabled!"
    
    print(f"  ✅ Config валиден")
    print(f"    - Spam filters: ENABLED")
    print(f"    - ML filter: ENABLED")
    print(f"    - Model: {config.get('spam_filters', {}).get('ml_filter', {}).get('model')}")
    print(f"    - Risk threshold: {config.get('spam_filters', {}).get('ml_filter', {}).get('risk_threshold')}")
    
except Exception as e:
    print(f"  ❌ Config error: {e}")
    sys.exit(1)

# Test 3: Initialize filters
print("\n[3️⃣ ИНИЦИАЛИЗАЦИЯ ФИЛЬТРОВ]")
try:
    basic_filter = SpamFilter(config)
    print(f"  ✅ Basic filter initialized")
    print(f"    - Subject patterns: {len(basic_filter.subject_blacklist)}")
    print(f"    - Body patterns: {len(basic_filter.body_blacklist)}")
    print(f"    - Sender patterns: {len(basic_filter.sender_blacklist)}")
    print(f"    - Company blacklist: {len(basic_filter.company_blacklist)}")
    
    advanced_filter = AdvancedSpamFilter(config)
    print(f"  ✅ Advanced ML filter initialized")
    print(f"    - Classifier available: {advanced_filter.classifier is not None}")
    print(f"    - Spam patterns: {len(advanced_filter.spam_patterns)}")
    print(f"    - Phishing patterns: {len(advanced_filter.phishing_patterns)}")
    print(f"    - Suspicious patterns: {len(advanced_filter.suspicious_patterns)}")
    
except Exception as e:
    print(f"  ❌ Filter initialization error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test spam detection
print("\n[4️⃣ ТЕСТИРОВАНИЕ ДЕТЕКЦИИ СПАМА]")
test_cases = [
    {
        "name": "Легитимное письмо",
        "subject": "Consultation Request - CRM Implementation",
        "body": "Hello, I am interested in your CRM services for our company. We are looking for a solution to improve our customer management process. Could you provide more information about pricing and implementation timeline? Best regards, John Smith Director of Operations ABC Corporation Tel: +7 (999) 123-45-67 Email: john.smith@abccorp.com",
        "sender": "john@company.com",
        "expected": False
    },
    {
        "name": "Явный спам",
        "subject": "URGENT: WIN $1,000,000!!!",
        "body": "Click here now to claim your prize! Limited offer!",
        "sender": "spam@spam.com",
        "expected": True
    },
    {
        "name": "Фишинг",
        "subject": "Verify Your Account",
        "body": "Your account has been suspended. Click to verify immediately.",
        "sender": "verify@fake.com",
        "expected": True
    }
]

spam_count = 0
legit_count = 0
error_count = 0

for test in test_cases:
    try:
        # Предоставить корректные данные письма
        is_spam, reason = advanced_filter.is_spam(
            email_data={"emails": [test["sender"]], "company": "Test Corp"},
            subject=test["subject"],
            body=test["body"],
            sender=test["sender"]
        )
        
        is_correct = is_spam == test["expected"]
        status = "✅" if is_correct else "⚠️"
        spam_type = "SPAM" if is_spam else "LEGIT"
        expected_type = "SPAM" if test["expected"] else "LEGIT"
        
        print(f"  {status} {test['name']}")
        print(f"     Prediction: {spam_type}, Expected: {expected_type}")
        
        if is_correct:
            if is_spam:
                spam_count += 1
            else:
                legit_count += 1
        else:
            error_count += 1
            
    except Exception as e:
        print(f"  ❌ {test['name']}: {e}")
        error_count += 1

print(f"\n  📊 Результаты: {spam_count+legit_count}/{len(test_cases)} правильно")
if error_count > 0:
    print(f"  ⚠️  Ошибок: {error_count}")

# Test 5: Check risk score calculation
print("\n[5️⃣ ПРОВЕРКА RISK-СКОР]")
try:
    risk_score, reasons = advanced_filter.calculate_risk_score(
        email_data={},
        subject="CLICK HERE!!! WIN MONEY!!!",
        body="Click now for money! Urgent! Act now immediately!",
        sender="spam@spam.com"
    )
    
    print(f"  ✅ Risk score calculation works")
    print(f"    - Score: {risk_score:.1f}/100")
    print(f"    - Risk level: ", end="")
    
    if risk_score >= 80:
        print("🔴 CRITICAL")
    elif risk_score >= 60:
        print("🟠 HIGH")
    elif risk_score >= 40:
        print("🟡 MEDIUM")
    else:
        print("🟢 LOW")
    
    print(f"    - Factors: {len(reasons)} detected")
    for factor in reasons[:3]:
        print(f"      • {factor}")
        
except Exception as e:
    print(f"  ❌ Risk score error: {e}")

# Test 6: Check ML analysis
print("\n[6️⃣ ПРОВЕРКА ML-АНАЛИЗА]")
if advanced_filter.classifier:
    try:
        ml_prob, reasons = advanced_filter.analyze_with_ml(
            "This is a legitimate business inquiry about your products"
        )
        print(f"  ✅ ML analysis works")
        print(f"    - Spam probability: {ml_prob:.1%}")
        print(f"    - Threshold: {advanced_filter.ml_threshold:.0%}")
        print(f"    - Decision: {'SPAM' if ml_prob > 0.5 else 'LEGIT'}")
    except Exception as e:
        print(f"  ❌ ML analysis error: {e}")
else:
    print(f"  ⚠️  ML classifier not loaded (transformers issue?)")

# Test 7: Check file structure
print("\n[7️⃣ ПРОВЕРКА СТРУКТУРЫ ФАЙЛОВ]")
required_files = [
    "scr/spam_filter.py",
    "scr/advanced_spam_filter.py",
    "scr/imap_client.py",
    "config.yaml",
    "test_advanced_spam_ml.py"
]

all_exists = True
for file in required_files:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"  {status} {file}")
    if not exists:
        all_exists = False

# Test 8: Summary
print("\n" + "=" * 80)
print("ИТОГОВЫЙ ОТЧЕТ")
print("=" * 80)

if error_count == 0 and all_exists and advanced_filter.classifier:
    print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!\n")
    print("Система готова к использованию:")
    print("  1. Запустить обновление спам-фильтра:")
    print("     python main.py reprocess --engine combined")
    print("  2. Проверить логи:")
    print("     tail -f logs/app.log | grep SPAM")
    print("  3. Просмотреть подозрительные письма:")
    print("     ls data/review/")
    sys.exit(0)
else:
    print("\n⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ:\n")
    if error_count > 0:
        print(f"  • Ошибки в тестах спам-детекции: {error_count}")
    if not all_exists:
        print(f"  • Отсутствуют файлы: {len([f for f in required_files if not os.path.exists(f)])}")
    if not advanced_filter.classifier:
        print(f"  • ML-классификатор не загрузился")
        print(f"    Решение: pip install transformers torch")
    print("\nОднако система может работать в режиме базовых фильтров.")
    sys.exit(1)
