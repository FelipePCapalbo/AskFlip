import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

app = Flask(__name__)

CHATS_DIR      = Path(__file__).parent / "Chats"
EXTRACTIONS_DIR = Path(__file__).parent / "Extractions"
CHATS_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT = """\
You are a legal assistant specialized exclusively in family law and divorce proceedings.
You must always respond in English, regardless of the language used by the user.
Answer only questions directly related to family law, divorce, or the specific case provided as context.
If a question falls outside this scope, politely decline and redirect to the case at hand.
Always be direct and concise. Do not elaborate beyond what is asked.
The following is the extracted case data you must use as your knowledge base:

{context_json}"""

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    max_tokens=2048,
)

# In-memory sessions: phone_number -> list of {role, text, timestamp}
conversations:   dict[str, list] = {}
# Loaded extraction context: phone_number -> system prompt string with context
active_contexts: dict[str, str]  = {}


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

    with open(CHATS_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(conversations[phone_number], f, ensure_ascii=False, indent=2)

    del conversations[phone_number]
    active_contexts.pop(phone_number, None)


def get_gemini_response(phone_number: str, user_message: str) -> str:
    # Initializes history on first message after context is loaded
    if phone_number not in conversations:
        conversations[phone_number] = []

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Builds LangChain message list: system prompt + conversation history + new message
    system_message = SystemMessage(content=active_contexts[phone_number])
    history = [
        HumanMessage(content=turn["text"]) if turn["role"] == "user"
        else AIMessage(content=turn["text"])
        for turn in conversations[phone_number]
    ]

    response = llm.invoke([system_message] + history + [HumanMessage(content=user_message)])
    reply    = response.content

    # Persists both turns with timestamps
    conversations[phone_number].append({"role": "user",  "text": user_message, "timestamp": timestamp})
    conversations[phone_number].append({"role": "model", "text": reply,        "timestamp": timestamp})

    return reply


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_message = request.form.get("Body", "").strip()
    sender_phone     = request.form.get("From", "")

    twiml = MessagingResponse()

    if incoming_message.lower() == "quit":
        if sender_phone in conversations:
            save_conversation(sender_phone)
        twiml.message("Conversation saved. See you next time.")
        return str(twiml), 200, {"Content-Type": "text/xml"}

    # Gate: requires a valid extraction file to start a session
    if sender_phone not in active_contexts:
        extraction_path = EXTRACTIONS_DIR / incoming_message

        if not extraction_path.exists():
            twiml.message("Please send the name of the extraction file (e.g. Docket 1-1.json) to begin.")
            return str(twiml), 200, {"Content-Type": "text/xml"}

        context_json = extraction_path.read_text(encoding="utf-8")
        active_contexts[sender_phone] = SYSTEM_PROMPT.format(context_json=context_json)
        twiml.message("File loaded. Ask your question.")
        return str(twiml), 200, {"Content-Type": "text/xml"}

    reply_text = get_gemini_response(sender_phone, incoming_message)
    twiml.message(reply_text)

    return str(twiml), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    port   = int(os.getenv("FLASK_PORT", 5000))
    domain = os.getenv("NGROK_DOMAIN")

    start_ngrok(port, domain)
    app.run(port=port, debug=False)
