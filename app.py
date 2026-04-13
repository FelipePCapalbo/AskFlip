import json
import os
import subprocess
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)

# Gemini client setup
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

CHATS_DIR = os.path.join(os.path.dirname(__file__), "Chats")
os.makedirs(CHATS_DIR, exist_ok=True)

# In-memory session: phone_number -> list of {role, text, timestamp}
conversations: dict[str, list] = {}


def start_ngrok(port: int, domain: str) -> subprocess.Popen:
    # Starts ngrok in background pointing the static domain to the local port
    process = subprocess.Popen(
        ["ngrok", "http", f"--url={domain}", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Waits for the tunnel to establish before continuing
    time.sleep(2)
    print(f" * ngrok active at https://{domain}")
    return process


def save_conversation(phone_number: str) -> None:
    # Sanitizes phone number for use in filename (removes "whatsapp:+" prefix)
    clean_number  = phone_number.replace("whatsapp:+", "").replace("+", "")
    session_start = conversations[phone_number][0]["timestamp"]
    filename      = f"{clean_number}_{session_start}.json"

    with open(os.path.join(CHATS_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(conversations[phone_number], f, ensure_ascii=False, indent=2)

    del conversations[phone_number]


def get_gemini_response(phone_number: str, user_message: str) -> str:
    # Initializes history on first contact
    if phone_number not in conversations:
        conversations[phone_number] = []

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Builds Gemini-compatible history from stored turns
    gemini_history = [
        types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
        for turn in conversations[phone_number]
    ]

    # Sends message with accumulated history
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=gemini_history + [types.Content(role="user", parts=[types.Part(text=user_message)])],
    )

    reply = response.text

    # Persists both turns with timestamps
    conversations[phone_number].append({"role": "user",  "text": user_message, "timestamp": timestamp})
    conversations[phone_number].append({"role": "model", "text": reply,         "timestamp": timestamp})

    return reply


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_message = request.form.get("Body", "").strip()
    sender_phone     = request.form.get("From", "")

    if incoming_message.lower() == "quit":
        if sender_phone in conversations:
            save_conversation(sender_phone)
        twiml = MessagingResponse()
        twiml.message("Conversation saved. See you next time.")
        return str(twiml), 200, {"Content-Type": "text/xml"}

    reply_text = get_gemini_response(sender_phone, incoming_message)

    twiml = MessagingResponse()
    twiml.message(reply_text)

    return str(twiml), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    port   = int(os.getenv("FLASK_PORT", 5000))
    domain = os.getenv("NGROK_DOMAIN")

    start_ngrok(port, domain)
    app.run(port=port, debug=False)
