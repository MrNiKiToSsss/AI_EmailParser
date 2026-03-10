"""Веб-интерфейс для просмотра писем с группировкой по компании/товару/ФИО"""

import json
import os
import time
from io import BytesIO

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
app = Flask(__name__, template_folder=TEMPLATES_DIR)

app.config["DATA_FOLDER"] = os.environ.get("RESULTS_DIR", os.path.join(BASE_DIR, "results"))
os.makedirs(app.config["DATA_FOLDER"], exist_ok=True)


def safe_lower(value):
    """Безопасное преобразование в нижний регистр для строк и списков"""
    if isinstance(value, str):
        return value.lower()
    elif isinstance(value, list):
        return [item.lower() if isinstance(item, str) else str(item).lower() for item in value]
    elif value is None:
        return ""
    return str(value).lower()


def is_sufficient(info: dict) -> bool:
    """
    Фильтр "достаточно обработанных" писем.
    
    ТРЕБУЕТ наличие компании!
    На сайт попадают только те записи, где указана компания,
    и есть хотя бы контакт (email/телефон) или ФИО.
    """
    company = str(info.get("company") or "").strip()
    full_name = str(info.get("full_name") or "").strip()

    emails = info.get("emails") or []
    if isinstance(emails, list):
        has_email = any(str(e).strip() for e in emails)
    else:
        has_email = bool(str(emails).strip())

    phones = info.get("phones") or []
    if isinstance(phones, list):
        has_phone = any(str(p).strip() for p in phones)
    else:
        has_phone = bool(str(phones).strip())

    def _is_default(s: str) -> bool:
        s_low = s.lower()
        return s_low in ("", "не указано", "не найдено")

    # Обязательно наличие компании
    has_company = not _is_default(company)
    if not has_company:
        return False
    
    # И хотя бы контакт или имя
    return has_email or has_phone or not _is_default(full_name)

def get_file_info(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return {
                    'full_name': f"Не JSON: {os.path.basename(filepath)}",
                    'company': "Не удалось распарсить",
                    'position': "Проверьте формат файла",
                    'emails': [],
                    'phones': [],
                    'product': "",
                    'raw_content': content
                }
            
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    data = {"content": data}
            
            # Извлекаем информацию с проверкой типов
            full_name = data.get('full_name') or data.get('Full_name') or data.get('fullName') or 'Не указано'
            company = data.get('company') or data.get('Company') or 'Не указано'
            position = data.get('position') or data.get('Position') or 'Не указано'
            product = data.get('product') or data.get('Product') or 'Не найдено'
            
            # Если поля не найдены пытаемся извлечь данные из любого места
            if full_name == 'Не указано':
                for key, value in data.items():
                    if 'name' in key.lower() and (isinstance(value, str) or isinstance(value, list)):
                        full_name = value
                        break
            
            # Обеспечиваем что emails и phones списки
            emails = data.get('emails', [])
            if not isinstance(emails, list):
                emails = [emails] if emails else []
                
            phones = data.get('phones', [])
            if not isinstance(phones, list):
                phones = [phones] if phones else []
            
            return {
                'full_name': full_name,
                'company': company,
                'position': position,
                'emails': emails,
                'phones': phones,
                'product': product,
                'raw_content': content
            }
    except Exception as e:
        print(f"Ошибка чтения {filepath}: {str(e)}")
        return {
            'full_name': f"Ошибка: {os.path.basename(filepath)}",
            'company': "Не удалось прочитать",
            'position': "Проверьте формат файла",
            'emails': [],
            'phones': [],
            'product': "Не найдено",
            'raw_content': str(e)
        }

def group_files_by_attribute(files: list) -> list:
    """
    Группирует письма по компании/товару/ФИО.
    Возвращает список групп с письмами внутри.
    """
    groups = {}
    
    for file in files:
        # Приоритет: компания > товар > ФИО
        company = str(file.get('company', '') or '').strip()
        product = str(file.get('product', '') or '').strip()
        full_name = str(file.get('full_name', '') or '').strip()
        
        def _is_default(s: str) -> bool:
            s_low = s.lower()
            return s_low in ("", "не указано", "не найдено")
        
        # Выбираем первый неEmpty атрибут
        if not _is_default(company):
            group_key = f"company:{company.lower()}"
            group_name = f"🏢 {company}"
        elif not _is_default(product):
            group_key = f"product:{product.lower()}"
            group_name = f"📦 {product}"
        elif not _is_default(full_name):
            group_key = f"name:{full_name.lower()}"
            group_name = f"👤 {full_name}"
        else:
            continue  # Пропускаем файл без признаков группировки
        
        if group_key not in groups:
            groups[group_key] = {
                "group_name": group_name,
                "group_type": group_key.split(':')[0],
                "files": []
            }
        
        groups[group_key]["files"].append(file)
    
    # Сортируем: сначала по типу (company > product > name), потом по количеству файлов
    type_order = {"company": 0, "product": 1, "name": 2}
    grouped_list = sorted(
        groups.values(),
        key=lambda g: (type_order.get(g['group_type'], 999), -len(g['files']))
    )
    
    return grouped_list


_SCAN_CACHE = {"ts": 0.0, "files": []}
_SCAN_TTL_S = 3.0


def scan_folder(force: bool = False):
    """Сканирование папки с лёгким кешем (ускоряет поиск/экспорт на больших объёмах)."""
    now = time.time()
    if not force and _SCAN_CACHE["files"] and (now - _SCAN_CACHE["ts"] < _SCAN_TTL_S):
        return _SCAN_CACHE["files"]

    files = []
    try:
        for filename in os.listdir(app.config["DATA_FOLDER"]):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(app.config["DATA_FOLDER"], filename)
            file_info = get_file_info(filepath)
            if not is_sufficient(file_info):
                # Недостаточно обработанное письмо — не показываем на сайте
                continue
            files.append(
                {
                    "filename": filename,
                    "path": filepath,
                    **file_info,
                }
            )
    except Exception as e:
        print(f"Ошибка сканирования папки: {e}")
        files = []

    _SCAN_CACHE["ts"] = now
    _SCAN_CACHE["files"] = files
    return files

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files')
def list_files():
    files = scan_folder()
    grouped = group_files_by_attribute(files)
    return jsonify(grouped)

@app.route('/search')
def search_files():
    query = request.args.get('q', '').lower().strip()
    if not query:
        return jsonify([])
    
    results = []
    for file in scan_folder():
        # Безопасный поиск по всем полям
        fields_to_search = [
            safe_lower(file['full_name']),
            safe_lower(file['company']),
            safe_lower(file['position']),
            safe_lower(file['emails']),
            safe_lower(file['product']),
            safe_lower(file['phones'])
        ]
        
        # Проверяем все варианты
        found = False
        for field in fields_to_search:
            if isinstance(field, list):
                if any(query in item for item in field):
                    found = True
                    break
            else:
                if query in field:
                    found = True
                    break
        
        if found:
            results.append(file)
    
    # Группируем результаты поиска
    grouped = group_files_by_attribute(results)
    return jsonify(grouped)

@app.route('/file/<filename>')
def get_file(filename):
    try:
        # защита от path traversal
        base = os.path.abspath(app.config["DATA_FOLDER"])
        filepath = os.path.abspath(os.path.join(base, filename))
        if not filepath.startswith(base + os.sep):
            return jsonify({"error": "invalid filename"}), 400

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            try:
                return jsonify(json.loads(content))
            except:
                return jsonify({"raw_content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/export')
def export_to_excel():
    query = request.args.get('q', '').lower().strip()
    files = scan_folder()
    
    # Фильтрация данных по запросу (аналогично поиску)
    if query:
        filtered_files = []
        for file in files:
            fields_to_search = [
                safe_lower(file['full_name']),
                safe_lower(file['company']),
                safe_lower(file['position']),
                safe_lower(file['emails']),
                safe_lower(file['product']),
                safe_lower(file['phones'])
            ]
            found = False
            for field in fields_to_search:
                if isinstance(field, list):
                    if any(query in item for item in field):
                        found = True
                        break
                else:
                    if query in field:
                        found = True
                        break
            if found:
                filtered_files.append(file)
    else:
        filtered_files = files
    
    # Подготовка данных для экспорта
    export_data = []
    for file in filtered_files:
        # Преобразование списков в строки
        try:
            emails_val = file.get("emails", [])
            emails = ", ".join(emails_val) if isinstance(emails_val, list) else str(emails_val or "")
        except Exception:
            emails = ""

        try:
            phones_val = file.get("phones", [])
            phones = ", ".join(phones_val) if isinstance(phones_val, list) else str(phones_val or "")
        except Exception:
            phones = ""

        export_data.append({
            'Файл': file['filename'],
            'Полное имя': file['full_name'],
            'Компания': file['company'],
            'Должность': file['position'],
            'Emails': emails,
            'Телефоны': phones,
            "Интересуемый продукт": file["product"],
            'Содержимое': file.get('raw_content', '')
        })
    
    # Создание Excel-файла в памяти
    df = pd.DataFrame(export_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Данные')
    
    output.seek(0)
    
    # Отправка файла пользователю
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='exported_data.xlsx'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=False)