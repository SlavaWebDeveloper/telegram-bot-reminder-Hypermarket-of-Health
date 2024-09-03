# Этот файл предназначен для создания Telegram-бота, 
# который отправляет сообщение в заданный чат через определённые интервалы времени.

import logging
import os
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

# Загрузка токена из .env файла
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TARGET_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и планировщика
bot = Bot(token=TOKEN)
scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(10)})
scheduler.start()

# Установка московского времени
MSK = pytz.timezone('Europe/Moscow')

async def send_message():
    try:
        await bot.send_message(chat_id=TARGET_CHAT_ID, text="Это сообщение отправлено через 10 секунд.")
        logger.info("Message sent to chat!")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

def job_function():
    asyncio.run_coroutine_threadsafe(send_message(), loop)

def schedule_job():
    # Получаем текущее время по MSK
    now = datetime.now(MSK)
    logger.info(f"Current MSK time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Пример планирования задания
    scheduler.add_job(job_function, 'interval', seconds=10, timezone=MSK)

def main():
    global loop
    loop = asyncio.get_event_loop()
    schedule_job()
    
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        loop.stop()

if __name__ == '__main__':
    main()
