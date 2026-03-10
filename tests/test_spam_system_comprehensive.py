#!/usr/bin/env python3
"""
Комплексный тест системы фильтрации спама и отдельного раздела для мусора.
Проверяет все аспекты спам-фильтрации, управление папкой review, и потенциальные ошибки.
"""

import pytest
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from scr.spam_filter import SpamFilter, should_process_email


class TestSpamSystemComprehensive:
    """Комплексные тесты системы спама/мусора."""

    @pytest.fixture
    def test_config(self):
        """Тестовая конфигурация со всеми параметрами."""
        return {
            "spam_filters": {
                "enabled": True,
                "subject_blacklist": ["unsubscribe", "viagra", "casino", "lottery"],
                "body_blacklist": ["click here", "bitcoin", "limited offer", "buy now"],
                "sender_blacklist": ["*@spam.com", "*noreply*", "notification@*"],
                "min_company_length": 2,
                "min_email_count": 0,
                "min_contact_info": 1,
                "exclude_replies": False,
                "exclude_forwards": False,
                "max_email_size_mb": 10,
                "min_email_size_kb": 0,  # Не фильтровать по минимальному размеру
                "company_blacklist": ["Google", "Яндекс", "Microsoft", "Apple", "Amazon"],
                "company_whitelist": [],
                "require_review_before_delete": True,
                "review_folder": "./data/review_test"
            }
        }

    @pytest.fixture
    def cleanup_review_folder(self, test_config):
        """Очищает папку review до и после теста."""
        review_folder = test_config["spam_filters"]["review_folder"]
        # Очистить перед тестом
        if os.path.exists(review_folder):
            shutil.rmtree(review_folder)
        
        yield
        
        # Очистить после теста
        if os.path.exists(review_folder):
            shutil.rmtree(review_folder)

    # ========== ТЕСТЫ ОСНОВНОЙ ФИЛЬТРАЦИИ ==========

    def test_spam_enabled_disabled_mode(self, test_config):
        """Тест: включение/отключение фильтра спама."""
        # Отключенный фильтр
        disabled_config = test_config.copy()
        disabled_config["spam_filters"]["enabled"] = False
        
        filter_obj = SpamFilter(disabled_config)
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="VIAGRA SALE!!!",
            body="Click here now for best prices",
            sender="spam@spam.com"
        )
        
        assert not is_spam, "Отключенный фильтр должен пропускать спам"
        assert reason is None

    def test_subject_blacklist_case_insensitive(self, test_config):
        """Тест: черный список по теме (игнорирует регистр)."""
        filter_obj = SpamFilter(test_config)
        
        test_cases = [
            "UNSUBSCRIBE from our list",
            "unsubscribe here",
            "VIAGRA for sale",
            "Casino games online"
        ]
        
        for subject in test_cases:
            is_spam, reason = filter_obj.is_spam(
                email_data={},
                subject=subject,
                body="Normal content",
                sender="test@example.com"
            )
            assert is_spam, f"Subject '{subject}' должен быть отфильтрован"
            assert "Subject matches blacklist" in reason

    def test_body_blacklist_detection(self, test_config):
        """Тест: обнаружение спама в теле письма."""
        filter_obj = SpamFilter(test_config)
        
        body_text = """
        Привет! Это специальное предложение.
        Click here now for limited offer.
        Не пропусти возможность!
        """
        
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="Special Offer",
            body=body_text,
            sender="sales@company.com"
        )
        
        assert is_spam, "Текст с 'click here' должен быть отфильтрован"
        assert "Body contains blacklisted" in reason

    def test_sender_wildcard_matching(self, test_config):
        """Тест: совпадение отправителя с wildcards."""
        filter_obj = SpamFilter(test_config)
        
        test_cases = [
            ("user@spam.com", True),  # Совпадает *@spam.com
            ("admin@spam.com", True),  # Совпадает *@spam.com
            ("noreply@company.com", True),  # Совпадает *noreply*
            ("notification@service.com", True),  # Совпадает notification@*
            ("normal@example.com", False),  # Не совпадает
        ]
        
        for sender, should_match in test_cases:
            is_spam, reason = filter_obj.is_spam(
                email_data={
                    "company": "TestCorp",
                    "emails": ["test@example.com"],
                    "phones": []
                },
                subject="Test",
                body="Content",
                sender=sender
            )
            
            if should_match:
                assert is_spam, f"Отправитель '{sender}' должен быть отфильтрован"
            else:
                assert not is_spam, f"Отправитель '{sender}' не должен быть отфильтрован"

    def test_reply_forward_filtering(self, test_config):
        """Тест: фильтрация ответов и пересылаемых писем."""
        test_config["spam_filters"]["exclude_replies"] = True
        test_config["spam_filters"]["exclude_forwards"] = True
        
        filter_obj = SpamFilter(test_config)
        
        # Тест Reply
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="Re: Important Meeting",
            body="Content",
            sender="test@example.com"
        )
        assert is_spam, "Ответы должны быть отфильтрованы"
        assert "reply" in reason.lower()
        
        # Тест Forward
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="Fwd: Check this out",
            body="Content",
            sender="test@example.com"
        )
        assert is_spam, "Пересланные письма должны быть отфильтрованы"
        assert "forward" in reason.lower()

    def test_email_size_filtering(self, test_config):
        """Тест: фильтрация по размеру письма."""
        filter_obj = SpamFilter(test_config)
        
        # Слишком большое письмо
        large_email_size = 11 * 1024 * 1024  # 11MB (лимит 10MB)
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "TestCorp",
                "emails": ["test@example.com"],
                "phones": []
            },
            subject="Test",
            body="Content",
            sender="test@example.com",
            email_size_bytes=large_email_size
        )
        assert is_spam, "Большие письма должны быть отфильтрованы"
        assert "size" in reason.lower()

    def test_company_length_validation(self, test_config):
        """Тест: проверка минимальной длины названия компании."""
        filter_obj = SpamFilter(test_config)
        
        # Компания слишком короткая (< 2 символов)
        is_spam, reason = filter_obj.is_spam(
            email_data={"company": "A"},
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        assert is_spam, "Короткие названия компаний должны быть отфильтрованы"
        assert "too short" in reason.lower()

    # ========== ТЕСТЫ ЧЕРНОГО СПИСКА КОМПАНИЙ ==========

    def test_company_blacklist_exact_match(self, test_config):
        """Тест: точное совпадение компании в черном списке."""
        filter_obj = SpamFilter(test_config)
        
        blacklisted_companies = ["Google", "Яндекс", "Microsoft", "Apple", "Amazon"]
        
        for company in blacklisted_companies:
            is_spam, reason = filter_obj.is_spam(
                email_data={"company": company},
                subject="Test",
                body="Content",
                sender="test@example.com"
            )
            assert is_spam, f"Компания '{company}' должна быть в черном списке"
            assert "blacklisted" in reason.lower()

    def test_company_blacklist_case_insensitive(self, test_config):
        """Тест: игнорирование регистра при проверке черного списка."""
        filter_obj = SpamFilter(test_config)
        
        test_cases = ["GOOGLE", "google", "GoOgLe", "ЯНДЕКС", "яндекс"]
        
        for company in test_cases:
            is_spam, reason = filter_obj.is_spam(
                email_data={"company": company},
                subject="Test",
                body="Content",
                sender="test@example.com"
            )
            assert is_spam, f"Компания '{company}' должна быть отфильтрована (case-insensitive)"

    def test_company_blacklist_substring_match(self, test_config):
        """Тест: совпадение подстроки компании в черном списке."""
        filter_obj = SpamFilter(test_config)
        
        # "Google" находится в "Google Inc", "Google Cloud" и т.д.
        test_companies = ["Google Inc", "Google Cloud", "Google Workspace", "My Google Partner"]
        
        for company in test_companies:
            is_spam, reason = filter_obj.is_spam(
                email_data={"company": company},
                subject="Test",
                body="Content",
                sender="test@example.com"
            )
            assert is_spam, f"Компания '{company}' должна быть отфильтрована (substring)"

    # ========== ТЕСТЫ БЕЛОГО СПИСКА КОМПАНИЙ ==========

    def test_company_whitelist_empty_allows_all(self, test_config):
        """Тест: пустой белый список разрешает все компании (кроме черного списка)."""
        # Белый список пуст (по умолчанию)
        test_config["spam_filters"]["company_whitelist"] = []
        filter_obj = SpamFilter(test_config)
        
        # Обычная компания (не в черном списке)
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "TechCorp",
                "emails": ["test@techcorp.com"],
                "phones": []
            },
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        assert not is_spam, "Обычная компания должна быть разрешена при пустом белом списке"

    def test_company_whitelist_restricts_companies(self, test_config):
        """Тест: белый список ограничивает обработку только разрешенными компаниями."""
        # Белый список с конкретными компаниями
        test_config["spam_filters"]["company_whitelist"] = ["TechCorp", "StartUp Inc"]
        filter_obj = SpamFilter(test_config)
        
        # Разрешенная компания
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "TechCorp",
                "emails": ["test@techcorp.com"],
                "phones": []
            },
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        assert not is_spam, "Компания из белого списка должна быть разрешена"
        
        # Не разрешенная компания
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "OtherCompany",
                "emails": ["test@other.com"],
                "phones": []
            },
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        assert is_spam, "Компания вне белого списка должна быть отфильтрована"
        assert "not in whitelist" in reason.lower()

    def test_company_whitelist_case_insensitive(self, test_config):
        """Тест: белый список игнорирует регистр."""
        test_config["spam_filters"]["company_whitelist"] = ["TechCorp"]
        filter_obj = SpamFilter(test_config)
        
        for company_variant in ["techcorp", "TECHCORP", "TechCorp", "TeChCoRp"]:
            is_spam, reason = filter_obj.is_spam(
                email_data={
                    "company": company_variant,
                    "emails": ["test@example.com"],
                    "phones": []
                },
                subject="Test",
                body="Content",
                sender="test@example.com"
            )
            assert not is_spam, f"'{company_variant}' должна быть разрешена в белом списке"

    # ========== ТЕСТЫ ПАПКИ REVIEW ==========

    def test_review_folder_creation(self, test_config, cleanup_review_folder):
        """Тест: автоматическое создание папки review."""
        filter_obj = SpamFilter(test_config)
        review_path = Path(test_config["spam_filters"]["review_folder"])
        
        # Папка еще не должна существовать
        assert not review_path.exists(), "Папка review не должна существовать до первого сохранения"
        
        # Сохранить для review
        filter_obj.save_for_review("123", "Test Subject", {"company": "Test"}, "Test reason")
        
        # Теперь папка должна существовать
        assert review_path.exists(), "Папка review должна быть создана"
        assert review_path.is_dir(), "review должна быть папкой"

    def test_review_file_creation_and_format(self, test_config, cleanup_review_folder):
        """Тест: создание файла review с правильным форматом."""
        filter_obj = SpamFilter(test_config)
        
        email_data = {
            "company": "TestCorp",
            "full_name": "John Doe",
            "emails": ["john@example.com"],
            "phones": ["+1234567890"]
        }
        
        filter_obj.save_for_review(
            uid="email_456",
            email_subject="Test Subject Line",
            email_data=email_data,
            reason="Company blacklisted"
        )
        
        # Проверить, что файл был создан
        review_file = Path(test_config["spam_filters"]["review_folder"]) / "email_456_review.json"
        assert review_file.exists(), "Файл review должен быть создан"
        
        # Проверить содержимое файла
        with open(review_file, 'r', encoding='utf-8') as f:
            review_data = json.load(f)
        
        assert review_data["uid"] == "email_456"
        assert review_data["subject"] == "Test Subject Line"
        assert review_data["reason"] == "Company blacklisted"
        assert "timestamp" in review_data
        assert review_data["extracted_data"]["company"] == "TestCorp"

    def test_review_disabled_no_save(self, test_config, cleanup_review_folder):
        """Тест: отключенный review не сохраняет файлы."""
        test_config["spam_filters"]["require_review_before_delete"] = False
        filter_obj = SpamFilter(test_config)
        
        review_path = Path(test_config["spam_filters"]["review_folder"])
        
        # Попытаться сохранить для review
        filter_obj.save_for_review("123", "Test", {}, "Test reason")
        
        # Папка не должна быть создана
        assert not review_path.exists(), "Папка review не должна быть создана если review отключен"

    def test_review_unicode_support(self, test_config, cleanup_review_folder):
        """Тест: поддержка Unicode в файлах review."""
        filter_obj = SpamFilter(test_config)
        
        email_data = {
            "company": "ООО Компания",
            "full_name": "Иван Петров",
            "position": "Менеджер по продажам"
        }
        
        filter_obj.save_for_review(
            uid="email_ru_123",
            email_subject="Предложение услуг",
            email_data=email_data,
            reason="Компания в черном списке"
        )
        
        # Проверить, что Unicode сохранился правильно
        review_file = Path(test_config["spam_filters"]["review_folder"]) / "email_ru_123_review.json"
        with open(review_file, 'r', encoding='utf-8') as f:
            review_data = json.load(f)
        
        assert review_data["extracted_data"]["company"] == "ООО Компания"
        assert review_data["extracted_data"]["full_name"] == "Иван Петров"

    # ========== ТЕСТЫ ЛОГИРОВАНИЯ ОТКЛОНЕНИЙ ==========

    def test_rejection_logging(self, test_config):
        """Тест: логирование отклоненных писем."""
        filter_obj = SpamFilter(test_config)
        
        # Начально логирование должно быть пустым
        assert len(filter_obj.rejected_log) == 0
        
        # Добавить несколько отклонений
        filter_obj.log_rejection("email_1", "Subject blacklisted")
        filter_obj.log_rejection("email_2", "Sender blacklisted")
        filter_obj.log_rejection("email_3", "Company blacklisted")
        
        # Проверить логирование
        assert len(filter_obj.rejected_log) == 3
        summary = filter_obj.get_rejected_summary()
        assert summary["total_rejected"] == 3
        assert len(summary["rejections"]) == 3

    def test_rejection_log_timestamps(self, test_config):
        """Тест: логирование включает временные метки."""
        filter_obj = SpamFilter(test_config)
        
        filter_obj.log_rejection("email_1", "Test reason")
        
        summary = filter_obj.get_rejected_summary()
        rejection = summary["rejections"][0]
        
        assert "timestamp" in rejection
        assert rejection["uid"] == "email_1"
        assert rejection["reason"] == "Test reason"
        
        # Проверить формат timestamp (ISO format)
        timestamp = rejection["timestamp"]
        datetime.fromisoformat(timestamp)  # Должен не вызвать исключение

    # ========== ТЕСТЫ СТАТИСТИКИ ==========

    def test_filter_statistics(self, test_config):
        """Тест: получение статистики фильтров."""
        filter_obj = SpamFilter(test_config)
        stats = filter_obj.get_stats()
        
        # Проверить наличие всех ключей
        assert "enabled" in stats
        assert "subject_blacklist_items" in stats
        assert "body_blacklist_items" in stats
        assert "sender_blacklist_items" in stats
        assert "company_blacklist_items" in stats
        assert "company_whitelist_items" in stats
        assert "min_company_length" in stats
        assert "min_email_count" in stats
        assert "min_contact_info" in stats
        assert "exclude_replies" in stats
        assert "exclude_forwards" in stats
        assert "max_email_size_mb" in stats
        assert "min_email_size_kb" in stats
        assert "require_review_before_delete" in stats
        
        # Проверить значения
        assert stats["enabled"] is True
        assert stats["company_blacklist_items"] == 5  # Google, Яндекс, Microsoft, Apple, Amazon
        assert stats["company_whitelist_items"] == 0  # Пустой

    # ========== ТЕСТЫ CONTACT INFO REQUIREMENTS ==========

    def test_contact_info_requirement(self, test_config):
        """Тест: проверка минимального количества контактной информации."""
        filter_obj = SpamFilter(test_config)
        
        # Письмо с contacts
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "TestCorp",
                "emails": ["test@example.com"],
                "phones": []
            },
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        assert not is_spam, "Письмо с email должно быть принято"
        
        # Письмо без contacts
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "TestCorp",
                "emails": [],
                "phones": []
            },
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        assert is_spam, "Письмо без контактной информации должно быть отфильтровано"
        assert "contact info" in reason.lower()

    def test_minimum_email_count_requirement(self, test_config):
        """Тест: требование минимального количества email адресов."""
        test_config["spam_filters"]["min_email_count"] = 2
        filter_obj = SpamFilter(test_config)
        
        # Слишком мало email
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "TestCorp",
                "emails": ["one@example.com"],
                "phones": []
            },
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        assert is_spam, "Письмо с одним email (нужно 2) должно быть отфильтровано"

    # ========== ИНТЕГРАЦИОННЫЕ ТЕСТЫ ==========

    def test_integration_complex_spam_email(self, test_config):
        """Тест: комплексная проверка письма, которое должно быть спамом."""
        filter_obj = SpamFilter(test_config)
        
        # Письмо, которое совпадает с несколькими критериями спама
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "Unknown Corp",
                "emails": ["unknown@company.com"],
                "phones": []
            },
            subject="UNSUBSCRIBE from our newsletter",
            body="Click here now for limited offer!",
            sender="noreply@unknown.com"
        )
        
        assert is_spam, "Письмо должно быть отфильтровано"
        # Первое совпадение (subject blacklist) должно быть причиной
        assert "Subject matches blacklist" in reason

    def test_integration_legitimate_email(self, test_config):
        """Тест: проверка, что легитимное письмо не отфильтруется."""
        filter_obj = SpamFilter(test_config)
        
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "TechCorp Solutions",
                "full_name": "John Smith",
                "emails": ["john@techcorp.com"],
                "phones": ["+1-800-123-4567"],
                "position": "Sales Manager",
                "product": "CRM System"
            },
            subject="CRM Implementation Proposal",
            body="We would like to discuss your business needs and propose our CRM solution.",
            sender="john@techcorp.com"
        )
        
        assert not is_spam, "Легитимное письмо не должно быть отфильтровано"
        assert reason is None

    def test_integration_with_should_process_email_function(self, test_config):
        """Тест:使用 helper функции should_process_email."""
        should_process, spam_reason = should_process_email(
            config=test_config,
            email_data={"company": "Google"},
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        
        assert not should_process, "Google должна быть в черном списке"
        assert "blacklist" in spam_reason.lower()

    # ========== ТЕСТЫ ОБРАБОТКИ ОШИБОК ==========

    def test_empty_config(self):
        """Тест: обработка пустой конфигурации."""
        empty_config = {"spam_filters": {}}
        filter_obj = SpamFilter(empty_config)
        
        # Должна работать с дефолтными значениями
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="Test",
            body="Content",
            sender="test@example.com"
        )
        
        # По умолчанию должно быть включено
        assert filter_obj.enabled is True

    def test_none_values_in_email_data(self, test_config):
        """Тест: обработка None и пустых значений в данных письма."""
        filter_obj = SpamFilter(test_config)
        
        test_emails = [
            {"company": "TestCorp", "emails": None, "phones": None},
            {"company": "TestCorp", "emails": [], "phones": []},
            {"company": "TestCorp"},  # Пустой словарь без emails/phones
        ]
        
        for email_data in test_emails:
            is_spam, reason = filter_obj.is_spam(
                email_data=email_data,
                subject="Test Subject",
                body="Test Body",
                sender="test@example.com"
            )
            
            # Не должно быть exception
            assert isinstance(is_spam, bool)

    def test_special_characters_in_strings(self, test_config):
        """Тест: обработка специальных символов в строках."""
        filter_obj = SpamFilter(test_config)
        
        special_inputs = [
            {"subject": "Test\n\rSubject", "body": "Content\x00with\x01nulls", "sender": "test@example.com"},
            {"subject": "Subject with 你好 Chinese", "body": "Содержание на русском", "sender": "тест@пример.ру"},
            {"subject": "Subject with <html>tags</html>", "body": "<script>alert('xss')</script>", "sender": "test@example.com"},
        ]
        
        for inputs in special_inputs:
            is_spam, reason = filter_obj.is_spam(
                email_data={},
                subject=inputs["subject"],
                body=inputs["body"],
                sender=inputs["sender"]
            )
            
            # Не должно быть exception
            assert isinstance(is_spam, bool)

    def test_very_long_strings(self, test_config):
        """Тест: обработка очень длинных строк."""
        filter_obj = SpamFilter(test_config)
        
        very_long_subject = "A" * 10000
        very_long_body = "B" * 1000000
        
        is_spam, reason = filter_obj.is_spam(
            email_data={"company": "Test"},
            subject=very_long_subject,
            body=very_long_body,
            sender="test@example.com"
        )
        
        # Должна обработаться без зависаний
        assert isinstance(is_spam, bool)


# ========== ТЕСТЫ ФАЙЛОВОЙ СИСТЕМЫ ==========

class TestSpamSystemFileOperations:
    """Тесты работы с файловой системой для хранения спама."""

    def test_review_folder_permissions(self, tmp_path):
        """Тест: проверка создания папки с правильными разрешениями."""
        test_config = {
            "spam_filters": {
                "enabled": True,
                "require_review_before_delete": True,
                "review_folder": str(tmp_path / "review")
            }
        }
        
        filter_obj = SpamFilter(test_config)
        filter_obj.save_for_review("test_1", "Subject", {}, "Reason")
        
        review_path = Path(test_config["spam_filters"]["review_folder"])
        assert review_path.exists()
        assert os.access(review_path, os.R_OK)  # Read permission
        assert os.access(review_path, os.W_OK)  # Write permission

    def test_concurrent_review_saves(self, tmp_path):
        """Тест: сохранение нескольких review файлов одновременно."""
        test_config = {
            "spam_filters": {
                "enabled": True,
                "require_review_before_delete": True,
                "review_folder": str(tmp_path / "review")
            }
        }
        
        filter_obj = SpamFilter(test_config)
        
        # Сохраните несколько писем
        for i in range(10):
            filter_obj.save_for_review(f"email_{i}", f"Subject {i}", {"index": i}, f"Reason {i}")
        
        # Проверьте, что все файлы созданы
        review_path = Path(test_config["spam_filters"]["review_folder"])
        review_files = list(review_path.glob("*_review.json"))
        assert len(review_files) == 10, f"Expected 10 review files, got {len(review_files)}"

    def test_review_file_overwrite(self, tmp_path):
        """Тест: перезапись файла review с тем же UID."""
        test_config = {
            "spam_filters": {
                "enabled": True,
                "require_review_before_delete": True,
                "review_folder": str(tmp_path / "review")
            }
        }
        
        filter_obj = SpamFilter(test_config)
        
        # Сохраните первый раз
        filter_obj.save_for_review("email_1", "First Subject", {"version": 1}, "First reason")
        
        # Сохраните второй раз с тем же UID
        filter_obj.save_for_review("email_1", "Second Subject", {"version": 2}, "Second reason")
        
        # Проверьте, что был перезаписан
        review_file = Path(test_config["spam_filters"]["review_folder"]) / "email_1_review.json"
        with open(review_file, 'r', encoding='utf-8') as f:
            review_data = json.load(f)
        
        assert review_data["subject"] == "Second Subject"
        assert review_data["extracted_data"]["version"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
