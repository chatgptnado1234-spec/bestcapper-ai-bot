
import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, MessageHandler, Filters

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)

# Создаём диспетчер (нужен для обработки входящих сообщений)
dispatcher = Dispatcher(bot, None, workers=0)

# ОБРАБОТЧИК СООБЩЕНИЙ
def message_handler(update, context):
    chat_id = update.effective_chat.id
    bot.send_message(chat_id, "Бот работает на webhook! 👍")

# Регистрируем обработчик
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))


# ГЛАВНЫЙ ENDPOINT ДЛЯ WEBHOOK
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok", 200


# РУТ ДЛЯ ПРОВЕРКИ
@app.route("/", methods=["GET"])
def index():
    return "Bot is running via webhook!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))