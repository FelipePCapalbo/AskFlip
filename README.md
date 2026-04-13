# AskFlip

Sistema de atendimento via WhatsApp com IA generativa (Gemini), construído em Python.

---

## Architecture

```
AskFlip/
├── WhatsApp - Backend.py   # WhatsApp communication layer (Twilio + Flask)
├── Extractor.py            # PDF extraction pipeline (run manually)
├── Documents/              # Source PDFs
├── Extractions/            # Extracted JSON files (gitignored)
├── Chats/                  # Saved conversation sessions (gitignored)
└── .env                    # Environment variables (not versioned)
```

---

## Components

### `WhatsApp - Backend.py` — WhatsApp Gateway

Responsável pela interface entre o WhatsApp e o modelo de linguagem.

| Responsabilidade | Detalhe |
|---|---|
| Tunnel | Sobe o ngrok com domínio estático ao iniciar o processo |
| Webhook | Recebe mensagens via `POST /whatsapp` no formato TwiML (Twilio) |
| Context gate | Primeira mensagem do usuário deve ser o nome do arquivo `.json` em `Extractions/` |
| LLM | `ChatGoogleGenerativeAI` (Gemini 2.5 Flash) com `SystemMessage` de escopo restrito |
| Scope restriction | Respostas limitadas a family law e divórcio, apenas em inglês |
| Session memory | Histórico de conversa por número de telefone em memória |
| Persistence | Ao receber `quit`, salva a sessão como JSON em `Chats/` e limpa a memória |

**Key functions**

- `start_ngrok(port, domain)` — spawna o processo ngrok e aguarda o túnel estabelecer
- `get_gemini_response(phone_number, user_message)` — monta mensagens LangChain com system prompt + histórico e chama o LLM
- `save_conversation(phone_number)` — serializa a sessão em JSON e remove da memória
- `whatsapp_webhook()` — endpoint Flask com gate de contexto e roteamento de mensagens

---

### `Extractor.py` — PDF Extraction Pipeline

Extrai dados estruturados de PDFs via agentes LangChain com `with_structured_output`. Executado manualmente para gerar os arquivos em `Extractions/`.

| Responsabilidade | Detalhe |
|---|---|
| PDF reading | `pypdf` concatena o texto de todas as páginas |
| Agent abstraction | Dataclass `Agent` com `name`, `description` e `schema` Pydantic |
| Structured output | `ChatGoogleGenerativeAI.with_structured_output` garante JSON válido sem parsing manual |
| Output | `Extractions/{pdf_stem}.json` com metadados e resultado de cada agente |

**Agents**

| Agent key | Schema | Description |
|---|---|---|
| `case_status_and_timeline` | `CaseStatusAndTimeline` | Extrai todos os eventos do docket como lista de `TimelineEvent` (`date`, `event`, `form_number`, `status`, `notes`) |

**Key functions**

- `read_pdf(path)` — lê o PDF e retorna o texto completo
- `run_agent(agent, document_text)` — invoca o LLM com structured output e retorna dict
- `extract(pdf_path)` — orquestra leitura, agentes e escrita do JSON final

**JSON de saída**
```json
{
  "source": "Docket 1-1.pdf",
  "extracted_at": "2026-04-13T...",
  "case_status_and_timeline": {
    "events": [
      { "date": "Oct 02, 2023", "event": "Petition for Dissolution of Marriage", "form_number": "12.901(b)(1)", "status": "Accepted", "notes": "Case opened by Petitioner." }
    ]
  }
}
```

---

## Chat flow

```
User sends "Docket 1-1.json"
  → File found in Extractions/ → context loaded → "File loaded. Ask your question."
  → File not found             → deterministic reply asking for a valid filename

User sends any message (context loaded)
  → LLM responds within family law / divorce scope only, always in English

User sends "quit"
  → Conversation saved to Chats/{number}_{timestamp}.json → session cleared
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | API key do Google Gemini |
| `NGROK_DOMAIN` | Domínio estático do ngrok (ex: `xyz.ngrok-free.app`) |
| `FLASK_PORT` | Porta local do Flask (padrão: `5000`) |

---

## Setup

```bash
pip install -r requirements.txt
```

Criar `.env` na raiz com as variáveis acima.

**Extraction** (run once per document):
```bash
python Extractor.py
```

**Chat server:**
```bash
python "WhatsApp - Backend.py"
```

Configurar o webhook do Twilio Sandbox para `https://<NGROK_DOMAIN>/whatsapp`.

---

## Dependencies

| Package | Role |
|---|---|
| `flask` | HTTP server / webhook receiver |
| `twilio` | TwiML response builder |
| `google-genai` | Gemini API client (direct) |
| `langchain-google-genai` | `ChatGoogleGenerativeAI` with `SystemMessage` and `with_structured_output` |
| `pypdf` | PDF text extraction |
| `python-dotenv` | Loads `.env` at runtime |

---

## Roadmap

> Novos agentes devem ser adicionados em `Extractor.py` como entradas em `AGENTS`, com schema Pydantic próprio.

- [ ] ...
