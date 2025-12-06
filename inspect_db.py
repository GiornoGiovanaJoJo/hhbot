#!/usr/bin/env python3
# inspect_db.py

import sqlite3
import os
import sys
import json

def inspect_db(db_path: str, telegram_id: int):
    if not os.path.exists(db_path):
        print(f"Ошибка: файл БД не найден по пути {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1) Получаем internal user_id
    cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    if not row:
        print(f"Пользователь с telegram_id={telegram_id} не найден.")
        conn.close()
        return
    internal_user_id = row[0]

    # 2) Выводим настройки
    print("Настройки поиска:")
    cur.execute("""
        SELECT keywords, area_id, area_name,
               min_salary, max_salary, currency,
               experience, employment_type, schedule,
               exclude_companies, exclude_keywords,
               min_match_score, cover_letter_template,
               auto_response_enabled
        FROM search_settings
        WHERE user_id = ?
    """, (internal_user_id,))
    settings = cur.fetchone()
    if not settings:
        print("  Нет сохранённых настроек.")
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
        settings_dict["auto_response_enabled"] = bool(settings_dict["auto_response_enabled"])
        print(json.dumps(settings_dict, ensure_ascii=False, indent=4))

    # 3) Выводим отклики
    print("\nResponses:")
    cur.execute(
        "SELECT vacancy_id, created_at FROM responses WHERE user_id = ?",
        (internal_user_id,)
    )
    rows = cur.fetchall()
    if not rows:
        print("  Нет записей об откликах.")
    else:
        for vacancy_id, created_at in rows:
            print(f"  Вакансия {vacancy_id} — отклик отправлен {created_at}")

    conn.close()

if __name__ == "__main__":
    default_db = os.path.join("data", "hh_bot.db")
    if len(sys.argv) < 2:
        print("Использование: python inspect_db.py <telegram_id> [<путь_к_бд>]")
        sys.exit(1)

    telegram_id = int(sys.argv[1])
    db_path = sys.argv[2] if len(sys.argv) >= 3 else default_db

    inspect_db(db_path, telegram_id)
