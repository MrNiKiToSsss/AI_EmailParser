import email
import email.policy
import os
import codecs
import logging
import time
from imap_tools import MailBox

from .utils import (
    extract_text_from_email,
    load_processed_ids,
    save_email_to_file,
    update_processed_db,
)
from .spam_filter import SpamFilter
from .advanced_spam_filter import AdvancedSpamFilter

logger = logging.getLogger(__name__)


def _connect_mailbox(config, attempts: int = 3, base_sleep_s: float = 1.0):
    """Подключение к IMAP с короткими ретраями (для стабильности)."""
    server = config["imap"]["server"]
    port = int(config["imap"].get("port", 993))
    username = config["imap"]["username"]
    password = config["imap"]["password"]
    mailbox_name = config["imap"].get("mailbox", "INBOX")

    last_exc = None
    for i in range(1, attempts + 1):
        try:
            mailbox = MailBox(server, port=port).login(username, password)
            # Set the mailbox folder after login
            mailbox.folder.set(mailbox_name)
            return mailbox
        except Exception as e:
            last_exc = e
            sleep_s = base_sleep_s * i
            logger.warning("IMAP connect failed (attempt %s/%s): %s", i, attempts, e)
            time.sleep(sleep_s)
    raise last_exc  # type: ignore[misc]


def process_emails(config, callback):
    """Основной процесс обработки писем. Возвращает статистику фильтрации спама."""
    emails_dir = config["storage"]["emails_dir"]
    results_dir = config["storage"]["results_dir"]
    processed_db = config["storage"]["processed_db"]

    os.makedirs(emails_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    processed_ids = load_processed_ids(processed_db)
    
    # Используем продвинутый фильтр если ML включен, иначе базовый
    use_advanced = config.get('spam_filters', {}).get('ml_filter', {}).get('enabled', False)
    if use_advanced:
        logger.info("✓ Using Advanced ML-based spam filter")
        spam_filter = AdvancedSpamFilter(config)
    else:
        logger.info("Using basic pattern-based spam filter")
        spam_filter = SpamFilter(config)

    # Потоковая обработка: не держим все письма в памяти
    mailbox = None
    try:
        mailbox = _connect_mailbox(config)
        # Don't rely on MailBox.__exit__ for logout — some servers return
        # unexpected responses during LOGOUT which can raise in the context
        # manager. Manage logout explicitly to handle such cases gracefully.
        for msg in mailbox.fetch():
                uid = str(msg.uid)
                if uid in processed_ids:
                    continue

                try:
                    # Проверка спама перед обработкой письма
                    subject = msg.subject or ""
                    sender = msg.from_ or ""
                    text = msg.text or ""
                    if not text and msg.html:
                        text = extract_text_from_email(msg.html)

                    # Получаем размер письма (примерный расчет)
                    raw_eml = msg.obj.as_string(policy=email.policy.SMTPUTF8)
                    email_size_bytes = len(raw_eml.encode('utf-8'))

                    # Проверяем базовые фильтры парезд обработкой через AI
                    is_spam, spam_reason = spam_filter.is_spam(
                        email_data={},  # Пустой результат AI (еще не переобработано)
                        subject=subject,
                        body=text,
                        sender=sender,
                        email_size_bytes=email_size_bytes
                    )

                    if is_spam:
                        logger.warning(f"SPAM DETECTED - {uid}: {spam_reason}")
                        
                        # Если используется продвинутый фильтр - выводим детальный анализ
                        if isinstance(spam_filter, AdvancedSpamFilter):
                            risk_profile = spam_filter.get_email_risk_profile(
                                email_data={},
                                subject=subject,
                                body=text,
                                sender=sender,
                                email_size_bytes=email_size_bytes
                            )
                            logger.warning(f"  Risk level: {risk_profile['risk_level']} ({risk_profile['risk_score']:.0f}/100)")
                            logger.warning(f"  ML spam probability: {risk_profile['ml_spam_probability']:.1%}")
                            for factor in risk_profile['risk_factors'][:3]:
                                logger.warning(f"  - {factor}")
                        
                        # Логируем отклонение
                        spam_filter.log_rejection(uid, spam_reason)
                        # Сохраняем для review если требуется
                        spam_filter.save_for_review(uid, subject, {}, spam_reason)
                        update_processed_db(processed_db, uid, processed_ids=processed_ids)
                        continue

                    email_path = os.path.join(emails_dir, f"{uid}.eml")
                    save_email_to_file(raw_eml, email_path)

                    result_json_str = callback(text, config)
                    if not isinstance(result_json_str, str):
                        # На всякий случай приводим к строке
                        result_json_str = str(result_json_str)

                    result_path = os.path.join(results_dir, f"{uid}.json")
                    with codecs.open(result_path, "w", "utf-8") as f:
                        f.write(result_json_str)

                    update_processed_db(processed_db, uid, processed_ids=processed_ids)

                except Exception as e:
                    logger.exception("Error processing uid=%s: %s", uid, e)
    except Exception as e:
        logger.exception("Fatal IMAP error: %s", e)
    finally:
        # ensure we try to logout/close connection but swallow transport
        # related errors to keep the app stable
        try:
            if mailbox is not None:
                try:
                    mailbox.logout()
                except Exception:
                    logger.debug("Ignoring error during mailbox.logout()")
        except Exception:
            # defensive: any unexpected error during cleanup should not fail
            pass

    # Выводим статистику спам-фильтра
    spam_summary = spam_filter.get_rejected_summary()
    if spam_summary["total_rejected"] > 0:
        logger.warning(f"═" * 70)
        logger.warning(f"SPAM STATISTICS: Отклонено {spam_summary['total_rejected']} писем")
        for i, rejection in enumerate(spam_summary["rejections"][-5:], 1):  # Последние 5
            logger.warning(f"  {i}. [{rejection['uid']}] {rejection['reason']}")
        logger.warning(f"═" * 70)
    else:
        logger.info("SPAM: Нежелательных писем не найдено")

    return spam_filter


def reprocess_local_emails(config, callback, only_missing: bool = False) -> None:
    """
    Переобработка уже сохранённых .eml файлов без подключения к IMAP.

    Берёт письма из storage.emails_dir, прогоняет через callback и сохраняет
    результаты в storage.results_dir, перезаписывая старые JSON (если нужно).
    """
    emails_dir = config["storage"]["emails_dir"]
    results_dir = config["storage"]["results_dir"]

    os.makedirs(results_dir, exist_ok=True)

    if not os.path.isdir(emails_dir):
        logger.warning("Emails directory does not exist, nothing to reprocess: %s", emails_dir)
        return

    spam_filter = SpamFilter(config)

    for filename in sorted(os.listdir(emails_dir)):
        if not filename.lower().endswith(".eml"):
            continue

        uid, _ = os.path.splitext(filename)
        eml_path = os.path.join(emails_dir, filename)
        result_path = os.path.join(results_dir, f"{uid}.json")

        if only_missing and os.path.exists(result_path):
            continue

        try:
            with open(eml_path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()

            msg = email.message_from_string(raw, policy=email.policy.SMTPUTF8)

            text = ""
            html_part = None
            subject = msg.get("Subject", "")
            sender = msg.get("From", "")

            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/plain":
                        try:
                            text = part.get_content()
                        except Exception:
                            payload = part.get_payload(decode=True) or b""
                            text = payload.decode("utf-8", errors="replace")
                        break
                    if ctype == "text/html" and html_part is None:
                        try:
                            html_part = part.get_content()
                        except Exception:
                            payload = part.get_payload(decode=True) or b""
                            html_part = payload.decode("utf-8", errors="replace")
            else:
                ctype = msg.get_content_type()
                if ctype == "text/plain":
                    try:
                        text = msg.get_content()
                    except Exception:
                        payload = msg.get_payload(decode=True) or b""
                        text = payload.decode("utf-8", errors="replace")
                elif ctype == "text/html":
                    try:
                        html_part = msg.get_content()
                    except Exception:
                        payload = msg.get_payload(decode=True) or b""
                        html_part = payload.decode("utf-8", errors="replace")

            if not text and html_part is not None:
                if isinstance(html_part, bytes):
                    html_str = html_part.decode("utf-8", errors="replace")
                else:
                    html_str = str(html_part)
                text = extract_text_from_email(html_str)

            if not isinstance(text, str):
                text = str(text or "")

            # Получаем размер файла
            email_size_bytes = len(raw.encode('utf-8'))

            # Проверяем спам перед обработкой
            is_spam, spam_reason = spam_filter.is_spam(
                email_data={},  # Пустая AI обработка для локальной переобработки
                subject=subject,
                body=text,
                sender=sender,
                email_size_bytes=email_size_bytes
            )

            if is_spam:
                logger.warning(f"SPAM DETECTED - {uid}: {spam_reason}")
                # Логируем отклонение
                spam_filter.log_rejection(uid, spam_reason)
                # Сохраняем для review если требуется
                spam_filter.save_for_review(uid, subject, {}, spam_reason)
                continue

            result_json_str = callback(text, config)
            if not isinstance(result_json_str, str):
                result_json_str = str(result_json_str)

            with codecs.open(result_path, "w", "utf-8") as f:
                f.write(result_json_str)

            logger.info("Reprocessed %s -> %s", eml_path, result_path)

        except Exception as e:
            logger.exception("Error reprocessing %s: %s", eml_path, e)

    # Выводим статистику спам-фильтра
    spam_summary = spam_filter.get_rejected_summary()
    if spam_summary["total_rejected"] > 0:
        logger.warning(f"═" * 70)
        logger.warning(f"SPAM STATISTICS: Отклонено {spam_summary['total_rejected']} писем")
        for i, rejection in enumerate(spam_summary["rejections"][-5:], 1):  # Последние 5
            logger.warning(f"  {i}. [{rejection['uid']}] {rejection['reason']}")
        logger.warning(f"═" * 70)
    else:
        logger.info("SPAM: Нежелательных писем не найдено")

    return spam_filter
