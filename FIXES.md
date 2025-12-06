# 🔧 Основные исправления ошибок

**Дата**: 2025-12-06  
**Версия**: 1.1

---

## Ошибка: `'>=' not supported between instances of 'NoneType' and 'int'`

### Проблема

Ошибка возникала в двух местах:

1. **`database/repository.py`**: Отсутствовал метод `get_today_stats()`
2. **`utils/scheduler.py`**: Метод `_get_today_responses_count()` возвращал `None`, а не интегер

Трассировка ошибки:
```
AttributeError: 'DatabaseRepository' object has no attribute 'get_today_stats'
ERROR: '>=' not supported between instances of 'NoneType' and 'int'
```

### Решение

#### 1. добавлен метод `get_today_stats()` в DatabaseRepository

```python
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
```

#### 2. Обновлен метод `_get_today_responses_count()` в scheduler.py

```python
async def _get_today_responses_count(self, telegram_id: int) -> Optional[int]:
    """Получение количества откликов за сегодня"""
    try:
        stats = await db_repository.get_today_stats(telegram_id)
        return stats.get('today_count', 0)
    except Exception as e:
        logger.error(f"Ошибка получения статистики тодая: {e}")
        return None
```

#### 3. добавлен None-check в `_validate_user_conditions()` и `_send_responses()`

```python
# В _validate_user_conditions:
today_count = await self._get_today_responses_count(telegram_id)
if today_count is None:
    logger.warning(f"today_count вернул None для пользователя {telegram_id}, используем 0")
    today_count = 0

max_responses = getattr(Config, 'MAX_RESPONSES_PER_DAY', 20)
if today_count >= max_responses:
    # ...
```

То же самое в `_send_responses()` перед логикой отправки.

---

## Ошибка: `AttributeError: 'DatabaseRepository' object has no attribute 'get_today_stats'`

### Решение

Добавлен метод `get_today_stats()` в `database/repository.py` - см. выше.

---

## Проверка исправления

Открытые комиты:

1. `87e9a57` - добавлен `get_today_stats()` в DatabaseRepository
2. `880ef04` - добавлен None-check в scheduler.py

### До пуска бота:

```bash
# Проверьте обновления
git pull origin main

# Перезагружение навоесяся с .выс файлами
pip install --force-reinstall -e .

# Остановите старые процессы бота
pkill -f "python -m bot.main"

# Пустите бот снова
python -m bot.main
```

---

## Онтология ошибок

| Но | Ошибка | Модуль | Оригинал | На | Статус |
|----|---------|--------|---------|---|--------|
| 1 | `'>=' not supported between NoneType and int` | `utils/scheduler.py:346` | `today_count >= max_responses` | Нон-чек | ✅ Фиксед |
| 2 | `AttributeError: no attribute 'get_today_stats'` | `bot/handlers/main.py:540` | `db_repository.get_today_stats()` | Новый метод | ✅ Фиксед |
| 3 | `today_count вроется None` | `utils/scheduler.py` | `_get_today_responses_count()` | Обновлен | ✅ Фиксед |

---

## Логи выполнения

### Ожидаемые мессажи логов:

**НОМАЛЬНО:**
```
2025-12-06 15:36:57 | INFO | utils.scheduler:_validate_user_conditions:187 | today_count вернул число, поскольку проверка None работает
```

**Если это стало ПН:**
```
2025-12-06 15:36:57 | ERROR | utils.scheduler:_validate_user_conditions:189 | today_count вернул None для пользователя, используем 0
```

---

## Относятся к:

- Книга `PROBLEMS_AND_SOLUTIONS.md` - рассмотрено в Проблеме #3
- Книга `ENV_SETUP_GUIDE.md` - рассмотрено в виолациях базы данных
