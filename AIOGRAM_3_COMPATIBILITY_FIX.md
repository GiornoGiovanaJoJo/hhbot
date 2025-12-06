# 🔐 Aiogram 3.x Compatibility Fixes

## ⚠️ Problem

If you see this error:

```
ImportError: cannot import name 'TelegramError' from 'aiogram.exceptions'
Did you mean: 'TelegramAPIError'?
```

This means your code is written for **aiogram 2.x** but you have **aiogram 3.x** installed.

---

## 🚀 Quick Fix

### Step 1: Find all occurrences

**In VSCode (Ctrl+H):**
```
Find:    from aiogram.exceptions import TelegramError
Replace: from aiogram.exceptions import TelegramAPIError
```

**In PowerShell:**
```powershell
Select-String -Path main.py -Pattern "TelegramError" -AllMatches
```

### Step 2: Replace in code

**Find and replace all instances:**
```python
# WRONG (aiogram 2.x)
except TelegramError as e:
    logger.error(f"Telegram error: {e}")

# CORRECT (aiogram 3.x)
except TelegramAPIError as e:
    logger.error(f"Telegram error: {e}")
```

### Step 3: Update imports

```python
# At the top of main.py, change:
from aiogram.exceptions import TelegramError

# To:
from aiogram.exceptions import TelegramAPIError
```

### Step 4: Test

```bash
python main.py
```

---

## 📄 Complete Aiogram 2.x → 3.x Migration

### Import Changes

| aiogram 2.x | aiogram 3.x | Notes |
|-------------|-------------|-------|
| `from aiogram import Bot, Dispatcher` | `from aiogram import Bot, Router` | Dispatcher → Router |
| `from aiogram.types import Message` | `from aiogram.types import Message` | ✅ Same |
| `from aiogram.exceptions import TelegramError` | `from aiogram.exceptions import TelegramAPIError` | ❌ CHANGED |
| `from aiogram.utils.exceptions_handler` | N/A (use middleware) | ❌ REMOVED |
| `from aiogram.dispatcher import FSMContext` | `from aiogram.fsm.context import FSMContext` | ❌ CHANGED |
| `from aiogram.contrib.fsm_storage.memory import MemoryStorage` | `from aiogram.fsm.storage.memory import MemoryStorage` | ❌ CHANGED |
| `from aiogram.contrib.fsm_storage.redis import RedisStorage` | `from aiogram.fsm.storage.redis import RedisStorage` | ❌ CHANGED |

### Code Changes

#### Exception Handling

**Aiogram 2.x:**
```python
from aiogram.exceptions import TelegramError

try:
    await bot.send_message(...)
except TelegramError as e:
    logger.error(f"Telegram error: {e}")
```

**Aiogram 3.x:**
```python
from aiogram.exceptions import TelegramAPIError

try:
    await bot.send_message(...)
except TelegramAPIError as e:
    logger.error(f"Telegram error: {e}")
```

#### FSM Storage

**Aiogram 2.x:**
```python
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage

storage = MemoryStorage()
# or
storage = RedisStorage(host='localhost')
```

**Aiogram 3.x:**
```python
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

storage = MemoryStorage()
# or
storage = RedisStorage(redis=redis_client)
```

#### Dispatcher

**Aiogram 2.x:**
```python
from aiogram import Bot, Dispatcher
from aiogram.utils import executor

dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    await message.reply("Hello!")

if __name__ == '__main__':
    executor.start_polling(dp)
```

**Aiogram 3.x:**
```python
from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Dispatcher

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()

@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.answer("Hello!")

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 📚 Common Error Messages

### 1. TelegramError

```
ImportError: cannot import name 'TelegramError' from 'aiogram.exceptions'
Did you mean: 'TelegramAPIError'?
```

**Solution:**
```python
from aiogram.exceptions import TelegramAPIError

try:
    await bot.send_message(...)
except TelegramAPIError as e:
    logger.error(f"Error: {e}")
```

### 2. MessageNotModified

```
ImportError: cannot import name 'MessageNotModified' from 'aiogram.exceptions'
```

**Solution:**
```python
from aiogram.exceptions import TelegramBadRequest

try:
    await bot.edit_message_text(...)
except TelegramBadRequest as e:
    if "message is not modified" in str(e):
        logger.info("Message not modified")
```

### 3. FSMContext location

```
ImportError: cannot import name 'FSMContext' from 'aiogram.dispatcher'
```

**Solution:**
```python
from aiogram.fsm.context import FSMContext

@router.message()
async def handler(message: Message, state: FSMContext):
    await state.set_data({"key": "value"})
```

### 4. Dispatcher storage

```
ImportError: cannot import name 'MemoryStorage' from 'aiogram.contrib.fsm_storage.memory'
```

**Solution:**
```python
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Dispatcher

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
```

---

## ✅ Testing the Fix

### Test 1: Import Test

```bash
python -c "from aiogram.exceptions import TelegramAPIError; print('✓ Import works')"
```

### Test 2: Bot Start

```bash
python main.py
```

You should see:
```
✓ Bot started
✓ Connected to Telegram
```

### Test 3: Send Message in Telegram

Send `/start` to your bot → Should get a response

---

## 📚 Reference Links

- [Aiogram 3.x Migration Guide](https://docs.aiogram.dev/en/latest/guide/getting-started/)
- [Aiogram 3.x Documentation](https://docs.aiogram.dev/)
- [Aiogram Exceptions](https://docs.aiogram.dev/en/latest/api/exceptions/)
- [GitHub Aiogram Issues](https://github.com/aiogram/aiogram/issues)

---

## 🚨 Prevention for Future

### Pin Aiogram Version

Update `requirements.txt` to specify aiogram version:

```txt
aiogram==3.9.0
# Instead of:
# aiogram  (no version = latest)
```

### Add Version Check

Add to `main.py`:

```python
import aiogram

required_version = "3.0.0"
if aiogram.__version__ < required_version:
    raise RuntimeError(
        f"Aiogram {required_version}+ required. "
        f"You have {aiogram.__version__}. "
        f"Run: pip install --upgrade aiogram"
    )
```

---

## ❓ FAQ

**Q: Should I downgrade to aiogram 2.x?**
A: No, aiogram 3.x is newer and better. Fix your code instead.

**Q: Will these changes break aiogram 2.x?**
A: Yes, use the compatibility layer below.

**Q: Can I support both versions?**
A: Yes, use this:

```python
try:
    from aiogram.exceptions import TelegramAPIError as TelegramError
except ImportError:
    from aiogram.exceptions import TelegramError

# Now use TelegramError in your code
```

**Q: What about other changes?**
A: Most are similar. Search for the import path in the [official docs](https://docs.aiogram.dev/).

---

**Status**: 😟 Fixed  
**Last Updated**: December 6, 2025  
**Tested With**: aiogram 3.9.0
