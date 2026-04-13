# AskFlip

Sistema de atendimento via WhatsApp com IA generativa (Gemini), construído em Python.

---

## Architecture

```
AskFlip/
├── app.py            # WhatsApp communication layer (Twilio + Flask)
├── Chats/            # Saved conversation sessions (JSON, gitignored)
└── .env              # Environment variables (not versioned)
```

---

## Components

### `app.py` — WhatsApp Gateway

Responsável pela interface entre o WhatsApp e o modelo de linguagem.

| Responsabilidade | Detalhe |
|---|---|
| Tunnel | Sobe o ngrok com domínio estático ao iniciar o processo |
| Webhook | Recebe mensagens via `POST /whatsapp` no formato TwiML (Twilio) |
| Session memory | Mantém histórico de conversa por número de telefone em memória |
| LLM | Envia histórico acumulado ao Gemini 2.0 Flash e retorna a resposta |
| Persistence | Ao receber `quit`, salva a sessão como JSON em `Chats/` e limpa a memória |

**Key functions**

- `start_ngrok(port, domain)` — spawna o processo ngrok e aguarda o túnel estabelecer
- `get_gemini_response(phone_number, user_message)` — gerencia histórico e chama a API do Gemini
- `save_conversation(phone_number)` — serializa a sessão em JSON e remove da memória
- `whatsapp_webhook()` — endpoint Flask que recebe o payload do Twilio e devolve TwiML

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

Criar `.env` na raiz com as variáveis acima e executar:

```bash
python app.py
```

Configurar o webhook do Twilio Sandbox para `https://<NGROK_DOMAIN>/whatsapp`.

---

## Dependencies

| Package | Role |
|---|---|
| `flask` | HTTP server / webhook receiver |
| `twilio` | TwiML response builder |
| `google-genai` | Gemini API client |
| `python-dotenv` | Loads `.env` at runtime |

---

## Roadmap

> Novos componentes devem ser registrados nesta seção à medida que forem adicionados.

- [ ] ...
