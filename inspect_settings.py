#!/usr/bin/env python3
# inspect_settings.py

import sqlite3
import os
import sys
import json

def inspect_settings(db_path: str, telegram_id: int):
    if not os.path.exists(db_path):
        print(f"Ошибка: файл БД не найден по пути {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Получаем internal user_id
    cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    if not row:
        print(f"Пользователь с telegram_id={telegram_id} не найден в таблице users.")
        conn.close()
        return
    user_id = row[0]

    # Проверяем наличие записи в search_settings
    cur.execute("""
        SELECT keywords, area_id, area_name,
               min_salary, max_salary, currency,
               experience, employment_type, schedule,
               exclude_companies, exclude_keywords,
               min_match_score, cover_letter_template,
               auto_response_enabled
        FROM search_settings
        WHERE user_id = ?
    """, (user_id,))
    settings = cur.fetchone()
    if not settings:
        print("Настройки поиска для этого пользователя не найдены.")
    else:
        keys = [
            "keywords", "area_id", "area_name",
            "min_salary", "max_salary", "currency",
            "experience", "employment_type", "schedule",
            "exclude_companies", "exclude_keywords",
            "min_match_score", "cover_letter_template",
            "auto_response_enabled"
        ]
        settings_dict = dict(zip(keys, settings))
        # Преобразуем булево значение
        settings_dict["auto_response_enabled"] = bool(settings_dict["auto_response_enabled"])
        print("Текущие настройки поиска:")
        print(json.dumps(settings_dict, ensure_ascii=False, indent=4))

    conn.close()

if __name__ == "__main__":
    # Путь к файлу БД относительно корня проекта
    default_db = os.path.join("data", "hh_bot.db")
    # Получить telegram_id из аргументов командной строки
    if len(sys.argv) < 2:
        print("Использование: python inspect_settings.py <telegram_id> [<путь_к_бд>]")
        sys.exit(1)

    tg_id = int(sys.argv[1])
    db_path = sys.argv[2] if len(sys.argv) >= 3 else default_db

    inspect_settings(db_path, tg_id)
