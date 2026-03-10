# Email Parser 2.0 - Примеры использования

## 📖 Содержание

1. [Базовые примеры](#базовые-примеры)
2. [Сценарии использования](#сценарии-использования)
3. [Интеграция с инструментами](#интеграция-с-инструментами)
4. [Python API](#python-api)
5. [Автоматизация](#автоматизация)

---

## Базовые примеры

### Пример 1: Первый запуск (веб-интерфейс)

```bash
cd email_parser20

# Запустить веб-сервер
python main.py web

# В браузере откройте: http://localhost:5555
```

**Что будет**:
- Веб-страница с интерфейсом
- Список всех обработанных писем
- Поиск и фильтрация
- Экспорт в Excel

---

### Пример 2: Загрузка писем из почты

```bash
# 1. Отредактируйте config.yaml с вашей почтой
nano config.yaml

# 2. Загрузите письма
python main.py parse

# 3. Откройте веб-интерфейс
python main.py web
```

**Что происходит внутри**:
1. Подключается к IMAP серверу
2. Скачивает все письма из INBOX
3. Сохраняет их как .eml файлы
4. Анализирует каждое письмо
5. Сохраняет результаты как .json

**Результаты**:
- Папка `data/emails/` - содержит .eml файлы
- Папка `data/results/` - содержит .json файлы с анализом
- Файл `data/processed.json` - БД обработанных писем

---

### Пример 3: Переобработка с другим движком

```bash
# Синтаксис
python main.py reprocess --engine <ENGINE>

# Примеры
python main.py reprocess --engine local-nn      # Локальная нейросеть
python main.py reprocess --engine ollama        # Ollama (если установлена)
python main.py reprocess --engine combined      # Оба миода (рекомендуется)
```

---

### Пример 4: Обновление только новых писем

```bash
# Быстрое добавление только новых
python main.py reprocess --only-missing

# Это не переобработает уже имеющиеся файлы
# Намного быстрее, чем переработка всего
```

---

## Сценарии использования

### Сценарий A: Компания получает много писем через одну почту

**Задача**: Автоматически извлекать контакты и данные о компаниях из входящих писем

**Решение**:
```bash
# День 1: Первичная загрузка
python main.py parse --engine combined
python main.py web

# Каждый день/неделю: Обновить новые письма
python main.py reprocess --only-missing
```

**Результат**:
- CRM система заполнена контактами из писем
- Автоматическое извлечение компаний и продуктов
- Веб-интерфейс для просмотра

---

### Сценарий B: Архивирование старых писем

**Задача**: Обработать архив в 10,000 писем

**Решение**:
```bash
# 1. Скопируйте .eml файлы в data/emails/
cp /archive/*.eml ./data/emails/

# 2. Переработайте все письма
python main.py reprocess --engine local-nn

# 3. Экспортируйте результаты
# Откройте веб и кликните "Export to Excel"
```

**Параметры для большого объема**:
- Используйте `local-nn` (быстрее)
- Обработает 10,000 писем за ~15 минут
- Память использует минимально

---

### Сценарий C: Интеграция с CRM

**Задача**: Отправлять извлеченные контакты в CRM (Salesforce, Pipedrive, etc.)

**Решение** (Python скрипт):
```python
import json
import requests
from pathlib import Path

RESULTS_DIR = Path('./data/results')
CRM_API_URL = 'https://api.crm.example.com/contacts'
CRM_API_KEY = 'your-api-key'

# Получить все результаты
for json_file in RESULTS_DIR.glob('*.json'):
    with open(json_file) as f:
        contact = json.load(f)
    
    # Отправить в CRM
    data = {
        'name': contact['full_name'],
        'company': contact['company'],
        'emails': contact['emails'],
        'phones': contact['phones'],
        'position': contact['position'],
    }
    
    response = requests.post(
        CRM_API_URL,
        json=data,
        headers={'Authorization': f'Bearer {CRM_API_KEY}'}
    )
    
    if response.ok:
        print(f"✅ {contact['full_name']} отправлен в CRM")
    else:
        print(f"❌ Ошибка: {response.text}")
```

**Запуск**:
```bash
python importer_to_crm.py
```

---

### Сценарий D: Мониторинг качества анализа

**Задача**: Проверить точность анализа на выборке

**Решение**:
```bash
# 1. Обработайте пример писем
python main.py reprocess --engine local-nn --only-missing

# 2. Проверьте качество
python test_analyzer.py

# 3. Если не устраивает точность - использьте Ollama
python main.py reprocess --engine ollama
```

---

### Сценарий E: Поиск по всем письмам

**Задача**: Найти все письма от компании "Амплифер"

**Решение 1: Веб-интерфейс**
```
Откройте http://localhost:5555
Введите "Амплифер" в поле поиска
```

**Решение 2: API**
```bash
curl "http://localhost:5555/search?q=Амплифер"
```

**Решение 3: Python скрипт**
```python
import json
from pathlib import Path

RESULTS_DIR = Path('./data/results')
SEARCH_QUERY = 'Амплифер'

for json_file in RESULTS_DIR.glob('*.json'):
    with open(json_file) as f:
        contact = json.load(f)
    
    company = str(contact.get('company', '')).lower()
    if SEARCH_QUERY.lower() in company:
        print(f"✅ {json_file.stem}: {contact['full_name']} - {contact['company']}")
```

**Запуск**:
```bash
python search_contacts.py
```

---

## Интеграция с инструментами

### Интеграция с Zapier (автоматизация)

```
1. Trigger: Email received
2. Action: Save email as file
3. Trigger Email Parser: Process file
4. Action: Send results to Sheet/CRM
```

**Webhook URL**:
```
POST http://your-server:5555/process
Content-Type: application/json

{
  "email_text": "Привет, интересует CRM...",
  "from": "ivan@mail.com"
}
```

---

### Интеграция с Google Sheets

```python
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import gspread
import json
from pathlib import Path

# Аутентификация
gc = gspread.service_account(filename='credentials.json')
sh = gc.open('Email Contacts')
ws = sh.sheet1

# Загрузить результаты
for json_file in Path('./data/results').glob('*.json'):
    with open(json_file) as f:
        data = json.load(f)
    
    # Добавить строку в Google Sheet
    ws.append_row([
        data['full_name'],
        ','.join(data['emails']),
        ','.join(data['phones']),
        data['company'],
        data['position'],
        data['product']
    ])
```

---

### Интеграция с Telegram ботом

```python
import telebot
from pathlib import Path
import json
from datetime import datetime

bot = telebot.TeleBot('YOUR-TOKEN')
RESULTS_DIR = Path('./data/results')

@bot.message_handler(commands=['stats'])
def get_stats(message):
    # Подсчет контактов
    if RESULTS_DIR.exists():
        files = list(RESULTS_DIR.glob('*.json'))
        companies = set()
        contacts = []
        
        for f in files[:10]:  # Last 10
            with open(f) as jf:
                data = json.load(jf)
                companies.add(data.get('company', ''))
                contacts.append(data.get('full_name', ''))
        
        text = f"""
📊 Статистика:
- Обработано писем: {len(files)}
- Компаний: {len(companies)}
- Последние контакты: {', '.join(contacts[:5])}
"""
        bot.send_message(message.chat.id, text)

bot.polling()
```

---

## Python API

### Использование as library

```python
from scr.imap_client import reprocess_local_emails
from main import analyze_email_local_nn, load_config
from pathlib import Path

# Загрузить конфиг
config = load_config(Path('config.yaml'))

# Переобработать все письма
reprocess_local_emails(
    config,
    callback=analyze_email_local_nn,
    only_missing=True
)
```

---

### Анализ отдельного письма

```python
from main import analyze_email_local_nn
import json

config = {
    "local_nn": {"model": "Davlan/xlm-roberta-base-ner-hrl"}
}

email_text = """
Привет!
Интересует ваша CRM система.
Контакт: Иван Петров
Email: ivan@mail.com
Телефон: +7-999-123-45-67
Компания: ООО Амплифер
"""

# Анализировать
result_json = analyze_email_local_nn(email_text, config)
result = json.loads(result_json)

print(f"Имя: {result['full_name']}")
print(f"Компания: {result['company']}")
print(f"Email: {result['emails']}")
print(f"Продукт: {result['product']}")
```

---

### Чтение результатов

```python
import json
from pathlib import Path

RESULTS_DIR = Path('./data/results')

# Получить результат конкретного письма
with open(RESULTS_DIR / '123.json') as f:
    data = json.load(f)

print(data)
# {
#     "full_name": "Иван Петров",
#     "emails": ["ivan@mail.com"],
#     "phones": ["+7-999-123-45-67"],
#     "company": "ООО Амплифер",
#     "position": "Менеджер",
#     "product": "CRM"
# }
```

---

## Автоматизация

### Ежедневное обновление (cron)

**Linux/macOS**:
```bash
# Отредактировать crontab
crontab -e

# Добавить строку (запуск каждый день в 9 утра)
0 9 * * * cd /home/user/email_parser20 && python main.py reprocess --only-missing >> /var/log/email_parser.log 2>&1
```

---

### Еженедельная обработка архива

```bash
#!/bin/bash
# weekly_archive.sh

cd ~/email_parser20

# Скопировать новые письма из архива
cp ~/mail_archive/2024/*.eml ./data/emails/

# Обработать новые письма
python main.py reprocess --only-missing

# Экспортировать результаты
# (добавьте скрипт экспорта)

# Отправить уведомление
echo "Weekly processing complete" | mail -s "Email Parser" admin@company.com
```

**Запуск по расписанию**:
```bash
chmod +x weekly_archive.sh
# В crontab:
0 6 * * 0 ~/weekly_archive.sh  # Каждое воскресенье в 6 утра
```

---

### Docker контейнер (опционально)

```dockerfile
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py", "web"]
```

**Запуск**:
```bash
docker build -t email-parser .
docker run -p 5555:5555 -v ./data:/app/data email-parser
```

---

### REST API wrapping

```python
from flask import Flask, request, jsonify
from main import analyze_email_local_nn
import json

app = Flask(__name__)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    email_text = data.get('text', '')
    
    if not email_text:
        return jsonify({'error': 'No text provided'}), 400
    
    config = {
        "local_nn": {"model": "Davlan/xlm-roberta-base-ner-hrl"}
    }
    
    result_json = analyze_email_local_nn(email_text, config)
    result = json.loads(result_json)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=False, port=8000)
```

**Использование**:
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, интересует CRM. Иван. ivan@mail.com"}'
```

---

## Метрики и мониторинг

### Команда для сбора статистики

```python
import json
from pathlib import Path
from collections import Counter

RESULTS_DIR = Path('./data/results')

companies = []
emails_list = []
phones_list = []
products = []

for json_file in RESULTS_DIR.glob('*.json'):
    with open(json_file) as f:
        data = json.load(f)
        
        if data.get('company'):
            companies.append(data['company'])
        emails_list.extend(data.get('emails', []))
        phones_list.extend(data.get('phones', []))
        if data.get('product'):
            products.append(data['product'])

print("📊 Статистика:")
print(f"Всего писем: {len(list(RESULTS_DIR.glob('*.json')))}")
print(f"Уникальных компаний: {len(set(companies))}")
print(f"Email адресов: {len(set(emails_list))}")
print(f"Номеров телефонов: {len(set(phones_list))}")
print(f"Упомянутых продуктов: {len(set(products))}")
print("\nТоп-10 компаний:")
for company, count in Counter(companies).most_common(10):
    print(f"  {company}: {count}")
```

---

## Примеры результатов

### Пример анализа письма 1

**Входящее письмо**:
```
Subject: Интересует CRM система

Здравствуйте!

Называюсь Иван Петров, работаю в компании ООО "Амплифер".
Должность - Менеджер по продажам.

Интересует ваша CRM система с интеграцией 1С.
Нужны возможности аналитики и дашборд.

Мой контакт:
Email: Ivan.Petrov@amplifier1.ru
Телефон: +7 (999) 123-45-67

С увважением,
Иван
```

**Результат анализа**:
```json
{
  "full_name": "Иван Петров",
  "company": "ООО \"Амплифер\"",
  "emails": ["Ivan.Petrov@amplifier1.ru"],
  "phones": ["+7 (999) 123-45-67"],
  "position": "Менеджер по продажам",
  "product": "CRM система с интеграцией 1С"
}
```

---

### Пример анализа письма 2

**Входящее письмо**:
```
Привет,

Нужна автоматизация наших бизнес-процессов.
Слышали про ваш ERP. Можно ли задать вопросы?

Спасибо,
Александр
ООО ТехРешения
```

**Результат анализа**:
```json
{
  "full_name": "Александр",
  "company": "ООО ТехРешения",
  "emails": [],
  "phones": [],
  "position": "Не указано",
  "product": "ERP система"
}
```

> ✅ Даже неполные письма анализируются!

---

**Конец примеров. Надеемся, что эти примеры помогли вам!** 🚀

