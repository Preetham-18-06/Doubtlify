import json
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

USERS_FILE = "users.json"


def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id
    user = update.effective_user

    if context.args:

        connection_token = context.args[0]

        users = load_users()

        users[connection_token] = {
            "telegram_chat_id": chat_id,
            "telegram_username": user.username,
            "telegram_name": user.first_name,
        }

        save_users(users)

        await update.message.reply_text(
            "✅ Telegram connected successfully!\n\n"
            "You can now return to Doubtlify.\n"
            "Your study summaries will be sent here. 📚"
        )

    else:

        await update.message.reply_text(
            "Hey! 👋\n\n"
            "I'm Doubtlify, your AI study buddy. 📚\n\n"
            "Please connect to me through the "
            "Doubtlify website."
        )


def main():

    if not TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is missing."
        )

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    print("Doubtlify Telegram bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()