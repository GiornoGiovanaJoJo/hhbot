# 🔐 Security Setup Guide

## ⚠️  CRITICAL SECURITY NOTICE

**NEVER commit `.env` file to GitHub or any public repository!**

Your `.env` file contains sensitive credentials that can be used to:
- Control your Telegram bot
- Access your HeadHunter recruiter account
- Steal user data
- Impersonate you

---

## 🔍 Step 1: Verify Security Setup

### Check that `.env` is protected:

```bash
# Make sure .env is in .gitignore
cat .gitignore | grep "^.env"

# Should output:
# .env
# .env.local
# .env.*.local
```

### Check that no .env exists in Git history:

```bash
# Search entire Git history for .env file
git log --all --full-history -- ".env*"

# If there is any output - you have a security problem!
# See "Emergency: Token Leaked" section below
```

---

## 🔑 Step 2: Create Your Local .env File

### 2.1 Copy the template:

```bash
cp .env.example .env
```

### 2.2 Never commit it:

```bash
# Verify it's not staged
git status | grep ".env"

# If you see .env - STOP!
# REMOVE IT:
git rm --cached .env
git commit -m "Remove .env from tracking"
```

---

## 📄 Step 3: Get Your Credentials

### Option A: Telegram Bot Token

**Where to get it:**
1. Open Telegram
2. Find **@BotFather**
3. Send `/newbot` command
4. Follow the prompts:
   - Enter bot name (e.g., "my_hh_bot")
   - Enter username (e.g., "my_hh_bot_bot")
5. Copy the token you receive
6. **SAVE IT SECURELY** (password manager, not email)

**Token format:**
```
123456789:ABCdefGHIjklMNOpqrSTuvwxyzABCDEFghi
```

**Edit your `.env`:**
```bash
# Open .env in your editor
TELEGRAM_BOT_TOKEN=<paste_your_token_here>
```

---

### Option B: HeadHunter Credentials

**Where to get them:**
1. Go to https://dev.hh.ru/admin/applications
2. Sign in with your HeadHunter account
3. Click "Create application" (or "Создать приложение")
4. Fill in:
   - **Name**: HH Bot Recruiting Tool
   - **Description**: Auto-recruiting bot for vacancies
   - **Redirect URI**: `http://localhost:8000/auth/callback`
5. Click "Create" (или "Создать")
6. You'll see:
   - **Client ID** - copy it
   - **Client Secret** - copy it

**Edit your `.env`:**
```bash
HH_CLIENT_ID=<paste_your_client_id>
HH_CLIENT_SECRET=<paste_your_client_secret>
HH_REDIRECT_URI=http://localhost:8000/auth/callback
```

---

### Option C: Your Telegram Admin Chat ID

**To get your Chat ID:**
1. Open Telegram
2. Find **@userinfobot**
3. Send any message
4. Bot will reply with your ID

**Edit your `.env`:**
```bash
ADMIN_CHAT_ID=<your_chat_id>
# Example: 123456789
```

---

## 🥘 Step 4: Verify Your Setup

```bash
# 1. Make sure .env exists
ls -la .env

# 2. Make sure .env is in .gitignore
cat .gitignore | grep "^.env"

# 3. Verify .env is not tracked by Git
git status
# Should NOT show ".env" in "Changes to be committed"

# 4. Check that you have all required variables
grep "^[A-Z_]*=" .env | wc -l
# Should be at least 10 variables

# 5. Try to run the bot
python main.py
# If it fails - check .env file for typos
```

---

## 🌐 Step 5: Test the Bot

```bash
# In one terminal:
python main.py

# In another terminal:
# Send /start command to your bot in Telegram
# Check if you receive a response

# Check the logs:
tail -f hh_bot.log
```

---

## 🚨 Emergency: Token Leaked

**If someone might have accessed your token:**

### 1️⃣ Telegram Token Compromised

```bash
# 1. IMMEDIATELY revoke the token:
#    Open Telegram → @BotFather
#    /mybots → Select your bot → Edit Bot → Revoke current token

# 2. Get a new token from @BotFather

# 3. Update .env with new token
TELEGRAM_BOT_TOKEN=<new_token>

# 4. Restart the bot
python main.py

# 5. The old token will stop working in 30 seconds
```

### 2️⃣ HeadHunter Credentials Compromised

```bash
# 1. Go to https://dev.hh.ru/admin/applications

# 2. Delete the old application

# 3. Create a new application
#    (same steps as "Option B" above)

# 4. Copy new Client ID and Client Secret

# 5. Update .env
HH_CLIENT_ID=<new_id>
HH_CLIENT_SECRET=<new_secret>

# 6. Restart the bot
python main.py
```

### 3️⃣ Token Was Pushed to GitHub

**If .env with real token was committed:**

```bash
# 1. IMMEDIATELY revoke all tokens (see above)

# 2. Remove .env from Git history
git filter-branch --tree-filter 'rm -f .env' HEAD

# 3. Force push (careful!)
git push --force-all

# 4. GitHub will also clean up old versions

# 5. Create fresh .env with new tokens
cp .env.example .env
# Add new credentials here

# 6. Make sure .env is in .gitignore

# 7. Commit the fix
git add .gitignore
git commit -m "Fix: Secure .env file and revoke compromised tokens"
git push
```

---

## ❌ Common Mistakes

| ❌ DON'T | ✅ DO |
|----------|-------|
| Commit `.env` | Only commit `.env.example` |
| Share token in chat | Use password manager |
| Email your token | Store locally, nowhere else |
| Push token to GitHub | Use .gitignore |
| Hardcode credentials | Use environment variables |
| Show token in logs | Log only non-sensitive info |
| Same token for dev & prod | Different tokens for each env |
| No backup of token | Save in password manager |
| Forget to revoke old token | Always revoke when changing |
| Ignore .gitignore | Always check before commit |

---

## 📝 Security Checklist

```
📋 Before First Run:
☐ .env file created from .env.example
☐ All credentials filled in correctly
☐ .gitignore contains .env
☐ No .env in Git history (git log --all -- .env)
☐ Running bot locally first
☐ Logs checked for errors

🏰 For Each Session:
☐ .env file on local machine only
☐ Token not shared with anyone
☐ Token not visible in screenshots
☐ Logs don't contain sensitive info
☐ Bot only used for intended purpose

🚨 When Token Might Be Compromised:
☐ Token immediately revoked
☐ New token obtained
☐ .env updated with new token
☐ Bot restarted
☐ Old token confirmed non-functional
☐ Action logged for audit trail
```

---

## 📚 Additional Resources

- [Telegram Bot Security](https://core.telegram.org/bots/api#authorizing-your-bot)
- [HeadHunter API Docs](https://dev.hh.ru/)
- [Environment Variables in Python](https://docs.python.org/3/library/os.html#os.environ)
- [Git Security Best Practices](https://docs.github.com/en/code-security/security-and-analysis/secret-scanning)

---

## 🎆 You're All Set!

✅ Your credentials are secure
✅ Your `.env` won't be committed
✅ You're following security best practices

**Ready to run the bot! 🚀**

```bash
python main.py
```

---

**Last updated**: 2025-12-06  
**Status**: 🛰 All systems secure
