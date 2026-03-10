"""
Продвинутый спам-фильтр на основе нейросетей для глубокого анализа содержимого писем.
Использует трансформеры для классификации текста и распознавания паттернов спама.
"""

import re
import logging
import json
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from datetime import datetime
import hashlib

try:
    from transformers import pipeline, AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

from .spam_filter import SpamFilter

logger = logging.getLogger(__name__)


class AdvancedSpamFilter(SpamFilter):
    """
    Расширенный фильтр спама с использованием нейросетей.
    
    Использует:
    1. Zero-shot классификацию для определения типа письма
    2. NLP анализ для распознавания паттернов спама и фишинга
    3. Эвристические правила для определения подозрительных писем
    4. Систему рейтинга риска (0-100)
    """

    def __init__(self, config: Dict[str, Any]):
        """Инициализирует продвинутый фильтр спама."""
        super().__init__(config)
        
        self.ml_config = config.get('spam_filters', {}).get('ml_filter', {})
        self.use_ml_filter = self.ml_config.get('enabled', HAS_TRANSFORMERS)
        self.ml_threshold = self.ml_config.get('spam_threshold', 0.7)  # 70% = спам
        self.model_name = self.ml_config.get('model', 'facebook/bart-large-mnli')
        
        # Инициализируем ML модели
        self.classifier = None
        self.tokenizer = None
        self._init_ml_models()
        
        # Паттерны для распознавания спама/фишинга
        self.spam_patterns = self._compile_spam_patterns()
        self.phishing_patterns = self._compile_phishing_patterns()
        self.suspicious_patterns = self._compile_suspicious_patterns()

    def _init_ml_models(self) -> None:
        """Инициализирует трансформер-модели для анализа."""
        if not self.use_ml_filter or not HAS_TRANSFORMERS:
            logger.info("ML-based spam filtering disabled or transformers not available")
            return
        
        try:
            logger.info(f"Loading ML model: {self.model_name}")
            # Используем zero-shot классификацию
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=-1  # CPU (используй device=0 для GPU)
            )
            logger.info("✓ ML spam classifier loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load ML classifier: {e}")
            self.classifier = None

    @staticmethod
    def _compile_spam_patterns() -> List[re.Pattern]:
        """Паттерны для распознавания типичного спама."""
        spam_keywords = [
            # Финансовые мошенства
            r'(?:click|tap|verify|confirm|update)\s+(?:now|immediately|immediately)',
            r'(?:verify|confirm|update).*account',
            r'(?:urgent|immediately|asap).*(?:action|click|verify)',
            r'(?:you(?:r)?)?.*(?:account|password|credentials).*(?:expired|suspended|locked)',
            
            # Лотереи и призы
            r'won|won\s+(?:you|a|the|grand|prize)',
            r'(?:congratulations|claim|winner|prize|jackpot)',
            r'(?:free|claim).{0,30}(?:money|cash|prize|iphone|amazon)',
            
            # Технические мошенства
            r'ransomware|malware|trojan|virus detected',
            r'(?:microsoft|apple|amazon|google).*(?:support|security|urgent)',
            r'system\s+(?:error|alert|warning).*(?:repair|fix|update)',
            
            # Фармацевтические товары
            r'(?:cheap|discount|order).{0,20}(?:viagra|cialis|phentermine|xanax)',
            
            # Деньги и инвестиции
            r'(?:make|earn|get).{0,30}(?:money|dollars|fast|quick)',
            r'(?:guaranteed|sure|no\s+risk).*(?:profit|earn|return)',
            r'(?:nigerian|prince|inheritance|lottery|fund)',
        ]
        
        compiled = []
        for pattern in spam_keywords:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid spam pattern: {pattern}, error: {e}")
        
        return compiled

    @staticmethod
    def _compile_phishing_patterns() -> List[re.Pattern]:
        """Паттерны для распознавания фишинга."""
        phishing_keywords = [
            # Запросы логинов/паролей
            r'(?:click|tap).{0,30}(?:confirm|verify|update).*(?:credentials|password|account)',
            r'please\s+(?:click|confirm|verify).*(?:identity|account|credentials)',
            
            # Подозрительные ссылки и запросы
            r'(?:re-?confirm|re-?verify).*(?:details|information|account)',
            r'unusual\s+(?:activity|access|sign-?in)',
            
            # Срочность
            r'(?:act\s+)?now|(?:do\s+)?immediately|urgent\s+action\s+required',
            r'(?:your\s+)?account\s+(?:will|may)\s+be\s+(?:closed|suspended|limited)',
            
            # Технический предлог
            r'(?:for\s+)?security\s+(?:reason|purpose|update)',
            r'(?:system|account).*(?:maintenance|upgrade|update)',
        ]
        
        compiled = []
        for pattern in phishing_keywords:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid phishing pattern: {pattern}, error: {e}")
        
        return compiled

    @staticmethod
    def _compile_suspicious_patterns() -> List[re.Pattern]:
        """Паттерны для распознавания подозрительных писем."""
        suspicious_keywords = [
            # Ненормальная пунктуация/форматирование
            r'[!]{3,}|\?{3,}|={10,}',  # Много ! или ? или =
            
            # Капслок
            r'([A-Z]{5,}\s+){2,}',  # Несколько слов капслоком
            
            # Странные URL паттерны
            r'(?:http|ftp).*(?:tiny|bit|short)',  # Короткие URL
            r'@.*(?:bit|tiny|short)',  # Скрытые домены
            
            # Неправильная грамматика (признак спама)
            r'(?:i\s+am|we\s+are)\s+(?:happy|pleased|delighted).*(?:inform|notify)',
            r'(?:dear|valued|beloved)\s+(?:customer|user|friend)',
            
            # Странные символы
            r'\$\$+|XXX+|[^\x00-\x7F]{10,}',  # Много $ или X или не-ASCII
        ]
        
        compiled = []
        for pattern in suspicious_keywords:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid suspicious pattern: {pattern}, error: {e}")
        
        return compiled

    def analyze_with_ml(self, text: str, subject: str = "") -> Tuple[float, List[str]]:
        """
        Анализирует текст с помощью нейросети.
        
        Returns:
            (spam_probability: float, reasons: List[str])
            spam_probability: 0.0 (легитимное) - 1.0 (определённо спам)
        """
        if not self.classifier:
            return 0.0, []
        
        try:
            # Подготавливаем текст
            combined_text = f"{subject}. {text}"[:512]  # Max 512 символов
            
            # Классифицируем
            candidate_labels = [
                "This is spam or unsolicited email",
                "This is legitimate business email"
            ]
            
            result = self.classifier(
                combined_text,
                candidate_labels,
                multi_class=False
            )
            
            # Извлекаем вероятность спама
            spam_idx = next(i for i, label in enumerate(result['labels']) if 'spam' in label.lower())
            spam_probability = result['scores'][spam_idx]
            
            reasons = []
            if spam_probability > 0.8:
                reasons.append(f"High spam probability ({spam_probability:.1%})")
            
            return spam_probability, reasons
            
        except Exception as e:
            logger.warning(f"ML analysis failed: {e}")
            return 0.0, []

    def calculate_risk_score(
        self,
        email_data: Dict[str, Any],
        subject: str = "",
        body: str = "",
        sender: str = "",
        email_size_bytes: int = 0
    ) -> Tuple[float, List[str]]:
        """
        Рассчитывает риск-скор письма (0-100).
        
        Returns:
            (risk_score: float, reasons: List[str])
        """
        risk_score = 0.0
        reasons = []
        
        # === ПАТТЕРНЫ СПАМА (до 30 баллов) ===
        spam_pattern_matches = sum(1 for p in self.spam_patterns if p.search(body + subject))
        spam_risk = min(30, spam_pattern_matches * 5)
        if spam_risk > 0:
            risk_score += spam_risk
            reasons.append(f"Spam patterns detected ({spam_pattern_matches} matches, +{spam_risk:.0f}pts)")
        
        # === ПАТТЕРНЫ ФИШИНГА (до 35 баллов) ===
        phishing_pattern_matches = sum(1 for p in self.phishing_patterns if p.search(body + subject))
        phishing_risk = min(35, phishing_pattern_matches * 7)
        if phishing_risk > 0:
            risk_score += phishing_risk
            reasons.append(f"Phishing indicators ({phishing_pattern_matches} matches, +{phishing_risk:.0f}pts)")
        
        # === ПОДОЗРИТЕЛЬНОЕ ФОРМАТИРОВАНИЕ (до 20 баллов) ===
        suspicious_match_count = sum(1 for p in self.suspicious_patterns if p.search(body + subject))
        suspicious_risk = min(20, suspicious_match_count * 4)
        if suspicious_risk > 0:
            risk_score += suspicious_risk
            reasons.append(f"Suspicious formatting ({suspicious_match_count} issues, +{suspicious_risk:.0f}pts)")
        
        # === ПОДОЗРИТЕЛЬНЫЕ EMAIL-Ы (до 15 баллов) ===
        if self._check_suspicious_emails(email_data.get('emails', [])):
            risk_score += 15
            reasons.append("Suspicious email addresses detected (+15pts)")
        
        # === ML КЛАССИФИКАЦИЯ (до 20 баллов, если включена) ===
        if self.use_ml_filter and self.classifier:
            ml_spam_prob, ml_reasons = self.analyze_with_ml(body, subject)
            ml_risk = ml_spam_prob * 20
            if ml_risk > 0:
                risk_score += ml_risk
                reasons.extend(ml_reasons)
                reasons.append(f"ML analysis risk: {ml_risk:.0f}pts")
        
        # === АНАЛИЗ ТЕКСТА (до 10 баллов) ===
        text_risk = self._analyze_text_quality(body)
        if text_risk > 0:
            risk_score += text_risk
            reasons.append(f"Poor text quality (+{text_risk:.0f}pts)")
        
        risk_score = min(100.0, max(0.0, risk_score))
        
        return risk_score, reasons

    @staticmethod
    def _check_suspicious_emails(emails: List[str]) -> bool:
        """Проверяет, есть ли подозрительные email адреса."""
        suspicious_patterns = [
            r'test\d+@',  # test123@
            r'temp\w+@',  # temp...@
            r'[0-9]{5,}@',  # 12345@
            r'noreply@',  # no-reply системные письма
            r'notification.*@',  # notification@
        ]
        
        for email in emails:
            for pattern in suspicious_patterns:
                if re.search(pattern, email, re.IGNORECASE):
                    return True
        
        return False

    @staticmethod
    def _analyze_text_quality(text: str) -> float:
        """Анализирует качество текста. Низкое качество = выше риск."""
        risk = 0.0
        
        # Слишком короткий текст
        words = text.split()
        if len(words) < 5:
            risk += 3
        
        # Слишком много пунктуации
        punct_ratio = sum(1 for c in text if c in '!?.,;:') / max(len(text), 1)
        if punct_ratio > 0.15:
            risk += 4
        
        # Слишком много цифр
        digit_ratio = sum(1 for c in text if c.isdigit()) / max(len(text), 1)
        if digit_ratio > 0.2:
            risk += 3
        
        return risk

    def is_spam(
        self,
        email_data: Dict[str, Any],
        subject: str = "",
        body: str = "",
        sender: str = "",
        email_size_bytes: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """
        Определяет, является ли письмо спамом, используя комбинацию методов.
        
        Returns:
            (is_spam: bool, reason: str or None)
        """
        # === ПЕРВАЯ ЛИНИЯ ЗАЩИТЫ: Быстрые проверки ===
        basic_is_spam, basic_reason = super().is_spam(
            email_data, subject, body, sender, email_size_bytes
        )
        
        if basic_is_spam:
            # Базовые проверки уже определили спам
            return True, basic_reason
        
        # === ВТОРАЯ ЛИНИЯ ЗАЩИТЫ: Углубленный анализ ===
        risk_score, risk_reasons = self.calculate_risk_score(
            email_data, subject, body, sender, email_size_bytes
        )
        
        # Определяем спам по риск-скору
        spam_threshold = self.ml_config.get('risk_threshold', 60)  # 60 баллов = спам
        
        if risk_score >= spam_threshold:
            reason = f"High spam risk score: {risk_score:.0f}/100. Reasons: {', '.join(risk_reasons[:3])}"
            return True, reason
        
        return False, None

    def get_email_risk_profile(
        self,
        email_data: Dict[str, Any],
        subject: str = "",
        body: str = "",
        sender: str = "",
        email_size_bytes: int = 0
    ) -> Dict[str, Any]:
        """
        Возвращает полный профиль рисков письма (без блокировки).
        Полезно для анализа и отладки.
        """
        risk_score, risk_reasons = self.calculate_risk_score(
            email_data, subject, body, sender, email_size_bytes
        )
        
        ml_spam_prob = 0.0
        if self.use_ml_filter and self.classifier:
            ml_spam_prob, _ = self.analyze_with_ml(body, subject)
        
        return {
            "risk_score": risk_score,
            "risk_level": (
                "🔴 CRITICAL" if risk_score >= 80 else
                "🟠 HIGH" if risk_score >= 60 else
                "🟡 MEDIUM" if risk_score >= 40 else
                "🟢 LOW"
            ),
            "ml_spam_probability": ml_spam_prob,
            "risk_factors": risk_reasons,
            "sender": sender,
            "subject": subject[:50],
            "company": email_data.get('company', 'Unknown'),
            "recommendation": (
                "BLOCK" if risk_score >= 80 else
                "REVIEW" if risk_score >= 60 else
                "PROCESS"
            )
        }
