import os
from pathlib import Path
from typing import Tuple

import yaml


def _load_storage_paths(base_dir: Path) -> Tuple[Path, Path]:
    """
    Безопасно получает пути к results/emails из config.yaml.
    Если конфиг не найден или повреждён — использует стандартные ./data/*.
    """
    config_path = base_dir / "config.yaml"
    default_results = base_dir / "data" / "results"
    default_emails = base_dir / "data" / "emails"

    if not config_path.exists():
        return default_results, default_emails

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        storage = cfg.get("storage", {}) or {}
        results_dir = Path(storage.get("results_dir", default_results))
        emails_dir = Path(storage.get("emails_dir", default_emails))

        if not results_dir.is_absolute():
            results_dir = (base_dir / results_dir).resolve()
        if not emails_dir.is_absolute():
            emails_dir = (base_dir / emails_dir).resolve()

        return results_dir, emails_dir
    except Exception:
        return default_results, default_emails


def rename_files(directory: Path, extension: str) -> None:
    """
    Переименовывает файлы в указанной папке в последовательность 1.ext, 2.ext, ...
    Работает только с именами, состоящими целиком из цифр.
    """
    if not directory.is_dir():
        print(f"Папка не найдена, пропускаю: {directory}")
        return

    files = os.listdir(directory)
    target_files = [
        f for f in files if f.endswith(extension) and f[: -len(extension)].isdigit()  # noqa: E203
    ]

    target_files.sort(key=lambda x: int(x[: -len(extension)]))  # noqa: E203

    for idx, filename in enumerate(target_files, start=1):
        old_path = directory / filename
        new_name = f"{idx}{extension}"
        new_path = directory / new_name
        if old_path == new_path:
            continue
        os.rename(old_path, new_path)


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    json_directory, eml_directory = _load_storage_paths(base_dir)

    rename_files(json_directory, ".json")
    rename_files(eml_directory, ".eml")

    print("Переименование завершено.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())