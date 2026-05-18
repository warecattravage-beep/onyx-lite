#!/usr/bin/env python3
"""
✦ Onyx Lite — Minimal agent. One file, stdlib only.

Usage:
    python3 onyx_lite.py          Start interactive chat
    python3 onyx_lite.py "hello"  Single question
    python3 onyx_lite.py --setup  Quick setup
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

# ── Config ──
CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_CONFIG = {
    "name": "Onyx",
    "model": "gemma2:2b",
    "host": "http://localhost:11434",
    "ollama_path": "ollama",
    "theme": "violet",
}

NAME = "Onyx"
MODEL = "gemma2:2b"
HOST = "http://localhost:11434"
THEME = "violet"

# ── ANSI colors ──
C = lambda: None
C.V = "\033[38;5;141m" if sys.stdout.isatty() else ""
C.G = "\033[38;5;83m" if sys.stdout.isatty() else ""
C.C = "\033[38;5;51m" if sys.stdout.isatty() else ""
C.D = "\033[38;5;240m" if sys.stdout.isatty() else ""
C.B = "\033[1m" if sys.stdout.isatty() else ""
C.N = "\033[0m" if sys.stdout.isatty() else ""


# ── Config ──

def load_config():
    global NAME, MODEL, HOST, THEME
    if CONFIG_PATH.exists():
        try:
            d = json.loads(CONFIG_PATH.read_text())
            NAME = d.get("name", NAME)
            MODEL = d.get("model", MODEL)
            HOST = d.get("host", HOST)
            THEME = d.get("theme", THEME)
        except Exception:
            pass


def save_config():
    CONFIG_PATH.write_text(json.dumps({
        "name": NAME, "model": MODEL, "host": HOST, "theme": THEME,
    }, indent=2))


# ── Setup ──

def run_setup():
    global NAME, MODEL, HOST
    print(f"\n{C.V}✦ Onyx Lite — Setup{C.N}\n")
    inp = input(f"  Agent name [{NAME}]: ").strip()
    if inp: NAME = inp
    inp = input(f"  Ollama model [{MODEL}]: ").strip()
    if inp: MODEL = inp
    inp = input(f"  Ollama host [{HOST}]: ").strip()
    if inp: HOST = inp
    save_config()
    print(f"\n{C.G}✓ Saved! Run: python3 {Path(__file__).name}{C.N}\n")


# ── Ollama chat ──

def chat_ollama(messages: list[dict]) -> str:
    """Call Ollama API via subprocess (no httpx needed)."""
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7},
    })
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{HOST}/api/chat",
             "-d", payload],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            return f"Error: Ollama not reachable at {HOST}"
        data = json.loads(r.stdout)
        return data.get("message", {}).get("content", "")
    except json.JSONDecodeError:
        return "Error: Ollama returned invalid response"
    except subprocess.TimeoutExpired:
        return "Error: request timed out"
    except FileNotFoundError:
        return "Error: curl not found. Install curl or use the full Onyx Agent."


def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        r = subprocess.run(
            ["curl", "-s", f"{HOST}/api/tags"],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def pull_model() -> bool:
    """Pull the model if not available."""
    print(f"  {C.D}Pulling {MODEL} (first time may take a minute)...{C.N}")
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{HOST}/api/pull",
         "-d", json.dumps({"model": MODEL})],
        capture_output=True, text=True, timeout=300,
    )
    return r.returncode == 0


# ── Skills ──

SKILLS = ["chat", "terminal", "coding"]


def run_terminal(cmd: str) -> str:
    """Run a shell command (safe blocklist)."""
    blocklist = ["sudo", "su ", "rm -rf /", "dd if=", "mkfs", "shutdown", "reboot"]
    for b in blocklist:
        if cmd.lower().startswith(b):
            return f"Blocked: {b}"
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = ""
        if r.stdout: out += r.stdout.strip()[:2000]
        if r.stderr: out += f"\n(r)/n{r.stderr.strip()[:500]}"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "Timed out"
    except Exception as e:
        return f"Error: {e}"


def run_code(code: str, lang: str = "py") -> str:
    """Run code in a temp file."""
    interpreters = {"py": "python3", "sh": "bash", "js": "node"}
    ext = lang.lower().strip(".")
    interp = interpreters.get(ext)
    if not interp:
        return f"Unsupported: {lang}"
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=f".{ext}", delete=False) as f:
            f.write(code)
            tmp = f.name
        r = subprocess.run([interp, tmp], capture_output=True, text=True, timeout=30, cwd="/tmp")
        Path(tmp).unlink(missing_ok=True)
        out = ""
        if r.stdout: out += r.stdout.strip()[:2000]
        if r.stderr: out += f"\n(r)/n{r.stderr.strip()[:500]}"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "Timed out"
    except Exception as e:
        return f"Error: {e}"


def process_skills(response: str) -> str:
    """Parse and run @skill() calls."""
    import re
    def repl(m):
        name = m.group(1)
        args_str = m.group(2)
        kwargs = {}
        for pair in args_str.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                kwargs[k.strip()] = v.strip().strip("\"'")
        if name == "terminal":
            return run_terminal(kwargs.get("command", ""))
        elif name == "coding":
            return run_code(kwargs.get("code", ""), kwargs.get("language", "py"))
        return f"(unknown skill: {name})"
    return re.sub(r'@(\w+)\(([^)]*)\)', repl, response)


# ── Chat ──

def build_messages(text: str, history: list, system_extra: str = "") -> list[dict]:
    skills_list = ", ".join(SKILLS)
    system = (
        f"You are {NAME}, a helpful AI assistant.\n"
        f"You have up to 10 reasoning steps to complete tasks.\n"
        f"Available: @terminal(command), @coding(code, language)\n"
        f"When you need to do something, use a skill. After it runs, continue.\n"
        f"When done, give a final answer.\n"
        f"Personality: Helpful, efficient."
    )
    if system_extra:
        system += f"\n{system_extra}"
    msgs = [{"role": "system", "content": system}]
    for h in history[-10:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": text})
    return msgs


def chat_loop():
    """Interactive chat loop."""
    history = []
    print(f"\n{C.V}  ✦ {NAME} Lite  |  Model: {MODEL}  |  /help  /quit{C.N}")
    print(f"  {C.D}Type your message, Enter to send.{C.N}\n")

    while True:
        try:
            text = input(f"  {C.V}✦{C.N} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() == "/quit":
            break
        if text.lower() == "/help":
            print(f"  {C.D}/help  /quit  /status  /clear{C.N}")
            continue
        if text.lower() == "/clear":
            history.clear()
            print(f"  {C.D}Memory cleared.{C.N}")
            continue
        if text.lower() == "/status":
            print(f"  {C.D}Model: {MODEL}  Host: {HOST}{C.N}")
            continue
        if text.lower() == "/models":
            try:
                r = subprocess.run(["curl", "-s", f"{HOST}/api/tags"],
                                   capture_output=True, text=True, timeout=5)
                data = json.loads(r.stdout)
                models = [m["name"] for m in data.get("models", [])]
                print(f"  {C.D}Available: {', '.join(models)}{C.N}")
            except Exception:
                print(f"  {C.D}Could not fetch models{C.N}")
            continue

        # Show typing effect
        sys.stdout.write(f"  {C.D}...{C.N}")
        sys.stdout.flush()

        # Autonomous loop
        messages = build_messages(text, history)
        final = ""
        max_steps = 10

        for step in range(max_steps):
            response = chat_ollama(messages)
            skill_result = process_skills(response)

            if skill_result == response:
                # No skill calls — final answer
                final = response
                break

            # Skill was used — feed result back
            messages.append({"role": "assistant", "content": response})
            msgs = messages.copy()
            msgs.append({"role": "user",
                "content": f"Result:\n{skill_result[:1500]}\n\nProceed."})
            response2 = chat_ollama(msgs)
            skill2 = process_skills(response2)
            if skill2 == response2:
                final = response2
                break
            else:
                messages.append({"role": "assistant", "content": response2})
                messages.append({"role": "user",
                    "content": f"Result: {skill2[:1500]}\n\nProceed."})
                response3 = chat_ollama(messages)
                final = response3
                break

        if not final:
            final = "(Done)"

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": final})

        # Clear typing and print
        sys.stdout.write("\r  ")
        sys.stdout.flush()
        print(f"  {C.G}✦{C.N} {final}")
        print()


# ── Single message mode ──

def single_chat(text: str):
    messages = build_messages(text, [])
    response = chat_ollama(messages)
    final = process_skills(response)
    print(final)


# ── Main ──

def main():
    load_config()

    if len(sys.argv) > 1:
        if sys.argv[1] in ("--setup", "-s"):
            run_setup()
            return
        if sys.argv[1] in ("--help", "-h"):
            print(__doc__.strip())
            return
        # Single message
        single_chat(" ".join(sys.argv[1:]))
        return

    # Check Ollama
    if not check_ollama():
        print(f"\n{C.R}✗ Ollama not reachable at {HOST}{C.N}")
        print(f"  Start it: ollama serve")
        print(f"  Or run:   python3 {Path(__file__).name} --setup")
        print()
        sys.exit(1)

    chat_loop()


if __name__ == "__main__":
    main()
