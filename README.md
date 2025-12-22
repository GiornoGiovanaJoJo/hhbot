# 🤖 HH Bot - HeadHunter Auto-Recruiting Bot

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](Dockerfile)
[![Tests](https://img.shields.io/badge/tests-included-green.svg)](tests/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)]()

Auto-recruiting bot for HeadHunter using Telegram to manage job applications and auto-responders.

## ✨ What's New

### 🚀 Version 1.0 - Production Ready
- ✅ **Comprehensive Test Suite** - Unit tests with pytest
- ✅ **CI/CD Pipeline** - Automated testing on GitHub Actions
- ✅ **Docker Support** - Production-ready Docker images
- ✅ **Redis Required** - Mandatory for reliability and scaling
- ✅ **Deployment Guide** - Complete deployment documentation
- ✅ **Security Hardened** - Non-root Docker user, health checks

## 🍐 Features

- 🤖 **Telegram Bot Interface** - Control everything from Telegram
- 📄 **Auto Responses** - Automatically respond to applicants
- 🔍 **Job Search** - Monitor new vacancies matching your criteria
- 💾 **FSM State Management** - Async conversation states with Redis
- 📊 **Logging** - Comprehensive logging with rotation
- 🐳 **Docker & Compose** - Easy deployment with Docker
- 🧪 **Full Test Coverage** - Automated testing
- 🔄 **CI/CD Pipeline** - GitHub Actions integration
- 💪 **Production Ready** - Health checks, monitoring, security

## ⚠️ Security First

**Important:** This repository uses `.env.example` as a template. Your actual `.env` file:
- ✅ Should NEVER be committed to Git
- ✅ Should NEVER be shared publicly
- ✅ Should be protected in `.gitignore`
- ✅ Should contain real credentials only on your machine

[See Security Setup Guide](SECURITY_SETUP.md) for detailed instructions.

## 🚀 Quick Start

### Option 1: Docker (Recommended for Production)

```bash
# Clone repository
git clone https://github.com/GiornoGiovanaJoJo/hhbot.git
cd hhbot

# Setup environment
cp .env.example .env
vim .env  # Edit with your credentials

# Run with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f bot
```

[See Deployment Guide →](DEPLOYMENT_GUIDE.md)

### Option 2: Python (For Development)

```bash
# Clone repository
git clone https://github.com/GiornoGiovanaJoJo/hhbot.git
cd hhbot

# Create .env file
cp .env.example .env
vim .env  # Edit with your credentials

# Install dependencies
pip install -r requirements.txt

# Make sure Redis is running
# Linux: sudo systemctl start redis-server
# Mac: brew services start redis
# Docker: docker run -d -p 6379:6379 redis:7-alpine

# Run the bot
python main.py
```

## 📋 Requirements

- **Docker** (for containerized deployment)
- **Python 3.8+** (for direct execution)
- **Redis 7+** (mandatory for state management)
- **Telegram Bot Token** (from @BotFather)
- **HeadHunter API Credentials** (from dev.hh.ru)

## 📚 Documentation

### Quick References
- [🚀 Deployment Guide](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [🔐 Security Setup](SECURITY_SETUP.md) - Credentials and security
- [📖 Quick Start](QUICK_START.md) - Step-by-step setup
- [🆘 Troubleshooting](PROBLEMS_AND_SOLUTIONS.md) - Common issues
- [📖 Usage Guide](USAGE_GUIDE.md) - Bot commands and usage

### Technical Documentation
- [📊 Architecture](ANALYSIS_REPORT.md) - How everything works
- [⚙️ Configuration](ENV_SETUP_GUIDE.md) - Environment variables
- [🧪 Testing](tests/) - Test suite and examples

## 🔑 Setting Up Credentials

### Telegram Bot Token

1. Open Telegram and find **@BotFather**
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the token you receive
5. Add to `.env`: `TELEGRAM_BOT_TOKEN=<token>`

[Detailed Telegram setup →](SECURITY_SETUP.md)

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

[Detailed HH setup →](SECURITY_SETUP.md)

## 💻 Project Structure

```
hhbot/
├── bot/                        # Bot handlers and commands
├── hh_api/                     # HeadHunter API client
├── database/                   # Database models
├── matching/                   # Job matching logic
├── utils/                      # Utility functions
├── tests/                      # 🆕 Unit tests
│   ├── __init__.py
│   └── test_matching.py
├── .github/workflows/          # 🆕 CI/CD Pipeline
│   └── tests.yml
├── main.py                     # Bot entry point
├── config.py                   # Configuration
├── Dockerfile                  # 🆕 Docker image
├── docker-compose.yml          # 🆕 Docker Compose
├── requirements.txt            # Python dependencies
├── pytest.ini                  # 🆕 Test configuration
├── .env.example                # Configuration template
├── .gitignore                  # 🔐 Ignore .env
├── DEPLOYMENT_GUIDE.md         # 🆕 Complete deployment guide
├── SECURITY_SETUP.md           # Security guide
├── QUICK_START.md              # Setup instructions
├── PROBLEMS_AND_SOLUTIONS.md   # Troubleshooting
├── USAGE_GUIDE.md              # How to use
└── README.md                   # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_matching.py::TestJobMatching::test_salary_range_matching -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run with output
pytest tests/ -s -v
```

## 🔄 CI/CD Pipeline

Every commit automatically runs:
- ✅ Unit tests (Python 3.8-3.12)
- ✅ Code linting (flake8, black, isort)
- ✅ Security checks (bandit, safety)
- ✅ Docker build verification
- ✅ Coverage reports

## 🐳 Docker

### Build Image
```bash
docker build -t hhbot:latest .
```

### Run Container
```bash
docker run -d \
  --name hhbot \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e HH_CLIENT_ID=your_id \
  -e HH_CLIENT_SECRET=your_secret \
  -e ADMIN_CHAT_ID=your_chat_id \
  --link redis:redis \
  hhbot:latest
```

### Docker Compose (Recommended)
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

[See Deployment Guide →](DEPLOYMENT_GUIDE.md)

## 📊 Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram bot token | `123456789:ABCD...` |
| `HH_CLIENT_ID` | ✅ | HeadHunter app ID | `ab12cd34ef...` |
| `HH_CLIENT_SECRET` | ✅ | HeadHunter app secret | `ab12cd34ef...` |
| `HH_REDIRECT_URI` | ✅ | OAuth callback URL | `http://localhost:8000` |
| `ADMIN_CHAT_ID` | ⚠️ | Your Telegram Chat ID | `123456789` |
| `REDIS_HOST` | ❌ | Redis hostname | `redis` |
| `REDIS_PORT` | ❌ | Redis port | `6379` |
| `LOG_LEVEL` | ❌ | Log level | `INFO` |
| `LOG_FILE` | ❌ | Log file path | `logs/hh_bot.log` |

[See all variables →](.env.example)

## 🚀 Common Commands

### Docker
```bash
# Start bot
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f bot

# Check Redis
docker-compose exec redis redis-cli ping

# Stop bot
docker-compose down
```

### Python
```bash
# Run bot
python main.py

# Run with debug logging
LOG_LEVEL=DEBUG python main.py

# Run in background
python main.py &
tail -f logs/hh_bot.log
```

## 📧 Common Issues

### "TELEGRAM_BOT_TOKEN not set"
- Check `.env` file exists
- Verify token is set: `grep TELEGRAM_BOT_TOKEN .env`
- Restart bot: `docker-compose restart bot`

### "Redis connection refused"
- Check Redis is running: `docker-compose ps`
- Verify Redis service started: `docker-compose logs redis`
- Restart: `docker-compose restart redis`

### "ModuleNotFoundError"
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version`

[All issues & solutions →](PROBLEMS_AND_SOLUTIONS.md)

## 🕣 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Make your changes
4. Write tests for new functionality
5. Ensure all tests pass: `pytest tests/ -v`
6. Commit your changes: `git commit -am 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing`
8. Submit a Pull Request

## 📝 Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Test changes
- `chore:` Maintenance
- `docker:` Docker-related
- `ci:` CI/CD changes

Example: `feat: add job matching algorithm`

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 📚 Additional Resources

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Aiogram Documentation](https://aiogram.dev/)
- [HeadHunter API](https://dev.hh.ru/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Docker Documentation](https://docs.docker.com/)
- [Redis Documentation](https://redis.io/docs/)

## 💁 Support

Having issues? Check these in order:

1. [📖 Quick Start](QUICK_START.md) - Setup instructions
2. [🔐 Security Setup](SECURITY_SETUP.md) - Credentials guide
3. [🚀 Deployment Guide](DEPLOYMENT_GUIDE.md) - Deployment help
4. [🆘 Problems & Solutions](PROBLEMS_AND_SOLUTIONS.md) - Troubleshooting
5. [📖 Usage Guide](USAGE_GUIDE.md) - How to use

## 🎯 Quick Navigation

| I want to... | Read this |
|-------------|----------|
| Deploy to production | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) |
| Fix an error | [PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md) |
| Understand the code | [ANALYSIS_REPORT.md](ANALYSIS_REPORT.md) |
| Set up credentials | [SECURITY_SETUP.md](SECURITY_SETUP.md) |
| Use the bot | [USAGE_GUIDE.md](USAGE_GUIDE.md) |
| Contribute code | [CONTRIBUTING.md](CONTRIBUTING.md) (if exists) |
| Run tests | See [Testing](#-testing) section |

## 🚀 You're Ready!

```bash
# Choose your deployment method:

# Option 1: Docker (recommended)
cp .env.example .env
# Edit .env
docker-compose up -d

# Option 2: Python
cp .env.example .env
# Edit .env
pip install -r requirements.txt
python main.py
```

---

**Version:** 1.0 (Production Ready) 🚀  
**Last Updated:** December 22, 2025  
**Status:** Active Development  
**Python:** 3.8+  
**License:** MIT  
**Docker:** ✅ Supported  
**Tests:** ✅ Included  
**CI/CD:** ✅ GitHub Actions  

🔒 **Remember: Keep your `.env` file SAFE and NEVER commit it to Git!** 🔒
