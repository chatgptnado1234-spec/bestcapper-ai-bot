
import logging
from aiogram import Bot, Dispatcher, executor, types
import os
from dotenv import load_dotenv

# Загружаем токен
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("Бот работает! Отправь /help чтобы увидеть команды.")

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.answer("Доступные команды:\n/start — запуск\n/help — помощь")

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
