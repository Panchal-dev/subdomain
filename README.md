﻿
## 💻 Run Locally

Follow these simple steps to run the bot on your machine:

```bash
# 1️⃣ Install dependencies
pip install -r requirements.txt

# 2️⃣ Activate virtual environment
venv\Scripts\activate

# 3️⃣ Set your Telegram Bot token and Chat ID (replace with your own values)
set TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
set TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# 4️⃣ Run the bot
python -m src.main


## ☁️ Deploy on Railway

Want to host the bot online 24/7? Follow these steps to deploy on Railway effortlessly:

🔼 **Upload your project to GitHub**

🔗 **Go to [Railway](https://railway.app) → Create New Project → Deploy from GitHub**

📂 **Connect your GitHub repo to Railway**

🛠️ **Go to the "Variables" tab and add the following:**

TELEGRAM_BOT_TOKEN = "your_bot_token_here"
TELEGRAM_CHAT_ID = "your_chat_id_here"

✅ **Done!** Railway will auto-deploy and your bot will be live 🎉