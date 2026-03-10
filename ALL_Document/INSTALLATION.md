# Email Parser 2.0 - Полная инструкция по установке

**Дата**: 17 февраля 2026  
**Версия**: 2.0  
**Статус**: Production Ready

---

## 📋 Содержание

1. [Системные требования](#системные-требования)
2. [Установка на Windows](#установка-на-windows)
3. [Установка на Linux/macOS](#установка-на-linuxmacos)
4. [Конфигурация](#конфигурация)
5. [Первый запуск](#первый-запуск)
6. [Установка Ollama (опционально)](#установка-ollama-опционально)
7. [Решение проблем](#решение-проблем)

---

## Системные требования

### Минимум
- **ОС**: Windows 10, Ubuntu 18.04+, macOS 10.14+
- **Python**: 3.9 или выше
- **RAM**: 4GB
- **Место на диске**: 2GB для моделей + место для писем
- **Интернет**: Только для первой загрузки моделей

### Рекомендуемо
- **ОС**: Windows 11, Ubuntu 20.04+, macOS 12+
- **Python**: 3.11+
- **RAM**: 8GB+
- **GPU**: NVIDIA (для ускорения при Ollama)
- **Место на диске**: 5GB+

### Проверка версии Python

```bash
python --version
# Должно быть Python 3.9+

# Если не работает, попробуйте
python3 --version
```

**Если Python не установлен**: https://www.python.org/downloads/

---

## Установка на Windows

### Шаг 1: Скачиваем Python (если не установлен)

1. Откройте https://www.python.org/downloads/
2. Скачайте **Python 3.11** (или выше)
3. Запустите установщик
4. ⚠️ **ВАЖНО**: Отметьте "Add Python to PATH"
5. Кликните "Install Now"

### Шаг 2: Проверяем Python

Откройте Command Prompt или PowerShell:

```bash
python --version
# Вывод: Python 3.11.x

pip --version
# Вывод: pip 23.x ...
```

Если не работает, перезагрузитесь.

### Шаг 3: Скачиваем Email Parser

```bash
# Используя git
git clone <repository-url>
cd email_parser20

# Или скачайте ZIP и распакуйте
# Затем откройте папку в Command Prompt
```

### Шаг 4: Создаем виртуальное окружение

```bash
# Создать окружение
python -m venv ollama_env

# Активировать окружение
ollama_env\Scripts\activate

# Должно появиться "(ollama_env)" в начале строки
# Если нет - перезагрузитесь и попробуйте PowerShell вместо CMD
```

### Шаг 5: Устанавливаем зависимости

```bash
# Убедитесь, что окружение активировано (должно быть (ollama_env))

pip install -r requirements.txt

# Это может занять 5-10 минут
# Дождитесь окончания установки
```

### Шаг 6: Конфигурируем

```bash
# Откройте config.yaml в текстовом редакторе
# Например, Notepad++:
notepad++ config.yaml

# Или в любом другом редакторе
# Отредактируйте IMAP данные
```

### Шаг 7: Запускаем

```bash
# Веб-интерфейс
python main.py web

# Откройте браузер на http://localhost:5555
```

---

## Установка на Linux/macOS

### Шаг 1: Проверяем Python

```bash
python3 --version
# Должно быть Python 3.9+

# Если Python не установлен:
# Ubuntu:
sudo apt update
sudo apt install python3 python3-pip python3-venv

# macOS:
brew install python3
```

### Шаг 2: Клонируем репозиторий

```bash
git clone <repository-url>
cd email_parser20
```

### Шаг 3: Создаем виртуальное окружение

```bash
python3 -m venv ollama_env

# Активируем
source ollama_env/bin/activate

# Должно появиться "(ollama_env)" в начале строки
```

### Шаг 4: Устанавливаем зависимости

```bash
pip install --upgrade pip
pip install -r requirements.txt

# Это может занять 5-10 минут
```

### Шаг 5: Конфигурируем

```bash
# Отредактируйте config.yaml
nano config.yaml

# Измените IMAP параметры
# Когда закончите: Ctrl+X, Y, Enter
```

### Шаг 6: Запускаем

```bash
python main.py web

# Откройте браузер на http://localhost:5555
```

---

## Конфигурация

### Основные параметры config.yaml

```yaml
imap:
  # IMAP сервер вашей почты
  server: mail.nic.ru
  
  # Порт (обычно 993 для IMAPS)
  port: 993
  
  # Ваш email адрес
  username: your@email.com
  
  # Ваш пароль (или пароль приложения)
  password: 'your_password'
  
  # Папка которую парсить
  mailbox: INBOX
```

### Примеры популярных IMAP серверов

| Провайдер | IMAP сервер | Порт | Пароль |
|-----------|------------|------|--------|
| Gmail | imap.gmail.com | 993 | App password* |
| Яндекс | imap.yandex.com | 993 | Обычный пароль |
| Mail.ru | imap.mail.ru | 993 | Обычный пароль |
| Outlook | outlook.office365.com | 993 | Обычный пароль |
| Nic.ru | mail.nic.ru | 993 | Обычный пароль |

*Для Gmail нужен специальный **App Password**: https://support.google.com/accounts/answer/185833

### Переменные окружения (для production)

Вместо хранения пароля в config.yaml, используйте переменные окружения:

**Windows**:
```bash
setx IMAP_PASSWORD your_password
# Перезагрузитесь
```

**Linux/macOS**:
```bash
export IMAP_PASSWORD=your_password
export IMAP_USERNAME=your@email.com
```

Или в файле `.env`:
```
IMAP_PASSWORD=your_password
IMAP_USERNAME=your@email.com
IMAP_SERVER=mail.nic.ru
```

---

## Первый запуск

### Вариант 1: Веб-интерфейс (самый простой)

```bash
# Активируйте окружение (если еще не активировано)
ollama_env\Scripts\activate  # Windows
# source ollama_env/bin/activate  # Linux/Mac

# Запустите веб-сервер
python main.py web

# Откройте в браузере
# http://localhost:5555
```

### Вариант 2: Загрузка писем из почты

```bash
# Активируйте окружение
ollama_env\Scripts\activate  # Windows

# Загрузите письма
python main.py parse

# Это может занять время (зависит от количества писем)

# Затем откройте веб
python main.py web
```

### Вариант 3: Проверка конфигурации

```bash
# Если что-то не работает
python debug_test.py

# Это проверит:
# ✅ Python версию
# ✅ Зависимости
# ✅ Конфигурацию
# ✅ IMAP подключение
# ✅ Сохранение файлов
```

---

## Установка Ollama (опционально)

Ollama позволяет использовать продвинутые языковые модели для анализа.

### Зачем Ollama?

- 📈 **Точность**: ⭐⭐⭐⭐⭐ вместо ⭐⭐⭐
- 🧠 **Понимание контекста**: лучше анализирует сложные письма
- 🛡️ **Локально**: все обрабатывается на вашем ПК

### Минусы

- 🐢 **Медленнее**: 5-7 писем/сек вместо 13+
- 💾 **Место**: Нужно ~8GB для моделей
- 🖥️ **Ресурсы**: Требует мощный ПК (8GB+ RAM)

### Установка Ollama

#### На Windows

1. Скачайте с https://ollama.ai
2. Запустите установщик
3. Откройте PowerShell и запустите:

```bash
ollama pull mistral:7b
# Это загрузит модель (~8GB)

# Запустите сервер
ollama serve
# Сервер будет на http://localhost:11434
```

#### На macOS

```bash
# Установите через brew
brew install ollama

# Загрузите модель
ollama pull mistral:7b

# Запустите сервер
ollama serve
```

#### На Linux

```bash
# Скачайте с https://ollama.ai
curl -fsSL https://ollama.ai/install.sh | sh

# Загрузите модель
ollama pull mistral:7b

# Запустите сервер
ollama serve
```

### Использование Ollama

#### В другом терминале, с активным Ollama сервером:

```bash
# Активируйте окружение Email Parser
ollama_env\Scripts\activate

# Используйте Ollama режим
python main.py reprocess --engine ollama

# Или комбинированный (рекомендуется)
python main.py reprocess --engine combined
```

### Альтернативные модели Ollama

```bash
ollama pull llama2              # Хороший баланс
ollama pull neural-chat         # Быстрая
ollama pull dolphin-mixtral     # Лучшая точность
```

---

## Решение проблем при установке

### Проблема 1: "Python не найден"

**Решение**:
```bash
# Проверьте установлен ли Python
python --version

# Если нет:
# Windows: Скачайте с https://www.python.org/downloads/
# Linux: sudo apt install python3
# macOS: brew install python3

# Перезагрузитесь после установки
```

### Проблема 2: "Permission denied" (Linux/Mac)

**Решение**:
```bash
# Дайте права на выполнение
chmod +x ollama_env/bin/activate

# Активируйте снова
source ollama_env/bin/activate
```

### Проблема 3: "pip: command not found"

**Решение**:
```bash
# Переустановите pip
python -m pip install --upgrade pip

# Или используйте python3
python3 -m pip install -r requirements.txt
```

### Проблема 4: "ModuleNotFoundError"

**Решение**:
```bash
# 1. Убедитесь, что окружение активировано
# Должно быть "(ollama_env)" в начале строки

# 2. Переустановите зависимости
pip install -r requirements.txt --force-reinstall

# 3. Если все еще не работает
pip install sentencepiece protobuf transformers torch
```

### Проблема 5: "IMAP Connection refused"

**Решение**:
```bash
# 1. Проверьте учетные данные в config.yaml
nano config.yaml

# 2. Убедитесь, что разрешен доступ к IMAP:
# Gmail: https://support.google.com/accounts/answer/185833
# Яндекс: Проверьте, включен ли IMAP в настройках
# Outlook: Может быть нужен App Password

# 3. Проверьте доступ в интернет
ping imap.gmail.com
```

### Проблема 6: "Port 5555 already in use"

**Решение**:
```bash
# Используйте другой порт
python main.py web --port 8080

# Или убейте процесс на старом порту
# Windows:
netstat -ano | findstr :5555
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :5555
kill -9 <PID>
```

### Проблема 7: "Out of memory"

**Решение**:
```bash
# Обработайте меньше писем
python main.py reprocess --only-missing

# Или используйте local-nn вместо Ollama
python main.py reprocess --engine local-nn

# Проверьте свободную память
# Windows: Ctrl+Shift+Esc -> Производительность
# Linux: free -h
# Mac: Activity Monitor
```

### Проблема 8: "CUDA out of memory" (с GPU)

**Решение**:
```bash
# Использует local-nn (не требует GPU)
python main.py reprocess --engine local-nn

# Или обновите NVIDIA драйверы
# https://www.nvidia.com/download/driverDetails.aspx
```

---

## Проверка успешной установки

Запустите команду:
```bash
python final_test.py
```

Должен вывести:
```
======================================================================
FINAL VERIFICATION TEST
======================================================================

[Test 1] Checking all imports...
  OK: All modules imported successfully

[Test 2] Checking config loading...
  OK: Config loaded (IMAP server: mail.nic.ru)

[Test 3] Checking regex functions...
  OK: Email and phone extraction working

[Test 4] Checking file scanning...
  OK: Found 132 sufficient files

[Test 5] Checking grouping...
  OK: Created 59 groups

======================================================================
ALL TESTS PASSED - SYSTEM IS OPERATIONAL
======================================================================
```

---

## Структура после установки

```
email_parser20/
├── ollama_env/              # Виртуальное окружение
│   ├── Scripts/             # Исполняемые файлы
│   ├── Lib/                 # Библиотеки Python
│   └── ...
├── scr/                     # Исходный код
│   ├── __init__.py
│   ├── imap_client.py
│   ├── ai_processor.py
│   ├── utils.py
│   └── __pycache__/
├── data/                    # Данные
│   ├── emails/              # Скачанные письма
│   ├── results/             # Результаты анализа
│   └── processed.json       # DB обработанных
├── main.py                  # Главный скрипт
├── config.yaml              # Конфигурация (отредактируйте!)
├── requirements.txt         # Зависимости
├── README.md                # Главный файл
├── DOCUMENTATION.md         # Полная документация
├── QUICK_REFERENCE.md       # Шпаргалка
├── EXAMPLES.md              # Примеры
└── INSTALLATION.md          # Этот файл
```

---

## 🎓 Что дальше?

После успешной установки:

1. 📖 Прочитайте [README.md](README.md) для обзора
2. 🚀 Запустите `python main.py web`
3. 🌐 Откройте http://localhost:5555
4. 📚 Смотрите [DOCUMENTATION.md](DOCUMENTATION.md) для подробностей
5. 💡 Смотрите [EXAMPLES.md](EXAMPLES.md) для примеров

---

## 🆘 Если что-то не работает

1. Запустите `python debug_test.py` для диагностики
2. Проверьте логи: `LOG_LEVEL=DEBUG python main.py web`
3. Прочитайте раздел "Решение проблем" выше
4. Проверьте [DOCUMENTATION.md](DOCUMENTATION.md) FAQ

---

**Успешной установки!** 🚀

Если возникли вопросы, смотрите полную документацию в [DOCUMENTATION.md](DOCUMENTATION.md)
