import asyncio
import json
import secrets

import streamlit as st

from google import genai
from google.genai import types
from telegram import Bot

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    SUMMARY_REQUEST_PROMPT,
    SIMPLE_EXPLANATION_PROMPT,
    EXAM_MODE_PROMPT,
    QUIZ_MODE_PROMPT,
    STEP_BY_STEP_PROMPT,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Doubtlify",
    page_icon="📚",
    layout="centered",
)


# ============================================================
# SECRETS
# ============================================================

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]

TELEGRAM_BOT_USERNAME = st.secrets[
    "TELEGRAM_BOT_USERNAME"
]

MODEL_NAME = "gemini-3.6-flash"

USERS_FILE = "users.json"


# ============================================================
# GEMINI CLIENT
# ============================================================

@st.cache_resource
def get_gemini_client():

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


gemini_client = get_gemini_client()


# ============================================================
# TELEGRAM CLIENT
# ============================================================

@st.cache_resource
def get_telegram_bot():

    return Bot(
        token=TELEGRAM_BOT_TOKEN
    )


telegram_bot = get_telegram_bot()


# ============================================================
# USER DATABASE
# ============================================================

def load_users():

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except FileNotFoundError:

        return {}


# ============================================================
# TELEGRAM CONNECTION TOKEN
# ============================================================

def get_connection_token():

    if "telegram_connection_token" not in st.session_state:

        st.session_state.telegram_connection_token = (
            secrets.token_urlsafe(16)
        )

    return st.session_state.telegram_connection_token


# ============================================================
# CHECK TELEGRAM CONNECTION
# ============================================================

def check_telegram_connection():

    token = st.session_state.get(
        "telegram_connection_token"
    )

    if not token:
        return False

    users = load_users()

    if token in users:

        st.session_state.telegram_chat_id = (
            users[token]["telegram_chat_id"]
        )

        st.session_state.telegram_connected = True

        return True

    return False


# ============================================================
# SEND TELEGRAM MESSAGE
# ============================================================

def send_telegram_message(summary):

    chat_id = st.session_state.get(
        "telegram_chat_id"
    )

    if not chat_id:

        return False, "Telegram is not connected."

    try:

        message = (
            "📚 DOUBTLIFY STUDY SUMMARY\n\n"
            f"Student: "
            f"{st.session_state.student_name}\n\n"
            f"{summary}"
        )

        # Telegram has a message length limit.
        if len(message) > 4000:

            message = (
                message[:4000]
                + "\n\n[Summary shortened]"
            )

        asyncio.run(
            telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
            )
        )

        return True, "Summary sent successfully."

    except Exception as error:

        return False, str(error)


# ============================================================
# GEMINI CHAT
# ============================================================

def create_chat():

    personalized_prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + f"The student's name is "
        + f"{st.session_state.student_name}.\n"
        + "Address the student by name naturally "
        + "when appropriate. Do not repeat their "
        + "name in every sentence."
    )

    return gemini_client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=personalized_prompt
        ),
    )


# ============================================================
# ONBOARDING
# ============================================================

if "onboarded" not in st.session_state:

    st.title("📚 Welcome to Doubtlify")

    st.write(
        "Your AI study buddy for questions, "
        "diagrams, notes and concepts."
    )

    st.divider()

    name = st.text_input(
        "What's your name?",
        placeholder="Enter your name"
    )

    if name.strip():

        st.session_state.student_name = name.strip()

        # Generate Telegram connection token
        token = get_connection_token()

        telegram_link = (
            f"https://t.me/"
            f"{TELEGRAM_BOT_USERNAME}"
            f"?start={token}"
        )

        st.subheader("📱 Connect Telegram")

        st.write(
            "Connect your Telegram account so "
            "Doubtlify can send your study summaries "
            "directly to you."
        )

        st.link_button(
            "🔗 Connect Telegram",
            telegram_link,
            use_container_width=True,
        )

        if st.button(
            "🔄 Check Telegram Connection",
            use_container_width=True,
        ):

            if check_telegram_connection():

                st.success(
                    "🟢 Telegram connected successfully!"
                )

            else:

                st.warning(
                    "Telegram isn't connected yet.\n\n"
                    "Click 'Connect Telegram', press "
                    "Start in the Doubtlify bot, then "
                    "come back and check again."
                )

        if st.session_state.get(
            "telegram_connected",
            False
        ):

            st.success(
                "🟢 Telegram is ready!"
            )

            if st.button(
                "🚀 Start Learning",
                use_container_width=True,
            ):

                st.session_state.chat = create_chat()

                st.session_state.messages = []

                st.session_state.onboarded = True

                st.rerun()

    st.stop()


# ============================================================
# MESSAGE FUNCTIONS
# ============================================================

def render_message(message):

    with st.chat_message(message["role"]):

        if message["kind"] == "text":

            st.markdown(
                message["content"]
            )

        elif message["kind"] == "image":

            st.image(
                message["content"]
            )


def add_message(
    role,
    kind,
    content
):

    message = {
        "role": role,
        "kind": kind,
        "content": content,
    }

    st.session_state.messages.append(
        message
    )

    render_message(message)


# ============================================================
# ASK GEMINI
# ============================================================

def ask_gemini(parts):

    try:

        response = (
            st.session_state.chat.send_message(
                parts
            )
        )

        return response.text

    except Exception as error:

        return (
            "Sorry, something went wrong.\n\n"
            f"{error}"
        )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("📚 Doubtlify")

    st.caption(
        f"Welcome, "
        f"{st.session_state.student_name}!"
    )

    st.divider()

    st.subheader("👤 Profile")

    st.write(
        f"Name: **{st.session_state.student_name}**"
    )

    if st.session_state.get(
        "telegram_connected",
        False
    ):

        st.success("🟢 Telegram Connected")

    else:

        st.warning("🔴 Telegram Not Connected")

    st.divider()

    # ========================================================
    # SEND SUMMARY
    # ========================================================

    st.subheader("📱 Study Summary")

    send_summary = st.button(
        "📤 Send Summary to Telegram",
        use_container_width=True,
        disabled=(
            len(st.session_state.messages) <= 1
            or not st.session_state.get(
                "telegram_connected",
                False
            )
        ),
    )

    # ========================================================
    # CLEAR CHAT
    # ========================================================

    clear_chat = st.button(
        "🗑️ Clear Chat",
        use_container_width=True,
    )

    st.divider()

    # ========================================================
    # STUDY MODES
    # ========================================================

    st.subheader("🎓 Study Modes")

    simple_mode = st.button(
        "Simple Explanation",
        use_container_width=True,
    )

    exam_mode = st.button(
        "Exam Mode",
        use_container_width=True,
    )

    steps_mode = st.button(
        "Step-by-Step",
        use_container_width=True,
    )

    quiz_mode = st.button(
        "Quiz Me",
        use_container_width=True,
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.title("📚 Doubtlify")

st.caption(
    "Snap your doubt. Ask anything. Understand better."
)


# ============================================================
# WELCOME MESSAGE
# ============================================================

if not st.session_state.messages:

    welcome = (
        WELCOME_MESSAGE_TEMPLATE.format(
            name=st.session_state.student_name
        )
    )

    add_message(
        "assistant",
        "text",
        welcome
    )


# ============================================================
# DISPLAY CHAT
# ============================================================

else:

    for message in st.session_state.messages:

        render_message(message)


# ============================================================
# CLEAR CHAT
# ============================================================

if clear_chat:

    st.session_state.messages = []

    st.session_state.chat = create_chat()

    st.rerun()


# ============================================================
# SEND SUMMARY
# ============================================================

if send_summary:

    with st.spinner(
        "Creating your revision summary..."
    ):

        summary = ask_gemini(
            [SUMMARY_REQUEST_PROMPT]
        )

    with st.spinner(
        "Sending summary to Telegram..."
    ):

        success, info = (
            send_telegram_message(
                summary
            )
        )

    if success:

        st.success(
            "📱 Summary sent to your Telegram!"
        )

    else:

        st.error(
            f"Couldn't send the summary: {info}"
        )


# ============================================================
# STUDY MODES
# ============================================================

if simple_mode:

    answer = ask_gemini(
        [SIMPLE_EXPLANATION_PROMPT]
    )

    add_message(
        "assistant",
        "text",
        answer
    )


if exam_mode:

    answer = ask_gemini(
        [EXAM_MODE_PROMPT]
    )

    add_message(
        "assistant",
        "text",
        answer
    )


if steps_mode:

    answer = ask_gemini(
        [STEP_BY_STEP_PROMPT]
    )

    add_message(
        "assistant",
        "text",
        answer
    )


if quiz_mode:

    answer = ask_gemini(
        [QUIZ_MODE_PROMPT]
    )

    add_message(
        "assistant",
        "text",
        answer
    )


# ============================================================
# CHAT INPUT
# ============================================================

user_input = st.chat_input(
    "Ask your doubt or upload an image",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png",
        "webp",
    ],
)


# ============================================================
# PROCESS INPUT
# ============================================================

if user_input:

    photo = (
        user_input.files[0]
        if user_input.files
        else None
    )

    text = user_input.text

    parts = []

    # IMAGE
    if photo is not None:

        photo_bytes = photo.getvalue()

        add_message(
            "user",
            "image",
            photo_bytes
        )

        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type,
            )
        )

    # TEXT
    if text:

        add_message(
            "user",
            "text",
            text
        )

        parts.append(text)

    # IMAGE ONLY
    elif photo is not None:

        parts.append(
            "Analyze this educational image "
            "and explain it clearly."
        )

    # GEMINI
    with st.spinner(
        "Doubtlify is thinking..."
    ):

        answer = ask_gemini(parts)

    add_message(
        "assistant",
        "text",
        answer
    )