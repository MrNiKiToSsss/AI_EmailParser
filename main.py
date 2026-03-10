"""Единый запуск: парсер + локальная нейросеть + веб-просмотрщик."""

from __future__ import annotations

# Fix Fortran/BLAS issue on Windows (must be before numpy/torch imports)
import os as _os
_os.environ.setdefault("FOR_DISABLE_CONSOLE_CTRL_HANDLER", "1")

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import collections
import collections.abc as _collections_abc
# Compatibility shim: older PyYAML versions reference collections.Hashable
# which was moved to collections.abc in Python 3.10+. Ensure attribute exists
if not hasattr(collections, "Hashable"):
    collections.Hashable = _collections_abc.Hashable
import yaml

from scr.imap_client import process_emails, reprocess_local_emails

logger = logging.getLogger(__name__)
_LOCAL_NN_UNAVAILABLE = False


def _setup_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_config(config_path: Path) -> Dict[str, Any]:
    """Загружает `config.yaml` + env overrides + нормализует пути storage.*."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cfg.setdefault("imap", {})
    cfg.setdefault("storage", {})
    cfg.setdefault("ollama", {})
    cfg.setdefault("local_nn", {})

    # env overrides (IMAP)
    cfg["imap"]["server"] = os.environ.get("IMAP_SERVER", cfg["imap"].get("server"))
    cfg["imap"]["port"] = int(os.environ.get("IMAP_PORT", cfg["imap"].get("port", 993)))
    cfg["imap"]["username"] = os.environ.get("IMAP_USERNAME", cfg["imap"].get("username"))
    cfg["imap"]["password"] = os.environ.get("IMAP_PASSWORD", cfg["imap"].get("password"))
    cfg["imap"]["mailbox"] = os.environ.get("IMAP_MAILBOX", cfg["imap"].get("mailbox", "INBOX"))

    # env overrides (storage)
    cfg["storage"]["emails_dir"] = os.environ.get("EMAILS_DIR", cfg["storage"].get("emails_dir"))
    cfg["storage"]["results_dir"] = os.environ.get("RESULTS_DIR", cfg["storage"].get("results_dir"))
    cfg["storage"]["processed_db"] = os.environ.get("PROCESSED_DB", cfg["storage"].get("processed_db"))

    # env overrides (ollama)
    cfg["ollama"]["api_url"] = os.environ.get("OLLAMA_API_URL", cfg["ollama"].get("api_url"))
    cfg["ollama"]["model"] = os.environ.get("OLLAMA_MODEL", cfg["ollama"].get("model"))
    if "OLLAMA_TIMEOUT" in os.environ:
        try:
            cfg["ollama"]["timeout"] = int(os.environ["OLLAMA_TIMEOUT"])
        except Exception:
            pass

    # env overrides (local nn)
    cfg["local_nn"]["model"] = os.environ.get(
        "LOCAL_NN_MODEL",
        cfg["local_nn"].get("model", "Davlan/xlm-roberta-base-ner-hrl"),
    )
    if "LOCAL_NN_DEVICE" in os.environ:
        cfg["local_nn"]["device"] = os.environ["LOCAL_NN_DEVICE"]
    if "HF_HOME" in os.environ:
        # просто пробрасываем — transformers сам использует это
        pass

    # Нормализуем пути хранилища: относительные -> относительно config.yaml
    base_dir = config_path.parent
    for key in ("emails_dir", "results_dir", "processed_db"):
        val = cfg["storage"].get(key)
        if isinstance(val, str) and val:
            p = Path(val)
            if not p.is_absolute():
                cfg["storage"][key] = str((base_dir / p).resolve())

    return cfg


def _validate_config_for_parser(cfg: Dict[str, Any]) -> None:
    required = [
        ("imap", "server"),
        ("imap", "username"),
        ("imap", "password"),
        ("storage", "emails_dir"),
        ("storage", "results_dir"),
        ("storage", "processed_db"),
    ]
    missing = [f"{a}.{b}" for a, b in required if not cfg.get(a, {}).get(b)]
    if missing:
        raise ValueError(f"Missing config keys: {', '.join(missing)}")


# -------------------- локальная "нейросеть" (transformers) + fallback --------------------
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:(?:\+7|8)\s*)?(?:\(?\d{3}\)?\s*)?\d{3}[\s-]?\d{2}[\s-]?\d{2}")


def _extract_emails(text: str) -> List[str]:
    seen = set()
    out: List[str] = []
    for m in EMAIL_RE.finditer(text or ""):
        v = m.group(0).strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def _extract_phones(text: str) -> List[str]:
    # очень осторожно: телефоны в письмах часто "ломаные"
    seen = set()
    out: List[str] = []
    for m in PHONE_RE.finditer(text or ""):
        v = re.sub(r"\s+", " ", m.group(0).strip())
        if not v:
            continue
        key = re.sub(r"\D+", "", v)
        if len(key) < 10:
            continue
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def _heuristic_product(text: str) -> str:
    """
    Простая эвристика: ищем строки "интересует/нужен/хочу/заявка" и берём хвост.
    (Нужно, чтобы даже без нейросети программа давала результат.)
    """
    if not text:
        return ""
    triggers = ("интересует", "интересует:", "нужен", "нужно", "хочу", "заявка", "запрос", "по продукту")
    for line in (ln.strip() for ln in text.splitlines()):
        low = line.lower()
        if any(t in low for t in triggers) and len(line) <= 200:
            # уберём "Интересует:" и подобное
            cleaned = re.sub(r"^(интересует|нужен|нужно|хочу|заявка|запрос|по продукту)\s*[:\-]?\s*", "", low)
            cleaned = cleaned.strip(" .;,-")
            if cleaned and len(cleaned) >= 3:
                return cleaned[:120]
    return ""


@dataclass
class LocalNeuralAnalyzer:
    model_name: str
    device: Optional[str] = None
    _nlp: Any = None

    def _load(self) -> None:
        if self._nlp is not None:
            return
        try:
            from transformers import pipeline  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Не установлены зависимости для локальной нейросети. "
                "Поставьте `transformers` и backend (обычно `torch`)."
            ) from e

        # device: оставим auto (CPU) по умолчанию ради стабильности
        # pipeline сам выберет доступное; на Windows так меньше сюрпризов
        kwargs: Dict[str, Any] = {"aggregation_strategy": "simple"}
        self._nlp = pipeline("token-classification", model=self.model_name, **kwargs)

    def analyze(self, text: str) -> Dict[str, Any]:
        self._load()
        entities = self._nlp(text or "")

        # В разных моделях лейблы отличаются: PER/PERSON, ORG/ORGANIZATION
        persons = []
        orgs = []
        for ent in entities or []:
            label = str(ent.get("entity_group") or ent.get("entity") or "")
            word = str(ent.get("word") or "").strip()
            score = float(ent.get("score") or 0.0)
            if not word:
                continue
            if label.upper() in ("PER", "PERSON"):
                persons.append((score, word))
            elif label.upper() in ("ORG", "ORGANIZATION"):
                orgs.append((score, word))

        full_name = max(persons, key=lambda x: (len(x[1]), x[0]))[1] if persons else ""
        company = max(orgs, key=lambda x: (len(x[1]), x[0]))[1] if orgs else ""

        return {
            "full_name": full_name,
            "emails": _extract_emails(text),
            "phones": _extract_phones(text),
            "company": company,
            "position": "",
            "product": _heuristic_product(text),
        }


def analyze_email_local_nn(text: str, config: Dict[str, Any]) -> str:
    global _LOCAL_NN_UNAVAILABLE

    # Если уже знаем, что локальная NN недоступна, сразу идём в fallback,
    # чтобы не спамить лог и не тратить время на повторные попытки.
    if _LOCAL_NN_UNAVAILABLE:
        data = {
            "full_name": "",
            "emails": _extract_emails(text),
            "phones": _extract_phones(text),
            "company": "",
            "position": "",
            "product": _heuristic_product(text),
        }
    else:
        model_name = config.get("local_nn", {}).get("model") or "Davlan/xlm-roberta-base-ner-hrl"
        analyzer = analyze_email_local_nn._analyzer  # type: ignore[attr-defined]
        if analyzer is None or analyzer.model_name != model_name:
            analyzer = LocalNeuralAnalyzer(model_name=model_name)
            analyze_email_local_nn._analyzer = analyzer  # type: ignore[attr-defined]

        try:
            data = analyzer.analyze(text or "")
        except Exception as e:
            # максимально стабильный fallback, логируем один раз
            _LOCAL_NN_UNAVAILABLE = True
            if not getattr(analyze_email_local_nn, "_warned_once", False):
                logger.warning("Local NN failed, using fallback: %s", e)
                analyze_email_local_nn._warned_once = True  # type: ignore[attr-defined]

            data = {
                "full_name": "",
                "emails": _extract_emails(text),
                "phones": _extract_phones(text),
                "company": "",
                "position": "",
                "product": _heuristic_product(text),
            }

    return json.dumps(data, ensure_ascii=False)


analyze_email_local_nn._analyzer = None  # type: ignore[attr-defined]


def _load_json_safe(payload: str) -> Dict[str, Any]:
    try:
        data = json.loads(payload) if payload else {}
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def _score_result(data: Dict[str, Any]) -> int:
    """
    Примерная "оценка качества" распознавания: чем больше полей и контактов,
    тем выше балл. Используется для выбора лучшего из local NN и Ollama.
    """
    if not isinstance(data, dict):
        return 0

    score = 0

    def norm_str(v: Any) -> str:
        return str(v or "").strip().lower()

    def is_default(v: Any) -> bool:
        s = norm_str(v)
        return not s or s in ("не указано", "не найдено")

    # ФИО, компания, должность, продукт — по 2 балла, если не пустые/дефолтные
    for key in ("full_name", "company", "position", "product"):
        if not is_default(data.get(key)):
            score += 2

    # Emails / телефоны — по 1 баллу за каждый непустой элемент
    for key in ("emails", "phones"):
        v = data.get(key, [])
        if isinstance(v, list):
            score += sum(1 for item in v if norm_str(item))
        else:
            if norm_str(v):
                score += 1

    return score


def analyze_email_combined(text: str, config: Dict[str, Any]) -> str:
    """
    Прогоняет письмо через локальную NN и Ollama и возвращает
    лучший результат по простой метрике заполненности полей.
    """
    from scr.ai_processor import analyze_email as analyze_email_ollama

    # Локальный анализ (нейросеть / fallback)
    local_json = analyze_email_local_nn(text, config)
    local_data = _load_json_safe(local_json)
    local_score = _score_result(local_data)

    # Анализ через Ollama (внешняя модель)
    try:
        ollama_json = analyze_email_ollama(text, config)
    except Exception as e:
        logger.warning("Ollama call failed, using local result only: %s", e)
        return json.dumps(local_data, ensure_ascii=False)

    ollama_data = _load_json_safe(ollama_json)
    ollama_score = _score_result(ollama_data)

    # Выбираем лучший по баллу, при равенстве — предпочитаем локальный
    if ollama_score > local_score:
        best = ollama_data
    else:
        best = local_data

    return json.dumps(best, ensure_ascii=False)


def _run_web(results_dir: str, host: str, port: int) -> None:
    # Подскажем Flask-части, где лежат результаты
    os.environ["RESULTS_DIR"] = results_dir
    from data.app import app  # импорт после установки env

    app.run(host=host, port=port, debug=False)


def _parse_args() -> argparse.Namespace:
    # Keep CLI help ASCII-only for Windows consoles.
    p = argparse.ArgumentParser(description="Email parser (single entrypoint).")
    sub = p.add_subparsers(dest="cmd")

    p_parse = sub.add_parser("parse", help="Fetch and process emails")
    p_parse.add_argument(
        "--engine",
        choices=("local-nn", "ollama", "combined"),
        default=os.environ.get("ENGINE", "combined"),
        help="Processing engine",
    )

    p_web = sub.add_parser("web", help="Run web viewer")
    p_web.add_argument("--host", default=os.environ.get("WEB_HOST", "0.0.0.0"))
    p_web.add_argument("--port", type=int, default=int(os.environ.get("WEB_PORT", "5555")))

    p_re = sub.add_parser("reprocess", help="Reprocess saved .eml files without IMAP")
    p_re.add_argument(
        "--engine",
        choices=("local-nn", "ollama", "combined"),
        default=os.environ.get("ENGINE", "combined"),
        help="Processing engine",
    )
    p_re.add_argument(
        "--only-missing",
        action="store_true",
        help="Only reprocess emails that do not yet have JSON result",
    )

    # удобный дефолт: если не указали подкоманду — считаем, что parse
    return p.parse_args()


def main() -> int:
    _setup_logging()
    args = _parse_args()

    config_path = Path(__file__).resolve().parent / "config.yaml"
    config = load_config(config_path)

    # cmd=None  -> по умолчанию просто запускаем веб-интерфейс (без подключения к IMAP)
    cmd = args.cmd or "web"

    if cmd == "web":
        results_dir = config.get("storage", {}).get("results_dir") or str(
            (config_path.parent / "data" / "results").resolve()
        )
        host = getattr(args, "host", os.environ.get("WEB_HOST", "0.0.0.0"))
        port = getattr(args, "port", int(os.environ.get("WEB_PORT", "5555")))
        _run_web(results_dir=results_dir, host=host, port=port)
        return 0

    # parse: ручной запуск парсера писем через IMAP
    if cmd == "parse":
        _validate_config_for_parser(config)
        engine = getattr(args, "engine", os.environ.get("ENGINE", "combined"))
        if engine == "ollama":
            from scr.ai_processor import analyze_email as analyze_email_ollama

            callback = analyze_email_ollama
        elif engine == "local-nn":
            callback = analyze_email_local_nn
        else:  # combined
            callback = analyze_email_combined

        try:
            spam_filter = process_emails(config, callback)
            logger.info("✅ Email processing completed successfully")
            logger.info(f"   Spam/Junk emails filtered: {spam_filter.get_rejected_summary()['total_rejected']}")
        except Exception as e:
            logger.error("Email processing failed: %s", e)
            return 1
        return 0

    # reprocess: прогнать уже сохранённые .eml через выбранный движок
    if cmd == "reprocess":
        engine = getattr(args, "engine", os.environ.get("ENGINE", "combined"))
        if engine == "ollama":
            from scr.ai_processor import analyze_email as analyze_email_ollama

            callback = analyze_email_ollama
        elif engine == "local-nn":
            callback = analyze_email_local_nn
        else:  # combined
            callback = analyze_email_combined

        try:
            spam_filter = reprocess_local_emails(config, callback, only_missing=getattr(args, "only_missing", False))
            logger.info("✅ Reprocessing completed successfully")
            logger.info(f"   Spam/Junk emails filtered: {spam_filter.get_rejected_summary()['total_rejected']}")
        except Exception as e:
            logger.error("Reprocess failed: %s", e)
            return 1
        return 0

    logger.error("Unknown command: %s", cmd)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
