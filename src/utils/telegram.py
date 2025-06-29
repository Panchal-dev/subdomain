from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import os
import asyncio
import json

flask_app = Flask(__name__)

class TelegramBot:
    def __init__(self, bot_token, chat_id, subfinder):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.subfinder = subfinder
        self.app = Application.builder().token(bot_token).build()
        self.is_running = False
        self.cancel_event = asyncio.Event()
        self.last_message_id = None
        self.setup_handlers()
        self.setup_webhook()

    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("cmd", self.cmd))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("cancel", self.cancel))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    def setup_webhook(self):
        @flask_app.route(f"/{self.bot_token}", methods=["POST"])
        def webhook():
            try:
                update = Update.de_json(request.get_json(), self.app.bot)
                if update:
                    asyncio.run_coroutine_threadsafe(self.app.process_update(update), self.app.loop)
                return "OK", 200
            except Exception as e:
                print(f"Webhook error: {str(e)}")
                return "Error", 500

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Welcome to the Subdomain Enumerator Bot!\n"
            "Send a domain, multiple domains (one per line), or a .txt file path.\n"
            "Commands:\n"
            "/cmd - List all commands\n"
            "/status - Check scan status\n"
            "/cancel - Cancel current scan\n"
            "Example: wibmo.com\nor\nwibmo.com\npayu.in"
        )

    async def cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Available commands:\n"
            "/start - Show welcome message\n"
            "/cmd - List all commands\n"
            "/status - Check scan status\n"
            "/cancel - Cancel current scan\n"
            "Or send a domain, multiple domains (one per line), or a .txt file path."
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status = "Scanning in progress..." if self.is_running else "No scan is currently running."
        await update.message.reply_text(status)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_chat.id) != self.chat_id:
            await update.message.reply_text("Unauthorized chat ID.")
            return
        if self.is_running:
            self.cancel_event.set()
            await update.message.reply_text("Scan cancellation requested. Please wait...")
        else:
            await update.message.reply_text("No scan is currently running.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_chat.id) != self.chat_id:
            await update.message.reply_text("Unauthorized chat ID.")
            return

        message_id = update.message.message_id
        if message_id == self.last_message_id:
            return
        self.last_message_id = message_id

        if self.is_running:
            await update.message.reply_text("A scan is already in progress. Use /cancel to stop it.")
            return

        text = update.message.text.strip()
        if not text:
            await update.message.reply_text("Please provide a domain, multiple domains (one per line), or a .txt file path.")
            return

        self.cancel_event.clear()
        self.is_running = True

        try:
            if text.endswith('.txt') and os.path.isfile(text):
                await update.message.reply_text(f"Detected file input: {text}")
                await self.subfinder.run_async(text, is_file=True, cancel_event=self.cancel_event)
            else:
                domains = [d.strip() for d in text.split('\n') if d.strip()]
                if not domains:
                    await update.message.reply_text("No valid input provided.")
                    return
                await self.subfinder.run_async(domains, is_file=False, cancel_event=self.cancel_event)
        finally:
            self.is_running = False

    async def send_message(self, message):
        try:
            await self.app.bot.send_message(chat_id=self.chat_id, text=message)
            print("Telegram notification sent successfully.")
        except Exception as e:
            print(f"Error sending Telegram notification: {str(e)}")

    async def send_file(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                await self.app.bot.send_document(chat_id=self.chat_id, document=file, filename=os.path.basename(file_path))
            print(f"Telegram file sent successfully: {file_path}")
        except Exception as e:
            print(f"Error sending Telegram file: {str(e)}")

    def run(self):
        port = int(os.getenv("PORT", 8080))
        flask_app.run(host="0.0.0.0", port=port)