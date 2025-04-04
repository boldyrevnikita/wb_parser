import re
import json
from datetime import datetime

def clean_text(text):
    """Очищает текст от лишних пробелов и специальных символов"""
    if not text:
        return ""
    # Удаляем HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    # Заменяем множественные пробелы и переносы строк на один пробел
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_price(price_value):
    """Форматирует цену в числовой формат"""
    if not price_value:
        return 0
    
    if isinstance(price_value, (int, float)):
        return float(price_value)
    
    # Удаляем все нечисловые символы, кроме точки
    price_str = re.sub(r'[^\d.]', '', str(price_value))
    try:
        return float(price_str)
    except ValueError:
        return 0

def save_to_json(data, filename):
    """Сохраняет данные в JSON-файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_from_json(filename):
    """Загружает данные из JSON-файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def format_datetime(dt):
    """Форматирует дату и время в строку"""
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt