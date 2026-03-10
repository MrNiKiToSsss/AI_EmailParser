import json
import logging
import subprocess
import time
from typing import Any, Dict
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

"""Промпт для Ollama и создание запроса (локальная модель)"""

logger = logging.getLogger(__name__)

EXPECTED_KEYS = ("full_name", "emails", "phones", "company", "position", "product")
_OLLAMA_START_ATTEMPTED = False


def format_prompt(text: str) -> str:
    return f"""Проанализируй текст письма и выдели персональные данные, присылай даные в кодровке UTF-8, начни поддерживать русский язык, найди в письме продукт которым интересовались. Ответ строго в JSON:
    {{
    "full_name": "",
    "emails": [],
    "phones": [],
    "company": "",
    "position": "",
    "product": ""
    }}

    Текст письма:
    {text}
    """

def _make_session() -> requests.Session:
    """Session + ретраи на сетевые сбои для стабильности."""
    s = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("POST",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


_SESSION = _make_session()


def _normalize_result(data: Any) -> Dict[str, Any]:
    """Приводит ответ модели к стабильной схеме."""
    if not isinstance(data, dict):
        data = {}

    normalized: Dict[str, Any] = {}
    for k in EXPECTED_KEYS:
        normalized[k] = data.get(k, "")

    # типы
    if not isinstance(normalized["full_name"], str):
        normalized["full_name"] = str(normalized["full_name"])
    if not isinstance(normalized["company"], str):
        normalized["company"] = str(normalized["company"])
    if not isinstance(normalized["position"], str):
        normalized["position"] = str(normalized["position"])
    if not isinstance(normalized["product"], str):
        normalized["product"] = str(normalized["product"])

    emails = normalized.get("emails", [])
    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(",") if e.strip()]
    elif not isinstance(emails, list):
        emails = [str(emails)] if emails else []
    normalized["emails"] = [str(e) for e in emails if str(e).strip()]

    phones = normalized.get("phones", [])
    if isinstance(phones, str):
        phones = [p.strip() for p in phones.split(",") if p.strip()]
    elif not isinstance(phones, list):
        phones = [str(phones)] if phones else []
    normalized["phones"] = [str(p) for p in phones if str(p).strip()]

    return normalized


def _ensure_ollama_running(api_url: str, model: str) -> None:
    """
    Пытается убедиться, что Ollama-сервер запущен.

    1. Делает быстрый запрос к /api/tags.
    2. Если соединения нет, один раз пробует запустить `ollama serve` в фоне.
    3. Ждёт пару секунд и проверяет ещё раз.

    Если ничего не получилось, просто пишет предупреждение в лог и продолжает,
    чтобы не ломать общую обработку писем.
    """
    global _OLLAMA_START_ATTEMPTED

    try:
        parsed = urlparse(api_url)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        base = f"{scheme}://{host}:{port}"

        # Быстрая проверка: сервер уже работает?
        try:
            r = _SESSION.get(f"{base}/api/tags", timeout=1)
            if r.ok:
                return
        except Exception:
            pass

        if _OLLAMA_START_ATTEMPTED:
            # Уже пытались запустить — не спамим
            logger.warning("Ollama server not reachable at %s", base)
            return

        _OLLAMA_START_ATTEMPTED = True

        # Пробуем запустить ollama serve в фоне
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            logger.info("Attempted to start Ollama daemon via `ollama serve`.")
        except Exception as e:
            logger.warning(
                "Failed to auto-start Ollama daemon (ollama serve). "
                "Please ensure Ollama is installed and in PATH. Error: %s",
                e,
            )
            return

        # Даём серверу немного времени на запуск
        time.sleep(3)

        try:
            r = _SESSION.get(f"{base}/api/tags", timeout=3)
            if r.ok:
                logger.info("Ollama server is now reachable at %s", base)
                return
        except Exception:
            pass

        logger.warning(
            "Could not reach Ollama server at %s even after auto-start attempt. "
            "Please start Ollama manually (e.g. `ollama serve`).",
            base,
        )
    except Exception as e:
        logger.warning("Error while checking/starting Ollama server: %s", e)


def analyze_email(text, config) -> str:
    """Запрос к локальной модели Ollama. Возвращает JSON-строку."""
    try:
        api_url = config["ollama"]["api_url"]
        model = config["ollama"]["model"]
        timeout_s = config.get("ollama", {}).get("timeout", 160)

        # Перед запросом убеждаемся, что Ollama-сервер запущен (по возможности).
        _ensure_ollama_running(api_url, model)

        # requests timeout лучше задавать как (connect, read)
        timeout = (10, int(timeout_s)) if isinstance(timeout_s, (int, float)) else (10, 160)

        response = _SESSION.post(
            api_url,
            json={
                "model": model,
                "prompt": format_prompt(text),
                "format": "json",
                "stream": False,
            },
            timeout=timeout,
        )

        if response.status_code != 200:
            logger.warning("Ollama HTTP %s: %s", response.status_code, response.text[:5000])
            return json.dumps(_normalize_result({}), ensure_ascii=False)

        try:
            payload = response.json()
        except Exception:
            logger.warning("Ollama returned non-JSON response: %s", response.text[:2000])
            return json.dumps(_normalize_result({}), ensure_ascii=False)

        raw = (payload.get("response") or "").strip()

        # распакуем 1-2 раза, если пришло "JSON внутри строки"
        data: Any = {}
        for _ in range(2):
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {}
            if isinstance(parsed, str):
                raw = parsed.strip()
                continue
            data = parsed
            break

        return json.dumps(_normalize_result(data), ensure_ascii=False)

    except Exception as e:
        logger.exception("AI Error: %s", e)
        return json.dumps(_normalize_result({}), ensure_ascii=False)