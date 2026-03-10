#!/usr/bin/env python3
"""Тесты для модуля фильтрации спама."""

import pytest
import yaml
from pathlib import Path
from scr.spam_filter import SpamFilter, should_process_email


class TestSpamFilter:
    """Тесты для класса SpamFilter."""

    @pytest.fixture
    def config_with_spam_filters(self):
        """Конфигурация с фильтрами спама."""
        return {
            "spam_filters": {
                "enabled": True,
                "subject_blacklist": ["unsubscribe", "viagra", "casino", "winner"],
                "body_blacklist": ["click here", "bitcoin", "limited offer"],
                "sender_blacklist": ["*@spam.com", "*noreply*"],
                "min_company_length": 2,
                "min_email_count": 0,
                "min_contact_info": 1,
                "exclude_replies": False,
                "exclude_forwards": False,
                "max_email_size_mb": 10,
                "min_email_size_kb": 1,
                "company_blacklist": ["Google", "Яндекс", "Microsoft"],
                "company_whitelist": [],
                "require_review_before_delete": False,
            }
        }

    def test_filter_disabled(self):
        """Тест: отключенный фильтр не фильтрует ничего."""
        config = {"spam_filters": {"enabled": False}}
        filter_obj = SpamFilter(config)
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="Viagra for sale",
            body="Click here now",
            sender="spam@spam.com"
        )
        assert not is_spam
        assert reason is None

    def test_filter_subject_blacklist(self, config_with_spam_filters):
        """Тест: проверка черного списка по теме."""
        filter_obj = SpamFilter(config_with_spam_filters)
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="You are a VIAGRA winner",
            body="Normal content",
            sender="test@example.com"
        )
        assert is_spam
        assert "Subject matches blacklist" in reason

    def test_filter_body_blacklist(self, config_with_spam_filters):
        """Тест: проверка черного списка по телу письма."""
        filter_obj = SpamFilter(config_with_spam_filters)
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="Normal subject",
            body="Click here now for limited offer",
            sender="test@example.com"
        )
        assert is_spam
        assert "Body contains blacklisted content" in reason

    def test_filter_sender_blacklist(self, config_with_spam_filters):
        """Тест: проверка черного списка отправителей."""
        filter_obj = SpamFilter(config_with_spam_filters)
        is_spam, reason = filter_obj.is_spam(
            email_data={},
            subject="Normal",
            body="Normal",
            sender="admin@spam.com"
        )
        assert is_spam
        assert "blacklisted" in reason

    def test_company_blacklist(self, config_with_spam_filters):
        """Тест: исключение компаний из черного списка."""
        filter_obj = SpamFilter(config_with_spam_filters)
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "Google Inc",
                "emails": ["contact@google.com"],
                "phones": []
            },
            subject="Normal",
            body="Normal",
            sender="test@google.com",
            email_size_bytes=5000
        )
        assert is_spam
        assert "blacklist" in reason.lower()

    def test_company_whitelist(self):
        """Тест: белый список компаний."""
        config = {
            "spam_filters": {
                "enabled": True,
                "subject_blacklist": [],
                "body_blacklist": [],
                "sender_blacklist": [],
                "company_blacklist": [],
                "company_whitelist": ["Valid Corp", "Trusted Inc"],
                "min_company_length": 2,
                "min_email_count": 0,
                "min_contact_info": 1,
            }
        }
        filter_obj = SpamFilter(config)
        
        # В белом списке - разрешено
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "Valid Corp",
                "emails": ["contact@validcorp.com"],
                "phones": []
            },
            subject="Normal",
            body="Normal",
            sender="test@validcorp.com",
            email_size_bytes=5000
        )
        assert not is_spam

        # Не в белом списке - запрещено
        is_spam, reason = filter_obj.is_spam(
            email_data={
                "company": "Unknown Company",
                "emails": ["contact@unknown.com"],
                "phones": []
            },
            subject="Normal",
            body="Normal",
            sender="test@unknown.com",
            email_size_bytes=5000
        )
        assert is_spam
        assert "whitelist" in reason.lower()

    def test_rejection_logging(self, config_with_spam_filters):
        """Тест: логирование отклоненных писем."""
        filter_obj = SpamFilter(config_with_spam_filters)
        
        filter_obj.log_rejection("1", "Spam subject")
        filter_obj.log_rejection("2", "Blacklisted company")
        filter_obj.log_rejection("3", "Insufficient info")
        
        stats = filter_obj.get_rejected_summary()
        assert stats["total_rejected"] == 3
        assert len(stats["rejections"]) == 3
        
        reasons = [r["reason"] for r in stats["rejections"]]
        assert "Spam subject" in reasons
        assert "Blacklisted company" in reasons
        assert "Insufficient info" in reasons

    def test_get_stats(self, config_with_spam_filters):
        """Тест: получение статистики фильтра."""
        filter_obj = SpamFilter(config_with_spam_filters)
        stats = filter_obj.get_stats()
        
        assert stats['enabled'] is True
        assert stats['subject_blacklist_items'] > 0
        assert stats['body_blacklist_items'] > 0
        assert stats['company_blacklist_items'] == 3
        assert stats['min_company_length'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
