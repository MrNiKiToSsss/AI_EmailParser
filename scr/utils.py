import json
import os
from pathlib import Path
from typing import Optional, Set, Union

from bs4 import BeautifulSoup
from email.header import decode_header as email_decode_header


def extract_text_from_email(raw_email: str) -> str:
    """Извлечение текста из HTML/plaintext"""
    if not raw_email:
        return ""
    try:
        soup = BeautifulSoup(raw_email, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return str(raw_email)


def save_email_to_file(raw_data: str, path: str) -> None:
    """Сохранение письма"""
    parent = Path(path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", errors="replace", newline="\n") as f:
        f.write(raw_data or "")


def load_processed_ids(db_path: str) -> Set[str]:
    """
    Загружает базу обработанных UID.

    Поддерживает два формата:
    - построчный текст (как сейчас в `data/processed.json`, по одному UID в строке)
    - JSON список строк: ["1","2",...]

    Любые ошибки чтения/парсинга -> пустой набор (стабильность важнее).
    """
    try:
        if not db_path or not os.path.exists(db_path):
            return set()

        with open(db_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        stripped = content.strip()
        if not stripped:
            return set()

        # Пытаемся понять JSON по первому символу, иначе считаем построчным списком
        if stripped[0] in "[{":
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return {str(x).strip() for x in parsed if str(x).strip()}
            except Exception:
                pass

        return {line.strip() for line in content.splitlines() if line.strip()}
    except Exception:
        return set()


def update_processed_db(
    db_path: str,
    message_id: Union[str, int],
    processed_ids: Optional[Set[str]] = None,
) -> None:
    """
    Добавляет UID в базу обработанных.

    По умолчанию работает в "append-only" режиме (самый устойчивый к падениям),
    чтобы не перезаписывать большой файл и не рисковать его повредить.

    Если передан `processed_ids`, то обновим и его (чтобы не писать дубликаты).
    """
    if not db_path:
        return

    uid = str(message_id).strip()
    if not uid:
        return

    if processed_ids is not None:
        if uid in processed_ids:
            return
        processed_ids.add(uid)

    parent = Path(db_path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)

    # append + fsync для устойчивости
    with open(db_path, "a", encoding="utf-8", errors="replace", newline="\n") as f:
        f.write(uid + "\n")
        try:
            f.flush()
            os.fsync(f.fileno())
        except Exception:
            # На некоторых FS/окружениях fsync может быть недоступен — это не критично.
            pass


def decode_header(header) -> str:
    """Корректно декодирует email-заголовки"""
    try:
        if header is None:
            return ""
        if isinstance(header, bytes):
            return header.decode("utf-8", errors="replace")

        decoded_parts = []
        for part, encoding in email_decode_header(str(header)):
            if isinstance(part, bytes):
                enc = encoding or "utf-8"
                try:
                    decoded_parts.append(part.decode(enc, errors="replace"))
                except Exception:
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(str(part))

        return "".join(decoded_parts).strip()
    except Exception:
        return str(header)