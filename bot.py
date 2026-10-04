import os

from dotenv import load_dotenv
from supabase import create_client

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Telegram username
    username = user.username

    # Check whether token was provided
    if not context.args:

        await update.message.reply_text(
            "Hey! 👋\n\n"
            "I'm Doubtlify.\n"
            "To connect your Telegram account, "
            "please use the Connect Telegram button "
            "on the Doubtlify website."
        )

        return

    token = context.args[0]

    # Find connection request
    response = (
        supabase
        .table("telegram_connections")
        .select("*")
        .eq("connection_token", token)
        .limit(1)
        .execute()
    )

    if not response.data:

        await update.message.reply_text(
            "❌ This connection link is invalid or expired.\n\n"
            "Please generate a new connection link "
            "from Doubtlify."
        )

        return

    connection = response.data[0]

    # Update database
    (
        supabase
        .table("telegram_connections")
        .update({
            "telegram_chat_id": str(chat_id),
            "telegram_username": username,
            "connected": True
        })
        .eq("connection_token", token)
        .execute()
    )

    student_name = connection["student_name"]

    await update.message.reply_text(
        f"🎉 You're connected, {student_name}!\n\n"
        "Doubtlify can now send your study summaries "
        "to this Telegram account.\n\n"
        "You can return to the Doubtlify website and "
        "continue studying. 📚"
    )


def main():

    print("Doubtlify Telegram bot is running...")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.run_polling()


if __name__ == "__main__":
    main()