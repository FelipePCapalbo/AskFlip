import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Type

import pypdf
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel

load_dotenv()

DOCUMENTS_DIR  = Path(__file__).parent / "Documents"
EXTRACTIONS_DIR = Path(__file__).parent / "Extractions"
EXTRACTIONS_DIR.mkdir(exist_ok=True)

PDF_PATH = DOCUMENTS_DIR / "Docket 1-1.pdf"

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    max_tokens=8192,
)


# --- Schemas ---

class TimelineEvent(BaseModel):
    date:        str
    event:       str
    form_number: str
    status:      str
    notes:       str


class CaseStatusAndTimeline(BaseModel):
    events: list[TimelineEvent]


# --- Agent abstraction ---

@dataclass
class Agent:
    name:        str             # chave no JSON de saída
    description: str             # instrução de extração para o LLM
    schema:      Type[BaseModel]


AGENTS: list[Agent] = [
    Agent(
        name="case_status_and_timeline",
        description=(
            "Extract every docket entry from the document as a structured timeline. "
            "For each entry capture: the date, the event or filing name, the form number "
            "(use 'N/A' when absent), the status, and any notes or descriptions."
        ),
        schema=CaseStatusAndTimeline,
    ),
]


# --- Core pipeline ---

def read_pdf(path: Path) -> str:
    reader = pypdf.PdfReader(str(path))
    return "\n".join(page.extract_text() for page in reader.pages)


def run_agent(agent: Agent, document_text: str) -> dict:
    chain = llm.with_structured_output(agent.schema)
    result = chain.invoke([
        SystemMessage(content=agent.description),
        HumanMessage(content=document_text),
    ])
    return result.model_dump()


def extract(pdf_path: Path) -> None:
    document_text = read_pdf(pdf_path)

    output = {
        "source":       pdf_path.name,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }

    for agent in AGENTS:
        print(f"Running agent: {agent.name}")
        output[agent.name] = run_agent(agent, document_text)

    output_path = EXTRACTIONS_DIR / (pdf_path.stem + ".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    extract(PDF_PATH)
