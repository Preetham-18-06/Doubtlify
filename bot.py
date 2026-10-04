import os

from dotenv import load_dotenv
from supabase import create_client

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# --------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# --------------------------------------------------
# VALIDATE ENVIRONMENT VARIABLES
# --------------------------------------------------

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY is missing")


# --------------------------------------------------
# SUPABASE CLIENT
# --------------------------------------------------

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# --------------------------------------------------
# /START COMMAND
# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    chat_id = update.effective_chat.id

    username = user.username

    if not context.args:

        await update.message.reply_text(
            "Hey! 👋\n\n"
            "I'm Doubtlify.\n"
            "To connect your Telegram account, "
            "please use the Connect Telegram button "
            "on the Doubtlify website."
        )

        return

    token = context.args[0].strip()

    # DEBUG: show the token received by the bot
    print("TOKEN RECEIVED BY BOT:", token)

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
            "❌ This Doubtlify connection link is invalid "
            "or has expired.\n\n"
            "Don't worry — your Doubtlify account is still "
            "safe and unchanged.\n\n"
            "Return to the Doubtlify website and click "
            "'Connect Telegram' to generate a new link."
        )

        return

    connection = response.data[0]

    student_name = connection.get("student_name", "Student")

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

    await update.message.reply_text(
        f"🎉 You're connected, {student_name}!\n\n"
        "Your Telegram account is now connected to "
        "Doubtlify. 🔗\n\n"
        "You can return to the Doubtlify website and "
        "continue studying. 📚"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("🤖 Doubtlify Telegram bot is running...")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    print("Waiting for Telegram messages...")

    application.run_polling()




# --------------------------------------------------
# RUN BOT
# --------------------------------------------------

if __name__ == "__main__":
    main()