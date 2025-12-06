"""
Модели данных и репозиторий для работы с базой данных SQLite
"""

import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pathlib import Path

import aiosqlite
from loguru import logger

from config import Config


class DatabaseRepository:
    """Репозиторий для работы с базой данных"""

    def __init__(self):
        self.db_path: Path = Config.DATA_DIR / "hh_bot.db"

    async def is_auto_response_active(self, telegram_id: int) -> bool:
        """Проверяет, запущены ли автоотклики для пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT auto_response_enabled
                FROM search_settings s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            row = await cursor.fetchone()
            return bool(row and row[0])

    async def set_auto_response_status(self, telegram_id: int, enabled: bool) -> None:
        """Включает или отключает автоотклики для пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем internal user_id
            cursor = await db.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Пользователь {telegram_id} не найден")
            user_id = row[0]

            # Обновляем флаг в search_settings
            await db.execute("""
                UPDATE search_settings
                SET auto_response_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (int(enabled), user_id))
            await db.commit()


    async def get_active_resume(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает данные активного резюме пользователя, либо None."""
        import json

        async with aiosqlite.connect(self.db_path) as db:
            # Ищем активное резюме
            cursor = await db.execute("""
                SELECT r.resume_data
                FROM resumes r
                JOIN users u ON r.user_id = u.id
                WHERE u.telegram_id = ? AND r.is_active = TRUE
                LIMIT 1
            """, (telegram_id,))
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])

            # Если нет активного, берём последнее по дате
            cursor = await db.execute("""
                SELECT r.resume_data
                FROM resumes r
                JOIN users u ON r.user_id = u.id
                WHERE u.telegram_id = ?
                ORDER BY r.updated_at DESC
                LIMIT 1
            """, (telegram_id,))
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])

            return None

    async def init_database(self) -> None:
        """Инициализация БД и создание таблиц"""
        # Внутри async def init_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            # … существующие CREATE TABLE …

            # Таблица логов активности
            await db.execute("""
                CREATE TABLE IF NOT EXISTS search_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    keywords TEXT,
                    area_id INTEGER,
                    area_name TEXT,
                    min_salary INTEGER,
                    max_salary INTEGER,
                    currency TEXT DEFAULT 'RUR',
                    experience TEXT,
                    employment_type TEXT,
                    schedule TEXT,
                    exclude_companies TEXT,
                    exclude_keywords TEXT,
                    min_match_score INTEGER DEFAULT 60,
                    cover_letter_template TEXT,
                    auto_response_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            await db.commit()

        async with aiosqlite.connect(self.db_path) as db:
            # Таблица настроек поиска
            await db.execute("""
                CREATE TABLE IF NOT EXISTS search_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    keywords TEXT,
                    area_id INTEGER,
                    area_name TEXT,
                    min_salary INTEGER,
                    max_salary INTEGER,
                    currency TEXT DEFAULT 'RUR',
                    experience TEXT,
                    employment_type TEXT,
                    schedule TEXT,
                    exclude_companies TEXT,
                    exclude_keywords TEXT,
                    min_match_score INTEGER DEFAULT 60,
                    cover_letter_template TEXT,
                    auto_response_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            # users
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # hh_profiles
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hh_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    hh_user_id TEXT,
                    email TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    profile_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            # resumes
            await db.execute("""
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    hh_resume_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    status TEXT,
                    is_active BOOLEAN DEFAULT FALSE,
                    resume_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            # остальные таблицы...
            # Таблица отправленных откликов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    vacancy_id INTEGER NOT NULL,
                    cover_letter TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            await db.commit()
        logger.info("База данных инициализирована")

    async def create_or_update_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> int:
        """Создание или обновление пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            if row:
                await db.execute("""
                    UPDATE users
                    SET username = ?, first_name = ?, last_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """, (username, first_name, last_name, telegram_id))
                user_id = row[0]
            else:
                cursor = await db.execute("""
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (telegram_id, username, first_name, last_name))
                user_id = cursor.lastrowid
            await db.commit()
            return user_id

    async def save_hh_profile(
        self,
        telegram_id: int,
        user_info: Dict[str, Any],
        resumes: List[Dict[str, Any]]
    ) -> None:
        """Сохранение профиля HH и резюме"""
        async with aiosqlite.connect(self.db_path) as db:
            # получаем internal user_id
            cursor = await db.execute(
                "SELECT id FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Пользователь {telegram_id} не найден")
            user_id = row[0]

            # hh_profiles
            await db.execute("""
                INSERT OR REPLACE INTO hh_profiles
                (user_id, hh_user_id, email, first_name, last_name, phone, profile_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id,
                str(user_info.get('id')),
                user_info.get('email'),
                user_info.get('first_name'),
                user_info.get('last_name'),
                user_info.get('phone'),
                json.dumps(user_info, ensure_ascii=False)
            ))

            # resumes
            for resume in resumes:
                await db.execute("""
                    INSERT OR REPLACE INTO resumes
                    (user_id, hh_resume_id, title, status, resume_data, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user_id,
                    str(resume['id']),
                    resume.get('title'),
                    resume.get('status', {}).get('name'),
                    json.dumps(resume, ensure_ascii=False)
                ))

            await db.commit()

    async def set_active_resume(self, telegram_id: int, resume_id: str) -> bool:
        """Установка активного резюме"""
        async with aiosqlite.connect(self.db_path) as db:
            # проверяем, есть ли резюме
            cursor = await db.execute("""
                SELECT r.hh_resume_id
                FROM resumes r
                JOIN users u ON r.user_id = u.id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            all_rows = await cursor.fetchall()
            logger.info(f"Resumes in DB for {telegram_id}: {all_rows}")

            # target
            cursor = await db.execute("""
                SELECT r.id
                FROM resumes r
                JOIN users u ON r.user_id = u.id
                WHERE u.telegram_id = ? AND r.hh_resume_id = ?
            """, (telegram_id, resume_id))
            target = await cursor.fetchone()
            if not target:
                return False

            # сбрасываем старые
            await db.execute("""
                UPDATE resumes
                SET is_active = FALSE
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
            """, (telegram_id,))
            # активируем новое
            cursor = await db.execute("""
                UPDATE resumes
                SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE hh_resume_id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
            """, (resume_id, telegram_id))
            await db.commit()
            return cursor.rowcount > 0

    # ... остальные методы ...

    async def log_activity(self, telegram_id: int, action: str, details: Optional[str] = None) -> None:
        """Лог активности"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            if not row:
                raise ValueError("User not found")
            user_id = row[0]
            await db.execute(
                "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, action, details)
            )
            await db.commit()

    async def save_user_settings(self, telegram_id: int, settings: Dict[str, Any]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            # 1) Находим internal user_id
            cur = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cur.fetchone()
            if not row:
                raise ValueError(f"User {telegram_id} not found")
            user_id = row[0]
            # 2) Сохраняем или обновляем настройки
            await db.execute("""
                INSERT OR REPLACE INTO search_settings
                (user_id, keywords, area_id, area_name, min_salary, max_salary,
                 currency, experience, employment_type, schedule,
                 exclude_companies, exclude_keywords, min_match_score,
                 cover_letter_template, auto_response_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id,
                settings.get('keywords'),
                settings.get('area_id'),
                settings.get('area_name'),
                settings.get('min_salary'),
                settings.get('max_salary'),
                settings.get('currency'),
                settings.get('experience'),
                settings.get('employment_type'),
                settings.get('schedule'),
                settings.get('exclude_companies'),
                settings.get('exclude_keywords'),
                settings.get('min_match_score'),
                settings.get('cover_letter_template'),
                settings.get('auto_response_enabled', False),
            ))
            await db.commit()

    async def get_user_settings(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("""
                SELECT s.keywords, s.area_id, s.area_name,
                       s.min_salary, s.max_salary, s.currency,
                       s.experience, s.employment_type, s.schedule,
                       s.exclude_companies, s.exclude_keywords,
                       s.min_match_score, s.cover_letter_template,
                       s.auto_response_enabled
                FROM search_settings s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return {
                'keywords': row[0],
                'area_id': row[1],
                'area_name': row[2],
                'min_salary': row[3],
                'max_salary': row[4],
                'currency': row[5],
                'experience': row[6],
                'employment_type': row[7],
                'schedule': row[8],
                'exclude_companies': row[9],
                'exclude_keywords': row[10],
                'min_match_score': row[11],
                'cover_letter_template': row[12],
                'auto_response_enabled': bool(row[13]),
            }

    async def get_today_stats(self, telegram_id: int) -> Dict[str, int]:
        """Возвращает статистику откликов за сегодня"""
        today = date.today().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем internal user_id
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            if not row:
                return {'today_count': 0, 'today_responses': []}
            user_id = row[0]

            # Сколько откликов сегодня
            cursor = await db.execute(
                "SELECT COUNT(*) FROM responses WHERE user_id = ? AND DATE(created_at) = ?",
                (user_id, today)
            )
            today_count = (await cursor.fetchone())[0] or 0

            return {
                'today_count': today_count,
                'today_responses': []
            }

    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Возвращает общую статистику пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем internal user_id
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            if not row:
                return {}
            user_id = row[0]

            # Сколько всего откликов
            cursor = await db.execute("SELECT COUNT(*) FROM responses WHERE user_id = ?", (user_id,))
            total_responses = (await cursor.fetchone())[0]

            # Сколько приглашений (ответов от работодателей)
            cursor = await db.execute("SELECT COUNT(*) FROM activity_logs WHERE user_id = ? AND action = 'invitation'", (user_id,))
            total_invitations = (await cursor.fetchone())[0]

            # Сколько успешных собеседований
            cursor = await db.execute("SELECT COUNT(*) FROM activity_logs WHERE user_id = ? AND action = 'interview'", (user_id,))
            successful_interviews = (await cursor.fetchone())[0]

            # Коэффициент отклика = успешных собеседований / откликов * 100
            response_rate = int(successful_interviews / total_responses * 100) if total_responses > 0 else 0

            # Дата регистрации (минимальная запись activity_logs или users.created_at)
            cursor = await db.execute("SELECT MIN(created_at) FROM activity_logs WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            registration_date = row[0] if row and row[0] else None

            # Последний отклик (максимальная дата в responses)
            cursor = await db.execute("SELECT MAX(created_at) FROM responses WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            last_response = row[0] if row and row[0] else None

            return {
                'total_responses': total_responses,
                'total_invitations': total_invitations,
                'successful_interviews': successful_interviews,
                'response_rate': response_rate,
                'registration_date': registration_date,
                'last_response': last_response
            }


# Глобальный экземпляр
db_repository = DatabaseRepository()
