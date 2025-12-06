# Нинструкции по исправлению main.py

## Главные исправления, которые нужно внести

### 1. Замена MemoryStorage на RedisStorage

**Текущий код (main.py, строка 49):**
```python
storage = MemoryStorage()
```

**Оисправленный код:**
```python
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

async def create_bot() -> tuple[Bot, Dispatcher]:
    """Создание и настройка бота"""
    
    # Проверка конфигурации
    config_errors = Config.validate_config()
    if config_errors:
        logger.error(f"Ошибки конфигурации: {', '.join(config_errors)}")
        raise ValueError(f"Некорректная конфигурация: {', '.join(config_errors)}")

    # Инициализация бота с новым синтаксисом aiogram 3.7+
    bot_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN, default=bot_properties)

    # Инициализация хранилища FSM в зависимости от конфигурации
    if Config.FSM_STORAGE_TYPE == 'redis':
        redis = Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )
        storage = RedisStorage(redis=redis)
        logger.info("🔴 Redis хранилище инициализировано")
    else:
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
        logger.warning("⚠️ Используется MemoryStorage - состояния будут потеряны при перезагрузке!")

    # ... остальной код
```

### 2. Добавление retry-логики для polling

**Замените функцию `main()`:**

```python
async def main() -> None:
    """Основная функция запуска с восстановлением при ошибках"""
    global bot_instance, dp_instance

    try:
        # Настройка логирования
        setup_logger()
        logger.info("📝 Логирование настроено")

        # Настройка обработчиков сигналов
        setup_signal_handlers()

        # Создание бота и диспетчера
        logger.info("⚙️ Создаем экземпляры бота и диспетчера...")
        bot, dp = await create_bot()
        bot_instance, dp_instance = bot, dp

        # Регистрация событий жизненного цикла
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Запуск polling с retry-логикой
        logger.info("📡 Запускаем polling...")
        logger.info("🎯 Бот готов принимать сообщения!")

        retry_count = 0
        max_retries = 5
        retry_delay = 5

        while True:
            try:
                await dp.start_polling(bot, skip_updates=True)
            except TelegramError as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.critical(f"💀 Не удалось переподключиться после {max_retries} попыток")
                    raise
                
                logger.error(f"❌ Ошибка Telegram API (попытка {retry_count}/{max_retries}): {e}")
                logger.info(f"⏳ Ожидание {retry_delay} секунд перед переподключением...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 60)  # Exponential backoff, макс 60 сек
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.critical(f"💀 Непредвиденная ошибка: {e}")
                    raise
                
                logger.error(f"❌ Непредвиденная ошибка (попытка {retry_count}/{max_retries}): {e}")
                await asyncio.sleep(retry_delay)

    except KeyboardInterrupt:
        logger.info("⚠️ Получен сигнал прерывания (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка в main(): {e}")
        raise
    finally:
        logger.info("🏁 Завершение основной функции...")
```

### 3. Исправление signal_handler

**Замените функцию `setup_signal_handlers()`:**

```python
def setup_signal_handlers() -> None:
    """Настройка обработчиков сигналов для корректного завершения"""
    def signal_handler(signum, frame):
        logger.info(f"🛑 Получен сигнал {signum}, начинаем корректное завершение...")
        # Корректно завершаем event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Создаем задачу для корректного завершения
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(on_shutdown(bot_instance))
            )
        else:
            # Если loop не запущен, просто выходим
            sys.exit(0)

    if sys.platform != 'win32':
        # На Unix-подобных системах используем стандартные сигналы
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:
        # На Windows используем альтернативный подход
        # Обработка Ctrl+C в run_bot()
        pass
```

### 4. Добавление проверки импорта логирования

**Добавьте в начало main.py:**

```python
from aiogram.exceptions import TelegramError
import traceback
```

## 📋 Чек-лист для внесения изменений

- [ ] Обновить imports в начале main.py
- [ ] Заменить MemoryStorage на RedisStorage
- [ ] Добавить retry-логику в main()
- [ ] Исправить setup_signal_handlers()
- [ ] Заменить requirements.txt (✅ уже сделано)
- [ ] Создать .env.example (✅ уже создан)
- [ ] Протестировать запуск бота

## 🧪 Тестирование

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Скопировать и настроить .env
cp .env.example .env
# Отредактировать .env с актуальными данными

# 3. Если используется Redis, запустить Redis
redis-server
# или через Docker
docker run -d -p 6379:6379 redis:7-alpine

# 4. Запустить бота
python main.py
```

## ⚙️ Использование Redis

Для production-среды рекомендуется использовать Redis:

```bash
# Установка Redis (macOS)
brew install redis
redis-server

# Установка Redis (Linux)
sudo apt-get install redis-server
redis-server

# Установка Redis (Docker)
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

Измените в .env:
```
FSM_STORAGE_TYPE=redis
REDIS_HOST=localhost
REDIS_PORT=6379
```
