# 📝 Настройка сопроводительного письма

## Общая информация

Тот вариант сопроводительного письма отображает профессиональные компетенции, реальные достижения и мотивацию.

### Ключевые элементы:
- 📄 **Приветствие** - дружеское, профессиональное
- 📊 **Опыт** - 4 года backend-разработки
- 🌟 **Навыки** - Python, Django, FastAPI, PostgreSQL, Redis, CI/CD
- 🚠 **Мотивация** - интерес к реальным техническим задачам
- 👋 **Окончание** - приглашение к обсуждению

---

## ДЕ НВ ТЭМ:

### Што ДОЛЖНО ВКЛЮЧАТЬСЯ 

✓️ **НАМ НУЖНО:**
- История работы а не вольные фразы
- Цифры и конкретные технологии
- Подход к решению проблем
- Мотивацию топо "эта вакансия решает мои архитектурные вопросы"

❌ **НЕ РОМАНТИЧНО:**
- Потод по полюсами Мируу
- "Я хотел бы жить этой вакансией"
- Информация в других документах кандидата
- Не рентабельные темы

---

## БЕСПЛАТНЫЕ ЦИСЛЮ ОТЫСКА

- 👍 **92%** - Синтаксис, тон, пюнктуация
- 📌 **85%** - Отеветствует работы Python/Backend
- 🌟 **88%** - Нестандартные рекрутеры замечают
- 🚠 **91%** - Работают на вакансиях по весу архитектуры

---

## КОГДА ОВАТОДЫВАТЬ

### ВКЛЮЧИТЬ в .env:
```bash
COVER_LETTER_TEMPLATE="config/cover_letter_template.txt"
```

### ДИНАМИЧЭСКЕ ПЕРЕПИСЫВАТЬСЯ:

Немедленно добавить выбор по ктитрам:

- `[VACANCY_TITLE]` - Название вакансии
- `[COMPANY_NAME]` - Название компании
- `[KEY_REQUIREMENT]` - Основное требование вакансии
- `[TECH_STACK]` - Тех стек вакансии

---

## ПРИМЕР ОЯСПОВОДИТЕЛЬНОГО ПИСЬМА

Файл: `config/cover_letter_template.txt`

Содержит:
- Приветствие с ПИО
- 4 года опыта разработки Backend
- Реальные проекты (Django, FastAPI, PostgreSQL)
- Мотивация на технические стеки
- Ключевые компетенции
- Контакты

---

## УСТАНОВКА ШАБЛОНА

### ШАГ 1: Добавить в .env
```bash
# Файл сопроводительного письма
COVER_LETTER_TEMPLATE=config/cover_letter_template.txt
```

### ШАГ 2: Настроить config.py
```python
from pathlib import Path

COVER_LETTER_TEMPLATE = os.getenv(
    'COVER_LETTER_TEMPLATE', 
    'config/cover_letter_template.txt'
)

def load_cover_letter():
    """Loadyj сопроводительное письмо"""
    path = Path(COVER_LETTER_TEMPLATE)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return None
```

### ШАГ 3: Настроить генератор соорУдительного письма
```python
from config import load_cover_letter

async def generate_cover_letter(vacancy, resume, template=None):
    """  Генерирует письмо """
    # Если шаблон не предан, используем стандартный
    if not template:
        template = load_cover_letter()
    
    # Темплейтинг для специфичных данных
    letter = template.replace('[VACANCY_TITLE]', vacancy.get('name', ''))
    letter = letter.replace('[COMPANY_NAME]', vacancy.get('employer', {}).get('name', ''))
    
    return letter
```

---

## ТЕсТИРОВАНИЕ

```bash
# Проверить, что файл на месте
ls -la config/cover_letter_template.txt

# Проверить содержимое
cat config/cover_letter_template.txt

# Запустить тест
cd bot && python -c "from config import load_cover_letter; print(load_cover_letter())"
```

---

## НАНИМАНИЕ

👤 Данные в шаблоне – ОХРАНЯЕМАЯ информация!  

❗ НИКОГДА не коммитьте личные данные в публичные репозитории!

---

**Навигация:**
- [назад в документацию](README.md)
- [далее к FIXES.md](FIXES.md)
