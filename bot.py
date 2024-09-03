import asyncio
import logging
import os
import datetime
import pytz
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import gspread

# Загрузка токена из .env файла
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TARGET_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация планировщика
scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(10)})
scheduler.start()

# Установка московского времени
MSK = pytz.timezone('Europe/Moscow')

# Авторизация Google Sheets
gc = gspread.service_account(filename='credentials.json')
worksheet = gc.open('Plant Watering Log').sheet1

# Отслеживание задач полива
pending_tasks = {}
message_ids_to_remove = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Используйте команду /schedule, чтобы настроить сообщение.')

async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        date_str, time_str, *message = context.args
        message_text = ' '.join(message) or "Привет! Не забудь полить, пожалуйста, траву в Витграссе, иначе она завянет))"

        schedule_time = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        schedule_time = MSK.localize(schedule_time)  # Локализуем время в московскую зону
        now = datetime.datetime.now(tz=MSK)
        if schedule_time < now:
            await update.message.reply_text('Время должно быть в будущем.')
            return

        loop = asyncio.get_event_loop()
        scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(send_message(schedule_time, message_text), loop),
            'date',
            run_date=schedule_time
        )
        await update.message.reply_text(f'Сообщение запланировано на {schedule_time}.')
    
    except (IndexError, ValueError):
        await update.message.reply_text('Использование команды: /schedule YYYY-MM-DD HH:MM <текст сообщения, которое должно отправляться>')

async def send_message(schedule_time, message_text: str) -> None:
    try:
        bot = application.bot
        sent_message = await bot.send_message(TARGET_CHAT_ID, message_text)
        follow_up_time = datetime.datetime.now(tz=MSK) + datetime.timedelta(seconds=60)

        loop = asyncio.get_event_loop()
        scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(show_keyboard(sent_message.message_id, schedule_time), loop),
            'date',
            run_date=follow_up_time
        )

        pending_tasks[schedule_time] = {"status": "pending", "message": message_text, "message_id": sent_message.message_id}

        # Отладочный вывод
        logger.info(f"Message scheduled for {schedule_time}. Sent message ID: {sent_message.message_id}")

    except Exception as e:
        logger.error(f"Error sending message: {e}")

async def show_keyboard(message_id: int, schedule_time) -> None:
    keyboard = [[InlineKeyboardButton("Да", callback_data='yes')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        bot = application.bot
        header_message = "Пожалуйста, подтвердите, что полив выполнен)"
        sent_header_message = await bot.send_message(TARGET_CHAT_ID, header_message, reply_markup=reply_markup)

        message_ids_to_remove[schedule_time] = sent_header_message.message_id

        logger.info(f"Keyboard shown for message ID {message_id}")
        logger.info(f"Header message sent with ID {sent_header_message.message_id}")

        await schedule_removal(sent_header_message.message_id, 30)
        await schedule_check_response(schedule_time, 30)

    except Exception as e:
        logger.error(f"Error while showing keyboard: {e}")

async def schedule_removal(message_id: int, seconds: int) -> None:
    loop = asyncio.get_event_loop()
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(remove_message(message_id), loop),
        'date',
        run_date=datetime.datetime.now(tz=MSK) + datetime.timedelta(seconds=seconds)
    )

async def schedule_check_response(schedule_time, seconds: int) -> None:
    loop = asyncio.get_event_loop()
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(check_response(schedule_time), loop),
        'date',
        run_date=datetime.datetime.now(tz=MSK) + datetime.timedelta(seconds=seconds)
    )

async def remove_message(message_id: int) -> None:
    try:
        bot = application.bot
        await bot.delete_message(chat_id=TARGET_CHAT_ID, message_id=message_id)
        logger.info(f"Message removed with ID {message_id}")
    except Exception as e:
        logger.error(f"Error while removing message: {e}")

async def check_response(schedule_time) -> None:
    if schedule_time in pending_tasks and pending_tasks[schedule_time]["status"] == "pending":
        record_watering(schedule_time, False)
        del pending_tasks[schedule_time]

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query.data == 'yes':
        for schedule_time, task in list(pending_tasks.items()):
            if task["status"] == "pending":
                await remove_keyboard(task["message_id"])

                if schedule_time in message_ids_to_remove:
                    header_message_id = message_ids_to_remove[schedule_time]
                    try:
                        await application.bot.delete_message(chat_id=TARGET_CHAT_ID, message_id=header_message_id)
                        logger.info(f"Header message deleted for schedule time {schedule_time}")
                    except Exception as e:
                        logger.error(f"Error while deleting header message: {e}")

                record_watering(schedule_time, True)
                del pending_tasks[schedule_time]
                await update.callback_query.message.reply_text('Спасибо, что полили цветы!')
                break

async def remove_keyboard(message_id: int) -> None:
    try:
        bot = application.bot
        await bot.edit_message_reply_markup(chat_id=TARGET_CHAT_ID, message_id=message_id, reply_markup=None)
        logger.info(f"Keyboard removed for message ID {message_id}")
    except Exception as e:
        logger.error(f"Error while removing keyboard: {e}")

def record_watering(schedule_time, success: bool) -> None:
    try:
        date_str = schedule_time.strftime('%d-%m-%Y')
        time_str = schedule_time.strftime('%H:%M')
        status = "Полив выполнен" if success else "Полив не выполнен"
        worksheet.append_row([date_str, time_str, status])
        logger.info(f"Recorded watering status: {status} for {date_str} {time_str}")
    except Exception as e:
        logger.error(f"Error while recording watering: {e}")

def schedule_jobs():
    job_times = {
        'tue': [(11, 36, "Привет! Не забудь полить, пожалуйста, траву в Витграссе, иначе она завянет)"),
                (11, 40, "Не забудь полить, ещё раз, пожалуйста, траву в Витграссе, иначе она завянет))")],
        'sat': [(10, 0, "Привет! Не забудь полить, пожалуйста, траву в Витграссе, иначе она завянет))"),
                (18, 0, "Не забудь полить, ещё раз, пожалуйста, траву в Витграссе, иначе она завянет))")],
        'sun': [(10, 0, "Привет! Не забудь полить, пожалуйста, траву в Витграссе, иначе она завянет))"),
                (18, 0, "Не забудь полить, ещё раз, пожалуйста, траву в Витграссе, иначе она завянет))")]
    }

    for day, times in job_times.items():
        for hour, minute, message in times:
            job_time = datetime.datetime.now(tz=MSK).replace(hour=hour, minute=minute, second=0, microsecond=0)
            if job_time < datetime.datetime.now(tz=MSK):
                job_time += datetime.timedelta(weeks=1)
            scheduler.add_job(
                lambda message=message, job_time=job_time: asyncio.run_coroutine_threadsafe(send_message(job_time, message), loop),
                'cron',
                day_of_week=day,
                hour=hour,
                minute=minute,
                timezone=MSK
            )

def main() -> None:
    global application, loop
    loop = asyncio.get_event_loop()
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", schedule_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))
    application.add_handler(CallbackQueryHandler(handle_response))

    schedule_jobs()  # Запуск планировщика

    try:
        application.run_polling()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        loop.stop()

if __name__ == '__main__':
    main()
