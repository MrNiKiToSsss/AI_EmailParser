#!/usr/bin/env python3
"""
Тест полной интеграции спам-фильтра в основную программу.
Проверяет, что система автоматически фильтрует спам при обработке.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from scr.imap_client import reprocess_local_emails
from scr.spam_filter import SpamFilter


def create_test_eml(uid: str, subject: str, from_addr: str, body: str) -> str:
    """Создаёт простой .eml файл для тестирования."""
    eml_content = f"""From: {from_addr}
To: test@example.com
Subject: {subject}
Date: Mon, 17 Feb 2026 10:00:00 +0000
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

{body}
"""
    return eml_content


def test_spam_integration():
    """Тест: интеграция спам-фильтра в обработку писем."""
    
    print("\n" + "="*70)
    print("ТЕСТ ИНТЕГРАЦИИ СПАМ-ФИЛЬТРА В ОСНОВНУЮ ПРОГРАММУ")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        emails_dir = os.path.join(tmp_dir, "emails")
        results_dir = os.path.join(tmp_dir, "results")
        review_dir = os.path.join(tmp_dir, "review")
        
        os.makedirs(emails_dir)
        os.makedirs(results_dir)
        
        # Создаём тестовую конфигурацию
        config = {
            "storage": {
                "emails_dir": emails_dir,
                "results_dir": results_dir,
                "processed_db": os.path.join(tmp_dir, "processed.json")
            },
            "spam_filters": {
                "enabled": True,
                "subject_blacklist": ["viagra", "casino", "lottery"],
                "body_blacklist": ["click here", "limited offer"],
                "sender_blacklist": ["*@spam.com", "*noreply*"],
                "min_company_length": 2,
                "min_email_count": 0,
                "min_contact_info": 0,
                "exclude_replies": False,
                "exclude_forwards": False,
                "max_email_size_mb": -1,
                "min_email_size_kb": 0,
                "company_blacklist": ["Google", "Яндекс"],
                "company_whitelist": [],
                "require_review_before_delete": True,
                "review_folder": review_dir
            }
        }
        
        # Создаём тестовые письма
        test_cases = [
            {
                "uid": "1",
                "name": "Legit email from TechCorp",
                "subject": "Partnership Opportunity",
                "from": "john@techcorp.com",
                "body": "Hi, we would like to discuss partnership opportunities.",
                "should_be_spam": False
            },
            {
                "uid": "2",
                "name": "Spam with viagra in subject",
                "subject": "VIAGRA for sale!!!",
                "from": "spam@example.com",
                "body": "Click here for best prices",
                "should_be_spam": True
            },
            {
                "uid": "3",
                "name": "Spam from noreply sender",
                "subject": "Promotional offer",
                "from": "noreply@marketing.com",
                "body": "Join our program now!",
                "should_be_spam": True
            },
            {
                "uid": "4",
                "name": "Spam with limited offer in body",
                "subject": "Special offer",
                "from": "sales@promotional.com",
                "body": "This is a limited offer - click here to learn more",
                "should_be_spam": True
            },
            {
                "uid": "5",
                "name": "Legit work email",
                "subject": "Meeting schedule",
                "from": "manager@company.com",
                "body": "Please review the attached agenda for tomorrow's meeting",
                "should_be_spam": False
            }
        ]
        
        # Сохраняем тестовые письма
        for test_case in test_cases:
            eml_content = create_test_eml(
                test_case["uid"],
                test_case["subject"],
                test_case["from"],
                test_case["body"]
            )
            eml_path = os.path.join(emails_dir, f"{test_case['uid']}.eml")
            with open(eml_path, 'w', encoding='utf-8') as f:
                f.write(eml_content)
        
        # Запускаем обработку с фильтром спама
        print(f"\n📧 Тестовых писем создано: {len(test_cases)}")
        print(f"📁 Папка emails: {emails_dir}")
        print(f"📁 Папка results: {results_dir}")
        print(f"📁 Папка review: {review_dir}")
        
        # Простой callback для тестирования
        # ВАЖНО: Нужна функция с сигнатурой (text, config) -> json_string
        def test_callback(text, config):
            return json.dumps({"text": text[:100], "processed": True})
        
        # Запускаем переобработку с фильтром спама
        print(f"\n🔍 Запускаем фильтрацию спама...")
        spam_filter = reprocess_local_emails(config, test_callback, only_missing=False)
        
        # Проверяем результаты
        print(f"\n📊 РЕЗУЛЬТАТЫ ФИЛЬТРАЦИИ:")
        print(f"{"─"*70}")
        
        rejection_summary = spam_filter.get_rejected_summary()
        total_rejected = rejection_summary["total_rejected"]
        
        print(f"✅ Всего выполнено писем: {len(test_cases)}")
        print(f"⚠️  Отклонено как спам: {total_rejected}")
        print(f"✓ Обработано легитимных: {len(test_cases) - total_rejected}")
        
        # Проверяем какие письма были отклонены
        print(f"\n📋 ДЕТАЛИ ОТКЛОНЕНИЙ:")
        for rejection in rejection_summary["rejections"]:
            print(f"  ❌ [{rejection['uid']}] {rejection['reason']}")
        
        # Проверяем файлы результатов
        result_files = os.listdir(results_dir)
        print(f"\n✅ ОБРАБОТАННЫЕ ПИСЬМА ({len(result_files)}):")
        for result_file in sorted(result_files):
            print(f"  ✓ {result_file}")
        
        # Проверяем папку review
        if os.path.exists(review_dir):
            review_files = os.listdir(review_dir)
            print(f"\n🔍 ПИСЬМА ДЛЯ ПРОВЕРКИ ({len(review_files)}):")
            for review_file in sorted(review_files):
                review_path = os.path.join(review_dir, review_file)
                with open(review_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"  📄 {review_file}")
                print(f"     └─ {data['reason']}")
        
        # Проверяем статистику
        stats = spam_filter.get_stats()
        print(f"\n⚙️  СТАТИСТИКА ФИЛЬТРА:")
        print(f"  Включен: {stats['enabled']}")
        print(f"  Black list компаний: {stats['company_blacklist_items']} (Google, Яндекс)")
        print(f"  White list компаний: {stats['company_whitelist_items']}")
        print(f"  Требует review: {stats['require_review_before_delete']}")
        
        # ПРОВЕРКА РЕЗУЛЬТАТОВ
        print(f"\n🧪 ПРОВЕРКА РЕЗУЛЬТАТОВ:")
        print(f"{"─"*70}")
        
        expected_spam = sum(1 for tc in test_cases if tc["should_be_spam"])
        actual_spam = total_rejected
        
        if actual_spam == expected_spam:
            print(f"✅ ПРОЙДЕНО: Отклонено правильное количество писем ({actual_spam}/{expected_spam})")
        else:
            print(f"❌ ОШИБКА: Ожидалось {expected_spam}, получено {actual_spam}")
            return False
        
        if len(result_files) == len(test_cases) - expected_spam:
            print(f"✅ ПРОЙДЕНО: Обработано правильное количество писем ({len(result_files)})")
        else:
            print(f"❌ ОШИБКА: Ожидалось {len(test_cases) - expected_spam} файлов результатов, получено {len(result_files)}")
            return False
        
        if spam_filter.config["spam_filters"]["require_review_before_delete"]:
            if len(review_files) > 0:
                print(f"✅ ПРОЙДЕНО: Письма сохранены на проверку ({len(review_files)} файлов)")
            else:
                print(f"⚠️  ВНИМАНИЕ: Папка review пуста (требуется ручная проверка)")
        
        print(f"\n✅ ВСЕ ТЕСТЫ ИНТЕГРАЦИИ ПРОЙДЕНЫ!")
        print("="*70 + "\n")
        
        return True
        
        print(f"\n✅ ВСЕ ТЕСТЫ ИНТЕГРАЦИИ ПРОЙДЕНЫ!")
        print("="*70 + "\n")
        
        return True


if __name__ == "__main__":
    success = test_spam_integration()
    exit(0 if success else 1)
