import telebot

BOT_TOKEN = "8336864920:AAGfdyNt-ZovdJ5viVRtAlfCgp46R7WMoAY"

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Бот активирован и работает.")

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

bot.polling()
