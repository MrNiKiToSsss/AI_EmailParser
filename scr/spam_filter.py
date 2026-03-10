"""Фильтрация спам-писем на основе конфигурируемых параметров."""

import re
import logging
import json
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class SpamFilter:
    """Фильтрует письма на основе конфигурации spam_filters."""

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализирует фильтр спама.
        
        Args:
            config: Конфигурация из config.yaml
        """
        self.config = config
        self.spam_config = config.get('spam_filters', {})
        self.enabled = self.spam_config.get('enabled', True)
        
        # Загрузить черные списки
        self.subject_blacklist = self._compile_patterns(
            self.spam_config.get('subject_blacklist', [])
        )
        self.body_blacklist = self._compile_patterns(
            self.spam_config.get('body_blacklist', [])
        )
        self.sender_blacklist = self.spam_config.get('sender_blacklist', [])
        
        # Параметры качества контакта
        self.min_company_length = self.spam_config.get('min_company_length', 2)
        self.min_email_count = self.spam_config.get('min_email_count', 0)
        self.min_contact_info = self.spam_config.get('min_contact_info', 1)
        
        # Параметры типа письма
        self.exclude_replies = self.spam_config.get('exclude_replies', False)
        self.exclude_forwards = self.spam_config.get('exclude_forwards', False)
        
        # Параметры размера
        self.max_email_size_mb = self.spam_config.get('max_email_size_mb', -1)
        self.min_email_size_kb = self.spam_config.get('min_email_size_kb', 0)
        
        # Черный и белый список компаний
        self.company_blacklist = [c.lower() for c in self.spam_config.get('company_blacklist', [])]
        self.company_whitelist = [c.lower() for c in self.spam_config.get('company_whitelist', [])]
        
        # Параметры повторной проверки
        self.require_review_before_delete = self.spam_config.get('require_review_before_delete', False)
        self.review_folder = self.spam_config.get('review_folder', './data/review')
        
        # Логирование отклоненных писем
        self.rejected_log = []

    @staticmethod
    def _compile_patterns(patterns: list) -> list:
        """Компилирует строки в регулярные выражения (без учета регистра)."""
        compiled = []
        for pattern in patterns:
            try:
                # Преобразуем обычные строки в regex паттерны
                regex_pattern = pattern.replace('*', '.*')
                compiled.append(re.compile(regex_pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern: {pattern}, error: {e}")
        return compiled

    def is_spam(
        self,
        email_data: Dict[str, Any],
        subject: str = "",
        body: str = "",
        sender: str = "",
        email_size_bytes: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, является ли письмо спамом.
        
        Args:
            email_data: Результат анализа письма (с extracted data)
            subject: Тема письма
            body: Тело письма
            sender: Email адрес отправителя
            email_size_bytes: Размер письма в байтах
            
        Returns:
            (is_spam: bool, reason: str or None)
        """
        if not self.enabled:
            return False, None

        # 1. Проверка по теме письма
        if self._matches_patterns(subject, self.subject_blacklist):
            return True, f"Subject matches blacklist: {subject[:50]}"

        # 2. Проверка по телу письма
        if self._matches_patterns(body, self.body_blacklist):
            return True, f"Body contains blacklisted content"

        # 3. Проверка по отправителю
        if self._matches_sender(sender):
            return True, f"Sender {sender} is blacklisted"

        # 4. Проверка по типу письма (Reply/Forward)
        if self.exclude_replies and subject.lower().startswith('re:'):
            return True, "Email is a reply (Re:)"

        if self.exclude_forwards and subject.lower().startswith('fwd:'):
            return True, "Email is forwarded (Fwd:)"

        # 5. Проверка качества контакта и компании (ДО проверки размера)
        company = email_data.get('company', '')
        emails = email_data.get('emails', []) or []
        phones = email_data.get('phones', []) or []

        # Проверка компании в черном списке
        is_blacklisted, blacklist_reason = self._check_company_blacklist(company)
        if is_blacklisted:
            return True, blacklist_reason

        # Проверка компании в белом списке (если он заполнен)
        if self.company_whitelist:
            is_whitelisted, whitelist_reason = self._check_company_whitelist(company)
            if not is_whitelisted:
                return True, whitelist_reason

        # Проверка минимальной длины компании
        if company and len(company) < self.min_company_length:
            return True, f"Company name too short: {company} ({len(company)} chars)"

        # Проверка минимального количества email-адресов
        if self.min_email_count > 0 and len(emails) < self.min_email_count:
            return True, f"Not enough emails: {len(emails)} (min: {self.min_email_count})"

        # Проверка минимального количества контактной информации
        contact_count = len(emails) + len(phones)
        if contact_count < self.min_contact_info:
            return True, f"Not enough contact info: {contact_count} (min: {self.min_contact_info})"

        # 6. Проверка по размеру (ПОСЛЕ проверки компании)
        if self.max_email_size_mb > 0:
            size_mb = email_size_bytes / (1024 * 1024)
            if size_mb > self.max_email_size_mb:
                return True, f"Email size {size_mb:.1f}MB exceeds limit {self.max_email_size_mb}MB"

        if self.min_email_size_kb > 0:
            size_kb = email_size_bytes / 1024
            if size_kb < self.min_email_size_kb:
                return True, f"Email size {size_kb:.1f}KB is below minimum {self.min_email_size_kb}KB"

        # Письмо прошло все проверки
        return False, None

    @staticmethod
    def _matches_patterns(text: str, patterns: list) -> bool:
        """Проверяет, совпадает ли текст с одним из паттернов."""
        for pattern in patterns:
            if pattern.search(text):
                return True
        return False

    def _matches_sender(self, sender: str) -> bool:
        """Проверяет, находится ли отправитель в черном списке."""
        for blacklist_pattern in self.sender_blacklist:
            # Преобразуем паттерн с wildcards в regex
            regex_pattern = blacklist_pattern.replace('*', '.*')
            if re.match(regex_pattern, sender, re.IGNORECASE):
                return True
        return False

    def _check_company_blacklist(self, company: str) -> Tuple[bool, Optional[str]]:
        """Проверяет, находится ли компания в черном списке."""
        if not company:
            return False, None
        
        company_lower = company.lower()
        for blacklisted in self.company_blacklist:
            # Точное совпадение или подстрока
            if company_lower == blacklisted or blacklisted in company_lower:
                return True, f"Company '{company}' is blacklisted (generic/useless company)"
        
        return False, None

    def _check_company_whitelist(self, company: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, находится ли компания в белом списке (если он заполнен).
        
        Returns:
            (is_allowed: bool, reason: str or None)
        """
        if not self.company_whitelist:
            # Белый список пуст = все разрешено
            return True, None
        
        if not company:
            return False, "Company name is empty (whitelist mode requires company)"
        
        company_lower = company.lower()
        for whitelisted in self.company_whitelist:
            if company_lower == whitelisted or whitelisted in company_lower:
                return True, None
        
        return False, f"Company '{company}' not in whitelist"

    def save_for_review(self, uid: str, email_subject: str, email_data: Dict[str, Any], reason: str) -> None:
        """
        Сохраняет письмо для повторной проверки.
        
        Args:
            uid: Уникальный ID письма
            email_subject: Тема письма
            email_data: Данные анализа
            reason: Причина отклонения
        """
        if not self.require_review_before_delete:
            return
        
        # Создать папку для рецензии
        review_path = Path(self.review_folder)
        review_path.mkdir(parents=True, exist_ok=True)
        
        # Сохранить в файл
        review_file = review_path / f"{uid}_review.json"
        review_data = {
            "uid": uid,
            "timestamp": datetime.now().isoformat(),
            "subject": email_subject,
            "reason": reason,
            "extracted_data": email_data
        }
        
        try:
            with open(review_file, 'w', encoding='utf-8') as f:
                json.dump(review_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved for review: {uid} (reason: {reason})")
        except Exception as e:
            logger.error(f"Failed to save review file: {e}")

    def log_rejection(self, uid: str, reason: str) -> None:
        """Логирует отклоенные письма."""
        self.rejected_log.append({
            "uid": uid,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        })

    def get_rejected_summary(self) -> Dict[str, Any]:
        """Возвращает статистику отклоененных писем."""
        return {
            "total_rejected": len(self.rejected_log),
            "rejections": self.rejected_log
        }

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику фильтров."""
        return {
            'enabled': self.enabled,
            'subject_blacklist_items': len(self.subject_blacklist),
            'body_blacklist_items': len(self.body_blacklist),
            'sender_blacklist_items': len(self.sender_blacklist),
            'company_blacklist_items': len(self.company_blacklist),
            'company_whitelist_items': len(self.company_whitelist),
            'min_company_length': self.min_company_length,
            'min_email_count': self.min_email_count,
            'min_contact_info': self.min_contact_info,
            'exclude_replies': self.exclude_replies,
            'exclude_forwards': self.exclude_forwards,
            'max_email_size_mb': self.max_email_size_mb,
            'min_email_size_kb': self.min_email_size_kb,
            'require_review_before_delete': self.require_review_before_delete,
        }


def should_process_email(
    config: Dict[str, Any],
    email_data: Dict[str, Any],
    subject: str = "",
    body: str = "",
    sender: str = "",
    email_size_bytes: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Удобная функция для проверки, нужно ли обрабатывать письмо.
    
    Args:
        config: Конфигурация
        email_data: Результат анализа
        subject: Тема
        body: Текст
        sender: От кого
        email_size_bytes: Размер
        
    Returns:
        (should_process: bool, spam_reason: str or None)
        
    Example:
        should_process, reason = should_process_email(config, email_data, subject, body, sender)
        if should_process:
            # Обработать письмо
            ...
        else:
            logger.info(f"Skipping spam: {reason}")
    """
    spam_filter = SpamFilter(config)
    is_spam, reason = spam_filter.is_spam(email_data, subject, body, sender, email_size_bytes)
    return not is_spam, reason if is_spam else None
