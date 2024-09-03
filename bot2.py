import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    # Попытка получить ID треда
    msg_thread_id = getattr(update.message, 'message_thread_id', 'No thread ID')
    await update.message.reply_text(f'Chat ID: {chat_id}\nMessage Thread ID: {msg_thread_id}')

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("getchatid", get_chat_id))
    
    application.run_polling()

if __name__ == '__main__':
    main()
