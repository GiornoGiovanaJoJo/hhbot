# Квичек по Настройке HH Bot

## ❓ ОПТИМАЛЬНЫЕ НАСТРОЙКИ

### 1️⃣ Используется MemoryStorage?

❌ **НО** - Вы потеряете данные при перезагрузке!

✅ **ДА** - установите Redis

```bash
# macOS
brew install redis
redis-server

# Linux
sudo apt-get install redis-server
redis-server

# Docker – рекомендуется
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### 2️⃣ Настройка файлов

```bash
# 1. Клонировать репо
 ngit clone https://github.com/GiornoGiovanaJoJo/hhbot.git
cd hhbot

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Скопировать и эредактировать .env
cp .env.example .env
# Открыть .env и заполнить:
# - TELEGRAM_BOT_TOKEN
# - HH_CLIENT_ID
# - HH_CLIENT_SECRET
# - FSM_STORAGE_TYPE=redis

# 4. Повторите список выполнимых фиксов
cat README_FIX_SUMMARY.md
```

### 3️⃣ ОБОВЛЕНИЕ main.py

> “📁 МИРНОЖНУ виде `FIX_INSTRUCTIONS.md`

**Недостаетя Как МИНИМУМ:**

1. MemoryStorage → RedisStorage
2. Адд retry-логика в `main()`
3. Окончи `setup_signal_handlers()`
4. Полная валидация в `config.py`

### 4️⃣ Тестирование

```bash
# Запустите бот
python main.py

# В логах должны быть:
# [✅] Base data initialized
# [✅] HH API client initialized
# [✅] Scheduler started
# [👋] Bot is ready to receive messages
```

### 5️⃣ ОТКЛЮЧЕННОМУ НОрМАЛТНО

```bash
# Одать Ctrl+C - Корректно активрзируется

# Логи:
# [INFO] Shutdown signal received...
# [INFO] Gracefully stopping bot...
# [INFO] Cleanup complete
```

## ♀️ ОБЩИЕ ОПОВОРЫ

**Вопрос:** Redis выбрана обязательно?

“: Для production да. Для разработки можете тровать Memory (с учетом минусов).

**Вопрос:** Команды для Конфиг?

“: `cat .env.example` и `cat FIX_INSTRUCTIONS.md`

## 📁 ДОПОЛНИТЕЛЬНОЕ

| Файл | Зачем |
|------|--------|
| `ANALYSIS_REPORT.md` | Нинаы всех проблем |
| `FIX_INSTRUCTIONS.md` | Найты кода для фиксов |
| `FIXES_CHANGELOG.md` | Осоисание поизведенных юменений |

---

**Мы рекомендуем ачень фиксы ОДНОВРОМЕННО для стабильности системы!** 🙏
