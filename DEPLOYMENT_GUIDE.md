# 🚀 Deployment Guide - HH Bot

Полное руководство по развертыванию HH Bot в production окружении.

## 📋 Требования

- Docker & Docker Compose (рекомендуется для production)
- Python 3.12+ (если запускать без Docker)
- Redis 7+ (обязательно для production)
- Telegram Bot Token
- HeadHunter API credentials

## 🐳 Развертывание с Docker (РЕКОМЕНДУЕТСЯ)

### 1. Подготовка

```bash
# Клонируйте репозиторий
git clone https://github.com/GiornoGiovanaJoJo/hhbot.git
cd hhbot

# Создайте .env файл
cp .env.example .env

# Отредактируйте .env с вашими credentials
vim .env
```

### 2. Запуск с Docker Compose

```bash
# Запустите все сервисы (Redis + Bot)
docker-compose up -d

# Проверьте статус
docker-compose ps

# Смотрите логи
docker-compose logs -f bot

# Остановите сервис
docker-compose down
```

### 3. Проверка здоровья

```bash
# Проверьте, что Redis работает
docker-compose exec redis redis-cli ping

# Проверьте логи бота
docker-compose logs bot | tail -50

# Проверьте подключение
docker-compose exec bot python -c "import main; print('OK')"
```

## 🐍 Развертывание с Python (для разработки)

### 1. Установка зависимостей

```bash
# Установите Python 3.12 или выше
python --version  # должен быть 3.12+

# Установите requirements
pip install -r requirements.txt
```

### 2. Настройка Redis

```bash
# На Linux/Mac с Homebrew
brew install redis
brew services start redis

# На Linux
sudo apt-get install redis-server
sudo systemctl start redis-server

# На Windows - используйте Docker или WSL2
# docker run -d -p 6379:6379 redis:7-alpine
```

### 3. Запуск бота

```bash
# Убедитесь в наличии .env
cp .env.example .env
vim .env  # отредактируйте credentials

# Запустите бота
python main.py

# Или с логированием
python main.py &
tail -f logs/hh_bot.log
```

## ✅ Проверка после развертывания

### 1. Тестирование в Telegram

```
1. Откройте Telegram
2. Найдите вашего бота (@YourBotName)
3. Отправьте команду /start
4. Должно появиться приветственное сообщение
```

### 2. Проверка логов

```bash
# Docker
docker-compose logs bot | grep -i error

# Python
tail -f logs/hh_bot.log | grep -i error
```

### 3. Проверка подключения к HH API

```bash
# Docker
docker-compose exec bot python inspect_settings.py

# Python
python inspect_settings.py
```

### 4. Проверка БД

```bash
# Docker
docker-compose exec bot python inspect_db.py

# Python
python inspect_db.py
```

## 🔒 Production рекомендации

### Безопасность

- ✅ Используйте Redis с паролем:
  ```bash
  redis-cli CONFIG SET requirepass "YOUR_STRONG_PASSWORD"
  ```

- ✅ Обновите REDIS_PASSWORD в .env

- ✅ Используйте firewall для Redis (не открывайте 6379 в интернет)

- ✅ Регулярно ротируйте Telegram token

- ✅ Логируйте доступ админов

### Мониторинг

- ✅ Настройте алерты на ошибки в Telegram (ADMIN_CHAT_ID)

- ✅ Мониторьте использование памяти

- ✅ Проверяйте Redis на чистоту памяти

- ✅ Ротируйте логи файлы

### Backup

```bash
# Бэкапируйте БД
docker-compose exec bot sqlite3 database/hhbot.db ".dump" > backup.sql

# Бэкапируйте Redis
docker-compose exec redis redis-cli BGSAVE
docker cp hhbot-redis:/data/dump.rdb ./redis-backup.rdb
```

## 🐛 Решение проблем

### Redis не подключается

```bash
# Проверьте статус Redis
docker-compose exec redis redis-cli ping

# Проверьте логи
docker-compose logs redis

# Перезагрузите Redis
docker-compose restart redis
```

### Бот не отвечает на команды

```bash
# Проверьте токен
grep TELEGRAM_BOT_TOKEN .env

# Проверьте логи
docker-compose logs bot | tail -50

# Перезагрузите бота
docker-compose restart bot
```

### Нет памяти на диске

```bash
# Проверьте место
df -h

# Очистите старые логи
docker-compose exec bot rm logs/hh_bot.log.*.gz

# Проверьте размер БД
docker-compose exec bot ls -lh database/
```

## 📊 Масштабирование

### Для большого числа пользователей

1. **Используйте Redis Sentinel** для высокой доступности
2. **Настройте отдельный Redis сервер** (не в контейнере)
3. **Используйте Load Balancer** если нужно несколько инстансов
4. **Настройте Database replication**

```yaml
# Пример redis-compose для production
services:
  redis-master:
    image: redis:7
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
  
  redis-replica:
    image: redis:7
    command: redis-server --slaveof redis-master 6379
```

## 🔄 Обновление

### Обновите код

```bash
git pull origin main
```

### Обновите dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Перестройте Docker образ

```bash
docker-compose build --no-cache
docker-compose up -d
```

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте [PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md)
2. Посмотрите [USAGE_GUIDE.md](USAGE_GUIDE.md)
3. Откройте issue на GitHub
4. Свяжитесь с автором: kbootovsk@gmail.com

---

**Последнее обновление:** 22 декабря 2025  
**Версия:** 1.0  
**Статус:** Production Ready ✅
