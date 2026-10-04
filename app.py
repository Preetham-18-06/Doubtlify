import re
import secrets
import requests

import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    SUMMARY_REQUEST_PROMPT,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-3.6-flash"

st.set_page_config(
    page_title="Doubtlify",
    page_icon="📚",
    layout="centered",
)


# ============================================================
# SECRETS
# ============================================================

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_BOT_USERNAME = st.secrets["TELEGRAM_BOT_USERNAME"]


# ============================================================
# CLIENTS
# ============================================================

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


@st.cache_resource
def get_supabase_client():
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


gemini_client = get_gemini_client()
supabase = get_supabase_client()


# ============================================================
# SESSION STATE
# ============================================================

if "onboarded" not in st.session_state:
    st.session_state.onboarded = False

if "messages" not in st.session_state:
    st.session_state.messages = []

if "telegram_token" not in st.session_state:
    st.session_state.telegram_token = None

if "telegram_connected" not in st.session_state:
    st.session_state.telegram_connected = False

if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = None

if "telegram_username" not in st.session_state:
    st.session_state.telegram_username = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_response(text):
    """
    Removes unnecessary Markdown symbols from Gemini responses.
    Keeps the conversation readable inside Streamlit.
    """

    if not text:
        return "I couldn't generate a response."

    # Remove bold/italic markdown
    text = text.replace("**", "")
    text = text.replace("__", "")

    # Remove markdown heading symbols
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Remove markdown bullet stars
    text = re.sub(r"^\s*\*\s+", "• ", text, flags=re.MULTILINE)

    # Remove markdown links but keep the text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    return text.strip()


def render_message(message):
    """
    Display a stored chat message.
    """

    with st.chat_message(message["role"]):

        if message["kind"] == "text":
            st.write(message["content"])

        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role, kind, content):
    """
    Add a message to session state and display it.
    """

    message = {
        "role": role,
        "kind": kind,
        "content": content
    }

    st.session_state.messages.append(message)

    render_message(message)


def create_gemini_chat():
    """
    Create a new Gemini conversation using the Doubtlify system prompt.
    """

    return gemini_client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        )
    )


def ask_gemini(parts):
    """
    Send the user's content to Gemini.
    """

    try:

        response = st.session_state.chat.send_message(parts)

        return clean_response(response.text)

    except Exception as error:

        return (
            "Sorry, I couldn't process that right now.\n\n"
            f"Error: {error}"
        )


# ============================================================
# TELEGRAM / SUPABASE FUNCTIONS
# ============================================================

def create_telegram_connection():
    token = secrets.token_urlsafe(24)

    try:
        response = (
            supabase
            .table("telegram_connections")
            .insert({
                "connection_token": token,
                "student_name": st.session_state.name,
                "telegram_chat_id": None,
                "telegram_username": None,
                "connected": False,
            })
            .execute()
        )

        print("SUPABASE INSERT RESPONSE:", response)

        if not response.data:
            st.error("Could not create Telegram connection.")
            return None

        print("TELEGRAM CONNECTION CREATED:", response.data)

        return token

    except Exception as error:
        st.error(f"Telegram connection error: {error}")
        print("SUPABASE INSERT ERROR:", error)
        return None


def check_telegram_connection(token):
    """
    Check Supabase to see whether Telegram has connected.
    """

    if not token:
        return None

    try:

        response = (
            supabase
            .table("telegram_connections")
            .select(
                "connected, telegram_chat_id, telegram_username"
            )
            .eq(
                "connection_token",
                token
            )
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]

    except Exception as error:

        st.error(
            f"Could not check Telegram connection: {error}"
        )

        return None


def send_telegram_message(chat_id, message):
    """
    Send a message through the Telegram Bot API.
    """

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": chat_id,
        "text": message
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        data = response.json()

        if response.ok and data.get("ok"):
            return True, None

        return False, data.get(
            "description",
            "Telegram could not send the message."
        )

    except Exception as error:

        return False, str(error)


def generate_summary():
    """
    Ask Gemini to summarize the current study session.
    """

    try:

        response = st.session_state.chat.send_message(
            SUMMARY_REQUEST_PROMPT
        )

        return clean_response(response.text)

    except Exception as error:

        return (
            "I couldn't generate your revision summary.\n\n"
            f"Error: {error}"
        )


# ============================================================
# ONBOARDING
# ============================================================

if not st.session_state.onboarded:

    st.title("📚 Doubtlify")

    st.subheader("Your AI study buddy")

    st.write(
        "Let's get you started. First, tell me your name."
    )

    with st.form("onboarding_form"):

        name = st.text_input(
            "Student name",
            placeholder="Enter your name"
        )

        submitted = st.form_submit_button(
            "Start Learning 🚀",
            use_container_width=True
        )

        if submitted:

            if not name.strip():

                st.warning(
                    "Please enter your name to continue."
                )

            else:

                st.session_state.name = name.strip()

                # Create Gemini conversation
                st.session_state.chat = create_gemini_chat()

                # Reset chat
                st.session_state.messages = []

                # Reset Telegram state
                st.session_state.telegram_token = None
                st.session_state.telegram_connected = False
                st.session_state.telegram_chat_id = None
                st.session_state.telegram_username = None

                st.session_state.onboarded = True

                st.rerun()

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("📚 Doubtlify")

    st.caption(
        f"Student: {st.session_state.name}"
    )

    st.divider()

    # --------------------------------------------------------
    # TELEGRAM CONNECTION
    # --------------------------------------------------------

    st.subheader("📱 Telegram")

    connection = None

    if st.session_state.telegram_token:

        connection = check_telegram_connection(
            st.session_state.telegram_token
        )

        if connection:

            st.session_state.telegram_connected = bool(
                connection.get("connected")
            )

            st.session_state.telegram_chat_id = (
                connection.get("telegram_chat_id")
            )

            st.session_state.telegram_username = (
                connection.get("telegram_username")
            )

    if st.session_state.telegram_connected:

        st.success("🟢 Telegram Connected")

        if st.session_state.telegram_username:

            st.caption(
                f"Connected as "
                f"@{st.session_state.telegram_username}"
            )

        else:

            st.caption(
                "Your Telegram account is connected."
            )

        if st.button(
            "🔄 Check Connection",
            use_container_width=True
        ):

            st.rerun()

    else:

        st.info(
            "Connect Telegram to receive "
            "your study summaries."
        )

        if st.session_state.telegram_token is None:

            if st.button(
                "🔗 Connect Telegram",
                use_container_width=True
            ):

                token = create_telegram_connection(
                    
                )

                if token:

                    st.session_state.telegram_token = token

                    st.rerun()

        else:

            telegram_link = (
                f"https://t.me/"
                f"{TELEGRAM_BOT_USERNAME}"
                f"?start="
                f"{st.session_state.telegram_token}"
            )

            st.link_button(
                "📲 Open Doubtlify on Telegram",
                telegram_link,
                use_container_width=True
            )

            st.caption(
                "Open Telegram and press START."
            )

            if st.button(
                "🔄 Check Connection",
                use_container_width=True
            ):

                st.rerun()

    st.divider()

    # --------------------------------------------------------
    # SEND SUMMARY
    # --------------------------------------------------------

    st.subheader("📖 Study Tools")

    can_send_summary = (
        len(st.session_state.messages) > 1
        and st.session_state.telegram_connected
    )

    if st.button(
        "📤 Send Summary to Telegram",
        disabled=not can_send_summary,
        use_container_width=True
    ):

        with st.spinner(
            "Creating your revision summary..."
        ):

            summary = generate_summary()

        telegram_message = (
            f"📚 Doubtlify Study Summary\n\n"
            f"Hi {st.session_state.name}!\n\n"
            f"{summary}\n\n"
            f"Keep learning. You've got this! 💪"
        )

        success, error = send_telegram_message(
            st.session_state.telegram_chat_id,
            telegram_message
        )

        if success:

            st.success(
                "Summary sent to your Telegram! 📲"
            )

        else:

            st.error(
                f"Couldn't send the summary: {error}"
            )

    if not st.session_state.telegram_connected:

        st.caption(
            "Connect Telegram first to enable "
            "the summary button."
        )

    st.divider()

    # --------------------------------------------------------
    # CLEAR CHAT
    # --------------------------------------------------------

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        # Start a completely new Gemini conversation
        st.session_state.chat = create_gemini_chat()

        st.rerun()


# ============================================================
# MAIN PAGE
# ============================================================

st.title("📚 Doubtlify")

st.caption(
    f"Hey {st.session_state.name}! "
    "What are we learning today?"
)


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

if not st.session_state.messages:

    welcome_message = WELCOME_MESSAGE_TEMPLATE.format(
        name=st.session_state.name
    )

    add_message(
        "assistant",
        "text",
        clean_response(welcome_message)
    )

else:

    for message in st.session_state.messages:

        render_message(message)


# ============================================================
# CHAT INPUT
# ============================================================

user_input = st.chat_input(
    "Ask a doubt or upload a study image...",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png",
        "webp"
    ]
)


# ============================================================
# PROCESS USER INPUT
# ============================================================

if user_input:

    photo = (
        user_input.files[0]
        if user_input.files
        else None
    )

    text = user_input.text

    parts = []

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

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
                mime_type=photo.type
            )
        )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    if text:

        add_message(
            "user",
            "text",
            text
        )

        parts.append(text)

    elif photo is not None:

        parts.append(
            "Analyze this study image and help me "
            "understand it step by step."
        )

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    if parts:

        with st.spinner(
            "Doubtlify is thinking..."
        ):

            answer = ask_gemini(parts)

        add_message(
            "assistant",
            "text",
            answer
        )