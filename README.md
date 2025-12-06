# 🤖 HH Bot - HeadHunter Auto-Recruiting Bot

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Active-brightgreen.svg)]()

Auto-recruiting bot for HeadHunter using Telegram to manage job applications and auto-responders.

## 🍐 Features

- 🤖 **Telegram Bot Interface** - Control everything from Telegram
- 📄 **Auto Responses** - Automatically respond to applicants
- 🔍 **Job Search** - Monitor new vacancies matching your criteria
- 💾 **FSM State Management** - Async conversation states with Memory or Redis
- 📊 **Logging** - Comprehensive logging with rotation
- 🚪 **Redis Support** - Optional Redis for distributed state management
- 💡 **Async/Await** - Modern Python async patterns with aiogram

## ⚠️  Security First

**Important:** This repository uses `.env.example` as a template. Your actual `.env` file:
- ✅ Should NEVER be committed to Git
- ✅ Should NEVER be shared publicly
- ✅ Should be protected in `.gitignore`
- ✅ Should contain real credentials only on your machine

[See Security Setup Guide](SECURITY_SETUP.md) for detailed instructions.

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/GiornoGiovanaJoJo/hhbot.git
cd hhbot
```

### 2. Create `.env` File

```bash
cp .env.example .env
```

**Edit `.env` and add your credentials:**

```env
# Get from @BotFather in Telegram
TELEGRAM_BOT_TOKEN=your_token_here

# Get from https://dev.hh.ru/admin/applications
HH_CLIENT_ID=your_client_id
HH_CLIENT_SECRET=your_client_secret

# Your Telegram Chat ID (from @userinfobot)
ADMIN_CHAT_ID=your_chat_id
```

[Need detailed setup? See setup instructions](SECURITY_SETUP.md)

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

```bash
python main.py
```

### 5. Test in Telegram

Send `/start` command to your bot - it should respond!

## 📄 Documentation

### Getting Started
- [Quick Start Guide](SECURITY_SETUP.md) - Setup .env and credentials
- [.env Setup Instructions](.env.setup_instructions.txt) - Quick reference
- [.env Example](.env.example) - All available configuration options

### Understanding the Project
- [QUICK_START.md](QUICK_START.md) - Step-by-step setup instructions
- [Architecture Overview](ANALYSIS_REPORT.md) - How everything works
- [Configuration Guide](ENV_SETUP_GUIDE.md) - Detailed .env documentation

### Troubleshooting
- [Problems & Solutions](PROBLEMS_AND_SOLUTIONS.md) - Common issues and fixes
- [Usage Guide](USAGE_GUIDE.md) - How to use the bot

## 💻 Project Structure

```
hhbot/
├── bot/                    # Bot handlers and commands
├── hh_api/                 # HeadHunter API client
├── database/               # Database models and queries
├── matching/               # Job matching logic
├── utils/                  # Utility functions
├── main.py                 # Bot entry point
├── config.py               # Configuration from .env
├── requirements.txt        # Python dependencies
├── .env.example            # Configuration template
├── .gitignore              # Ignore .env and artifacts
├─═ SECURITY_SETUP.md       # 🔐 Security guide (REQUIRED READING)
├─═ README.md               # This file
├─═ QUICK_START.md          # Setup instructions
├─═ ENV_SETUP_GUIDE.md      # Detailed .env guide
├─═ PROBLEMS_AND_SOLUTIONS.md # Troubleshooting
├─═ USAGE_GUIDE.md          # How to use
├─═ ANALYSIS_REPORT.md      # Technical analysis
├═ logs/                   # Application logs
├═ data/                   # Data files
├═ database/               # Database files
├═ .gitignore              # 🔐 NEVER commit .env
├═ hh_bot.log             # Application log file
└── __pycache__/            # Python cache (ignored)
```

## 🔑 Setting Up Credentials

### Telegram Bot Token

1. Open Telegram and find **@BotFather**
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the token you receive
5. Add to `.env`: `TELEGRAM_BOT_TOKEN=<token>`

[Detailed Telegram setup →](SECURITY_SETUP.md#-step-3-get-your-credentials)

### HeadHunter Credentials

1. Go to https://dev.hh.ru/admin/applications
2. Sign in with your HeadHunter account
3. Create a new application
4. Copy Client ID and Client Secret
5. Add to `.env`:
   ```env
   HH_CLIENT_ID=<your_id>
   HH_CLIENT_SECRET=<your_secret>
   ```

[Detailed HH setup →](SECURITY_SETUP.md#option-b-headhunter-credentials)

## 🚨 Security Checklist

Before running the bot:

- [ ] `.env` file created from `.env.example`
- [ ] All credentials filled in (Telegram, HeadHunter)
- [ ] `.gitignore` contains `.env`
- [ ] Ran `git log --all -- .env` (returns nothing)
- [ ] `.env` is NOT staged for commit
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Bot runs without errors: `python main.py`

[Full security checklist →](SECURITY_SETUP.md#-security-checklist)

## ⚠️  If Token Gets Compromised

**If someone gains access to your token:**

1. **IMMEDIATELY** revoke it in @BotFather
2. Create a new token
3. Update `.env` with new token
4. Restart the bot

[Emergency procedures →](SECURITY_SETUP.md#-emergency-token-leaked)

## 📋 Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram bot token from @BotFather | `123456789:ABCD...` |
| `HH_CLIENT_ID` | ✅ | HeadHunter app Client ID | `ab12cd34ef...` |
| `HH_CLIENT_SECRET` | ✅ | HeadHunter app Client Secret | `ab12cd34ef...` |
| `HH_REDIRECT_URI` | ✅ | OAuth callback URL | `http://localhost:8000/auth/callback` |
| `ADMIN_CHAT_ID` | ⚠️ | Your Telegram Chat ID | `123456789` |
| `FSM_STORAGE_TYPE` | ❌ | memory or redis | `memory` |
| `LOG_LEVEL` | ❌ | DEBUG, INFO, WARNING, ERROR | `INFO` |
| `LOG_FILE` | ❌ | Log file path | `hh_bot.log` |

[See all variables →](.env.example)

## 🛠️ Installation Troubleshooting

### Python version
```bash
# Check Python version (need 3.8+)
python --version
```

### Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# If issues with async:
pip install aiogram>=3.0.0
```

### Redis (optional)
```bash
# Linux/Mac with Homebrew
brew install redis
redis-server

# Docker
docker run -d -p 6379:6379 redis:latest
```

[More troubleshooting →](PROBLEMS_AND_SOLUTIONS.md)

## 🚀 Running the Bot

### Basic startup
```bash
python main.py
```

### With logging
```bash
python main.py &
tail -f hh_bot.log
```

### With debug logging
```bash
LOG_LEVEL=DEBUG python main.py
```

### Using different .env
```bash
export $(cat .env.production | xargs)
python main.py
```

## 📑 Usage

### Commands
- `/start` - Initialize bot
- `/help` - Show available commands
- `/status` - Check bot status
- `/config` - Show current configuration

[Full command list →](USAGE_GUIDE.md)

## 📧 Common Issues

### "TELEGRAM_BOT_TOKEN not set"
- Check `.env` file exists
- Make sure `TELEGRAM_BOT_TOKEN=...` is there
- Run: `grep TELEGRAM_BOT_TOKEN .env`

### "ModuleNotFoundError: No module named 'bot'"
- Run: `pip install -r requirements.txt`
- Check Python path is correct

### "HH API authentication failed"
- Verify HH_CLIENT_ID and HH_CLIENT_SECRET in .env
- Check redirect URI matches on dev.hh.ru

[All issues & solutions →](PROBLEMS_AND_SOLUTIONS.md)

## 🕣 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📚 License

MIT License - see LICENSE file

## 📄 Additional Resources

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Aiogram Documentation](https://aiogram.dev/)
- [HeadHunter API](https://dev.hh.ru/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

## 💆 Support

Having issues? Check these in order:

1. [Quick Start →](QUICK_START.md)
2. [Security Setup →](SECURITY_SETUP.md)
3. [Problems & Solutions →](PROBLEMS_AND_SOLUTIONS.md)
4. [Usage Guide →](USAGE_GUIDE.md)

## 🚀 You're Ready!

```bash
# 1. Setup
cp .env.example .env
# Edit .env with your credentials

# 2. Install
pip install -r requirements.txt

# 3. Run
python main.py

# 4. Test in Telegram
# Send /start to your bot
```

---

**Created:** December 2025  
**Status:** 🚨 Active Development  
**Python:** 3.8+  
**License:** MIT  

퉪️ **Remember: Keep your `.env` file SAFE and NEVER commit it to Git!** 퉪️
