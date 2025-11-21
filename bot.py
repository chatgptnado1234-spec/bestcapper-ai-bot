
import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Создаём Flask для Render
app = Flask(__name__)

# Создаём Telegram App
telegram_app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает! 🎉")


telegram_app.add_handler(CommandHandler("start", start))


# --- WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.process_update(update)
    return "ok", 200


@app.route("/")
def home():
    return "Bot is running!", 200


# Запуск локально (Render игнорирует это)
if __name__ == "__main__":
    app.run(port=5000)