# ✦ Onyx Lite

**Minimal AI agent. One file. Zero dependencies (stdlib only).**

Chat with local LLMs through your terminal. No pip install, no setup, no bloat.

## Usage

```bash
python3 onyx_lite.py              # Interactive chat
python3 onyx_lite.py --setup       # Configure model/host
python3 onyx_lite.py "hello"       # Single question
```

## Requirements

- Python 3.10+
- Ollama (running locally)
- curl (for API calls)

## Commands

| Command | What it does |
|---|---|
| `/help` | Show commands |
| `/quit` | Exit |
| `/status` | Show model info |
| `/clear` | Clear memory |
| `/models` | List available models |

## Skills

- `@terminal(command='ls -la')` — Run shell commands
- `@coding(code='print("hi")', language='py')` — Execute code

## Why Lite?

- **One file** — 300 lines, read it all in one go
- **Zero deps** — uses `curl` + `subprocess` instead of httpx
- **Fast startup** — no import overhead
- **Perfect for**: Quick prototyping, low-resource systems, learning how agents work

Full-featured version: https://github.com/warecattravage-beep/onyx-agent-v3
