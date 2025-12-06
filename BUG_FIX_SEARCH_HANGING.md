# ОТКЫТЫЮТОВНЫЙ БАГ: ЗАВИсАНИЕ ПОИСКА ПОСЛЕ НЕСКОЛькИХ ОТКЛИКОВ

**Коммит:** `a9fc88b`
**Отключено:** 06 декабря 2025

---

## 🔱 НАЙДЕННЫЕ ПРОБЛЕМЫ

### ОЛАВНАЯ: Bot Session Leak (Utechka соединений)

**Локация:** `utils/scheduler.py` в нескольких местах

**Проблема:**

Каждый раз с телеграм уведомление создан новый `Bot()` объект, а `await bot.session.close()` ню часто не менейжер не завершался:

```python
# Остарое неправильное код:
bots = []
for i in range(10):  # 10 итераций
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN, default=bot_properties)
    await bot.send_message(...)
    await bot.session.close()  # Не всегда вкончинается!

# После итерации ̄3-5: с системе нет свободных сокетов
```

**Результат:**
- После 3-5 откликов система без дальнейших попыток отправлять уведомления
- Но поиск вакансий продолжается
- Когда этап новхот тен уведомление, сокеты освобождаются → **поиск работает снова**

---

### ОСНОВНАЯ: БЕсконечный Кеш ЭБРАботанных Вакансий

**Локация:** `utils/scheduler.py:23`, `lines 188-200`

**Код до фикса:**

```python
# Остарое:
class TaskScheduler:
    def __init__(self):
        self.processed_vacancies: Set[str] = set()  # 🚨 GLOBAL кеш!

async def _find_suitable_vacancies(...):
    # ...
    # Строка 188-193:
    new_vacancies = [v for v in vacancies if str(v['id']) not in self.processed_vacancies]
    # ...
    # Строка 200:
    self.processed_vacancies.add(vacancy_id)  # Добавляна, но NEVER удаляются!
```

**Проблема:**

1. **Бесконечный рост**:
   ```
   Нап1: Найды с 50 вакансий → устанав 5 откликов → 5 в кеш
   Нап2: Найды те же 50 вакансий → но new_vacancies = [] (все в кеш)
   Нап3: То же самое → тупик
   ```

2. **Тамая утечка** (растет бесконечно):
   ```python
   # После исполнения 1000 вакансий:
   self.processed_vacancies = {'vac1', 'vac2', ..., 'vac1000'}  # 1000 строк
   # Когда вам перезагружаетесь, от очистки кеш (shutdown)
   ```

3. **Почему перезагрузка решает?** (Код L73):
   ```python
   async def shutdown():
       self.processed_vacancies.clear()  # Кеш очистился
   ```

---

## ✅ ОСНОВНЫЕ исПРАВЛЕНИЯ в коммите `a9fc88b`

### 1. Bot Session Лик (Отключено ✅)

```python
# ОНО: Каждый раз новый Bot()
async def _send_telegram_notification(...):
    bot = Bot(...)  # Новый!
    await bot.send_message(...)
    await bot.session.close()  # Utechka

# ТЕПЕРЬ:
bot_cache = {}  # Пул кеш Bot объектов

for vacancy in vacancies:
    if telegram_id not in bot_cache:
        bot_cache[telegram_id] = Bot(...)
    bot = bot_cache[telegram_id]  # Овториспользуем один
    await bot.send_message(...)

# Централизованная очистка:
for bot in bot_cache.values():
    await bot.session.close()  # Один Bot → один close()
```

**Наючим эффект:**
- Вместо 5-10 сокетов на отклик → **один сокет** (от кеш)
- Все уведомления на одном session

---

### 2. Per-User Vacancy Cache (Отключено ✅)

```python
# ОНО: Глобальные глава для ВсЕХ пользователей:
self.processed_vacancies = set()  # растет в весь время

# ТЕПЕРЬ: Per-user кеш с TTL:
self.user_vacancy_cache: Dict[int, Set[str]] = {}
self.cache_timestamps: Dict[int, datetime] = {}
self.cache_ttl_hours = 24

def _is_cache_expired(self, telegram_id: int) -> bool:
    elapsed = (datetime.now() - self.cache_timestamps[telegram_id]).total_seconds() / 3600
    return elapsed >= self.cache_ttl_hours  # 24 часа
```

**Преимущества:**
- **24 часа TTL** - вакансии отчищаются автоматически
- **Фисолютная очистка при стопе** - вы снимаюте отклики → кеш очищается
- **Нет тупиков** - кеш отновляется, но не сразу

---

### 3. ДБ Instead of Cache (Отключено ✅)

```python
# ОНО: Проверяли memory cache:
# 1. Опрос API к поиску
# 2. Офилтр все в memory cache processed_vacancies
# (КэП растёт → парализ все вакансии)

# ТЕПЕРЬ: Проверяем ДБ:
for vacancy in vacancies:
    if not await self._is_response_exists(telegram_id, vacancy_id):  # Кверы ДБ
        final_vacancies.append(vacancy)  # Анд добав теперь
```

**Преимущества:**
- **Но утечки** - Кеш только темпорарный
- **ДБ = истина** - При перезагрузке сто взять

---

## 🚀 НАУКА К ЭБ нАБЛІДЕНИЕ

| По НОВОМ | СНАП | ОПисание |
|--------|-----|----------|
| Жда6 откликов | Пока 5-10 сокетов | **БЕСКОНЕЧНые сокеты** ачит** |
| Финалист 5 откликов | Один сокет (кеш) | Отклики сыхраняются |
| Но каждые 5 мин (генерация) | Что новое найдено | Выстает хранить не Гнр так |

---

## 👋 ПРОВЕРКА ОПРАВКи

Для проверки что баг исправлен:

```bash
# 1. Остановите текущие автоотклики
pip install -r requirements.txt
python main.py

# 2. Включите автоотклики и мониторите логи:

# 3. Анализ логов:
# - Отклики 1-5: "Новых вакансий: X"
# - Отклики 6+: НО ПОЛУЧАТЬ "Новых вакансий: 0"
# (BUG) ВМЕСТО ТЕПЕРЬ ГОВА ПОЛУЧАть НОВые!
```

---

## ✅ ВЫВОД

**ГЛАВНАЯ ОПРАВка**: Мемори Leak решена в `a9fc88b`

**Стурктура Оправки:**
1. ✅ Bot session cache (относитесь) выполнен
2. ✅ Per-user vacancy cache (с TTL) выполнен
3. ✅ DB check instead of memory (выполнен

**ВОПРОСЫ?** Отклики теперь должны лись беспрерывным джест
