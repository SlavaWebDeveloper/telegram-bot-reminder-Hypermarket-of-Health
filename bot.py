import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import os
from dotenv import load_dotenv
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job

# Загрузка токена из .env файла
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Загрузка id чата из .env файла
TARGET_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация планировщика
scheduler = BackgroundScheduler()
scheduler.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Используйте команду /schedule, чтобы настроить сообщение.')

async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Параметры команды: /schedule YYYY-MM-DD HH:MM сообщение
        date_str, time_str, *message = context.args
        message_text = ' '.join(message)

        # Обработка времени
        schedule_time = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        now = datetime.datetime.now()
        if schedule_time < now:
            await update.message.reply_text('Время должно быть в будущем.')
            return
        
        # Добавление задачи в планировщик
        loop = asyncio.get_event_loop()
        scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(send_message(message_text), loop), 'date', run_date=schedule_time)
        await update.message.reply_text(f'Сообщение запланировано на {schedule_time}.')
    
    except (IndexError, ValueError):
        await update.message.reply_text('Использование команды: /schedule YYYY-MM-DD HH:MM <текст сообщения, которое должно отправляться>')

async def send_message(message_text: str) -> None:
    bot = application.bot
    await bot.send_message(TARGET_CHAT_ID, message_text)

def main() -> None:
    global application
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", schedule_message))

    application.run_polling()

if __name__ == '__main__':
    main()
