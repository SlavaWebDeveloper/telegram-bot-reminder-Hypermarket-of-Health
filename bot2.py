# Это тестовый файл для вашего Telegram-бота, который демонстрирует базовую функциональность обработки команд. 
# В данном примере бот отвечает на команду /getchatid, отправляя пользователю ID его чата.

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
    await update.message.reply_text(f'Your chat ID is: {chat_id}')

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("getchatid", get_chat_id))
    
    application.run_polling()

if __name__ == '__main__':
    main()
